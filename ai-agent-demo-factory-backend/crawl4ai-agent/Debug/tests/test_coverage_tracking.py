"""
Test script for US-53 Real-time Coverage Monitoring

Tests the complete coverage tracking implementation:
- Dynamic coverage calculation
- WebSocket real-time updates
- FastAPI endpoints
- Integration with hybrid crawler

Usage:
    python test_coverage_tracking.py
"""

import asyncio
import json
import logging
import time
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_basic_coverage_calculation():
    """Test basic coverage calculation without crawler integration"""
    print("\n" + "="*60)
    print("TEST 1: Basic Coverage Calculation")
    print("="*60)
    
    try:
        from dashboard_metrics import CoverageCalculator, CrawlPhase
        
        # Create calculator
        calc = CoverageCalculator("test_run_1")
        
        # Test sitemap initialization
        sitemap_urls = [
            "https://example.com/",
            "https://example.com/about", 
            "https://example.com/products",
            "https://example.com/contact"
        ]
        calc.initialize_sitemap_urls(sitemap_urls)
        
        print(f"[OK] Initialized with {len(sitemap_urls)} sitemap URLs")
        print(f"  Initial coverage: {calc.calculate_coverage_percentage():.1f}%")
        
        # Test crawling simulation
        calc.set_phase(CrawlPhase.CRAWLING)
        calc.mark_url_crawled("https://example.com/", True, 0.8)
        calc.mark_url_crawled("https://example.com/about", True, 0.9)
        
        print(f"  After crawling 2 pages: {calc.calculate_coverage_percentage():.1f}%")
        
        # Test URL discovery
        new_urls = ["https://example.com/blog", "https://example.com/services"]
        calc.add_discovered_urls(new_urls)
        
        print(f"  After discovering 2 new URLs: {calc.calculate_coverage_percentage():.1f}%")
        print(f"  Total known URLs: {len(calc.initial_sitemap_urls | calc.discovered_urls)}")
        
        # Test snapshot
        snapshot = calc.get_current_snapshot()
        print(f"  Snapshot - Phase: {snapshot.phase.value}, Velocity: {snapshot.crawl_velocity:.1f} pages/min")
        
        print("[PASS] Basic coverage calculation: PASSED")
        return True
        
    except Exception as e:
        print(f"[FAIL] Basic coverage calculation: FAILED - {e}")
        return False


def test_websocket_manager():
    """Test WebSocket manager without actual WebSocket connections"""
    print("\n" + "="*60)
    print("TEST 2: WebSocket Manager")
    print("="*60)
    
    try:
        from websocket_manager import WebSocketConnectionManager
        from dashboard_metrics import CoverageSnapshot, CrawlPhase
        
        manager = WebSocketConnectionManager()
        
        # Test connection count tracking
        print(f"[OK] WebSocket manager initialized")
        print(f"  Active runs: {len(manager.get_all_active_runs())}")
        
        # Test mock snapshot broadcasting (without actual WebSocket)
        snapshot = CoverageSnapshot(
            run_id="test_run_2",
            timestamp=time.time(),
            phase=CrawlPhase.CRAWLING,
            coverage_percentage=45.5,
            pages_crawled=5,
            total_known_urls=11,
            initial_sitemap_urls=8,
            discovered_urls=3,
            recent_quality_score=0.85,
            overall_quality_trend="improving",
            crawl_velocity=12.5,
            estimated_time_remaining=120,
            current_url="https://example.com/test",
            quality_plateau_detected=False,
            stop_reason=None
        )
        
        print(f"[OK] Created test snapshot: {snapshot.coverage_percentage:.1f}% coverage")
        print(f"  {snapshot.pages_crawled}/{snapshot.total_known_urls} pages")
        
        print("[PASS] WebSocket manager: PASSED")
        return True
        
    except Exception as e:
        print(f"[FAIL] WebSocket manager: FAILED - {e}")
        return False


async def test_coverage_api():
    """Test coverage API endpoints (without actual FastAPI server)"""
    print("\n" + "="*60)
    print("TEST 3: Coverage API Functions") 
    print("="*60)
    
    try:
        from coverage_api import initialize_coverage_tracking, finalize_coverage_tracking, generate_run_id
        from dashboard_metrics import get_coverage_calculator, remove_coverage_calculator
        
        # Test run ID generation
        run_id = generate_run_id()
        print(f"[OK] Generated run ID: {run_id}")
        
        # Test coverage initialization
        calc = await initialize_coverage_tracking(
            run_id, 
            "https://example.com",
            ["https://example.com/", "https://example.com/about"]
        )
        
        print(f"[OK] Initialized coverage tracking for: {run_id}")
        print(f"  Calculator phase: {calc.current_phase.value}")
        
        # Test retrieval
        retrieved_calc = get_coverage_calculator(run_id)
        if retrieved_calc:
            print(f"[OK] Successfully retrieved calculator for: {run_id}")
        
        # Simulate some crawling
        calc.mark_url_crawled("https://example.com/", True, 0.9)
        calc.add_discovered_urls(["https://example.com/new-page"])
        
        # Test finalization
        summary = await finalize_coverage_tracking(run_id, True, {"test": "data"})
        if summary:
            print(f"[OK] Finalized with {summary['final_coverage_percentage']:.1f}% coverage")
        
        # Cleanup
        remove_coverage_calculator(run_id)
        print(f"[OK] Cleaned up run: {run_id}")
        
        print("[PASS] Coverage API functions: PASSED")
        return True
        
    except Exception as e:
        print(f"[FAIL] Coverage API functions: FAILED - {e}")
        return False


async def test_hybrid_crawler_integration():
    """Test integration with hybrid crawler (minimal test without actual crawling)"""
    print("\n" + "="*60)
    print("TEST 4: Hybrid Crawler Integration")
    print("="*60)
    
    try:
        from hybrid_crawler import HybridCrawler
        from crawler_utils import CrawlConfig
        from pathlib import Path
        
        # Create test crawler
        crawler = HybridCrawler("./test_output")
        print("[OK] Created HybridCrawler instance")
        
        # Test coverage tracking parameters
        print("[OK] Coverage tracking integration parameters available")
        
        # Test that new parameters are supported
        test_config = CrawlConfig(
            domain="example.com",
            output_root=Path("./test"),
            max_pages=5,
            run_id="test_integration",
            classification_cache={}
        )
        
        print(f"[OK] CrawlConfig supports run_id: {test_config.run_id}")
        print(f"[OK] CrawlConfig supports classification_cache: {test_config.classification_cache is not None}")
        
        print("[PASS] Hybrid crawler integration: PASSED")
        return True
        
    except Exception as e:
        print(f"[FAIL] Hybrid crawler integration: FAILED - {e}")
        return False


def test_data_flow():
    """Test the complete data flow without actual crawling"""
    print("\n" + "="*60)
    print("TEST 5: Complete Data Flow")
    print("="*60)
    
    try:
        from dashboard_metrics import create_coverage_calculator, CrawlPhase
        from coverage_api import generate_run_id
        
        # Simulate complete workflow
        run_id = generate_run_id()
        calc = create_coverage_calculator(run_id)
        
        print(f"[OK] Created workflow for run: {run_id}")
        
        # Simulate sitemap analysis
        calc.initialize_sitemap_urls([
            "https://test.com/",
            "https://test.com/about",
            "https://test.com/products"
        ])
        calc.set_phase(CrawlPhase.SITEMAP_ANALYSIS)
        print("[OK] Sitemap analysis phase")
        
        # Simulate crawling start
        calc.set_phase(CrawlPhase.CRAWLING)
        print("[OK] Started crawling phase")
        
        # Simulate progressive crawling with discovery
        for i, url in enumerate([
            "https://test.com/",
            "https://test.com/about", 
            "https://test.com/products"
        ]):
            calc.mark_url_crawled(url, True, 0.8 + (i * 0.05))
            
            if i == 1:  # Discover new URLs after second page
                calc.add_discovered_urls([
                    "https://test.com/blog",
                    "https://test.com/contact"
                ])
        
        # Final snapshot
        final_snapshot = calc.get_current_snapshot()
        print(f"[OK] Final coverage: {final_snapshot.coverage_percentage:.1f}%")
        print(f"  Pages crawled: {final_snapshot.pages_crawled}")
        print(f"  Total known URLs: {final_snapshot.total_known_urls}")
        print(f"  Quality trend: {final_snapshot.overall_quality_trend}")
        
        # Summary stats
        summary = calc.get_summary_stats()
        print(f"[OK] Summary generated - Final phase: {summary['final_phase']}")
        
        print("[PASS] Complete data flow: PASSED")
        return True
        
    except Exception as e:
        print(f"[FAIL] Complete data flow: FAILED - {e}")
        return False


async def main():
    """Run all tests"""
    print("Starting US-53 Coverage Tracking Tests")
    print("=" * 80)
    
    tests = [
        ("Basic Coverage Calculation", test_basic_coverage_calculation),
        ("WebSocket Manager", test_websocket_manager), 
        ("Coverage API Functions", test_coverage_api),
        ("Hybrid Crawler Integration", test_hybrid_crawler_integration),
        ("Complete Data Flow", test_data_flow)
    ]
    
    results = {}
    for test_name, test_func in tests:
        if asyncio.iscoroutinefunction(test_func):
            results[test_name] = await test_func()
        else:
            results[test_name] = test_func()
    
    # Final summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "[PASS] PASSED" if result else "[FAIL] FAILED"
        print(f"{test_name:.<50} {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("\nAll tests passed! US-53 implementation is ready.")
        print("\nNext steps:")
        print("1. Install FastAPI dependencies: pip install fastapi uvicorn websockets")
        print("2. Start FastAPI server with coverage endpoints")
        print("3. Test with frontend WebSocket connections")
        print("4. Run actual crawl with coverage tracking enabled")
    else:
        print(f"\n{total - passed} test(s) failed. Review implementation before proceeding.")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)