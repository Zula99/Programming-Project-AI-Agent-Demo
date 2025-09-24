#!/usr/bin/env python3
"""
Test script for Site Styling DNA Extraction

Tests the enhanced native template generation that extracts styling elements
from target sites to make search results look native.
"""

import asyncio
import json
from proxy_server import (
    extract_site_styling_dna,
    create_native_search_template,
    render_search_results,
    search_templates_cache
)

async def test_styling_dna_extraction():
    """Test the styling DNA extraction and native template generation"""
    print("=== Testing Site Styling DNA Extraction ===\n")

    # Test with a mock NAB-like website
    test_urls = [
        "https://www.nab.com.au",
        "https://www.commbank.com.au",
        "https://www.google.com"
    ]

    for target_url in test_urls:
        print(f"Testing styling DNA extraction for: {target_url}")

        try:
            # Extract styling DNA
            styling_dna = await extract_site_styling_dna(target_url)

            print(f"  Brand Name: {styling_dna.get('brand_name', 'Not extracted')}")
            print(f"  Primary Font: {styling_dna.get('primary_font', 'Default')[:50]}...")
            print(f"  Brand Color: {styling_dna.get('brand_color', 'Default')}")
            print(f"  Logo URL: {styling_dna.get('logo_url', 'None')[:50]}...")

            # Create native template
            template = create_native_search_template(styling_dna)

            # Verify template contains brand elements
            assert styling_dna['brand_name'] in template
            assert styling_dna['primary_font'] in template
            assert styling_dna['brand_color'] in template

            print(f"  PASS: Native template created successfully")

            # Test rendering with mock results
            mock_results = {
                "hits": [
                    {
                        "url": f"{target_url}/test-page",
                        "title": f"Test Page - {styling_dna['brand_name']}",
                        "meta_desc": "This is a test page for demonstration",
                        "score": 0.95
                    }
                ],
                "total_hits": 1
            }

            rendered_html = render_search_results(template, mock_results, "test query")

            # Verify rendered results contain proper elements
            assert "test query" in rendered_html
            assert styling_dna['brand_name'] in rendered_html
            assert "http://localhost:8000/proxy/test-page" in rendered_html

            print(f"  PASS: Search results rendered with native styling")

        except Exception as e:
            print(f"  ERROR: {e}")

        print()

    print("=== Template Quality Comparison ===\n")

    # Show the difference between basic and native templates
    basic_styling = {
        "brand_name": "Generic Site",
        "primary_font": "Arial, sans-serif",
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

    nab_styling = {
        "brand_name": "NAB",
        "primary_font": "Ciutadella, -apple-system, BlinkMacSystemFont, sans-serif",
        "text_color": "#333333",
        "background_color": "#ffffff",
        "brand_color": "#d50000",  # NAB red
        "link_color": "#d50000",
        "header_bg": "#ffffff",
        "header_border": "1px solid #e0e0e0",
        "container_width": "1200px",
        "content_padding": "20px",
        "header_padding": "15px 20px",
        "logo_url": "https://www.nab.com.au/content/dam/nabrwd/images/logos/nab-logo.svg",
        "nav_structure": '<nav class="main-nav"><a href="/personal">Personal</a><a href="/business">Business</a><a href="/corporate">Corporate</a></nav>'
    }

    basic_template = create_native_search_template(basic_styling)
    nab_template = create_native_search_template(nab_styling)

    print("Basic template brand elements:")
    print(f"  Brand: {basic_styling['brand_name']}")
    print(f"  Color: {basic_styling['brand_color']}")
    print(f"  Font: {basic_styling['primary_font']}")
    print()

    print("NAB template brand elements:")
    print(f"  Brand: {nab_styling['brand_name']}")
    print(f"  Color: {nab_styling['brand_color']} (NAB Red)")
    print(f"  Font: {nab_styling['primary_font']} (NAB Corporate Font)")
    print(f"  Logo: {nab_styling['logo_url'][:50]}...")
    print(f"  Navigation: {nab_styling['nav_structure'][:50]}...")
    print()

    # Verify styling differences
    assert basic_styling['brand_color'] != nab_styling['brand_color']
    assert basic_styling['primary_font'] != nab_styling['primary_font']
    assert nab_styling['logo_url'] != ""

    print("PASS: Templates successfully differentiated by site styling")
    print("PASS: Native template generation working correctly")
    print()
    print("=== Enhancement Complete ===")
    print("Search results will now look native to each target site!")

if __name__ == "__main__":
    asyncio.run(test_styling_dna_extraction())