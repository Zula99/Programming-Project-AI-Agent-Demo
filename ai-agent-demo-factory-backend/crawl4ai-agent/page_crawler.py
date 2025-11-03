# page_crawler.py - Single page crawling logic
import time
import asyncio
import logging
from typing import Set, Optional, Dict, Any
from dataclasses import dataclass

from crawl4ai import AsyncWebCrawler
from link_extraction import extract_links
from ai_classification import is_demo_worthy_url_ai

_logger = logging.getLogger(__name__)

@dataclass
class CrawlResult:
    """Result of crawling a single page"""
    url: str
    success: bool
    raw_html: str = ""
    markdown: str = ""
    title: str = ""
    content_type: str = ""
    links: Set[str] = None
    error: Optional[str] = None
    ai_classification: Optional[Dict[str, Any]] = None
    html_type: str = "raw"  # "raw" or "rendered"

    def __post_init__(self):
        if self.links is None:
            self.links = set()

async def crawl_page(crawler: AsyncWebCrawler, url: str, config, cost_tracker=None, classification_cache=None) -> CrawlResult:
    """Crawl a single page and return structured results"""
    try:
        if config.request_gap > 0:
            time.sleep(config.request_gap)

        # Configure page-level settings for JS-heavy sites
        arun_kwargs = {
            'timeout': config.timeout * 1000,  # Convert to milliseconds
            'wait_for': config.wait_for,
            'screenshot': config.screenshot,
            'extract_format': 'html'  # Force rendered HTML instead of markdown
        }

        # Add wait for specific selector if configured
        if config.wait_for_selector:
            arun_kwargs['wait_for_selector'] = config.wait_for_selector
            arun_kwargs['selector_timeout'] = config.selector_timeout

        # Add post-load delay for JS completion
        if config.post_load_delay > 0:
            arun_kwargs['post_load_delay'] = config.post_load_delay

        # Build JS code list for execution
        js_code_list = []

        # Add stealth mode if enabled
        if config.stealth_mode:
            stealth_js = """
            // Basic anti-detection measures
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-AU', 'en']});
            window.chrome = {runtime: {}};
            """
            js_code_list.append(stealth_js)

        # Add auto-scroll if enabled (triggers lazy loading)
        if config.auto_scroll:
            scroll_js = """
            // Auto-scroll to trigger lazy loading
            console.log('Starting auto-scroll for lazy loading...');

            // Scroll to bottom
            window.scrollTo(0, document.body.scrollHeight);
            await new Promise(r => setTimeout(r, {scroll_delay}));

            // Scroll to middle
            window.scrollTo(0, document.body.scrollHeight / 2);
            await new Promise(r => setTimeout(r, {scroll_delay}));

            // Scroll back to top
            window.scrollTo(0, 0);
            await new Promise(r => setTimeout(r, {scroll_delay}));

            console.log('Auto-scroll complete');
            """.format(scroll_delay=config.scroll_delay)
            js_code_list.append(scroll_js)

        # Add custom JS code if provided
        if config.js_code:
            js_code_list.extend(config.js_code)

        # Set js_code if we have any
        if js_code_list:
            arun_kwargs['js_code'] = js_code_list

        # Filter out None values and invalid parameters
        arun_kwargs = {k: v for k, v in arun_kwargs.items() if v is not None}

        result = await crawler.arun(url, **arun_kwargs)

        # Additional wait for heavy JS apps (after networkidle)
        if config.additional_wait > 0:
            _logger.info(f"Additional wait: {config.additional_wait}s for JS completion")
            await asyncio.sleep(config.additional_wait)

        # Extract content - prioritize rendered HTML over raw HTML for JS-heavy sites
        rendered_html = getattr(result, "html", None) or getattr(result, "cleaned_html", None)
        raw_html = getattr(result, "raw_html", None)

        # For JS-heavy sites, use rendered HTML if available, otherwise fall back to raw_html
        final_html = rendered_html if rendered_html else raw_html or ""

        content_md = getattr(result, "markdown", None) or getattr(result, "clean_text", "") or ""
        title = getattr(result, "title", "") or ""
        content_type = getattr(result, "content_type", "") or ""

        # Log which HTML we're using for debugging
        if rendered_html and rendered_html != raw_html:
            _logger.info(f" Using rendered HTML (post-JS) for {url}")
        else:
            _logger.info(f"  Using raw HTML (pre-JS) for {url}")

        # AI Content Classification - analyze actual page content
        ai_worthy = True  # default to worthy
        ai_reasoning = ""
        ai_confidence = 0.7

        try:
            # Extract domain for domain-specific caching
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            if domain.startswith('www.'):
                domain = domain[4:]

            # Use AI to classify the actual page content
            is_worthy, reason, details = await is_demo_worthy_url_ai(url, content_md, title, cost_tracker, classification_cache, domain)
            ai_worthy = is_worthy
            ai_reasoning = details.get('reasoning', reason)
            ai_confidence = details.get('confidence', 0.7)

            # Log AI decisions for monitoring
            _logger.info(f"AI Classification: {url} -> {'WORTHY' if ai_worthy else 'FILTERED'} ({ai_confidence:.2f}) - {ai_reasoning[:100]}")

            # If AI says not worthy, skip this page entirely
            if not ai_worthy:
                return CrawlResult(
                    url=url,
                    success=False,
                    error=f"AI classified as not demo-worthy: {ai_reasoning}",
                    ai_classification={'worthy': False, 'reasoning': ai_reasoning, 'confidence': ai_confidence}
                )

        except Exception as e:
            _logger.warning(f"AI classification failed for {url}: {e}, proceeding with content")
            # Continue with page if AI fails

        # Extract links from the final HTML (rendered if available)
        links = extract_links(final_html, url)

        return CrawlResult(
            url=url,
            success=True,
            raw_html=final_html,  # Use rendered HTML instead of raw
            markdown=content_md,
            title=title,
            content_type=content_type,
            links=links,
            ai_classification={'worthy': ai_worthy, 'reasoning': ai_reasoning, 'confidence': ai_confidence},
            html_type="rendered" if rendered_html and rendered_html != raw_html else "raw"
        )

    except Exception as e:
        return CrawlResult(
            url=url,
            success=False,
            error=str(e)
        )
