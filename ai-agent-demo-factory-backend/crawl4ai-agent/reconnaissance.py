"""
Site Reconnaissance Module

Quick analysis of websites to determine optimal crawling strategy.
Target: <10s reconnaissance time for strategy selection.
"""

import asyncio
import aiohttp
import time
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import re
from dataclasses import dataclass

from smart_mirror_agent import SiteType, CrawlStrategy, ReconResults


@dataclass
class FrameworkSignature:
    """Framework detection signature"""
    name: str
    indicators: List[str]
    weight: float


class SiteRecon:
    """Site reconnaissance and analysis"""
    
    # Framework detection signatures
    FRAMEWORK_SIGNATURES = [
        FrameworkSignature("React", ["react", "_react", "React", "ReactDOM"], 0.9),
        FrameworkSignature("Angular", ["ng-", "angular", "@angular", "Angular"], 0.9),
        FrameworkSignature("Vue", ["vue", "Vue", "__vue__", "v-"], 0.9),
        FrameworkSignature("jQuery", ["jquery", "jQuery", "$"], 0.7),
        FrameworkSignature("WordPress", ["wp-content", "wordpress", "wp-includes"], 0.8),
        FrameworkSignature("Bootstrap", ["bootstrap", "Bootstrap"], 0.5),
        FrameworkSignature("Tailwind", ["tailwind", "tw-"], 0.5),
        FrameworkSignature("Next.js", ["next", "_next", "__next"], 0.9),
        FrameworkSignature("Nuxt", ["nuxt", "_nuxt", "__nuxt"], 0.9),
    ]
    
    # Site type patterns
    SITE_TYPE_PATTERNS = {
        SiteType.BANKING: ["bank", "banking", "financial", "loan", "mortgage"],
        SiteType.ECOMMERCE: ["shop", "store", "cart", "checkout", "product", "buy"],
        SiteType.NEWS: ["news", "article", "blog", "post", "story"],
        SiteType.WORDPRESS: ["wp-content", "wp-admin", "wp-includes"],
    }
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        
    async def analyze_site(self, url: str) -> ReconResults:
        """
        Perform comprehensive site analysis
        
        Returns ReconResults with recommended strategy
        """
        start_time = time.time()
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout)) as session:
            # Step 1: Basic HTTP request and response analysis
            html_content, response_info = await self._fetch_initial_page(session, url)
            
            if not html_content:
                return ReconResults(
                    site_type=SiteType.UNKNOWN,
                    frameworks=[],
                    js_complexity=0.0,
                    page_load_time=0.0,
                    asset_count=0,
                    recommended_strategy=CrawlStrategy.BASIC_HTTP
                )
            
            # Step 2: Parse HTML and detect frameworks
            soup = BeautifulSoup(html_content, 'html.parser')
            frameworks = self._detect_frameworks(html_content, soup)
            
            # Step 3: Analyze JavaScript complexity
            js_complexity = self._analyze_js_complexity(soup)
            
            # Step 4: Count assets
            asset_count = self._count_assets(soup)
            
            # Step 5: Determine site type
            site_type = self._classify_site_type(url, html_content, soup)
            
            # Step 6: Calculate page load time
            page_load_time = time.time() - start_time
            
            # Step 7: Recommend strategy
            strategy = self._recommend_strategy(frameworks, js_complexity, site_type)
            
            return ReconResults(
                site_type=site_type,
                frameworks=frameworks,
                js_complexity=js_complexity,
                page_load_time=page_load_time,
                asset_count=asset_count,
                recommended_strategy=strategy
            )
    
    async def _fetch_initial_page(self, session: aiohttp.ClientSession, url: str) -> Tuple[str, Dict]:
        """Fetch initial page and gather response info"""
        try:
            async with session.get(url) as response:
                content = await response.text()
                response_info = {
                    'status': response.status,
                    'headers': dict(response.headers),
                    'content_type': response.content_type,
                    'charset': response.charset
                }
                return content, response_info
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
            return "", {}
    
    def _detect_frameworks(self, html_content: str, soup: BeautifulSoup) -> List[str]:
        """Detect JavaScript frameworks and libraries"""
        detected = []
        
        # Check script tags
        scripts = soup.find_all('script')
        script_content = " ".join([script.get_text() for script in scripts if script.get_text()])
        script_srcs = [script.get('src', '') for script in scripts if script.get('src')]
        
        # Check for framework signatures
        for signature in self.FRAMEWORK_SIGNATURES:
            confidence = 0.0
            
            # Check in HTML content
            for indicator in signature.indicators:
                if indicator in html_content:
                    confidence += 0.3
                if indicator in script_content:
                    confidence += 0.4
                if any(indicator in src for src in script_srcs):
                    confidence += 0.5
            
            if confidence >= signature.weight:
                detected.append(signature.name)
                
        return detected
    
    def _analyze_js_complexity(self, soup: BeautifulSoup) -> float:
        """Analyze JavaScript complexity level (0.0 - 1.0)"""
        scripts = soup.find_all('script')
        
        # Count inline scripts
        inline_scripts = sum(1 for script in scripts if script.get_text().strip())
        
        # Count external scripts  
        external_scripts = sum(1 for script in scripts if script.get('src'))
        
        # Check for SPA indicators
        spa_indicators = [
            'data-reactroot', 'ng-app', 'v-app', 'id="app"', 'id="root"'
        ]
        html_str = str(soup)
        spa_score = sum(1 for indicator in spa_indicators if indicator in html_str)
        
        # Calculate complexity score
        complexity = min(1.0, (inline_scripts * 0.1 + external_scripts * 0.05 + spa_score * 0.3))
        
        return complexity
    
    def _count_assets(self, soup: BeautifulSoup) -> int:
        """Count total assets (CSS, JS, images, etc.)"""
        css_links = len(soup.find_all('link', rel='stylesheet'))
        js_scripts = len(soup.find_all('script', src=True))
        images = len(soup.find_all('img', src=True))
        
        return css_links + js_scripts + images
    
    def _classify_site_type(self, url: str, html_content: str, soup: BeautifulSoup) -> SiteType:
        """Classify the type of website"""
        url_lower = url.lower()
        content_lower = html_content.lower()
        
        # Check URL and content for site type indicators
        for site_type, patterns in self.SITE_TYPE_PATTERNS.items():
            for pattern in patterns:
                if pattern in url_lower or pattern in content_lower:
                    return site_type
        
        # Check for SPA frameworks
        title = soup.find('title')
        title_text = title.get_text().lower() if title else ""
        
        if any(framework in ["React", "Angular", "Vue", "Next.js", "Nuxt"] 
               for framework in self._detect_frameworks(html_content, soup)):
            if "shop" in content_lower or "store" in content_lower:
                return SiteType.ECOMMERCE
            else:
                return SiteType.SPA_REACT  # Default SPA type
        
        # Check for WordPress
        if "wp-content" in html_content or "wordpress" in html_content:
            return SiteType.WORDPRESS
            
        return SiteType.STATIC_HTML
    
    def _recommend_strategy(self, frameworks: List[str], js_complexity: float, site_type: SiteType) -> CrawlStrategy:
        """Recommend optimal crawling strategy based on analysis"""
        
        # High JS complexity or SPA frameworks require browser rendering
        if js_complexity > 0.7 or any(fw in ["React", "Angular", "Vue", "Next.js", "Nuxt"] for fw in frameworks):
            return CrawlStrategy.FULL_BROWSER
        
        # Medium JS complexity may benefit from JS rendering
        if js_complexity > 0.4 or site_type in [SiteType.ECOMMERCE, SiteType.BANKING]:
            return CrawlStrategy.JAVASCRIPT_RENDER
        
        # Banking sites often require careful handling
        if site_type == SiteType.BANKING:
            return CrawlStrategy.HYBRID
        
        # Simple sites can use basic HTTP
        if site_type in [SiteType.STATIC_HTML, SiteType.WORDPRESS] and js_complexity < 0.3:
            return CrawlStrategy.BASIC_HTTP
        
        # Default fallback
        return CrawlStrategy.JAVASCRIPT_RENDER


# Example usage
async def test_recon():
    recon = SiteRecon()
    result = await recon.analyze_site("https://www.nab.com.au")
    
    print(f"Site Type: {result.site_type}")
    print(f"Frameworks: {result.frameworks}")
    print(f"JS Complexity: {result.js_complexity}")
    print(f"Page Load Time: {result.page_load_time:.2f}s")
    print(f"Asset Count: {result.asset_count}")
    print(f"Recommended Strategy: {result.recommended_strategy}")


if __name__ == "__main__":
    asyncio.run(test_recon())