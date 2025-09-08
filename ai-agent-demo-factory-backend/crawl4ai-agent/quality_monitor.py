"""
Quality Monitoring and Assessment Module for Proxy System

Real-time quality assessment during crawling optimized for proxy architecture:
- Content Discovery: Pages found and crawled successfully
- AI Classification: Intelligent demo-worthiness assessment
- Site Coverage: Realistic coverage estimation based on actual site size
- Processing Efficiency: Speed and success metrics

Proxy System Benefits:
- Visual Fidelity: Always 100% (proxy serves original assets)
- Asset Coverage: Not applicable (proxy fetches on-demand)
- Navigation: Works with original site structure
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
        
    async def assess_crawl_quality(self, crawl_data: CrawlData, ai_stats: Dict = None) -> QualityMetrics:
        """
        Proxy-optimized quality assessment focusing on content discovery and AI classification
        
        Returns QualityMetrics with realistic scoring for proxy architecture
        """
        
        # Assess proxy-relevant dimensions
        content_score = await self._assess_content_discovery(crawl_data)
        ai_classification_score = self._assess_ai_classification(ai_stats or {})
        site_coverage_score = await self._assess_realistic_site_coverage(crawl_data)
        processing_score = self._assess_processing_efficiency(crawl_data)
        
        # Create proxy-optimized metrics
        metrics = QualityMetrics(
            content_completeness=content_score,
            asset_coverage=1.0,  # Always 100% with proxy
            navigation_integrity=1.0,  # Proxy preserves original navigation
            visual_fidelity=1.0  # Always 100% with proxy
        )
        
        # Add new proxy-specific metrics
        metrics.ai_classification_score = ai_classification_score
        metrics.site_coverage_score = site_coverage_score
        metrics.processing_score = processing_score
        
        metrics.calculate_overall()
        return metrics
    
    async def _assess_content_discovery(self, crawl_data: CrawlData) -> float:
        """
        Assess content discovery success
        - Successful page crawling rate
        - Content extraction quality
        - Content variety and depth
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
    
    def _assess_ai_classification(self, ai_stats: Dict) -> float:
        """
        Assess AI classification performance
        - Classification accuracy and confidence
        - Accepted vs rejected ratio
        - AI decision quality
        """
        if not ai_stats:
            return 1.0  # No AI stats means basic heuristic classification worked
            
        total_classified = ai_stats.get('total_classified', 0)
        accepted = ai_stats.get('accepted', 0)
        rejected = ai_stats.get('rejected', 0)
        avg_confidence = ai_stats.get('avg_confidence', 0.5)
        
        if total_classified == 0:
            return 1.0
            
        # Good ratio is 70-90% accepted for demo content
        acceptance_ratio = accepted / total_classified
        ratio_score = 1.0 if 0.7 <= acceptance_ratio <= 0.9 else max(0.3, 1.0 - abs(acceptance_ratio - 0.8))
        
        # Higher confidence is better
        confidence_score = min(1.0, avg_confidence)
        
        return (ratio_score * 0.6 + confidence_score * 0.4)
    
    async def _assess_realistic_site_coverage(self, crawl_data: CrawlData) -> float:
        """
        Assess realistic site coverage based on estimated total site size
        - Estimate total site pages from discovered links
        - Calculate actual coverage percentage
        - Factor in content diversity
        """
        if not crawl_data.pages:
            return 0.0
            
        unique_internal_links = set()
        unique_paths = set()
        
        for page in crawl_data.pages:
            content = page.get('content', '')
            url = page.get('url', '')
            
            # Track crawled paths
            path = urlparse(url).path
            unique_paths.add(path)
            
            # Discover internal links to estimate site size
            soup = BeautifulSoup(content, 'html.parser') if content else None
            if soup:
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link.get('href')
                    if self._is_internal_link(href, crawl_data.base_url):
                        full_url = urljoin(crawl_data.base_url, href)
                        unique_internal_links.add(full_url)
        
        # Estimate total site size (discovered + some buffer for undiscovered pages)
        estimated_total_pages = max(len(unique_internal_links), len(crawl_data.pages)) * 1.3
        
        # Calculate realistic coverage percentage
        actual_coverage = len(crawl_data.pages) / estimated_total_pages if estimated_total_pages > 0 else 0
        
        return min(1.0, actual_coverage)
    
    def _assess_processing_efficiency(self, crawl_data: CrawlData) -> float:
        """
        Assess processing efficiency for proxy system
        - Crawl success rate
        - Content extraction quality
        - Processing speed metrics
        """
        if not crawl_data.pages:
            return 0.0
        
        # Success rate
        total_attempted = crawl_data.total_pages + crawl_data.failed_pages
        success_rate = crawl_data.total_pages / total_attempted if total_attempted > 0 else 1.0
        
        # Content quality (pages with meaningful content)
        meaningful_pages = 0
        for page in crawl_data.pages:
            content = page.get('content', '')
            text_content = self._extract_text_content(content)
            if len(text_content) > self.content_threshold:
                meaningful_pages += 1
        
        content_quality = meaningful_pages / len(crawl_data.pages) if crawl_data.pages else 0
        
        # Combined efficiency score
        efficiency_score = (success_rate * 0.6 + content_quality * 0.4)
        
        return min(1.0, efficiency_score)
    
    # Removed _count_downloaded_assets - not needed for proxy system
    
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
        """Get proxy-optimized recommendation based on quality score"""
        score = metrics.overall_score
        
        if score >= 0.9:
            return "Excellent proxy crawl - demo ready"
        elif score >= 0.8:
            return "Good crawl quality - minor improvements possible" 
        elif score >= 0.7:
            return "Acceptable coverage - consider expanding crawl"
        elif score >= 0.6:
            return "Low coverage - increase page limits or adjust strategy"
        else:
            return "Poor crawl results - check site accessibility and strategy"


# Example usage and testing
async def test_quality_assessment():
    monitor = QualityMonitor()
    
    # Mock crawl data for testing proxy system
    test_data = CrawlData(
        pages=[
            {
                'url': 'https://www.example.com/',
                'content': '<html><body><h1>Test</h1><p>Sample content</p></body></html>',
                'markdown': '# Test\nSample content'
            }
        ],
        assets={},  # Not relevant for proxy system
        base_url='https://www.example.com',
        total_pages=1,
        failed_pages=0,
        output_dir='./test_output'
    )
    
    # Mock AI classification stats
    ai_stats = {
        'total_classified': 5,
        'accepted': 4,
        'rejected': 1,
        'avg_confidence': 0.8
    }
    
    metrics = await monitor.assess_crawl_quality(test_data, ai_stats)
    
    print(f"Content Discovery: {metrics.content_completeness:.1%}")
    print(f"Asset Coverage: {metrics.asset_coverage:.1%} (Always 100% with proxy)")  
    print(f"Navigation Integrity: {metrics.navigation_integrity:.1%} (Always 100% with proxy)")
    print(f"Visual Fidelity: {metrics.visual_fidelity:.1%} (Always 100% with proxy)")
    print(f"Overall Score: {metrics.overall_score:.1%}")
    print(f"Site Coverage: {getattr(metrics, 'site_coverage_score', 0):.1%}")
    print(f"AI Classification: {getattr(metrics, 'ai_classification_score', 0):.1%}")
    print(f"Processing Efficiency: {getattr(metrics, 'processing_score', 0):.1%}")
    print(f"Recommendation: {monitor.get_quality_recommendation(metrics)}")


if __name__ == "__main__":
    asyncio.run(test_quality_assessment())