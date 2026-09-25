"""Merge the researched rows into docs/data/list.json (company-level fields only; named
people stay out of the public page) and write the full calling list with names to the
private delivery folder. Geocodes each firm's town with Nominatim, cached on disk."""
import csv, json, math, pathlib, re, subprocess, sys, time, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
RES = ROOT.parent / "rtp-partner" / "research"
DELIVER = ROOT.parent / "rtp-partner" / "deliver"
OUT = ROOT / "docs" / "data" / "list.json"
GEO = ROOT / "cache" / "geocode.json"

RTP_OFFICE = "124 City Road, London EC1V 2NX"
UK_BOX = (-8.7, 49.8, 1.9, 60.9)


def read_tsv(path):
    with open(path, newline="") as f:
        rows = [r for r in csv.reader(f, delimiter="\t") if r and any(c.strip() for c in r)]
    head = [h.strip().lstrip("#").strip() or "n" for h in rows[0]]
    return [dict(zip(head, r)) for r in rows[1:]]


def tier_of(verdict):
    v = (verdict or "").lower()
    if "drop" in v:
        return None
    for t in "abc":
        if re.search(rf"\b{t}\b", v):
            return t.upper()
    return None


def geocode(q, cache):
    if q in cache:
        return cache[q]
    url = ("https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=gb&q="
           + urllib.parse.quote(q))
    out = subprocess.run(["curl", "-s", "-A", "hongdam-rtp-map/1.0 (nan@motdang.net)", url],
                         capture_output=True, text=True).stdout
    time.sleep(1.1)
    try:
        hit = json.loads(out)[0]
        cache[q] = [round(float(hit["lon"]), 4), round(float(hit["lat"]), 4), hit["display_name"]]
    except Exception:
        cache[q] = None
    GEO.write_text(json.dumps(cache, ensure_ascii=False, indent=0))
    return cache[q]


def town_of(region):
    r = re.sub(r"\(.*?\)", "", region or "")          # drop parentheticals
    r = re.sub(r"(?i)^\s*(reg\.?\s*office|head\s*office|hq)[:\s]*", "", r)
    r = re.split(r"[,/;]| and |\+", r)[0]              # first place, before any comma
    r = re.sub(r"\b[A-Z]{1,2}\d[A-Z\d]?\b.*", "", r)   # drop a trailing postcode + rest
    r = r.replace("UK", "").replace("t/a", "").strip(" ,.")
    return r


def km(a, b):
    (lo1, la1), (lo2, la2) = a, b
    p = math.pi / 180
    h = (math.sin((la2 - la1) * p / 2) ** 2
         + math.cos(la1 * p) * math.cos(la2 * p) * math.sin((lo2 - lo1) * p / 2) ** 2)
    return 2 * 6371 * math.asin(math.sqrt(h))


def urls(s):
    return re.findall(r"https?://[^\s,;|)]+", s or "")


def main():
    finished = sorted(RES.glob("finish-*.tsv")) + sorted(RES.glob("harvest-*.tsv"))
    rows = []
    if finished:
        for p in finished:
            for r in read_tsv(p):
                t = tier_of(r.get("verdict"))
                if t:
                    r["tier"] = t
                    r["file"] = p.name
                    rows.append(r)
    else:
        sys.exit("no finished rows yet")

    seen, uniq = set(), []
    for r in rows:
        key = re.sub(r"[^a-z0-9]", "", r.get("company", "").lower())
        if key and key not in seen:
            seen.add(key)
            uniq.append(r)
    rows = uniq

    cache = json.loads(GEO.read_text()) if GEO.exists() else {}
    office = geocode(RTP_OFFICE, cache) or geocode("City Road, London", cache)
    public, problems = [], []
    for r in rows:
        town = town_of(r.get("region", ""))
        g = geocode(f"{town}, United Kingdom", cache) if town else None
        if not g:
            problems.append(f"no geocode: {r.get('company')} ({r.get('region')})")
            continue
        lon, lat = g[0], g[1]
        if not (UK_BOX[0] <= lon <= UK_BOX[2] and UK_BOX[1] <= lat <= UK_BOX[3]):
            problems.append(f"outside UK: {r.get('company')} {lat},{lon}")
            continue
        public.append({
            "t": r["tier"], "co": r.get("company", "").strip(),
            "reg": r.get("region", "").strip(), "lon": lon, "lat": lat,
            "km": round(km((office[0], office[1]), (lon, lat))),
            "size": r.get("staff_or_accounts", "").strip(),
            "pt": r.get("pentest_today", "").strip(), "crest": r.get("crest", "").strip(),
            "ev": r.get("evidence", "").strip(), "op": r.get("opener", "").strip().strip('"'),
            "tel": r.get("switchboard", "").strip(),
            "src": list(dict.fromkeys(urls(r.get("sources", "")) + urls(r.get("name_source_url", ""))))[:4],
        })
    order = {"A": 0, "B": 1, "C": 2}
    public.sort(key=lambda x: (order[x["t"]], x["km"]))
    counts = {t: sum(1 for x in public if x["t"] == t) for t in "ABC"}
    OUT.write_text(json.dumps({
        "built": time.strftime("%Y-%m-%d"),
        "office": {"lon": office[0], "lat": office[1], "q": RTP_OFFICE},
        "counts": dict(counts, total=len(public)),
        "rows": public}, ensure_ascii=False, separators=(",", ":")))

    DELIVER.mkdir(exist_ok=True)
    cols = ["tier", "company", "ch_number", "region", "staff_or_accounts", "decision_maker",
            "role", "name_source_url", "second_contact", "switchboard", "pentest_today", "crest",
            "evidence", "opener", "sources", "notes"]
    placed = {x["co"] for x in public}
    with open(DELIVER / "RTP-UK-MSP-calling-list.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(cols + ["tps_ctps_checked", "outcome"])
        for r in sorted(rows, key=lambda r: order[r["tier"]]):
            if r.get("company", "").strip() in placed:
                w.writerow([r.get(c, "").strip() for c in cols] + ["", ""])
    print(f"list.json: {len(public)} rows  A {counts['A']} · B {counts['B']} · C {counts['C']}")
    for p in problems:
        print("  !", p)


if __name__ == "__main__":
    main()
