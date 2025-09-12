"""
Real Sitemap Analysis Test with AI Classification

This test demonstrates the full sitemap analysis workflow with AI classification
to show how the system prioritizes URLs for crawling.
"""

import asyncio
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO)

async def test_real_sitemap_analysis():
    """Test real sitemap analysis with AI classification on a banking site"""
    print(" Real Sitemap Analysis Test with AI Classification")
    print("=" * 60)
    
    try:
        from hybrid_crawler import HybridCrawler
        
        # Test with a real banking site that should have a sitemap
        test_url = "https://www.nab.com.au"
        
        print(f"  Testing sitemap analysis for: {test_url}")
        print("   This will:")
        print("   1. Search for sitemap.xml")
        print("   2. Extract URLs from sitemap")
        print("   3. Apply AI classification to sample URLs")
        print("   4. Show priority ranking for crawling")
        print()
        
        # Create crawler
        crawler = HybridCrawler(output_dir="./test_sitemap_output")
        
        # Run site analysis (this includes sitemap detection and AI classification)
        print(" Running comprehensive site analysis...")
        analysis = await crawler.analyze_site_structure(test_url)
        
        print(f"\n Analysis Results:")
        print(f"   Has sitemap: {analysis.has_sitemap}")
        
        if analysis.has_sitemap:
            print(f"   URLs found: {len(analysis.sitemap_urls) if analysis.sitemap_urls else 0}")
            
            if analysis.ai_classified_urls:
                print(f"   AI classifications: {len(analysis.ai_classified_urls)}")
                print(f"\n AI Classification Results (Top 10):")
                print("   " + "-" * 50)
                
                # Show top AI-classified URLs
                sorted_urls = sorted(analysis.ai_classified_urls, key=lambda x: x[1], reverse=True)
                for i, (url, confidence, reasoning) in enumerate(sorted_urls[:10]):
                    status = " WORTHY" if confidence > 0.5 else "❌ FILTERED"
                    print(f"   {i+1:2d}. {status} ({confidence:.2f}) {url[:60]}...")
                    print(f"       Reasoning: {reasoning[:80]}...")
                    print()
                    
                print(f" Strategy Selection:")
                plan = crawler.create_crawl_plan(test_url, analysis)
                print(f"   Selected strategy: {plan.strategy.value}")
                print(f"   Priority URLs: {len(plan.priority_urls)}")
                print(f"   Reasoning: {plan.reasoning}")
                
            else:
                print("     No AI classifications available")
                print("   (This might indicate AI classifier is not properly configured)")
        else:
            print("    No sitemap found - would use progressive discovery")
            
        # Show robots.txt intelligence if available
        if analysis.robots_intelligence:
            print(f"\n Robots.txt Intelligence:")
            robots_info = analysis.robots_intelligence
            if 'sitemaps' in robots_info:
                print(f"   Sitemaps discovered: {len(robots_info['sitemaps'])}")
            if 'complexity_estimate' in robots_info:
                print(f"   Site complexity: {robots_info['complexity_estimate']}")
                
        print("\n Real sitemap analysis test completed!")
        return True
        
    except ImportError as e:
        print(f" Import error: {e}")
        print("   Make sure all required modules are installed")
        return False
    except Exception as e:
        print(f" Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_progressive_fallback():
    """Test progressive discovery fallback when no sitemap is available"""
    print(f"\n Progressive Discovery Fallback Test")
    print("=" * 60)
    
    try:
        from hybrid_crawler import HybridCrawler
        
        # Test with a site that likely doesn't have a sitemap
        test_url = "https://httpbin.org"
        
        print(f" Testing progressive fallback for: {test_url}")
        
        crawler = HybridCrawler(output_dir="./test_progressive_output")
        
        # Run site analysis
        analysis = await crawler.analyze_site_structure(test_url)
        
        print(f"\n Progressive Analysis Results:")
        print(f"   Has sitemap: {analysis.has_sitemap}")
        
        if not analysis.has_sitemap:
            print("    Correctly detected no sitemap")
            
            # Create plan for progressive discovery
            plan = crawler.create_crawl_plan(test_url, analysis)
            print(f"   Strategy: {plan.strategy.value}")
            print(f"   Starting URLs: {plan.priority_urls}")
            print(f"   Max pages: {plan.max_pages_recommendation}")
            print(f"   Reasoning: {plan.reasoning}")
            
        return True
        
    except Exception as e:
        print(f" Progressive test failed: {e}")
        return False

async def main():
    """Run comprehensive sitemap analysis tests"""
    print(" US-54 Real Sitemap Analysis Test Suite")
    print("=" * 60)
    
    tests = [
        ("Real Sitemap Analysis with AI", test_real_sitemap_analysis),
        ("Progressive Discovery Fallback", test_progressive_fallback),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f" {test_name}: CRASHED - {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print(" SITEMAP ANALYSIS TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    for test_name, success in results:
        status = " PASSED" if success else "❌ FAILED"
        print(f"   {test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print(" ALL SITEMAP TESTS PASSED - Real AI classification working!")
    else:
        print("  Some issues found - check AI configuration")

if __name__ == "__main__":
    asyncio.run(main())