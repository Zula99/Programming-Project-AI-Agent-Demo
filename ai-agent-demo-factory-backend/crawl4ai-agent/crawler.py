# crawler.py - Main crawl orchestration and configuration
import os
import time
import logging
import urllib.parse
import urllib.robotparser as robotparser
from collections import deque
from pathlib import Path
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass

from crawl4ai import AsyncWebCrawler

from url_utils import url_canon, is_same_site, looks_binary, is_demo_worthy_url_sync
from page_crawler import crawl_page, CrawlResult
from file_utils import save_crawl_result
from quality_monitoring import _get_site_specific_thresholds

# Quality Plateau Detection
try:
    from quality_plateau import HybridQualityMonitor, QualityMetrics as PlateauQualityMetrics
    PLATEAU_AVAILABLE = True
except ImportError as e:
    PLATEAU_AVAILABLE = False
    logging.warning(f"Quality plateau detection not available: {e}")

# Content Deduplication System
try:
    from content_deduplicator import ContentDeduplicator
    DEDUPLICATION_AVAILABLE = True
except ImportError as e:
    DEDUPLICATION_AVAILABLE = False
    logging.warning(f"Content deduplication not available: {e}")

# Coverage tracking integration
try:
    from websocket_manager import notify_page_crawled, notify_urls_discovered
    from dashboard_metrics import get_coverage_calculator
    COVERAGE_TRACKING_AVAILABLE = True
except ImportError as e:
    COVERAGE_TRACKING_AVAILABLE = False
    logging.warning(f"Coverage tracking not available: {e}")

# AI Classification
try:
    from ai_content_classifier import AIContentClassifier
    from ai_config import get_ai_config
    AI_AVAILABLE = True
except ImportError as e:
    AI_AVAILABLE = False
    logging.warning(f"AI classification not available: {e}")

_logger = logging.getLogger(__name__)

@dataclass
class CrawlConfig:
    """Configuration for web crawling"""
    domain: str
    output_root: Path
    max_pages: int = 100
    request_gap: float = 0.6
    user_agent: str = "Mozilla/5.0 (compatible; Crawl4AI-Agent/1.0)"
    respect_robots: bool = True
    start_url: Optional[str] = None
    # Browser configuration for JS-heavy sites
    timeout: int = 30
    wait_for: str = 'networkidle'  # 'networkidle', 'domcontentloaded', 'load'
    additional_wait: float = 0.0  # Extra wait after wait_for condition (for heavy JS)
    headless: bool = True
    screenshot: bool = False
    # Cost tracking
    cost_tracker: Optional[Any] = None  # CostTracker instance for AI cost monitoring
    javascript: bool = True
    max_concurrent: int = 5
    # Content deduplication settings
    enable_deduplication: bool = True
    dedup_similarity_threshold: float = 0.85  # 85% similarity threshold
    dedup_min_content_length: int = 100  # Minimum content length to analyze
    # Anti-detection features
    stealth_mode: bool = False
    realistic_viewport: bool = True
    # Coverage tracking integration
    run_id: Optional[str] = None  # Run ID for real-time coverage monitoring
    classification_cache: Optional[Dict] = None  # Session-scoped classification cache
    extra_headers: dict = None
    # Enhanced JS rendering features
    wait_for_selector: Optional[str] = None  # CSS selector to wait for
    selector_timeout: int = 10000  # Timeout for selector wait (ms)
    auto_scroll: bool = False  # Auto-scroll to trigger lazy loading
    scroll_delay: int = 1000  # Delay between scroll actions (ms)
    post_load_delay: int = 0  # Extra delay after all loading (ms)
    js_code: Optional[List[str]] = None  # JavaScript code to execute
    # Progress callback for real-time updates
    progress_callback: Optional[callable] = None  # Callback for live progress updates

def setup_robots_parser(start_url: str) -> robotparser.RobotFileParser:
    """Setup and load robots.txt parser"""
    rp = robotparser.RobotFileParser()
    rp.set_url(urllib.parse.urljoin(start_url, "/robots.txt"))
    try:
        rp.read()
    except Exception:
        pass  # if robots fails to load, we proceed
    return rp

async def generic_crawl(config: CrawlConfig) -> Tuple[List[CrawlResult], Dict[str, Any]]:
    """
    Generic web crawler that can be configured for any domain with smart URL filtering

    Returns:
        results: List of crawl results
        stats: Dictionary with crawling statistics including filtering metrics
    """
    config.output_root.mkdir(parents=True, exist_ok=True)

    start_url = config.start_url or f"https://www.{config.domain}/"

    # Setup robots.txt if respecting it
    rp = None
    if config.respect_robots:
        rp = setup_robots_parser(start_url)

    q = deque([url_canon(start_url)])
    seen: Set[str] = set()
    results: List[CrawlResult] = []
    pages_crawled = 0

    # Track filtering stats
    filtered_urls = {
        "path_too_long": 0,
        "complex_query": 0,
        "non_content_path": 0,
        "tracking_params": 0,
        "useless_file_type": 0,
        "too_deep_nesting": 0,
        "too_many_special_chars": 0,
        "robots_blocked": 0,
        "binary_files": 0,
        "external_domains": 0
    }

    # Track AI classification stats
    ai_classifications_made = 0
    # Start with pre-populated cache count (sitemap classifications)
    initial_cache_size = len(config.classification_cache) if hasattr(config, 'classification_cache') and config.classification_cache else 0
    cache_hits = initial_cache_size  # Initialize with pre-loaded classifications

    # Initialize total_urls_discovered with sitemap count for accurate progress tracking
    total_urls_discovered = initial_cache_size
    cache_size_before = initial_cache_size

    # Configure crawler with browser settings for JS-heavy sites
    crawler_config = {
        'user_agent': config.user_agent,
        'headless': config.headless,
        'timeout': config.timeout
    }

    # Add JS-specific settings if needed
    if config.javascript:
        crawler_config['wait_for'] = config.wait_for

    # Add stealth mode settings
    if config.stealth_mode:
        # Check for playwright-stealth availability
        try:
            import playwright_stealth
            _logger.info("Playwright-stealth available - enabling anti-detection")
            crawler_config.update({
                'viewport_width': 1920 if config.realistic_viewport else None,
                'viewport_height': 1080 if config.realistic_viewport else None,
                'stealth_mode': True  # Custom flag for our stealth implementation
            })
        except ImportError as e:
            _logger.warning(f"Playwright-stealth not available ({e}) - using basic anti-detection")
            crawler_config.update({
                'viewport_width': 1920 if config.realistic_viewport else None,
                'viewport_height': 1080 if config.realistic_viewport else None,
            })

    # Add extra headers for anti-detection
    if config.extra_headers:
        crawler_config['extra_headers'] = config.extra_headers

    # Initialize content deduplication system
    deduplicator = None
    if DEDUPLICATION_AVAILABLE and config.enable_deduplication:
        try:
            deduplicator = ContentDeduplicator(
                min_content_length=config.dedup_min_content_length
            )
            _logger.info(f"Content deduplication enabled (exact duplicates only)")
        except Exception as e:
            _logger.warning(f"Could not initialize content deduplicator: {e}")
            deduplicator = None

    # Initialize quality plateau monitoring if available
    plateau_monitor = None
    if PLATEAU_AVAILABLE and AI_AVAILABLE:
        try:
            # Create AI classifier and site detector
            ai_config = get_ai_config()
            ai_classifier = AIContentClassifier(
                api_key=getattr(ai_config, 'openai_api_key', None),
                model=getattr(ai_config, 'model', 'gpt-4o-mini')
            )

            # Use existing BusinessSiteDetector for site type detection
            site_detector = ai_classifier.site_detector
            site_type = site_detector.detect_site_type(start_url, "", "")

            # Get site-specific quality thresholds
            thresholds = _get_site_specific_thresholds(site_type)

            plateau_monitor = HybridQualityMonitor(
                quality_window_size=thresholds['quality_window_size'],
                worthy_threshold=thresholds['worthy_threshold'],
                diversity_threshold=thresholds['diversity_threshold'],
                diversity_window_size=thresholds['diversity_window_size']
            )

            _logger.info(f"Quality plateau detection enabled for {site_type.value} site")
            _logger.info(f"Thresholds: worthy={thresholds['worthy_threshold']:.1%}, diversity={thresholds['diversity_threshold']:.1%}")

        except Exception as e:
            _logger.warning(f"Could not initialize quality plateau detection: {e}")
            plateau_monitor = None

    # Track crawl start time for speed calculation
    crawl_start_time = time.time()

    # Track progress metrics for live updates
    crawl_speed = 0.0

    # Send initial progress update (0/max_pages)
    if config.progress_callback:
        try:
            await config.progress_callback(
                pages_crawled=0,
                total_known=config.max_pages,
                discovered_urls=0,
                crawl_speed=0,
                ai_classifications=0,
                cache_hits=0,
                current_url=start_url
            )
        except Exception as e:
            _logger.debug(f"Initial progress callback error: {e}")

    async with AsyncWebCrawler(**crawler_config) as crawler:
        while q and pages_crawled < config.max_pages:
            # Check stop flag at start of every iteration
            if config.run_id:
                try:
                    from task_manager import task_manager
                    if task_manager.should_stop(config.run_id):
                        _logger.info(f"FORCE STOP detected - terminating crawl for run_id: {config.run_id}")
                        break
                except Exception:
                    pass  # If task_manager not available, continue

            url = q.popleft()
            if url in seen:
                continue
            seen.add(url)

            # Check domain
            if not is_same_site(url, config.domain):
                filtered_urls["external_domains"] += 1
                continue

            # Check binary files
            if looks_binary(url):
                filtered_urls["binary_files"] += 1
                continue

            # Smart URL filtering (enhanced with AI heuristics)
            is_worthy, filter_reason = is_demo_worthy_url_sync(url)
            if not is_worthy:
                filtered_urls[filter_reason] += 1
                _logger.info(f"  Skipped {url} ({filter_reason})")
                continue

            # Check robots.txt if enabled
            if rp and config.respect_robots:
                try:
                    if not rp.can_fetch(config.user_agent, url):
                        filtered_urls["robots_blocked"] += 1
                        continue
                except Exception:
                    pass

            # Crawl the page (pass cost tracker and classification cache if available)
            cost_tracker = getattr(config, 'cost_tracker', None)
            classification_cache = getattr(config, 'classification_cache', None)

            # Track cache state before crawl_page
            cache_size_before_crawl = len(classification_cache) if classification_cache else 0

            result = await crawl_page(crawler, url, config, cost_tracker, classification_cache)

            # Track if this was a cache hit or new AI classification
            if classification_cache:
                cache_size_after_crawl = len(classification_cache)
                if cache_size_after_crawl > cache_size_before_crawl:
                    # New classification was added
                    ai_classifications_made += 1
                elif hasattr(result, 'ai_classification') and result.ai_classification:
                    # Result has AI classification but cache didn't grow = cache hit
                    cache_hits += 1

            # Check for content duplication before processing
            is_duplicate = False
            duplicate_reason = ""
            if result.success and deduplicator:
                try:
                    is_duplicate, duplicate_reason = deduplicator.is_duplicate(
                        url=result.url,
                        content=result.markdown,
                        title=result.title
                    )

                    if is_duplicate:
                        _logger.info(f"  Skipped duplicate content: {url} ({duplicate_reason})")
                        # Still add to results for statistics but mark as filtered
                        result.error = f"duplicate_content: {duplicate_reason}"
                        result.success = False
                except Exception as e:
                    _logger.warning(f"Deduplication check failed for {url}: {e}")
                    # Continue processing if deduplication fails
            results.append(result)

            # Coverage tracking: Notify page crawled
            if COVERAGE_TRACKING_AVAILABLE and config.run_id:
                try:
                    # Get quality score if available (from AI classification)
                    quality_score = None
                    if hasattr(result, 'ai_classification') and result.ai_classification:
                        quality_score = result.ai_classification.get('confidence', None)

                    await notify_page_crawled(config.run_id, url, result.success and not is_duplicate, quality_score)
                except Exception as e:
                    _logger.debug(f"Coverage tracking notification failed: {e}")

            if result.success and not is_duplicate:
                pages_crawled += 1

                # Save result
                saved_path = save_crawl_result(result, config)
                if saved_path:
                    _logger.info(f"[{pages_crawled}/{config.max_pages}] {url} -> {saved_path.name}")
                else:
                    _logger.warning(f"[{pages_crawled}/{config.max_pages}] {url} -> [save failed]")

                # Send real-time progress update
                if config.progress_callback:
                    try:
                        # Calculate crawl speed (pages per minute)
                        elapsed_time = time.time() - crawl_start_time
                        crawl_speed = (pages_crawled / (elapsed_time / 60)) if elapsed_time > 0 else 0

                        total_cached = len(config.classification_cache) if config.classification_cache else 0
                        _logger.info(f"PROGRESS CALLBACK: Sending update {pages_crawled}/{config.max_pages}")
                        await config.progress_callback(
                            pages_crawled=pages_crawled,
                            total_known=total_urls_discovered,
                            discovered_urls=len(q),
                            crawl_speed=crawl_speed,
                            ai_classifications=ai_classifications_made,
                            cache_hits=cache_hits,
                            current_url=url
                        )
                    except Exception as e:
                        _logger.error(f"Progress callback error: {e}")

                # Queue new links with filtering
                all_links = list(result.links)
                total_urls_discovered += len(all_links)

                # Filter and queue links
                worthy_links = []
                for link_url in all_links:
                    if link_url in seen:
                        continue

                    if not is_same_site(link_url, config.domain):
                        continue

                    if looks_binary(link_url):
                        continue

                    is_worthy, _ = is_demo_worthy_url_sync(link_url)
                    if is_worthy:
                        worthy_links.append(link_url)

                # Add to queue
                new_queued = 0
                new_urls = []
                for u in worthy_links:
                    if u not in q:
                        q.append(u)
                        new_urls.append(u)
                        new_queued += 1

                _logger.info(f"  found {len(all_links)} links, queued {new_queued} worthy ones (queue: {len(q)})")

                # Coverage tracking: Notify new URLs discovered
                if COVERAGE_TRACKING_AVAILABLE and config.run_id and new_urls:
                    try:
                        await notify_urls_discovered(config.run_id, new_urls)
                    except Exception as e:
                        _logger.debug(f"Coverage tracking URL discovery notification failed: {e}")

                # Quality plateau monitoring and intelligent stopping
                if plateau_monitor:
                    try:
                        # Create quality metrics from AI classification
                        if result.ai_classification:
                            is_worthy = result.ai_classification.get('worthy', True)
                            confidence = result.ai_classification.get('confidence', 0.7)
                            reasoning = result.ai_classification.get('reasoning', 'AI classified as worthy')
                        else:
                            # Fallback: assume successful crawl is worthy
                            is_worthy = True
                            confidence = 0.6
                            reasoning = 'Successful crawl without AI classification'

                        # Generate content hash for diversity monitoring
                        import hashlib
                        content_hash = hashlib.md5(result.markdown.encode()).hexdigest()

                        # Create plateau quality metrics
                        plateau_quality = PlateauQualityMetrics(
                            is_worthy=is_worthy,
                            confidence_score=confidence,
                            reasoning=reasoning,
                            url=url
                        )

                        # Update plateau monitor
                        plateau_monitor.assess_page(plateau_quality, content_hash)

                        # Check if we should stop crawling
                        should_stop, stop_reason = plateau_monitor.should_stop_crawling()

                        if should_stop:
                            _logger.info(f"Quality plateau detected: {stop_reason}")
                            _logger.info(f"Intelligent stopping: {stop_reason}")
                            _logger.info(f"   Crawled {pages_crawled} pages with sufficient quality coverage")
                            break  # Exit the crawling loop
                        else:
                            # Log quality status every 10 pages
                            if pages_crawled % 10 == 0:
                                stats = plateau_monitor.get_comprehensive_stats()
                                _logger.info(f"Quality check at page {pages_crawled}: {stats['recent_worthy_ratio']:.1%} recent quality")

                    except Exception as e:
                        _logger.warning(f"Quality plateau monitoring failed for {url}: {e}")
                        # Continue crawling even if plateau monitoring fails

            else:
                _logger.error(f"  Error on {url}: {result.error}")

    # Calculate filtering statistics
    total_filtered = sum(filtered_urls.values())
    quality_ratio = pages_crawled / (pages_crawled + total_filtered) if (pages_crawled + total_filtered) > 0 else 0

    # Include deduplication statistics if available
    deduplication_stats = {}
    if deduplicator:
        try:
            deduplication_stats = deduplicator.get_deduplication_summary()
            _logger.info(f"Content deduplication summary: {deduplication_stats['duplicate_rate']} duplicates filtered")

            # Get available breakdown stats
            breakdown = deduplication_stats.get('breakdown', {})
            exact_dups = breakdown.get('exact_duplicates', 0)
            redirect_stubs = breakdown.get('redirect_stubs', 0)

            if exact_dups > 0 or redirect_stubs > 0:
                _logger.info(f"  Breakdown: {exact_dups} exact duplicates, {redirect_stubs} redirect stubs")
        except Exception as e:
            _logger.warning(f"Could not get deduplication statistics: {e}")

    # Include quality plateau statistics if available
    plateau_stats = {}  # Initialize to empty dict to avoid undefined variable
    if plateau_monitor:
        try:
            plateau_stats = plateau_monitor.get_comprehensive_stats()
            _logger.info(f"Quality plateau summary: {plateau_stats['recent_worthy_ratio']:.1%} recent quality, {plateau_stats['overall_worthy_ratio']:.1%} overall")
        except Exception as e:
            _logger.warning(f"Could not get plateau statistics: {e}")
            plateau_stats = {}  # Reset to empty on error

    stats = {
        "pages_crawled": pages_crawled,
        "total_urls_seen": len(seen),
        "total_urls_discovered": total_urls_discovered,
        "successful_crawls": len([r for r in results if r.success]),
        "failed_crawls": len([r for r in results if not r.success]),
        "queue_remaining": len(q),
        "filtered_urls": filtered_urls,
        "total_filtered": total_filtered,
        "url_quality_ratio": quality_ratio,
        "filtering_efficiency": total_filtered / total_urls_discovered if total_urls_discovered > 0 else 0,
        "quality_plateau_stats": plateau_stats,  # Include plateau monitoring results
        "deduplication_stats": deduplication_stats,  # Include content deduplication results
        "ai_classifications_made": ai_classifications_made,  # New AI classifications during crawl
        "cache_hits": cache_hits,  # Cache hits during crawl
        "total_cached": len(config.classification_cache) if hasattr(config, 'classification_cache') and config.classification_cache else 0  # Total cache size
    }

    # Save discovered link classifications to persistent cache for future crawls
    if AI_AVAILABLE and hasattr(config, 'classification_cache') and config.classification_cache:
        try:
            from ai_content_classifier import populate_url_cache_from_session
            populate_url_cache_from_session(config.classification_cache)
            _logger.info(f"Saved {len(config.classification_cache)} link classifications to persistent cache")
        except Exception as e:
            _logger.warning(f"Failed to save link classifications to persistent cache: {e}")

    _logger.info(f"Done. Crawled {pages_crawled} quality page(s), filtered {total_filtered} junk URLs")
    _logger.info(f"URL Quality Ratio: {quality_ratio:.1%} (higher is better)")
    _logger.info(f"Output in: {config.output_root.resolve()}")

    return results, stats
