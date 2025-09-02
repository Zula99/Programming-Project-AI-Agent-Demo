#!/usr/bin/env python3
"""
Quick debug of the specific function call
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / "crawl4ai"))

def test_direct_call():
    """Test the exact function call that's failing"""
    from crawler_utils import is_demo_worthy_url_sync
    
    test_url = "https://www.commbank.com.au"
    
    print(f"Testing: {test_url}")
    try:
        result = is_demo_worthy_url_sync(test_url)
        print(f"✅ Success: {result}")
        print(f"   Type: {type(result)}")
        
        # Test the unpacking that happens in the crawler
        is_worthy, filter_reason = result
        print(f"   is_worthy: {is_worthy} (type: {type(is_worthy)})")
        print(f"   filter_reason: {filter_reason} (type: {type(filter_reason)})")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def test_ai_availability():
    """Check if AI imports are working"""
    print("\nTesting AI imports...")
    try:
        from crawler_utils import AI_AVAILABLE
        print(f"AI_AVAILABLE: {AI_AVAILABLE}")
        
        if AI_AVAILABLE:
            from crawler_utils import HeuristicClassifier
            classifier = HeuristicClassifier()
            result = classifier.classify("https://www.commbank.com.au")
            print(f"Direct HeuristicClassifier: {result}")
        else:
            print("AI components not available")
            
    except Exception as e:
        print(f"❌ AI import error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_direct_call()
    test_ai_availability()