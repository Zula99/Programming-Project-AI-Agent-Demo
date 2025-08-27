# crawl_nab.py
import asyncio
import os
import re
import time
import json
import urllib.parse
import urllib.robotparser as robotparser
from collections import deque
from pathlib import Path

try:
    from bs4 import BeautifulSoup
    HAVE_BS4 = True
except Exception:
    HAVE_BS4 = False

from crawl4ai import AsyncWebCrawler

START_URL   = "https://www.nab.com.au/"
DOMAIN      = "nab.com.au"          # allow subdomains of nab.com.au
OUTPUT_ROOT = Path("output/nab")
MAX_PAGES   = 80                    # bump as needed
REQUEST_GAP = 0.6                   # polite delay (s)
USER_AGENT  = "Mozilla/5.0 (compatible; Crawl4AI-NAB-Tester/1.1)"

# ---- URL helpers

# strip tracking/query noise but keep essential params if needed
DROP_QUERY_KEYS = {"utm_source","utm_medium","utm_campaign","utm_term","utm_content","gclid","fbclid","_ga","_gl"}

def url_canon(url: str) -> str:
    """
    Canonicalize a URL for de-duplication:
    - lowercase scheme/host
    - collapse duplicate slashes
    - drop fragment
    - drop known tracking params
    - normalise trailing slash (except root)
    """
    parts = urllib.parse.urlsplit(url)
    scheme = parts.scheme.lower()
    netloc = parts.netloc.lower()

    # collapse // in path
    path = re.sub(r"/{2,}", "/", parts.path)

    # drop fragment
    fragment = ""

    # clean query
    q = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
    q = [(k, v) for (k, v) in q if k not in DROP_QUERY_KEYS]
    query = urllib.parse.urlencode(q, doseq=True)

    # normalise trailing slash: keep root "/", but strip elsewhere
    if path != "/" and path.endswith("/"):
        path = path[:-1]

    return urllib.parse.urlunsplit((scheme, netloc, path, query, fragment))

def is_same_site(url: str) -> bool:
    try:
        host = urllib.parse.urlsplit(url).netloc.lower()
        return host.endswith(DOMAIN)
    except Exception:
        return False

BINARY_EXTENSIONS = (
    ".png",".jpg",".jpeg",".gif",".webp",".svg",".pdf",".zip",".rar",".7z",
    ".mp4",".mov",".avi",".mp3",".wav",".ogg",".webm",".ico",".dmg",".exe",".css",".js",".mjs",".json",".xml",".txt",".csv"
)

def looks_binary(url: str) -> bool:
    path = urllib.parse.urlsplit(url).path.lower()
    return any(path.endswith(ext) for ext in BINARY_EXTENSIONS)

def to_abs(base: str, href: str | None) -> str | None:
    if not href:
        return None
    if href.startswith(("mailto:", "tel:", "javascript:", "#")):
        return None
    u = urllib.parse.urljoin(base, href)
    return url_canon(u)

# ---- folder-style slugify

_invalid = re.compile(r"[^a-z0-9._-]+")

def path_slug(url: str) -> Path:
    """
    Map a URL to a folder structure:

    https://www.nab.com.au/                   -> output/nab/www.nab.com.au/index.md
    https://www.nab.com.au/personal-banking   -> output/nab/www.nab.com.au/personal-banking/index.md
    https://www.nab.com.au/pb/cards?x=1       -> output/nab/www.nab.com.au/pb/cards/_q_x=1/index.md

    We keep query (if any) as a subfolder `_q_<sorted query>` to avoid overwriting.
    """
    parts = urllib.parse.urlsplit(url)
    host = parts.netloc.lower()
    path = parts.path

    if not path or path == "/":
        segments = []
    else:
        segments = [s for s in path.split("/") if s]

    # sanitise each segment
    segments = [_invalid.sub("-", s.lower()).strip("-")[:80] for s in segments]

    # encode query if present (after dropping trackers in url_canon)
    if parts.query:
        q = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
        q.sort()
        qstr = "&".join([f"{_invalid.sub('-', k.lower())}={_invalid.sub('-', v.lower())}" for k, v in q])[:120]
        segments.append(f"_q_{qstr}")

    # compose final path: OUTPUT_ROOT/<host>/<segments...>/index.md
    final_dir = OUTPUT_ROOT / host
    for s in segments:
        final_dir = final_dir / s
    return final_dir  # this is the folder; we write index.md inside

# ---- link extraction

def extract_links(html: str, base_url: str) -> set[str]:
    links: set[str] = set()
    if not html:
        return links

    if HAVE_BS4:
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            u = to_abs(base_url, a["href"])
            if u:
                links.add(u)
        return links

    # fallback regex
    for m in re.finditer(r'href=["\']([^"\']+)["\']', html, flags=re.I):
        u = to_abs(base_url, m.group(1))
        if u:
            links.add(u)
    return links

# ---- crawler

async def crawl():
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    # robots.txt
    rp = robotparser.RobotFileParser()
    rp.set_url(urllib.parse.urljoin(START_URL, "/robots.txt"))
    try:
        rp.read()
    except Exception:
        pass  # if robots fails to load, we proceed cautiously

    q = deque([url_canon(START_URL)])
    seen: set[str] = set()
    pages = 0

    async with AsyncWebCrawler(user_agent=USER_AGENT) as crawler:
        while q and pages < MAX_PAGES:
            url = q.popleft()
            if url in seen:
                continue
            seen.add(url)

            if not is_same_site(url) or looks_binary(url):
                continue

            try:
                # robots
                try:
                    if not rp.can_fetch(USER_AGENT, url):
                        print(f"🚫 robots.txt disallows: {url}")
                        continue
                except Exception:
                    pass

                time.sleep(REQUEST_GAP)

                # Crawl
                result = await crawler.arun(url)

                # Prefer raw_html; fall back to html or markdown
                raw_html = getattr(result, "raw_html", None) or getattr(result, "html", None) or ""
                content_md = getattr(result, "markdown", None) or getattr(result, "clean_text", "") or ""

                # Save in folder-structure
                folder = path_slug(url)
                folder.mkdir(parents=True, exist_ok=True)

                md_path = folder / "index.md"
                meta_path = folder / "meta.json"
                html_path = folder / "raw.html"

                # write files
                with md_path.open("w", encoding="utf-8") as f:
                    f.write(content_md)

                if raw_html:
                    with html_path.open("w", encoding="utf-8") as f:
                        f.write(raw_html)

                meta = {
                    "url": url,
                    "title": getattr(result, "title", None),
                    "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "content_type": getattr(result, "content_type", None),
                    "bytes_html": len(raw_html) if raw_html else 0,
                }
                with meta_path.open("w", encoding="utf-8") as f:
                    json.dump(meta, f, ensure_ascii=False, indent=2)

                pages += 1
                print(f"✅ [{pages}/{MAX_PAGES}] {url}  ->  {md_path}")

                # Discover more links
                links = extract_links(raw_html, url)
                # Keep only same-site, non-binary, unseen
                keep = [
                    u for u in links
                    if is_same_site(u) and not looks_binary(u) and u not in seen
                ]

                # Deduplicate but maintain relative BFS order
                for u in keep:
                    if u not in q:
                        q.append(u)

                print(f"   ↳ queued {len(keep)} new links (queue size: {len(q)})")

            except Exception as e:
                print(f"⚠️  Error on {url}: {e}")

    print(f"Done. Crawled {pages} page(s). Output in: {OUTPUT_ROOT.resolve()}")

if __name__ == "__main__":
    asyncio.run(crawl())
