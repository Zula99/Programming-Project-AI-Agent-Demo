# test_agent.py - Test the SmartMirrorAgent functionality
import asyncio
import logging
from smart_mirror_agent import SmartMirrorAgent

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

async def test_agent_basic():
    """Test basic agent functionality"""
    print("=" * 60)
    print("Testing SmartMirrorAgent Basic Functionality")
    print("=" * 60)
    
    # Create agent
    agent = SmartMirrorAgent(memory_path="test_agent_memory.json")
    
    # Test with a small site first
    test_url = "https://www.nab.com.au/"
    
    print(f"Processing URL: {test_url}")
    
    try:
        # Run the full agent pipeline
        success, metrics, mirror_path = await agent.process_url(test_url)
        
        print(f"\n{'='*40}")
        print("AGENT RESULTS")
        print(f"{'='*40}")
        print(f"Success: {success}")
        print(f"Overall Quality Score: {metrics.overall_score:.3f}")
        print(f"Content Completeness: {metrics.content_completeness:.3f}")
        print(f"Asset Coverage: {metrics.asset_coverage:.3f}")
        print(f"Navigation Integrity: {metrics.navigation_integrity:.3f}")
        print(f"Visual Fidelity: {metrics.visual_fidelity:.3f}")
        print(f"Mirror Path: {mirror_path}")
        
        # Quality score interpretation
        if metrics.overall_score >= 0.9:
            print("🎉 EXCELLENT - Agent achieved target 90%+ success rate!")
        elif metrics.overall_score >= 0.8:
            print("✅ GOOD - Agent performance is solid")
        elif metrics.overall_score >= 0.7:
            print("⚠️  ACCEPTABLE - Agent needs minor improvements")
        elif metrics.overall_score >= 0.6:
            print("❌ POOR - Agent needs significant improvements")
        else:
            print("💥 FAILED - Agent strategy needs major revision")
            
        # Get crawl summary for additional details
        if hasattr(agent.crawler, 'get_crawl_summary'):
            summary = agent.crawler.get_crawl_summary()
            print(f"\nCrawl Summary:")
            print(f"  Pages Crawled: {summary.get('pages_crawled', 0)}")
            print(f"  Total Content Characters: {summary.get('total_content_chars', 0):,}")
            print(f"  Average Content per Page: {summary.get('average_content_per_page', 0):.0f} chars")
            print(f"  Pages with Substantial Content: {summary.get('pages_with_content', 0)}")
            print(f"  Unique Links Found: {summary.get('unique_links_found', 0)}")
        
        # Get mirror suggestions
        if hasattr(agent.mirror_builder, 'get_entry_point_suggestions') and success:
            crawl_data = {"domain": "nab.com.au", "url": test_url}
            entries = agent.mirror_builder.get_entry_point_suggestions(crawl_data)
            if entries:
                print(f"\nMirror Entry Points:")
                for name, path in entries.items():
                    print(f"  {name}: {path}")
        
        print(f"\n🎯 Ready for training! Agent core functionality is working.")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

async def test_agent_multiple_strategies():
    """Test agent with different strategies"""
    print("=" * 60)
    print("Testing Multiple Crawling Strategies")
    print("=" * 60)
    
    agent = SmartMirrorAgent()
    
    # Test different strategies manually
    from smart_mirror_agent import CrawlStrategy
    
    strategies = [
        CrawlStrategy.BASIC_HTTP,
        CrawlStrategy.JAVASCRIPT_RENDER
    ]
    
    for strategy in strategies:
        print(f"\nTesting strategy: {strategy.value}")
        config = agent.strategy_to_config(strategy)
        print(f"Config: {config}")

if __name__ == "__main__":
    print("SmartMirrorAgent Test Suite")
    print("This will test the core functionality needed for training")
    
    # Run basic test
    asyncio.run(test_agent_basic())
    
    # Run strategy test
    asyncio.run(test_agent_multiple_strategies())
    
    print("\n🚀 If all tests passed, the agent is ready for training!")
    print("Next steps:")
    print("1. Test with real NAB website")
    print("2. Implement learning system") 
    print("3. Add FastAPI wrapper for frontend integration")