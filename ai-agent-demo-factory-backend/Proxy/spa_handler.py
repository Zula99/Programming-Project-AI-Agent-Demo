#!/usr/bin/env python3
"""
SPA Handler Module
Handles Single Page Application (SPA) search API requests
"""
from fastapi.responses import JSONResponse
from urllib.parse import urlparse
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


def is_search_api_request(path: str, query_params: Dict[str, Any]) -> bool:
    """
    Enhanced detection of search API requests for any site including SPAs

    Args:
        path: Request path
        query_params: Query parameters dict

    Returns:
        True if this appears to be a search API request
    """
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
    """
    Extract search query from request parameters

    Args:
        query_params: Query parameters dict

    Returns:
        Extracted search query or None
    """
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


async def handle_spa_search_api(query: str, original_path: str, target_url: str, opensearch_integration, opensearch_index_name: str) -> JSONResponse:
    """
    Handle SPA search API requests by returning our OpenSearch data
    formatted to match their expected API structure

    Args:
        query: Search query string
        original_path: Original request path
        target_url: Target site URL
        opensearch_integration: OpenSearch integration instance
        opensearch_index_name: OpenSearch index name

    Returns:
        JSONResponse with search results
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


def is_spa_site(html_content: str) -> bool:
    """
    Detect if site is a Single Page Application (SPA)

    Args:
        html_content: HTML content to analyze

    Returns:
        True if SPA indicators are detected
    """
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
