from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response, HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import logging
import asyncio
from typing import Optional, Dict, List, Any
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse, parse_qs
import json
import sys
from pathlib import Path
import hashlib
from datetime import datetime, timedelta
import re
from typing import Set
import os
from dotenv import load_dotenv
from search_templates import create_native_search_template, create_result_item_html, create_no_results_html

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)
print(f"Loading .env from: {env_path}")
print(f"API Key loaded: {bool(os.getenv('OPENAI_API_KEY'))}")

# Try to import cssutils, but it's not essential
try:
    import cssutils
    HAVE_CSSUTILS = True
except ImportError:
    HAVE_CSSUTILS = False

# Add Utility directory to path for OpenSearch integration
sys.path.insert(0, str(Path(__file__).parent.parent / "Utility"))

try:
    from opensearch_integration import Crawl4AIOpenSearchIntegration, OpenSearchConfig
    OPENSEARCH_AVAILABLE = True
except ImportError:
    OPENSEARCH_AVAILABLE = False
    print("Warning: OpenSearch integration not available")

# Initialize FastAPI app for proxy
app = FastAPI(title="Auto-Proxy Server")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Proxy configuration - will be set when crawl completes
proxy_config = {
    "target_url": None,
    "enabled": False,
    "run_id": None,
    "crawl_completed": False,
    "search_injection_enabled": True
}

# OpenSearch integration for search injection
opensearch_integration = None
opensearch_index_name = None

# Template caching for HTML search results (US-65)
search_templates_cache = {}  # Domain-specific template cache

def initialize_opensearch(domain: str = None, host: str = "opensearch-demo", port: int = 9200):
    """Initialize OpenSearch integration for search injection"""
    global opensearch_integration, opensearch_index_name

    if not OPENSEARCH_AVAILABLE:
        logger.warning("OpenSearch not available - search injection disabled")
        return False

    try:
        config = OpenSearchConfig(host=host, port=port, scheme="http")
        opensearch_integration = Crawl4AIOpenSearchIntegration(config)

        # Generate index name from domain if provided
        if domain:
            domain_clean = domain.replace("www.", "").split(".")[0]
            opensearch_index_name = f"demo-{domain_clean}"

        logger.info(f"OpenSearch initialized for search injection - Index: {opensearch_index_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize OpenSearch: {e}")
        return False

def is_search_api_request(path: str, query_params: Dict[str, Any]) -> bool:
    """Enhanced detection of search API requests for any site including SPAs"""
    path_lower = path.lower()

    # Enhanced search API path patterns for SPAs
    search_path_indicators = [
        'search', 'find', 'query', 'lookup', 'results',
        'api/search', 'search/api', 'search/results',
        # SPA patterns
        'graphql', 'api/v1/search', 'api/v2/search',
        'autocomplete', 'suggest', 'typeahead',
        # CommBank specific patterns
        'site-search', 'content/search', 'search-api'
    ]

    # Check if path contains search indicators
    path_has_search = any(indicator in path_lower for indicator in search_path_indicators)

    # Enhanced search query parameter names
    search_param_names = [
        'q', 'query', 'search', 'term', 'keyword', 'text',
        # SPA patterns
        'searchTerm', 'searchQuery', 'input', 'value',
        # GraphQL patterns
        'variables', 'operationName'
    ]

    # Check if request has search-like parameters OR is a known search endpoint
    has_search_params = any(param.lower() in search_param_names for param in query_params.keys())

    # For SPAs, sometimes search APIs don't have query params (POST with body)
    is_known_search_endpoint = any(endpoint in path_lower for endpoint in [
        '/search', '/api/search', '/graphql', '/autocomplete'
    ])

    return path_has_search and (has_search_params or is_known_search_endpoint)

def extract_search_query(query_params: Dict[str, Any]) -> Optional[str]:
    """Extract search query from request parameters"""
    search_param_names = ['q', 'query', 'search', 'term', 'keyword', 'text']

    for param_name in search_param_names:
        for key, value in query_params.items():
            if key.lower() == param_name:
                # Handle both string and list values
                if isinstance(value, list) and value:
                    return value[0]
                elif isinstance(value, str):
                    return value

    return None

async def handle_spa_search_api(query: str, original_path: str, target_url: str) -> JSONResponse:
    """
    Handle SPA search API requests by returning our OpenSearch data
    formatted to match their expected API structure
    """
    if not opensearch_integration or not opensearch_index_name:
        logger.warning("SPA search API intercepted but OpenSearch not configured")
        return JSONResponse({"results": [], "total": 0, "error": "Search temporarily unavailable"})

    try:
        # Get OpenSearch results
        results = opensearch_integration.search(
            query=query,
            index_name=opensearch_index_name,
            size=10
        )

        # Convert our results to a universal SPA-friendly format
        spa_results = []
        for hit in results.get("hits", []):
            # Convert URLs to proxy URLs
            original_url = hit.get("url", "")
            if original_url.startswith("http"):
                parsed_url = urlparse(original_url)
                proxy_url = f"http://localhost:8000/proxy{parsed_url.path}"
                if parsed_url.query:
                    proxy_url += f"?{parsed_url.query}"
            else:
                proxy_url = f"http://localhost:8000/proxy{original_url}"

            # Create universal result format that works with most SPA structures
            spa_result = {
                # Common result fields
                "id": hit.get("id", hit.get("url", "")),
                "title": hit.get("title", ""),
                "description": hit.get("meta_desc", ""),
                "url": proxy_url,
                "snippet": hit.get("meta_desc", ""),
                "score": hit.get("score", 1.0),

                # Alternative field names for different SPA frameworks
                "name": hit.get("title", ""),
                "content": hit.get("meta_desc", ""),
                "link": proxy_url,
                "href": proxy_url,
                "text": hit.get("meta_desc", ""),
                "summary": hit.get("meta_desc", ""),

                # CommBank specific fields (if needed)
                "contentType": "page",
                "category": "general",
                "relevance": hit.get("score", 1.0)
            }

            spa_results.append(spa_result)

        # Universal response format that works with most SPAs
        response_data = {
            # Standard fields
            "results": spa_results,
            "hits": spa_results,  # Alternative name
            "data": spa_results,  # Another alternative
            "total": results.get("total_hits", 0),
            "totalResults": results.get("total_hits", 0),
            "count": len(spa_results),
            "query": query,
            "searchTerm": query,
            "status": "success",
            "success": True,

            # Pagination (even if we don't use it)
            "page": 1,
            "pageSize": 10,
            "hasMore": False
        }

        logger.info(f"SPA search API handled: '{query}' -> {len(spa_results)} results")
        return JSONResponse(response_data)

    except Exception as e:
        logger.error(f"SPA search API error: {e}")
        return JSONResponse({
            "results": [],
            "total": 0,
            "error": f"Search failed: {str(e)}",
            "status": "error",
            "success": False
        }, status_code=500)

async def extract_site_styling_dna(target_url: str) -> Dict[str, str]:
    """
    Extract the visual DNA of any site to make search results look native

    Extracts fonts, colors, spacing, branding elements that make each site unique
    """
    logger.info(f"Extracting styling DNA for {target_url}")

    styling_dna = {
        "brand_name": "Search",
        "primary_font": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        "text_color": "#333333",
        "background_color": "#ffffff",
        "brand_color": "#0066cc",
        "link_color": "#0066cc",
        "header_bg": "#ffffff",
        "header_border": "1px solid #e0e0e0",
        "container_width": "1200px",
        "content_padding": "20px",
        "header_padding": "15px 20px",
        "logo_url": "",
        "nav_structure": ""
    }

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # Fetch homepage HTML
            response = await client.get(target_url)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch {target_url} for styling extraction")
                return styling_dna

            html = response.text
            soup = BeautifulSoup(html, 'html.parser')

            # Extract brand name
            styling_dna["brand_name"] = extract_brand_name(soup, target_url)

            # Extract logo URL
            styling_dna["logo_url"] = extract_logo_url(soup, target_url)

            # Extract colors from HTML and inline styles
            colors = extract_colors_from_html(soup)
            if colors.get("brand_color"):
                styling_dna["brand_color"] = colors["brand_color"]
                styling_dna["link_color"] = colors["brand_color"]
            if colors.get("text_color"):
                styling_dna["text_color"] = colors["text_color"]
            if colors.get("background_color"):
                styling_dna["background_color"] = colors["background_color"]

            # Extract navigation structure
            styling_dna["nav_structure"] = extract_navigation_structure(soup)

            # Extract CSS files and analyze them
            css_urls = extract_css_file_urls(soup, target_url)
            if css_urls:
                css_styling = await analyze_css_files(client, css_urls, target_url)
                styling_dna.update(css_styling)

            logger.info(f"Extracted styling DNA: brand={styling_dna['brand_name']}, colors={styling_dna['brand_color']}")

    except Exception as e:
        logger.error(f"Error extracting styling DNA: {e}")

    return styling_dna

def extract_brand_name(soup: BeautifulSoup, target_url: str) -> str:
    """Extract brand name from page"""
    # Try multiple methods to find brand name

    # Method 1: Page title
    title_tag = soup.find('title')
    if title_tag:
        title = title_tag.get_text().strip()
        # Clean up common title patterns
        for separator in [' | ', ' - ', ' :: ', ' — ']:
            if separator in title:
                parts = title.split(separator)
                return parts[-1].strip()  # Usually brand is last part
        if title and len(title) < 50:  # Reasonable brand name length
            return title

    # Method 2: Logo alt text
    logo_selectors = ['img[alt*="logo"]', 'img[class*="logo"]', '.logo img', '#logo img']
    for selector in logo_selectors:
        logo = soup.select_one(selector)
        if logo and logo.get('alt'):
            alt_text = logo['alt'].strip()
            if alt_text and len(alt_text) < 30:
                return alt_text.replace(' logo', '').replace('Logo', '').strip()

    # Method 3: Domain name
    domain = urlparse(target_url).netloc.replace('www.', '')
    brand = domain.split('.')[0]
    return brand.upper()

def extract_logo_url(soup: BeautifulSoup, target_url: str) -> str:
    """Extract logo URL from page"""
    logo_selectors = [
        'img[alt*="logo" i]',
        'img[class*="logo" i]',
        '.logo img',
        '#logo img',
        'header img',
        '.header img',
        '.brand img',
        '.navbar-brand img'
    ]

    for selector in logo_selectors:
        logo = soup.select_one(selector)
        if logo and logo.get('src'):
            src = logo['src']
            # Convert relative URLs to absolute
            if src.startswith('//'):
                return f"https:{src}"
            elif src.startswith('/'):
                return f"{target_url.rstrip('/')}{src}"
            elif not src.startswith('http'):
                return f"{target_url.rstrip('/')}/{src}"
            return src

    return ""

def extract_colors_from_html(soup: BeautifulSoup) -> Dict[str, str]:
    """Extract colors from HTML styles and CSS"""
    colors = {}

    # Look for style attributes
    elements_with_style = soup.find_all(attrs={"style": True})
    color_patterns = []

    for element in elements_with_style:
        style = element['style']
        # Extract color values
        color_matches = re.findall(r'color:\s*([^;]+)', style, re.IGNORECASE)
        bg_matches = re.findall(r'background(?:-color)?:\s*([^;]+)', style, re.IGNORECASE)
        color_patterns.extend(color_matches + bg_matches)

    # Look for CSS variables in :root or html
    style_tags = soup.find_all('style')
    for style_tag in style_tags:
        if style_tag.string:
            css_content = style_tag.string
            # Extract CSS variables that might be brand colors
            var_matches = re.findall(r'--[^:]*color[^:]*:\s*([^;]+)', css_content, re.IGNORECASE)
            color_patterns.extend(var_matches)

    # Analyze colors to find brand color (usually the most unique/saturated)
    valid_colors = []
    for color in color_patterns:
        color = color.strip()
        if color and not color.lower() in ['inherit', 'transparent', 'none']:
            valid_colors.append(color)

    if valid_colors:
        # Simple heuristic: pick first non-gray color as brand color
        for color in valid_colors:
            if not any(gray in color.lower() for gray in ['gray', 'grey', '#333', '#666', '#999', 'black', 'white']):
                colors["brand_color"] = color
                break

    return colors

def extract_navigation_structure(soup: BeautifulSoup) -> str:
    """Extract enhanced navigation structure to recreate in search template"""
    nav_html = ""

    try:
        # Enhanced navigation extraction - look for full header structure
        header_selectors = [
            'header', '.header', '.site-header', '.main-header',
            '.nav-header', '[role="banner"]', '.navbar'
        ]

        header_element = None
        for selector in header_selectors:
            header_element = soup.select_one(selector)
            if header_element:
                break

        if header_element:
            # Extract the complete header structure but simplify it
            nav_items = []
            utility_items = []

            # Look for main navigation links
            main_nav_links = header_element.find_all('a')

            # Track text we've already seen to avoid duplicates
            seen_texts = set()

            for link in main_nav_links[:8]:  # Increased limit for more complete nav
                text = link.get_text(strip=True)
                href = link.get('href', '#')
                text_lower = text.lower()

                # Skip if we've already seen this text (avoid duplicates)
                if text_lower in seen_texts:
                    continue

                if text and len(text) < 25 and text not in ['', ' ']:
                    # Skip common duplicate content
                    if any(skip in text_lower for skip in ['bank accounts', 'credit cards', 'home loans', 'insurance']):
                        continue

                    # Classify as utility (login, chat, etc.) or main nav
                    if any(keyword in text_lower for keyword in ['login', 'chat', 'skip', 'account', 'help']):
                        utility_items.append(f'<a href="{href}" class="utility-link">{text}</a>')
                        seen_texts.add(text_lower)
                    elif not any(skip in text_lower for skip in ['cookie', 'privacy', 'accessibility']):
                        nav_items.append(f'<a href="{href}" class="nav-link">{text}</a>')
                        seen_texts.add(text_lower)

            # Build enhanced navigation HTML
            nav_html = '<div class="nav-wrapper">'

            if utility_items:
                nav_html += f'<div class="utility-nav">{"".join(utility_items[:3])}</div>'

            if nav_items:
                nav_html += f'<nav class="main-nav">{"".join(nav_items[:5])}</nav>'

            nav_html += '</div>'

        # Fallback to simpler extraction if enhanced fails
        if not nav_html or nav_html == '<div class="nav-wrapper"></div>':
            nav_selectors = ['nav', '.navigation', '.navbar', '.menu']
            for selector in nav_selectors:
                nav = soup.select_one(selector)
                if nav:
                    nav_items = []
                    links = nav.find_all('a')
                    for link in links[:5]:
                        text = link.get_text(strip=True)
                        href = link.get('href', '#')
                        if text and len(text) < 20:
                            nav_items.append(f'<a href="{href}" class="nav-link">{text}</a>')

                    if nav_items:
                        nav_html = f'<nav class="main-nav">{"".join(nav_items)}</nav>'
                        break

    except Exception as e:
        logger.warning(f"Error extracting navigation: {e}")
        nav_html = ""

    return nav_html

def extract_css_file_urls(soup: BeautifulSoup, target_url: str) -> List[str]:
    """Extract CSS file URLs from page"""
    css_urls = []
    base_url = target_url.rstrip('/')

    # Find all CSS link tags
    css_links = soup.find_all('link', rel='stylesheet')
    for link in css_links:
        href = link.get('href')
        if href:
            # Convert relative URLs to absolute
            if href.startswith('//'):
                css_url = f"https:{href}"
            elif href.startswith('/'):
                css_url = f"{base_url}{href}"
            elif not href.startswith('http'):
                css_url = f"{base_url}/{href}"
            else:
                css_url = href

            css_urls.append(css_url)

    return css_urls[:5]  # Limit to first 5 CSS files to avoid overload

async def analyze_css_files(client: httpx.AsyncClient, css_urls: List[str], target_url: str) -> Dict[str, str]:
    """Analyze CSS files to extract fonts, spacing, and layout patterns"""
    css_styling = {}

    # Disable cssutils logging if available
    if HAVE_CSSUTILS:
        cssutils.log.setLevel('ERROR')

    for css_url in css_urls:
        try:
            response = await client.get(css_url, timeout=10.0)
            if response.status_code == 200:
                css_content = response.text

                # Extract font families
                font_matches = re.findall(r'font-family:\s*([^;]+)', css_content, re.IGNORECASE)
                if font_matches:
                    # Use the first non-generic font family
                    for font in font_matches:
                        font = font.strip().strip('"\'')
                        if font and not font.lower() in ['inherit', 'sans-serif', 'serif', 'monospace']:
                            css_styling["primary_font"] = font
                            break

                # Extract container/layout widths
                width_matches = re.findall(r'(?:max-)?width:\s*(\d+(?:px|em|rem))', css_content)
                for width in width_matches:
                    if '1200' in width or '1000' in width or '960' in width:
                        css_styling["container_width"] = width
                        break

                # Extract more color patterns
                color_matches = re.findall(r'(?:color|background-color):\s*([^;]+)', css_content, re.IGNORECASE)
                # Process color matches similar to HTML extraction

        except Exception as e:
            logger.warning(f"Failed to analyze CSS file {css_url}: {e}")
            continue

    return css_styling

async def fetch_search_page_template(target_url: str) -> str:
    """
    Fetch and extract search page template from target site

    Args:
        target_url: The target site base URL (e.g., "https://nab.com.au")

    Returns:
        HTML template string with placeholders for search results
    """
    logger.info(f"Fetching search template for {target_url}")

    # Common search page paths to try - enhanced for SPA sites
    search_paths = [
        "/search",
        "/search?q=test",
        "/search?query=test",
        "/find",
        "/site-search",
        "/?q=test",
        "/?search=test",
        "/search-results",
        "/results"
    ]

    template_html = None

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # Try each search path until we find one that works
            for search_path in search_paths:
                search_url = f"{target_url.rstrip('/')}{search_path}"

                try:
                    logger.info(f"Trying search URL: {search_url}")
                    response = await client.get(search_url)

                    if response.status_code == 200:
                        content_type = response.headers.get("content-type", "").lower()

                        if "text/html" in content_type:
                            template_html = response.text
                            logger.info(f"Successfully fetched template from {search_url}")
                            break

                except Exception as e:
                    logger.warning(f"Failed to fetch {search_url}: {e}")
                    continue

            # If no search page found, use the homepage as fallback
            if not template_html:
                logger.info(f"No dedicated search page found, using homepage as template")
                try:
                    response = await client.get(target_url)
                    if response.status_code == 200:
                        template_html = response.text

                        # For SPA sites like CommBank, we need to detect if it's JS-heavy
                        if is_spa_site(template_html):
                            logger.info(f"Detected SPA site, using modified template approach")
                            template_html = create_spa_compatible_template(template_html, target_url)

                except Exception as e:
                    logger.error(f"Failed to fetch homepage template: {e}")

    except Exception as e:
        logger.error(f"Error fetching search template: {e}")

    # If still no template, create a basic fallback
    if not template_html:
        logger.warning(f"Creating fallback template for {target_url}")
        template_html = create_fallback_template(target_url)

    return template_html

def is_spa_site(html_content: str) -> bool:
    """Detect if site is a Single Page Application (SPA)"""
    spa_indicators = [
        'angular', 'react', 'vue.js', 'ember',
        'data-ng-', 'ng-app', 'data-react-',
        'window.React', 'window.Vue',
        'single-page', 'spa-',
        'app.js', 'main.js', 'bundle.js',
        'router-outlet', 'ui-view'
    ]

    html_lower = html_content.lower()
    return any(indicator in html_lower for indicator in spa_indicators)

def create_spa_compatible_template(original_html: str, target_url: str) -> str:
    """Create a template compatible with SPA sites by preserving their structure"""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(original_html, 'html.parser')

        # Find the main content area where results would be displayed
        content_selectors = [
            'main', '[role="main"]', '.main-content', '#main-content',
            '.content', '#content', '.page-content', '.search-results',
            '.results-container', '[data-testid*="content"]'
        ]

        main_content = None
        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break

        # If we can't find main content, use body
        if not main_content:
            main_content = soup.find('body')

        if main_content:
            # Clear the content but preserve structure
            # Keep header, navigation, footer intact
            main_content.clear()
            main_content.append(soup.new_string("{{SEARCH_RESULTS}}"))

            return str(soup)

    except Exception as e:
        logger.warning(f"Failed to create SPA template: {e}")

    # Fallback: Use original template with placeholder injection
    return original_html.replace('<body>', '<body>{{SEARCH_RESULTS}}')

def is_dynamic_search_site(target_url: str) -> bool:
    """
    Universal search button replacement for ALL website types

    Returns True for every site to enable comprehensive search replacement covering:
    - Banking sites (CommBank, NAB, Westpac, ANZ)
    - E-commerce sites (Amazon, eBay, shopping sites)
    - Government sites (.gov patterns)
    - Educational sites (.edu patterns)
    - WordPress/CMS sites (WordPress, Drupal, Joomla)
    - Modern framework sites (React, Vue, Angular)
    - Corporate sites with custom search implementations
    - Client-side search sites (no API calls)
    - Traditional server-side search sites
    - SPA sites with API-based search
    """
    return True

def inject_search_functionality(html_content: str, target_url: str) -> str:
    """Replace existing site search functionality with our demo search"""
    try:
        logger.info(f"Starting search injection for {target_url}")
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Add JavaScript to completely replace their search functionality
        script = soup.new_tag('script')
        script.string = '''
            document.addEventListener('DOMContentLoaded', function() {
                console.log('Demo search replacement initialized - v2.0');
                console.log('Current URL:', window.location.href);

                // Function to redirect to our lookalike search page
                function redirectToSearchPage(initialQuery = '') {
                    console.log('Redirecting to demo search page with query:', initialQuery);

                    // Build search URL with query parameter
                    const searchUrl = `/proxy/search${initialQuery ? `?q=${encodeURIComponent(initialQuery)}` : ''}`;

                    // Redirect in the same window for seamless experience
                    window.location.href = searchUrl;
                }

                // Function to show search input modal - fixed version
                function showSearchInput() {
                    console.log('🔍 MODAL: showSearchInput() called!');
                    // Prevent multiple modals
                    if (document.getElementById('demo-search-modal')) {
                        console.log('🔍 MODAL: Modal already exists, skipping');
                        return;
                    }

                    // Create a styled search modal that matches the site
                    const modal = document.createElement('div');
                    modal.id = 'demo-search-modal';
                    modal.style.cssText = `
                        position: fixed;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        background: rgba(0, 0, 0, 0.5);
                        z-index: 999999;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                    `;

                    const searchBox = document.createElement('div');
                    searchBox.style.cssText = `
                        background: white;
                        padding: 30px;
                        border-radius: 8px;
                        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
                        max-width: 400px;
                        width: 90%;
                        position: relative;
                        z-index: 1000000;
                    `;

                    searchBox.innerHTML = `
                        <h3 style="margin: 0 0 20px 0; color: #333; user-select: none;">Search</h3>
                        <input type="text" id="demo-search-input" placeholder="Enter your search query..."
                               style="width: 100%; padding: 12px; border: 2px solid #ddd; border-radius: 4px; font-size: 16px; margin-bottom: 15px; outline: none; box-sizing: border-box;"
                               autocomplete="off" spellcheck="false">
                        <div style="text-align: right; user-select: none;">
                            <button id="demo-cancel-btn" style="margin-right: 10px; padding: 8px 16px; border: 1px solid #ddd; background: white; border-radius: 4px; cursor: pointer; outline: none;">Cancel</button>
                            <button id="demo-search-btn" style="padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; outline: none;">Search</button>
                        </div>
                    `;

                    modal.appendChild(searchBox);
                    document.body.appendChild(modal);

                    // Add Enter key support for input
                    const input = document.getElementById('demo-search-input');
                    input.addEventListener('keydown', function(e) {
                        if (e.key === 'Enter') {
                            const query = input.value.trim();
                            if (query) {
                                document.getElementById('demo-search-modal').remove();
                                window.location.href = '/proxy/search?q=' + encodeURIComponent(query);
                            } else {
                                alert('Please enter a search query');
                            }
                        }
                        if (e.key === 'Escape') {
                            document.getElementById('demo-search-modal').remove();
                        }
                    });

                    // Add button event listeners
                    const searchBtn = document.getElementById('demo-search-btn');
                    const cancelBtn = document.getElementById('demo-cancel-btn');

                    searchBtn.addEventListener('click', function(e) {
                        e.preventDefault();
                        const query = input.value.trim();
                        if (query) {
                            document.getElementById('demo-search-modal').remove();
                            window.location.href = '/proxy/search?q=' + encodeURIComponent(query);
                        } else {
                            alert('Please enter a search query');
                        }
                    });

                    cancelBtn.addEventListener('click', function(e) {
                        e.preventDefault();
                        document.getElementById('demo-search-modal').remove();
                    });

                    // Close on background click
                    modal.addEventListener('click', function(e) {
                        if (e.target === modal) {
                            document.getElementById('demo-search-modal').remove();
                        }
                    });

                    // Focus management - wait for DOM to be ready
                    requestAnimationFrame(() => {
                        input.focus();
                    });
                }

                // AI-Powered search detection with caching
                async function replaceSearchButtonsWithAI() {
                    try {
                        console.log('Starting AI-powered search button replacement...');

                        // 1. Check cache first
                        const cachedPatterns = await loadSearchPatternsCache();
                        if (cachedPatterns) {
                            console.log('Using cached search patterns');
                            const foundElements = applyCachedPatterns(cachedPatterns);
                            if (foundElements.length > 0) {
                                return foundElements.length;
                            }
                            console.log('Cached patterns failed, falling back to AI...');
                        }

                        // 2. Use AI Vision API if no cache or cache failed
                        console.log('Analyzing page with AI Vision...');
                        const aiResults = await analyzePageWithOpenAI();

                        // 3. Extract and cache patterns
                        const patterns = extractReusablePatterns(aiResults);
                        await saveSearchPatternsCache(patterns);

                        // 4. Apply the results
                        return applyAIResults(aiResults);

                    } catch (error) {
                        console.error('AI search detection failed, falling back to rules:', error);
                        return replaceSearchButtonsLegacy();
                    }
                }

                // Cache management functions
                async function loadSearchPatternsCache() {
                    try {
                        const domain = window.location.hostname;
                        const response = await fetch(`http://localhost:8001/cache/${domain}`);
                        if (response.ok) {
                            const cache = await response.json();
                            // Check if cache is recent (within 30 days)
                            const cacheAge = Date.now() - new Date(cache.last_analyzed).getTime();
                            if (cacheAge < 30 * 24 * 60 * 60 * 1000) {
                                return cache;
                            }
                        }
                        return null;
                    } catch (error) {
                        console.log('No cached patterns found:', error);
                        return null;
                    }
                }

                async function saveSearchPatternsCache(patterns) {
                    try {
                        const domain = window.location.hostname;
                        const cache = {
                            domain: domain,
                            last_analyzed: new Date().toISOString(),
                            search_patterns: patterns,
                            version: "1.0"
                        };

                        await fetch(`http://localhost:8001/cache/${domain}`, {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify(cache, null, 2)
                        });

                        console.log('Search patterns cached successfully');
                    } catch (error) {
                        console.error('Failed to cache search patterns:', error);
                    }
                }

                function applyCachedPatterns(cache) {
                    const foundElements = [];

                    cache.search_patterns.forEach(pattern => {
                        // Try each selector until one works
                        for (const selector of pattern.selectors) {
                            try {
                                const elements = document.querySelectorAll(selector);
                                if (elements.length > 0) {
                                    // Verify it matches the cached context
                                    const validElements = Array.from(elements).filter(el =>
                                        isValidCachedElement(el, pattern.context)
                                    );

                                    if (validElements.length > 0) {
                                        foundElements.push(...validElements);
                                        console.log(`Found ${validElements.length} elements with cached selector: ${selector}`);
                                        break; // Move to next pattern
                                    }
                                }
                            } catch (e) {
                                console.log(`Cached selector failed: ${selector}`, e);
                            }
                        }
                    });

                    // Apply replacement to found elements
                    foundElements.forEach(element => {
                        replaceElementWithSearchModal(element);
                    });

                    return foundElements;
                }

                function isValidCachedElement(element, context) {
                    // Verify the element matches cached characteristics
                    return (
                        (!context.placeholder || element.placeholder === context.placeholder) &&
                        (!context.text_content || element.textContent?.includes(context.text_content)) &&
                        (!context.parent_class || element.parentElement?.className.includes(context.parent_class))
                    );
                }

                // OpenAI Vision API functions
                async function analyzePageWithOpenAI() {
                    try {
                        // Import html2canvas if not already available
                        if (typeof html2canvas === 'undefined') {
                            await loadScript('https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js');
                        }

                        console.log('🔍 Starting AI Vision analysis for search elements...');
                        console.log('🌐 Page URL:', window.location.href);
                        console.log('📸 Taking page screenshot...');
                        const canvas = await html2canvas(document.body, {
                            useCORS: true,
                            allowTaint: false,
                            scale: 0.5, // Reduce size for API efficiency
                            width: window.innerWidth,
                            height: Math.min(window.innerHeight, 1000), // Limit height
                            backgroundColor: '#ffffff'
                        });

                        const screenshot = canvas.toDataURL('image/jpeg', 0.8); // Compress for API

                        console.log('📊 Screenshot captured:', canvas.width, 'x', canvas.height);
                        console.log('🚀 Sending to AI Vision service at localhost:8001...');
                        const response = await fetch('http://localhost:8001/analyze', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                image: screenshot,
                                prompt: `Analyze this webpage screenshot and identify all search-related elements (search input fields, search buttons with text or magnifying glass icons). Return JSON array with pixel coordinates: [{"type": "input|button", "x": number, "y": number, "width": number, "height": number, "description": "brief description"}]`
                            })
                        });

                        if (!response.ok) {
                            throw new Error(`AI Vision API failed: ${response.status}`);
                        }

                        const result = await response.json();
                        console.log('AI Vision results:', result);
                        return result.elements || [];

                    } catch (error) {
                        console.error('OpenAI Vision analysis failed:', error);
                        throw error;
                    }
                }

                function loadScript(src) {
                    return new Promise((resolve, reject) => {
                        const script = document.createElement('script');
                        script.src = src;
                        script.onload = resolve;
                        script.onerror = reject;
                        document.head.appendChild(script);
                    });
                }

                function extractReusablePatterns(aiResults) {
                    return aiResults.map(result => {
                        // Find the DOM element at AI-identified coordinates
                        const element = document.elementFromPoint(result.x, result.y);

                        if (!element) {
                            console.warn('No element found at coordinates:', result);
                            return null;
                        }

                        // Generate multiple selector strategies
                        const selectors = [
                            element.id ? `#${element.id}` : null,
                            element.className ? `.${element.className.split(' ')[0]}` : null,
                            element.tagName.toLowerCase() + (element.className ? `.${element.className.split(' ')[0]}` : ''),
                            generateUniqueSelector(element),
                            // Parent-based selectors for complex structures
                            element.parentElement?.className ? `${element.parentElement.tagName.toLowerCase()}.${element.parentElement.className.split(' ')[0]} ${element.tagName.toLowerCase()}` : null
                        ].filter(Boolean);

                        return {
                            element_type: result.type,
                            selectors: selectors,
                            context: {
                                parent_class: element.parentElement?.className || '',
                                text_content: element.textContent?.trim() || '',
                                placeholder: element.placeholder || '',
                                aria_label: element.getAttribute('aria-label') || '',
                                tag_name: element.tagName.toLowerCase()
                            },
                            coordinates: {x: result.x, y: result.y},
                            confidence: 0.9
                        };
                    }).filter(Boolean);
                }

                function generateUniqueSelector(element) {
                    // Generate a unique CSS selector for the element
                    const path = [];
                    let current = element;

                    while (current && current.nodeType === Node.ELEMENT_NODE) {
                        let selector = current.tagName.toLowerCase();

                        if (current.id) {
                            selector += `#${current.id}`;
                            path.unshift(selector);
                            break;
                        }

                        if (current.className) {
                            selector += `.${current.className.split(' ')[0]}`;
                        }

                        // Add nth-child if needed
                        const siblings = Array.from(current.parentElement?.children || []);
                        const sameTagSiblings = siblings.filter(s => s.tagName === current.tagName);
                        if (sameTagSiblings.length > 1) {
                            const index = sameTagSiblings.indexOf(current) + 1;
                            selector += `:nth-of-type(${index})`;
                        }

                        path.unshift(selector);
                        current = current.parentElement;

                        if (path.length > 5) break; // Prevent overly long selectors
                    }

                    return path.join(' > ');
                }

                function applyAIResults(aiResults) {
                    let replacedCount = 0;

                    console.log('AI Results received:', aiResults);

                    // Handle different AI response formats
                    let elements = [];
                    if (aiResults.analysis && aiResults.analysis.elements) {
                        elements = aiResults.analysis.elements;
                    } else if (Array.isArray(aiResults)) {
                        elements = aiResults;
                    }

                    elements.forEach(result => {
                        console.log('Processing AI result:', result);

                        // Find elements using AI descriptions
                        let foundElements = [];

                        // Try to find by text content
                        if (result.text) {
                            const textElements = document.querySelectorAll('button, input[type="submit"], a, [role="button"]');
                            textElements.forEach(el => {
                                if (el.textContent.toLowerCase().includes(result.text.toLowerCase())) {
                                    foundElements.push(el);
                                }
                            });
                        }

                        // Try to find by type and search-related attributes
                        if (result.type === 'button' || result.type === 'input') {
                            const searchElements = document.querySelectorAll([
                                'button[class*="search" i]',
                                'input[type="submit"][class*="search" i]',
                                'button[aria-label*="search" i]',
                                '*[data-testid*="search" i]'
                            ].join(','));
                            foundElements.push(...searchElements);
                        }

                        // Process found elements
                        foundElements.forEach(element => {
                            if (element && !element.hasAttribute('data-demo-search-processed')) {
                                console.log(`Replacing AI-detected search element:`, element);
                                replaceElementWithSearchModal(element);
                                replacedCount++;
                            }
                        });
                    });

                    console.log(`AI Vision replaced ${replacedCount} search elements`);
                    return replacedCount;
                }

                function replaceElementWithSearchModal(element) {
                    // Clone the element to preserve styling
                    const newElement = element.cloneNode(true);

                    // Remove existing event listeners
                    newElement.removeAttribute('onclick');
                    newElement.removeAttribute('href');

                    // Add our search modal trigger
                    newElement.addEventListener('click', function(e) {
                        console.log('🔍 CLICK: Search element clicked!', newElement);
                        e.preventDefault();
                        e.stopPropagation();
                        showSearchInput();
                    });

                    // For input fields, also handle Enter key
                    if (newElement.tagName.toLowerCase() === 'input') {
                        newElement.addEventListener('keydown', function(e) {
                            if (e.key === 'Enter') {
                                e.preventDefault();
                                e.stopPropagation();

                                const query = newElement.value.trim();
                                if (query) {
                                    window.location.href = '/proxy/search?q=' + encodeURIComponent(query);
                                } else {
                                    showSearchInput();
                                }
                            }
                        });
                    }

                    // Mark as processed and replace
                    newElement.setAttribute('data-demo-search-processed', 'true');
                    element.parentNode.replaceChild(newElement, element);
                }

                // Legacy rule-based fallback
                function replaceSearchButtonsLegacy() {
                    console.log('Using legacy rule-based search detection...');

                        // Universal search detection patterns
                    const searchPatterns = {
                        // Text-based detection
                        textMatches: ['search', 'find', 'look', 'query', 'buscar', 'chercher'],
                        // Class name patterns
                        classPatterns: ['search', 'find', 'lookup', 'query', 'magnify'],
                        // Attribute patterns
                        attrPatterns: ['search', 'find', 'query']
                    };

                    // COMPREHENSIVE: Target all interactive search elements
                    const searchButtonSelectors = [
                        // === TRADITIONAL FORM ELEMENTS ===
                        'button[type="submit"]',
                        'input[type="submit"]',
                        'button[form]',
                        'input[type="button"]',

                        // === SEARCH-SPECIFIC PATTERNS ===
                        '*[class*="search" i]',
                        '*[id*="search" i]',
                        '*[aria-label*="search" i]',
                        '*[title*="search" i]',
                        '*[placeholder*="search" i]',
                        '*[data-testid*="search" i]',
                        '*[data-test*="search" i]',
                        '*[name*="search" i]',

                        // === ALTERNATIVE SEARCH TERMS ===
                        '*[class*="find" i]', '*[id*="find" i]',
                        '*[class*="query" i]', '*[id*="query" i]',
                        '*[class*="lookup" i]', '*[id*="lookup" i]',

                        // === MODERN FRAMEWORK PATTERNS ===
                        'div[role="button"]', 'span[role="button"]', 'a[role="button"]',
                        'div[onclick]', 'span[onclick]', 'a[onclick]',
                        'div[tabindex]', 'span[tabindex]',
                        '*[role="searchbox"]',

                        // === ICON PATTERNS ===
                        '*[class*="icon-search" i]', '*[class*="fa-search" i]',
                        '*[class*="search-icon" i]', '*[class*="magnify" i]',
                        '*[class*="glass" i]', '*[class*="loupe" i]',

                        // === AGILENT-SPECIFIC PATTERNS ===
                        '.tt-hint', '.homeSearchImg', '.searchContainer *',

                        // === FORM CONTEXT ===
                        'form[role="search"] *',
                        'form[class*="search" i] *',
                        'form[action*="search" i] *',

                        // === CONTAINER PATTERNS ===
                        '.search-container *', '.searchContainer *',
                        '.search-box *', '.searchbox *', '.search_box *',
                        '.search-form *', '.searchform *', '.search_form *',
                        '.search-bar *', '.searchbar *', '.search_bar *',
                        '.search-input *', '.searchinput *', '.search_input *',
                        '.search-button *', '.searchbutton *', '.search_button *',
                        '.search-field *', '.searchfield *', '.search_field *',
                        '.search-wrap *', '.searchwrap *', '.search_wrap *',
                        '.search-widget *', '.searchwidget *', '.search_widget *',
                        '.homeSearch *', '.home-search *', '.home_search *',
                        '.global-search *', '.globalsearch *', '.global_search *',
                        '.site-search *', '.sitesearch *', '.site_search *',
                        '.header-search *', '.headersearch *', '.header_search *',

                        // === COMMON CMS/FRAMEWORK CLASSES ===
                        '.btn-search', '.button-search', '.search-btn', '.search-button',
                        '.wp-search', '.drupal-search', '.joomla-search',
                        '.bootstrap-search', '.material-search', '.ant-search',

                        // === ARIA AND ACCESSIBILITY ===
                        '*[aria-describedby*="search" i]',
                        '*[aria-labelledby*="search" i]',
                        '*[data-toggle*="search" i]',
                        '*[data-target*="search" i]',

                        // === BUTTON TEXT PATTERNS (via text content) ===
                        'button', 'input[type="submit"]', 'input[type="button"]',
                        'a', 'span', 'div',

                        // === ULTRA-WIDE NET (any clickable element) ===
                        '*[style*="cursor: pointer"]', '*[style*="cursor:pointer"]'
                    ];

                    let replacedCount = 0;

                    searchButtonSelectors.forEach(selector => {
                        const buttons = document.querySelectorAll(selector);
                        console.log(`Checking selector "${selector}": found ${buttons.length} elements`);
                        buttons.forEach(button => {
                            // Skip if already processed
                            if (button.hasAttribute('data-demo-search-processed')) {
                                console.log('Skipping already processed button:', button);
                                return;
                            }
                            // COMBINED APPROACH: Text + Icon + Context + Form detection
                            const buttonText = button.textContent?.toLowerCase() || '';
                            const buttonClass = button.className?.toLowerCase() || '';
                            const buttonId = button.id?.toLowerCase() || '';
                            const ariaLabel = button.getAttribute('aria-label')?.toLowerCase() || '';

                            // Helper function to detect search icons
                            function hasSearchIcon(element) {
                                const text = element.textContent || '';
                                const className = element.className || '';

                                return (
                                    // Unicode search symbols
                                    text.includes('🔍') ||
                                    text.includes('⌕') ||
                                    text.includes('\\u{1F50D}') ||
                                    // Common icon fonts
                                    className.includes('fa-search') ||
                                    className.includes('icon-search') ||
                                    className.includes('search-icon') ||
                                    // SVG detection
                                    element.querySelector('svg[class*="search" i]') ||
                                    element.querySelector('use[href*="search" i]') ||
                                    // Material icons
                                    (className.includes('material-icons') && text.includes('search'))
                                );
                            }

                            // Exclude navigation elements explicitly
                            const isNavigationElement =
                                buttonClass.includes('nav') ||
                                buttonClass.includes('menu') ||
                                buttonClass.includes('dropdown') ||
                                buttonText.includes('personal') ||
                                buttonText.includes('business') ||
                                buttonText.includes('corporate') ||
                                buttonText.includes('about') ||
                                buttonText.includes('help') ||
                                buttonText.includes('support') ||
                                buttonText.includes('login') ||
                                button.closest('nav') ||
                                button.closest('.nav') ||
                                button.closest('.navigation') ||
                                button.closest('.menu') ||
                                button.closest('.dropdown') ||
                                button.closest('header .main-nav');

                            // Simplified and more direct search detection
                            const isSearchElement = !isNavigationElement && (
                                // Direct class/id/text matching (case insensitive)
                                buttonClass.toLowerCase().includes('search') ||
                                buttonId.toLowerCase().includes('search') ||
                                buttonText.toLowerCase().includes('search') ||
                                ariaLabel.toLowerCase().includes('search') ||

                                // Icon detection
                                hasSearchIcon(button) ||

                                // Context-based (already in a search container)
                                button.closest('.searchContainer') ||
                                button.closest('.homeSearch') ||
                                button.closest('.search-form') ||
                                button.closest('.search-box') ||
                                button.closest('form[role="search"]') ||

                                // Form association
                                (button.type === 'submit' && button.form?.querySelector('input[type="search"], input[name="q"], input[name*="search" i], input[placeholder*="search" i]'))
                            );

                            console.log(`Evaluating element: text="${buttonText}", class="${buttonClass}", isSearch=${isSearchElement}`);

                            if (isSearchElement) {
                                console.log('REPLACING search button:', button);
                                console.log('Button element details:', {
                                    tagName: button.tagName,
                                    className: button.className,
                                    id: button.id,
                                    ariaLabel: button.getAttribute('aria-label'),
                                    parentElement: button.parentElement?.tagName
                                });
                                // Clone the button to preserve styling
                                const newButton = button.cloneNode(true);

                                // Remove all existing event listeners and onclick handlers
                                newButton.removeAttribute('onclick');
                                newButton.removeAttribute('href');

                                // Add our search functionality
                                newButton.addEventListener('click', function(e) {
                                    e.preventDefault();
                                    e.stopPropagation();

                                    // Always show search modal for user control
                                    showSearchInput();
                                });

                                // Mark as processed and replace the original button
                                newButton.setAttribute('data-demo-search-processed', 'true');
                                button.parentNode.replaceChild(newButton, button);
                                replacedCount++;
                            }
                        });
                    });

                    // Universal search input field detection
                    const searchInputs = document.querySelectorAll(`
                        input[type="search"],
                        input[placeholder*="search" i],
                        input[name*="search" i],
                        input[id*="search" i],
                        input[class*="search" i],
                        input[placeholder*="find" i],
                        input[placeholder*="query" i],
                        input[placeholder*="keyword" i],
                        input[name*="q"],
                        input[name*="query"],
                        input[name*="keyword"],
                        input[id*="searchbox"],
                        input[class*="searchbox"],
                        input[class*="search-box"],
                        input[class*="search-field"],
                        input[class*="search-input"],
                        form[role="search"] input,
                        form[action*="search"] input,
                        form[id*="search"] input,
                        form[class*="search"] input,
                        .search-form input,
                        .searchform input,
                        .wp-search input
                    `);

                    searchInputs.forEach(input => {
                        // Skip if already processed
                        if (input.hasAttribute('data-demo-search-processed')) {
                            return;
                        }

                        // Only add Enter key handler - no click handlers on inputs
                        input.addEventListener('keydown', function(e) {
                            if (e.key === 'Enter') {
                                e.preventDefault();
                                e.stopPropagation();

                                const query = input.value.trim();
                                if (query) {
                                    redirectToSearchPage(query);
                                } else {
                                    showSearchInput();
                                }
                            }
                        });

                        // Mark input as processed to avoid duplicate processing
                        input.setAttribute('data-demo-search-processed', 'true');
                    });

                    const inputCount = searchInputs.length;
                    console.log(`Replaced ${replacedCount} search buttons and enhanced ${inputCount} search inputs with demo functionality`);
                    return replacedCount + inputCount;
                }

                // AI-POWERED: Run search replacement with caching
                console.log(' SEARCH INJECTION: Starting AI-powered search button replacement...');
                console.log(' Current domain:', window.location.hostname);
                console.log(' Page title:', document.title);

                // Event delegation approach - intercept clicks on ANY search elements
                document.addEventListener('click', function(e) {
                    const target = e.target;

                    // Check if clicked element matches our search patterns
                    if (isSearchElement(target)) {
                        console.log(' CLICK: Search element clicked via delegation!', target);
                        e.preventDefault();
                        e.stopPropagation();
                        showSearchInput();
                        return false;
                    }
                }, true); // Use capture phase to intercept before other handlers

                // Function to detect if an element is a search element
                function isSearchElement(element) {
                    if (!element) return false;

                    const text = (element.textContent || '').toLowerCase();
                    const className = (element.className || '').toLowerCase();
                    const id = (element.id || '').toLowerCase();
                    const ariaLabel = (element.getAttribute('aria-label') || '').toLowerCase();
                    const placeholder = (element.getAttribute('placeholder') || '').toLowerCase();

                    // Agilent-specific patterns
                    if (className.includes('homesearchimg') || className.includes('tt-hint') || className.includes('searchcontainer')) {
                        console.log(' MATCH: Agilent pattern detected', element);
                        return true;
                    }

                    // General search patterns
                    if (className.includes('search') || id.includes('search') || text.includes('search') ||
                        ariaLabel.includes('search') || placeholder.includes('search')) {
                        console.log(' MATCH: General search pattern detected', element);
                        return true;
                    }

                    return false;
                }

                console.log(' Event delegation for search elements is now active');

                // SIMPLIFIED: Only watch for major DOM changes, not every mutation
                const observer = new MutationObserver(function(mutations) {
                    let shouldCheck = false;
                    mutations.forEach(function(mutation) {
                        // Only check if significant nodes were added (not just text changes)
                        if (mutation.addedNodes.length > 3) {
                            shouldCheck = true;
                        }
                    });
                    if (shouldCheck) {
                        setTimeout(replaceSearchButtons, 500); // Debounced
                    }
                });

                observer.observe(document.body, {
                    childList: true,
                    subtree: false // Don't watch deep changes - too expensive
                });

                console.log('Demo search replacement complete. Dynamic monitoring active.');
            });
        '''

        # Find body and append our script
        body = soup.find('body')
        if body:
            body.append(script)
            logger.info(f"Search injection script added successfully to {target_url}")
        else:
            logger.warning(f"No body tag found for search injection in {target_url}")

        return str(soup)

    except Exception as e:
        logger.warning(f"Failed to inject search functionality: {e}")
        return html_content

def create_native_search_template(styling_dna: Dict[str, str]) -> str:
    """Create search template that looks native to the target site using extracted styling DNA"""

    # Extract styling values
    brand_name = styling_dna.get("brand_name", "Search")
    primary_font = styling_dna.get("primary_font", "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif")
    text_color = styling_dna.get("text_color", "#333333")
    background_color = styling_dna.get("background_color", "#ffffff")
    brand_color = styling_dna.get("brand_color", "#0066cc")
    link_color = styling_dna.get("link_color", "#0066cc")
    header_bg = styling_dna.get("header_bg", "#ffffff")
    header_border = styling_dna.get("header_border", "1px solid #e0e0e0")
    container_width = styling_dna.get("container_width", "1200px")
    content_padding = styling_dna.get("content_padding", "20px")
    header_padding = styling_dna.get("header_padding", "15px 20px")
    logo_url = styling_dna.get("logo_url", "")
    nav_structure = styling_dna.get("nav_structure", "")

    # Build logo HTML
    logo_html = ""
    if logo_url:
        logo_html = f'<img src="{logo_url}" alt="{brand_name}" class="site-logo" style="height: 40px; vertical-align: middle; margin-right: 15px;">'

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>Search Results - {brand_name}</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {{
            box-sizing: border-box;
        }}

        body {{
            font-family: {primary_font};
            color: {text_color};
            background-color: {background_color};
            margin: 0;
            padding: 0;
            line-height: 1.6;
        }}

        .site-header {{
            background: {header_bg};
            border-bottom: {header_border};
            padding: {header_padding};
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .header-content {{
            max-width: {container_width};
            margin: 0 auto;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        .brand-section {{
            display: flex;
            align-items: center;
        }}

        .brand-name {{
            font-size: 24px;
            font-weight: bold;
            color: {brand_color};
            text-decoration: none;
        }}

        .nav-wrapper {{
            display: flex;
            align-items: center;
            gap: 30px;
        }}

        .utility-nav {{
            margin-left: auto;
            display: flex;
            gap: 15px;
        }}

        .utility-nav a {{
            color: {text_color};
            text-decoration: none;
            font-size: 14px;
            padding: 5px 10px;
            border-radius: 4px;
            transition: background-color 0.2s;
        }}

        .utility-nav a:hover {{
            background-color: rgba(0,0,0,0.05);
        }}

        .main-nav {{
            display: flex;
            gap: 25px;
        }}

        .main-nav a {{
            color: {text_color};
            text-decoration: none;
            padding: 10px 15px;
            border-radius: 4px;
            font-weight: 500;
            transition: all 0.2s;
        }}

        .main-nav a:hover {{
            background-color: rgba(0,0,0,0.05);
            color: {brand_color};
        }}

        .container {{
            max-width: {container_width};
            margin: 0 auto;
            padding: {content_padding};
        }}

        .search-header {{
            background: {background_color};
            padding: 30px 0;
            border-bottom: 1px solid #e0e0e0;
        }}

        .back-button {{
            background: {brand_color};
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            font-size: 14px;
            cursor: pointer;
            margin-bottom: 20px;
            transition: opacity 0.2s;
        }}

        .back-button:hover {{
            opacity: 0.8;
        }}

        .search-info {{
            font-size: 14px;
            color: #666;
            margin-bottom: 20px;
        }}

        .search-query {{
            font-weight: 600;
            color: {brand_color};
        }}

        .results-count {{
            color: #666;
        }}

        .search-results {{
            background: {background_color};
        }}

        .result-item {{
            padding: 20px 0;
            border-bottom: 1px solid #f0f0f0;
        }}

        .result-item:last-child {{
            border-bottom: none;
        }}

        .result-title {{
            font-size: 20px;
            font-weight: 500;
            margin-bottom: 5px;
        }}

        .result-title a {{
            color: {link_color};
            text-decoration: none;
        }}

        .result-title a:hover {{
            text-decoration: underline;
        }}

        .result-url {{
            color: #006621;
            font-size: 14px;
            margin-bottom: 8px;
            word-break: break-all;
        }}

        .result-snippet {{
            color: #545454;
            line-height: 1.5;
            font-size: 14px;
        }}

        .no-results {{
            text-align: center;
            padding: 60px 20px;
            color: #666;
        }}

        .no-results h3 {{
            color: {brand_color};
            margin-bottom: 10px;
        }}

        /* Responsive design */
        @media (max-width: 768px) {{
            .header-content {{
                flex-direction: column;
                gap: 15px;
            }}

            .main-nav {{
                flex-wrap: wrap;
                justify-content: center;
            }}

            .container {{
                padding: 15px;
            }}
        }}
    </style>
</head>
<body>
    <header class="site-header">
        <div class="header-content">
            <div class="brand-section">
                {logo_html}
                <a href="/proxy/" class="brand-name">{brand_name}</a>
            </div>
        </div>
    </header>

    <main class="container">
        <div class="search-header">
            <button class="back-button" onclick="goBack()">← Back</button>
            <div class="search-info">
                Search results for: <span class="search-query">{{{{SEARCH_QUERY}}}}</span>
                <span class="results-count">({{{{TOTAL_RESULTS}}}} found)</span>
            </div>
        </div>

        <div class="search-results">
            {{{{SEARCH_RESULTS}}}}
        </div>
    </main>

    <script>
        function goBack() {{
            if (window.history.length > 1) {{
                window.history.back();
            }} else {{
                // Fallback to homepage if no history
                window.location.href = '/proxy/';
            }}
        }}
    </script>
</body>
</html>"""

async def create_fallback_template(target_url: str) -> str:
    """Create native-looking template using site styling DNA extraction"""
    try:
        # Extract styling DNA from target site
        styling_dna = await extract_site_styling_dna(target_url)

        # Create native template using extracted styling
        return create_native_search_template(styling_dna)

    except Exception as e:
        logger.error(f"Failed to create native template for {target_url}: {e}")

        # Fallback to basic template if extraction fails
        domain = urlparse(target_url).netloc
        basic_styling = {
            "brand_name": domain.replace('www.', '').split('.')[0].upper(),
            "primary_font": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
            "text_color": "#333333",
            "background_color": "#ffffff",
            "brand_color": "#0066cc",
            "link_color": "#0066cc",
            "header_bg": "#ffffff",
            "header_border": "1px solid #e0e0e0",
            "container_width": "1200px",
            "content_padding": "20px",
            "header_padding": "15px 20px",
            "logo_url": "",
            "nav_structure": ""
        }

        return create_native_search_template(basic_styling)

async def get_search_template(target_url: str) -> str:
    """
    Get cached search template for specific target site

    Now uses styling DNA extraction to create native-looking templates

    Args:
        target_url: Current proxy target URL

    Returns:
        HTML template string that looks native to the target site
    """
    domain = urlparse(target_url).netloc

    # Check if we have cached template for this domain
    if domain not in search_templates_cache:
        logger.info(f"No cached template for {domain}, creating template...")

        try:
            # TEMPORARY: Skip styling DNA extraction for strict sites to avoid 403 errors
            # TODO: Re-enable after fixing rate limiting issues
            if any(strict_domain in domain for strict_domain in ['rmit.edu.au', 'edu.au', 'gov.au']):
                logger.info(f"Skipping styling DNA extraction for strict site: {domain}")
                raise Exception("Skipping styling DNA for strict site")

            # Extract styling DNA from target site
            styling_dna = await extract_site_styling_dna(target_url)

            # Create native template using extracted styling
            template_html = create_native_search_template(styling_dna)

            # Cache the template and styling DNA
            search_templates_cache[domain] = {
                "template_html": template_html,
                "styling_dna": styling_dna,
                "cached_at": datetime.now(),
                "target_url": target_url,
                "domain": domain
            }

            logger.info(f"Cached native template for {domain} with brand: {styling_dna['brand_name']}")

        except Exception as e:
            logger.warning(f"Using basic template for {domain}: {e}")

            # Fallback to basic template
            domain_clean = domain.replace('www.', '').split('.')[0].upper()
            basic_styling = {
                "brand_name": domain_clean,
                "primary_font": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                "text_color": "#333333",
                "background_color": "#ffffff",
                "brand_color": "#0066cc",
                "link_color": "#0066cc",
                "header_bg": "#ffffff",
                "header_border": "1px solid #e0e0e0",
                "container_width": "1200px",
                "content_padding": "20px",
                "header_padding": "15px 20px",
                "logo_url": "",
                "nav_structure": ""
            }

            template_html = create_native_search_template(basic_styling)

            search_templates_cache[domain] = {
                "template_html": template_html,
                "styling_dna": basic_styling,
                "cached_at": datetime.now(),
                "target_url": target_url,
                "domain": domain
            }

    else:
        logger.info(f"Using cached template for {domain}")

    return search_templates_cache[domain]["template_html"]

def render_search_results(template_html: str, search_results: Dict[str, Any], query: str, proxy_base: str = "http://localhost:8000/proxy") -> str:
    """
    Render search results into HTML template with target site styling

    Args:
        template_html: The cached template HTML from target site
        search_results: OpenSearch results from opensearch_integration.search()
        query: The search query
        proxy_base: Base URL for proxy rewriting

    Returns:
        Complete HTML page with search results rendered in target site styling
    """
    try:
        # Extract results data
        hits = search_results.get("hits", [])
        total_hits = search_results.get("total_hits", 0)

        # Generate HTML for individual search results
        results_html = ""
        for hit in hits:
            # Rewrite result URL to proxy URL
            original_url = hit.get("url", "")
            if original_url.startswith("http"):
                # Convert absolute URL to proxy URL
                parsed_url = urlparse(original_url)
                proxy_url = f"{proxy_base}{parsed_url.path}"
                if parsed_url.query:
                    proxy_url += f"?{parsed_url.query}"
            else:
                proxy_url = f"{proxy_base}{original_url}"

            # Extract result data
            title = hit.get("title", "Untitled")
            snippet = hit.get("meta_desc", "")

            # Use highlight snippet if available
            highlights = hit.get("highlight", {})
            if highlights.get("content_md"):
                snippet = highlights["content_md"][0]
            elif highlights.get("meta_desc"):
                snippet = highlights["meta_desc"][0]
            elif not snippet and hit.get("source", {}).get("meta_desc"):
                snippet = hit["source"]["meta_desc"][:200] + "..."

            # Extract domain and page type for modern template
            domain = hit.get("domain", "")
            page_type = hit.get("source", {}).get("page_type", "")

            # Get brand color from template cache if available
            brand_color = "#3498db"  # Default
            domain_key = urlparse(proxy_base).netloc
            if domain_key in search_templates_cache:
                brand_color = search_templates_cache[domain_key]["styling_dna"].get("brand_color", "#3498db")

            # Build individual result HTML using modern template
            result_html = create_result_item_html(
                title=title,
                url=proxy_url,
                snippet=snippet,
                domain=domain,
                page_type=page_type,
                brand_color=brand_color
            )
            results_html += result_html

        # If no results found
        if not results_html:
            results_html = create_no_results_html(query)

        # Replace placeholders in template
        # For fallback template (has placeholders)
        if "{{SEARCH_QUERY}}" in template_html:
            rendered_html = template_html.replace("{{SEARCH_QUERY}}", query)
            rendered_html = rendered_html.replace("{{TOTAL_RESULTS}}", str(total_hits))
            rendered_html = rendered_html.replace("{{SEARCH_RESULTS}}", results_html)
        else:
            # For real site templates - inject results intelligently
            rendered_html = inject_results_into_template(template_html, results_html, query, total_hits)

        logger.info(f"Rendered search results: {len(hits)} results for query '{query}'")
        return rendered_html

    except Exception as e:
        logger.error(f"Error rendering search results: {e}")
        # Return fallback template on error
        fallback_template = create_fallback_template("localhost")
        return render_search_results(fallback_template, search_results, query, proxy_base)

def inject_results_into_template(template_html: str, results_html: str, query: str, total_hits: int) -> str:
    """
    Intelligently inject search results into a real site template

    This function attempts to find where to inject results in a real site's HTML structure
    by looking for common patterns like search result containers, content areas, etc.

    Args:
        template_html: Original site template HTML
        results_html: Generated search results HTML
        query: Search query
        total_hits: Number of results found

    Returns:
        Modified HTML with injected search results
    """
    try:
        soup = BeautifulSoup(template_html, 'html.parser')

        # Try to find existing search results container
        result_containers = [
            soup.find(class_=re.compile(r'search.*result', re.I)),
            soup.find(class_=re.compile(r'result.*list', re.I)),
            soup.find(class_=re.compile(r'content.*result', re.I)),
            soup.find(id=re.compile(r'search.*result', re.I)),
            soup.find(id=re.compile(r'result', re.I)),
            soup.find('main'),
            soup.find(class_=re.compile(r'main.*content', re.I)),
            soup.find(class_=re.compile(r'content', re.I))
        ]

        # Find the first valid container
        target_container = None
        for container in result_containers:
            if container:
                target_container = container
                break

        if target_container:
            # Clear existing content and inject our results
            target_container.clear()

            # Add search query info
            query_info = soup.new_tag("div", **{"class": "search-info"})
            query_info.string = f"Search results for: {query} ({total_hits} found)"
            target_container.append(query_info)

            # Add our results
            results_container = soup.new_tag("div", **{"class": "opensearch-results"})
            results_container.append(BeautifulSoup(results_html, 'html.parser'))
            target_container.append(results_container)

            logger.info(f"Injected results into {target_container.name} with class/id: {target_container.get('class')} / {target_container.get('id')}")
        else:
            # Fallback: inject into body
            body = soup.find('body')
            if body:
                search_section = soup.new_tag("div", **{"class": "injected-search-results", "style": "margin: 20px;"})
                search_section.append(BeautifulSoup(f"<h2>Search Results for: {query}</h2>{results_html}", 'html.parser'))
                body.insert(0, search_section)
                logger.info("Injected results into body as fallback")

        return str(soup)

    except Exception as e:
        logger.error(f"Error injecting results into template: {e}")
        # Return original template with appended results as last resort
        return template_html + f"<div style='margin: 20px;'><h2>Search Results for: {query}</h2>{results_html}</div>"

class ProxyConfig(BaseModel):
    target_url: str
    run_id: Optional[str] = None
    enabled: bool = True

@app.get("/")
async def proxy_status():
    return {
        "message": "Auto-Proxy Server", 
        "target_url": proxy_config["target_url"],
        "enabled": proxy_config["enabled"],
        "run_id": proxy_config["run_id"],
        "crawl_completed": proxy_config["crawl_completed"]
    }

@app.post("/auto-configure")
async def auto_configure_from_crawl(config: ProxyConfig):
    """Auto-configure proxy when crawl completes"""
    proxy_config["target_url"] = config.target_url.rstrip("/")
    proxy_config["run_id"] = config.run_id
    proxy_config["enabled"] = config.enabled
    proxy_config["crawl_completed"] = True

    # Initialize OpenSearch for search injection
    domain = urlparse(config.target_url).netloc
    opensearch_initialized = initialize_opensearch(domain)

    logger.info(f"Auto-proxy configured from crawl - Target: {proxy_config['target_url']}, Run ID: {config.run_id}")
    if opensearch_initialized:
        logger.info(f"OpenSearch search injection enabled for {domain}")

    return {
        "message": "Auto-proxy configured from crawl completion",
        "proxy_url": f"http://localhost:8000/proxy/",
        "config": proxy_config,
        "search_injection": opensearch_initialized,
        "opensearch_index": opensearch_index_name
    }

@app.get("/config")
async def get_proxy_config():
    """Get current proxy configuration"""
    return proxy_config

@app.post("/clear-template-cache")
async def clear_template_cache():
    """Clear the search template cache to force fresh template generation"""
    global search_templates_cache
    cache_count = len(search_templates_cache)
    search_templates_cache.clear()
    logger.info(f"Cleared {cache_count} cached templates")
    return {
        "message": f"Cleared {cache_count} cached templates",
        "cache_cleared": True
    }

# Vision endpoints moved to separate ai_vision_service.py (port 8001)

def rewrite_urls_in_html(html_content: str, target_url: str, proxy_base: str = "http://localhost:8000/proxy") -> str:
    """Rewrite URLs in HTML to work through proxy"""
    soup = BeautifulSoup(html_content, 'html.parser')
    parsed_target = urlparse(target_url)
    target_base = f"{parsed_target.scheme}://{parsed_target.netloc}"
    
    # Handle base tag for relative URLs (but be careful with existing navigation)
    head = soup.find('head')
    if head:
        # Remove existing base tags that might conflict
        existing_base = head.find('base')
        if existing_base:
            # If there's already a base tag, leave it but make sure it points to target domain through proxy
            current_base = existing_base.get('href', '')
            if current_base and not current_base.startswith(proxy_base):
                if current_base.startswith('http'):
                    # Absolute base URL - convert to proxy
                    parsed_base = urlparse(current_base)
                    if parsed_base.netloc in [parsed_target.netloc, f"www.{parsed_target.netloc}"]:
                        proxy_base_url = f"{proxy_base}{parsed_base.path}"
                        existing_base['href'] = proxy_base_url
                elif current_base.startswith('/'):
                    # Relative base URL - convert to proxy
                    existing_base['href'] = f"{proxy_base}{current_base}"
        else:
            # Only add base tag if there wasn't one originally
            # This prevents breaking sites that don't expect a base tag
            pass
        
    
    # Rewrite common URL attributes
    url_attrs = [
        ('a', 'href'), ('link', 'href'), ('script', 'src'), ('img', 'src'),
        ('form', 'action'), ('iframe', 'src'), ('source', 'src'), 
        ('embed', 'src'), ('object', 'data')
    ]
    
    for tag_name, attr in url_attrs:
        for tag in soup.find_all(tag_name, {attr: True}):
            original_url = tag[attr].strip()
            
            # Skip empty URLs, javascript:, mailto:, tel:, data: URLs
            if not original_url or any(original_url.startswith(prefix) for prefix in ['javascript:', 'mailto:', 'tel:', 'data:', '#']):
                continue
                
            # Convert to absolute URL first
            if original_url.startswith('//'):
                absolute_url = f"{parsed_target.scheme}:{original_url}"
            elif original_url.startswith('/'):
                absolute_url = f"{target_base}{original_url}"
            elif not original_url.startswith(('http://', 'https://')):
                # Handle relative URLs properly
                absolute_url = urljoin(target_url, original_url)
            else:
                absolute_url = original_url
            
            # Parse the absolute URL
            parsed_abs = urlparse(absolute_url)
            
            # Define target domains (main domain and www variant)
            target_domains = [parsed_target.netloc]
            if parsed_target.netloc.startswith('www.'):
                target_domains.append(parsed_target.netloc[4:])  # Remove www.
            else:
                target_domains.append(f"www.{parsed_target.netloc}")  # Add www.
            
            # Always rewrite URLs that belong to the target domain OR have no domain (relative URLs)
            should_rewrite = (
                not parsed_abs.netloc or  # Relative URLs with no domain
                parsed_abs.netloc in target_domains  # Same domain URLs
            )
            
            if should_rewrite:
                proxy_url = f"{proxy_base}{parsed_abs.path}"
                if parsed_abs.query:
                    proxy_url += f"?{parsed_abs.query}"
                if parsed_abs.fragment:
                    proxy_url += f"#{parsed_abs.fragment}"
                
                # Debug logging for URL rewriting
                print(f"REWRITE: {original_url} -> {proxy_url}")
                tag[attr] = proxy_url
            else:
                # Debug: log URLs we're NOT rewriting
                print(f"NOT REWRITING (external domain): {original_url} -> {parsed_abs.netloc}")
    
    return str(soup)

def rewrite_urls_in_css(css_content: str, target_url: str, proxy_base: str = "http://localhost:8000/proxy") -> str:
    """Rewrite URLs in CSS to work through proxy"""
    parsed_target = urlparse(target_url)
    target_base = f"{parsed_target.scheme}://{parsed_target.netloc}"
    
    # Pattern to match url() in CSS
    url_pattern = r'url\s*\(\s*["\']?([^"\')\s]+)["\']?\s*\)'
    
    def replace_css_url(match):
        original_url = match.group(1)
        
        # Skip data URLs
        if original_url.startswith('data:'):
            return match.group(0)
        
        # Convert to absolute URL
        if original_url.startswith('//'):
            absolute_url = f"{parsed_target.scheme}:{original_url}"
        elif original_url.startswith('/'):
            absolute_url = f"{target_base}{original_url}"
        elif not original_url.startswith(('http://', 'https://')):
            absolute_url = urljoin(target_url, original_url)
        else:
            absolute_url = original_url
        
        # Rewrite to proxy URL if same domain
        parsed_abs = urlparse(absolute_url)
        if parsed_abs.netloc == parsed_target.netloc:
            proxy_url = f"{proxy_base}{parsed_abs.path}"
            if parsed_abs.query:
                proxy_url += f"?{parsed_abs.query}"
            return f'url("{proxy_url}")'
        
        return match.group(0)
    
    return re.sub(url_pattern, replace_css_url, css_content)

def clean_response_headers(headers: dict) -> dict:
    """Clean headers for proxy response"""
    # Remove problematic headers
    cleaned = {k: v for k, v in headers.items() if k.lower() not in [
        'content-encoding', 'transfer-encoding', 'content-length',
        'content-security-policy', 'x-frame-options', 
        'strict-transport-security'
    ]}
    
    # Add CORS headers
    cleaned.update({
        'access-control-allow-origin': '*',
        'access-control-allow-methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'access-control-allow-headers': '*',
    })
    
    return cleaned

async def handle_search_request(query: str, original_path: str) -> HTMLResponse:
    """
    Handle search API request using OpenSearch (US-65 Implementation)

    Returns properly formatted HTML pages with proxy-rewritten URLs that maintain
    target site styling and provide seamless search experience.
    """
    if not opensearch_integration or not opensearch_index_name:
        logger.warning("Search request intercepted but OpenSearch not configured")
        # Return fallback HTML instead of JSON error
        current_target = proxy_config.get("target_url", "localhost")
        fallback_template = create_fallback_template(current_target)
        error_html = fallback_template.replace("{{SEARCH_QUERY}}", query)
        error_html = error_html.replace("{{TOTAL_RESULTS}}", "0")
        error_html = error_html.replace("{{SEARCH_RESULTS}}",
            "<div class='error'>Search service temporarily unavailable. Please try again later.</div>")
        return HTMLResponse(content=error_html, status_code=503)

    try:
        # 1. Get cached search template for current target site
        current_target = proxy_config["target_url"]
        template = await get_search_template(current_target)

        # 2. Get OpenSearch results
        results = opensearch_integration.search(
            query=query,
            index_name=opensearch_index_name,
            size=10
        )

        # 3. Generate HTML page using template + results with URL rewriting
        html_content = render_search_results(template, results, query)

        # 4. Apply proxy URL rewriting to the entire page
        final_html = rewrite_urls_in_html(html_content, current_target)

        logger.info(f"HTML search handled: '{query}' -> {results.get('total_hits', 0)} results")
        return HTMLResponse(content=final_html)

    except Exception as e:
        logger.error(f"HTML search error for query '{query}': {e}")

        # Return error page in target site styling
        try:
            current_target = proxy_config.get("target_url", "localhost")
            template = await get_search_template(current_target)
            error_results = {"hits": [], "total_hits": 0}
            error_html = render_search_results(template, error_results, query)
            final_html = rewrite_urls_in_html(error_html, current_target)
            return HTMLResponse(content=final_html, status_code=500)
        except:
            # Last resort fallback
            fallback_template = create_fallback_template("localhost")
            error_html = fallback_template.replace("{{SEARCH_QUERY}}", query)
            error_html = error_html.replace("{{TOTAL_RESULTS}}", "0")
            error_html = error_html.replace("{{SEARCH_RESULTS}}",
                f"<div class='error'>Search failed: {str(e)}</div>")
            return HTMLResponse(content=error_html, status_code=500)

@app.api_route("/proxy/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_request(request: Request, path: str):
    """Proxy all requests to the configured target site with URL rewriting"""

    # Exclude our API endpoints from proxying
    api_endpoints = ["test", "ai-vision-analyze", "ai-cache"]
    if any(path.startswith(endpoint) for endpoint in api_endpoints):
        return Response("API endpoint not found", status_code=404)

    if not proxy_config["enabled"] or not proxy_config["target_url"]:
        return Response("Proxy not configured or disabled", status_code=503)

    # Check for search API interception (US-63: API Replacement Search Injection)
    if proxy_config["search_injection_enabled"]:
        query_params = dict(request.query_params)

        # Enhanced debug logging for all requests to catch CommBank's real search API
        logger.info(f"DEBUG: Method={request.method}, Path='{path}', Params={query_params}")

        # Log POST requests which might contain search data
        if request.method == "POST":
            try:
                body = await request.body()
                if body:
                    body_str = body.decode('utf-8')[:200]  # First 200 chars
                    logger.info(f"DEBUG: POST body preview: {body_str}")
            except:
                pass

        is_search = is_search_api_request(path, query_params)
        logger.info(f"DEBUG: is_search_api_request={is_search}")

        # Detect if this is a search API request
        if is_search:
            search_query = extract_search_query(query_params)

            # Also try to extract query from POST body for SPAs
            if not search_query and request.method == "POST":
                try:
                    body = await request.body()
                    body_str = body.decode('utf-8')
                    # Try to find search terms in JSON or form data
                    import json
                    if body_str:
                        if body_str.startswith('{'):
                            # JSON body
                            body_data = json.loads(body_str)
                            for key in ['query', 'searchTerm', 'q', 'text', 'search']:
                                if key in body_data:
                                    search_query = body_data[key]
                                    break
                        else:
                            # Form data or other format
                            if 'search=' in body_str or 'query=' in body_str:
                                # Try to extract from URL-encoded data
                                from urllib.parse import parse_qs
                                parsed = parse_qs(body_str)
                                for key in ['query', 'searchTerm', 'q', 'text', 'search']:
                                    if key in parsed:
                                        search_query = parsed[key][0]
                                        break
                except:
                    pass

            logger.info(f"DEBUG: extracted query='{search_query}'")
            if search_query:
                logger.info(f"Search API intercepted: {path} -> query: '{search_query}'")

                # For SPAs, return JSON API response instead of HTML
                if any(api_indicator in path.lower() for api_indicator in ['api/', 'graphql', '.json']) or request.method == "POST":
                    logger.info(f"SPA API search detected: {path}")
                    return await handle_spa_search_api(search_query, path, proxy_config["target_url"])
                else:
                    # Traditional HTML search pages
                    return await handle_search_request(search_query, path)

    # Build target URL for normal proxying
    target_url = f"{proxy_config['target_url']}/{path}"
    if request.url.query:
        target_url += f"?{request.url.query}"

    logger.info(f"Proxying: {request.method} {target_url}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # Prepare headers - remove host header to avoid conflicts (original simple approach)
            headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}
            
            # Forward the request
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=await request.body()
            )

            # Handle 403 Forbidden responses
            if response.status_code == 403:
                logger.warning(f"Target site returned 403 Forbidden for {target_url}")
                return Response(
                    content=f"<html><body><h1>Access Denied</h1><p>The target site ({proxy_config['target_url']}) is blocking proxy requests.</p><p>This is common with educational institutions and some corporate sites.</p></body></html>",
                    status_code=403,
                    media_type="text/html"
                )

            # Handle other error status codes
            if response.status_code >= 400:
                logger.warning(f"Target site returned {response.status_code} for {target_url}")
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=clean_response_headers(dict(response.headers))
                )

            # Clean headers for successful responses
            clean_headers = clean_response_headers(dict(response.headers))

            # Get content type
            content_type = response.headers.get("content-type", "").lower()
            
            # Rewrite URLs for HTML and CSS content
            if "text/html" in content_type:
                try:
                    rewritten_content = rewrite_urls_in_html(
                        response.text,
                        proxy_config["target_url"]
                    )

                    # Re-enable search injection for testing
                    if is_dynamic_search_site(proxy_config["target_url"]):
                        rewritten_content = inject_search_functionality(rewritten_content, proxy_config["target_url"])
                    logger.info(f"Rewrote HTML content for {target_url}")
                    return HTMLResponse(
                        content=rewritten_content,
                        status_code=response.status_code,
                        headers=clean_headers
                    )
                except Exception as e:
                    logger.warning(f"HTML rewriting failed: {e}")
                    # Fall back to original content
            
            elif "text/css" in content_type:
                try:
                    rewritten_content = rewrite_urls_in_css(
                        response.text,
                        proxy_config["target_url"]
                    )
                    return Response(
                        content=rewritten_content,
                        status_code=response.status_code,
                        headers=clean_headers,
                        media_type="text/css"
                    )
                except Exception as e:
                    logger.warning(f"CSS rewriting failed: {e}")
                    # Fall back to original content
            
            # For all other content types, return as-is
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=clean_headers
            )
            
    except httpx.RequestError as e:
        logger.error(f"Proxy error: {e}")
        return Response(f"Proxy error: {str(e)}", status_code=502)

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def catch_all_proxy(request: Request, path: str):
    """Catch-all handler for requests that don't match /proxy/ prefix"""

    # Exclude our API endpoints and non-proxy routes
    print(f"[DEBUG CATCH-ALL] Processing path: '{path}'")
    excluded_paths = ["vision", "config", "auto-configure", "clear-template-cache"]

    # Check if path starts with any excluded path
    for excluded in excluded_paths:
        if path.startswith(excluded):
            print(f"[DEBUG CATCH-ALL] Path '{path}' starts with '{excluded}', excluding")
            return Response("Route not found", status_code=404)

    if path == "":
        print(f"[DEBUG CATCH-ALL] Empty path, excluding")
        return Response("Route not found", status_code=404)

    if not proxy_config["enabled"] or not proxy_config["target_url"]:
        return Response("Proxy not configured", status_code=503)

    # Skip if this is a proxy request (shouldn't happen but safety check)
    if path.startswith("proxy/"):
        return Response("Invalid proxy path", status_code=400)
    
    # Handle requests that don't start with /proxy/ by forwarding to target
    target_url = f"{proxy_config['target_url']}/{path}"
    if request.url.query:
        target_url += f"?{request.url.query}"
    
    logger.info(f"Catch-all proxying: {request.method} {target_url}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # Remove host header to avoid conflicts (original simple approach)
            headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}
            
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=await request.body()
            )
            
            clean_headers = clean_response_headers(dict(response.headers))
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=clean_headers
            )
            
    except httpx.RequestError as e:
        logger.error(f"Catch-all proxy error: {e}")
        return Response(f"Resource not found: {path}", status_code=404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)