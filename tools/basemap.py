"""Basemap for the UK map: Natural Earth 1:10m land (world-atlas@2 countries-10m),
drawn at build time into SVG paths. Equal metres on both axes about 54.5°N."""
import json, math, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "cache" / "countries-10m.json"
OUT = ROOT / "docs" / "data" / "base.json"

LAT0, LON0 = 54.5, -3.5
BBOX = (-11.0, 49.6, 2.6, 61.0)          # lon min, lat min, lon max, lat max
K = 100.0                                # px per degree of latitude
KEEP = {"United Kingdom", "Ireland", "Isle of Man", "France", "Belgium",
        "Netherlands", "Guernsey", "Jersey"}


def project(lon, lat):
    return ((lon - LON0) * math.cos(math.radians(LAT0)) * K, -(lat - LAT0) * K)


def arcs_of(topo):
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    out = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx; y += dy
            pts.append((x * sx + tx, y * sy + ty))
        out.append(pts)
    return out


def ring(arcs, idx):
    pts = []
    for i in idx:
        a = arcs[i] if i >= 0 else arcs[~i][::-1]
        pts.extend(a if not pts else a[1:])
    return pts


def main():
    topo = json.loads(SRC.read_text())
    arcs = arcs_of(topo)
    x0, y1 = project(BBOX[0], BBOX[1])
    x1, y0 = project(BBOX[2], BBOX[3])
    paths = []
    for g in topo["objects"]["countries"]["geometries"]:
        name = g["properties"]["name"]
        if name not in KEEP:
            continue
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        d = []
        for poly in polys:
            for r in poly:
                pts = ring(arcs, r)
                if not any(BBOX[0] - 3 < lo < BBOX[2] + 3 and BBOX[1] - 3 < la < BBOX[3] + 3
                           for lo, la in pts):
                    continue
                xy = []
                for lo, la in pts:
                    x, y = project(lo, la)
                    if not xy or abs(x - xy[-1][0]) + abs(y - xy[-1][1]) > 0.9:
                        xy.append((x, y))
                if len(xy) < 4:
                    continue
                d.append("M" + "L".join(f"{x - x0:.1f},{y - y0:.1f}" for x, y in xy) + "Z")
        if d:
            paths.append({"name": name, "home": name in ("United Kingdom", "Isle of Man"),
                          "d": "".join(d)})
    # scale bar: 100 km in px at LAT0 (1° lat ≈ 111.2 km)
    km100 = 100 / 111.2 * K
    OUT.write_text(json.dumps({
        "w": round(x1 - x0, 1), "h": round(y1 - y0, 1),
        "proj": {"lat0": LAT0, "lon0": LON0, "k": K, "x0": round(x0, 3), "y0": round(y0, 3)},
        "km100": round(km100, 2),
        "source": "Natural Earth 1:10m via world-atlas@2 (public domain)",
        "paths": paths}, separators=(",", ":")))
    print(f"base.json: {len(paths)} countries, {OUT.stat().st_size // 1024} KB, "
          f"{x1 - x0:.0f}x{y1 - y0:.0f}")


if __name__ == "__main__":
    main()
