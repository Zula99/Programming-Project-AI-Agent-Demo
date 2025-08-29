# run_agent.py - Interactive SmartMirrorAgent runner
import asyncio
import logging
import sys
from pathlib import Path
from smart_mirror_agent import SmartMirrorAgent

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_user_input():
    """Get target site from user - agent decides everything else"""
    print("=" * 60)
    print(" SmartMirrorAgent - Autonomous Demo Site Builder")
    print("=" * 60)
    print()
    
    # Get target site only
    while True:
        site = input("Enter target website (e.g., nab.com.au, example.com): ").strip()
        if site:
            # Add https:// if not present
            if not site.startswith(('http://', 'https://')):
                site = f"https://{site}"
                if not site.startswith('https://www.') and not '://' in site[8:]:
                    # Add www. if it looks like a main domain
                    site = site.replace('https://', 'https://www.')
            break
        print(" Please enter a valid website")
    
    print(f" Target: {site}")
    print(" Agent will automatically determine:")
    print("   • Optimal crawling strategy")
    print("   • Required coverage for quality demo")
    print("   • When to stop for best results")
    print()
    
    return site

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
        
        # Create agent
        agent = SmartMirrorAgent(memory_path="interactive_agent_memory.json")
        
        print(" Processing website...")
        
        # Run the agent - it decides everything
        success, metrics, mirror_path = await agent.process_url(target_url)
        
        # Display results
        print("\n" + "=" * 60)
        print(" RESULTS")
        print("=" * 60)
        
        if success:
            print(" Crawl completed successfully!")
        else:
            print(" Crawl failed or had issues")
        
        print(f"\n Quality Metrics:")
        print(f"   Overall Score:        {metrics.overall_score:.1%}")
        print(f"   Content Completeness: {metrics.content_completeness:.1%}")
        print(f"   Asset Coverage:       {metrics.asset_coverage:.1%}")
        print(f"   Navigation Integrity: {metrics.navigation_integrity:.1%}")
        print(f"   Visual Fidelity:      {metrics.visual_fidelity:.1%}")
        print(f"   Site Coverage:        {metrics.site_coverage:.1%} (90% target)")
        print(f"   URL Quality Ratio:    {metrics.url_quality_ratio:.1%} ({metrics.total_filtered_urls} filtered)")
        
        # Show filtering breakdown if significant
        if metrics.total_filtered_urls > 5:
            print(f"\n Smart Filtering Results:")
            if metrics.filtering_breakdown:
                sorted_filters = sorted(metrics.filtering_breakdown.items(), key=lambda x: x[1], reverse=True)
                for category, count in sorted_filters[:5]:
                    if count > 0:
                        category_name = category.replace('_', ' ').title()
                        print(f"   {category_name}: {count} URLs")
        
        # Quality interpretation
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
        
        # Show mirror info
        if success and mirror_path:
            print(f"\n  Static Mirror:")
            print(f"   Location: {mirror_path}")
            
            # Get entry points
            if hasattr(agent.mirror_builder, 'get_entry_point_suggestions'):
                import urllib.parse
                parsed = urllib.parse.urlsplit(target_url)
                domain = parsed.netloc.lower()
                if domain.startswith("www."):
                    domain = domain[4:]
                    
                crawl_data = {"domain": domain, "url": target_url}
                entries = agent.mirror_builder.get_entry_point_suggestions(crawl_data)
                
                if entries:
                    print(f"\n Entry Points:")
                    for name, path in entries.items():
                        print(f"   {name}: {path}")
                        
                    # Show how to serve
                    print(f"\n To view the mirror:")
                    print(f"   1. cd {Path(mirror_path).parent}")
                    print(f"   2. python -m http.server 8000")
                    print(f"   3. Open browser to: http://localhost:8000/{Path(mirror_path).name}/")
        
        print("\n" + "=" * 60)
        
        # Ask if user wants to run another site
        print()
        run_another = input("Run another site? (y/n): ").strip().lower()
        if run_another in ('y', 'yes'):
            await run_agent_interactive()
        else:
            print("\n Thanks for using SmartMirrorAgent!")
            
    except KeyboardInterrupt:
        print("\n\n⏹  Cancelled by user")
    except Exception as e:
        print(f"\n Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting SmartMirrorAgent Interactive Mode...")
    asyncio.run(run_agent_interactive())