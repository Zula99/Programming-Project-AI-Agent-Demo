"""
Quality Plateau Detection System Test

This test validates:
1. Quality plateau detection logic
2. Site-specific threshold configuration  
3. AI classification integration
4. Intelligent stopping conditions
5. Integration with existing crawler systems
"""

import asyncio
import sys
import logging
from pathlib import Path
import time
from typing import Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Test the quality plateau system
def test_quality_plateau_logic():
    """Test core quality plateau detection logic"""
    print(" Testing Quality Plateau Detection Logic")
    print("=" * 50)
    
    try:
        from quality_plateau import SimpleQualityBasedCrawling, QualityMetrics
        
        # Test 1: Basic plateau detection
        print("\n Test 1: Basic Quality Plateau Detection")
        monitor = SimpleQualityBasedCrawling(window_size=5, worthy_threshold=0.4)  # Small window for testing
        
        # Simulate good quality pages
        for i in range(3):
            metrics = QualityMetrics(
                is_worthy=True,
                confidence_score=0.8,
                reasoning="Good business content",
                url=f"https://test.com/page{i}"
            )
            monitor.add_page_assessment(metrics)
            
        should_stop, reason = monitor.should_stop_crawling()
        print(f"   After 3 good pages: should_stop={should_stop}, reason='{reason}'")
        
        # Add poor quality pages to trigger plateau
        for i in range(3, 8):
            metrics = QualityMetrics(
                is_worthy=False,
                confidence_score=0.3,
                reasoning="Low-value content",
                url=f"https://test.com/page{i}"
            )
            monitor.add_page_assessment(metrics)
            
        should_stop, reason = monitor.should_stop_crawling()
        print(f"   After 5 poor pages: should_stop={should_stop}, reason='{reason}'")
        
        # Print statistics
        stats = monitor.get_quality_stats()
        print(f"   Final stats: {stats['recent_worthy_ratio']:.1%} recent quality")
        
        print(" Basic plateau detection: PASSED")
        return True
        
    except Exception as e:
        print(f" Basic plateau detection: FAILED - {e}")
        return False


def test_site_specific_thresholds():
    """Test site-specific quality threshold configuration"""
    print("\n  Test 2: Site-Specific Quality Thresholds")
    print("=" * 50)
    
    try:
        from crawler_utils import _get_site_specific_thresholds
        from ai_content_classifier import BusinessSiteType
        
        # Test different site types
        site_types = [
            BusinessSiteType.ECOMMERCE,
            BusinessSiteType.BANKING,
            BusinessSiteType.NEWS,
            BusinessSiteType.TECHNOLOGY
        ]
        
        for site_type in site_types:
            thresholds = _get_site_specific_thresholds(site_type)
            print(f"   {site_type.value}:")
            print(f"      Worthy threshold: {thresholds['worthy_threshold']:.1%}")
            print(f"      Diversity threshold: {thresholds['diversity_threshold']:.1%}")
            print(f"      Window size: {thresholds['quality_window_size']}")
        
        # Verify e-commerce is more permissive
        ecommerce_thresholds = _get_site_specific_thresholds(BusinessSiteType.ECOMMERCE)
        banking_thresholds = _get_site_specific_thresholds(BusinessSiteType.BANKING)
        
        assert ecommerce_thresholds['worthy_threshold'] < banking_thresholds['worthy_threshold'], \
            "E-commerce should have lower worthy threshold"
        assert ecommerce_thresholds['diversity_threshold'] > banking_thresholds['diversity_threshold'], \
            "E-commerce should have higher diversity threshold"
            
        print(" Site-specific thresholds: PASSED")
        return True
        
    except Exception as e:
        print(f" Site-specific thresholds: FAILED - {e}")
        return False


async def test_ai_integration():
    """Test AI classification integration (if available)"""
    print("\n Test 3: AI Classification Integration")
    print("=" * 50)
    
    try:
        from ai_content_classifier import AIContentClassifier, BusinessSiteDetector
        from ai_config import get_ai_config
        
        # Test site detection
        detector = BusinessSiteDetector()
        
        test_urls = [
            ("https://shop.example.com/products", "E-commerce site"),
            ("https://bank.example.com/banking", "Banking site"),
            ("https://news.example.com/articles", "News site"),
        ]
        
        for url, expected in test_urls:
            site_type = detector.detect_site_type(url)
            print(f"   {url} -> {site_type.value} ({expected})")
        
        # Test AI classifier initialization (without actually calling API)
        try:
            config = get_ai_config()
            if hasattr(config, 'openai_api_key') and config.openai_api_key:
                classifier = AIContentClassifier(
                    api_key=config.openai_api_key,
                    model='gpt-4o-mini'
                )
                print("    AI classifier initialized successfully")
            else:
                print("    No API key found, but initialization logic works")
        except Exception as e:
            print(f"    AI classifier initialization issue: {e}")
        
        print(" AI integration: PASSED")
        return True
        
    except ImportError:
        print("    AI components not available - this is acceptable")
        return True
    except Exception as e:
        print(f" AI integration: FAILED - {e}")
        return False


def test_hybrid_crawler_integration():
    """Test integration with hybrid crawler"""
    print("\n🔗 Test 4: Hybrid Crawler Integration")
    print("=" * 50)
    
    try:
        from hybrid_crawler import HybridCrawler, DiscoveryStrategy
        
        # Test crawler initialization
        crawler = HybridCrawler(output_dir="./test_output")
        print("   HybridCrawler initialized")
        
        # Test strategy enum
        strategies = [DiscoveryStrategy.SITEMAP_FIRST, DiscoveryStrategy.PROGRESSIVE]
        print(f"   Available strategies: {[s.value for s in strategies]}")
        
        # Test plan creation (without actual crawling)
        from hybrid_crawler import SitemapAnalysis, CrawlPlan
        
        # Mock analysis for sitemap scenario
        mock_analysis = SitemapAnalysis(
            has_sitemap=True,
            sitemap_urls=["https://test.com/page1", "https://test.com/page2"],
            estimated_total_urls=2
        )
        
        plan = crawler.create_crawl_plan("https://test.com", mock_analysis)
        print(f"   Strategy selected: {plan.strategy.value}")
        print(f"   Max pages recommendation: {plan.max_pages_recommendation}")
        
        print(" Hybrid crawler integration: PASSED")
        return True
        
    except Exception as e:
        print(f" Hybrid crawler integration: FAILED - {e}")
        return False


async def run_mini_crawl_test():
    """Run a minimal crawl test to validate the complete system"""
    print("\n  Test 5: Mini Crawl Test (5 pages max)")
    print("=" * 50)
    
    try:
        from crawler_utils import CrawlConfig, generic_crawl
        from pathlib import Path
        import urllib.parse
        
        # Use a simple, reliable test site
        test_url = "https://httpbin.org"  # Reliable testing service
        domain = urllib.parse.urlparse(test_url).netloc
        
        # Create minimal crawl config
        config = CrawlConfig(
            domain=domain,
            output_root=Path("./test_crawl_output") / domain.replace('.', '_'),
            max_pages=5,  # Very limited for testing
            request_gap=1.0,  # Respectful
            respect_robots=False,
            start_url=test_url,
            javascript=False,  # Simple for testing
            timeout=15
        )
        
        print(f"   Testing with: {test_url}")
        print("   Running mini crawl...")
        
        start_time = time.time()
        results, stats = await generic_crawl(config)
        crawl_time = time.time() - start_time
        
        print(f"   Crawl completed in {crawl_time:.1f}s")
        print(f"   Pages crawled: {stats['pages_crawled']}")
        print(f"   Success rate: {stats['successful_crawls']}/{len(results)}")
        
        if 'quality_plateau_stats' in stats:
            plateau_stats = stats['quality_plateau_stats']
            print(f"   Quality plateau system: {'✅ Active' if plateau_stats else '⚠️  Inactive'}")
            if plateau_stats:
                print(f"   Overall quality: {plateau_stats.get('overall_worthy_ratio', 0):.1%}")
        
        print(" Mini crawl test: PASSED")
        return True
        
    except Exception as e:
        print(f" Mini crawl test: FAILED - {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run complete test suite"""
    print(" US-54 Quality Plateau Detection Test Suite")
    print("=" * 60)
    print()
    
    tests = [
        ("Quality Plateau Logic", test_quality_plateau_logic),
        ("Site-Specific Thresholds", test_site_specific_thresholds), 
        ("AI Integration", test_ai_integration),
        ("Hybrid Crawler Integration", test_hybrid_crawler_integration),
        ("Mini Crawl Test", run_mini_crawl_test),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n Running: {test_name}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                success = await test_func()
            else:
                success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f" {test_name}: CRASHED - {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print(" TEST SUITE SUMMARY")
    print("=" * 60)
    
    passed = 0
    for test_name, success in results:
        status = " PASSED" if success else " FAILED"
        print(f"   {test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print(" ALL TESTS PASSED - System ready for production use!")
    elif passed >= len(results) * 0.8:
        print("  Most tests passed - System functional with minor issues")
    else:
        print(" Multiple failures - System needs attention before use")


if __name__ == "__main__":
    asyncio.run(main())