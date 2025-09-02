#!/usr/bin/env python3
"""
Test script for True AI Integration
Tests AI classification of actual page content after fetching
"""
import asyncio
import sys
from pathlib import Path

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent.parent / "crawl4ai"))

from smart_mirror_agent import SmartMirrorAgent

async def test_true_ai_integration():
    """Test AI classification of actual crawled content"""
    print("Testing True AI Integration")
    print("=" * 60)
    
    # Initialize agent
    agent = SmartMirrorAgent()
    
    # Test URLs that should show clear AI decision making
    test_cases = [
        {
            "url": "https://www.nab.com.au/business",
            "expect": "Should analyze NAB business content and determine demo value",
            "name": "NAB Business"
        },
        {
            "url": "https://www.nab.com.au/personal/banking",
            "expect": "Should analyze personal banking content for demo value",
            "name": "NAB Personal Banking"
        }
    ]
    
    for case in test_cases:
        print(f"\nTesting: {case['name']} ({case['url']})")
        print(f"Expected: {case['expect']}")
        print("-" * 50)
        
        try:
            # Use agent_main with 50 page limit for focused testing
            from agent_main import SmartMirrorAgentIntegrated
            agent_main = SmartMirrorAgentIntegrated()
            
            print(f"Testing with 50 page limit...")
            result = await agent_main.process_url(case["url"], max_pages=50)
            
            success = result.get('success', False)
            print(f"Result: {'SUCCESS' if success else 'FAILED'}")
            
            if success:
                crawl_data = result.get('crawl_data')
                if crawl_data:
                    print(f"Pages Crawled: {len(crawl_data.pages)}")
                    
                    # Look for AI classifications in the crawl results
                    ai_decisions = []
                    for page in crawl_data.pages[:5]:  # Show first 5
                        if hasattr(page, 'ai_classification') and page.ai_classification:
                            ai_decisions.append({
                                'url': page.url,
                                'worthy': page.ai_classification.get('worthy', True),
                                'confidence': page.ai_classification.get('confidence', 0.0),
                                'reasoning': page.ai_classification.get('reasoning', '')
                            })
                    
                    if ai_decisions:
                        print("AI Classification Decisions:")
                        for decision in ai_decisions:
                            print(f"  {decision['url']}")
                            print(f"    Worthy: {decision['worthy']}")
                            print(f"    Confidence: {decision['confidence']:.2f}")
                            print(f"    Reasoning: {decision['reasoning'][:100]}...")
                            print()
                    else:
                        print("No AI classification data found")
                else:
                    print("No crawl data available")
                    
            else:
                error_msg = result.get('error', 'Unknown error')
                print(f"Error: {error_msg}")
                
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("True AI Integration Test Summary")
    print("=" * 60)
    print("What we should see:")
    print("1. AI classifications with real reasoning about page content")
    print("2. Confidence scores from actual AI analysis")
    print("3. Evidence of API calls in the logs")
    print("4. Content-aware filtering decisions")

async def test_single_page_ai():
    """Test AI classification on a single page for detailed analysis"""
    print("\nDetailed Single Page AI Test")
    print("=" * 60)
    
    try:
        from crawler_utils import crawl_page, CrawlConfig
        from crawl4ai import AsyncWebCrawler
        
        # Test configuration
        config = CrawlConfig(
            domain="nab.com.au",
            output_root=Path("output/test"),
            max_pages=1,
            request_gap=1.0,
            user_agent="SmartMirrorAgent-AI-Test",
            respect_robots=False
        )
        
        # Test URL with rich content
        test_url = "https://www.nab.com.au/business"
        
        print(f"Testing detailed AI classification for: {test_url}")
        
        async with AsyncWebCrawler() as crawler:
            result = await crawl_page(crawler, test_url, config)
            
            print(f"Crawl Success: {result.success}")
            
            if result.success:
                print(f"Title: {result.title}")
                print(f"Content Length: {len(result.markdown)} characters")
                
                if result.ai_classification:
                    ai = result.ai_classification
                    print(f"\nAI Classification Results:")
                    print(f"  Worthy: {ai['worthy']}")
                    print(f"  Confidence: {ai['confidence']:.3f}")
                    print(f"  Reasoning: {ai['reasoning']}")
                else:
                    print("No AI classification data")
            else:
                print(f"Crawl failed: {result.error}")
                
    except Exception as e:
        print(f"ERROR in detailed test: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main test function"""
    print("True AI Integration Test Suite")
    print("=" * 60)
    print("This tests AI classification of actual page content")
    print("You should see:")
    print("- Real AI API calls analyzing page content")
    print("- Intelligent reasoning about content value") 
    print("- Confidence scores from OpenAI")
    print()
    
    # Test 1: Agent-level integration
    await test_true_ai_integration()
    
    # Test 2: Single page detailed analysis
    await test_single_page_ai()
    
    print("\n" + "=" * 60)
    print("Implementation Complete!")
    print("=" * 60)
    print("Next steps:")
    print("1. Monitor costs (should be ~$0.001-0.002 per page)")
    print("2. Review AI reasoning quality")
    print("3. Adjust confidence thresholds if needed")
    print("4. Consider adding AI classification data to reports")

if __name__ == "__main__":
    asyncio.run(main())