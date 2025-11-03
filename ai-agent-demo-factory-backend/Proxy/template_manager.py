#!/usr/bin/env python3
"""
Template Manager Module
Handles template fetching, styling DNA extraction, and template caching
"""
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from typing import Dict, List
from datetime import datetime
import httpx
import re
import logging

try:
    import cssutils
    HAVE_CSSUTILS = True
except ImportError:
    HAVE_CSSUTILS = False

from Proxy.search_templates import create_native_search_template

logger = logging.getLogger(__name__)

# Template caching for HTML search results
search_templates_cache = {}


async def extract_site_styling_dna(target_url: str) -> Dict[str, str]:
    """
    Extract the visual DNA of any site to make search results look native

    Extracts fonts, colors, spacing, branding elements that make each site unique

    Args:
        target_url: Target site base URL

    Returns:
        Dict containing styling DNA (fonts, colors, brand info, etc.)
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


def clear_template_cache() -> int:
    """
    Clear the search template cache

    Returns:
        Number of cached templates cleared
    """
    global search_templates_cache
    cache_count = len(search_templates_cache)
    search_templates_cache.clear()
    logger.info(f"Cleared {cache_count} cached templates")
    return cache_count
