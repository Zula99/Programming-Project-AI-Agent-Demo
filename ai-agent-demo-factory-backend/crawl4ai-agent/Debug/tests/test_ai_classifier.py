#!/usr/bin/env python3
"""
Test script for AI Content Classifier
Run this to manually test the classification system
"""
import asyncio
import sys
from pathlib import Path

# Add the parent directory to the path so we can import our modules
sys.path.append(str(Path(__file__).parent.parent.parent / "crawl4ai"))

from ai_content_classifier import AIContentClassifier, HeuristicClassifier
from ai_config import get_ai_config, setup_ai_config
from crawler_utils import is_demo_worthy_url_ai, is_demo_worthy_url_sync, is_demo_worthy_url

def test_basic_filtering():
    """Test the basic (existing) filtering logic"""
    print("=" * 60)
    print("TESTING BASIC FILTERING (Current System)")
    print("=" * 60)
    
    test_urls = [
        "https://www.commbank.com.au/business/loans/commercial/agriculture",
        "https://www.commbank.com.au/api/v1/data.json",
        "https://www.commbank.com.au/admin/panel",
        "https://example.com/product/annual-report-2024.pdf",
        "https://example.com/debug/log/temp.log",
        "https://www.commbank.com.au/about-us/careers",
        "https://www.nab.com.au/business/banking/transaction-accounts"
    ]
    
    for url in test_urls:
        is_worthy, reason = is_demo_worthy_url(url)
        status = "✅ WORTHY" if is_worthy else f"❌ FILTERED ({reason})"
        print(f"{status:<25} | {url}")

def test_heuristic_classification():
    """Test the enhanced heuristic classification"""
    print("\n" + "=" * 60)
    print("TESTING ENHANCED HEURISTIC CLASSIFICATION")
    print("=" * 60)
    
    classifier = HeuristicClassifier()
    
    test_cases = [
        {
            "url": "https://www.commbank.com.au/business/loans/commercial/agriculture",
            "title": "Agriculture Business Loans - CommBank",
            "content": "Commercial agriculture lending solutions for farm businesses..."
        },
        {
            "url": "https://example.com/annual-report-2024.pdf", 
            "title": "Annual Report 2024",
            "content": "Annual report whitepaper guide for shareholders overview..."
        },
        {
            "url": "https://example.com/debug-temp.pdf",
            "title": "Debug Log File",
            "content": "Debug log cache temp backup data..."
        },
        {
            "url": "https://www.nab.com.au/personal/banking/savings-accounts",
            "title": "Savings Accounts - NAB",
            "content": "Personal banking savings account products and services..."
        },
        {
            "url": "https://example.com/admin/internal/panel",
            "title": "Admin Panel",
            "content": "Internal admin tools and configuration..."
        }
    ]
    
    for case in test_cases:
        result = classifier.classify(case["url"], case["content"], case["title"])
        status = "✅ WORTHY" if result.is_worthy else "❌ FILTERED"
        confidence = f"{result.confidence:.2f}"
        print(f"{status} ({confidence}) | {case['url']}")
        print(f"   Reasoning: {result.reasoning}")
        print()

async def test_ai_classification():
    """Test the full AI classification system"""
    print("=" * 60)
    print("TESTING AI-ENHANCED CLASSIFICATION")
    print("=" * 60)
    
    # Check if AI is configured
    config = get_ai_config()
    if not config.openai_api_key and not config.anthropic_api_key:
        print("⚠️  No AI API keys configured. Will use heuristics only.")
        print("   To set up AI:")
        print("   1. Set environment variable: OPENAI_API_KEY=your_key")
        print("   2. Or run: python -c 'from ai_config import setup_ai_config; print(setup_ai_config())'")
        print()
    
    test_cases = [
        {
            "url": "https://www.commbank.com.au/business/loans/commercial/agriculture",
            "title": "Agriculture Business Loans - CommBank", 
            "content": "Commercial agriculture lending solutions for farm businesses. Specialized financing for agricultural operations, equipment, and land purchases."
        },
        {
            "url": "https://www.nab.com.au/business/loans/commercial/hospitality",
            "title": "Hospitality Business Loans - NAB",
            "content": "Business loans for restaurants, hotels, and hospitality industry. Equipment financing and working capital solutions."
        },
        {
            "url": "https://example.com/debug/api/internal/cache",
            "title": "Internal Cache API",
            "content": "Internal API endpoint for cache management and debugging purposes."
        }
    ]
    
    for case in test_cases:
        try:
            is_worthy, reason, details = await is_demo_worthy_url_ai(
                case["url"], case["content"], case["title"]
            )
            
            status = "✅ WORTHY" if is_worthy else "❌ FILTERED"
            method = details.get('method', 'unknown')
            confidence = details.get('confidence', 0.0)
            
            print(f"{status} | {case['url']}")
            print(f"   Method: {method} (confidence: {confidence:.2f})")
            print(f"   Reasoning: {details.get('reasoning', 'No reasoning provided')}")
            if reason:
                print(f"   Filter reason: {reason}")
            print()
            
        except Exception as e:
            print(f"❌ ERROR testing {case['url']}: {e}")
            print()

def test_sync_classification():
    """Test the synchronous version"""
    print("=" * 60)
    print("TESTING SYNCHRONOUS AI CLASSIFICATION")
    print("=" * 60)
    
    test_cases = [
        ("https://www.commbank.com.au/business/commercial", "Commercial Banking", "Business banking solutions"),
        ("https://example.com/api/v1/debug", "API Debug", "Internal debugging interface"),
    ]
    
    for url, title, content in test_cases:
        is_worthy, reason = is_demo_worthy_url_sync(url, content, title)
        status = "✅ WORTHY" if is_worthy else f"❌ FILTERED ({reason})"
        print(f"{status} | {url}")

async def main():
    """Main test function"""
    print("🧪 AI Content Classifier Test Suite")
    print("=" * 60)
    
    # Test 1: Basic filtering (existing system)
    test_basic_filtering()
    
    # Test 2: Enhanced heuristics
    test_heuristic_classification()
    
    # Test 3: Full AI classification (async)
    await test_ai_classification()
    
    # Test 4: Sync classification
    test_sync_classification()
    
    print("=" * 60)
    print("✅ Test suite completed!")
    print("=" * 60)
    print("\n💡 Integration Points:")
    print("   - Replace is_demo_worthy_url() calls with is_demo_worthy_url_ai() for async contexts")
    print("   - Use is_demo_worthy_url_sync() for sync contexts with enhanced heuristics") 
    print("   - Original is_demo_worthy_url() still available as fallback")
    print()
    print("📝 Next steps:")
    print("   1. Test this script: python test_ai_classifier.py")
    print("   2. Set up AI API keys if desired (optional)")
    print("   3. Integrate into SmartMirrorAgent crawling logic")

if __name__ == "__main__":
    asyncio.run(main())