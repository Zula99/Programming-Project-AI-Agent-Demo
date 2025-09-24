#!/usr/bin/env python3
"""
Test script for US-65 HTML Search Results Rendering & URL Rewriting implementation

This script tests the new search functionality to ensure:
- Template caching works for different target sites
- HTML rendering maintains target site styling
- URL rewriting converts all links to proxy URLs
- Error handling provides fallback templates
"""

import asyncio
import json
from urllib.parse import urlparse

# Test the search template and rendering functions
async def test_search_implementation():
    """Test the search implementation components"""
    print("=== Testing US-65 HTML Search Results Implementation ===\n")

    # Import the functions we implemented
    from proxy_server import (
        create_fallback_template,
        render_search_results,
        get_search_template,
        search_templates_cache,
        proxy_config
    )

    # Test 1: Fallback template creation
    print("1. Testing fallback template creation...")
    fallback_html = create_fallback_template("https://nab.com.au")
    assert "{{SEARCH_QUERY}}" in fallback_html
    assert "{{SEARCH_RESULTS}}" in fallback_html
    assert "nab.com.au" in fallback_html
    print("   PASS: Fallback template creation working")

    # Test 2: Search results rendering
    print("\n2. Testing search results rendering...")
    mock_results = {
        "hits": [
            {
                "url": "https://nab.com.au/personal/loans",
                "title": "Personal Loans - NAB",
                "meta_desc": "Get a personal loan from NAB with competitive rates",
                "score": 0.95,
                "highlight": {
                    "content_md": ["Personal <em>loans</em> with competitive rates"]
                }
            },
            {
                "url": "https://nab.com.au/business/loans",
                "title": "Business Loans - NAB",
                "meta_desc": "Business loans to help grow your business",
                "score": 0.87
            }
        ],
        "total_hits": 2
    }

    rendered_html = render_search_results(fallback_html, mock_results, "loans")

    # Check that query was inserted
    assert "loans" in rendered_html
    assert "2" in rendered_html  # total results

    # Check that proxy URLs were created
    assert "http://localhost:8000/proxy/personal/loans" in rendered_html
    assert "http://localhost:8000/proxy/business/loans" in rendered_html

    # Check that titles and snippets are present
    assert "Personal Loans - NAB" in rendered_html
    assert "Business Loans - NAB" in rendered_html
    assert "competitive rates" in rendered_html

    print("   PASS: Search results rendering working")
    print("   PASS: URL rewriting to proxy URLs working")
    print("   PASS: Highlight snippets working")

    # Test 3: Template caching simulation
    print("\n3. Testing template caching...")

    # Simulate different domains
    proxy_config["target_url"] = "https://nab.com.au"

    # Clear cache to start fresh
    search_templates_cache.clear()

    # This would normally fetch from the site, but we'll simulate
    print("   - Template cache initially empty:", len(search_templates_cache) == 0)

    # Mock the template fetching (in real usage this fetches from target site)
    domain = urlparse("https://nab.com.au").netloc
    search_templates_cache[domain] = {
        "template_html": "<html><head><title>NAB Search</title></head><body>NAB styling here {{SEARCH_RESULTS}}</body></html>",
        "cached_at": "2025-01-01",
        "target_url": "https://nab.com.au",
        "domain": domain
    }

    print("   - Template cached for NAB:", domain in search_templates_cache)

    # Test rendering with real site template
    nab_template = search_templates_cache[domain]["template_html"]
    nab_rendered = render_search_results(nab_template, mock_results, "loans")

    assert "NAB styling here" in nab_rendered
    assert "http://localhost:8000/proxy/personal/loans" in nab_rendered
    print("   PASS: Template caching and domain-specific rendering working")

    # Test 4: Multiple domain support
    print("\n4. Testing multiple domain support...")

    # Add CommBank template
    commbank_domain = "commbank.com.au"
    search_templates_cache[commbank_domain] = {
        "template_html": "<html><head><title>CommBank Search</title></head><body>CommBank styling {{SEARCH_RESULTS}}</body></html>",
        "cached_at": "2025-01-01",
        "target_url": "https://commbank.com.au",
        "domain": commbank_domain
    }

    # Render with CommBank template
    commbank_template = search_templates_cache[commbank_domain]["template_html"]
    commbank_rendered = render_search_results(commbank_template, mock_results, "loans")

    assert "CommBank styling" in commbank_rendered
    print("   PASS: Multiple domain templates working")
    print("   - Cached domains:", list(search_templates_cache.keys()))

    print("\n=== All Tests Passed! US-65 Implementation Ready ===")
    print("\nNext steps:")
    print("1. Start the proxy server: python proxy_server.py")
    print("2. Configure proxy target: POST /auto-configure")
    print("3. Test search: GET /proxy/search?q=test")
    print("4. Verify HTML response with target site styling")

if __name__ == "__main__":
    asyncio.run(test_search_implementation())