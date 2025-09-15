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
import asyncio
import logging

# AI Classification imports (now in same directory)
try:
    from ai_content_classifier import AIContentClassifier, HeuristicClassifier, ClassificationResult
    from ai_config import get_ai_config
    AI_AVAILABLE = True
except ImportError as e:
    AI_AVAILABLE = False
    print(f"AI classification not available: {e}")

# Quality Plateau Detection
try:
    from quality_plateau import HybridQualityMonitor, QualityMetrics as PlateauQualityMetrics
    PLATEAU_AVAILABLE = True
except ImportError as e:
    PLATEAU_AVAILABLE = False
    print(f"Quality plateau detection not available: {e}")

# Content Deduplication System
try:
    from content_deduplicator import ContentDeduplicator
    DEDUPLICATION_AVAILABLE = True
except ImportError as e:
    DEDUPLICATION_AVAILABLE = False
    print(f"Content deduplication not available: {e}")

# Coverage tracking integration
try:
    from websocket_manager import notify_page_crawled, notify_urls_discovered
    from dashboard_metrics import get_coverage_calculator
    COVERAGE_TRACKING_AVAILABLE = True
except ImportError as e:
    COVERAGE_TRACKING_AVAILABLE = False
    print(f"Coverage tracking not available: {e}")

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

def _get_site_specific_thresholds(site_type):
    """
    Map BusinessSiteType to quality plateau thresholds
    All 13 site types from ai_content_classifier.py with appropriate settings
    """
    from ai_content_classifier import BusinessSiteType
    
    # VERY PERMISSIVE - Product/content rich sites that want comprehensive coverage
    if site_type == BusinessSiteType.ECOMMERCE:
        return {
            'quality_window_size': 25,      # Larger window for product variety
            'worthy_threshold': 0.15,       # Only 15% worthy needed (very low)
            'diversity_threshold': 0.95,    # 95% similarity to stop (very high)
            'diversity_window_size': 20     # Check more pages for diversity
        }
    elif site_type == BusinessSiteType.RESTAURANT:
        return {
            'quality_window_size': 20,
            'worthy_threshold': 0.2,        # Most restaurant content is valuable
            'diversity_threshold': 0.9,     # Menu items can be similar
            'diversity_window_size': 15
        }
    elif site_type == BusinessSiteType.REAL_ESTATE:
        return {
            'quality_window_size': 25,
            'worthy_threshold': 0.2,        # Property listings are valuable
            'diversity_threshold': 0.9,     # Properties can be similar
            'diversity_window_size': 18
        }
    
    # MODERATELY PERMISSIVE - Professional content sites
    elif site_type == BusinessSiteType.HEALTHCARE:
        return {
            'quality_window_size': 20,
            'worthy_threshold': 0.25,       # Medical content should be quality
            'diversity_threshold': 0.85,    # Allow some similar health topics
            'diversity_window_size': 15
        }
    elif site_type == BusinessSiteType.EDUCATIONAL:
        return {
            'quality_window_size': 22,
            'worthy_threshold': 0.25,       # Academic content variety important
            'diversity_threshold': 0.85,    # Courses/programs can be similar
            'diversity_window_size': 16
        }
    elif site_type == BusinessSiteType.LEGAL:
        return {
            'quality_window_size': 18,
            'worthy_threshold': 0.3,        # Legal content should be substantial
            'diversity_threshold': 0.85,    # Practice areas can overlap
            'diversity_window_size': 14
        }
    elif site_type == BusinessSiteType.TECHNOLOGY:
        return {
            'quality_window_size': 22,
            'worthy_threshold': 0.2,        # Tech content often valuable (bias toward inclusion)
            'diversity_threshold': 0.85,    # Products/solutions can be similar
            'diversity_window_size': 16
        }
    elif site_type == BusinessSiteType.NON_PROFIT:
        return {
            'quality_window_size': 20,
            'worthy_threshold': 0.25,       # Mission-driven content important
            'diversity_threshold': 0.8,     # Programs/initiatives should be diverse
            'diversity_window_size': 15
        }
    
    # BALANCED - Standard business content
    elif site_type == BusinessSiteType.BANKING:
        return {
            'quality_window_size': 20,
            'worthy_threshold': 0.3,        # Financial content needs quality
            'diversity_threshold': 0.8,     # Standard similarity threshold
            'diversity_window_size': 15
        }
    elif site_type == BusinessSiteType.CORPORATE:
        return {
            'quality_window_size': 18,
            'worthy_threshold': 0.3,        # Professional corporate content
            'diversity_threshold': 0.8,     # Business content should vary
            'diversity_window_size': 14
        }
    elif site_type == BusinessSiteType.GOVERNMENT:
        return {
            'quality_window_size': 20,
            'worthy_threshold': 0.3,        # Government services should be quality
            'diversity_threshold': 0.8,     # Services should be diverse
            'diversity_window_size': 15
        }
    
    # HIGHER STANDARDS - Content/editorial sites
    elif site_type == BusinessSiteType.NEWS:
        return {
            'quality_window_size': 18,
            'worthy_threshold': 0.4,        # News should be engaging
            'diversity_threshold': 0.7,     # Articles can be topically similar
            'diversity_window_size': 12
        }
    elif site_type == BusinessSiteType.ENTERTAINMENT:
        return {
            'quality_window_size': 20,
            'worthy_threshold': 0.35,       # Entertainment should be engaging
            'diversity_threshold': 0.75,    # Content can have similar themes
            'diversity_window_size': 14
        }
    
    # DEFAULT - Unknown or unmatched site types
    else:  # BusinessSiteType.UNKNOWN or any new types
        return {
            'quality_window_size': 20,
            'worthy_threshold': 0.3,        # Balanced default
            'diversity_threshold': 0.8,     # Standard similarity threshold
            'diversity_window_size': 15
        }

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
    # Browser configuration for JS-heavy sites
    timeout: int = 30
    wait_for: str = 'networkidle'  # 'networkidle', 'domcontentloaded', 'load'
    additional_wait: float = 0.0  # Extra wait after wait_for condition (for heavy JS)
    headless: bool = True
    screenshot: bool = False
    # Cost tracking
    cost_tracker: Optional[Any] = None  # CostTracker instance for AI cost monitoring
    javascript: bool = True
    max_concurrent: int = 5
    # Content deduplication settings
    enable_deduplication: bool = True
    dedup_similarity_threshold: float = 0.85  # 85% similarity threshold
    dedup_min_content_length: int = 100  # Minimum content length to analyze
    # Anti-detection features
    stealth_mode: bool = False
    realistic_viewport: bool = True
    # Coverage tracking integration
    run_id: Optional[str] = None  # Run ID for real-time coverage monitoring
    classification_cache: Optional[Dict] = None  # Session-scoped classification cache
    extra_headers: dict = None
    # Enhanced JS rendering features
    wait_for_selector: Optional[str] = None  # CSS selector to wait for
    selector_timeout: int = 10000  # Timeout for selector wait (ms)
    auto_scroll: bool = False  # Auto-scroll to trigger lazy loading
    scroll_delay: int = 1000  # Delay between scroll actions (ms)
    post_load_delay: int = 0  # Extra delay after all loading (ms)
    js_code: Optional[List[str]] = None  # JavaScript code to execute
    # Cost tracking
    cost_tracker: Optional[object] = None  # CostTracker instance for AI cost monitoring
    # Classification cache for avoiding duplicate AI calls
    classification_cache: Optional[dict] = None  # Session cache for AI classifications

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
    
    # Check for extremely long paths (likely auto-generated/spam)
    if len(path) > 300:  # Much more generous limit for business URLs
        return False, "path_too_long"
    
    # Check query string complexity (tracking/session URLs)
    if len(query) > 100:
        return False, "complex_query"
    
    # Skip technical/backend paths (but allow business content)
    skip_path_patterns = [
        '/api/', '/cgi-bin/', '/internal/', '/admin/', '/_',
        '/tracking/', '/analytics/', '/pixel/', '/beacon/',
        '/ajax/', '/json/', '/xml/', '/rss/', '/feed/',
        '/oauth/', '/auth/', '/login/', '/logout/', '/session/',
        '/forms/submit/', '/handlers/', '/processors/',
        # Keep: /download/, /pdf/, /export/, /print/ - these might have business value
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
    # Keep: .pdf (might have valuable business docs), .doc/.docx, .ppt/.pptx (business content)
    useless_extensions = [
        '.zip', '.rar', '.tar', '.gz', '.exe', '.dmg', '.msi',
        '.xml', '.json', '.csv', '.log', '.tmp', '.bak',
        # Technical files
        '.js.map', '.css.map', '.woff', '.woff2', '.eot', '.ttf'
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

# AI-Enhanced Classification Functions

_ai_classifier = None  # Global classifier instance
_logger = logging.getLogger(__name__)

def get_ai_classifier() -> Optional[AIContentClassifier]:
    """Get or create the global AI classifier instance"""
    global _ai_classifier
    if not AI_AVAILABLE:
        return None
        
    if _ai_classifier is None:
        try:
            config = get_ai_config()
            _ai_classifier = AIContentClassifier(
                api_key=config.openai_api_key or config.anthropic_api_key,
                model=config.preferred_model
            )
        except Exception as e:
            _logger.warning(f"Could not initialize AI classifier: {e}")
            return None
    
    return _ai_classifier

async def is_demo_worthy_url_ai(url: str, content: str = "", title: str = "", cost_tracker=None, classification_cache=None) -> tuple[bool, str, dict]:
    """
    AI-enhanced URL worthiness check with fallback to heuristics and session cache
    
    Args:
        url: URL to classify
        content: Page content (if available)
        title: Page title (if available)
        cost_tracker: Cost tracking instance
        classification_cache: Session cache dict to avoid duplicate classifications
    
    Returns:
        (is_worthy, reason, classification_details)
    """
    # Check classification cache first (avoid duplicate AI calls)
    if classification_cache and url in classification_cache:
        cached_result = classification_cache[url]
        _logger.debug(f"Session cache hit for {url}: {'WORTHY' if cached_result['is_worthy'] else 'NOT WORTHY'}")
        return cached_result['is_worthy'], cached_result['reasoning'], cached_result['details']
    
    classification_details = {
        'method': 'unknown',
        'confidence': 0.0,
        'reasoning': '',
        'ai_available': AI_AVAILABLE
    }
    
    # First, check basic technical filters (these are still useful)
    basic_worthy, basic_reason = is_demo_worthy_url(url)
    if not basic_worthy:
        classification_details.update({
            'method': 'basic_filter',
            'confidence': 0.9,
            'reasoning': f'Failed basic filter: {basic_reason}'
        })
        result = (False, basic_reason, classification_details)
        
        # Cache basic filter results too
        if classification_cache is not None:
            classification_cache[url] = {
                'is_worthy': False,
                'reasoning': basic_reason,
                'details': classification_details
            }
        
        return result
    
    # Try AI classification if available
    ai_classifier = get_ai_classifier()
    if ai_classifier:
        try:
            result: ClassificationResult = await ai_classifier.classify_content(url, content, title)
            
            # Track costs if cost_tracker provided
            if cost_tracker:
                content_length = len(content + title)
                cost_tracker.track_classification(url, result, content_length)
            
            classification_details.update({
                'method': result.method_used,
                'confidence': result.confidence,
                'reasoning': result.reasoning
            })
            
            final_result = (result.is_worthy, result.reasoning if not result.is_worthy else "", classification_details)
            
            # Cache AI classification result in session cache (takes priority)
            if classification_cache is not None:
                classification_cache[url] = {
                    'is_worthy': result.is_worthy,
                    'reasoning': result.reasoning if not result.is_worthy else "",
                    'details': classification_details
                }
                _logger.debug(f"Cached classification for {url}: {'WORTHY' if result.is_worthy else 'NOT WORTHY'}")
            
            return final_result
            
        except Exception as e:
            _logger.warning(f"AI classification failed for {url}: {e}")
            # Fall through to heuristic
    
    # Fallback to enhanced heuristic (better than just basic filters)
    if AI_AVAILABLE:
        try:
            heuristic_classifier = HeuristicClassifier()
            result = heuristic_classifier.classify(url, content, title)
            classification_details.update({
                'method': result.method_used,
                'confidence': result.confidence,
                'reasoning': result.reasoning
            })
            
            final_result = (result.is_worthy, result.reasoning if not result.is_worthy else "", classification_details)
            
            # Cache heuristic classification result
            if classification_cache is not None:
                classification_cache[url] = {
                    'is_worthy': result.is_worthy,
                    'reasoning': result.reasoning if not result.is_worthy else "",
                    'details': classification_details
                }
            
            return final_result
            
        except Exception as e:
            _logger.warning(f"Heuristic classification failed for {url}: {e}")
    
    # Final fallback to basic filters (already passed above)
    classification_details.update({
        'method': 'basic_only',
        'confidence': 0.7,
        'reasoning': 'Only basic filtering applied'
    })
    
    final_result = (True, "", classification_details)
    
    # Cache fallback result
    if classification_cache is not None:
        classification_cache[url] = {
            'is_worthy': True,
            'reasoning': "",
            'details': classification_details
        }
    
    return final_result

def is_demo_worthy_url_sync(url: str, content: str = "", title: str = "") -> tuple[bool, str]:
    """
    Synchronous version of AI-enhanced URL worthiness check
    Uses heuristics only (no async AI calls)
    """
    # Basic technical filters first
    basic_worthy, basic_reason = is_demo_worthy_url(url)
    if not basic_worthy:
        return False, basic_reason
    
    # Try enhanced heuristic if available
    if AI_AVAILABLE:
        try:
            heuristic_classifier = HeuristicClassifier()
            result = heuristic_classifier.classify(url, content, title)
            # Return simple reason for worthy URLs, full reasoning for filtered URLs
            if result.is_worthy:
                return True, ""
            else:
                # Extract just the key reason, not the full "Heuristic: ..." text
                reason = result.reasoning.replace("Heuristic: ", "").split(";")[0].split(",")[0]
                # Don't return generic messages as filter reasons
                if "default scoring" in reason.lower() or not reason.strip():
                    reason = "filtered"
                return False, reason
        except Exception as e:
            _logger.warning(f"Heuristic classification failed for {url}: {e}")
    
    # Fallback to basic (already passed)
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
    ai_classification: Optional[Dict[str, Any]] = None
    html_type: str = "raw"  # "raw" or "rendered"
    
    def __post_init__(self):
        if self.links is None:
            self.links = set()

async def crawl_page(crawler: AsyncWebCrawler, url: str, config: CrawlConfig, cost_tracker=None, classification_cache=None) -> CrawlResult:
    """Crawl a single page and return structured results"""
    try:
        if config.request_gap > 0:
            time.sleep(config.request_gap)
            
        # Configure page-level settings for JS-heavy sites
        arun_kwargs = {
            'timeout': config.timeout * 1000,  # Convert to milliseconds
            'wait_for': config.wait_for,
            'screenshot': config.screenshot,
            'extract_format': 'html'  # Force rendered HTML instead of markdown
        }
        
        # Add wait for specific selector if configured
        if config.wait_for_selector:
            arun_kwargs['wait_for_selector'] = config.wait_for_selector
            arun_kwargs['selector_timeout'] = config.selector_timeout
        
        # Add post-load delay for JS completion
        if config.post_load_delay > 0:
            arun_kwargs['post_load_delay'] = config.post_load_delay
        
        # Build JS code list for execution
        js_code_list = []
        
        # Add stealth mode if enabled
        if config.stealth_mode:
            stealth_js = """
            // Basic anti-detection measures
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-AU', 'en']});
            window.chrome = {runtime: {}};
            """
            js_code_list.append(stealth_js)
        
        # Add auto-scroll if enabled (triggers lazy loading)
        if config.auto_scroll:
            scroll_js = """
            // Auto-scroll to trigger lazy loading
            console.log('Starting auto-scroll for lazy loading...');
            
            // Scroll to bottom
            window.scrollTo(0, document.body.scrollHeight);
            await new Promise(r => setTimeout(r, {scroll_delay}));
            
            // Scroll to middle  
            window.scrollTo(0, document.body.scrollHeight / 2);
            await new Promise(r => setTimeout(r, {scroll_delay}));
            
            // Scroll back to top
            window.scrollTo(0, 0);
            await new Promise(r => setTimeout(r, {scroll_delay}));
            
            console.log('Auto-scroll complete');
            """.format(scroll_delay=config.scroll_delay)
            js_code_list.append(scroll_js)
        
        # Add custom JS code if provided
        if config.js_code:
            js_code_list.extend(config.js_code)
        
        # Set js_code if we have any
        if js_code_list:
            arun_kwargs['js_code'] = js_code_list
        
        # Filter out None values and invalid parameters
        arun_kwargs = {k: v for k, v in arun_kwargs.items() if v is not None}
        
        result = await crawler.arun(url, **arun_kwargs)
        
        # Additional wait for heavy JS apps (after networkidle)
        if config.additional_wait > 0:
            print(f"⏱️ Additional wait: {config.additional_wait}s for JS completion")
            await asyncio.sleep(config.additional_wait)
        
        # Extract content - prioritize rendered HTML over raw HTML for JS-heavy sites
        rendered_html = getattr(result, "html", None) or getattr(result, "cleaned_html", None)
        raw_html = getattr(result, "raw_html", None)
        
        # For JS-heavy sites, use rendered HTML if available, otherwise fall back to raw_html
        final_html = rendered_html if rendered_html else raw_html or ""
        
        content_md = getattr(result, "markdown", None) or getattr(result, "clean_text", "") or ""
        title = getattr(result, "title", "") or ""
        content_type = getattr(result, "content_type", "") or ""
        
        # Log which HTML we're using for debugging
        if rendered_html and rendered_html != raw_html:
            print(f" Using rendered HTML (post-JS) for {url}")
        else:
            print(f"  Using raw HTML (pre-JS) for {url}")
        
        # AI Content Classification - analyze actual page content
        ai_worthy = True  # default to worthy
        ai_reasoning = ""
        ai_confidence = 0.7
        
        if AI_AVAILABLE:
            try:
                # Use AI to classify the actual page content
                is_worthy, reason, details = await is_demo_worthy_url_ai(url, content_md, title, cost_tracker, classification_cache)
                ai_worthy = is_worthy
                ai_reasoning = details.get('reasoning', reason)
                ai_confidence = details.get('confidence', 0.7)
                
                # Log AI decisions for monitoring
                _logger.info(f"AI Classification: {url} -> {'WORTHY' if ai_worthy else 'FILTERED'} ({ai_confidence:.2f}) - {ai_reasoning[:100]}")
                
                # If AI says not worthy, skip this page entirely
                if not ai_worthy:
                    return CrawlResult(
                        url=url,
                        success=False,
                        error=f"AI classified as not demo-worthy: {ai_reasoning}",
                        ai_classification={'worthy': False, 'reasoning': ai_reasoning, 'confidence': ai_confidence}
                    )
                    
            except Exception as e:
                _logger.warning(f"AI classification failed for {url}: {e}, proceeding with content")
                # Continue with page if AI fails
        
        # Extract links from the final HTML (rendered if available)
        links = extract_links(final_html, url)
        
        return CrawlResult(
            url=url,
            success=True,
            raw_html=final_html,  # Use rendered HTML instead of raw
            markdown=content_md,
            title=title,
            content_type=content_type,
            links=links,
            ai_classification={'worthy': ai_worthy, 'reasoning': ai_reasoning, 'confidence': ai_confidence},
            html_type="rendered" if rendered_html and rendered_html != raw_html else "raw"
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
        raw_html_path = folder / "raw.html"
        rendered_html_path = folder / "index.html"
        
        # Write files
        with md_path.open("w", encoding="utf-8") as f:
            f.write(result.markdown)
        
        if result.raw_html:
            # Save to index.html for rendered content (post-JS)
            with rendered_html_path.open("w", encoding="utf-8") as f:
                f.write(result.raw_html)
            
            # Also save to raw.html for backwards compatibility
            with raw_html_path.open("w", encoding="utf-8") as f:
                f.write(result.raw_html)
        
        meta = {
            "url": result.url,
            "title": result.title,
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "content_type": result.content_type,
            "bytes_html": len(result.raw_html) if result.raw_html else 0,
            "html_type": result.html_type,
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
    
    # Configure crawler with browser settings for JS-heavy sites
    crawler_config = {
        'user_agent': config.user_agent,
        'headless': config.headless,
        'timeout': config.timeout
    }
    
    # Add JS-specific settings if needed
    if config.javascript:
        crawler_config['wait_for'] = config.wait_for
    
    # Add stealth mode settings  
    if config.stealth_mode:
        # Check for playwright-stealth availability
        try:
            import playwright_stealth
            _logger.info("Playwright-stealth available - enabling anti-detection")
            crawler_config.update({
                'viewport_width': 1920 if config.realistic_viewport else None,
                'viewport_height': 1080 if config.realistic_viewport else None,
                'stealth_mode': True  # Custom flag for our stealth implementation
            })
        except ImportError as e:
            _logger.warning(f"Playwright-stealth not available ({e}) - using basic anti-detection")
            crawler_config.update({
                'viewport_width': 1920 if config.realistic_viewport else None,
                'viewport_height': 1080 if config.realistic_viewport else None,
            })
    
    # Add extra headers for anti-detection
    if config.extra_headers:
        crawler_config['extra_headers'] = config.extra_headers
    
    # Initialize content deduplication system
    deduplicator = None
    if DEDUPLICATION_AVAILABLE and config.enable_deduplication:
        try:
            deduplicator = ContentDeduplicator(
                simhash_threshold=4,  # ~94% similarity threshold
                min_content_length=config.dedup_min_content_length
            )
            _logger.info(f"Content deduplication enabled (simhash threshold: 4 = ~94% similarity)")
        except Exception as e:
            _logger.warning(f"Could not initialize content deduplicator: {e}")
            deduplicator = None

    # Initialize quality plateau monitoring if available
    plateau_monitor = None
    if PLATEAU_AVAILABLE and AI_AVAILABLE:
        try:
            # Create AI classifier and site detector
            ai_config = get_ai_config()
            ai_classifier = AIContentClassifier(
                api_key=getattr(ai_config, 'openai_api_key', None),
                model=getattr(ai_config, 'model', 'gpt-4o-mini')
            )
            
            # Use existing BusinessSiteDetector for site type detection
            site_detector = ai_classifier.site_detector
            site_type = site_detector.detect_site_type(start_url, "", "")
            
            # Get site-specific quality thresholds
            thresholds = _get_site_specific_thresholds(site_type)
            
            plateau_monitor = HybridQualityMonitor(
                quality_window_size=thresholds['quality_window_size'],
                worthy_threshold=thresholds['worthy_threshold'],
                diversity_threshold=thresholds['diversity_threshold'],
                diversity_window_size=thresholds['diversity_window_size']
            )
            
            _logger.info(f"Quality plateau detection enabled for {site_type.value} site")
            _logger.info(f"Thresholds: worthy={thresholds['worthy_threshold']:.1%}, diversity={thresholds['diversity_threshold']:.1%}")
            
        except Exception as e:
            _logger.warning(f"Could not initialize quality plateau detection: {e}")
            plateau_monitor = None
    
    async with AsyncWebCrawler(**crawler_config) as crawler:
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
            
            # Smart URL filtering (enhanced with AI heuristics)
            is_worthy, filter_reason = is_demo_worthy_url_sync(url)
            if not is_worthy:
                filtered_urls[filter_reason] += 1
                print(f"  Skipped {url} ({filter_reason})")
                continue
            
            # Check robots.txt if enabled
            if rp and config.respect_robots:
                try:
                    if not rp.can_fetch(config.user_agent, url):
                        filtered_urls["robots_blocked"] += 1
                        continue
                except Exception:
                    pass
            
            # Crawl the page (pass cost tracker and classification cache if available)
            cost_tracker = getattr(config, 'cost_tracker', None)
            classification_cache = getattr(config, 'classification_cache', None)
            result = await crawl_page(crawler, url, config, cost_tracker, classification_cache)

            # Check for content duplication before processing
            is_duplicate = False
            duplicate_reason = ""
            if result.success and deduplicator:
                try:
                    is_duplicate, duplicate_reason = deduplicator.is_duplicate(
                        url=result.url,
                        content=result.markdown,
                        title=result.title
                    )

                    if is_duplicate:
                        print(f"  Skipped duplicate content: {url} ({duplicate_reason})")
                        # Still add to results for statistics but mark as filtered
                        result.error = f"duplicate_content: {duplicate_reason}"
                        result.success = False
                except Exception as e:
                    _logger.warning(f"Deduplication check failed for {url}: {e}")
                    # Continue processing if deduplication fails
            results.append(result)

            # Coverage tracking: Notify page crawled
            if COVERAGE_TRACKING_AVAILABLE and config.run_id:
                try:
                    # Get quality score if available (from AI classification)
                    quality_score = None
                    if hasattr(result, 'ai_classification') and result.ai_classification:
                        quality_score = result.ai_classification.get('confidence', None)
                    
                    await notify_page_crawled(config.run_id, url, result.success and not is_duplicate, quality_score)
                except Exception as e:
                    _logger.debug(f"Coverage tracking notification failed: {e}")

            if result.success and not is_duplicate:
                pages_crawled += 1

                # Save result
                saved_path = save_crawl_result(result, config)
                if saved_path:
                    print(f"\n [{pages_crawled}/{config.max_pages}] {url} -> {saved_path.name}")
                else:
                    print(f"\n [{pages_crawled}/{config.max_pages}] {url} -> [save failed]")
                
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
                        
                    is_worthy, _ = is_demo_worthy_url_sync(link_url)
                    if is_worthy:
                        worthy_links.append(link_url)
                
                # Add to queue
                new_queued = 0
                new_urls = []
                for u in worthy_links:
                    if u not in q:
                        q.append(u)
                        new_urls.append(u)
                        new_queued += 1
                        
                print(f"  found {len(all_links)} links, queued {new_queued} worthy ones (queue: {len(q)})")
                print()  # Add blank line after each crawl link processing
                
                # Coverage tracking: Notify new URLs discovered
                if COVERAGE_TRACKING_AVAILABLE and config.run_id and new_urls:
                    try:
                        await notify_urls_discovered(config.run_id, new_urls)
                    except Exception as e:
                        _logger.debug(f"Coverage tracking URL discovery notification failed: {e}")
                
                # Quality plateau monitoring and intelligent stopping
                if plateau_monitor:
                    try:
                        # Create quality metrics from AI classification
                        if result.ai_classification:
                            is_worthy = result.ai_classification.get('worthy', True)
                            confidence = result.ai_classification.get('confidence', 0.7)
                            reasoning = result.ai_classification.get('reasoning', 'AI classified as worthy')
                        else:
                            # Fallback: assume successful crawl is worthy
                            is_worthy = True
                            confidence = 0.6
                            reasoning = 'Successful crawl without AI classification'
                        
                        # Generate content hash for diversity monitoring
                        import hashlib
                        content_hash = hashlib.md5(result.markdown.encode()).hexdigest()
                        
                        # Create plateau quality metrics
                        plateau_quality = PlateauQualityMetrics(
                            is_worthy=is_worthy,
                            confidence_score=confidence,
                            reasoning=reasoning,
                            url=url
                        )
                        
                        # Update plateau monitor
                        plateau_monitor.assess_page(plateau_quality, content_hash)
                        
                        # Check if we should stop crawling
                        should_stop, stop_reason = plateau_monitor.should_stop_crawling()
                        
                        if should_stop:
                            _logger.info(f"🛑 Quality plateau detected: {stop_reason}")
                            print(f"\n🛑 Intelligent stopping: {stop_reason}")
                            print(f"   Crawled {pages_crawled} pages with sufficient quality coverage")
                            break  # Exit the crawling loop
                        else:
                            # Log quality status every 10 pages
                            if pages_crawled % 10 == 0:
                                stats = plateau_monitor.get_comprehensive_stats()
                                _logger.info(f"📊 Quality check at page {pages_crawled}: {stats['recent_worthy_ratio']:.1%} recent quality")
                                
                    except Exception as e:
                        _logger.warning(f"Quality plateau monitoring failed for {url}: {e}")
                        # Continue crawling even if plateau monitoring fails
                        
            else:
                print(f"  Error on {url}: {result.error}")
    
    # Calculate filtering statistics
    total_filtered = sum(filtered_urls.values())
    quality_ratio = pages_crawled / (pages_crawled + total_filtered) if (pages_crawled + total_filtered) > 0 else 0
    
    # Include deduplication statistics if available
    deduplication_stats = {}
    if deduplicator:
        try:
            deduplication_stats = deduplicator.get_deduplication_summary()
            print(f"Content deduplication summary: {deduplication_stats['duplicate_rate']} duplicates filtered")
            print(f"  Breakdown: {deduplication_stats['breakdown']['exact_duplicates']} exact, {deduplication_stats['breakdown']['url_pattern_duplicates']} URL pattern, {deduplication_stats['breakdown']['text_similarity_duplicates']} text similarity, {deduplication_stats['breakdown']['template_duplicates']} template")
        except Exception as e:
            _logger.warning(f"Could not get deduplication statistics: {e}")

    # Include quality plateau statistics if available
    plateau_stats = {}  # Initialize to empty dict to avoid undefined variable
    if plateau_monitor:
        try:
            plateau_stats = plateau_monitor.get_comprehensive_stats()
            print(f"Quality plateau summary: {plateau_stats['recent_worthy_ratio']:.1%} recent quality, {plateau_stats['overall_worthy_ratio']:.1%} overall")
        except Exception as e:
            _logger.warning(f"Could not get plateau statistics: {e}")
            plateau_stats = {}  # Reset to empty on error

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
        "filtering_efficiency": total_filtered / total_urls_discovered if total_urls_discovered > 0 else 0,
        "quality_plateau_stats": plateau_stats,  # Include plateau monitoring results
        "deduplication_stats": deduplication_stats  # Include content deduplication results
    }
    
    print(f"Done. Crawled {pages_crawled} quality page(s), filtered {total_filtered} junk URLs")
    print(f"URL Quality Ratio: {quality_ratio:.1%} (higher is better)")
    print(f"Output in: {config.output_root.resolve()}")
    
    return results, stats