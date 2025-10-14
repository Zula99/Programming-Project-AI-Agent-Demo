#!/usr/bin/env python3
"""
URL Rewriter Module
Handles rewriting URLs in HTML, CSS, and other content to work through the proxy
"""
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import re
import logging

logger = logging.getLogger(__name__)


def rewrite_urls_in_html(html_content: str, target_url: str, proxy_base: str = "http://localhost:8000/proxy") -> str:
    """
    Rewrite URLs in HTML to work through proxy

    Args:
        html_content: Original HTML content
        target_url: Target site base URL
        proxy_base: Proxy base URL for rewriting

    Returns:
        HTML content with rewritten URLs
    """
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


    # Rewrite common URL attributes (including lazy-loading data attributes)
    url_attrs = [
        ('a', 'href'), ('link', 'href'), ('script', 'src'), ('img', 'src'),
        ('form', 'action'), ('iframe', 'src'), ('source', 'src'),
        ('embed', 'src'), ('object', 'data'),
        # Lazy-loading attributes
        ('img', 'data-src'), ('img', 'data-srcset'), ('source', 'data-src'),
        ('source', 'data-srcset'), ('div', 'data-src'), ('div', 'data-background'),
        ('section', 'data-src'), ('section', 'data-background'),
        # Responsive images
        ('img', 'srcset'), ('source', 'srcset')
    ]

    for tag_name, attr in url_attrs:
        for tag in soup.find_all(tag_name, {attr: True}):
            original_url = tag[attr].strip()

            # Handle srcset specially (comma-separated list of "url size_descriptor")
            if 'srcset' in attr.lower():
                srcset_parts = []
                for srcset_item in original_url.split(','):
                    srcset_item = srcset_item.strip()
                    if not srcset_item:
                        continue

                    # Split into URL and descriptor (e.g., "image.jpg 300w")
                    parts = srcset_item.split()
                    if not parts:
                        continue

                    url_part = parts[0]
                    descriptor = ' '.join(parts[1:]) if len(parts) > 1 else ''

                    # Skip data URLs
                    if url_part.startswith('data:'):
                        srcset_parts.append(srcset_item)
                        continue

                    # Convert to absolute URL
                    if url_part.startswith('//'):
                        absolute_url = f"{parsed_target.scheme}:{url_part}"
                    elif url_part.startswith('/'):
                        absolute_url = f"{target_base}{url_part}"
                    elif not url_part.startswith(('http://', 'https://')):
                        absolute_url = urljoin(target_url, url_part)
                    else:
                        absolute_url = url_part

                    parsed_abs = urlparse(absolute_url)
                    target_domains = [parsed_target.netloc]
                    if parsed_target.netloc.startswith('www.'):
                        target_domains.append(parsed_target.netloc[4:])
                    else:
                        target_domains.append(f"www.{parsed_target.netloc}")

                    if not parsed_abs.netloc or parsed_abs.netloc in target_domains:
                        proxy_url = f"{proxy_base}{parsed_abs.path}"
                        if parsed_abs.query:
                            proxy_url += f"?{parsed_abs.query}"
                        if descriptor:
                            srcset_parts.append(f"{proxy_url} {descriptor}")
                        else:
                            srcset_parts.append(proxy_url)
                    else:
                        srcset_parts.append(srcset_item)

                tag[attr] = ', '.join(srcset_parts)
                continue

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
                logger.debug(f"REWRITE: {original_url} -> {proxy_url}")
                tag[attr] = proxy_url
            else:
                # Debug: log URLs we're NOT rewriting
                logger.debug(f"NOT REWRITING (external domain): {original_url} -> {parsed_abs.netloc}")

    # UNIVERSAL: Rewrite ANY data-* attribute that looks like a URL
    # This handles site-specific attributes like data-image-desktop-src, data-bg-url, etc.
    data_attr_count = 0
    for tag in soup.find_all():
        for attr_name in list(tag.attrs.keys()):
            # Check if it's a data-* attribute
            if attr_name.startswith('data-'):
                try:
                    # Ensure it's a string and strip whitespace
                    attr_value = tag[attr_name]
                    if isinstance(attr_value, list):
                        attr_value = ' '.join(attr_value)
                    attr_value = str(attr_value).strip()

                    # Skip empty values
                    if not attr_value:
                        continue

                    # Check if value looks like a URL
                    # (starts with /, http, or contains common resource extensions)
                    is_url_like = (
                        attr_value.startswith('/') or
                        attr_value.startswith('http://') or
                        attr_value.startswith('https://') or
                        any(ext in attr_value for ext in ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.css', '.js'])
                    )

                    if is_url_like and not any(attr_value.startswith(prefix) for prefix in ['javascript:', 'mailto:', 'tel:', 'data:', '#']):
                        # Convert to absolute URL
                        if attr_value.startswith('//'):
                            absolute_url = f"{parsed_target.scheme}:{attr_value}"
                        elif attr_value.startswith('/'):
                            absolute_url = f"{target_base}{attr_value}"
                        elif not attr_value.startswith(('http://', 'https://')):
                            absolute_url = urljoin(target_url, attr_value)
                        else:
                            absolute_url = attr_value

                        parsed_abs = urlparse(absolute_url)
                        target_domains = [parsed_target.netloc]
                        if parsed_target.netloc.startswith('www.'):
                            target_domains.append(parsed_target.netloc[4:])
                        else:
                            target_domains.append(f"www.{parsed_target.netloc}")

                        # Rewrite if same domain or no domain
                        if not parsed_abs.netloc or parsed_abs.netloc in target_domains:
                            proxy_url = f"{proxy_base}{parsed_abs.path}"
                            if parsed_abs.query:
                                proxy_url += f"?{parsed_abs.query}"
                            if parsed_abs.fragment:
                                proxy_url += f"#{parsed_abs.fragment}"

                            logger.info(f"REWRITE DATA-ATTR {attr_name}: {attr_value} -> {proxy_url}")
                            tag[attr_name] = proxy_url
                            data_attr_count += 1

                except Exception as e:
                    logger.error(f"Error rewriting data-* attribute {attr_name}: {e}")

    logger.info(f"Rewrote {data_attr_count} data-* attributes")

    # Rewrite URLs in inline style attributes (e.g., style="background-image: url(...)")
    for tag in soup.find_all(style=True):
        original_style = tag['style']
        # Use the CSS URL rewriter for inline styles
        rewritten_style = rewrite_urls_in_css(original_style, target_url, proxy_base)
        if rewritten_style != original_style:
            tag['style'] = rewritten_style
            logger.debug(f"REWRITE INLINE STYLE: {original_style[:100]} -> {rewritten_style[:100]}")

    # Rewrite URLs in <style> tags
    for style_tag in soup.find_all('style'):
        if style_tag.string:
            original_css = style_tag.string
            rewritten_css = rewrite_urls_in_css(original_css, target_url, proxy_base)
            if rewritten_css != original_css:
                style_tag.string = rewritten_css
                logger.debug(f"REWRITE STYLE TAG: {len(original_css)} chars")

    return str(soup)


def rewrite_urls_in_css(css_content: str, target_url: str, proxy_base: str = "http://localhost:8000/proxy") -> str:
    """
    Rewrite URLs in CSS to work through proxy

    Args:
        css_content: Original CSS content
        target_url: Target site base URL
        proxy_base: Proxy base URL for rewriting

    Returns:
        CSS content with rewritten URLs
    """
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

        # Define target domains (main domain and www variant)
        target_domains = [parsed_target.netloc]
        if parsed_target.netloc.startswith('www.'):
            target_domains.append(parsed_target.netloc[4:])  # Remove www.
        else:
            target_domains.append(f"www.{parsed_target.netloc}")  # Add www.

        # Check if URL belongs to target domain or has no domain (relative)
        should_rewrite = (
            not parsed_abs.netloc or  # Relative URLs with no domain
            parsed_abs.netloc in target_domains  # Same domain URLs
        )

        if should_rewrite:
            proxy_url = f"{proxy_base}{parsed_abs.path}"
            if parsed_abs.query:
                proxy_url += f"?{parsed_abs.query}"
            return f'url("{proxy_url}")'

        return match.group(0)

    return re.sub(url_pattern, replace_css_url, css_content)


def clean_response_headers(headers: dict) -> dict:
    """
    Clean headers for proxy response

    Removes problematic headers that can cause issues with proxying
    and adds necessary CORS headers

    Args:
        headers: Original response headers

    Returns:
        Cleaned headers dict
    """
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
