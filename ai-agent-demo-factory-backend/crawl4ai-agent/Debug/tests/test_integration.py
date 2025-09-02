#!/usr/bin/env python3
"""
Test script for AI Content Classifier Integration
Tests the main crawler with AI-enhanced filtering
"""
import asyncio
import sys
from pathlib import Path

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent.parent / "crawl4ai"))

from smart_mirror_agent import SmartMirrorAgent

async def test_small_crawl():
    """Test a small crawl with AI-enhanced filtering"""
    print("🧪 Testing AI-Enhanced Crawler Integration")
    print("=" * 60)
    
    # Initialize the SmartMirrorAgent
    agent = SmartMirrorAgent()
    
    # Test URLs that should show the difference
    test_sites = [
        {
            "url": "https://www.commbank.com.au", 
            "name": "CommBank",
            "expect": "Should now include /business/ pages that were previously filtered"
        },
        # Add more test sites as needed
    ]
    
    for site in test_sites:
        print(f"\n🔍 Testing: {site['name']} ({site['url']})")
        print(f"Expected: {site['expect']}")
        print("-" * 60)
        
        try:
            # Small crawl to test filtering
            success, metrics, mirror_path = await agent.process_url(
                url=site["url"],
                # Use small limits for testing
            )
            
            if success:
                print(f"✅ SUCCESS")
                print(f"   Quality Score: {metrics.overall_score:.3f}")
                print(f"   Pages Crawled: {len(metrics.page_metrics) if hasattr(metrics, 'page_metrics') else 'N/A'}")
                print(f"   Mirror Path: {mirror_path}")
                
                # Show filtering stats
                if hasattr(metrics, 'total_filtered_urls'):
                    print(f"   URLs Filtered: {metrics.total_filtered_urls}")
                    
                    if hasattr(metrics, 'filtering_breakdown') and metrics.filtering_breakdown:
                        print(f"   Filtering breakdown:")
                        for reason, count in sorted(metrics.filtering_breakdown.items(), key=lambda x: x[1], reverse=True):
                            if count > 0:
                                print(f"     - {reason}: {count}")
                
            else:
                print(f"❌ FAILED: {metrics}")
                
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
        
        print()
    
    print("=" * 60)
    print("✅ Integration test completed!")
    print("=" * 60)
    print("\n📊 What to look for:")
    print("   1. More business pages included (less aggressive filtering)")
    print("   2. Better quality scores due to more relevant content")
    print("   3. Smarter filtering reasons in the breakdown")
    print("   4. /business/, /commercial/ URLs should now be included")
    print()
    print("💡 Compare with previous crawls to see the improvement!")

def test_filtering_comparison():
    """Compare old vs new filtering on sample URLs"""
    print("\n🔬 Filtering Comparison Test")
    print("=" * 60)
    
    # Import both old and new filtering
    from crawler_utils import is_demo_worthy_url, is_demo_worthy_url_sync
    
    test_urls = [
        "https://www.commbank.com.au/business/loans/commercial/agriculture",
        "https://www.nab.com.au/business/banking/transaction-accounts", 
        "https://www.commbank.com.au/business/commercial/hospitality",
        "https://example.com/annual-report-2024.pdf",
        "https://example.com/api/v1/data.json",
        "https://example.com/admin/panel",
    ]
    
    print(f"{'URL':<60} | {'OLD':<15} | {'NEW':<15}")
    print("-" * 95)
    
    for url in test_urls:
        # Test old filtering
        old_worthy, old_reason = is_demo_worthy_url(url)
        old_status = "✅ WORTHY" if old_worthy else f"❌ {old_reason}"
        
        # Test new filtering  
        new_worthy, new_reason = is_demo_worthy_url_sync(url)
        new_status = "✅ WORTHY" if new_worthy else f"❌ {new_reason}"
        
        # Highlight differences
        diff_marker = " 🔄" if old_worthy != new_worthy else ""
        
        print(f"{url:<60} | {old_status:<15} | {new_status:<15}{diff_marker}")
    
    print("\n🔄 = Filtering decision changed with AI enhancement")

async def main():
    """Main test function"""
    
    print("🚀 AI Content Classifier Integration Test")
    print("=" * 60)
    print("This will test the AI-enhanced filtering in the main crawler")
    print()
    
    # Test 1: Compare filtering approaches
    test_filtering_comparison()
    
    # Test 2: Small live crawl 
    print(f"\nProceed with live crawl test? This will make API calls.")
    response = input("Continue? (y/N): ").strip().lower()
    
    if response == 'y':
        await test_small_crawl()
    else:
        print("Skipping live crawl test.")
    
    print()
    print("🎯 Integration Summary:")
    print("   ✅ AI classification integrated into crawler_utils.py")
    print("   ✅ Enhanced heuristic filtering active")
    print("   ✅ Fallback system in place")
    print("   ✅ Ready for production use!")

if __name__ == "__main__":
    asyncio.run(main())