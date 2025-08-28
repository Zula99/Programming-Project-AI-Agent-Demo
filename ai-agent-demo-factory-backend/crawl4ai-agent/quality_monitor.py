"""
Quality Monitoring and Assessment Module

Real-time quality assessment during crawling with multi-dimensional scoring:
- Content Completeness (35%): Text volume, content depth  
- Asset Coverage (25%): CSS, JS, images successfully downloaded
- Navigation Integrity (20%): Internal links, site structure
- Visual Fidelity (20%): Layout preservation, styling accuracy

Score Ranges:
- 0.9-1.0: Excellent - continue strategy
- 0.8-0.89: Good - minor tweaks  
- 0.7-0.79: Acceptable - monitor
- 0.6-0.69: Poor - fallback strategy
- <0.6: Failed - major strategy change
"""

import os
import re
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import json
import asyncio
import aiofiles
from dataclasses import dataclass

from smart_mirror_agent import QualityMetrics


@dataclass
class CrawlData:
    """Structure for crawled data analysis"""
    pages: List[Dict[str, Any]]
    assets: Dict[str, List[str]]  # asset_type -> list of urls
    base_url: str
    total_pages: int
    failed_pages: int
    output_dir: str


class QualityMonitor:
    """Real-time quality monitoring and assessment"""
    
    def __init__(self):
        self.content_threshold = 100  # Minimum characters for meaningful content
        self.link_depth_threshold = 3  # Minimum link depth for good navigation
        
    async def assess_crawl_quality(self, crawl_data: CrawlData) -> QualityMetrics:
        """
        Comprehensive quality assessment across all dimensions
        
        Returns QualityMetrics with detailed scoring
        """
        
        # Assess each dimension
        content_score = await self._assess_content_completeness(crawl_data)
        asset_score = await self._assess_asset_coverage(crawl_data)  
        navigation_score = await self._assess_navigation_integrity(crawl_data)
        visual_score = await self._assess_visual_fidelity(crawl_data)
        
        # Create and return metrics
        metrics = QualityMetrics(
            content_completeness=content_score,
            asset_coverage=asset_score,
            navigation_integrity=navigation_score,
            visual_fidelity=visual_score
        )
        
        metrics.calculate_overall()
        return metrics
    
    async def _assess_content_completeness(self, crawl_data: CrawlData) -> float:
        """
        Assess content completeness (35% weight)
        - Text volume across pages
        - Content depth and variety
        - Successful page extraction rate
        """
        if not crawl_data.pages:
            return 0.0
            
        total_content_length = 0
        meaningful_pages = 0
        total_links = 0
        unique_content_types = set()
        
        for page in crawl_data.pages:
            content = page.get('content', '')
            markdown = page.get('markdown', '')
            
            # Count text content
            text_content = self._extract_text_content(content)
            total_content_length += len(text_content)
            
            # Check if page has meaningful content
            if len(text_content) > self.content_threshold:
                meaningful_pages += 1
                
            # Count internal links
            soup = BeautifulSoup(content, 'html.parser') if content else None
            if soup:
                links = soup.find_all('a', href=True)
                internal_links = [link for link in links 
                                if self._is_internal_link(link.get('href'), crawl_data.base_url)]
                total_links += len(internal_links)
                
            # Identify content types
            if soup:
                if soup.find_all(['h1', 'h2', 'h3']):
                    unique_content_types.add('headings')
                if soup.find_all(['p']):
                    unique_content_types.add('paragraphs')  
                if soup.find_all(['img']):
                    unique_content_types.add('images')
                if soup.find_all(['form']):
                    unique_content_types.add('forms')
                if soup.find_all(['table']):
                    unique_content_types.add('tables')
        
        # Calculate content completeness score
        page_success_rate = meaningful_pages / len(crawl_data.pages) if crawl_data.pages else 0
        avg_content_length = total_content_length / len(crawl_data.pages) if crawl_data.pages else 0
        content_diversity = len(unique_content_types) / 5  # Max 5 content types
        
        # Weighted scoring
        content_score = (
            page_success_rate * 0.4 +  # 40% for successful page extraction
            min(1.0, avg_content_length / 1000) * 0.4 +  # 40% for content volume
            content_diversity * 0.2  # 20% for content variety
        )
        
        return min(1.0, content_score)
    
    async def _assess_asset_coverage(self, crawl_data: CrawlData) -> float:
        """
        Assess asset coverage (25% weight)  
        - CSS files successfully downloaded
        - JavaScript files downloaded
        - Images and media assets
        - Font files
        """
        if not crawl_data.assets:
            return 0.0
            
        total_assets = 0
        downloaded_assets = 0
        
        # Count assets by type
        asset_weights = {
            'css': 0.3,
            'js': 0.3, 
            'images': 0.25,
            'fonts': 0.1,
            'other': 0.05
        }
        
        weighted_score = 0.0
        
        for asset_type, urls in crawl_data.assets.items():
            if asset_type in asset_weights:
                total_type_assets = len(urls)
                
                # Check which assets were actually downloaded
                downloaded_type_assets = await self._count_downloaded_assets(
                    urls, crawl_data.output_dir
                )
                
                if total_type_assets > 0:
                    type_coverage = downloaded_type_assets / total_type_assets
                    weighted_score += type_coverage * asset_weights[asset_type]
                    
                total_assets += total_type_assets
                downloaded_assets += downloaded_type_assets
        
        # Overall coverage rate
        overall_coverage = downloaded_assets / total_assets if total_assets > 0 else 0
        
        # Combine weighted score with overall coverage
        final_score = (weighted_score * 0.7 + overall_coverage * 0.3)
        
        return min(1.0, final_score)
    
    async def _assess_navigation_integrity(self, crawl_data: CrawlData) -> float:
        """
        Assess navigation integrity (20% weight)
        - Internal link coverage
        - Site structure preservation  
        - Breadth vs depth balance
        """
        if not crawl_data.pages:
            return 0.0
            
        total_internal_links = 0
        working_links = 0
        unique_paths = set()
        max_depth = 0
        
        base_domain = urlparse(crawl_data.base_url).netloc
        
        for page in crawl_data.pages:
            content = page.get('content', '')
            url = page.get('url', '')
            
            # Calculate URL depth
            path = urlparse(url).path
            depth = len([p for p in path.split('/') if p])
            max_depth = max(max_depth, depth)
            unique_paths.add(path)
            
            soup = BeautifulSoup(content, 'html.parser') if content else None
            if soup:
                links = soup.find_all('a', href=True)
                
                for link in links:
                    href = link.get('href')
                    if self._is_internal_link(href, crawl_data.base_url):
                        total_internal_links += 1
                        
                        # Check if linked page was crawled
                        full_url = urljoin(crawl_data.base_url, href)
                        if any(p.get('url') == full_url for p in crawl_data.pages):
                            working_links += 1
        
        # Calculate navigation metrics
        link_coverage = working_links / total_internal_links if total_internal_links > 0 else 0
        path_diversity = min(1.0, len(unique_paths) / 20)  # Normalize to max 20 unique paths
        depth_score = min(1.0, max_depth / self.link_depth_threshold)
        
        # Weighted navigation score
        navigation_score = (
            link_coverage * 0.5 +  # 50% for working internal links
            path_diversity * 0.3 +  # 30% for path diversity  
            depth_score * 0.2  # 20% for navigation depth
        )
        
        return min(1.0, navigation_score)
    
    async def _assess_visual_fidelity(self, crawl_data: CrawlData) -> float:
        """
        Assess visual fidelity (20% weight)
        - CSS preservation and loading
        - Layout structure integrity
        - Asset availability for rendering
        """
        
        css_score = 0.0
        layout_score = 0.0
        asset_availability = 0.0
        
        # Assess CSS coverage
        css_files = crawl_data.assets.get('css', [])
        if css_files:
            downloaded_css = await self._count_downloaded_assets(css_files, crawl_data.output_dir)
            css_score = downloaded_css / len(css_files)
        
        # Assess layout structure preservation
        layout_elements = 0
        preserved_layout = 0
        
        for page in crawl_data.pages:
            content = page.get('content', '')
            soup = BeautifulSoup(content, 'html.parser') if content else None
            
            if soup:
                # Count important layout elements
                layout_tags = soup.find_all(['div', 'section', 'article', 'header', 'footer', 'nav'])
                layout_elements += len(layout_tags)
                
                # Check for preserved styling attributes
                styled_elements = soup.find_all(attrs={'class': True, 'style': True})
                preserved_layout += len(styled_elements)
        
        if layout_elements > 0:
            layout_score = min(1.0, preserved_layout / layout_elements)
        
        # Assess asset availability for visual rendering
        image_files = crawl_data.assets.get('images', [])
        font_files = crawl_data.assets.get('fonts', [])
        
        total_visual_assets = len(image_files) + len(font_files)
        if total_visual_assets > 0:
            downloaded_images = await self._count_downloaded_assets(image_files, crawl_data.output_dir)
            downloaded_fonts = await self._count_downloaded_assets(font_files, crawl_data.output_dir)
            asset_availability = (downloaded_images + downloaded_fonts) / total_visual_assets
        
        # Weighted visual fidelity score
        visual_score = (
            css_score * 0.4 +  # 40% for CSS preservation
            layout_score * 0.4 +  # 40% for layout structure
            asset_availability * 0.2  # 20% for visual assets
        )
        
        return min(1.0, visual_score)
    
    async def _count_downloaded_assets(self, asset_urls: List[str], output_dir: str) -> int:
        """Count how many assets were actually downloaded"""
        count = 0
        output_path = Path(output_dir)
        
        for url in asset_urls:
            # Convert URL to likely file path
            parsed = urlparse(url)
            file_path = output_path / parsed.path.lstrip('/')
            
            if file_path.exists() and file_path.is_file():
                count += 1
                
        return count
    
    def _extract_text_content(self, html: str) -> str:
        """Extract meaningful text content from HTML"""
        if not html:
            return ""
            
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
            
        # Get text content
        text = soup.get_text()
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def _is_internal_link(self, href: str, base_url: str) -> bool:
        """Check if a link is internal to the site"""
        if not href:
            return False
            
        # Handle relative links
        if href.startswith('/') or not href.startswith('http'):
            return True
            
        # Check domain
        base_domain = urlparse(base_url).netloc
        link_domain = urlparse(href).netloc
        
        return link_domain == base_domain or link_domain.endswith(f'.{base_domain}')
    
    def get_quality_recommendation(self, metrics: QualityMetrics) -> str:
        """Get recommendation based on quality score"""
        score = metrics.overall_score
        
        if score >= 0.9:
            return "Excellent - continue current strategy"
        elif score >= 0.8:
            return "Good - minor tweaks may improve quality" 
        elif score >= 0.7:
            return "Acceptable - monitor and consider adjustments"
        elif score >= 0.6:
            return "Poor - implement fallback strategy"
        else:
            return "Failed - major strategy change required"


# Example usage and testing
async def test_quality_assessment():
    monitor = QualityMonitor()
    
    # Mock crawl data for testing
    test_data = CrawlData(
        pages=[
            {
                'url': 'https://www.example.com/',
                'content': '<html><body><h1>Test</h1><p>Sample content</p></body></html>',
                'markdown': '# Test\nSample content'
            }
        ],
        assets={
            'css': ['https://www.example.com/style.css'],
            'js': ['https://www.example.com/script.js'],
            'images': ['https://www.example.com/image.jpg']
        },
        base_url='https://www.example.com',
        total_pages=1,
        failed_pages=0,
        output_dir='./test_output'
    )
    
    metrics = await monitor.assess_crawl_quality(test_data)
    
    print(f"Content Completeness: {metrics.content_completeness:.2f}")
    print(f"Asset Coverage: {metrics.asset_coverage:.2f}")  
    print(f"Navigation Integrity: {metrics.navigation_integrity:.2f}")
    print(f"Visual Fidelity: {metrics.visual_fidelity:.2f}")
    print(f"Overall Score: {metrics.overall_score:.2f}")
    print(f"Recommendation: {monitor.get_quality_recommendation(metrics)}")


if __name__ == "__main__":
    asyncio.run(test_quality_assessment())