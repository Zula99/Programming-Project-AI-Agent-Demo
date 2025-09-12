"""
SmartMirrorAgent - Core adaptive agent for web crawling and content processing

Single adaptive agent with learning capabilities and memory system for
achieving 90% visual fidelity and content coverage across all site types.

Core Components:
- Site Memory: Pattern database for similar sites and successful strategies
- Quality Monitor: Real-time assessment during crawling
- Strategy Adaptor: Dynamic parameter adjustment based on quality feedback  
- Learning System: Stores successful patterns for future use
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
import urllib.parse
import time
from agent_crawler import AgentCrawler


class SiteType(Enum):
    """Site classification types for strategy selection"""
    STATIC_HTML = "static_html"
    JAVASCRIPT_HEAVY = "javascript_heavy"
    SPA_REACT = "spa_react"
    SPA_ANGULAR = "spa_angular"
    SPA_VUE = "spa_vue"
    WORDPRESS = "wordpress"
    ECOMMERCE = "ecommerce"
    BANKING = "banking"
    NEWS = "news"
    UNKNOWN = "unknown"


class CrawlStrategy(Enum):
    """Available crawling strategies"""
    BASIC_HTTP = "basic_http"
    JAVASCRIPT_RENDER = "javascript_render"
    FULL_BROWSER = "full_browser"
    HYBRID = "hybrid"


@dataclass
class QualityMetrics:
    """Quality assessment metrics for crawl success"""
    content_completeness: float = 0.0  # 30% weight
    asset_coverage: float = 0.0        # 20% weight
    navigation_integrity: float = 0.0   # 20% weight
    visual_fidelity: float = 0.0       # 15% weight
    site_coverage: float = 0.0         # 10% weight - Coverage of important site areas
    url_quality_ratio: float = 0.0     # 5% weight - Quality URLs vs junk URLs
    overall_score: float = 0.0
    
    # Additional metrics for reporting
    total_filtered_urls: int = 0
    filtering_breakdown: dict = None
    
    def calculate_overall(self) -> float:
        """Calculate weighted overall quality score including URL quality penalty"""
        self.overall_score = (
            self.content_completeness * 0.30 +
            self.asset_coverage * 0.20 +
            self.navigation_integrity * 0.20 +
            self.visual_fidelity * 0.15 +
            self.site_coverage * 0.10 +
            self.url_quality_ratio * 0.05
        )
        return self.overall_score


@dataclass
class SitePattern:
    """Stored pattern for successful crawling strategies"""
    url_domain: str
    site_type: SiteType
    strategy: CrawlStrategy
    success_metrics: QualityMetrics
    crawl_config: Dict[str, Any]
    timestamp: str
    frameworks_detected: List[str]


@dataclass  
class ReconResults:
    """Results from site reconnaissance phase"""
    site_type: SiteType
    frameworks: List[str]
    js_complexity: float
    page_load_time: float
    asset_count: int
    recommended_strategy: CrawlStrategy
    estimated_total_pages: int
    main_sections: List[str]
    content_depth_estimate: int
    recommended_sample_size: int


class SmartMirrorAgent:
    """
    Single adaptive agent for intelligent web crawling and content processing
    
    Flow: URL Input → Check Memory → Quick Recon → Strategy Selection → 
          Adaptive Crawl → Quality Monitoring → Learning Storage
    """
    
    def __init__(self, memory_path: str = "agent_memory.json"):
        self.logger = logging.getLogger(__name__)
        self.memory_path = Path(memory_path)
        self.site_memory: List[SitePattern] = []
        self.crawler = AgentCrawler()
        self.load_memory()
        
    def load_memory(self):
        """Load stored patterns from memory database"""
        if self.memory_path.exists():
            try:
                with open(self.memory_path, 'r') as f:
                    data = json.load(f)
                    self.site_memory = [
                        SitePattern(**pattern) for pattern in data.get('patterns', [])
                    ]
                self.logger.info(f"Loaded {len(self.site_memory)} patterns from memory")
            except Exception as e:
                self.logger.error(f"Failed to load memory: {e}")
                
    def save_memory(self):
        """Save current patterns to memory database"""
        try:
            data = {
                'patterns': [
                    {
                        'url_domain': pattern.url_domain,
                        'site_type': pattern.site_type.value,
                        'strategy': pattern.strategy.value,
                        'success_metrics': {
                            'content_completeness': pattern.success_metrics.content_completeness,
                            'asset_coverage': pattern.success_metrics.asset_coverage,
                            'navigation_integrity': pattern.success_metrics.navigation_integrity,
                            'visual_fidelity': pattern.success_metrics.visual_fidelity,
                            'overall_score': pattern.success_metrics.overall_score
                        },
                        'crawl_config': pattern.crawl_config,
                        'timestamp': pattern.timestamp,
                        'frameworks_detected': pattern.frameworks_detected
                    }
                    for pattern in self.site_memory
                ]
            }
            with open(self.memory_path, 'w') as f:
                json.dump(data, f, indent=2)
            self.logger.info(f"Saved {len(self.site_memory)} patterns to memory")
        except Exception as e:
            self.logger.error(f"Failed to save memory: {e}")
            
    async def process_url(self, url: str) -> Tuple[bool, QualityMetrics, str]:
        """
        Main processing flow for a URL
        
        Returns:
            success: bool - Whether crawling succeeded
            metrics: QualityMetrics - Quality assessment
            output_path: str - Path to crawled data (for OpenSearch indexing)
        """
        self.logger.info(f"Processing URL: {url}")
        
        # Step 1: Check memory for similar sites
        similar_pattern = self.find_similar_pattern(url)
        
        # Step 2: Quick reconnaissance 
        recon_results = await self.reconnaissance(url)
        
        # Step 3: Strategy selection
        strategy = self.select_strategy(recon_results, similar_pattern)
        
        # Step 4: Adaptive crawling with quality monitoring
        crawl_success, crawl_data = await self.adaptive_crawl(url, strategy, recon_results)
        
        # Step 5: Quality assessment
        quality_metrics = await self.assess_quality(crawl_data)
        
        # Step 6: Get output path for OpenSearch indexing
        output_path = ""
        if crawl_success:
            output_path = crawl_data.get("output_path", "")
            
        # Step 7: Learning - store successful patterns
        if quality_metrics.overall_score >= 0.7:
            await self.store_learning(url, recon_results, strategy, quality_metrics, crawl_data)
            
        return crawl_success, quality_metrics, output_path
        
    def find_similar_pattern(self, url: str) -> Optional[SitePattern]:
        """Find similar successful patterns in memory"""
        # TODO: Implement similarity matching based on domain, frameworks, etc.
        return None
        
    async def reconnaissance(self, url: str) -> ReconResults:
        """Quick reconnaissance to understand site characteristics and plan smart crawling"""
        self.logger.info(f"Performing reconnaissance on {url}")
        
        try:
            # Quick crawl of homepage for analysis
            success, crawl_data = await self.crawler.crawl_website(
                url=url,
                max_pages=1,  # Just homepage for recon
                request_gap=0.3,  # Fast for recon
                user_agent="Mozilla/5.0 (compatible; SmartMirrorAgent-Recon/1.0)"
            )
            
            if not success:
                self.logger.warning("Reconnaissance failed, using fallback analysis")
                return self._fallback_recon(url)
            
            # Analyze the homepage
            results = self.crawler.last_crawl_results
            if not results or not results[0].success:
                return self._fallback_recon(url)
            
            homepage_result = results[0]
            html = homepage_result.raw_html
            links = homepage_result.links
            
            # Detect site type and frameworks
            site_type = self._detect_site_type(html, url)
            frameworks = self._detect_frameworks(html)
            
            # Analyze JavaScript complexity
            js_complexity = self._analyze_js_complexity(html)
            
            # Estimate site structure
            main_sections = self._identify_main_sections(html, links)
            estimated_total_pages = self._estimate_total_pages(links, main_sections)
            
            # Determine optimal sample size for 90% coverage
            recommended_sample_size = self._calculate_optimal_sample_size(
                estimated_total_pages, site_type, main_sections
            )
            
            # Select strategy based on analysis
            recommended_strategy = self._select_optimal_strategy(site_type, js_complexity, frameworks)
            
            self.logger.info(f"   Reconnaissance complete:")
            self.logger.info(f"   Site type: {site_type.value}")
            self.logger.info(f"   Frameworks: {frameworks}")
            self.logger.info(f"   Main sections: {len(main_sections)} identified")
            self.logger.info(f"   Estimated pages: {estimated_total_pages}")
            self.logger.info(f"   Recommended sample: {recommended_sample_size}")
            self.logger.info(f"   Strategy: {recommended_strategy.value}")
            
            return ReconResults(
                site_type=site_type,
                frameworks=frameworks,
                js_complexity=js_complexity,
                page_load_time=1.0,  # Placeholder
                asset_count=len([link for link in links if self._is_asset_link(link)]),
                recommended_strategy=recommended_strategy,
                estimated_total_pages=estimated_total_pages,
                main_sections=main_sections,
                content_depth_estimate=len(homepage_result.markdown),
                recommended_sample_size=recommended_sample_size
            )
            
        except Exception as e:
            self.logger.error(f"Reconnaissance failed: {e}")
            return self._fallback_recon(url)
        
    def select_strategy(self, recon: ReconResults, similar_pattern: Optional[SitePattern]) -> CrawlStrategy:
        """Select optimal crawling strategy based on reconnaissance and memory"""
        if similar_pattern:
            return similar_pattern.strategy
        return recon.recommended_strategy
        
    async def adaptive_crawl(self, url: str, strategy: CrawlStrategy, recon: ReconResults) -> Tuple[bool, Dict[str, Any]]:
        """Execute intelligent crawling with US-54 hybrid crawler integration"""
        try:
            # Import hybrid crawler system
            from hybrid_crawler import HybridCrawler
            from cost_tracker import CostTrackingSession
            from urllib.parse import urlparse
            
            # Extract domain for cost tracking
            domain = urlparse(url).netloc.replace('www.', '')
            
            # Initialize hybrid crawler with cost tracking
            with CostTrackingSession(domain, "./output/cost_logs") as cost_tracker:
                hybrid_crawler = HybridCrawler(
                    output_dir=f"./output/agent_crawls/{domain}"
                )
                
                self.logger.info(f"🔍 Using US-54 Hybrid Crawler System")
                
                # Step 1: Analyze site structure (sitemap-first vs progressive)
                analysis = await hybrid_crawler.analyze_site_structure(url)
                
                # Step 2: Create intelligent crawl plan
                plan = hybrid_crawler.create_crawl_plan(url, analysis)
                
                self.logger.info(f"📋 Crawl Plan:")
                self.logger.info(f"   Strategy: {plan.strategy.value}")
                self.logger.info(f"   Max pages: {plan.max_pages_recommendation}")
                self.logger.info(f"   Priority URLs: {len(plan.priority_urls)}")
                self.logger.info(f"   Reasoning: {plan.reasoning}")
                
                # Step 3: Execute hybrid crawl with cost tracking
                try:
                    results, stats = await hybrid_crawler.execute_crawl_plan(
                        plan=plan,
                        cost_tracker=cost_tracker
                    )
                    
                    # Calculate success metrics safely
                    successful_results = [r for r in results if hasattr(r, 'success') and r.success]
                    success = len(successful_results) > 0
                    success_rate = len(successful_results) / len(results) if results else 0
                    
                    # Build crawl_data compatible with existing system
                    crawl_data = {
                        "output_path": f"./output/agent_crawls/{domain}",
                        "results": results,
                        "stats": stats,
                        "cost_summary": cost_tracker.get_session_stats(),
                        "hybrid_analysis": {
                            "has_sitemap": analysis.has_sitemap,
                            "strategy_used": plan.strategy.value,
                            "urls_discovered": len(plan.priority_urls) if hasattr(plan, 'priority_urls') and plan.priority_urls else 0,
                            "ai_classifications": stats.get('ai_classifications', 0),
                            "quality_plateau_triggered": stats.get('quality_plateau_triggered', False)
                        }
                    }
                    
                    self.logger.info(f"✅ Hybrid crawl completed:")
                    self.logger.info(f"   Pages crawled: {len(results)}")
                    self.logger.info(f"   Success rate: {len(successful_results)}/{len(results)} ({success_rate:.1%})")
                    self.logger.info(f"   AI cost: ${cost_tracker.total_session_cost:.4f}")
                    
                    return success, crawl_data
                    
                except Exception as hybrid_error:
                    self.logger.error(f"Hybrid crawler failed: {hybrid_error}")
                    # Fallback to original system
                    return await self._fallback_to_original_crawl(url, strategy, recon)
                    
        except ImportError as import_error:
            self.logger.warning(f"Hybrid crawler not available: {import_error}")
            # Fallback to original system
            return await self._fallback_to_original_crawl(url, strategy, recon)
        except Exception as e:
            self.logger.error(f"Adaptive crawl failed: {e}")
            return False, {"error": str(e)}
            
    async def _fallback_to_original_crawl(self, url: str, strategy: CrawlStrategy, recon: ReconResults) -> Tuple[bool, Dict[str, Any]]:
        """Fallback to original AgentCrawler system if hybrid crawler fails"""
        self.logger.info("🔄 Falling back to original crawler system")
        
        try:
            # Get strategy configuration with stealth mode preserved
            strategy_config = self.strategy_to_config(strategy)
            
            # Initialize AgentCrawler with full configuration
            success, crawl_data = await self.crawler.crawl_website(
                url,
                max_pages=strategy_config.get('max_pages', 80),
                request_gap=strategy_config.get('request_gap', 0.6),
                respect_robots=strategy_config.get('respect_robots', False),
                # Browser configuration
                timeout=strategy_config.get('timeout', 30),
                wait_for=strategy_config.get('wait_for', 'domcontentloaded'),
                headless=strategy_config.get('headless', True),
                screenshot=strategy_config.get('screenshot', False),
                javascript=strategy_config.get('javascript', True),
                max_concurrent=strategy_config.get('max_concurrent', 5),
                # Anti-detection features (stealth mode kept)
                stealth_mode=strategy_config.get('stealth_mode', False),
                realistic_viewport=strategy_config.get('realistic_viewport', True),
                extra_headers=strategy_config.get('extra_headers', {}),
                # Enhanced JS rendering parameters
                wait_for_selector=strategy_config.get('wait_for_selector'),
                selector_timeout=strategy_config.get('selector_timeout', 10000),
                auto_scroll=strategy_config.get('auto_scroll', False),
                scroll_delay=strategy_config.get('scroll_delay', 1000),
                post_load_delay=strategy_config.get('post_load_delay', 0),
                js_code=strategy_config.get('js_code', [])
            )
            
            # Add reconnaissance data to crawl results
            if crawl_data:
                crawl_data["reconnaissance"] = {
                    "site_type": recon.site_type.value,
                    "frameworks": recon.frameworks,
                    "estimated_total_pages": recon.estimated_total_pages,
                    "main_sections": recon.main_sections,
                    "recommended_sample_size": recon.recommended_sample_size
                }
            
            return success, crawl_data
            
        except Exception as e:
            self.logger.error(f"Fallback crawl failed: {e}")
            return False, {"error": str(e)}
    
    def _calculate_optimal_delay(self, site_type: SiteType, strategy: CrawlStrategy) -> float:
        """Calculate optimal request delay based on site type and strategy"""
        base_delays = {
            CrawlStrategy.BASIC_HTTP: 0.3,
            CrawlStrategy.JAVASCRIPT_RENDER: 0.6,
            CrawlStrategy.FULL_BROWSER: 1.0,
            CrawlStrategy.HYBRID: 0.5
        }
        
        base_delay = base_delays.get(strategy, 0.6)
        
        # Adjust based on site type
        if site_type == SiteType.BANKING:
            return base_delay * 1.5  # Be more polite with banking sites
        elif site_type in [SiteType.NEWS, SiteType.ECOMMERCE]:
            return base_delay * 0.8  # These sites handle more traffic
        
        return base_delay
    
    def strategy_to_config(self, strategy: CrawlStrategy) -> Dict[str, Any]:
        """Convert strategy enum to crawler configuration"""
        configs = {
            CrawlStrategy.BASIC_HTTP: {
                'timeout': 10,
                'max_concurrent': 10,
                'delay': 0.5,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                "max_pages": 50,
                "request_gap": 0.5,
                "respect_robots": False
            },
            CrawlStrategy.JAVASCRIPT_RENDER: {
                'timeout': 45,  # Increased for JS rendering
                'max_concurrent': 4,
                'delay': 1.5,
                'wait_for': 'networkidle',
                'javascript': True,
                'additional_wait': 2.0,  # Extra wait for JS completion
                'post_load_delay': 2000,  # 2 seconds after loading
                'auto_scroll': True,  # Trigger lazy loading
                'js_code': [
                    'window.scrollTo(0, document.body.scrollHeight);',
                    'await new Promise(r => setTimeout(r, 500));',
                    'window.scrollTo(0, 0);'
                ],
                "max_pages": 100,
                "request_gap": 1.5,
                "respect_robots": False
            },
            CrawlStrategy.FULL_BROWSER: {
                'timeout': 90,  # Increased for heavy JS apps like CommBank
                'max_concurrent': 2,  # Reduced to avoid overwhelming JS-heavy sites
                'delay': 4.0,  # Increased delay for JS loading
                'headless': True,  # Fixed: should be headless for production
                'wait_for': 'networkidle',
                'additional_wait': 3.0,  # Artificial wait after networkidle for JS/lazy content
                'screenshot': True,
                'stealth_mode': True,  # Enable anti-detection
                'realistic_viewport': True,
                'viewport': {'width': 1920, 'height': 1080},  # Ensure large enough for hero sections
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
                'extra_headers': {
                    'Accept-Language': 'en-AU,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    # Force specific A/B test variation for Money Plan hero
                    'X-Forwarded-For': '203.217.5.1',  # Australia IP to avoid geo-targeting
                    'Cache-Control': 'no-cache',
                    'Cookie': 'mbox=PC#1234567890.31_0#1999999999|session#1234567890-123456#1999999999'  # Force specific mbox experience
                },
                # Enhanced JS rendering settings
                'wait_for_selector': '.hero-container, .app.homepage, main.honeycomb',  # Wait for CommBank main elements
                'selector_timeout': 10000,  # 10 second timeout for selector wait
                'auto_scroll': True,  # Enable auto-scroll to trigger lazy loading
                'scroll_delay': 1000,  # Wait between scroll actions
                'post_load_delay': 3000,  # Extra 3 seconds after all loading for JS to finish
                'js_code': [
                    # Auto-scroll to trigger lazy loading
                    'window.scrollTo(0, document.body.scrollHeight);',
                    'await new Promise(r => setTimeout(r, 1000));',  # Wait 1s
                    'window.scrollTo(0, 0);',  # Scroll back to top
                    'await new Promise(r => setTimeout(r, 500));',   # Wait 0.5s
                ],
                "max_pages": 80,
                "request_gap": 4.0,  # Increased for JS stability
                "respect_robots": False
            },
            CrawlStrategy.HYBRID: {
                'timeout': 20,
                'max_concurrent': 7,
                'delay': 1.0,
                'adaptive': True,
                "max_pages": 120,
                "request_gap": 1.0,
                "respect_robots": False
            }
        }
        
        return configs.get(strategy, configs[CrawlStrategy.BASIC_HTTP])
    
    def _fallback_recon(self, url: str) -> ReconResults:
        """Fallback reconnaissance when homepage analysis fails"""
        return ReconResults(
            site_type=SiteType.UNKNOWN,
            frameworks=[],
            js_complexity=0.5,
            page_load_time=2.0,
            asset_count=20,
            recommended_strategy=CrawlStrategy.JAVASCRIPT_RENDER,
            estimated_total_pages=100,
            main_sections=["home", "about", "contact"],
            content_depth_estimate=1000,
            recommended_sample_size=30
        )
    
    def _detect_site_type(self, html: str, url: str) -> SiteType:
        """Detect site type based on HTML content and URL"""
        html_lower = html.lower()
        url_lower = url.lower()
        
        # Banking sites
        if any(word in url_lower for word in ['bank', 'nab', 'commonwealth', 'westpac', 'anz']):
            return SiteType.BANKING
        
        # E-commerce indicators
        if any(word in html_lower for word in ['add to cart', 'shopping cart', 'checkout', 'price', '$']):
            return SiteType.ECOMMERCE
            
        # News sites
        if any(word in html_lower for word in ['article', 'news', 'breaking', 'latest']):
            return SiteType.NEWS
        
        # WordPress detection
        if 'wp-content' in html_lower or 'wordpress' in html_lower:
            return SiteType.WORDPRESS
        
        # JavaScript framework detection
        if any(fw in html_lower for fw in ['react', 'angular', 'vue']):
            if 'react' in html_lower:
                return SiteType.SPA_REACT
            elif 'angular' in html_lower:
                return SiteType.SPA_ANGULAR  
            elif 'vue' in html_lower:
                return SiteType.SPA_VUE
        
        # Heavy JavaScript detection
        js_scripts = html_lower.count('<script')
        if js_scripts > 10:
            return SiteType.JAVASCRIPT_HEAVY
        elif js_scripts < 3:
            return SiteType.STATIC_HTML
            
        return SiteType.UNKNOWN
    
    def _detect_frameworks(self, html: str) -> List[str]:
        """Detect JavaScript frameworks and libraries"""
        frameworks = []
        html_lower = html.lower()
        
        framework_patterns = {
            'react': ['react', '_react', 'reactdom'],
            'angular': ['angular', 'ng-app', '@angular'],
            'vue': ['vue.js', 'vuejs', '__vue__'],
            'jquery': ['jquery', '$'],
            'bootstrap': ['bootstrap', 'bs-'],
            'tailwind': ['tailwind', 'tw-'],
            'webpack': ['webpack', '__webpack'],
            'next.js': ['next.js', '_next'],
            'nuxt': ['nuxt', '_nuxt']
        }
        
        for framework, patterns in framework_patterns.items():
            if any(pattern in html_lower for pattern in patterns):
                frameworks.append(framework)
        
        return frameworks
    
    def _analyze_js_complexity(self, html: str) -> float:
        """Analyze JavaScript complexity (0.0 = simple, 1.0 = very complex)"""
        js_indicators = html.lower().count('<script')
        external_js = html.lower().count('src=')
        inline_js_size = sum(len(script) for script in html.split('<script'))
        
        # Normalize complexity score
        complexity = min((js_indicators * 0.1 + external_js * 0.05 + inline_js_size * 0.00001), 1.0)
        return complexity
    
    def _identify_main_sections(self, html: str, links: set) -> List[str]:
        """Identify main navigation sections from HTML and links"""
        sections = set()
        
        # Common navigation patterns
        nav_patterns = [
            'about', 'products', 'services', 'contact', 'help', 'support',
            'news', 'blog', 'careers', 'investor', 'personal', 'business',
            'home', 'solutions', 'resources', 'learn', 'get-started'
        ]
        
        # Extract from navigation HTML
        import re
        nav_matches = re.findall(r'<nav[^>]*>(.*?)</nav>', html, re.IGNORECASE | re.DOTALL)
        for nav_content in nav_matches:
            for pattern in nav_patterns:
                if pattern in nav_content.lower():
                    sections.add(pattern)
        
        # Extract from main menu areas
        menu_matches = re.findall(r'class="[^"]*menu[^"]*"[^>]*>(.*?)</[^>]*>', html, re.IGNORECASE | re.DOTALL)
        for menu_content in menu_matches:
            for pattern in nav_patterns:
                if pattern in menu_content.lower():
                    sections.add(pattern)
        
        # Extract from URLs
        for link in list(links)[:50]:  # Check first 50 links
            for pattern in nav_patterns:
                if f'/{pattern}' in link.lower() or f'{pattern}.' in link.lower():
                    sections.add(pattern)
        
        return list(sections) if sections else ['home', 'about', 'contact']
    
    def _estimate_total_pages(self, links: set, sections: List[str]) -> int:
        """Estimate total pages based on discovered links and sections"""
        unique_paths = set()
        
        for link in links:
            try:
                from urllib.parse import urlparse
                path = urlparse(link).path
                # Extract meaningful path segments
                segments = [s for s in path.split('/') if s and not s.startswith('.')]
                if segments:
                    unique_paths.add('/'.join(segments[:2]))  # First 2 levels
            except:
                continue
        
        # Estimate based on sections and link diversity
        base_estimate = len(unique_paths) * 2  # Assume each path has sub-pages
        section_multiplier = max(len(sections), 3)  # At least 3 sections
        
        # Apply heuristics based on site patterns
        estimated = min(base_estimate * section_multiplier, 1000)  # Cap at 1000
        
        return max(estimated, 20)  # Minimum 20 pages
    
    def _calculate_optimal_sample_size(self, estimated_pages: int, site_type: SiteType, sections: List[str]) -> int:
        """Calculate optimal sample size for 90% coverage"""
        
        # Base coverage ratios by site type
        coverage_ratios = {
            SiteType.STATIC_HTML: 0.7,      # Need more pages for static sites
            SiteType.JAVASCRIPT_HEAVY: 0.4,  # Fewer pages but more content per page
            SiteType.SPA_REACT: 0.3,        # SPAs have rich content per page
            SiteType.SPA_ANGULAR: 0.3,
            SiteType.SPA_VUE: 0.3,
            SiteType.WORDPRESS: 0.5,        # Standard blog/cms structure
            SiteType.ECOMMERCE: 0.6,        # Need product variety
            SiteType.BANKING: 0.4,          # Focus on main services
            SiteType.NEWS: 0.8,             # Need article variety
            SiteType.UNKNOWN: 0.5
        }
        
        ratio = coverage_ratios.get(site_type, 0.5)
        base_sample = int(estimated_pages * ratio)
        
        # Ensure minimum coverage per section
        min_per_section = 3
        section_minimum = len(sections) * min_per_section
        
        # Final sample size with reasonable bounds
        sample_size = max(base_sample, section_minimum)
        sample_size = min(sample_size, 1)  # Maximum 200 pages @CLAUDE This sets max page limit for crawl
        sample_size = max(sample_size, 1)   # Minimum 15 pages @CLAUDE This sets minimum page limit for crawl
        
        return sample_size
    
    def _select_optimal_strategy(self, site_type: SiteType, js_complexity: float, frameworks: List[str]) -> CrawlStrategy:
        """Select optimal crawling strategy based on site analysis"""
        
        # Strategy selection logic
        if js_complexity > 0.7 or any(fw in frameworks for fw in ['react', 'angular', 'vue']):
            return CrawlStrategy.FULL_BROWSER
        elif js_complexity > 0.4 or site_type in [SiteType.JAVASCRIPT_HEAVY, SiteType.BANKING]:
            return CrawlStrategy.JAVASCRIPT_RENDER
        elif site_type == SiteType.STATIC_HTML:
            return CrawlStrategy.BASIC_HTTP
        else:
            return CrawlStrategy.HYBRID
    
    def _is_asset_link(self, link: str) -> bool:
        """Check if link points to an asset"""
        asset_extensions = {'.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2'}
        return any(link.lower().endswith(ext) for ext in asset_extensions)
    
    def _assess_site_coverage(self, crawl_data: Dict[str, Any], summary: Dict[str, Any]) -> float:
        """Assess how well we covered the important parts of the site (90% target)"""
        try:
            recon_data = crawl_data.get("reconnaissance", {})
            main_sections = recon_data.get("main_sections", [])
            estimated_total = recon_data.get("estimated_total_pages", 100)
            recommended_sample = recon_data.get("recommended_sample_size", 50)
            
            pages_crawled = summary.get("pages_crawled", 0)
            
            # Coverage based on hitting our intelligent target
            target_coverage = min(pages_crawled / recommended_sample, 1.0) if recommended_sample > 0 else 0
            
            # Bonus for section diversity (did we hit different areas of the site?)
            if self.crawler.last_crawl_results:
                crawled_urls = [r.url for r in self.crawler.last_crawl_results if r.success]
                sections_found = set()
                
                for url in crawled_urls:
                    for section in main_sections:
                        if section.lower() in url.lower():
                            sections_found.add(section)
                
                section_coverage = len(sections_found) / len(main_sections) if main_sections else 1.0
                
                # Combine target achievement with section diversity
                site_coverage = (target_coverage * 0.7 + section_coverage * 0.3)
            else:
                site_coverage = target_coverage
            
            return min(site_coverage, 1.0)
            
        except Exception as e:
            self.logger.error(f"Site coverage assessment failed: {e}")
            return 0.5  # Neutral score on failure
        
    async def assess_quality(self, crawl_data: Dict[str, Any]) -> QualityMetrics:
        """Assess crawl quality across multiple dimensions"""
        if not crawl_data.get("successful", False):
            return QualityMetrics()
        
        try:
            # Get crawl summary from the crawler
            summary = self.crawler.get_crawl_summary()
            stats = crawl_data.get("stats", {})
            
            # Content Completeness (35% weight)
            # Based on pages with substantial content and average content per page
            pages_with_content = summary.get("pages_with_content", 0)
            total_pages = summary.get("pages_crawled", 1)
            avg_content = summary.get("average_content_per_page", 0)
            
            content_ratio = pages_with_content / total_pages if total_pages > 0 else 0
            content_depth = min(avg_content / 1000, 1.0) if avg_content > 0 else 0  # Normalize to 1000 chars
            content_completeness = (content_ratio * 0.6 + content_depth * 0.4)
            
            # Asset Coverage (25% weight)  
            # TODO: Implement actual asset downloading and counting
            # For now, estimate based on pages successfully crawled vs attempted
            successful_crawls = stats.get("successful_crawls", 0)
            total_attempts = stats.get("pages_crawled", 1)
            asset_coverage = successful_crawls / total_attempts if total_attempts > 0 else 0
            
            # Navigation Integrity (20% weight)
            # Based on internal links found and pages successfully crawled
            unique_links = summary.get("unique_links_found", 0)
            # Simple heuristic: more internal links found = better navigation coverage
            navigation_integrity = min(unique_links / 50, 1.0)  # Normalize to 50 links max
            
            # Visual Fidelity (20% weight)
            # Based on pages with titles and overall success rate
            pages_with_titles = summary.get("pages_with_title", 0)
            title_ratio = pages_with_titles / total_pages if total_pages > 0 else 0
            success_rate = successful_crawls / total_attempts if total_attempts > 0 else 0
            visual_fidelity = (title_ratio * 0.4 + success_rate * 0.6)
            
            # Site Coverage Assessment (90% of important content)
            site_coverage = self._assess_site_coverage(crawl_data, summary)
            
            # URL Quality Assessment (penalize junk URLs)
            url_quality_ratio = stats.get("url_quality_ratio", 0.5)
            
            # Create metrics object
            metrics = QualityMetrics(
                content_completeness=content_completeness,
                asset_coverage=asset_coverage,
                navigation_integrity=navigation_integrity,
                visual_fidelity=visual_fidelity,
                site_coverage=site_coverage,
                url_quality_ratio=url_quality_ratio,
                total_filtered_urls=stats.get("total_filtered", 0),
                filtering_breakdown=stats.get("filtered_urls", {})
            )
            
            metrics.calculate_overall()
            
            self.logger.info(f"Quality Assessment - Overall: {metrics.overall_score:.3f}")
            self.logger.info(f"   Content: {content_completeness:.3f}, Assets: {asset_coverage:.3f}")
            self.logger.info(f"   Navigation: {navigation_integrity:.3f}, Visual: {visual_fidelity:.3f}")
            self.logger.info(f"   Site Coverage: {site_coverage:.3f} (90% target)")
            self.logger.info(f"   URL Quality: {url_quality_ratio:.3f} (filtered {metrics.total_filtered_urls} junk URLs)")
            
            # Log filtering breakdown if significant
            if metrics.total_filtered_urls > 10:
                self.logger.info("   Top filtered categories:")
                sorted_filters = sorted(metrics.filtering_breakdown.items(), key=lambda x: x[1], reverse=True)
                for category, count in sorted_filters[:3]:
                    if count > 0:
                        self.logger.info(f"     {category}: {count} URLs")
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Quality assessment failed: {e}")
            return QualityMetrics()
        
        
    async def store_learning(self, url: str, recon: ReconResults, strategy: CrawlStrategy, 
                           metrics: QualityMetrics, crawl_data: Dict[str, Any]):
        """Store successful patterns for future learning"""
        # TODO: Implement learning storage
        pass


if __name__ == "__main__":
    # Example usage
    agent = SmartMirrorAgent()
    
    # Test with a URL
    async def test():
        success, metrics, output_path = await agent.process_url("https://www.nab.com.au")
        print(f"Success: {success}")
        print(f"Quality Score: {metrics.overall_score}")
        print(f"Output Path: {output_path}")
        
    # asyncio.run(test())