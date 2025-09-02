#!/usr/bin/env python3
"""
Debug the specific crawl failure
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / "crawl4ai"))

def test_commbank_url():
    """Test the exact same URL that's failing"""
    from crawler_utils import is_demo_worthy_url_sync, is_demo_worthy_url
    
    test_url = "https://www.commbank.com.au"
    
    print(f"🔍 Testing: {test_url}")
    print("=" * 60)
    
    # Test original function
    print("1. Original function:")
    try:
        worthy1, reason1 = is_demo_worthy_url(test_url)
        print(f"   Result: worthy={worthy1}, reason='{reason1}'")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test new sync function
    print("\n2. New sync function:")
    try:
        worthy2, reason2 = is_demo_worthy_url_sync(test_url)
        print(f"   Result: worthy={worthy2}, reason='{reason2}'")
        
        # This is what the crawler sees
        if not worthy2:
            print(f"   ⚠️  URL would be filtered with reason: '{reason2}'")
        else:
            print(f"   ✅ URL would be crawled (reason is empty: '{reason2}')")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Test the heuristic classifier directly
    print("\n3. Direct heuristic classifier test:")
    try:
        from ai_content_classifier import HeuristicClassifier
        classifier = HeuristicClassifier()
        result = classifier.classify(test_url, "", "")
        print(f"   Result: worthy={result.is_worthy}, confidence={result.confidence}")
        print(f"   Reasoning: '{result.reasoning}'")
        print(f"   Method: {result.method_used}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()

def test_crawler_basic():
    """Test if the basic crawler works with original function"""
    print("\n" + "=" * 60)
    print("Testing if basic crawler functionality works...")
    
    try:
        from crawler_utils import generic_crawl, CrawlConfig
        import asyncio
        
        async def test_basic_crawl():
            config = CrawlConfig(
                max_pages=1,
                request_gap=1.0,
                user_agent="Test",
                respect_robots=False
            )
            
            # Test with a simple, known-good URL
            try:
                result = await generic_crawl("https://example.com", config, Path("output/test"))
                print(f"   ✅ Basic crawl worked: {len(result.pages)} pages")
            except Exception as e:
                print(f"   ❌ Basic crawl failed: {e}")
        
        asyncio.run(test_basic_crawl())
        
    except Exception as e:
        print(f"❌ Could not test basic crawl: {e}")

if __name__ == "__main__":
    test_commbank_url()
    test_crawler_basic()