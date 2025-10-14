#!/usr/bin/env python3
"""
Search Handler Module
Handles search request processing and result rendering
"""
from fastapi.responses import HTMLResponse
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from typing import Dict, Any
import re
import logging

from Proxy.search_templates import create_result_item_html, create_no_results_html
from Proxy.template_manager import get_search_template, search_templates_cache
from Proxy.url_rewriter import rewrite_urls_in_html

logger = logging.getLogger(__name__)


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
        # Return fallback on error
        raise


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


async def handle_search_request(query: str, original_path: str, proxy_config: dict, opensearch_integration, opensearch_index_name: str) -> HTMLResponse:
    """
    Handle search API request using OpenSearch (US-65 Implementation)

    Returns properly formatted HTML pages with proxy-rewritten URLs that maintain
    target site styling and provide seamless search experience.

    Args:
        query: Search query string
        original_path: Original request path
        proxy_config: Proxy configuration dict
        opensearch_integration: OpenSearch integration instance
        opensearch_index_name: OpenSearch index name

    Returns:
        HTMLResponse with search results
    """
    if not opensearch_integration or not opensearch_index_name:
        logger.warning("Search request intercepted but OpenSearch not configured")
        # Return fallback HTML instead of JSON error
        current_target = proxy_config.get("target_url", "localhost")

        # Use the top-level import
        fallback_template = await get_search_template(current_target)

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
            fallback_template = await get_search_template("localhost")
            error_html = fallback_template.replace("{{SEARCH_QUERY}}", query)
            error_html = error_html.replace("{{TOTAL_RESULTS}}", "0")
            error_html = error_html.replace("{{SEARCH_RESULTS}}",
                f"<div class='error'>Search failed: {str(e)}</div>")
            return HTMLResponse(content=error_html, status_code=500)
