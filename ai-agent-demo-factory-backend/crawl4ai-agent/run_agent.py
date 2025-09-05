# run_agent.py - SmartMirrorAgent runner (interactive and CLI modes)
import asyncio
import logging
import sys
import argparse
from pathlib import Path
from smart_mirror_agent import SmartMirrorAgent
from crawl_logger import CrawlSession

# Setup logging  
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')




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
    print("=" * 60)
    print(" SmartMirrorAgent - Autonomous Demo Site Builder")
    print("=" * 60)
    print()
    
    if preset_url:
        # URL provided via command line - auto-fill but show what we're using
        site = normalize_url(preset_url)
        print(f"Target URL provided: {site}")
        print()
    else:
        # Interactive input
        while True:
            site = input("Enter target website (e.g., nab.com.au, example.com): ").strip()
            if site:
                site = normalize_url(site)
                break
            print(" Please enter a valid website")
    
    print(f" Target: {site}")
    print(" Agent will automatically determine:")
    print("   • Optimal crawling strategy")
    print("   • Required coverage for quality demo")
    print("   • When to stop for best results")
    print()
    
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
        
        print("\n" + "=" * 60)
        print(" Starting SmartMirrorAgent")
        print("=" * 60)
        print(f" Target: {target_url}")
        print(" Agent operating autonomously...")
        print()
        
        # Start comprehensive logging
        with CrawlSession(target_url, "./output/logs") as logger:
            logger.log_phase("INITIALIZATION", f"Target: {target_url}")
            
            # Create agent
            agent = SmartMirrorAgent(memory_path="interactive_agent_memory.json")
            
            try:
                print(" Processing website...")
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
        print("\n" + "=" * 60)
        print(" RESULTS")
        print("=" * 60)
        
        if success:
            print(" Crawl completed successfully!")
        else:
            print(" Crawl failed or had issues")
        
        if metrics:
            print(f"\n Quality Metrics:")
            print(f"   Overall Score:        {metrics.overall_score:.1%}")
            print(f"   Content Completeness: {metrics.content_completeness:.1%}")
            print(f"   Asset Coverage:       {metrics.asset_coverage:.1%}")
            print(f"   Navigation Integrity: {metrics.navigation_integrity:.1%}")
            print(f"   Visual Fidelity:      {metrics.visual_fidelity:.1%}")
            print(f"   Site Coverage:        {metrics.site_coverage:.1%} (90% target)")
            print(f"   URL Quality Ratio:    {metrics.url_quality_ratio:.1%} ({metrics.total_filtered_urls} filtered)")
        else:
            print(f"\n Quality Metrics: Not available due to crawl failure")
        
        # Show filtering breakdown if significant  
        if metrics and hasattr(metrics, 'total_filtered_urls') and metrics.total_filtered_urls > 5:
            print(f"\n Smart Filtering Results:")
            if metrics.filtering_breakdown:
                sorted_filters = sorted(metrics.filtering_breakdown.items(), key=lambda x: x[1], reverse=True)
                for category, count in sorted_filters[:5]:
                    if count > 0:
                        category_name = category.replace('_', ' ').title()
                        print(f"   {category_name}: {count} URLs")
        
        # Quality interpretation
        if metrics and hasattr(metrics, 'overall_score'):
            score = metrics.overall_score
            if score >= 0.9:
                print("\n EXCELLENT! Achieved 90%+ target success rate")
            elif score >= 0.8:
                print("\n GOOD performance")
            elif score >= 0.7:
                print("\n  ACCEPTABLE - minor improvements needed")
            elif score >= 0.6:
                print("\n NEEDS WORK - significant improvements needed")
            else:
                print("\n FAILED - major strategy revision required")
        
        # Show crawl details
        if hasattr(agent.crawler, 'get_crawl_summary'):
            summary = agent.crawler.get_crawl_summary()
            print(f"\n Crawl Summary:")
            print(f"   Pages crawled:     {summary.get('pages_crawled', 0)}")
            print(f"   Content chars:     {summary.get('total_content_chars', 0):,}")
            print(f"   Avg per page:      {summary.get('average_content_per_page', 0):.0f} chars")
            print(f"   Pages with content: {summary.get('pages_with_content', 0)}")
            print(f"   Unique links:      {summary.get('unique_links_found', 0)}")
        
        # Show output path for OpenSearch indexing
        if success and output_path:
            print(f"\n  Crawl Output:")
            print(f"   Location: {output_path}")
            print(f"   Ready for: OpenSearch indexing, Proxy system")
        
        print("\n" + "=" * 60)
        
        # Ask if user wants to run another site
        print()
        run_another = input("Run another site? (y/n): ").strip().lower()
        if run_another in ('y', 'yes'):
            return True  # Signal to continue
        else:
            print("\n Thanks for using SmartMirrorAgent!")
            return False  # Signal to exit
            
    except KeyboardInterrupt:
        print("\n\n⏹  Cancelled by user")
        return False
    except Exception as e:
        print(f"\n Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main loop to handle multiple crawls without recursion"""
    print("Starting SmartMirrorAgent Interactive Mode...")
    
    while True:
        continue_crawling = await run_agent_interactive()
        if not continue_crawling:
            break

if __name__ == "__main__":
    asyncio.run(main())