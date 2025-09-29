#!/usr/bin/env python3
# nort-report: zero-js drudge-style SSG with archives + RSS
import datetime as dt
import hashlib, os, pathlib, sys, urllib.parse
from typing import List, Dict, Any
try:
    import yaml
except ImportError:
    print("pip install pyyaml", file=sys.stderr); sys.exit(1)

ROOT   = pathlib.Path(__file__).parent.resolve()
PUBLIC = ROOT / "public"
INFILE = ROOT / "links.yml"

LANES = [("top","TOP"), ("geo","GEOPOLITICS"), ("mkts","MARKETS + TECH")]

CSS = """
:root{--bg:#0b0b0b;--fg:#e7e7e7;--muted:#9a9a9a;--link:#f1f1f1;}
*{box-sizing:border-box} html{font-family:system-ui,-apple-system,Segoe UI,Roboto,Inter,sans-serif}
body{margin:0;background:var(--bg);color:var(--fg);font-size:24px;line-height:1.5}
.wrap{max-width:1200px;margin:0 auto;padding:24px}
.head{text-align:center;margin:8px 0 20px} .h1{letter-spacing:2px;font-weight:800;font-size:36px}
.h1 a{color:var(--fg);text-decoration:none;font-size:36px}
.cols{display:grid;grid-template-columns:1.2fr 1fr 1fr;gap:28px}
@media(max-width:980px){.cols{grid-template-columns:1fr}}
.lane h2{font-size:14px;font-weight:700;color:var(--muted);margin:8px 0 12px;text-transform:uppercase;letter-spacing:.8px}
ul{list-style:none;margin:0;padding:0} li{margin:12px 0}
a{color:var(--link);text-decoration:none;font-size:16px} a:hover{text-decoration:underline}
.toplane li:nth-child(-n+3) a{font-weight:800;text-transform:uppercase;font-size:18px}
.hr{border-top:1px solid #222;margin:20px 0}
.story-separator{border:none;border-top:1px solid #333;margin:16px 0;opacity:0.6}
.footer{margin-top:20px;text-align:center;color:var(--muted);font-size:14px}
"""

HTML = """<!doctype html>
<html lang="en">
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><meta name="robots" content="index,follow">
<style>{css}</style>
<body><div class="wrap">
<header class="head">
  <div class="h1"><a href="/">{title}</a></div>
</header>
<div class="cols">{cols}</div>
<div class="footer hr"></div>
<div class="footer">© {year} nort report • one page, no js</div>
</div></body></html>"""

ARCHIVE_HTML = """<!doctype html>
<html lang="en">
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — Archive {date}</title><meta name="robots" content="index,follow">
<style>{css}</style>
<body><div class="wrap">
<header class="head">
  <div class="h1"><a href="/">{title} — archive {date}</a></div>
  <div class="sub">snapshot generated {generated}</div>
</header>
<div class="cols">{cols}</div>
<div class="footer hr"></div>
<div class="footer"><a href="/">back to front page</a></div>
</div></body></html>"""

RSS_TPL = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>{title}</title>
<link>{site_url}</link>
<description>{title} — latest curation</description>
<lastBuildDate>{last_build}</lastBuildDate>
{items}
</channel>
</rss>"""

def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)

def iso_parse(s: str) -> dt.datetime:
    # allow 'Z' or offsetless; assume local if naive
    if not s: return now_utc()
    try:
        if s.endswith("Z"): s = s.replace("Z","+00:00")
        d = dt.datetime.fromisoformat(s)
        return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)
    except Exception:
        return now_utc()

def human(dtobj: dt.datetime) -> str:
    return dtobj.astimezone().strftime("%a %b %d, %Y — %I:%M %p %Z")

def safe(a: str) -> str:
    return (a or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def sha_text(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def write_if_changed(path: pathlib.Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes()==data: return
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data); tmp.replace(path)

def normalize_links(links: List[Dict[str,Any]]) -> List[Dict[str,Any]]:
    out = []
    for it in links:
        t = it.get("title","").strip()
        u = it.get("url","").strip()
        if not t or not u: continue
        lane = it.get("lane","top")
        prio = int(it.get("priority",0))
        src  = (it.get("source","") or "").strip()
        added_at = iso_parse(it.get("added_at") or now_utc().isoformat())
        # stable id: explicit or hash of url+title
        sid = it.get("id")
        if not sid:
            sid = hashlib.sha1(f"{u}|{t}".encode("utf-8")).hexdigest()[:8]
        out.append({"id":sid,"title":t,"url":u,"lane":lane,"priority":prio,"source":src,"added_at":added_at})
    return out

def render_lane(key:str,label:str,items:List[Dict[str,Any]])->str:
    cls = "lane" + (" toplane" if key=="top" else "")
    s = [f'<div class="{cls}"><h2>{label}</h2><ul>']
    for i, it in enumerate(items):
        s.append(
            f'<li><a href="{safe(it["url"])}" rel="noopener" target="_blank">{safe(it["title"])}</a></li>'
        )
        # Add <hr> between items, but not after the last one
        if i < len(items) - 1:
            s.append('<hr class="story-separator">')
    s.append("</ul></div>")
    return "\n".join(s)

def build_front(site:Dict[str,Any], links:List[Dict[str,Any]]):
    # lanes
    lanes = {k:[] for k,_ in LANES}
    for it in links:
        if it["lane"] in lanes: lanes[it["lane"]].append(it)
    for k in lanes: lanes[k].sort(key=lambda x:(-x["priority"], x["title"]))
    cols = "\n".join(render_lane(k, lbl, lanes[k]) for k,lbl in LANES)
    html = HTML.format(title=safe(site.get("title","NORT REPORT")),
                       year=dt.datetime.now().year,
                       cols=cols, css=CSS)
    write_if_changed(PUBLIC/"index.html", html.encode("utf-8"))
    return cols

def build_archive(site:Dict[str,Any], cols_html:str, when:dt.datetime):
    d = when.astimezone().date().isoformat()
    html = ARCHIVE_HTML.format(
        title=safe(site.get("title","NORT REPORT")),
        date=d, generated=human(now_utc()),
        cols=cols_html, css=CSS
    )
    path = PUBLIC / "archive" / f"{d}.html"
    write_if_changed(path, html.encode("utf-8"))

def build_rss(site:Dict[str,Any], links:List[Dict[str,Any]], site_url:str):
    # top N across all lanes by priority then recency
    N = int(site.get("rss_count", 30))
    items = sorted(links, key=lambda x:(-x["priority"], x["added_at"]), reverse=False)
    items = sorted(links, key=lambda x:(-x["priority"], x["added_at"]), reverse=False)  # keep stable
    items = sorted(links, key=lambda x:(-x["priority"], x["added_at"]), reverse=True)[:N]
    rss_items=[]
    for it in items:
        pub = it["added_at"].astimezone(dt.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
        t = safe(it["title"])
        u = safe(it["url"])
        rss_items.append(f"<item><title>{t}</title><link>{u}</link><guid isPermaLink='false'>{it['id']}</guid><pubDate>{pub}</pubDate></item>")
    rss = RSS_TPL.format(
        title=safe(site.get("title","NORT REPORT")),
        site_url=site_url.rstrip("/"),
        last_build=now_utc().strftime("%a, %d %b %Y %H:%M:%S GMT"),
        items="\n".join(rss_items)
    )
    write_if_changed(PUBLIC/"rss.xml", rss.encode("utf-8"))

def main():
    PUBLIC.mkdir(parents=True, exist_ok=True)
    data = yaml.safe_load(INFILE.read_text(encoding="utf-8"))
    site  = data.get("site", {})
    links = normalize_links(data.get("links", []))
    cols_html = build_front(site, links)
    # archive today's snapshot
    build_archive(site, cols_html, now_utc())
    # rss
    site_url = site.get("site_url","https://example.com")
    build_rss(site, links, site_url)
    # sitemap + robots
    today = now_utc().date().isoformat()
    base = site_url.rstrip("/")
    sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>{base}/</loc></url>
<url><loc>{base}/archive/{today}.html</loc></url>
<url><loc>{base}/rss.xml</loc></url>
</urlset>"""
    write_if_changed(PUBLIC/"sitemap.xml", sitemap.encode("utf-8"))
    write_if_changed(PUBLIC/"robots.txt", b"User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n")

if __name__ == "__main__":
    main()
