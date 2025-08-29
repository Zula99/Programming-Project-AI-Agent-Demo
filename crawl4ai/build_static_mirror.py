# build_static_mirror.py
# Turn your Crawl4AI output into an offline-browseable mirror.
# - Parses output/nab/**/raw.html + meta.json
# - Rewrites internal links to local index.html
# - Downloads same-site assets (css/js/img/fonts)
# - Rewrites asset URLs in HTML (and optionally inside CSS)

import asyncio, aiohttp, os, re, json, hashlib, urllib.parse, urllib.robotparser
from pathlib import Path
from collections import defaultdict
from bs4 import BeautifulSoup

# === SETTINGS ===
DOMAIN                = "nab.com.au"                # treat any *.nab.com.au as internal
OUTPUT_ROOT           = Path("output/nab")          # where crawl saved pages
REQUEST_GAP_SECONDS   = 0.15                        # polite delay between asset fetches
CONCURRENCY           = 8                           # parallel asset downloads
RESPECT_ROBOTS        = True                        # honor robots for asset URLs
MIRROR_EXTERNAL_ASSETS= False                       # only nab.com.au by default
STRIP_SCRIPTS         = False                       # set True to remove <script> tags
REWRITE_CSS_URLS      = True                        # rewrite url(...) in CSS to local paths
MAX_WINDOWS_PATH      = 250 if os.name == "nt" else 4096 # Windows max path workaround
RETRIES               = 2                           # retry asset fetches this many times on failure
TIMEOUT_TOTAL         = 45                          # seconds total timeout for asset fetch
MIRROR_EXTERNAL_ASSETS = True
FORCE_MIRROR_PATH_PREFIXES = ("/etc.clientlibs/",)
OVERRIDE_ROBOTS_EXTS  = {".css", ".js", ".mjs", ".woff", ".woff2", ".ttf", ".otf"}


_invalid = re.compile(r"[^a-z0-9._-]+")

# Known binary/file types to mirror
ASSET_EXT = {
    ".css",".js",".mjs",".map",
    ".png",".jpg",".jpeg",".gif",".webp",".svg",".ico",
    ".woff",".woff2",".ttf",".otf",".eot",
    ".mp4",".webm",".mp3",".wav",
    ".pdf",".json",".xml",".txt",".csv"
}

# --- URL canon (aligns with your crawler’s approach) ---
DROP_QUERY_KEYS = {"utm_source","utm_medium","utm_campaign","utm_term","utm_content","gclid","fbclid","_ga","_gl"}

def _san(s: str, limit: int = 60) -> str:
    """Sanitize a single path segment and clamp length."""
    s = _invalid.sub("-", s.lower()).strip("-")
    return s[:limit] or "_"

def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()

def _ext_of(url: str) -> str:
    return Path(urllib.parse.urlsplit(url).path).suffix.lower()

def url_canon(url: str) -> str:
    p = urllib.parse.urlsplit(url)
    scheme = p.scheme.lower()
    netloc = p.netloc.lower()
    path   = re.sub(r"/{2,}", "/", p.path)
    # drop fragment
    frag   = ""
    # clean query
    q = [(k, v) for (k, v) in urllib.parse.parse_qsl(p.query, keep_blank_values=True) if k not in DROP_QUERY_KEYS]
    query = urllib.parse.urlencode(q, doseq=True)
    # normalise trailing slash (keep "/" only at root)
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    return urllib.parse.urlunsplit((scheme, netloc, path, query, frag))

def is_same_site(url: str) -> bool:
    try:
        host = urllib.parse.urlsplit(url).netloc.lower()
        return host.endswith(DOMAIN)
    except Exception:
        return False

_invalid = re.compile(r"[^a-z0-9._-]+")

def path_slug(url: str) -> Path:
    """Folder path where the page lives; we’ll write index.html inside it."""
    parts = urllib.parse.urlsplit(url)
    host  = parts.netloc.lower()
    path  = parts.path
    segs  = [] if not path or path == "/" else [s for s in path.split("/") if s]
    segs  = [_invalid.sub("-", s.lower()).strip("-")[:80] for s in segs]
    # encode cleaned query into subfolder (avoids overwrites)
    if parts.query:
        q = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
        q.sort()
        qstr = "&".join([f"{_invalid.sub('-', k.lower())}={_invalid.sub('-', v.lower())}" for k,v in q])[:120]
        segs.append(f"_q_{qstr}")
    d = OUTPUT_ROOT / host
    for s in segs:
        d = d / s
    return d

def asset_local_path(asset_url: str) -> Path:
    """
    Map asset URL to a local file path under OUTPUT_ROOT, with:
    - sanitized segments
    - AEM/coreimg flattening (merge .../foo.jpeg/<stamp> → foo__<stamp>.jpeg)
    - Windows-safe fallback to hashed filename when path gets too long
    """
    p = urllib.parse.urlsplit(asset_url)
    host = p.netloc.lower()
    raw_segments = [seg for seg in (p.path or "/").split("/") if seg]

    # sanitize and clamp each segment
    segs = [_san(seg) for seg in raw_segments]

    # if path "looks like" file-with-ext followed by a stamp/variant (AEM core image),
    # flatten the final two segments into a single filename to reduce depth
    if len(segs) >= 2:
        prev, last = segs[-2], segs[-1]
        prev_ext = Path(prev).suffix.lower()
        last_ext = Path(last).suffix.lower()
        if prev_ext and not last_ext and len(last) <= 32:
            # produce: "<prev_without_ext>__<last><prev_ext>"
            prev_stem = prev[: -len(prev_ext)] if prev_ext else prev
            merged = f"{prev_stem}__{last}{prev_ext}"
            segs = segs[:-2] + [merged]

    # ensure we have at least a filename
    if len(segs) == 0:
        segs = ["index"]

    # if final segment ends with "/", give it an index filename
    # (not common for assets, but harmless)
    if segs and segs[-1] == "":
        segs[-1] = "index"

    # append query to filename to avoid collisions
    base = OUTPUT_ROOT / host
    for s in segs[:-1]:
        base = base / s
    filename = segs[-1]

    if p.query:
        safe_q = _san(p.query, limit=40)
        stem = filename
        dot = filename.rfind(".")
        if dot != -1:
            stem_only = filename[:dot]
            ext = filename[dot:]
            filename = f"{stem_only}__q_{safe_q}{ext}"
        else:
            filename = f"{filename}__q_{safe_q}"

    target = (OUTPUT_ROOT / host).joinpath(*segs[:-1], filename)

    # Windows MAX_PATH guard → hashed fallback
    if len(str(target)) >= MAX_WINDOWS_PATH and os.name == "nt":
        ext = _ext_of(asset_url) or ""
        hashed = _sha1(asset_url)
        target = OUTPUT_ROOT / host / "_assets" / (hashed + ext)

    target.parent.mkdir(parents=True, exist_ok=True)
    return target

def ext_of(url: str) -> str:
    return Path(urllib.parse.urlsplit(url).path).suffix.lower()

def is_asset(url: str) -> bool:
    e = _ext_of(url)
    return e in ASSET_EXT

def make_rel(from_dir: Path, target_path: Path) -> str:
    """Relative filesystem path from one folder to a file, with forward slashes for browsers."""
    try:
        rel_path = os.path.relpath(target_path, start=from_dir)
        # Convert Windows backslashes to forward slashes for browser compatibility
        return rel_path.replace('\\', '/')
    except ValueError:
        # different drives on Windows, just return basename as fallback
        return target_path.name

# --- robots.txt
def build_robots(start_url: str) -> urllib.robotparser.RobotFileParser | None:
    if not RESPECT_ROBOTS:
        return None
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(urllib.parse.urljoin(start_url, "/robots.txt"))
    try:
        rp.read()
        return rp
    except Exception:
        return None

# --- load all crawled pages (url -> folder) ---
def collect_pages():
    url_to_dir = {}
    for meta_path in OUTPUT_ROOT.rglob("meta.json"):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        url = meta.get("url")
        if not url:
            continue
        c = url_canon(url)
        url_to_dir[c] = meta_path.parent
    return url_to_dir

# --- parse srcset like: "img1.jpg 1x, img2.jpg 2x"
def parse_srcset(val: str) -> list[tuple[str,str]]:
    out = []
    for part in [p.strip() for p in val.split(",") if p.strip()]:
        pieces = part.split()
        if len(pieces) == 1:
            out.append((pieces[0], ""))       # just URL
        else:
            out.append((" ".join(pieces[:-1]), pieces[-1]))  # URL, descriptor
    return out

def rebuild_srcset(items: list[tuple[str,str]]) -> str:
    rebuilt = []
    for url, desc in items:
        rebuilt.append(f"{url} {desc}".strip())
    return ", ".join(rebuilt)

# --- extract & rewrite helpers ---
def absolutize(base_url: str, href: str | None) -> str | None:
    if not href:
        return None
    if href.startswith(("mailto:", "tel:", "javascript:", "#")):
        return None
    return url_canon(urllib.parse.urljoin(base_url, href))

def rewrite_html(page_url: str, page_dir: Path, soup: BeautifulSoup,
                 page_map: dict[str, Path], asset_map: dict[str, Path]) -> None:
    # 1) Anchor links to other mirrored pages → local index.html
    for a in soup.find_all("a", href=True):
        absu = absolutize(page_url, a["href"])
        if not absu:
            continue
        if is_same_site(absu) and absu in page_map:
            a["href"] = make_rel(page_dir, page_map[absu] / "index.html")

    # 2) Stylesheets / icons / preloads → ALWAYS rewrite if we downloaded them
    for link in soup.find_all("link", href=True):
        absu = absolutize(page_url, link["href"])
        if not absu:
            continue
        if absu in asset_map:
            link["href"] = make_rel(page_dir, asset_map[absu])
            # local file: SRI/CORS no longer valid
            for attr in ("integrity", "crossorigin", "referrerpolicy"):
                if attr in link.attrs:
                    del link[attr]

    # 3) Scripts → rewrite if downloaded, strip SRI/CORS
    for s in soup.find_all("script", src=True):
        absu = absolutize(page_url, s["src"])
        if not absu:
            continue
        if absu in asset_map:
            s["src"] = make_rel(page_dir, asset_map[absu])
            for attr in ("integrity", "crossorigin", "referrerpolicy"):
                if attr in s.attrs:
                    del s[attr]

    # 4) Images / media
    for tag in soup.find_all(["img","source","video","audio"], src=True):
        absu = absolutize(page_url, tag["src"])
        if absu and absu in asset_map:
            tag["src"] = make_rel(page_dir, asset_map[absu])

    # 5) srcset (img/source)
    for tag in soup.find_all(["img","source"]):
        ss = tag.get("srcset")
        if not ss:
            continue
        items = parse_srcset(ss)
        new_items = []
        for u, desc in items:
            absu = absolutize(page_url, u)
            if absu and absu in asset_map:
                new_items.append((make_rel(page_dir, asset_map[absu]), desc))
            else:
                new_items.append((u, desc))
        tag["srcset"] = rebuild_srcset(new_items)

    # 6) Inline styles: url(...)
    for el in soup.find_all(style=True):
        style = el.get("style") or ""
        def repl(m):
            raw = m.group(1).strip('\'"')
            absu = absolutize(page_url, raw)
            if absu and absu in asset_map:
                return f"url({make_rel(page_dir, asset_map[absu])})"
            return f"url({raw})"
        el["style"] = re.sub(r"url\(([^)]+)\)", repl, style)

# --- CSS url(...) rewriting ---
def rewrite_css_urls(css_text: str, css_url: str, css_path: Path, asset_map: dict[str, Path]) -> str:
    base = css_url

    # Rewrite url(...)
    def repl_url(m):
        raw = m.group(1).strip('\'"')
        if raw.startswith(("data:", "about:", "mailto:")):
            return f"url({raw})"
        absu = url_canon(urllib.parse.urljoin(base, raw))
        if (MIRROR_EXTERNAL_ASSETS or is_same_site(absu)) and absu in asset_map:
            return f"url({make_rel(css_path.parent, asset_map[absu])})"
        return f"url({raw})"

    out = re.sub(r"url\(([^)]+)\)", repl_url, css_text)

    # Rewrite @import url(...) and @import "..."
    def repl_import(m):
        raw = m.group(1).strip('\'"')
        absu = url_canon(urllib.parse.urljoin(base, raw))
        if (MIRROR_EXTERNAL_ASSETS or is_same_site(absu)) and absu in asset_map:
            return f'@import url({make_rel(css_path.parent, asset_map[absu])})'
        return f'@import url({raw})'

    out = re.sub(r"@import\s+(?:url\()?['\"]?([^)\'\"]+)['\"]?\)?", repl_import, out, flags=re.I)
    return out


# --- MAIN BUILD ---
async def main():
    # Build robots
    robots = build_robots(f"https://{DOMAIN}/")

    # Collect crawled pages
    page_map = collect_pages()  # canon_url -> Path(dir)
    if not page_map:
        print("No crawled pages found under output/nab/. Run your crawler first.")
        return
    print(f"Found {len(page_map)} crawled pages.")

    # First pass: gather every asset URL we want
    asset_urls: set[str] = set()
    forced_css: set[str] = set()   # URLs we must fetch as CSS even if no .css ext
    page_html: dict[Path, tuple[str, BeautifulSoup]] = {}  # dir -> (url, soup)

    for canon_url, page_dir in page_map.items():
        raw = (page_dir / "raw.html")
        if not raw.exists():
            continue
        html = raw.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(html, "html.parser")
        page_html[page_dir] = (canon_url, soup)

        def want(u: str | None):
            if not u:
                return
            if (MIRROR_EXTERNAL_ASSETS or is_same_site(u)) and is_asset(u):
                asset_urls.add(u)

        # collect from <link>
        for link in soup.find_all("link", href=True):
            rels = [r.lower() for r in (link.get("rel") or [])]
            as_attr = (link.get("as") or "").lower()
            u = absolutize(canon_url, link["href"])
            if not u:
                continue
            # Always fetch stylesheets and style preloads (even if no .css suffix)
            if ("stylesheet" in rels) or ("preload" in rels and as_attr == "style"):
                forced_css.add(u)
                asset_urls.add(u)
            else:
                want(u)

        # collect from <script src>
        for s in soup.find_all("script", src=True):
            u = absolutize(canon_url, s["src"])
            want(u)

        # images/media
        for tag in soup.find_all(["img","source","video","audio"], src=True):
            u = absolutize(canon_url, tag["src"])
            want(u)

        # srcset
        for tag in soup.find_all(["img","source"]):
            ss = tag.get("srcset")
            if ss:
                for u, _desc in parse_srcset(ss):
                    want(absolutize(canon_url, u))

        # inline style attributes: url(...)
        for el in soup.find_all(style=True):
            for m in re.finditer(r"url\(([^)]+)\)", el["style"]):
                raw_url = m.group(1).strip('\'"')
                want(absolutize(canon_url, raw_url))

        # NEW: <style> blocks — @import url(...) and url(...)
        for style_tag in soup.find_all("style"):
            css_text = (style_tag.string or style_tag.get_text() or "")
            # @import url(...)
            for m in re.finditer(r"@import\s+url\(([^)]+)\)", css_text, flags=re.I):
                u = absolutize(canon_url, m.group(1).strip('\'"'))
                if u:
                    forced_css.add(u)
                    asset_urls.add(u)
            # generic url(...) inside CSS (e.g., fonts, images)
            for m in re.finditer(r"url\(([^)]+)\)", css_text, flags=re.I):
                u = absolutize(canon_url, m.group(1).strip('\'"'))
                want(u)

    print(f"Queued {len(asset_urls)} assets to download "
          f"(including {len(forced_css)} forced CSS URLs).")

    # Download assets concurrently (safer: retries + don't cancel siblings)
    asset_map: dict[str, Path] = {}  # asset_url -> local path
    headers = {"User-Agent": "Mozilla/5.0 (compatible; Crawl4AI-StaticMirror/1.0)"}
    sem = asyncio.Semaphore(CONCURRENCY)

    # local tunables
    retries = 2
    timeout_total = 45  # seconds

    async def fetch_asset(session: aiohttp.ClientSession, url: str):
        try:
            # --- robots override logic (AEM clientlibs etc.) ---
            purl = urllib.parse.urlsplit(url)
            ext  = Path(purl.path).suffix.lower()

            robots_exempt = (
                (ext in OVERRIDE_ROBOTS_EXTS) or
                any(purl.path.startswith(pref) for pref in FORCE_MIRROR_PATH_PREFIXES) or
                (url in forced_css)  # stylesheets we force-fetch even without .css
            )

            # Apply robots.txt only to same-site URLs that are NOT exempt
            if robots and is_same_site(url) and not robots_exempt:
                try:
                    if not robots.can_fetch(headers["User-Agent"], url):
                        print(f"🚫 robots.txt disallows asset: {url}")
                        return
                except Exception:
                    pass

            # allow external if (a) mirroring externals, (b) forced CSS, or (c) same-site
            external_ok = MIRROR_EXTERNAL_ASSETS or (url in forced_css) or is_same_site(url)
            if not external_ok:
                return

            # allow if recognized asset type OR explicitly forced as CSS
            if not is_asset(url) and url not in forced_css:
                return

            path = asset_local_path(url)
            # If this was identified as CSS but has no extension, force .css so the server serves text/css
            if url in forced_css and path.suffix.lower() != ".css":
                path = path.with_suffix(".css")

            if path.exists():
                asset_map[url] = path
                return

            async with sem:
                # polite delay while holding the slot to avoid stampedes
                await asyncio.sleep(REQUEST_GAP_SECONDS)

                last_err = None
                for attempt in range(retries + 1):
                    try:
                        async with session.get(
                            url,
                            headers=headers,
                            timeout=aiohttp.ClientTimeout(total=timeout_total),
                        ) as resp:
                            if resp.status != 200:
                                last_err = RuntimeError(f"HTTP {resp.status}")
                                # retry on transient statuses
                                if resp.status in (408, 425, 429, 500, 502, 503, 504) and attempt < retries:
                                    await asyncio.sleep(0.6 * (attempt + 1))
                                    continue
                                print(f"⚠️ {resp.status} on {url}")
                                return
                            data = await resp.read()
                            path.parent.mkdir(parents=True, exist_ok=True)
                            with open(path, "wb") as f:
                                f.write(data)
                            asset_map[url] = path
                            print(f"⬇️  {url} -> {path.relative_to(OUTPUT_ROOT)}")
                            return
                    except Exception as e:
                        last_err = e
                        if attempt < retries:
                            await asyncio.sleep(0.6 * (attempt + 1))
                            continue
                # after retries
                print(f"⚠️ Error fetching {url}: {last_err}")
        except Exception as e:
            # absolutely nothing should escape — prevents session shutdown
            print(f"⚠️ Unexpected error for {url}: {e}")


    connector = aiohttp.TCPConnector(limit_per_host=4)
    async with aiohttp.ClientSession(connector=connector) as session:
        # 1st round: fetch everything we discovered from HTML
        pending: set[str] = set(asset_urls)
        scanned_css: set[str] = set()  # which CSS URLs we've already parsed
    
        async def run_batch(urls: set[str]):
            results = await asyncio.gather(
                *(fetch_asset(session, u) for u in urls),
                return_exceptions=True,
            )
            fails = sum(1 for r in results if isinstance(r, Exception))
            if fails:
                print(f"⚠️ {fails} tasks returned exceptions.")
    
        # Round 1
        if pending:
            await run_batch(pending)
    
        # Round 2: discover CSS dependencies (@import + url(...) inside downloaded CSS) and fetch them
        newly_found: set[str] = set()
        for css_url, css_path in list(asset_map.items()):
            if (css_url in forced_css or _ext_of(css_url) == ".css") and css_url not in scanned_css:
                scanned_css.add(css_url)
                try:
                    css_text = css_path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
    
                # Discover @import targets (treat as CSS even if extensionless)
                for m in re.finditer(r"@import\s+(?:url\()?['\"]?([^)\'\"]+)['\"]?\)?", css_text, flags=re.I):
                    dep = url_canon(urllib.parse.urljoin(css_url, m.group(1).strip('\'"')))
                    if not dep:
                        continue
                    forced_css.add(dep)  # fetch as CSS
                    if dep not in asset_map:
                        newly_found.add(dep)
    
                # Discover url(...) targets (fonts/images from CSS)
                for m in re.finditer(r"url\(([^)]+)\)", css_text, flags=re.I):
                    raw = m.group(1).strip('\'"')
                    dep = url_canon(urllib.parse.urljoin(css_url, raw))
                    if not dep:
                        continue
                    if (MIRROR_EXTERNAL_ASSETS or is_same_site(dep)) and is_asset(dep) and dep not in asset_map:
                        newly_found.add(dep)
    
        if newly_found:
            print(f"Discovered {len(newly_found)} additional assets from CSS; fetching...")
            await run_batch(newly_found)


    # Optional: rewrite CSS url(...) to local paths
    if REWRITE_CSS_URLS:
        css_urls = [u for u in asset_map if _ext_of(u) in (".css",) or u in forced_css]
        for css_url in css_urls:
            css_path = asset_map[css_url]
            try:
                css_text = css_path.read_text(encoding="utf-8", errors="ignore")
                new_css = rewrite_css_urls(css_text, css_url, css_path, asset_map)
                if new_css != css_text:
                    css_path.write_text(new_css, encoding="utf-8")
            except Exception as e:
                print(f"⚠️ CSS rewrite failed for {css_path}: {e}")

    # Second pass: write index.html with rewritten links
    pages_written = 0
    for page_dir, (canon_url, soup) in page_html.items():
        if STRIP_SCRIPTS:
            for s in soup.find_all("script"):
                s.decompose()

        rewrite_html(canon_url, page_dir, soup, page_map, asset_map)
        out = page_dir / "index.html"
        out.write_text(str(soup), encoding="utf-8")
        pages_written += 1

    print(f"✅ Wrote {pages_written} HTML pages with local links.")
    root_index = OUTPUT_ROOT / list(page_map.values())[0].parts[len(OUTPUT_ROOT.parts)]
    print(f"Open a page like: {OUTPUT_ROOT}/www.nab.com.au/index.html in your browser.")
    print("Tip: serve via a tiny HTTP server for best results:")
    print(f"    cd {OUTPUT_ROOT} && python -m http.server 8000  # then visit http://localhost:8000/www.nab.com.au/")

if __name__ == "__main__":
    asyncio.run(main())
