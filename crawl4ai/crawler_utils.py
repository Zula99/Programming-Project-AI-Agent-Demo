# crawler_utils.py - Reusable web crawling utilities
import os
import re
import time
import json
import urllib.parse
import urllib.robotparser as robotparser
from collections import deque
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass

# Enable long paths on Windows
if os.name == 'nt':
    try:
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel32.SetProcessDEPPolicy.argtypes = [wintypes.DWORD]
        kernel32.SetProcessDEPPolicy.restype = wintypes.BOOL
    except:
        pass  # Ignore if not available

try:
    from bs4 import BeautifulSoup
    HAVE_BS4 = True
except Exception:
    HAVE_BS4 = False

from crawl4ai import AsyncWebCrawler

@dataclass
class CrawlConfig:
    """Configuration for web crawling"""
    domain: str
    output_root: Path
    max_pages: int = 100
    request_gap: float = 0.6
    user_agent: str = "Mozilla/5.0 (compatible; Crawl4AI-Agent/1.0)"
    respect_robots: bool = True
    start_url: Optional[str] = None

# URL helpers
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

def is_same_site(url: str, domain: str) -> bool:
    """Check if URL belongs to the specified domain"""
    try:
        host = urllib.parse.urlsplit(url).netloc.lower()
        return host.endswith(domain)
    except Exception:
        return False

BINARY_EXTENSIONS = (
    ".png",".jpg",".jpeg",".gif",".webp",".svg",".pdf",".zip",".rar",".7z",
    ".mp4",".mov",".avi",".mp3",".wav",".ogg",".webm",".ico",".dmg",".exe",
    ".css",".js",".mjs",".json",".xml",".txt",".csv"
)

def looks_binary(url: str) -> bool:
    """Check if URL points to a binary file"""
    path = urllib.parse.urlsplit(url).path.lower()
    return any(path.endswith(ext) for ext in BINARY_EXTENSIONS)

def is_demo_worthy_url(url: str) -> tuple[bool, str]:
    """
    Check if URL is worth including in demo site
    
    Returns:
        (is_worthy, reason_if_not)
    """
    parsed = urllib.parse.urlsplit(url)
    path = parsed.path.lower()
    query = parsed.query.lower()
    
    # Check path length (likely auto-generated if too long)
    if len(path) > 120:
        return False, "path_too_long"
    
    # Check query string complexity (tracking/session URLs)
    if len(query) > 100:
        return False, "complex_query"
    
    # Skip obvious non-content paths
    skip_path_patterns = [
        '/api/', '/cgi-bin/', '/internal/', '/admin/', '/_',
        '/tracking/', '/analytics/', '/pixel/', '/beacon/',
        '/download/', '/pdf/', '/export/', '/print/',
        '/ajax/', '/json/', '/xml/', '/rss/', '/feed/',
        '/oauth/', '/auth/', '/login/', '/logout/', '/session/',
        '/forms/submit/', '/handlers/', '/processors/'
    ]
    
    for pattern in skip_path_patterns:
        if pattern in path:
            return False, "non_content_path"
    
    # Skip tracking/analytics query parameters
    skip_query_patterns = [
        'utm_', 'gclid=', 'fbclid=', '_ga=', '_gl=',
        'session=', 'token=', 'auth=', 'key=',
        'timestamp=', 'cache=', 'v=', 'version='
    ]
    
    for pattern in skip_query_patterns:
        if pattern in query:
            return False, "tracking_params"
    
    # Skip file extensions that aren't useful for demos
    useless_extensions = [
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.zip', '.rar', '.tar', '.gz', '.exe', '.dmg', '.msi',
        '.xml', '.json', '.csv', '.txt', '.log', '.tmp'
    ]
    
    for ext in useless_extensions:
        if path.endswith(ext):
            return False, "useless_file_type"
    
    # Skip overly complex URLs (likely generated)
    path_segments = [s for s in path.split('/') if s]
    if len(path_segments) > 8:  # Very deep nesting
        return False, "too_deep_nesting"
    
    # Skip URLs with too many special characters (likely generated)
    special_char_count = sum(1 for c in path if c in '-_=&%?#')
    if special_char_count > 15:
        return False, "too_many_special_chars"
    
    return True, ""

def to_abs(base: str, href: str | None) -> str | None:
    """Convert relative URL to absolute"""
    if not href:
        return None
    if href.startswith(("mailto:", "tel:", "javascript:", "#")):
        return None
    u = urllib.parse.urljoin(base, href)
    return url_canon(u)

# Folder-style slugify
_invalid = re.compile(r"[^a-z0-9._-]+")

def path_slug(url: str, output_root: Path) -> Path:
    """
    Map a URL to a folder structure with Windows path length protection:
    
    https://example.com/                   -> output/example.com/index.md
    https://example.com/page               -> output/example.com/page/index.md
    https://example.com/page?x=1           -> output/example.com/page/_q_x=1/index.md
    """
    parts = urllib.parse.urlsplit(url)
    host = parts.netloc.lower()
    path = parts.path

    if not path or path == "/":
        segments = []
    else:
        segments = [s for s in path.split("/") if s]

    # sanitise each segment with shorter limits for Windows
    segments = [_invalid.sub("-", s.lower()).strip("-")[:40] for s in segments]

    # encode query if present (shorter for Windows)
    if parts.query:
        q = urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
        q.sort()
        qstr = "&".join([f"{_invalid.sub('-', k.lower())}={_invalid.sub('-', v.lower())}" for k, v in q])[:60]
        segments.append(f"_q_{qstr}")

    # compose final path: output_root/<host>/<segments...>/
    final_dir = output_root / host
    for s in segments:
        final_dir = final_dir / s
    
    return final_dir

def extract_links(html: str, base_url: str) -> Set[str]:
    """Extract all links from HTML content"""
    links: Set[str] = set()
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

@dataclass
class CrawlResult:
    """Result of crawling a single page"""
    url: str
    success: bool
    raw_html: str = ""
    markdown: str = ""
    title: str = ""
    content_type: str = ""
    links: Set[str] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.links is None:
            self.links = set()

async def crawl_page(crawler: AsyncWebCrawler, url: str, config: CrawlConfig) -> CrawlResult:
    """Crawl a single page and return structured results"""
    try:
        if config.request_gap > 0:
            time.sleep(config.request_gap)
            
        result = await crawler.arun(url)
        
        # Extract content
        raw_html = getattr(result, "raw_html", None) or getattr(result, "html", None) or ""
        content_md = getattr(result, "markdown", None) or getattr(result, "clean_text", "") or ""
        title = getattr(result, "title", "") or ""
        content_type = getattr(result, "content_type", "") or ""
        
        # Extract links
        links = extract_links(raw_html, url)
        
        return CrawlResult(
            url=url,
            success=True,
            raw_html=raw_html,
            markdown=content_md,
            title=title,
            content_type=content_type,
            links=links
        )
        
    except Exception as e:
        return CrawlResult(
            url=url,
            success=False,
            error=str(e)
        )

def save_crawl_result(result: CrawlResult, config: CrawlConfig) -> Optional[Path]:
    """Save crawl result to filesystem in organized structure"""
    try:
        folder = path_slug(result.url, config.output_root)
        folder.mkdir(parents=True, exist_ok=True)
        
        md_path = folder / "index.md"
        meta_path = folder / "meta.json"
        html_path = folder / "raw.html"
        
        # Write files
        with md_path.open("w", encoding="utf-8") as f:
            f.write(result.markdown)
        
        if result.raw_html:
            with html_path.open("w", encoding="utf-8") as f:
                f.write(result.raw_html)
        
        meta = {
            "url": result.url,
            "title": result.title,
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "content_type": result.content_type,
            "bytes_html": len(result.raw_html) if result.raw_html else 0,
            "success": result.success,
            "error": result.error
        }
        
        with meta_path.open("w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        
        return md_path
        
    except Exception as e:
        print(f"  Error saving {result.url}: {e} - skipping")
        return None

def setup_robots_parser(start_url: str) -> robotparser.RobotFileParser:
    """Setup and load robots.txt parser"""
    rp = robotparser.RobotFileParser()
    rp.set_url(urllib.parse.urljoin(start_url, "/robots.txt"))
    try:
        rp.read()
    except Exception:
        pass  # if robots fails to load, we proceed
    return rp

async def generic_crawl(config: CrawlConfig) -> Tuple[List[CrawlResult], Dict[str, Any]]:
    """
    Generic web crawler that can be configured for any domain with smart URL filtering
    
    Returns:
        results: List of crawl results
        stats: Dictionary with crawling statistics including filtering metrics
    """
    config.output_root.mkdir(parents=True, exist_ok=True)
    
    start_url = config.start_url or f"https://www.{config.domain}/"
    
    # Setup robots.txt if respecting it
    rp = None
    if config.respect_robots:
        rp = setup_robots_parser(start_url)
    
    q = deque([url_canon(start_url)])
    seen: Set[str] = set()
    results: List[CrawlResult] = []
    pages_crawled = 0
    
    # Track filtering stats
    filtered_urls = {
        "path_too_long": 0,
        "complex_query": 0,
        "non_content_path": 0,
        "tracking_params": 0,
        "useless_file_type": 0,
        "too_deep_nesting": 0,
        "too_many_special_chars": 0,
        "robots_blocked": 0,
        "binary_files": 0,
        "external_domains": 0
    }
    
    total_urls_discovered = 0
    
    async with AsyncWebCrawler(user_agent=config.user_agent) as crawler:
        while q and pages_crawled < config.max_pages:
            url = q.popleft()
            if url in seen:
                continue
            seen.add(url)
            
            # Check domain
            if not is_same_site(url, config.domain):
                filtered_urls["external_domains"] += 1
                continue
                
            # Check binary files
            if looks_binary(url):
                filtered_urls["binary_files"] += 1
                continue
            
            # Smart URL filtering
            is_worthy, filter_reason = is_demo_worthy_url(url)
            if not is_worthy:
                filtered_urls[filter_reason] += 1
                print(f"  ⏭️  Skipped {url} ({filter_reason})")
                continue
            
            # Check robots.txt if enabled
            if rp and config.respect_robots:
                try:
                    if not rp.can_fetch(config.user_agent, url):
                        filtered_urls["robots_blocked"] += 1
                        continue
                except Exception:
                    pass
            
            # Crawl the page
            result = await crawl_page(crawler, url, config)
            results.append(result)
            
            if result.success:
                pages_crawled += 1
                
                # Save result
                saved_path = save_crawl_result(result, config)
                if saved_path:
                    print(f" [{pages_crawled}/{config.max_pages}] {url} -> {saved_path.name}")
                else:
                    print(f" [{pages_crawled}/{config.max_pages}] {url} -> [save failed]")
                
                # Queue new links with filtering
                all_links = list(result.links)
                total_urls_discovered += len(all_links)
                
                # Filter and queue links
                worthy_links = []
                for link_url in all_links:
                    if link_url in seen:
                        continue
                        
                    if not is_same_site(link_url, config.domain):
                        continue
                        
                    if looks_binary(link_url):
                        continue
                        
                    is_worthy, _ = is_demo_worthy_url(link_url)
                    if is_worthy:
                        worthy_links.append(link_url)
                
                # Add to queue
                new_queued = 0
                for u in worthy_links:
                    if u not in q:
                        q.append(u)
                        new_queued += 1
                        
                print(f"   ↳ found {len(all_links)} links, queued {new_queued} worthy ones (queue: {len(q)})")
            else:
                print(f"  ❌ Error on {url}: {result.error}")
    
    # Calculate filtering statistics
    total_filtered = sum(filtered_urls.values())
    quality_ratio = pages_crawled / (pages_crawled + total_filtered) if (pages_crawled + total_filtered) > 0 else 0
    
    stats = {
        "pages_crawled": pages_crawled,
        "total_urls_seen": len(seen),
        "total_urls_discovered": total_urls_discovered,
        "successful_crawls": len([r for r in results if r.success]),
        "failed_crawls": len([r for r in results if not r.success]),
        "queue_remaining": len(q),
        "filtered_urls": filtered_urls,
        "total_filtered": total_filtered,
        "url_quality_ratio": quality_ratio,
        "filtering_efficiency": total_filtered / total_urls_discovered if total_urls_discovered > 0 else 0
    }
    
    print(f"Done. Crawled {pages_crawled} quality page(s), filtered {total_filtered} junk URLs")
    print(f"URL Quality Ratio: {quality_ratio:.1%} (higher is better)")
    print(f"Output in: {config.output_root.resolve()}")
    
    return results, stats