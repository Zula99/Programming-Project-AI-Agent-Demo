"""
Hybrid Crawler - Intelligent Site Structure Discovery

Orchestrates between sitemap-first and progressive discovery approaches based on
site characteristics and available information. Integrates with existing 
LinkExtractor for sitemap processing and quality plateau detection for
intelligent stopping conditions.
"""

import asyncio
import logging
import sys
from typing import Dict, List, Set, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import urllib.parse
import time

# Import existing components
from crawler_utils import CrawlConfig, generic_crawl, is_same_site
from quality_plateau import HybridQualityMonitor, QualityMetrics as PlateauQualityMetrics

# Import coverage tracking components
try:
    from dashboard_metrics import CrawlPhase, create_coverage_calculator, get_coverage_calculator
    from coverage_api import initialize_coverage_tracking, finalize_coverage_tracking, generate_run_id
    from websocket_manager import notify_crawl_start, notify_crawl_complete, broadcast_coverage_update
    COVERAGE_TRACKING_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Coverage tracking not available: {e}")
    COVERAGE_TRACKING_AVAILABLE = False

# Import AI components if available
try:
    from ai_content_classifier import AIContentClassifier, BusinessSiteDetector, BusinessSiteType
    AI_AVAILABLE = True
except ImportError as e:
    logging.warning(f"AI classification not available: {e}")
    AI_AVAILABLE = False

# Import LinkExtractor from Utility directory
try:
    utility_path = Path(__file__).parent.parent / "Utility"
    if str(utility_path) not in sys.path:
        sys.path.insert(0, str(utility_path))
    from link_extractor import LinkExtractor
    LINK_EXTRACTOR_AVAILABLE = True
except ImportError as e:
    logging.warning(f"LinkExtractor not available: {e}")
    LINK_EXTRACTOR_AVAILABLE = False


class DiscoveryStrategy(Enum):
    """Site discovery approaches based on US-54 implementation plan"""
    SITEMAP_FIRST = "sitemap_first"        # Scenario A: Sites with accessible sitemaps
    PROGRESSIVE = "progressive"            # Scenario B: Sites without sitemaps


@dataclass
class SitemapAnalysis:
    """Results of sitemap analysis and intelligence gathering"""
    has_sitemap: bool
    sitemap_urls: List[str] = None
    robots_intelligence: Dict[str, Any] = None
    estimated_total_urls: int = 0
    main_sections: List[str] = None
    ai_classified_urls: List[Tuple[str, float, str]] = None  # (url, confidence, reasoning)
    discovery_metadata: Dict[str, Any] = None


@dataclass
class CrawlPlan:
    """Comprehensive crawling plan based on site analysis"""
    strategy: DiscoveryStrategy
    priority_urls: List[str]
    estimated_coverage_target: int
    max_pages_recommendation: int
    sitemap_analysis: Optional[SitemapAnalysis]
    quality_thresholds: Dict[str, float]
    reasoning: str


class HybridCrawler:
    """
    Intelligent crawler that adapts strategy based on site characteristics.
    
    Implements US-54 hybrid approach:
    - Scenario A: Sitemap-First Discovery (with quality plateau detection)
    - Scenario B: Progressive Discovery (with quality plateau detection)
    
    Both scenarios use AI classification and intelligent stopping conditions.
    """
    
    def __init__(self, output_dir: str = "./hybrid_crawl_output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
        # Initialize AI components if available
        self.ai_classifier = None
        self.site_detector = None
        if AI_AVAILABLE:
            try:
                self.site_detector = BusinessSiteDetector()
                # AI classifier will be initialized with API key when needed
            except Exception as e:
                self.logger.warning(f"Failed to initialize AI components: {e}")
    
    async def analyze_site_structure(self, start_url: str) -> SitemapAnalysis:
        """
        Comprehensive site analysis to determine optimal discovery strategy.
        
        Returns:
            SitemapAnalysis with intelligence about site structure and sitemap availability
        """
        self.logger.info(f"🔍 Analyzing site structure for {start_url}")
        
        domain = urllib.parse.urlparse(start_url).netloc
        
        # Initialize analysis result
        analysis = SitemapAnalysis(
            has_sitemap=False,
            sitemap_urls=[],
            main_sections=[],
            discovery_metadata={'analysis_timestamp': time.time()}
        )
        
        if not LINK_EXTRACTOR_AVAILABLE:
            self.logger.warning("LinkExtractor not available, using progressive discovery")
            analysis.discovery_metadata['fallback_reason'] = 'LinkExtractor unavailable'
            return analysis
        
        try:
            # Create temporary directory for LinkExtractor
            temp_dir = self.output_dir / "temp_sitemap_analysis"
            temp_dir.mkdir(exist_ok=True)
            
            # Construct sitemap URL (common patterns)
            sitemap_candidates = [
                f"https://{domain}/sitemap.xml",
                f"https://{domain}/sitemap_index.xml", 
                f"https://www.{domain}/sitemap.xml",
                f"https://www.{domain}/sitemap_index.xml",
                start_url.rstrip('/') + '/sitemap.xml'
            ]
            
            successful_sitemap = None
            
            # Try to find working sitemap
            for sitemap_url in sitemap_candidates:
                try:
                    self.logger.info(f"   Trying sitemap: {sitemap_url}")
                    
                    # Initialize LinkExtractor for this sitemap
                    extractor = LinkExtractor(
                        sitemap_url=sitemap_url,
                        file_name="temp_analysis",
                        output_file="temp_urls.txt", 
                        file_path=str(temp_dir),
                        use_ai=True  # Enable AI for intelligent analysis
                    )
                    
                    # Test sitemap accessibility and extract URLs with AI analysis
                    urls, metadata = await extractor.process_sitemap_with_ai(
                        max_urls=None,  # No limit - process full sitemap
                        sample_content=True  # Get content samples for AI classification
                    )
                    
                    if urls and len(urls) > 1:  # Test minimum for valid sitemap (normally > 5)
                        successful_sitemap = sitemap_url
                        analysis.has_sitemap = True
                        # Use all sitemap URLs
                        analysis.sitemap_urls = urls
                        analysis.estimated_total_urls = len(analysis.sitemap_urls)
                        self.logger.info(f"SUCCESS: Using all {len(analysis.sitemap_urls)} URLs from sitemap (no limit applied)")
                        analysis.ai_classified_urls = metadata.get('ai_classifications', [])
                        analysis.discovery_metadata.update(metadata)
                        
                        # Get robots.txt intelligence
                        analysis.robots_intelligence = extractor.analyze_robots_txt(domain)
                        
                        self.logger.info(f"✅ Found working sitemap: {sitemap_url}")
                        self.logger.info(f"   Discovered {len(urls)} URLs")
                        break
                        
                except Exception as e:
                    self.logger.debug(f"   Sitemap {sitemap_url} failed: {e}")
                    continue
            
            if not successful_sitemap:
                self.logger.info("❌ No accessible sitemap found - will use progressive discovery")
                analysis.discovery_metadata['sitemap_search_attempted'] = len(sitemap_candidates)
                analysis.discovery_metadata['fallback_reason'] = 'No accessible sitemap'
            
            # Cleanup temp directory
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except Exception:
                pass  # Ignore cleanup errors
                
        except Exception as e:
            self.logger.error(f"Site structure analysis failed: {e}")
            analysis.discovery_metadata['analysis_error'] = str(e)
        
        return analysis
    
    def create_crawl_plan(self, start_url: str, analysis: SitemapAnalysis, 
                         site_type: Optional[BusinessSiteType] = None) -> CrawlPlan:
        """
        Create comprehensive crawling plan based on site analysis.
        
        Implements US-54 strategy selection:
        - Scenario A: Sitemap-First Discovery
        - Scenario B: Progressive Discovery
        
        Args:
            start_url: Starting URL for crawling
            analysis: Results from site structure analysis
            site_type: Detected site type for quality threshold configuration
            
        Returns:
            CrawlPlan with strategy, priority URLs, and configuration
        """
        self.logger.info("📋 Creating intelligent crawl plan")
        
        # US-54 Strategy Selection: Only two scenarios
        if analysis.has_sitemap and analysis.sitemap_urls:
            strategy = DiscoveryStrategy.SITEMAP_FIRST
            reasoning = f"Scenario A: Sitemap available ({len(analysis.sitemap_urls)} URLs) - sitemap-first approach with AI prioritization"
        else:
            strategy = DiscoveryStrategy.PROGRESSIVE  
            reasoning = "Scenario B: No sitemap available - progressive discovery from homepage with quality plateau detection"
        
        # Get site-specific quality thresholds
        from crawler_utils import _get_site_specific_thresholds
        if site_type:
            quality_thresholds = _get_site_specific_thresholds(site_type)
        else:
            # Default balanced thresholds
            quality_thresholds = {
                'quality_window_size': 20,
                'worthy_threshold': 0.3,
                'diversity_threshold': 0.8,
                'diversity_window_size': 15
            }
        
        # Configure strategy-specific parameters
        if strategy == DiscoveryStrategy.SITEMAP_FIRST:
            # Scenario A: Parse sitemap for comprehensive URL inventory
            # Apply AI classification to prioritize URLs
            # Extract navigation patterns from sitemap structure
            # Use quality plateau detection during crawling
            
            if analysis.ai_classified_urls:
                # Sort by AI confidence/worthiness for prioritization
                sorted_urls = sorted(
                    analysis.ai_classified_urls, 
                    key=lambda x: x[1], 
                    reverse=True
                )
                priority_urls = [url for url, conf, reason in sorted_urls[:50]]
            else:
                priority_urls = analysis.sitemap_urls[:50]  # Reasonable starting set
            
            estimated_coverage = len(analysis.sitemap_urls)
            max_pages = len(analysis.sitemap_urls) * 3  # Allow for additional discovered URLs (no 500 limit)
            
        else:  # PROGRESSIVE
            # Scenario B: Start with homepage and main navigation extraction
            # Build URL queue progressively as pages are crawled
            # Apply AI classification in real-time
            # Use quality plateau detection to prevent infinite crawling
            # Domain-bounded crawling (stays within single domain)
            
            priority_urls = [start_url]
            estimated_coverage = 150  # Conservative estimate without sitemap
            max_pages = 1000  # Higher limit for full testing (was 300)
        
        plan = CrawlPlan(
            strategy=strategy,
            priority_urls=priority_urls,
            estimated_coverage_target=estimated_coverage,
            max_pages_recommendation=max_pages,
            sitemap_analysis=analysis,
            quality_thresholds=quality_thresholds,
            reasoning=reasoning
        )
        
        self.logger.info(f"📋 Crawl plan created:")
        self.logger.info(f"   Strategy: {strategy.value}")
        self.logger.info(f"   Priority URLs: {len(priority_urls)}")
        self.logger.info(f"   Est. coverage target: {estimated_coverage}")
        self.logger.info(f"   Max pages: {max_pages}")
        self.logger.info(f"   Reasoning: {reasoning}")
        
        return plan
    
    async def execute_hybrid_crawl(self, start_url: str, crawl_config: Optional[CrawlConfig] = None, 
                                 run_id: Optional[str] = None, enable_coverage_tracking: bool = True) -> Tuple[bool, Dict[str, Any]]:
        """
        Execute complete hybrid crawling workflow with intelligent strategy selection.
        
        Implements the full US-54 workflow:
        1. Site structure analysis (sitemap detection)
        2. Strategy selection (Sitemap-First vs Progressive)
        3. AI classification integration
        4. Quality plateau detection for intelligent stopping
        5. Comprehensive results analysis
        
        Args:
            start_url: Starting URL to crawl
            crawl_config: Optional crawl configuration (will be created if not provided)
            
        Returns:
            Tuple of (success: bool, comprehensive_results: Dict)
        """
        try:
            self.logger.info(f" Starting US-54 hybrid crawl of {start_url}")
            start_time = time.time()
            
            # Generate run_id if not provided
            if not run_id:
                run_id = generate_run_id() if COVERAGE_TRACKING_AVAILABLE else f"crawl_{int(time.time())}"
            
            # Phase 1: Site Structure Analysis & Sitemap Detection
            self.logger.info(" Phase 1: Site structure analysis and sitemap detection")
            analysis = await self.analyze_site_structure(start_url)
            
            # Phase 2: Site Type Detection for Quality Thresholds
            site_type = None
            if self.site_detector:
                try:
                    site_type = self.site_detector.detect_site_type(start_url, "", "")
                    self.logger.info(f"  Site type detected: {site_type.value}")
                except Exception as e:
                    self.logger.warning(f"Site type detection failed: {e}")
            
            # Phase 3: Strategy Selection & Crawl Plan Creation
            self.logger.info(" Phase 2: Strategy selection and crawl planning") 
            plan = self.create_crawl_plan(start_url, analysis, site_type)
            
            # Phase 3.5: Initialize Coverage Tracking
            coverage_calculator = None
            if enable_coverage_tracking and COVERAGE_TRACKING_AVAILABLE:
                try:
                    sitemap_urls = analysis.sitemap_urls if analysis.has_sitemap else None
                    coverage_calculator = await initialize_coverage_tracking(run_id, start_url, sitemap_urls)
                    coverage_calculator.set_phase(CrawlPhase.CRAWLING)
                    
                    # Notify WebSocket clients that crawl is starting
                    await notify_crawl_start(run_id, {
                        'start_url': start_url,
                        'strategy': plan.strategy.value,
                        'has_sitemap': analysis.has_sitemap,
                        'estimated_coverage_target': plan.estimated_coverage_target
                    })
                    
                    self.logger.info(f"📊 Coverage tracking initialized for run_id: {run_id}")
                except Exception as e:
                    self.logger.warning(f"Failed to initialize coverage tracking: {e}")
                    enable_coverage_tracking = False
            
            # Phase 4: Crawler Configuration
            self.logger.info("  Phase 3: Configuring adaptive crawler")
            if not crawl_config:
                domain = urllib.parse.urlparse(start_url).netloc
                crawl_config = CrawlConfig(
                    domain=domain,
                    output_root=self.output_dir / domain.replace('.', '_'),
                    max_pages=plan.max_pages_recommendation,  # Use full recommendation
                    #max_pages=2,  # LIMIT DISABLED FOR FULL TESTING
                    request_gap=0.8,  # Respectful crawling
                    respect_robots=False,  # Demo purposes - ignore robots.txt
                    start_url=start_url,
                    # Configure for JS-heavy sites by default
                    javascript=True,
                    wait_for='networkidle',
                    timeout=30,
                    headless=True
                )
            
            # Phase 4.5: Initialize Session Classification Cache
            classification_cache = {}  # Session-scoped classification cache
            self.logger.info("Initialized session classification cache - will use sitemap worthy classifications during crawl")
            
            # Phase 5: Execute Crawling with Classification Cache
            self.logger.info(f"Phase 5: Executing {plan.strategy.value} crawl with cached classifications")
            
            # Add classification cache and run_id to crawl config
            crawl_config.classification_cache = classification_cache
            crawl_config.run_id = run_id  # Pass run_id for coverage tracking integration
            results, stats = await generic_crawl(crawl_config)
            
            # Phase 6: Comprehensive Results Analysis
            crawl_time = time.time() - start_time
            success = len(results) > 0
            
            # Phase 6.5: Finalize Coverage Tracking
            coverage_summary = None
            if enable_coverage_tracking and COVERAGE_TRACKING_AVAILABLE and coverage_calculator:
                try:
                    coverage_summary = await finalize_coverage_tracking(run_id, success, {
                        'crawl_strategy': plan.strategy.value,
                        'us54_scenario': 'A' if plan.strategy == DiscoveryStrategy.SITEMAP_FIRST else 'B',
                        'quality_plateau_triggered': stats.get('quality_plateau_stats', {}).get('should_stop', False)
                    })
                    self.logger.info(f"📊 Coverage tracking finalized: {coverage_summary['final_coverage_percentage']:.1f}% coverage")
                except Exception as e:
                    self.logger.warning(f"Failed to finalize coverage tracking: {e}")
            
            comprehensive_results = {
                'run_id': run_id,
                'success': success,
                'strategy_used': plan.strategy.value,
                'us54_implementation': {
                    'scenario': 'A' if plan.strategy == DiscoveryStrategy.SITEMAP_FIRST else 'B',
                    'sitemap_detected': analysis.has_sitemap,
                    'ai_classification_enabled': AI_AVAILABLE,
                    'quality_plateau_enabled': 'quality_plateau_stats' in stats,
                    'coverage_tracking_enabled': enable_coverage_tracking and COVERAGE_TRACKING_AVAILABLE
                },
                'sitemap_analysis': {
                    'had_sitemap': analysis.has_sitemap,
                    'sitemap_urls_found': len(analysis.sitemap_urls) if analysis.sitemap_urls else 0,
                    'ai_classifications': len(analysis.ai_classified_urls) if analysis.ai_classified_urls else 0
                },
                'crawl_results': {
                    'pages_crawled': stats['pages_crawled'],
                    'successful_crawls': stats['successful_crawls'],
                    'failed_crawls': stats['failed_crawls'],
                    'total_urls_discovered': stats['total_urls_discovered'],
                    'filtering_efficiency': stats['filtering_efficiency']
                },
                'quality_plateau_results': stats.get('quality_plateau_stats', {}),
                'performance': {
                    'total_crawl_time': crawl_time,
                    'avg_time_per_page': crawl_time / max(1, stats['pages_crawled']),
                    'urls_per_second': stats['total_urls_discovered'] / max(1, crawl_time)
                },
                'plan_execution': {
                    'target_coverage': plan.estimated_coverage_target,
                    'actual_pages': stats['pages_crawled'],
                    'coverage_ratio': stats['pages_crawled'] / max(1, plan.estimated_coverage_target),
                    'strategy_reasoning': plan.reasoning
                },
                'coverage_tracking': coverage_summary if coverage_summary else {},
                'output_location': str(crawl_config.output_root)
            }
            
            # Log comprehensive summary
            self.logger.info("    US-54 hybrid crawl completed:")
            self.logger.info(f"   Scenario: {comprehensive_results['us54_implementation']['scenario']}")
            self.logger.info(f"   Strategy: {plan.strategy.value}")
            self.logger.info(f"   Pages crawled: {stats['pages_crawled']}")
            self.logger.info(f"   Success rate: {stats['successful_crawls']}/{stats['pages_crawled']}")
            self.logger.info(f"   Total time: {crawl_time:.1f}s")
            
            if 'quality_plateau_stats' in stats:
                plateau_stats = stats['quality_plateau_stats']
                if plateau_stats:
                    self.logger.info(f"   Final quality: {plateau_stats.get('overall_worthy_ratio', 0):.1%} overall")
                    if plateau_stats.get('should_stop', False):
                        self.logger.info(f"   Intelligent stopping: {plateau_stats.get('stop_reason', 'N/A')}")
            
            return True, comprehensive_results
            
        except Exception as e:
            self.logger.error(f"US-54 hybrid crawl failed: {e}")
            return False, {
                'success': False,
                'error': str(e),
                'strategy_attempted': plan.strategy.value if 'plan' in locals() else 'unknown'
            }

    async def execute_crawl_plan(self, plan, cost_tracker=None) -> Tuple[List, Dict]:
        """
        Execute crawl plan with cost tracking - matches SmartMirrorAgent interface
        
        Args:
            plan: CrawlPlan object with strategy and priority URLs
            cost_tracker: CostTracker instance for tracking AI costs
            
        Returns:
            Tuple of (results: List, stats: Dict)
        """
        try:
            # Create crawl config from plan
            domain = urllib.parse.urlparse(plan.start_url if hasattr(plan, 'start_url') else plan.priority_urls[0]).netloc
            crawl_config = CrawlConfig(
                domain=domain,
                output_root=self.output_dir / domain.replace('.', '_'),
                max_pages=plan.max_pages_recommendation,
                request_gap=0.8,
                respect_robots=False,
                start_url=plan.priority_urls[0] if plan.priority_urls else plan.start_url,
                cost_tracker=cost_tracker  # Add cost tracking
            )
            
            # Execute the crawl using generic_crawl directly to get actual results
            results, generic_stats = await generic_crawl(crawl_config)
            
            # Calculate success from actual results
            successful_results = [r for r in results if r.success]
            success = len(successful_results) > 0
            
            # Use actual results data instead of detailed_results
            pages_crawled = len(results)
            successful_crawls = len(successful_results)
            
            # Get site analysis data for quality metrics
            had_sitemap = hasattr(plan, 'sitemap_urls') and len(plan.sitemap_urls) > 0 if hasattr(plan, 'sitemap_urls') else False
            sitemap_urls_found = len(plan.sitemap_urls) if hasattr(plan, 'sitemap_urls') and plan.sitemap_urls else 0
            
            # Calculate quality metrics based on sitemap analysis and crawl success
            success_rate = successful_crawls / max(1, pages_crawled)
            overall_worthy_ratio = generic_stats.get('overall_worthy_ratio', success_rate)
            
            # Demo quality metrics derived from crawling performance
            content_completeness = success_rate * 100  # Based on successful page crawls
            asset_coverage = success_rate * 90 if success_rate > 0.8 else success_rate * 70  # High success = good assets
            navigation_integrity = (sitemap_urls_found / max(1, pages_crawled)) * 100 if had_sitemap else success_rate * 80
            visual_fidelity = success_rate * 85 if success_rate > 0.9 else success_rate * 75  # High success = good rendering
            site_coverage = (pages_crawled / max(1, sitemap_urls_found)) * 100 if sitemap_urls_found > 0 else success_rate * 80
            overall_score = (content_completeness + asset_coverage + navigation_integrity + visual_fidelity) / 4
            
            stats = {
                'pages_crawled': pages_crawled,
                'successful_crawls': successful_crawls,
                'failed_crawls': generic_stats.get('failed_crawls', pages_crawled - successful_crawls),
                'total_urls_discovered': generic_stats.get('total_urls_discovered', pages_crawled),
                'filtering_efficiency': generic_stats.get('filtering_efficiency', 0.0),
                'quality_plateau_stats': generic_stats.get('quality_plateau_stats', {}),
                'ai_classifications': len(plan.sitemap_analysis.ai_classified_urls) if hasattr(plan, 'sitemap_analysis') and plan.sitemap_analysis.ai_classified_urls else 0,
                'quality_plateau_triggered': generic_stats.get('quality_plateau_stats', {}).get('should_stop', False),
                'success_rate': success_rate,
                # Demo quality metrics derived from sitemap and AI analysis
                'overall_score': overall_score,
                'content_completeness': content_completeness,
                'asset_coverage': asset_coverage,
                'navigation_integrity': navigation_integrity,
                'visual_fidelity': visual_fidelity,
                'site_coverage': site_coverage,
                'url_quality_ratio': overall_worthy_ratio * 100 if overall_worthy_ratio else success_rate * 100
            }
            
            return results, stats
            
        except Exception as e:
            self.logger.error(f"execute_crawl_plan failed: {e}")
            return [], {'error': str(e)}


# Convenience functions for integration with existing systems

async def hybrid_crawl_url(start_url: str, output_dir: str = "./hybrid_output", 
                          enable_coverage_tracking: bool = True) -> Tuple[bool, Dict[str, Any]]:
    """
    Simple interface for US-54 hybrid crawling a single URL.
    
    Args:
        start_url: URL to crawl
        output_dir: Output directory for results
        enable_coverage_tracking: Enable real-time coverage monitoring
        
    Returns:
        Tuple of (success: bool, results: Dict)
    """
    crawler = HybridCrawler(output_dir)
    return await crawler.execute_hybrid_crawl(start_url, enable_coverage_tracking=enable_coverage_tracking)


def create_hybrid_crawler_for_agent(agent_output_dir: str) -> HybridCrawler:
    """
    Create a HybridCrawler instance configured for SmartMirrorAgent integration.
    
    Args:
        agent_output_dir: Output directory from agent
        
    Returns:
        Configured HybridCrawler instance
    """
    return HybridCrawler(output_dir=agent_output_dir)


# Example usage and testing
async def test_hybrid_crawler():
    """Test the US-54 hybrid crawler with different site types"""
    test_urls = [
        "https://www.nab.com.au",      # Banking site with sitemap (Scenario A)
        "https://www.commbank.com.au", # Banking site, JS-heavy (Scenario A/B)
        # Add more test URLs as needed
    ]
    
    for url in test_urls:
        print(f"\n{'='*60}")
        print(f"Testing US-54 hybrid crawler with: {url}")
        print(f"{'='*60}")
        
        crawler = HybridCrawler()
        success, results = await crawler.execute_hybrid_crawl(url)
        
        print(f"Success: {success}")
        if success:
            scenario = results['us54_implementation']['scenario']
            strategy = results['strategy_used']
            pages = results['crawl_results']['pages_crawled']
            
            print(f"US-54 Scenario: {scenario}")
            print(f"Strategy used: {strategy}")
            print(f"Pages crawled: {pages}")
            print(f"Output: {results['output_location']}")


if __name__ == "__main__":
    # Run test
    asyncio.run(test_hybrid_crawler())