# url_utils.py - URL manipulation and filtering utilities
import re
import urllib.parse
from typing import Set

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

def is_demo_worthy_url_sync(url: str, content: str = "", title: str = "") -> tuple[bool, str]:
    """
    Synchronous version of AI-enhanced URL worthiness check
    Uses heuristics only (no async AI calls)

    For discovered links (no content/title), this will use URL-only heuristic classification
    which can benefit from the patterns learned during sitemap analysis.
    """
    import logging
    _logger = logging.getLogger(__name__)

    # Basic technical filters first
    basic_worthy, basic_reason = is_demo_worthy_url(url)
    if not basic_worthy:
        return False, basic_reason

    # Try enhanced heuristic if available
    try:
        from ai_content_classifier import HeuristicClassifier
        AI_AVAILABLE = True
    except ImportError:
        AI_AVAILABLE = False

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
