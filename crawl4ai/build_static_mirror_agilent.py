import asyncio, os, re, json, hashlib, urllib.parse
from pathlib import Path
from collections import deque
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# ===== SETTINGS =====
START_URL   = "https://www.agilent.com/"
DOMAIN      = "agilent.com"                 # treat any *.agilent.com as internal
OUTPUT_ROOT = Path("output/agilent_render") # where we save pages + assets
MAX_PAGES   = 40                            # bump as needed
REQUEST_GAP = 0.25                          # polite delay between page visits
HEADLESS    = True
USER_AGENT  = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36"
VIEWPORT    = {"width": 1366, "height": 900}
TIMEOUT_MS  = 60000
MAX_WINDOWS_PATH = 250 if os.name == "nt" else 4096
ALLOWED_PATH_PREFIXES = ("/en", "/cs", "/content", "/search", "/store", "/sites")  # keeps BFS sane

# ===== Helpers =====
_invalid = re.compile(r"[^a-z0-9._-]+", re.I)

ASSET_CT_PREFIX = (
    "text/css", "application/javascript", "text/javascript", "application/x-javascript",
    "image/", "font/", "audio/", "video/", "application/font-woff", "application/font-woff2",
    "application/pdf", "application/json", "text/xml", "application/xml"
)

ASSET_EXT = {
    ".css",".js",".mjs",".map",
    ".png",".jpg",".jpeg",".gif",".webp",".svg",".ico",
    ".woff",".woff2",".ttf",".otf",".eot",
    ".mp4",".webm",".mp3",".wav",
    ".pdf",".json",".xml"
}

def canon_url(u: str) -> str:
    p = urllib.parse.urlsplit(u)
    q = urllib.parse.parse_qsl(p.query, keep_blank_values=True)
    drop = {"utm_source","utm_medium","utm_campaign","utm_term","utm_content","gclid","fbclid","_ga","_gl","ver"}
    q = [(k,v) for (k,v) in q if k.lower() not in drop]
    path = re.sub(r"/{2,}", "/", p.path)
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    return urllib.parse.urlunsplit((p.scheme.lower(), p.netloc.lower(), path, urllib.parse.urlencode(q, doseq=True), ""))

def is_same_site(u: str) -> bool:
    try:
        return urllib.parse.urlsplit(u).netloc.lower().endswith(DOMAIN)
    except Exception:
        return False

def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8","ignore")).hexdigest()

def _san_seg(s: str, limit=80) -> str:
    return (_invalid.sub("-", s).strip("-") or "_")[:limit]

def _ext_of(u: str) -> str:
    return Path(urllib.parse.urlsplit(u).path).suffix.lower()

def page_dir_for(u: str) -> Path:
    p = urllib.parse.urlsplit(u)
    host = p.netloc.lower()
    segs = [s for s in p.path.split("/") if s]
    segs = [_san_seg(s) for s in segs]
    if p.query:
        segs.append("_q_" + _san_seg(p.query, 120))
    d = OUTPUT_ROOT / host
    for s in segs:
        d = d / s
    return d

def asset_local_path(asset_url: str, force_ext: str | None = None) -> Path:
    p = urllib.parse.urlsplit(asset_url)
    host = p.netloc.lower()
    segs = [s for s in p.path.split("/") if s]
    segs = [_san_seg(s, 70) for s in segs]
    if not segs:
        segs = ["index"]
    filename = segs[-1]
    ext = Path(filename).suffix.lower()
    if not ext and force_ext:
        filename += force_ext
    # include query in filename to avoid collisions
    if p.query:
        qsan = _san_seg(p.query, 60)
        if "." in filename:
            stem, ext2 = filename.rsplit(".", 1)
            filename = f"{stem}__q_{qsan}.{ext2}"
        else:
            filename = f"{filename}__q_{qsan}"
    base = OUTPUT_ROOT / host
    for s in segs[:-1]:
        base = base / s
    target = base / filename
    if len(str(target)) >= MAX_WINDOWS_PATH and os.name == "nt":
        hashed = _sha1(asset_url)
        ext = force_ext or _ext_of(asset_url)
        target = OUTPUT_ROOT / host / "_assets" / (hashed + (ext or ""))
    target.parent.mkdir(parents=True, exist_ok=True)
    return target

def make_rel(from_dir: Path, tgt: Path) -> str:
    try:
        return os.path.relpath(tgt, start=from_dir)
    except ValueError:
        return tgt.name

def url_abs(base: str, href: str | None) -> str | None:
    if not href: return None
    if href.startswith(("mailto:", "tel:", "javascript:", "#")):
        return None
    return canon_url(urllib.parse.urljoin(base, href))

def candidate_asset_keys(u: str) -> list[str]:
    s = urllib.parse.urlsplit(u)
    no_query = urllib.parse.urlunsplit((s.scheme, s.netloc, s.path, "", ""))
    drop_ver = canon_url(u)
    return [canon_url(u), canon_url(no_query), drop_ver]

# ===== Core mirror =====

async def render_and_capture(playwright):
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    browser = await playwright.chromium.launch(
        headless=HEADLESS,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-web-security",
            "--no-sandbox",
        ]
    )

    context = await browser.new_context(
        user_agent=USER_AGENT,
        viewport=VIEWPORT,
        java_script_enabled=True,
        bypass_csp=True,                 # helpful when rewriting/reading
        locale="en-US",
    )

    # Global asset map across pages
    asset_map: dict[str, Path] = {}
    seen_pages: set[str] = set()

    q = deque([START_URL])

    async def save_response(resp):
        try:
            url = canon_url(resp.url)
            # Only keep assets (by resource type or content-type)
            rtype = resp.request.resource_type
            ctype = (resp.headers or {}).get("content-type","").lower()
            is_asset_type = (
                rtype in ("stylesheet","script","image","media","font") or
                any(ctype.startswith(p) for p in ASSET_CT_PREFIX) or
                _ext_of(url) in ASSET_EXT
            )
            if not is_asset_type:
                return

            # Figure out extension if missing and forced CSS/script/image by type
            force_ext = None
            if rtype == "stylesheet" and _ext_of(url) == "":
                force_ext = ".css"
            elif rtype == "script" and _ext_of(url) == "":
                force_ext = ".js"

            if any(k in asset_map for k in candidate_asset_keys(url)):
                return  # already saved

            body = await resp.body()
            if not body:
                return
            path = asset_local_path(url, force_ext=force_ext)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "wb") as f:
                f.write(body)

            for k in candidate_asset_keys(url):
                asset_map[k] = path
        except Exception:
            pass

    # Seed cookies (consent, etc.) by visiting root once
    seed = await context.new_page()
    seed.on("response", save_response)
    await seed.goto(START_URL, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
    await seed.wait_for_timeout(600)
    await seed.close()

    pages_done = 0
    while q and pages_done < MAX_PAGES:
        url = canon_url(q.popleft())
        if not is_same_site(url): 
            continue
        if not urllib.parse.urlsplit(url).path.startswith(ALLOWED_PATH_PREFIXES):
            # keep crawl bounded; relax if you want the whole site
            pass
        if url in seen_pages:
            continue
        seen_pages.add(url)

        page = await context.new_page()
        page.on("response", save_response)

        try:
            await page.goto(url, wait_until="networkidle", timeout=TIMEOUT_MS)
        except Exception:
            try:
                await page.wait_for_load_state("domcontentloaded", timeout=10000)
            except Exception:
                pass

        # Trigger lazy assets
        try:
            await auto_scroll(page)
            await page.wait_for_timeout(800)
        except Exception:
            pass

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        # Collect new links for BFS
        for a in soup.find_all("a", href=True):
            u = url_abs(url, a["href"])
            if u and is_same_site(u) and u not in seen_pages:
                q.append(u)

        # Write raw + rewritten
        pdir = page_dir_for(url)
        pdir.mkdir(parents=True, exist_ok=True)
        (pdir / "raw.html").write_text(html, encoding="utf-8")
        (pdir / "meta.json").write_text(json.dumps({"url": url}, indent=2), encoding="utf-8")

        rewrite_html(url, pdir, soup, asset_map)
        (pdir / "index.html").write_text(str(soup), encoding="utf-8")

        await page.close()
        pages_done += 1
        print(f"✓ {pages_done:03}/{MAX_PAGES} {url}")
        await asyncio.sleep(REQUEST_GAP)

    await context.close()
    await browser.close()

def resolve_asset(asset_map: dict[str, Path], u: str) -> Path | None:
    for k in candidate_asset_keys(u):
        p = asset_map.get(k)
        if p is not None:
            return p
    return None

def rewrite_html(page_url: str, page_dir: Path, soup: BeautifulSoup, asset_map: dict[str, Path]) -> None:
    # 1) links: prefer local assets; fall back to absolute URL; convert in-domain pages to local index.html when seen later
    for a in soup.find_all("a", href=True):
        absu = url_abs(page_url, a["href"])
        if not absu:
            continue
        tgt = resolve_asset(asset_map, absu)
        if tgt is not None:
            a["href"] = make_rel(page_dir, tgt)
        elif is_same_site(absu):
            # point at expected local location; if page not crawled yet, live URL will still work
            loc = page_dir_for(absu) / "index.html"
            a["href"] = make_rel(page_dir, loc)

    # 2) Stylesheets/icons/preloads → rewrite + normalize preload-as-style
    for link in soup.find_all("link", href=True):
        absu = url_abs(page_url, link["href"])
        if not absu:
            continue
        tgt = resolve_asset(asset_map, absu)
        if tgt is not None:
            link["href"] = make_rel(page_dir, tgt)
        else:
            link["href"] = absu  # fall back to live

        rels = [r.lower() for r in (link.get("rel") or [])]
        as_attr = (link.get("as") or "").lower()
        if ("preload" in rels and as_attr == "style") or ("stylesheet" in rels):
            link["rel"] = ["stylesheet"]
            link.attrs.pop("as", None)
            if link.get("media","").lower() == "print":
                link["media"] = "all"
            link.attrs.pop("onload", None)
            link["type"] = "text/css"
        for attr in ("integrity","crossorigin","referrerpolicy"):
            link.attrs.pop(attr, None)

    # 3) Scripts
    for s in soup.find_all("script", src=True):
        absu = url_abs(page_url, s["src"])
        if not absu: 
            continue
        tgt = resolve_asset(asset_map, absu)
        if tgt is not None:
            s["src"] = make_rel(page_dir, tgt)
        else:
            s["src"] = absu
        for attr in ("integrity","crossorigin","referrerpolicy"):
            s.attrs.pop(attr, None)

    # 4) Images / media
    for tag in soup.find_all(["img","source","video","audio"], src=True):
        absu = url_abs(page_url, tag["src"])
        if not absu:
            continue
        tgt = resolve_asset(asset_map, absu)
        tag["src"] = make_rel(page_dir, tgt) if tgt is not None else absu

    # 5) srcset
    def parse_srcset(val: str):
        out=[]
        for part in [p.strip() for p in val.split(",") if p.strip()]:
            pieces = part.split()
            if len(pieces)==1: out.append((pieces[0], ""))
            else: out.append((" ".join(pieces[:-1]), pieces[-1]))
        return out
    def rebuild_srcset(items):
        return ", ".join([f"{u} {d}".strip() for u,d in items])

    for tag in soup.find_all(["img","source"]):
        ss = tag.get("srcset")
        if not ss: continue
        items = parse_srcset(ss)
        new=[]
        for u,desc in items:
            absu = url_abs(page_url, u)
            if absu:
                tgt = resolve_asset(asset_map, absu)
                new.append((make_rel(page_dir, tgt) if tgt is not None else absu, desc))
            else:
                new.append((u, desc))
        tag["srcset"] = rebuild_srcset(new)

    # 6) Inline style url(...)
    def repl(m):
        raw = m.group(1).strip('\'"')
        absu = url_abs(page_url, raw)
        if absu:
            tgt = resolve_asset(asset_map, absu)
            return f"url({make_rel(page_dir, tgt)})" if tgt is not None else f"url({absu})"
        return f"url({raw})"
    for el in soup.find_all(style=True):
        style = el.get("style") or ""
        el["style"] = re.sub(r"url\(([^)]+)\)", repl, style)

async def auto_scroll(page):
    await page.evaluate("""
        async () => {
          await new Promise((resolve) => {
            let total = 0;
            const step = 600;
            const timer = setInterval(() => {
              const { scrollHeight } = document.documentElement;
              window.scrollBy(0, step);
              total += step;
              if (total >= scrollHeight) { clearInterval(timer); resolve(); }
            }, 120);
          });
        }
    """)

# ===== Entry =====
async def main():
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        await render_and_capture(p)
    print(f"\nDone. Serve:\n  cd {OUTPUT_ROOT}\n  python -m http.server 8000\nThen open:  http://localhost:8000/www.agilent.com/")

if __name__ == "__main__":
    asyncio.run(main())
