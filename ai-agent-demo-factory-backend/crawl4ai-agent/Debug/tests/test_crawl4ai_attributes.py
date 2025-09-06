#!/usr/bin/env python3
"""
Test script to examine what attributes crawl4ai AsyncWebCrawler.arun() actually returns
"""
import asyncio
import sys
from pathlib import Path

try:
    from crawl4ai import AsyncWebCrawler
except ImportError:
    print("❌ crawl4ai not available - install with: pip install crawl4ai")
    sys.exit(1)

async def test_crawl4ai_result():
    """Test what attributes are available in the crawl4ai result"""
    print("Testing crawl4ai result attributes")
    print("=" * 60)
    
    try:
        async with AsyncWebCrawler(headless=True) as crawler:
            # Test with a complex JS page like NAB
            test_url = "https://www.nab.com.au/"
            print(f"Testing with: {test_url}")
            
            result = await crawler.arun(
                url=test_url,
                wait_for='networkidle',
                timeout=30000
            )
            
            print(f"\nAvailable attributes in result:")
            print("-" * 40)
            
            # Get all attributes
            attrs = [attr for attr in dir(result) if not attr.startswith('_')]
            for attr in sorted(attrs):
                try:
                    value = getattr(result, attr)
                    if callable(value):
                        print(f"   {attr}: <method>")
                    elif isinstance(value, str):
                        print(f"   {attr}: str (len={len(value)})")
                    else:
                        print(f"   {attr}: {type(value).__name__}")
                except:
                    print(f"   {attr}: <unable to access>")
            
            print(f"\nHTML-related attributes:")
            print("-" * 40)
            
            # Check specific HTML attributes
            html_attrs = ['html', 'raw_html', 'cleaned_html', 'fit_html', 'final_html', 'rendered_html']
            for attr in html_attrs:
                if hasattr(result, attr):
                    value = getattr(result, attr)
                    if value:
                        print(f"   OK {attr}: Available (len={len(value) if isinstance(value, str) else 'unknown'})")
                        if attr in ['html', 'raw_html'] and len(str(value)) < 500:
                            print(f"      Preview: {str(value)[:200]}...")
                    else:
                        print(f"   -- {attr}: Exists but empty/None")
                else:
                    print(f"   XX {attr}: Not available")
            
            print(f"\nContent attributes:")
            print("-" * 40)
            
            content_attrs = ['markdown', 'text', 'clean_text', 'title', 'content_type']
            for attr in content_attrs:
                if hasattr(result, attr):
                    value = getattr(result, attr)
                    if value:
                        print(f"   OK {attr}: {type(value).__name__} (len={len(str(value))})")
                    else:
                        print(f"   -- {attr}: Exists but empty/None")
                else:
                    print(f"   XX {attr}: Not available")
            
            # Show which HTML attribute has the most content
            print(f"\nBest HTML source for processing:")
            print("-" * 40)
            
            best_attr = None
            best_len = 0
            
            for attr in ['html', 'raw_html', 'cleaned_html', 'fit_html']:
                if hasattr(result, attr):
                    value = getattr(result, attr)
                    if value and len(str(value)) > best_len:
                        best_attr = attr
                        best_len = len(str(value))
            
            if best_attr:
                print(f"   ** Use '{best_attr}' - {best_len} characters")
                print(f"      This is the fully rendered HTML after JavaScript execution")
            else:
                print("   XX No HTML content found")
                
    except Exception as e:
        print(f"XX Error testing crawl4ai: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_crawl4ai_result())