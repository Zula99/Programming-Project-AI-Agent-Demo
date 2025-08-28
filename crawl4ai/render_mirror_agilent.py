# render_mirror_agilent_persistent_fixed.py
import asyncio, os, re, json, hashlib, urllib.parse
from pathlib import Path
from collections import deque
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# --- stealth shim (works even if playwright-stealth isn't installed) ---
try:
    from playwright_stealth import stealth_async as apply_stealth  # optional
except Exception:
    async def apply_stealth(page):
        await page.add_init_script("""
            // Look less like automation
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US','en'] });
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
              parameters.name === 'notifications'
                ? Promise.resolve({ state: Notification.permission })
                : originalQuery(parameters)
            );
        """)

# ===== SETTINGS =====
START_URL   = "https://www.agilent.com/"
DOMAIN      = "agilent.com"
OUTPUT_ROOT = Path("output/agilent_render")
MAX_PAGES   = 40
REQUEST_GAP = 0.25
USER_DATA_DIR = Path(".agilent_chrome_profile").absolute()  # persistent Chrome profile
HEADLESS = False  # keep visible for first run to accept cookies
VIEWPORT = {"width": 1366, "height": 900}
TIMEOUT_MS = 60000
ALLOWED_PATH_PREFIXES = ("/en", "/cs", "/content", "/search", "/store", "/sites")
MAX_WINDOWS_PATH = 250 if os.name == "nt" else 4096

_invalid = re.compile(r"[^a-z0-9._-]+", re.I)
ASSET_CT_PREFIX = (
    "text/css","application/javascript","text/javascript","application/x-javascript",
    "image/","font/","audio/","video/","application/font-woff","application/font-woff2",
    "application/pdf","application/json","text/xml","application/xml"
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
    if path != "/" and path.endswith("/"): path = path[:-1]
    return urllib.parse.urlunsplit((p.scheme.lower(), p.netloc.lower(), path, urllib.parse.urlencode(q, doseq=True), ""))

def is_same_site(u: str) -> bool:
    try: return urllib.parse.urlsplit(u).netloc.lower().endswith(DOMAIN)
    except Exception: return False

def _sha1(s: str) -> str: return hashlib.sha1(s.encode("utf-8","ignore")).hexdigest()
def _san_seg(s: str, limit=80) -> str: return (_invalid.sub("-", s).strip("-") or "_")[:limit]
def _ext_of(u: str) -> str: return Path(urllib.parse.urlsplit(u).path).suffix.lower()

def page_dir_for(u: str) -> Path:
    p = urllib.parse.urlsplit(u)
    host = p.netloc.lower()
    segs = [_san_seg(s) for s in p.path.split("/") if s]
    if p.query: segs.append("_q_" + _san_seg(p.query, 120))
    d = OUTPUT_ROOT / host
    for s in segs: d = d / s
    return d

def asset_local_path(asset_url: str, force_ext: str | None = None) -> Path:
    p = urllib.parse.urlsplit(asset_url)
    host = p.netloc.lower()
    segs = [_san_seg(s, 70) for s in p.path.split("/") if s] or ["index"]
    filename = segs[-1]
    if not Path(filename).suffix.lower() and force_ext:
        filename += force_ext
    if p.query:
        qsan = _san_seg(p.query, 60)
        if "." in filename:
            stem, ext2 = filename.rsplit(".", 1)
            filename = f"{stem}__q_{qsan}.{ext2}"
        else:
            filename = f"{filename}__q_{qsan}"
    base = OUTPUT_ROOT / host
    for s in segs[:-1]: base = base / s
    target = base / filename
    if len(str(target)) >= MAX_WINDOWS_PATH and os.name == "nt":
        hashed = _sha1(asset_url)
        ext = force_ext or _ext_of(asset_url)
        target = OUTPUT_ROOT / host / "_assets" / (hashed + (ext or ""))
    target.parent.mkdir(parents=True, exist_ok=True)
    return target

def make_rel(from_dir: Path, tgt: Path) -> str:
    try: return os.path.relpath(tgt, start=from_dir)
    except ValueError: return tgt.name

def url_abs(base: str, href: str | None) -> str | None:
    if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")): return None
    return canon_url(urllib.parse.urljoin(base, href))

def candidate_asset_keys(u: str) -> list[str]:
    s = urllib.parse.urlsplit(u)
    no_query = urllib.parse.urlunsplit((s.scheme, s.netloc, s.path, "", ""))
    drop_ver = canon_url(u)
    return [canon_url(u), canon_url(no_query), drop_ver]

def resolve_asset(asset_map: dict[str, Path], u: str) -> Path | None:
    for k in candidate_asset_keys(u):
        p = asset_map.get(k)
        if p is not None: return p
    return None

def parse_srcset(val: str):
    out=[]
    for part in [p.strip() for p in val.split(",") if p.strip()]:
        pieces = part.split()
        out.append(((" ".join(pieces[:-1]) if len(pieces)>1 else pieces[0]),
                    (pieces[-1] if len(pieces)>1 else "")))
    return out

def rebuild_srcset(items): return ", ".join([f"{u} {d}".strip() for u,d in items])

def rewrite_html(page_url: str, page_dir: Path, soup: BeautifulSoup, asset_map: dict[str, Path]) -> None:
    # anchors → local asset/index or fall back to absolute
    for a in soup.find_all("a", href=True):
        absu = url_abs(page_url, a["href"])
        if not absu: continue
        tgt = resolve_asset(asset_map, absu)
        if tgt is not None:
            a["href"] = make_rel(page_dir, tgt)
        elif is_same_site(absu):
            a["href"] = make_rel(page_dir, page_dir_for(absu) / "index.html")
        else:
            a["href"] = absu

    # stylesheets/preloads
    for link in soup.find_all("link", href=True):
        absu = url_abs(page_url, link["href"])
        if not absu: continue
        tgt = resolve_asset(asset_map, absu)
        link["href"] = make_rel(page_dir, tgt) if tgt is not None else absu
        rels = [r.lower() for r in (link.get("rel") or [])]
        as_attr = (link.get("as") or "").lower()
        if ("preload" in rels and as_attr == "style") or ("stylesheet" in rels):
            link["rel"] = ["stylesheet"]
            link.attrs.pop("as", None)
            if link.get("media","").lower() == "print": link["media"] = "all"
            link.attrs.pop("onload", None)
            link["type"] = "text/css"
        for attr in ("integrity","crossorigin","referrerpolicy"):
            link.attrs.pop(attr, None)

    # scripts
    for s in soup.find_all("script", src=True):
        absu = url_abs(page_url, s["src"])
        if not absu: continue
        tgt = resolve_asset(asset_map, absu)
        s["src"] = make_rel(page_dir, tgt) if tgt is not None else absu
        for attr in ("integrity","crossorigin","referrerpolicy"):
            s.attrs.pop(attr, None)

    # images/media
    for tag in soup.find_all(["img","source","video","audio"], src=True):
        absu = url_abs(page_url, tag["src"])
        if absu:
            tgt = resolve_asset(asset_map, absu)
            tag["src"] = make_rel(page_dir, tgt) if tgt is not None else absu

    # srcset
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

    # inline url(...)
    def repl(m):
        raw = m.group(1).strip('\'"')
        absu = url_abs(page_url, raw)
        if absu:
            tgt = resolve_asset(asset_map, absu)
            return f"url({make_rel(page_dir, tgt)})" if tgt is not None else f"url({absu})"
        return f"url({raw})"
    for el in soup.find_all(style=True):
        el["style"] = re.sub(r"url\(([^)]+)\)", repl, el.get("style") or "")

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

async def render_and_capture(playwright):
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Launch your real Chrome with a persistent profile
    #context = await playwright.chromium.launch_persistent_context(
    #    user_data_dir=str(USER_DATA_DIR),
    #    channel="chrome",        # uses system Chrome
    #    headless=HEADLESS,
    #    viewport=VIEWPORT,
    #    java_script_enabled=True,
    #    bypass_csp=True,
    #    locale="en-US",
    #    color_scheme="light",
    #    extra_http_headers={
    #        "Accept-Language": "en-US,en;q=0.9",
    #        "Upgrade-Insecure-Requests": "1",
    #    },
    #    args=[
    #        "--disable-blink-features=AutomationControlled",
    #        "--no-sandbox",
    #        "--disable-features=IsolateOrigins,site-per-process",
    #    ],
    #)

    asset_map: dict[str, Path] = {}
    seen_pages: set[str] = set()
    q = deque([START_URL])

    async def launch_ctx(playwright):
        # Launch your real Chrome with the same persistent profile
        ctx = await playwright.chromium.launch_persistent_context(
            user_data_dir=str(USER_DATA_DIR),
            channel="chrome",        # use system Chrome
            headless=HEADLESS,
            viewport=VIEWPORT,
            java_script_enabled=True,
            bypass_csp=True,
            locale="en-US",
            color_scheme="light",
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Upgrade-Insecure-Requests": "1",
            },
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-gpu",                # helps stability on some Windows setups
                "--no-first-run",
                "--no-default-browser-check",
            ],
        )
        return ctx

    context = await launch_ctx(playwright)

    async def save_response(resp):
        try:
            url = canon_url(resp.url)
            rtype = resp.request.resource_type
            ctype = (resp.headers or {}).get("content-type","").lower()
            is_asset_type = (
                rtype in ("stylesheet","script","image","media","font") or
                any(ctype.startswith(p) for p in ASSET_CT_PREFIX) or
                _ext_of(url) in ASSET_EXT
            )
            if not is_asset_type: return
            force_ext = None
            if rtype == "stylesheet" and _ext_of(url) == "": force_ext = ".css"
            if rtype == "script" and _ext_of(url) == "":     force_ext = ".js"
            if any(k in asset_map for k in candidate_asset_keys(url)): return
            body = await resp.body()
            if not body: return
            path = asset_local_path(url, force_ext=force_ext)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "wb") as f: f.write(body)
            for k in candidate_asset_keys(url): asset_map[k] = path
        except Exception:
            pass

    # Warm-up: open homepage visibly, apply stealth, let you accept cookies/challenge
    warm = await context.new_page()
    await apply_stealth(warm)
    warm.on("response", save_response)
    print("\n🔓 Chrome window opened. If you see a consent or bot check, resolve it.")
    await warm.goto(START_URL, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
    await warm.wait_for_timeout(6000)
    input("When the site is visible and normal in Chrome, press ENTER here to start the crawl... ")
    await warm.close()

    pages_done = 0
    while q and pages_done < MAX_PAGES:
        url = canon_url(q.popleft())
        if not is_same_site(url): continue
        path = urllib.parse.urlsplit(url).path or "/"
        if url in seen_pages: continue
        seen_pages.add(url)

        try:
            page = await context.new_page()
        except Exception as e:
            if "has been closed" in str(e):
                print("⚠️ Chrome window was closed. Relaunching…")
                try:
                    await context.close()
                except Exception:
                    pass
                context = await launch_ctx(playwright)
        
                # quick, automatic warm-up (no prompt this time)
                warm = await context.new_page()
                await apply_stealth(warm)
                try:
                    await warm.goto(START_URL, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
                    await warm.wait_for_timeout(1500)
                except Exception:
                    pass
                await warm.close()
        
                page = await context.new_page()
            else:
                raise

        await apply_stealth(page)
        page.on("response", save_response)

        try:
            await page.goto(url, wait_until="networkidle", timeout=TIMEOUT_MS)
        except Exception:
            try: await page.wait_for_load_state("domcontentloaded", timeout=12000)
            except Exception: pass

        try:
            await auto_scroll(page)
            await page.wait_for_timeout(800)
        except Exception:
            pass

        html = await page.content()
        soup = BeautifulSoup(html, "html.parser")

        # enqueue links
        for a in soup.find_all("a", href=True):
            u = url_abs(url, a["href"])
            if u and is_same_site(u) and u not in seen_pages:
                # keep the crawl bounded to sane sections
                upath = urllib.parse.urlsplit(u).path or "/"
                if any(upath.startswith(p) for p in ALLOWED_PATH_PREFIXES):
                    q.append(u)

        # write files
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
    print(f"\nDone. Serve:\n  cd {OUTPUT_ROOT}\n  python -m http.server 8000\nThen open:  http://localhost:8000/www.agilent.com/")

async def main():
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        await render_and_capture(p)

if __name__ == "__main__":
    asyncio.run(main())
