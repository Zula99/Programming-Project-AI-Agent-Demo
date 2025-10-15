#!/usr/bin/env python3
"""
Proxy Handler Module
Handles core proxy request forwarding and response processing
"""
from fastapi import Request
from fastapi.responses import Response, HTMLResponse
from typing import Dict, Any
import httpx
import logging

from Proxy.url_rewriter import rewrite_urls_in_html, rewrite_urls_in_css, clean_response_headers
from Proxy.search_injection import inject_search_functionality, is_dynamic_search_site
from Proxy.spa_handler import is_search_api_request, extract_search_query, handle_spa_search_api
from Proxy.search_handler import handle_search_request

logger = logging.getLogger(__name__)


async def proxy_request_handler(
    request: Request,
    path: str,
    proxy_config: Dict[str, Any],
    opensearch_integration,
    opensearch_index_name: str
) -> Response:
    """
    Core proxy request handler

    Handles:
    - Search API interception
    - Request forwarding to target site
    - Response rewriting (HTML, CSS)
    - Search functionality injection

    Args:
        request: FastAPI Request object
        path: Request path
        proxy_config: Proxy configuration dict
        opensearch_integration: OpenSearch integration instance
        opensearch_index_name: OpenSearch index name

    Returns:
        Response with proxied content
    """
    # Exclude our API endpoints from proxying
    api_endpoints = ["test", "ai-vision-analyze", "ai-cache"]
    if any(path.startswith(endpoint) for endpoint in api_endpoints):
        return Response("API endpoint not found", status_code=404)

    if not proxy_config["enabled"] or not proxy_config["target_url"]:
        return Response("Proxy not configured or disabled", status_code=503)

    # Check for search API interception (US-63: API Replacement Search Injection)
    if proxy_config["search_injection_enabled"]:
        query_params = dict(request.query_params)

        # Enhanced debug logging for all requests
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
        logger.info(f" SEARCH DETECTION: path='{path}', params={query_params}, is_search={is_search}")

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
                    return await handle_spa_search_api(search_query, path, proxy_config["target_url"], opensearch_integration, opensearch_index_name)
                else:
                    # Traditional HTML search pages
                    return await handle_search_request(search_query, path, proxy_config, opensearch_integration, opensearch_index_name)

    # Build target URL for normal proxying
    target_url = f"{proxy_config['target_url']}/{path}"
    if request.url.query:
        target_url += f"?{request.url.query}"

    logger.info(f"Proxying: {request.method} {target_url}")

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # Prepare headers - remove host and origin to avoid conflicts, but keep referer (rewritten)
            headers = {k: v for k, v in request.headers.items() if k.lower() not in ["host", "origin"]}

            # Rewrite referer to target domain if present (many sites require this for static assets)
            if 'referer' in headers or 'Referer' in headers:
                # Remove the proxy referer and replace with target site referer
                headers.pop('referer', None)
                headers.pop('Referer', None)
                headers['Referer'] = proxy_config["target_url"]

            # Add proper Accept header for CSS/JS/image requests to avoid homepage redirects
            if path.endswith(('.css', '.js', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.eot')):
                if path.endswith('.css'):
                    headers['Accept'] = 'text/css,*/*;q=0.1'
                elif path.endswith('.js'):
                    headers['Accept'] = 'application/javascript,*/*;q=0.1'
                elif path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico')):
                    headers['Accept'] = 'image/*,*/*;q=0.1'
                elif path.endswith(('.woff', '.woff2', '.ttf', '.eot')):
                    headers['Accept'] = 'font/*,*/*;q=0.1'

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
                        target_url
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

            # For all other content types (JS, images, fonts, etc.), return as-is with proper content-type
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=clean_headers,
                media_type=content_type or "application/octet-stream"
            )

    except httpx.RequestError as e:
        logger.error(f"Proxy error: {e}")
        return Response(f"Proxy error: {str(e)}", status_code=502)


async def catch_all_proxy_handler(
    request: Request,
    path: str,
    proxy_config: Dict[str, Any],
    opensearch_integration=None,
    opensearch_index_name: str = None
) -> Response:
    """
    Catch-all handler for requests that don't match /proxy/ prefix

    Args:
        request: FastAPI Request object
        path: Request path
        proxy_config: Proxy configuration dict
        opensearch_integration: OpenSearch integration instance
        opensearch_index_name: OpenSearch index name

    Returns:
        Response with proxied content
    """
    # Exclude our API endpoints and non-proxy routes
    logger.debug(f"[CATCH-ALL] Processing path: '{path}'")
    excluded_paths = ["vision", "config", "auto-configure", "clear-template-cache"]

    # Check if path starts with any excluded path
    for excluded in excluded_paths:
        if path.startswith(excluded):
            logger.debug(f"[CATCH-ALL] Path '{path}' starts with '{excluded}', excluding")
            return Response("Route not found", status_code=404)

    if not proxy_config["enabled"] or not proxy_config["target_url"]:
        return Response("Proxy not configured", status_code=503)

    # Check for search API interception (same logic as main proxy handler)
    if proxy_config["search_injection_enabled"]:
        query_params = dict(request.query_params)
        logger.info(f" CATCH-ALL SEARCH DETECTION: path='{path}', params={query_params}")

        is_search = is_search_api_request(path, query_params)
        logger.info(f" CATCH-ALL is_search={is_search}")

        if is_search:
            search_query = extract_search_query(query_params)
            logger.info(f" CATCH-ALL extracted query='{search_query}'")

            if search_query:
                logger.info(f" CATCH-ALL Search API intercepted: {path} -> query: '{search_query}'")
                # Traditional HTML search pages
                return await handle_search_request(search_query, path, proxy_config, opensearch_integration, opensearch_index_name)

    # Skip if this is a proxy request (shouldn't happen but safety check)
    if path.startswith("proxy/"):
        return Response("Invalid proxy path", status_code=400)

    # Handle requests by forwarding to target (empty path = homepage)
    if path == "":
        target_url = proxy_config['target_url']
    else:
        target_url = f"{proxy_config['target_url']}/{path}"

    if request.url.query:
        target_url += f"?{request.url.query}"

    logger.info(f"Catch-all proxying: {request.method} {target_url}")

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # Prepare headers - remove host and origin to avoid conflicts, but keep referer (rewritten)
            headers = {k: v for k, v in request.headers.items() if k.lower() not in ["host", "origin"]}

            # Rewrite referer to target domain if present (many sites require this for static assets)
            if 'referer' in headers or 'Referer' in headers:
                # Remove the proxy referer and replace with target site referer
                headers.pop('referer', None)
                headers.pop('Referer', None)
                headers['Referer'] = proxy_config["target_url"]

            # Add proper Accept header for CSS/JS/image requests to avoid homepage redirects
            if path.endswith(('.css', '.js', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf', '.eot')):
                if path.endswith('.css'):
                    headers['Accept'] = 'text/css,*/*;q=0.1'
                elif path.endswith('.js'):
                    headers['Accept'] = 'application/javascript,*/*;q=0.1'
                elif path.endswith(('.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico')):
                    headers['Accept'] = 'image/*,*/*;q=0.1'
                elif path.endswith(('.woff', '.woff2', '.ttf', '.eot')):
                    headers['Accept'] = 'font/*,*/*;q=0.1'

            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=await request.body()
            )

            clean_headers = clean_response_headers(dict(response.headers))
            content_type = response.headers.get("content-type", "").lower()

            # Check file extension as fallback for content-type detection
            is_js_file = path.endswith('.js')
            is_css_file = path.endswith('.css')
            is_html_file = path.endswith(('.html', '.htm', '')) or path == ""

            logger.debug(f"Content-Type: {content_type}, Path: {path}")

            # Rewrite URLs for HTML content only (not JS/CSS files)
            if "text/html" in content_type and not is_js_file and not is_css_file:
                try:
                    rewritten_content = rewrite_urls_in_html(
                        response.text,
                        proxy_config["target_url"]
                    )

                    # Inject search functionality for all sites
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

            elif ("text/css" in content_type or is_css_file) and not is_js_file:
                try:
                    rewritten_content = rewrite_urls_in_css(
                        response.text,
                        target_url
                    )
                    return Response(
                        content=rewritten_content,
                        status_code=response.status_code,
                        headers=clean_headers,
                        media_type="text/css"
                    )
                except Exception as e:
                    logger.warning(f"CSS rewriting failed: {e}")

            # For all other content types (JS, images, fonts, etc.), return as-is with proper content-type
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=clean_headers,
                media_type=content_type or "application/octet-stream"
            )

    except httpx.RequestError as e:
        logger.error(f"Catch-all proxy error: {e}")
        return Response(f"Resource not found: {path}", status_code=404)
