"""
Adaptive Crawling System

Multi-strategy crawler that adapts based on real-time quality monitoring.
Supports different crawling strategies with dynamic parameter adjustment.

Strategies:
- BASIC_HTTP: Simple HTTP requests for static content
- JAVASCRIPT_RENDER: JavaScript execution with crawl4ai
- FULL_BROWSER: Full browser automation with Playwright/Selenium
- HYBRID: Combination approach based on page analysis
"""

import asyncio
import aiohttp
from typing import Dict, List, Any, Optional, Tuple, Callable
from pathlib import Path
import json
import time
import logging
from urllib.parse import urljoin, urlparse, urlunparse
from bs4 import BeautifulSoup
import hashlib
import re

# Import crawl4ai components
from crawl4ai import AsyncWebCrawler
from crawl4ai.extraction_strategy import LLMExtractionStrategy

from smart_mirror_agent import CrawlStrategy, SiteType, QualityMetrics
from quality_monitor import QualityMonitor, CrawlData


class AdaptiveCrawler:
    """
    Adaptive crawler with real-time quality monitoring and strategy adjustment
    """
    
    def __init__(self, output_dir: str = "./crawl_output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.quality_monitor = QualityMonitor()
        self.logger = logging.getLogger(__name__)
        
        # Strategy-specific configurations
        self.strategy_configs = {
            CrawlStrategy.BASIC_HTTP: {
                'timeout': 10,
                'max_concurrent': 10,
                'delay': 0.5,
                'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
            CrawlStrategy.JAVASCRIPT_RENDER: {
                'timeout': 30,
                'max_concurrent': 5,
                'delay': 1.0,
                'wait_for': 'networkidle',
                'javascript': True
            },
            CrawlStrategy.FULL_BROWSER: {
                'timeout': 45,
                'max_concurrent': 3,
                'delay': 2.0,
                'headless': True,
                'wait_for': 'networkidle',
                'screenshot': True
            },
            CrawlStrategy.HYBRID: {
                'timeout': 20,
                'max_concurrent': 7,
                'delay': 1.0,
                'adaptive': True
            }
        }
        
        # Quality thresholds for strategy adaptation
        self.quality_thresholds = {
            'excellent': 0.9,
            'good': 0.8,
            'acceptable': 0.7,
            'poor': 0.6
        }
        
        # Crawl session data
        self.session_data = {
            'pages': [],
            'assets': {'css': [], 'js': [], 'images': [], 'fonts': [], 'other': []},
            'failed_urls': [],
            'quality_history': []
        }
    
    async def crawl_with_strategy(self, base_url: str, strategy: CrawlStrategy, 
                                max_pages: int = 50) -> Tuple[bool, CrawlData]:
        """
        Execute crawling with specified strategy and real-time monitoring
        """
        self.logger.info(f"Starting crawl of {base_url} with strategy: {strategy}")
        
        # Initialize session
        self._reset_session()
        config = self.strategy_configs[strategy]
        
        # Start crawling based on strategy
        if strategy == CrawlStrategy.BASIC_HTTP:
            success = await self._crawl_basic_http(base_url, config, max_pages)
        elif strategy == CrawlStrategy.JAVASCRIPT_RENDER:
            success = await self._crawl_javascript_render(base_url, config, max_pages)
        elif strategy == CrawlStrategy.FULL_BROWSER:
            success = await self._crawl_full_browser(base_url, config, max_pages)
        elif strategy == CrawlStrategy.HYBRID:
            success = await self._crawl_hybrid(base_url, config, max_pages)
        else:
            success = False
        
        # Create crawl data for quality assessment
        crawl_data = CrawlData(
            pages=self.session_data['pages'],
            assets=self.session_data['assets'],
            base_url=base_url,
            total_pages=len(self.session_data['pages']),
            failed_pages=len(self.session_data['failed_urls']),
            output_dir=str(self.output_dir)
        )
        
        return success, crawl_data
    
    async def _crawl_basic_http(self, base_url: str, config: Dict, max_pages: int) -> bool:
        """Basic HTTP crawling strategy for static content"""
        try:
            connector = aiohttp.TCPConnector(limit=config['max_concurrent'])
            timeout = aiohttp.ClientTimeout(total=config['timeout'])
            
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                urls_to_crawl = [base_url]
                crawled_urls = set()
                
                while urls_to_crawl and len(self.session_data['pages']) < max_pages:
                    current_url = urls_to_crawl.pop(0)
                    
                    if current_url in crawled_urls:
                        continue
                        
                    crawled_urls.add(current_url)
                    
                    # Fetch page
                    page_data = await self._fetch_page_basic(session, current_url)
                    
                    if page_data:
                        self.session_data['pages'].append(page_data)
                        
                        # Extract links for further crawling
                        new_links = self._extract_internal_links(
                            page_data['content'], base_url, current_url
                        )
                        urls_to_crawl.extend(new_links)
                        
                        # Extract assets
                        self._extract_assets(page_data['content'], current_url)
                        
                        # Monitor quality every 10 pages
                        if len(self.session_data['pages']) % 10 == 0:
                            await self._monitor_quality_checkpoint(base_url)
                    
                    # Delay between requests
                    await asyncio.sleep(config['delay'])
                
                return True
                
        except Exception as e:
            self.logger.error(f"Basic HTTP crawl failed: {e}")
            return False
    
    async def _crawl_javascript_render(self, base_url: str, config: Dict, max_pages: int) -> bool:
        """JavaScript rendering strategy using crawl4ai"""
        try:
            async with AsyncWebCrawler(verbose=True, headless=True) as crawler:
                urls_to_crawl = [base_url]
                crawled_urls = set()
                
                while urls_to_crawl and len(self.session_data['pages']) < max_pages:
                    current_url = urls_to_crawl.pop(0)
                    
                    if current_url in crawled_urls:
                        continue
                        
                    crawled_urls.add(current_url)
                    
                    # Crawl with JavaScript rendering
                    # Banking sites need longer wait times for complex JS loading
                    delay = 2.0
                    if any(bank in current_url.lower() for bank in ['commbank', 'nab.com.au', 'westpac', 'anz']):
                        delay = 8.0  # Much longer wait for banking sites
                    
                    result = await crawler.arun(
                        url=current_url,
                        wait_for=config.get('wait_for', 'networkidle'),
                        delay_before_return_html=delay,
                        screenshot=True,
                        bypass_cache=True
                    )
                    
                    if result.success:
                        page_data = {
                            'url': current_url,
                            'content': result.html,
                            'markdown': result.markdown,
                            'metadata': result.metadata,
                            'links': result.links,
                            'screenshot': result.screenshot,
                            'crawl_time': time.time()
                        }
                        
                        self.session_data['pages'].append(page_data)
                        
                        # Extract new links
                        new_links = self._extract_internal_links(
                            result.html, base_url, current_url
                        )
                        urls_to_crawl.extend(new_links)
                        
                        # Extract assets
                        self._extract_assets(result.html, current_url)
                        
                        # Quality monitoring
                        if len(self.session_data['pages']) % 10 == 0:
                            await self._monitor_quality_checkpoint(base_url)
                    else:
                        self.session_data['failed_urls'].append(current_url)
                    
                    # Delay between requests  
                    await asyncio.sleep(config['delay'])
                
                return True
                
        except Exception as e:
            self.logger.error(f"JavaScript render crawl failed: {e}")
            return False
    
    async def _crawl_full_browser(self, base_url: str, config: Dict, max_pages: int) -> bool:
        """Full browser automation strategy"""
        try:
            from playwright.async_api import async_playwright
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=config['headless'])
                context = await browser.new_context(
                    user_agent=config.get('user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                )
                
                page = await context.new_page()
                
                urls_to_crawl = [base_url]
                crawled_urls = set()
                
                while urls_to_crawl and len(self.session_data['pages']) < max_pages:
                    current_url = urls_to_crawl.pop(0)
                    
                    if current_url in crawled_urls:
                        continue
                        
                    crawled_urls.add(current_url)
                    
                    try:
                        # Navigate to page
                        await page.goto(current_url, wait_until='networkidle', timeout=config['timeout'] * 1000)
                        
                        # Get page content
                        content = await page.content()
                        
                        # Take screenshot if configured
                        screenshot = None
                        if config.get('screenshot'):
                            screenshot = await page.screenshot(full_page=True)
                        
                        page_data = {
                            'url': current_url,
                            'content': content,
                            'title': await page.title(),
                            'screenshot': screenshot,
                            'crawl_time': time.time()
                        }
                        
                        self.session_data['pages'].append(page_data)
                        
                        # Extract links
                        new_links = self._extract_internal_links(content, base_url, current_url)
                        urls_to_crawl.extend(new_links)
                        
                        # Extract assets
                        self._extract_assets(content, current_url)
                        
                        # Quality monitoring
                        if len(self.session_data['pages']) % 10 == 0:
                            await self._monitor_quality_checkpoint(base_url)
                            
                    except Exception as e:
                        self.logger.warning(f"Failed to crawl {current_url}: {e}")
                        self.session_data['failed_urls'].append(current_url)
                    
                    await asyncio.sleep(config['delay'])
                
                await browser.close()
                return True
                
        except Exception as e:
            self.logger.error(f"Full browser crawl failed: {e}")
            return False
    
    async def _crawl_hybrid(self, base_url: str, config: Dict, max_pages: int) -> bool:
        """Hybrid strategy that adapts per page"""
        # Start with JavaScript rendering as default
        return await self._crawl_javascript_render(base_url, config, max_pages)
    
    async def _fetch_page_basic(self, session: aiohttp.ClientSession, url: str) -> Optional[Dict]:
        """Fetch a single page with basic HTTP"""
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    return {
                        'url': url,
                        'content': content,
                        'status': response.status,
                        'headers': dict(response.headers),
                        'crawl_time': time.time()
                    }
                else:
                    self.session_data['failed_urls'].append(url)
                    return None
                    
        except Exception as e:
            self.logger.warning(f"Failed to fetch {url}: {e}")
            self.session_data['failed_urls'].append(url)
            return None
    
    def _extract_internal_links(self, html: str, base_url: str, current_url: str) -> List[str]:
        """Extract internal links from HTML content"""
        if not html:
            return []
            
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        base_domain = urlparse(base_url).netloc
        
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            
            if not href:
                continue
                
            # Convert relative URLs to absolute
            absolute_url = urljoin(current_url, href)
            parsed_url = urlparse(absolute_url)
            
            # Only include internal links
            if parsed_url.netloc == base_domain or parsed_url.netloc == '':
                # Clean the URL
                clean_url = urlunparse((
                    parsed_url.scheme,
                    parsed_url.netloc,
                    parsed_url.path,
                    '', '', ''  # Remove query, fragment
                ))
                
                if clean_url not in links:
                    links.append(clean_url)
        
        return links[:20]  # Limit to prevent explosion
    
    def _extract_assets(self, html: str, current_url: str):
        """Extract and categorize assets from HTML"""
        if not html:
            return
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # CSS files
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href')
            if href:
                asset_url = urljoin(current_url, href)
                if asset_url not in self.session_data['assets']['css']:
                    self.session_data['assets']['css'].append(asset_url)
        
        # JavaScript files
        for script in soup.find_all('script', src=True):
            src = script.get('src')
            if src:
                asset_url = urljoin(current_url, src)
                if asset_url not in self.session_data['assets']['js']:
                    self.session_data['assets']['js'].append(asset_url)
        
        # Images
        for img in soup.find_all('img', src=True):
            src = img.get('src')
            if src:
                asset_url = urljoin(current_url, src)
                if asset_url not in self.session_data['assets']['images']:
                    self.session_data['assets']['images'].append(asset_url)
        
        # Fonts (from CSS @font-face rules would need CSS parsing)
        # For now, detect common font URLs
        for link in soup.find_all('link'):
            href = link.get('href', '')
            if any(font_ext in href for font_ext in ['.woff', '.woff2', '.ttf', '.otf']):
                if href not in self.session_data['assets']['fonts']:
                    self.session_data['assets']['fonts'].append(urljoin(current_url, href))
    
    async def _monitor_quality_checkpoint(self, base_url: str):
        """Monitor quality at regular intervals during crawling"""
        crawl_data = CrawlData(
            pages=self.session_data['pages'],
            assets=self.session_data['assets'],
            base_url=base_url,
            total_pages=len(self.session_data['pages']),
            failed_pages=len(self.session_data['failed_urls']),
            output_dir=str(self.output_dir)
        )
        
        metrics = await self.quality_monitor.assess_crawl_quality(crawl_data)
        self.session_data['quality_history'].append({
            'timestamp': time.time(),
            'pages_crawled': len(self.session_data['pages']),
            'quality_score': metrics.overall_score,
            'metrics': metrics
        })
        
        self.logger.info(f"Quality checkpoint - Pages: {len(self.session_data['pages'])}, "
                        f"Quality: {metrics.overall_score:.2f}")
        
        # TODO: Implement strategy adaptation based on quality trends
        
    def _reset_session(self):
        """Reset session data for new crawl"""
        self.session_data = {
            'pages': [],
            'assets': {'css': [], 'js': [], 'images': [], 'fonts': [], 'other': []},
            'failed_urls': [],
            'quality_history': []
        }
    
    def get_crawl_statistics(self) -> Dict[str, Any]:
        """Get comprehensive crawl statistics"""
        total_pages = len(self.session_data['pages'])
        failed_pages = len(self.session_data['failed_urls'])
        success_rate = total_pages / (total_pages + failed_pages) if (total_pages + failed_pages) > 0 else 0
        
        total_assets = sum(len(urls) for urls in self.session_data['assets'].values())
        
        return {
            'pages_crawled': total_pages,
            'failed_pages': failed_pages,
            'success_rate': success_rate,
            'total_assets': total_assets,
            'assets_by_type': {k: len(v) for k, v in self.session_data['assets'].items()},
            'quality_history': self.session_data['quality_history']
        }


# Example usage
async def test_adaptive_crawler():
    crawler = AdaptiveCrawler()
    
    success, crawl_data = await crawler.crawl_with_strategy(
        "https://www.example.com", 
        CrawlStrategy.JAVASCRIPT_RENDER,
        max_pages=10
    )
    
    stats = crawler.get_crawl_statistics()
    print(f"Crawl Success: {success}")
    print(f"Pages Crawled: {stats['pages_crawled']}")
    print(f"Success Rate: {stats['success_rate']:.2f}")


if __name__ == "__main__":
    asyncio.run(test_adaptive_crawler())