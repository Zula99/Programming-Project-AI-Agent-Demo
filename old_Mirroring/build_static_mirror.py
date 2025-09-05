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
DOMAIN                = None                         # will be set dynamically at runtime
OUTPUT_ROOT           = None                        # will be set dynamically at runtime
REQUEST_GAP_SECONDS   = 0.15                        # polite delay between asset fetches
CONCURRENCY           = 8                           # parallel asset downloads
RESPECT_ROBOTS        = False                        # honor robots for asset URLs
STRIP_SCRIPTS         = False                       # set True to remove <script> tags
REWRITE_CSS_URLS      = True                        # rewrite url(...) in CSS to local paths
# Docker runs on Linux - no path length limits needed
MAX_PATH_LENGTH = 4096  # Linux filesystem limit (much higher than needed)
RETRIES               = 3                           # retry asset fetches this many times on failure  
TIMEOUT_TOTAL         = 60                          # seconds total timeout for asset fetch
MIRROR_EXTERNAL_ASSETS = True                        # download CDN assets for better demos
FORCE_MIRROR_PATH_PREFIXES = ("/etc.clientlibs/", "/etc/clientlibs/", "/content/dam/", "/etc/designs/", "/apps/", "/libs/", 
                                "/assets/", "/static/", "/resources/", "./etc/", "./etc.clientlibs/", "./etc/clientlibs/")
OVERRIDE_ROBOTS_EXTS  = {".css", ".js", ".mjs", ".woff", ".woff2", ".ttf", ".otf", 
                         ".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp", ".ico", ".eot"}


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

    # Only hash extremely long paths (very rare in practice)
    if len(str(target)) >= MAX_PATH_LENGTH:
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
        rel_path = rel_path.replace('\\', '/')
        
        # Ensure relative paths start with ./ or ../ for browser compatibility
        if not rel_path.startswith(('./', '../')):
            if '/' in rel_path:
                rel_path = './' + rel_path
        
        return rel_path
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
    
    # Normalize Windows-style backslashes to forward slashes before URL joining
    # This fixes malformed paths like "..\..\..\_assets\file.woff2"
    normalized_href = href.replace('\\', '/')
    
    # Fix malformed relative paths like "../..-cdn-fonts" -> "../../cdn/fonts"
    normalized_href = re.sub(r'\.\.-.\.\.', '../..', normalized_href)
    
    # Handle /etc/clientlibs/ and other relative assets properly
    if normalized_href.startswith(('./etc/', './etc.clientlibs/', './etc/clientlibs/')):
        # Remove leading ./ to make it absolute from site root
        normalized_href = normalized_href[1:]
    elif normalized_href.startswith(('/etc.clientlibs/', '/etc/clientlibs/')):
        # These are already absolute paths from site root
        pass
    
    return url_canon(urllib.parse.urljoin(base_url, normalized_href))

def rewrite_html(page_url: str, page_dir: Path, soup: BeautifulSoup,
                 page_map: dict[str, Path], asset_map: dict[str, Path]) -> None:
    # 1) Anchor links to other mirrored pages → local index.html with enhanced traversal
    for a in soup.find_all("a", href=True):
        original_href = a["href"]
        absu = absolutize(page_url, original_href)
        if not absu:
            continue
        
        if is_same_site(absu) and absu in page_map:
            # Internal link - rewrite to local mirror path
            a["href"] = make_rel(page_dir, page_map[absu] / "index.html")
        elif not is_same_site(absu) and not original_href.startswith(('#', 'mailto:', 'tel:', 'javascript:')):
            # External link - ensure opens in new tab for demo
            if not a.get('target'):
                a['target'] = '_blank'
                a['rel'] = a.get('rel', []) + ['noopener', 'noreferrer']
        
        # Drop query params and hashes for cleaner local navigation
        if 'href' in a.attrs and a['href'].startswith('./'):
            # Clean up local links by removing query params and hashes
            local_href = a['href'].split('?')[0].split('#')[0]
            if local_href != a['href']:
                a['href'] = local_href

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

# --- Adobe Target/Alloy Fix for SPA Sites ---
def fix_adobe_blocking_styles(soup: BeautifulSoup) -> None:
    """
    Remove Adobe Target/Alloy styles that hide content in static mirrors.
    These styles hide the entire page until A/B testing JS runs, but we want 
    content visible in static demos.
    """
    # Remove Adobe Target opacity blocking
    for style in soup.find_all("style", id=lambda x: x and ("at-body-style" in x or "alloy-prehiding" in x)):
        print(f"🔧 Removing Adobe blocking style: {style.get('id', 'unknown')}")
        style.decompose()
    
    # Remove inline styles that hide body/container
    adobe_blocking_patterns = [
        r'body\s*\{\s*opacity:\s*0\s*!important\s*\}',
        r'\.container\s*\{\s*opacity:\s*0\s*!important\s*\}',
        r'body\s*\{\s*display:\s*none\s*!important\s*\}',
        r'\.container\s*\{\s*display:\s*none\s*!important\s*\}'
    ]
    
    for style in soup.find_all("style"):
        if style.string:
            original = style.string
            modified = original
            for pattern in adobe_blocking_patterns:
                modified = re.sub(pattern, '', modified, flags=re.I)
            if modified != original:
                print(f"🔧 Fixed Adobe blocking CSS in <style> tag")
                style.string = modified

def fix_adobe_target_mbox(soup: BeautifulSoup) -> None:
    """
    Fix Adobe Target mbox issues that prevent hero sections from showing.
    Remove mboxDefault class and make hero content visible.
    """
    # Remove mboxDefault class that hides hero content
    mbox_elements = soup.find_all(class_="mboxDefault")
    for element in mbox_elements:
        print(f"🔧 Removing mboxDefault class from {element.name} element")
        element['class'] = [cls for cls in element.get('class', []) if cls != 'mboxDefault']
        
        # If no classes left, remove the class attribute entirely
        if not element.get('class'):
            del element['class']
    
    # Force hero sections to be visible by removing common hiding patterns
    hero_selectors = [
        '[id*="HERO"]',
        '[class*="hero"]',
        '[class*="banner"]'
    ]
    
    for selector in hero_selectors:
        elements = soup.select(selector)
        for element in elements:
            # Remove display: none styles if present
            style = element.get('style', '')
            if 'display: none' in style or 'display:none' in style:
                print(f"🔧 Removing display:none from {element.name} element")
                style = style.replace('display: none', '').replace('display:none', '')
                if style.strip():
                    element['style'] = style
                else:
                    if 'style' in element.attrs:
                        del element['style']

def fix_spa_layout_issues(soup: BeautifulSoup) -> None:
    """
    Fix common SPA layout issues that occur in static mirrors
    - Overlapping elements
    - Broken positioning
    - Runaway absolute positioning
    """
    fixed_count = 0
    
    # 1. Fix hero/banner sections with runaway positioning
    hero_selectors = [
        '[id*="hero" i]', '[id*="HERO"]', '[class*="hero" i]', 
        '[class*="banner" i]', '[id*="banner" i]'
    ]
    
    for selector in hero_selectors:
        containers = soup.select(selector)
        for container in containers:
            # Add containment to prevent overflow
            existing_style = container.get('style', '')
            if 'position: relative' not in existing_style:
                new_style = existing_style + '; position: relative; overflow: hidden;'
                container['style'] = new_style
                fixed_count += 1
    
    # 2. Constrain elements with extreme positioning
    all_elements = soup.find_all(lambda tag: tag.get('style'))
    for element in all_elements:
        style = element.get('style', '')
        modified = False
        
        # Fix elements positioned outside viewport
        if 'position: absolute' in style:
            # Prevent elements from escaping their containers
            if 'max-width' not in style:
                style += '; max-width: 100%;'
                modified = True
            if 'max-height' not in style and any(prop in style for prop in ['top:', 'bottom:', 'height:']):
                style += '; max-height: 100vh;'
                modified = True
        
        # Fix elements with excessive z-index that overlay everything
        if 'z-index:' in style:
            import re
            z_match = re.search(r'z-index:\s*(\d+)', style)
            if z_match and int(z_match.group(1)) > 1000:
                style = re.sub(r'z-index:\s*\d+', 'z-index: 999', style)
                modified = True
        
        if modified:
            element['style'] = style
            fixed_count += 1
    
    # 3. Fix common SPA loading states that get stuck
    loading_selectors = ['[class*="loading" i]', '[class*="spinner" i]', '[id*="loading" i]']
    for selector in loading_selectors:
        loading_elements = soup.select(selector)
        for element in loading_elements:
            # Hide stuck loading spinners
            existing_style = element.get('style', '')
            if 'display: none' not in existing_style:
                element['style'] = existing_style + '; display: none;'
                fixed_count += 1
    
    if fixed_count > 0:
        print(f"🔧 Fixed {fixed_count} SPA layout issues (generic fixes for all sites)")

def remove_anti_flicker_styles(soup: BeautifulSoup) -> None:
    """
    Remove anti-flicker styles and CSP meta tags that break static mirrors
    """
    removed_count = 0
    
    # Remove Content Security Policy meta tags (break static mirrors)
    for meta in soup.find_all('meta', {'http-equiv': lambda x: x and x.lower() == 'content-security-policy'}):
        print(f"🔧 Removing CSP meta tag: {meta.get('content', '')[:50]}...")
        meta.decompose()
        removed_count += 1
    
    # Remove anti-flicker style blocks
    anti_flicker_patterns = [
        r'opacity:\s*0\s*!important',
        r'FORCE.*ACTIVATION',
        r'display:\s*none\s*!important.*body',
        r'visibility:\s*hidden\s*!important.*body',
        r'at-body-style',
        r'alloy-prehiding'
    ]
    
    for style_tag in soup.find_all('style'):
        style_content = style_tag.string or style_tag.get_text() or ''
        if any(re.search(pattern, style_content, re.I | re.DOTALL) for pattern in anti_flicker_patterns):
            print(f"🔧 Removing anti-flicker style block")
            style_tag.decompose()
            removed_count += 1
    
    if removed_count > 0:
        print(f"🔧 Removed {removed_count} anti-flicker styles and CSP tags")

def add_static_mirror_css_fixes(soup: BeautifulSoup) -> None:
    """
    Add CSS to fix common static mirror layout issues via <style> injection
    """
    # CSS to fix common SPA issues in static mirrors
    css_fixes = """
    <style id="static-mirror-fixes">
    /* Fix hero section - keep content but constrain background elements */
    #CB-HOME-HERO, .hero-container, .banner-image {
        position: relative !important;
        overflow: hidden !important;
        max-height: 500px !important;
        contain: layout style paint !important;
    }
    
    /* Specifically target the diamond background elements */
    #CB-HOME-HERO::before, #CB-HOME-HERO::after,
    .hero-container::before, .hero-container::after,
    .banner-image::before, .banner-image::after {
        max-width: 100% !important;
        max-height: 100% !important;
        position: absolute !important;
        z-index: 1 !important;
    }
    
    /* Fix CommBank product tiles - constrain yellow diamond backgrounds */
    .icon, .icon *, [class*="pictogram"], [src*="pictogram"] {
        position: relative !important;
        overflow: hidden !important;
        max-width: 100px !important;
        max-height: 100px !important;
        z-index: 1 !important;
    }
    
    /* Remove all pseudo-elements that might create overlay diamonds */
    .icon::before, .icon::after,
    [class*="button"]::before, [class*="button"]::after,
    [class*="drop-down"]::before, [class*="drop-down"]::after {
        display: none !important;
    }
    
    /* SURGICAL APPROACH: Keep ALL layout CSS, only fix the specific overlay problem */
    
    /* Only constrain elements that are clearly overlaying the entire viewport */
    [style*="position: absolute"][style*="width: 100vw"],
    [style*="position: fixed"][style*="width: 100vw"],
    [style*="position: absolute"][style*="height: 100vh"],
    [style*="position: fixed"][style*="height: 100vh"] {
        max-width: 500px !important;
        max-height: 400px !important;
        position: absolute !important;
    }
    
    /* Hide loading states and overlays */
    [class*="loading" i], [class*="spinner" i], [class*="overlay" i],
    [class*="modal" i]:not(.show), [style*="position: absolute"]:empty {
        display: none !important;
    }
    
    /* Ensure content is visible with white background */
    body {
        background: white !important;
        color: #333 !important;
        opacity: 1 !important;
        visibility: visible !important;
    }
    
    /* Force all major content containers to be visible */
    main, .main, .content, .container {
        opacity: 1 !important;
        visibility: visible !important;
        display: block !important;
    }
    </style>
    """
    
    # Find the head tag and insert the CSS
    head = soup.find('head')
    if head:
        head.append(BeautifulSoup(css_fixes, 'html.parser'))
        print("🔧 Added CSS fixes for static mirror layout issues")
    else:
        # If no head tag, add it to body
        body = soup.find('body')
        if body:
            body.insert(0, BeautifulSoup(css_fixes, 'html.parser'))
            print("🔧 Added CSS fixes to body (no head tag found)")

def strip_analytics_scripts(soup: BeautifulSoup) -> None:
    """
    Remove analytics/personalization scripts that break static mirrors
    Strips Adobe Launch/Target, Google Analytics, Facebook Pixel, etc.
    """
    removed_count = 0
    
    # Analytics/tracking script patterns to remove completely
    analytics_patterns = [
        # Adobe tracking and personalization
        '_satellite', 'alloy', 'adobedatalayer', 'commbankaep-launch',
        'adobe.target', 'mboxdefine', 'mboxcreate', 'at.js',
        # Google tracking
        'google-analytics', 'gtag', 'ga(', '_gaq', 'googletagmanager',
        'analytics.google', 'tagmanager.google',
        # Social media tracking
        'facebook.net', 'fbevents.js', 'connect.facebook', 'fbq(',
        'twitter.com/widgets', 'platform.twitter',
        # Other tracking services  
        'hotjar', 'optimizely', 'segment.', 'tealium', 'demdex',
        'omniture', 'chartbeat', 'quantserve', 'doubleclick.net',
        # AEM-specific tracking
        'cq_analytics', 'cq.analytics', 'ClientContext'
    ]
    
    # Inline script content patterns to remove
    inline_patterns = [
        'CQ_Analytics', 'mboxDefine', 'gtag(', '_satellite',
        'window.alloy', 'facebook.net', 'fbq(', 'analytics.google',
        'dataLayer.push', '_gaq.push', 'ga("create"', 
        'hotjar.init', 'optimizely.push'
    ]
    
    scripts = soup.find_all('script')
    for script in scripts:
        should_remove = False
        
        # Check external script sources
        script_src = (script.get('src') or '').lower()
        if script_src and any(pattern in script_src for pattern in analytics_patterns):
            should_remove = True
        
        # Check inline script content
        script_content = script.string or script.get_text() or ''
        if script_content and any(pattern in script_content for pattern in inline_patterns):
            should_remove = True
        
        # Remove the entire script tag
        if should_remove:
            script.decompose()
            removed_count += 1
    
    if removed_count > 0:
        print(f"🔧 Removed {removed_count} analytics/tracking scripts")

def disable_overlay_javascript(soup: BeautifulSoup) -> None:
    """
    Disable JavaScript that creates problematic overlays in static mirrors
    (Keep for essential interactivity, disable problematic ones)
    """
    disabled_count = 0
    
    # Find script tags that might create overlays (disable, don't remove)
    problem_patterns = [
        'lottie',  # Animation library often used for overlays
        'canvas',  # Canvas rendering that might overlay
        'overlay', 'modal', 'popup',  # Overlay-related scripts
        'transform3d', 'translate3d',  # 3D positioning scripts
    ]
    
    scripts = soup.find_all('script')
    for script in scripts:
        script_content = script.string or ''
        script_src = script.get('src', '')
        
        # Check if script contains problematic patterns
        if any(pattern in script_content.lower() or pattern in script_src.lower() 
               for pattern in problem_patterns):
            script['type'] = 'text/plain'  # Disable instead of removing
            disabled_count += 1
    
    if disabled_count > 0:
        print(f"🔧 Disabled {disabled_count} potentially problematic JavaScript files")

def normalize_lazy_loaded_media(soup: BeautifulSoup) -> None:
    """
    Normalize lazy-loaded media by moving data-* attributes to proper src/srcset
    Handles <img>, <video>, <iframe>, <source> elements
    """
    normalized_count = 0
    
    # Data attribute mappings for different lazy loading implementations
    src_mappings = [
        'data-src', 'data-lazy-src', 'data-original', 'data-image-desktop-src', 
        'data-image-mobile-src', 'data-lazy', 'data-echo', 'data-unveil'
    ]
    
    srcset_mappings = [
        'data-srcset', 'data-lazy-srcset', 'data-sizes'
    ]
    
    # Process images
    for img in soup.find_all(['img', 'source', 'video', 'iframe']):
        # Normalize src attribute
        if not img.get('src') or img.get('src') in ['', 'data:,', 'data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==']:
            for data_attr in src_mappings:
                data_src = img.get(data_attr)
                if data_src and data_src not in ['', '#', 'data:,']:
                    img['src'] = data_src
                    img.attrs.pop(data_attr, None)  # Remove data attribute
                    normalized_count += 1
                    break
        
        # Normalize srcset attribute (for img and source)
        if img.name in ['img', 'source'] and not img.get('srcset'):
            for data_attr in srcset_mappings:
                data_srcset = img.get(data_attr)
                if data_srcset:
                    img['srcset'] = data_srcset
                    img.attrs.pop(data_attr, None)  # Remove data attribute
                    normalized_count += 1
                    break
    
    if normalized_count > 0:
        print(f"🔧 Normalized {normalized_count} lazy-loaded media elements")

def add_missing_layout_classes(soup: BeautifulSoup) -> None:
    """
    Add CSS classes that JavaScript normally adds to activate layouts
    """
    added_count = 0
    
    # Add common JavaScript-activated classes to body
    body = soup.find('body')
    if body:
        current_classes = body.get('class', [])
        new_classes = ['loaded', 'js-enabled', 'layout-ready']
        for cls in new_classes:
            if cls not in current_classes:
                current_classes.append(cls)
                added_count += 1
        body['class'] = current_classes
    
    # Add layout activation classes to main containers
    containers = soup.find_all(['main', 'div'], class_=lambda x: x and any(
        keyword in ' '.join(x) for keyword in ['container', 'hero', 'banner', 'homepage']
    ))
    
    for container in containers:
        current_classes = container.get('class', [])
        if 'layout-active' not in current_classes:
            current_classes.append('layout-active')
            container['class'] = current_classes
            added_count += 1
    
    # Add responsive classes that activate mobile/desktop layouts
    honeycomb = soup.find(class_='honeycomb')
    if honeycomb:
        current_classes = honeycomb.get('class', [])
        responsive_classes = ['responsive-ready', 'desktop-layout']
        for cls in responsive_classes:
            if cls not in current_classes:
                current_classes.append(cls)
                added_count += 1
        honeycomb['class'] = current_classes
    
    if added_count > 0:
        print(f"🔧 Added {added_count} JavaScript-activated layout classes")


def convert_css_preloads_to_stylesheets(soup: BeautifulSoup) -> None:
    """Convert CSS preload links to actual stylesheets for AEM compatibility"""
    converted_count = 0
    
    for link in soup.find_all("link"):
        rel = link.get("rel") or []
        as_attr = (link.get("as") or "").lower()
        
        if "preload" in rel and as_attr == "style":
            link["rel"] = ["stylesheet"]
            link.attrs.pop("as", None)
            converted_count += 1
            print(f"🔄 Converted CSS preload to stylesheet: {link.get('href', 'unknown')}")
    
    if converted_count > 0:
        print(f"🔧 Converted {converted_count} CSS preloads to stylesheets")

def add_js_enabled_classes(soup: BeautifulSoup) -> None:
    """Add JavaScript-enabled classes for CSS gate activation"""
    changes = 0
    
    # Add js/js-enabled classes to html element
    if soup.html:
        classes = set(soup.html.get("class") or [])
        new_classes = {"js", "js-enabled"}
        added = new_classes - classes
        if added:
            classes.update(added)
            soup.html["class"] = list(classes)
            changes += len(added)
    
    # Add js/js-enabled classes to body element
    if soup.body:
        classes = set(soup.body.get("class") or [])
        new_classes = {"js", "js-enabled"}
        added = new_classes - classes
        if added:
            classes.update(added)
            soup.body["class"] = list(classes)
            changes += len(added)
    
    if changes > 0:
        print(f"🔧 Added {changes} JS-enabled classes for CSS gate activation")

def add_base_href(soup: BeautifulSoup) -> None:
    """Add base href for relative URL resolution"""
    if soup.head and not soup.head.find("base"):
        base_tag = soup.new_tag("base", href="./")
        soup.head.insert(0, base_tag)
        print("🔧 Added base href for relative URL resolution")

def create_hybrid_html(raw_html_path: Path, rendered_html_path: Path) -> str:
    """
    Create hybrid HTML combining:
    - Head section preferably from rendered HTML (includes critical inline styles)
    - Body content from rendered HTML (post-JavaScript content)
    - Safe metadata from raw HTML when missing from rendered
    """
    try:
        raw_content = raw_html_path.read_text(encoding="utf-8", errors="ignore")
        rendered_content = rendered_html_path.read_text(encoding="utf-8", errors="ignore")
        
        raw_soup = BeautifulSoup(raw_content, "html.parser")
        rendered_soup = BeautifulSoup(rendered_content, "html.parser")
        
        # Prefer rendered HTML as base (better for SPAs with inline styles)
        base = rendered_soup if rendered_soup.head and rendered_soup.body else raw_soup
        
        # If raw has canonical/charset/viewport and rendered doesn't, copy them
        def copy_meta(name):
            if not base.head or not raw_soup.head:
                return
            if not base.head.find('meta', attrs={'name': name}) and raw_soup.head.find('meta', attrs={'name': name}):
                base.head.append(raw_soup.head.find('meta', attrs={'name': name}))

        copy_meta('viewport')
        copy_meta('charset')
        
        # Copy canonical link if missing
        if base.head and raw_soup.head:
            if not base.head.find('link', attrs={'rel': 'canonical'}) and raw_soup.head.find('link', attrs={'rel': 'canonical'}):
                base.head.append(raw_soup.head.find('link', attrs={'rel': 'canonical'}))

        # Ensure body is the rendered one if available
        if base is raw_soup and rendered_soup.body and raw_soup.body:
            raw_soup.body.replace_with(rendered_soup.body)
            base = raw_soup
            
        print(f"🔄 Using hybrid HTML (rendered head + safe raw metas + rendered body)")
        return str(base)
        
    except Exception as e:
        print(f"⚠️ Hybrid HTML creation failed: {e}, falling back to rendered HTML")
        return rendered_html_path.read_text(encoding="utf-8", errors="ignore")


def add_site_specific_fixes(soup: BeautifulSoup, domain: str) -> None:
    """Add site-specific CSS fixes based on domain"""
    
    # CommBank-specific fixes
    if 'commbank.com.au' in domain.lower():
        style_tag = soup.new_tag('style', type='text/css')
        style_tag.string = """
/* CommBank Static Mirror Fixes */
/* Force main content areas to show */
main.honeycomb, .app.homepage, .hero-container {
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
}

/* Constrain hero image that covers everything */
.hero-container img, .banner-image img {
    max-height: 400px !important;
    object-fit: cover !important;
    position: relative !important;
}

/* Ensure content sections are visible */
.target, .parsys, .banner-content {
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
    position: relative !important;
    z-index: 10 !important;
}

/* Fix any remaining hidden overlays */
[style*="display:none"], [style*="display: none"] {
    display: block !important;
}
"""
        
        if soup.head:
            soup.head.append(style_tag)
            print(f"🔧 Added CommBank-specific CSS fixes for {domain}")
    
    # Add other site-specific fixes here as needed
    # elif 'nab.com.au' in domain.lower():
    #     # NAB-specific fixes
    # elif 'westpac.com.au' in domain.lower():
    #     # Westpac-specific fixes


def inject_layout_initialization_script(soup: BeautifulSoup) -> None:
    """Inject CSS and JavaScript to force CommBank layout activation"""
    
    # Create a comprehensive CSS fix first
    css_fix = soup.new_tag('style', type='text/css')
    css_fix.string = """
/* FORCE COMMBANK LAYOUT ACTIVATION */
.honeycomb, .app.homepage {
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
    position: relative !important;
    width: 100% !important;
}

/* Force hero container to show */
.container.hero-container, .hero-container {
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
    min-height: 400px !important;
    position: relative !important;
}

/* Force all content sections to display */
.target, .parsys, [class*="section"], [class*="content"] {
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
}

/* Force navigation and header to show */
header, nav, .header, .navigation {
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
}

/* Force grid and column layouts */
.column-combo, [class*="column"], .grid {
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
}

/* Remove any transform that might hide content */
* {
    transform: none !important;
}
"""
    
    # Create script to simulate successful initialization
    init_script = soup.new_tag('script', type='text/javascript')
    init_script.string = """
// Static Mirror Layout Initialization
(function() {
    console.log('Static mirror layout initialization...');
    
    // Mock the failing 'defaults' object
    window.defaults = {
        cookieSettings: {},
        analytics: {},
        targeting: {}
    };
    
    // Simulate successful Adobe Target initialization
    window.adobe = window.adobe || {};
    window.adobe.target = window.adobe.target || {
        applyOffers: function() { return Promise.resolve(); },
        getOffers: function() { return Promise.resolve([]); }
    };
    
    // Mock _satellite functions that are failing
    window._satellite = window._satellite || {};
    window._satellite._runScript1 = function() { return true; };
    window._satellite._runScript2 = function() { return true; };
    window._satellite._runScript3 = function() { return true; };
    window._satellite._runScript4 = function() { return true; };
    window._satellite._runScript5 = function() { return true; };
    
    // Force show all major layout containers
    setTimeout(function() {
        var containers = document.querySelectorAll('main, .honeycomb, .app, .hero-container, .container');
        containers.forEach(function(el) {
            el.style.display = 'block';
            el.style.visibility = 'visible';
            el.style.opacity = '1';
            el.style.position = 'relative';
        });
        
        // Force show all content divs
        var content = document.querySelectorAll('.target, .parsys, [class*="section"], [class*="content"]');
        content.forEach(function(el) {
            el.style.display = 'block';
            el.style.visibility = 'visible';
            el.style.opacity = '1';
        });
        
        document.body.classList.add('layout-initialized', 'content-ready');
        console.log('Static mirror layout initialization complete');
    }, 100);
})();
"""
    
    # Insert the CSS fix in head
    if soup.head:
        soup.head.append(css_fix)
    
    # Insert the script at the end of the body
    if soup.body:
        soup.body.append(init_script)
        print("🔧 Injected comprehensive layout fix for CommBank compatibility")

def mirror_report(page_url: str, page_dir: Path, soup: BeautifulSoup) -> None:
    """Generate comprehensive mirror report for debugging"""
    import re
    print(f"--- MIRROR REPORT+ ---")
    print(f"URL: {page_url}")
    print(f"Dir: {page_dir}")

    # Check stylesheets
    links = [l for l in soup.find_all("link") if (l.get("rel") or []) and "stylesheet" in l.get("rel")]
    print(f"Stylesheets applied: {len(links)}")
    for l in links[:6]:
        href = l.get("href", "unknown")
        print(f"  🧵 {href}")
        if href.startswith(("./", "../")) and (page_dir / href).exists():
            print(f"    ✅ File exists")
        elif href.startswith(("http://", "https://")):
            print(f"    🌐 External stylesheet")
        elif not href.startswith(("data:", "mailto:")):
            print(f"    ❌ Local file missing")

    # Confirm CSS files exist and count url(...) rewrites
    total_css = 0; total_urls = 0; missing = 0
    for l in links:
        href = l.get("href") or ""
        if href.startswith(("./", "../")):
            css_path = (page_dir / href).resolve()
            if css_path.exists() and css_path.suffix.lower() == ".css":
                total_css += 1
                try:
                    css_content = css_path.read_text(encoding="utf-8", errors="ignore")
                    urls = re.findall(r"url\(([^)]+)\)", css_content, flags=re.I)
                    total_urls += len(urls)
                    for u in urls:
                        u2 = u.strip('\'"')
                        # Check if local asset exists
                        if not (u2.startswith("http") or u2.startswith("data:")):
                            target = (css_path.parent / u2).resolve()
                            if not target.exists():
                                missing += 1
                except Exception:
                    pass
    
    print(f"CSS files found: {total_css}, url(...) refs: {total_urls}, missing assets: {missing}")

    # Check images
    imgs = soup.find_all("img")
    with_src = sum(1 for i in imgs if i.get("src"))
    lazy_only = sum(1 for i in imgs if any(i.get(attr) for attr in ['data-src', 'data-lazy-src', 'data-original']) and not i.get("src"))
    print(f"Images with src: {with_src}/{len(imgs)} (lazy-only: {lazy_only})")

    # Check for blocking elements
    csp = bool(soup.find("meta", attrs={"http-equiv": lambda v: v and v.lower() == "content-security-policy"}))
    anti_flicker = any(("opacity:0 !important" in (st.string or st.get_text() or "")) for st in soup.find_all("style"))
    adobe = any(("_satellite" in (s.get_text() or "").lower() or "alloy" in (s.get_text() or "").lower())
                for s in soup.find_all("script"))
    
    print(f"Blockers - CSP: {csp}, Anti-flicker: {anti_flicker}, Adobe/Target: {adobe}")
    print(f"HTML classes: {soup.html.get('class') if soup.html else None}")
    print(f"BODY classes: {soup.body.get('class') if soup.body else None}")
    print(f"----------------------")

# --- CONFIGURATION ---
def configure_mirror_builder(domain: str, output_root: Path, mirror_external: bool = True):
    """Configure the mirror builder with dynamic domain and output path"""
    global DOMAIN, OUTPUT_ROOT, MIRROR_EXTERNAL_ASSETS
    DOMAIN = domain
    OUTPUT_ROOT = output_root
    MIRROR_EXTERNAL_ASSETS = mirror_external
    print(f"Configured mirror builder: domain={domain}, output={output_root}, external_assets={mirror_external}")

async def build_mirror_for_domain(domain: str, output_root: Path, mirror_external: bool = True) -> Path:
    """
    Public API function for the MirrorBuilder to call
    
    Args:
        domain: The domain being mirrored (e.g., 'commbank.com.au')
        output_root: Path where crawled pages are stored
        mirror_external: Whether to download external CDN assets (default: True)
        
    Returns:
        Path to the generated mirror root
    """
    await main(domain=domain, output_root=output_root, mirror_external=mirror_external)
    return OUTPUT_ROOT

# --- MAIN BUILD ---
async def main(domain: str = "nab.com.au", output_root: Path = None, mirror_external: bool = True):
    # Configure the builder with dynamic parameters
    if output_root is None:
        output_root = Path("output") / domain.replace("www.", "").replace(".", "_")
    
    configure_mirror_builder(domain, output_root, mirror_external)
    
    # Build robots
    robots = build_robots(f"https://{DOMAIN}/")

    # Collect crawled pages
    page_map = collect_pages()  # canon_url -> Path(dir)
    if not page_map:
        print(f"No crawled pages found under {OUTPUT_ROOT}/. Run your crawler first.")
        return
    print(f"Found {len(page_map)} crawled pages.")

    # First pass: gather every asset URL we want
    asset_urls: set[str] = set()
    forced_css: set[str] = set()   # URLs we must fetch as CSS even if no .css ext
    page_html: dict[Path, tuple[str, BeautifulSoup]] = {}  # dir -> (url, soup)

    for canon_url, page_dir in page_map.items():
        # PREFER RENDERED HTML: Use Crawl4AI's rendered.html (Playwright output) over raw.html
        rendered_html = (page_dir / "index.html")
        raw_html = (page_dir / "raw.html")
        
        print(f"🔍 Checking {rendered_html} - exists: {rendered_html.exists()}")
        print(f"🔍 Checking {raw_html} - exists: {raw_html.exists()}")
        
        # Priority order: rendered > hybrid > raw
        if rendered_html.exists():
            if raw_html.exists():
                # Hybrid approach: merge <head> from raw + <body> from rendered 
                html = create_hybrid_html(raw_html, rendered_html)
                print(f"🔀 Using hybrid HTML (raw head + rendered body) for {canon_url}")
            else:
                # Pure rendered HTML (best for JS-heavy sites)
                html = rendered_html.read_text(encoding="utf-8", errors="ignore")
                print(f"✅ Using rendered HTML (post-JS) for {canon_url}")
        elif raw_html.exists():
            html = raw_html.read_text(encoding="utf-8", errors="ignore")
            print(f"⚠️  Using raw HTML (pre-JS fallback) for {canon_url}")
        else:
            print(f"❌ No HTML files found in {page_dir}")
            continue
        # Strip analytics before asset discovery to avoid queuing their bundles
        soup = BeautifulSoup(html, "html.parser")
        strip_analytics_scripts(soup)  # Remove tracking scripts early
        
        page_html[page_dir] = (canon_url, soup)

        def want(u: str | None):
            if not u:
                return
            if (MIRROR_EXTERNAL_ASSETS or is_same_site(u)) and is_asset(u):
                asset_urls.add(u)

        # collect from <link> - enhanced for /etc/clientlibs/ and AEM assets
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
            # Force download AEM/CMS assets even if not typical extensions
            elif any(pattern in u for pattern in ['/etc.clientlibs/', '/etc/clientlibs/', '/content/dam/', '/etc/designs/']):
                asset_urls.add(u)
                # If it smells like CSS but has no extension, force it
                if ('css' in u.lower() or 'style' in u.lower() or 'clientlib' in u.lower()):
                    forced_css.add(u)
                    if u.startswith("https://www.commbank.com.au/etc") or "/etc.clientlibs/" in u:
                        print(f"🎯 AEM CSS queued: {u}")
            else:
                want(u)

        # collect from <script src>
        for s in soup.find_all("script", src=True):
            u = absolutize(canon_url, s["src"])
            want(u)

        # images/media - collect both src and lazy data-src attributes
        for tag in soup.find_all(["img","source","video","audio","iframe"]):
            # Regular src attribute
            if tag.get("src"):
                u = absolutize(canon_url, tag["src"])
                want(u)
            
            # Lazy loading attributes - discover before downloading
            lazy_attrs = ['data-src', 'data-lazy-src', 'data-original', 
                         'data-image-desktop-src', 'data-image-mobile-src', 
                         'data-lazy', 'data-echo', 'data-unveil']
            
            for attr in lazy_attrs:
                lazy_src = tag.get(attr)
                if lazy_src:
                    u = absolutize(canon_url, lazy_src)
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
                (url in forced_css) or  # stylesheets we force-fetch even without .css
                # Always mirror AEM/CMS assets regardless of robots.txt
                any(pattern in purl.path for pattern in ['/etc.clientlibs/', '/etc/clientlibs/', '/content/dam/', '/etc/designs/'])
            )

            # Apply robots.txt only to same-site URLs that are NOT exempt
            if robots and is_same_site(url) and not robots_exempt:
                try:
                    if not robots.can_fetch(headers["User-Agent"], url):
                        print(f" robots.txt disallows asset: {url}")
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

        # 1) unblock/cleanup first (safe to run before rewrites)
        fix_adobe_blocking_styles(soup)
        fix_adobe_target_mbox(soup)
        remove_anti_flicker_styles(soup)

        # 2) normalize lazy media BEFORE we rewrite URLs
        normalize_lazy_loaded_media(soup)

        # 2.5) Convert CSS preloads to stylesheets and add JS-enabled classes
        convert_css_preloads_to_stylesheets(soup)
        add_js_enabled_classes(soup)

        # 3) now rewrite HTML to local assets/links (uses the newly-set src/srcset)
        rewrite_html(canon_url, page_dir, soup, page_map, asset_map)

        # 3.5) Add base href for relative URL resolution
        add_base_href(soup)

        # 4) generic layout polish (optional)
        fix_spa_layout_issues(soup)
        add_site_specific_fixes(soup, DOMAIN)
        disable_overlay_javascript(soup)
        
        # TODO: Add AI features injection here when ready for development
        # inject_ai_features(soup)  # Searchbar + chatbot components
        
        # 5) Generate mirror report for debugging
        mirror_report(canon_url, page_dir, soup)
        
        # Final optimizations before saving
        # Convert preload to stylesheet
        for l in soup.find_all("link"):
            rel = (l.get("rel") or [])
            if "preload" in rel and (l.get("as") or "").lower()=="style":
                l["rel"] = ["stylesheet"]; l.attrs.pop("as", None)
        
        # Force JS classes
        for node in (soup.html, soup.body):
            if node:
                node["class"] = list(set((node.get("class") or []) + ["js","js-enabled"]))
        
        # Add base href
        if soup.head and not soup.head.find("base"):
            soup.head.insert(0, soup.new_tag("base", href="./"))
        
        out = page_dir / "index.html"
        out.write_text(str(soup), encoding="utf-8")
        pages_written += 1

    print(f"✅ Wrote {pages_written} HTML pages with local links.")
    
    # Fix root_index computation
    if page_map:
        first_dir = list(page_map.values())[0]
        root_index = first_dir / "index.html"
        print(f"Open: {root_index}")
        print("Tip: serve via a tiny HTTP server for best results:")
        print(f"    cd {OUTPUT_ROOT} && python -m http.server 8000")
    else:
        print("No pages to display")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python build_static_mirror.py <output_path> <domain> [--no-external]")
        print("Example: python build_static_mirror.py ./output/commbank.com.au commbank.com.au")
        print("         python build_static_mirror.py ./output/commbank.com.au commbank.com.au --no-external")
        sys.exit(1)
    
    output_path = Path(sys.argv[1])
    domain = sys.argv[2]
    mirror_external = '--no-external' not in sys.argv
    
    # Configure the builder with command line arguments
    configure_mirror_builder(domain, output_path, mirror_external)
    
    asyncio.run(main(domain, output_path, mirror_external))
