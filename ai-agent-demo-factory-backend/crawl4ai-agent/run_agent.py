# run_agent.py - SmartMirrorAgent runner (interactive and CLI modes)
import asyncio
import logging
import sys
import argparse
from pathlib import Path
from smart_mirror_agent import SmartMirrorAgent
from crawl_logger import CrawlSession
import httpx
import uuid

# Setup logging  
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s', datefmt='%H:%M:%S')

async def auto_configure_proxy(target_url: str, run_id: str = None):
    """Auto-configure proxy server when crawl completes successfully"""
    if not run_id:
        run_id = str(uuid.uuid4())
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post("http://localhost:8000/auto-configure", json={
                "target_url": target_url,
                "run_id": run_id,
                "enabled": True
            })
            
            if response.status_code == 200:
                logging.info(f"Auto-Proxy Configured!")
                logging.info(f"   Proxy URL: http://localhost:8000/proxy/")
                logging.info(f"   Target: {target_url}")
                logging.info(f"   Run ID: {run_id}")
                return True
            else:
                logging.warning(f"Proxy configuration failed: {response.status_code}")
                return False

    except httpx.ConnectError:
        logging.warning(f"Proxy server not running (http://localhost:8000)")
        logging.info(f"   Start with: python ai-agent-demo-factory-backend/Proxy/proxy_server.py")
        return False
    except Exception as e:
        logging.warning(f"Proxy configuration error: {e}")
        return False




def normalize_url(url):
    """Normalize URL format"""
    if not url:
        return None
        
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = f"https://{url}"
        if not url.startswith('https://www.') and '://' not in url[8:]:
            # Add www. if it looks like a main domain
            url = url.replace('https://', 'https://www.')
    return url

def get_user_input(preset_url=None):
    """Get target site from user - agent decides everything else"""
    logging.info("=" * 60)
    logging.info(" SmartMirrorAgent - Autonomous Demo Site Builder")
    logging.info("=" * 60)
    logging.info("")

    if preset_url:
        # URL provided via command line - auto-fill but show what we're using
        site = normalize_url(preset_url)
        logging.info(f"Target URL provided: {site}")
        logging.info("")
    else:
        # Interactive input
        while True:
            site = input("Enter target website (e.g., nab.com.au, example.com): ").strip()
            if site:
                site = normalize_url(site)
                break
            logging.info(" Please enter a valid website")

    logging.info(f" Target: {site}")
    logging.info(" Agent will automatically determine:")
    logging.info("   - Optimal crawling strategy")
    logging.info("   - Required coverage for quality demo")
    logging.info("   - When to stop for best results")
    logging.info("")

    return site

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='SmartMirrorAgent - Autonomous Demo Site Builder',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python run_agent.py

  # Auto-fill URL mode  
  python run_agent.py nab.com.au
  python run_agent.py https://www.commbank.com.au
  
  # Docker usage
  docker run smart-mirror-agent nab.com.au
        """
    )
    
    parser.add_argument(
        'url', 
        nargs='?',
        help='Target website URL (e.g., nab.com.au, example.com). Auto-fills the input but keeps interactive display.'
    )
    
    return parser.parse_args()

async def run_agent_interactive():
    """Run the agent with user input"""
    try:
        # Get target site only
        target_url = get_user_input()

        logging.info("")
        logging.info("=" * 60)
        logging.info(" Starting SmartMirrorAgent")
        logging.info("=" * 60)
        logging.info(f" Target: {target_url}")
        logging.info(" Agent operating autonomously...")
        logging.info("")
        
        # Start comprehensive logging
        with CrawlSession(target_url, "./output/logs") as logger:
            logger.log_phase("INITIALIZATION", f"Target: {target_url}")
            
            # Create agent
            agent = SmartMirrorAgent(memory_path="interactive_agent_memory.json")
            
            try:
                logging.info(" Processing website...")
                logger.log_phase("CRAWLING", "Starting autonomous crawl process")
                
                # Run the agent - it decides everything
                success, metrics, output_path = await agent.process_url(target_url)
                
                logger.log_phase("QUALITY_ASSESSMENT", "Analyzing crawl quality")
                
                # Log metrics
                if metrics:
                    metrics_dict = {
                        "success": success,
                        "content_completeness": getattr(metrics, 'content_completeness', 'N/A'),
                        "asset_coverage": getattr(metrics, 'asset_coverage', 'N/A'),
                        "navigation_integrity": getattr(metrics, 'navigation_integrity', 'N/A'),
                        "visual_fidelity": getattr(metrics, 'visual_fidelity', 'N/A'),
                        "overall_score": getattr(metrics, 'overall_score', 'N/A'),
                        "site_coverage": getattr(metrics, 'site_coverage', 'N/A'),
                        "output_path": output_path or 'N/A'
                    }
                    logger.log_metrics(metrics_dict)
                
                logger.log_phase("RESULTS", "Displaying crawl results")
                
            except Exception as e:
                logger.log_error(e, "agent_process")
                success, metrics, output_path = False, None, None
            finally:
                # Ensure agent resources are cleaned up
                if hasattr(agent, 'cleanup'):
                    await agent.cleanup()
                    logger.log_phase("CLEANUP", "Agent resources cleaned up")
        
        # Display results (after logging context ends)
        logging.info("")
        logging.info("=" * 60)
        logging.info(" RESULTS")
        logging.info("=" * 60)

        # Debug auto-proxy trigger conditions
        logging.info(f" DEBUG: success={success}, output_path={output_path}")

        if success:
            logging.info(" Crawl completed successfully!")
        else:
            logging.warning(" Crawl failed or had issues")
        
        if metrics:
            logging.info("")
            logging.info(" Quality Metrics:")
            logging.info(f"   Overall Score:        {metrics.overall_score:.1%}")
            logging.info(f"   Content Completeness: {metrics.content_completeness:.1%}")
            logging.info(f"   Asset Coverage:       {metrics.asset_coverage:.1%}")
            logging.info(f"   Navigation Integrity: {metrics.navigation_integrity:.1%}")
            logging.info(f"   Visual Fidelity:      {metrics.visual_fidelity:.1%}")
            logging.info(f"   Site Coverage:        {metrics.site_coverage:.1%} (90% target)")
            logging.info(f"   URL Quality Ratio:    {metrics.url_quality_ratio:.1%} ({metrics.total_filtered_urls} filtered)")
        else:
            logging.warning(" Quality Metrics: Not available due to crawl failure")
        
        # Show filtering breakdown if significant
        if metrics and hasattr(metrics, 'total_filtered_urls') and metrics.total_filtered_urls > 5:
            logging.info("")
            logging.info(" Smart Filtering Results:")
            if metrics.filtering_breakdown:
                sorted_filters = sorted(metrics.filtering_breakdown.items(), key=lambda x: x[1], reverse=True)
                for category, count in sorted_filters[:5]:
                    if count > 0:
                        category_name = category.replace('_', ' ').title()
                        logging.info(f"   {category_name}: {count} URLs")
        
        # Quality interpretation
        if metrics and hasattr(metrics, 'overall_score'):
            score = metrics.overall_score
            if score >= 0.9:
                logging.info("")
                logging.info(" EXCELLENT! Achieved 90%+ target success rate")
            elif score >= 0.8:
                logging.info("")
                logging.info(" GOOD performance")
            elif score >= 0.7:
                logging.info("")
                logging.info(" ACCEPTABLE - minor improvements needed")
            elif score >= 0.6:
                logging.warning("")
                logging.warning(" NEEDS WORK - significant improvements needed")
            else:
                logging.error("")
                logging.error(" FAILED - major strategy revision required")
        
        # Show crawl details
        if hasattr(agent.crawler, 'get_crawl_summary'):
            summary = agent.crawler.get_crawl_summary()
            logging.info("")
            logging.info(" Crawl Summary:")
            logging.info(f"   Pages crawled:     {summary.get('pages_crawled', 0)}")
            logging.info(f"   Content chars:     {summary.get('total_content_chars', 0):,}")
            logging.info(f"   Avg per page:      {summary.get('average_content_per_page', 0):.0f} chars")
            logging.info(f"   Pages with content: {summary.get('pages_with_content', 0)}")
            logging.info(f"   Unique links:      {summary.get('unique_links_found', 0)}")
        
        # Show output path for OpenSearch indexing
        if success and output_path:
            logging.info("")
            logging.info(" Crawl Output:")
            logging.info(f"   Location: {output_path}")
            logging.info(f"   Ready for: OpenSearch indexing, Proxy system")

            # Auto-configure proxy for successful crawls
            crawl_id = str(uuid.uuid4())
            await auto_configure_proxy(target_url, crawl_id)

        logging.info("")
        logging.info("=" * 60)

        # Ask if user wants to run another site
        logging.info("")
        run_another = input("Run another site? (y/n): ").strip().lower()
        if run_another in ('y', 'yes'):
            return True  # Signal to continue
        else:
            logging.info(" Thanks for using SmartMirrorAgent!")
            return False  # Signal to exit

    except KeyboardInterrupt:
        logging.warning("Cancelled by user")
        return False
    except Exception as e:
        logging.error(f" Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main loop to handle multiple crawls without recursion"""
    logging.info("Starting SmartMirrorAgent Interactive Mode...")

    while True:
        continue_crawling = await run_agent_interactive()
        if not continue_crawling:
            break

if __name__ == "__main__":
    asyncio.run(main())