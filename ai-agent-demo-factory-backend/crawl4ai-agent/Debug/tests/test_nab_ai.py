#!/usr/bin/env python3
"""
Simple test of AI integration with NAB content
"""
import asyncio
import sys
from pathlib import Path

# Add the parent directory to the path
sys.path.append(str(Path(__file__).parent.parent.parent / "crawl4ai"))

async def test_nab_ai():
    """Test AI classification on NAB pages"""
    print("Testing NAB AI Integration")
    print("=" * 50)
    
    try:
        from crawler_utils import crawl_page, CrawlConfig
        from crawl4ai import AsyncWebCrawler
        
        # Test URLs for NAB
        test_urls = [
            "https://www.nab.com.au/business",
            "https://www.nab.com.au/personal/banking",
            "https://www.nab.com.au/about-us/contact-us"
        ]
        
        # Configuration
        config = CrawlConfig(
            domain="nab.com.au",
            output_root=Path("output/test"),
            max_pages=1,
            request_gap=1.0,
            user_agent="SmartMirrorAgent-AI-Test",
            respect_robots=False
        )
        
        async with AsyncWebCrawler() as crawler:
            for url in test_urls:
                print(f"\nTesting: {url}")
                print("-" * 40)
                
                result = await crawl_page(crawler, url, config)
                
                print(f"Crawl Success: {result.success}")
                
                if result.success:
                    print(f"Title: {result.title}")
                    print(f"Content Length: {len(result.markdown)} characters")
                    
                    if result.ai_classification:
                        ai = result.ai_classification
                        print(f"\nAI Classification:")
                        print(f"  Worthy: {ai['worthy']}")
                        print(f"  Confidence: {ai['confidence']:.3f}")
                        print(f"  Reasoning: {ai['reasoning']}")
                        
                        # Show cost estimate
                        tokens_est = len(result.markdown) // 4  # Rough estimate
                        cost_est = tokens_est * 0.0000015  # GPT-3.5-turbo rate
                        print(f"  Estimated cost: ${cost_est:.6f}")
                    else:
                        print("No AI classification data")
                else:
                    print(f"Crawl failed: {result.error}")
                
                print()
                
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_nab_ai())