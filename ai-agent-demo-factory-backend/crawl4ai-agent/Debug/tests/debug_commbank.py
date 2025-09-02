#!/usr/bin/env python3
"""
Debug why CommBank homepage is being filtered
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / "crawl4ai"))

def debug_commbank():
    """Debug the CommBank homepage classification"""
    from crawler_utils import is_demo_worthy_url, is_demo_worthy_url_sync
    from ai_content_classifier import HeuristicClassifier
    
    test_url = "https://www.commbank.com.au"
    
    print(f"🔍 Debugging: {test_url}")
    print("=" * 60)
    
    # Test original basic filtering
    print("1. BASIC FILTERING:")
    worthy_basic, reason_basic = is_demo_worthy_url(test_url)
    print(f"   worthy: {worthy_basic}")
    print(f"   reason: '{reason_basic}'")
    
    # Test heuristic classifier directly
    print("\n2. HEURISTIC CLASSIFIER:")
    classifier = HeuristicClassifier()
    result = classifier.classify(test_url, "", "")
    print(f"   worthy: {result.is_worthy}")
    print(f"   confidence: {result.confidence}")
    print(f"   reasoning: '{result.reasoning}'")
    
    # Test the sync function
    print("\n3. SYNC FUNCTION:")
    worthy_sync, reason_sync = is_demo_worthy_url_sync(test_url)
    print(f"   worthy: {worthy_sync}")
    print(f"   reason: '{reason_sync}'")
    
    print("\n" + "=" * 60)
    print("ANALYSIS:")
    if worthy_basic and not worthy_sync:
        print("❌ PROBLEM: Basic filtering says WORTHY, but sync function says FILTERED")
        print("   This means the heuristic classifier is being too aggressive")
    elif not worthy_basic:
        print("❌ PROBLEM: Basic filtering already filtering this URL")
        print(f"   Reason: {reason_basic}")
    else:
        print("✅ Both methods agree the URL is worthy")

if __name__ == "__main__":
    debug_commbank()