#!/usr/bin/env python3
"""
Debug the integration issue
"""
import sys
from pathlib import Path

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent.parent / "crawl4ai"))

def test_function_signatures():
    """Test what each filtering function returns"""
    from crawler_utils import is_demo_worthy_url, is_demo_worthy_url_sync
    
    test_url = "https://www.commbank.com.au/business/loans"
    
    print("🔍 Testing Function Signatures")
    print("=" * 50)
    
    # Test original function
    try:
        result1 = is_demo_worthy_url(test_url)
        print(f"is_demo_worthy_url() returns: {result1}")
        print(f"  Type: {type(result1)}")
        print(f"  Length: {len(result1) if hasattr(result1, '__len__') else 'N/A'}")
    except Exception as e:
        print(f"❌ is_demo_worthy_url() failed: {e}")
    
    print()
    
    # Test new sync function
    try:
        result2 = is_demo_worthy_url_sync(test_url)
        print(f"is_demo_worthy_url_sync() returns: {result2}")
        print(f"  Type: {type(result2)}")
        print(f"  Length: {len(result2) if hasattr(result2, '__len__') else 'N/A'}")
    except Exception as e:
        print(f"❌ is_demo_worthy_url_sync() failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_function_signatures()