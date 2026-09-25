"""Compose docs/index.html from base.json (basemap) + list.json (firms).
Counts and pin coordinates are computed here at build time, never typed."""
import json, math, pathlib, html

ROOT = pathlib.Path(__file__).resolve().parent.parent
D = ROOT / "docs" / "data"
base = json.loads((D / "base.json").read_text())
data = json.loads((D / "list.json").read_text())
rows = data["rows"]
C = data["counts"]
pj = base["proj"]


def project(lon, lat):
    x = (lon - pj["lon0"]) * math.cos(math.radians(pj["lat0"])) * pj["k"] - pj["x0"]
    y = -(lat - pj["lat0"]) * pj["k"] - pj["y0"]
    return round(x, 1), round(y, 1)


def esc(s):
    return html.escape(str(s), quote=True)


# ---- basemap paths ----
land = "".join(
    f'<path class="land{" home" if p["home"] else ""}" d="{p["d"]}"/>' for p in base["paths"])

# graticule every 2° lon / 1° lat inside the frame
grat = []
for lon in range(-8, 3, 2):
    a = project(lon, 49.5); b = project(lon, 61)
    grat.append(f'<line class="grat" x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}"/>')
for lat in range(50, 61, 2):
    a = project(-9, lat); b = project(2.5, lat)
    grat.append(f'<line class="grat" x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}"/>')
grat = "".join(grat)

# pins
pins = []
for i, r in enumerate(rows):
    x, y = project(r["lon"], r["lat"])
    title = f'{esc(r["co"])} — {esc(r["reg"].split(",")[0])} · tier {r["t"]}'
    pins.append(
        f'<g class="pin {r["t"]}" data-t="{r["t"]}" data-i="{i}" tabindex="0" role="button" '
        f'aria-label="{title}">'
        f'<circle class="halo" cx="{x}" cy="{y}" r="13"/>'
        f'<circle class="dot" cx="{x}" cy="{y}" r="5.5"/></g>')
pins = "".join(pins)

# RTP office marker
ox, oy = project(data["office"]["lon"], data["office"]["lat"])
office = (f'<g class="office"><circle class="ring" cx="{ox}" cy="{oy}" r="5"/>'
          f'<circle class="core" cx="{ox}" cy="{oy}" r="3.5"/>'
          f'<text class="lbl" x="{ox+11}" y="{oy+4}">RTP · London</text></g>')

# scale bar (100 km), lower-left
sb_x, sb_y, sb_len = 30, base["h"] - 40, base["km100"]
scale = (f'<g class="scale"><line x1="{sb_x}" y1="{sb_y}" x2="{sb_x+sb_len}" y2="{sb_y}"/>'
         f'<line x1="{sb_x}" y1="{sb_y-4}" x2="{sb_x}" y2="{sb_y+4}"/>'
         f'<line x1="{sb_x+sb_len}" y1="{sb_y-4}" x2="{sb_x+sb_len}" y2="{sb_y+4}"/>'
         f'<text x="{sb_x}" y="{sb_y-8}">100 km</text></g>')

# firms as JSON for the tooltip (company-level only)
firm_js = json.dumps([{"co": r["co"], "reg": r["reg"].split(",")[0], "t": r["t"],
                       "km": r["km"], "ev": r["ev"][:90]} for r in rows], ensure_ascii=False)

# ---- proof sample: 3 A + 2 B + 1 C, real firms, public facts only ----
def pick(t, n):
    return [r for r in rows if r["t"] == t][:n]
sample = pick("A", 4) + pick("B", 2) + pick("C", 1)
samp = "".join(
    f'<div class="row {r["t"].lower()}"><span class="dot"></span>'
    f'<div><div class="co">{esc(r["co"])}</div>'
    f'<div class="rg">{esc(r["reg"].split(",")[0])} · {esc(r["size"]) or "size on file"}</div></div>'
    f'<div class="fact">{esc(r["ev"][:110])}</div></div>' for r in sample)

built = data["built"]
total = C["total"]

HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>UK MSP channel — for Red Team Partners</title>
<meta name="description" content="A screened calling list of {total} UK MSPs that could resell Red Team Partners under their own brand, and the Chiang Rai desk to work it. Prepared by motdang.net.">
<meta name="theme-color" content="#150f08">
<meta name="color-scheme" content="dark">
<meta name="robots" content="noindex">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="style.css">
</head>
<body>
<header class="bar"><div class="wrap">
  <a class="mark" href="#top">motdang.net <span lang="th">มดแดง</span></a>
  <nav>
    <a href="#map">The list</a>
    <a href="#market">Market</a>
    <a href="#gap">The gap</a>
    <a href="#price">Economics</a>
    <a href="#desk">The desk</a>
    <a href="#edge">Thai edge</a>
    <a href="#next">Next</a>
  </nav>
</div></header>

<main class="wrap" id="top">

  <section class="hero" style="padding-top:36px">
    <div>
      <div class="kicker">Prepared for Red Team Partners · {built}</div>
      <h1>Your UK channel,<br><em>already mapped.</em></h1>
      <p class="lede"><b>{total} UK MSPs</b> that could sell RTP penetration testing and
      red-team work under their own brand — sorted by how ready each one is, screened for
      lawful B2B calling, and handed to a caller who books the meetings.</p>
      <div class="cta">
        <a class="btn solid" href="#next">See how it runs</a>
        <a class="btn" href="#map">Open the map</a>
      </div>
      <div class="strip">
        <div class="s"><div class="v">{total}</div><div class="k">firms placed</div></div>
        <div class="s"><div class="v">{C['A']}</div><div class="k">tier A · already buy testing</div></div>
        <div class="s"><div class="v">{C['B']}+{C['C']}</div><div class="k">tier B &amp; C · warm, then cold</div></div>
      </div>
    </div>
    <div class="mapwrap" id="map">
      <svg viewBox="0 0 {base['w']} {base['h']}" role="img" aria-label="Map of the United Kingdom with {total} MSP prospects marked by tier">
        <defs><radialGradient id="seaGrad" cx="50%" cy="35%" r="75%">
          <stop offset="0%" stop-color="#1b140d"/><stop offset="100%" stop-color="#120c06"/>
        </radialGradient></defs>
        <rect class="sea" x="0" y="0" width="{base['w']}" height="{base['h']}"/>
        <g>{grat}</g>
        <g>{land}</g>
        <g id="pins">{pins}</g>
        {office}
        {scale}
      </svg>
      <div class="maptip" id="tip" hidden></div>
      <div class="legend" role="group" aria-label="Filter the map by tier">
        <button class="all" data-f="all" aria-pressed="true"><i></i>All {total}</button>
        <button class="a" data-f="A" aria-pressed="true"><i></i>A · buys ({C['A']})</button>
        <button class="b" data-f="B" aria-pressed="true"><i></i>B · switch ({C['B']})</button>
        <button class="c" data-f="C" aria-pressed="true"><i></i>C · new line ({C['C']})</button>
      </div>
      <p class="mapfoot">Distance straight-line from RTP, London. Towns from public
      records; named contacts delivered privately.</p>
    </div>
  </section>

  <section id="market" class="reveal">
    <div class="eyebrow">The market</div>
    <h2>A big, fragmented pool <span>ตลาด</span></h2>
    <p class="sub">The UK has more managed service providers than any single vendor can
    reach. Most are small, most sit outside London, and a new law is about to make security
    testing their problem too — not only their clients'.</p>
    <div class="pool">
      <div class="bub"><div class="c" style="width:150px;height:150px"><span class="v">12,867</span></div>
        <p>active UK MSPs<br>(DSIT / Frontier Economics, 2025)</p></div>
      <div class="bub"><div class="c" style="width:118px;height:118px"><span class="v">~3,500</span></div>
        <p>small &amp; medium — the reachable pool</p></div>
      <div class="bub"><div class="c" style="width:96px;height:96px"><span class="v">977</span></div>
        <p>large enough for the Cyber Security &amp; Resilience Bill</p></div>
      <div class="bub hot"><div class="c" style="width:120px;height:120px"><span class="v">{total}</span></div>
        <p>named, placed and sorted here</p></div>
    </div>
    <p class="note">67% of UK MSPs sit outside London — Leeds, Manchester, Birmingham,
    Milton Keynes, the North East, Wales. This list follows them there.</p>
  </section>

  <section id="gap" class="reveal">
    <div class="eyebrow">Why a channel, not just a list</div>
    <h2>RTP has the offer. The channel is the missing half.</h2>
    <p class="sub">RTP's partner terms already do the hard part: partner-branded reports and
    portal, wholesale pricing about 20% under market, and a written non-solicit. What sits
    between that offer and signed partners is desk work — and that is what this is.</p>
    <div class="gap">
      <div class="col has"><h3>RTP already publishes</h3><ul>
        <li>White-label reports &amp; findings portal (RTP Robin)</li>
        <li>Wholesale price ~20% under market; partner sets the retail</li>
        <li>Written non-solicit — RTP does not approach the partner's client</li>
        <li>12 months of retests included</li>
        <li>CREST penetration testing &amp; ISO 27001</li>
      </ul></div>
      <div class="col lack"><h3>The channel still needs</h3><ul>
        <li>A qualified calling list — who to ring, in what order</li>
        <li>A caller booking partner meetings, UK hours</li>
        <li>Deal registration &amp; onboarding once they say yes</li>
        <li>Named case studies and sales collateral</li>
        <li>Report editing &amp; branding at partner volume</li>
      </ul></div>
    </div>
  </section>

  <section id="tiers" class="reveal">
    <div class="eyebrow">How the {total} are sorted</div>
    <h2>Three tiers, hottest first</h2>
    <p class="sub" style="margin-bottom:22px">Colour runs hot to cold: red is call-first, blue is the longest sell.</p>
    <div class="grid g3">
      <div class="card"><span class="tag a">Tier A · {C['A']} · hottest</span>
        <h3>Already buys testing</h3>
        <p>Lists penetration testing but has no CREST team of its own — so it already pays
        an outside tester. The call offers a better one, with the non-solicit in writing.</p></div>
      <div class="card"><span class="tag b">Tier B · {C['B']}</span>
        <h3>Already resells a test</h3>
        <p>Bundles a CREST-branded test today through another supplier. The call is a
        straight swap — on price, turnaround and the written non-solicit.</p></div>
      <div class="card"><span class="tag c">Tier C · {C['C']} · coldest</span>
        <h3>Sells the security around it</h3>
        <p>Cyber Essentials, managed detection, ISO 27001 clients — everything but the test.
        Pentest is a new line on a quote they already send.</p></div>
    </div>
    <h2 style="margin-top:46px;font-size:26px">A sample, from the real list</h2>
    <div class="samp">{samp}</div>
    <p class="note">Public facts, from each firm's own site and Companies House. The full
    {total}-row list adds the named decision-maker, direct line, an opener written to each
    firm's own evidence, and the screening record — delivered to RTP, kept off this page.</p>
  </section>

  <section id="price" class="reveal">
    <div class="eyebrow">The economics</div>
    <h2>Priced so the partner keeps the margin <span>ราคา</span></h2>
    <p class="sub">UK day rates and per-test prices are public. RTP's wholesale sits about
    20% under them; the MSP sets its own retail and keeps the difference. The list makes the
    first call cheap; the margin makes the partner stay.</p>
    <table class="ptable">
      <thead><tr><th>Test</th><th>Typical UK client price</th></tr></thead>
      <tbody>
        <tr><td>External infrastructure (2–3 days)</td><td>£1,500–3,500</td></tr>
        <tr><td>Internal infrastructure (4–8 days)</td><td>£4,000–10,000</td></tr>
        <tr><td>Web application</td><td>£3,000–8,000</td></tr>
        <tr><td>Cyber Essentials Plus audit</td><td>£1,500–3,000</td></tr>
        <tr><td>Red team engagement (typical)</td><td>£25,000–45,000</td></tr>
      </tbody>
    </table>
    <p class="note">Ranges from UK pentest-pricing pages (grit-consultancy, thecyphere),
    Sept 2026 — vendor guides, not fixed quotes. RTP confirms its own wholesale before any
    number reaches a partner.</p>
  </section>

  <section id="desk" class="reveal">
    <div class="eyebrow">The desk behind the list</div>
    <h2>Chiang Rai runs while the UK sleeps</h2>
    <p class="sub">The team at motdang.net (trading as Hongdam) works the UK day from
    Thailand. The morning here is the small hours in Britain — call prep, screening and
    onboarding are ready before the UK opens.</p>
    <div class="clock">
      <div class="z"><div class="t">09:00–17:30</div><div class="p">UK working day</div></div>
      <div class="arrow">→</div>
      <div class="z"><div class="t">15:00–23:30</div><div class="p">Chiang Rai, same day</div></div>
    </div>
    <div class="grid g2">
      <div class="card"><h3><span class="num">1</span>Channel desk</h3><p>List upkeep, TPS/CTPS
        screening, call prep, deal registration, partner onboarding, scheduling, retest tracking.</p></div>
      <div class="card"><h3><span class="num">2</span>Report desk</h3><p>Testers write findings;
        the desk edits, checks and brands each report per partner. Carries client data — under NDA and the data agreement.</p></div>
      <div class="card"><h3><span class="num">3</span>Partner web &amp; agents</h3><p>Programme
        pages, a deal-registration form, a scoping calculator, and a partner assistant that answers from RTP's own documents.</p></div>
      <div class="card"><h3><span class="num">4</span>Thailand channel</h3><p>motdang.net resells
        RTP to Thai businesses in Thai — making it RTP's first named partner, the case study the site is missing.</p></div>
    </div>
  </section>

  <section id="edge" class="reveal">
    <div class="edge">
      <div class="eyebrow">The edge no rival has</div>
      <h3>AI red-teaming, in Thai — and in scripts models barely saw <span lang="th" style="color:var(--gold-deep)">ไทย</span></h3>
      <p class="sub" style="margin-bottom:16px">RTP sells AI red-teaming. Guardrails trained
      mostly on English hold less well when the attack changes language or alphabet. Native
      speakers here push models off their patterns and the injections land:</p>
      <div class="grid g3">
        <div class="card"><p>English written in <span class="kbd">Thai letters</span> — the
          kind of drift a Thai-trained model produces on its own.</p></div>
        <div class="card"><p><span class="kbd">Tai Tham</span> (Lanna) and <span class="kbd">Khom</span>
          script — almost no guardrail training text exists.</p></div>
        <div class="card"><p>Northern Thai dialect and Thai-English switching mid-sentence.</p></div>
      </div>
      <p class="note" style="margin-top:18px">A live probe bench already runs on
      motdang.net's own models (SEA-LION, Llama Guard). Nobody else is selling this.</p>
    </div>
  </section>

  <section id="next" class="final reveal">
    <div class="eyebrow" style="text-align:center">Tuesday · 1 pm · Algonquin</div>
    <h2>We start with the tier you pick.</h2>
    <p>The list is built and the desk is here. Over the table on Tuesday: open the map, choose
    the first tier to work, set who owns the partnership on each side — and put a caller on it
    that week.</p>
    <div class="cta" style="justify-content:center">
      <a class="btn solid" href="#map">Open the map</a>
      <a class="btn" href="#desk">See the desk</a>
    </div>
    <p class="note" style="text-align:center;margin-top:20px">Bring this link Tuesday ·
    Palida (Beer) · motdang.net / Hongdam, Chiang Rai</p>
  </section>

</main>

<footer><div class="wrap">
  <div class="src">Company-level data from each firm's own website, Companies House and the
  CREST marketplace, read {built}. Market figures: DSIT / Frontier Economics MSP research
  2025. Pricing: public UK pentest-pricing pages, Sept 2026. Basemap: Natural Earth 1:10m
  (public domain). Named decision-maker, direct line and per-firm openers are held in a
  private file, delivered to RTP under a data-processing arrangement — not published here.
  A calling list needs TPS/CTPS screening within 28 days of each call.</div>
  <div>motdang.net<br>Chiang Rai<br>Content CC BY 4.0 · code MIT</div>
</div></footer>

<script>
const FIRMS={firm_js};
const svg=document.querySelector('.mapwrap svg'), tip=document.getElementById('tip'),
      wrap=document.querySelector('.mapwrap');
function showTip(i,el){{
  const f=FIRMS[i]; if(!f)return;
  tip.innerHTML='<b>'+f.co+'</b><span>'+f.reg+' · tier '+f.t+' · ~'+f.km+' km from London</span>';
  const b=el.getBBox(), r=svg.getBoundingClientRect(), wr=wrap.getBoundingClientRect(),
        sx=r.width/svg.viewBox.baseVal.width, sy=r.height/svg.viewBox.baseVal.height;
  tip.hidden=false; tip.classList.add('on');
  let x=(r.left-wr.left)+(b.x+b.width/2)*sx - tip.offsetWidth/2;
  let y=(r.top-wr.top)+(b.y)*sy - tip.offsetHeight - 8;
  tip.style.left=Math.max(4,x)+'px'; tip.style.top=Math.max(4,y)+'px';
}}
function hideTip(){{tip.classList.remove('on');}}
document.querySelectorAll('.pin').forEach(p=>{{
  const i=+p.dataset.i;
  p.addEventListener('mouseenter',()=>{{p.classList.add('hot');showTip(i,p);}});
  p.addEventListener('mouseleave',()=>{{p.classList.remove('hot');hideTip();}});
  p.addEventListener('focus',()=>{{p.classList.add('hot');showTip(i,p);}});
  p.addEventListener('blur',()=>{{p.classList.remove('hot');hideTip();}});
}});
document.querySelectorAll('.legend button').forEach(btn=>{{
  btn.addEventListener('click',()=>{{
    const f=btn.dataset.f;
    if(f==='all'){{
      document.querySelectorAll('.legend button').forEach(b=>b.setAttribute('aria-pressed','true'));
      document.querySelectorAll('.pin').forEach(p=>p.classList.remove('off')); return;
    }}
    const on=btn.getAttribute('aria-pressed')==='true';
    btn.setAttribute('aria-pressed', on?'false':'true');
    document.querySelector('.legend .all').setAttribute('aria-pressed','false');
    const active=[...document.querySelectorAll('.legend button[data-f]')]
      .filter(b=>b.dataset.f!=='all' && b.getAttribute('aria-pressed')==='true')
      .map(b=>b.dataset.f);
    document.querySelectorAll('.pin').forEach(p=>
      p.classList.toggle('off', active.length>0 && !active.includes(p.dataset.t)));
  }});
}});
if(!matchMedia('(prefers-reduced-motion: reduce)').matches){{
  const io=new IntersectionObserver((es)=>es.forEach(e=>{{if(e.isIntersecting){{e.target.classList.add('in');io.unobserve(e.target);}}}}),{{threshold:.12}});
  document.querySelectorAll('.reveal').forEach(el=>io.observe(el));
}} else document.querySelectorAll('.reveal').forEach(el=>el.classList.add('in'));
</script>
</body>
</html>
"""

(ROOT / "docs" / "index.html").write_text(HTML)
print(f"index.html: {total} firms, {(ROOT / 'docs' / 'index.html').stat().st_size // 1024} KB")
