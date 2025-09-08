# agent_crawler.py - Generic crawler interface for SmartMirrorAgent
import asyncio
import urllib.parse
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import sys

# Import crawler utilities (now in same directory)
from crawler_utils import CrawlConfig, CrawlResult, generic_crawl

class AgentCrawler:
    """
    Generic crawler that can be configured by the SmartMirrorAgent
    for any website with adaptive parameters
    """
    
    def __init__(self):
        self.last_crawl_results: List[CrawlResult] = []
        self.last_crawl_stats: Dict[str, Any] = {}
    
    async def crawl_website(self, 
                          url: str, 
                          max_pages: int = 50,
                          request_gap: float = 0.6,
                          user_agent: str = "Mozilla/5.0 (compatible; SmartMirrorAgent/1.0)",
                          respect_robots: bool = False,  # Demo sites - ignore robots.txt
                          output_path: Optional[str] = None,
                          # Browser configuration for JS-heavy sites
                          timeout: int = 30,
                          wait_for: str = 'networkidle',
                          headless: bool = True,
                          screenshot: bool = False,
                          javascript: bool = True,
                          max_concurrent: int = 5,
                          # Anti-detection features
                          stealth_mode: bool = False,
                          realistic_viewport: bool = True,
                          extra_headers: Optional[Dict[str, str]] = None,
                          additional_wait: float = 0.0,
                          # Enhanced JS rendering features
                          wait_for_selector: Optional[str] = None,
                          selector_timeout: int = 10000,
                          auto_scroll: bool = False,
                          scroll_delay: int = 1000,
                          post_load_delay: int = 0,
                          js_code: Optional[List[str]] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Crawl a website with the specified configuration
        
        Args:
            url: Starting URL to crawl
            max_pages: Maximum number of pages to crawl
            request_gap: Delay between requests in seconds
            user_agent: User agent string
            respect_robots: Whether to respect robots.txt
            output_path: Custom output directory path
            
        Returns:
            success: Whether crawling completed successfully
            crawl_data: Dictionary containing crawl results and metadata
        """
        try:
            # Extract domain from URL
            parsed = urllib.parse.urlsplit(url)
            domain = parsed.netloc.lower()
            
            # Remove www. for cleaner folder names
            if domain.startswith("www."):
                domain_folder = domain[4:]
            else:
                domain_folder = domain
            
            # Setup output path
            if output_path:
                output_root = Path(output_path)
            else:
                output_root = Path("output") / "agent_crawls" / domain_folder
            
            # Create crawl configuration
            config = CrawlConfig(
                domain=domain,
                output_root=output_root,
                max_pages=max_pages,
                request_gap=request_gap,
                user_agent=user_agent,
                respect_robots=respect_robots,
                start_url=url,
                # Browser configuration
                timeout=timeout,
                wait_for=wait_for,
                headless=headless,
                screenshot=screenshot,
                javascript=javascript,
                max_concurrent=max_concurrent,
                additional_wait=additional_wait,
                # Anti-detection features
                stealth_mode=stealth_mode,
                realistic_viewport=realistic_viewport,
                extra_headers=extra_headers or {},
                # Enhanced JS rendering features
                wait_for_selector=wait_for_selector,
                selector_timeout=selector_timeout,
                auto_scroll=auto_scroll,
                scroll_delay=scroll_delay,
                post_load_delay=post_load_delay,
                js_code=js_code or []
            )
            
            print(f"Starting crawl of {url} (max {max_pages} pages)")
            print(f"Output: {output_root.resolve()}")
            
            # Execute crawl
            results, stats = await generic_crawl(config)
            
            # Store results for quality assessment
            self.last_crawl_results = results
            self.last_crawl_stats = stats
            
            # Prepare return data
            crawl_data = {
                "url": url,
                "domain": domain,
                "config": {
                    "max_pages": max_pages,
                    "request_gap": request_gap,
                    "user_agent": user_agent,
                    "respect_robots": respect_robots
                },
                "results": results,
                "stats": stats,
                "output_path": str(output_root.resolve()),
                "successful": stats["successful_crawls"] > 0
            }
            
            success = stats["successful_crawls"] > 0
            
            print(f"Crawl completed: {stats['successful_crawls']}/{stats['pages_crawled']} successful")
            return success, crawl_data
            
        except Exception as e:
            print(f"Crawl failed: {e}")
            return False, {
                "url": url,
                "error": str(e),
                "successful": False
            }
    
    def get_crawl_summary(self) -> Dict[str, Any]:
        """Get summary of last crawl for quality assessment"""
        if not self.last_crawl_results:
            return {}
            
        successful_results = [r for r in self.last_crawl_results if r.success]
        
        total_content_length = sum(len(r.markdown) for r in successful_results)
        total_html_length = sum(len(r.raw_html) for r in successful_results)
        unique_links = set()
        for r in successful_results:
            unique_links.update(r.links)
        
        return {
            "pages_crawled": len(successful_results),
            "total_content_chars": total_content_length,
            "total_html_chars": total_html_length,
            "unique_links_found": len(unique_links),
            "average_content_per_page": total_content_length / len(successful_results) if successful_results else 0,
            "pages_with_content": len([r for r in successful_results if len(r.markdown) > 100]),
            "pages_with_title": len([r for r in successful_results if r.title]),
        }
    
    def get_content_for_indexing(self) -> List[Dict[str, str]]:
        """
        Extract content in format suitable for OpenSearch indexing
        
        Returns:
            List of documents with url, title, content for search indexing
        """
        documents = []
        
        for result in self.last_crawl_results:
            if result.success and result.markdown:
                doc = {
                    "url": result.url,
                    "title": result.title or "Untitled",
                    "content": result.markdown,
                    "content_type": result.content_type,
                    "content_length": len(result.markdown)
                }
                documents.append(doc)
        
        return documents

async def test_crawler():
    """Test the agent crawler with NAB website"""
    crawler = AgentCrawler()
    
    success, crawl_data = await crawler.crawl_website(
        url="https://www.nab.com.au/",
        max_pages=5,  # Small test
        request_gap=0.5
    )
    
    print(f"Crawl success: {success}")
    if success:
        summary = crawler.get_crawl_summary()
        print(f"Summary: {summary}")
        
        content = crawler.get_content_for_indexing()
        print(f"Indexable documents: {len(content)}")

if __name__ == "__main__":
    asyncio.run(test_crawler())