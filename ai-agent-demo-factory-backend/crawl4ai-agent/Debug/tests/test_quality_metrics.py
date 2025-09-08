"""
Test for the updated proxy-optimized quality metrics system
"""

import asyncio
from dataclasses import dataclass
from typing import Dict, List, Any
from urllib.parse import urlparse, urljoin

# Mock QualityMetrics class since we can't import the real one
@dataclass
class QualityMetrics:
    content_completeness: float = 0.0
    asset_coverage: float = 0.0
    navigation_integrity: float = 0.0
    visual_fidelity: float = 0.0
    overall_score: float = 0.0
    
    # New proxy-specific metrics
    ai_classification_score: float = 0.0
    site_coverage_score: float = 0.0
    processing_score: float = 0.0
    
    def calculate_overall(self):
        """Calculate overall score from component scores"""
        self.overall_score = (
            self.content_completeness * 0.35 +
            self.asset_coverage * 0.25 +
            self.navigation_integrity * 0.20 +
            self.visual_fidelity * 0.20
        )

@dataclass
class CrawlData:
    """Structure for crawled data analysis"""
    pages: List[Dict[str, Any]]
    assets: Dict[str, List[str]]
    base_url: str
    total_pages: int
    failed_pages: int
    output_dir: str


class MockQualityMonitor:
    """Simplified version of QualityMonitor for testing"""
    
    def __init__(self):
        self.content_threshold = 100
        self.link_depth_threshold = 3
    
    async def assess_crawl_quality(self, crawl_data: CrawlData, ai_stats: Dict = None) -> QualityMetrics:
        """Proxy-optimized quality assessment"""
        
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
        """Assess content discovery success"""
        if not crawl_data.pages:
            return 0.0
            
        meaningful_pages = 0
        total_content_length = 0
        
        for page in crawl_data.pages:
            content = page.get('content', '')
            # Simple text extraction (without BeautifulSoup)
            text_content = self._extract_text_simple(content)
            total_content_length += len(text_content)
            
            if len(text_content) > self.content_threshold:
                meaningful_pages += 1
        
        page_success_rate = meaningful_pages / len(crawl_data.pages)
        avg_content_length = total_content_length / len(crawl_data.pages)
        
        content_score = (
            page_success_rate * 0.6 +
            min(1.0, avg_content_length / 1000) * 0.4
        )
        
        return min(1.0, content_score)
    
    def _assess_ai_classification(self, ai_stats: Dict) -> float:
        """Assess AI classification performance"""
        if not ai_stats:
            return 1.0
            
        total_classified = ai_stats.get('total_classified', 0)
        accepted = ai_stats.get('accepted', 0)
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
        """Assess realistic site coverage"""
        if not crawl_data.pages:
            return 0.0
        
        # Simple estimation: assume 50 total pages for demo purposes
        estimated_total_pages = 50
        actual_coverage = len(crawl_data.pages) / estimated_total_pages
        
        return min(1.0, actual_coverage)
    
    def _assess_processing_efficiency(self, crawl_data: CrawlData) -> float:
        """Assess processing efficiency"""
        if not crawl_data.pages:
            return 0.0
        
        # Success rate
        total_attempted = crawl_data.total_pages + crawl_data.failed_pages
        success_rate = crawl_data.total_pages / total_attempted if total_attempted > 0 else 1.0
        
        # Content quality
        meaningful_pages = 0
        for page in crawl_data.pages:
            content = page.get('content', '')
            if len(self._extract_text_simple(content)) > self.content_threshold:
                meaningful_pages += 1
        
        content_quality = meaningful_pages / len(crawl_data.pages)
        
        return (success_rate * 0.6 + content_quality * 0.4)
    
    def _extract_text_simple(self, html: str) -> str:
        """Simple text extraction without BeautifulSoup"""
        if not html:
            return ""
        # Very basic HTML tag removal
        import re
        text = re.sub(r'<[^>]+>', '', html)
        return text.strip()
    
    def get_quality_recommendation(self, metrics: QualityMetrics) -> str:
        """Get proxy-optimized recommendation"""
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


async def test_single_page_crawl():
    """Test quality metrics for single page (like your 1-page example)"""
    print("=== Testing Single Page Crawl ===")
    
    monitor = MockQualityMonitor()
    
    # Single page crawl data
    test_data = CrawlData(
        pages=[
            {
                'url': 'https://www.commbank.com.au/',
                'content': '<html><body><h1>CommBank Home</h1><p>Welcome to Commonwealth Bank. This is a substantial amount of content about banking services, loans, accounts, and financial products. Our bank offers personal banking, business banking, institutional banking, and wealth management services.</p></body></html>',
                'markdown': '# CommBank Home\nWelcome to Commonwealth Bank...'
            }
        ],
        assets={},  # Not relevant for proxy
        base_url='https://www.commbank.com.au',
        total_pages=1,
        failed_pages=0,
        output_dir='./test_output'
    )
    
    # Mock AI stats
    ai_stats = {
        'total_classified': 1,
        'accepted': 1,
        'rejected': 0,
        'avg_confidence': 0.9
    }
    
    metrics = await monitor.assess_crawl_quality(test_data, ai_stats)
    
    print(f"PROXY-OPTIMIZED QUALITY METRICS:")
    print(f"   Content Discovery:     {metrics.content_completeness:.1%}")
    print(f"   Asset Coverage:        {metrics.asset_coverage:.1%} (Always 100% with proxy)")
    print(f"   Navigation Integrity:  {metrics.navigation_integrity:.1%} (Always 100% with proxy)")
    print(f"   Visual Fidelity:       {metrics.visual_fidelity:.1%} (Always 100% with proxy)")
    print(f"   Overall Score:         {metrics.overall_score:.1%}")
    print(f"")
    print(f"AI & COVERAGE METRICS:")
    print(f"   Site Coverage:         {metrics.site_coverage_score:.1%} (1/50 = realistic 2%)")
    print(f"   AI Classification:     {metrics.ai_classification_score:.1%} (100% accepted)")
    print(f"   Processing Efficiency: {metrics.processing_score:.1%}")
    print(f"")
    print(f"Recommendation: {monitor.get_quality_recommendation(metrics)}")
    print()


async def test_multi_page_crawl():
    """Test quality metrics for multi-page crawl"""
    print("=== Testing Multi-Page Crawl ===")
    
    monitor = MockQualityMonitor()
    
    # Multi-page crawl data
    test_data = CrawlData(
        pages=[
            {
                'url': 'https://www.example.com/',
                'content': '<html><body><h1>Home</h1><p>Welcome to our website with lots of content about our services.</p></body></html>',
                'markdown': '# Home\nWelcome...'
            },
            {
                'url': 'https://www.example.com/about',
                'content': '<html><body><h1>About Us</h1><p>We are a company that provides excellent services to customers worldwide.</p></body></html>',
                'markdown': '# About Us\nWe are...'
            },
            {
                'url': 'https://www.example.com/services',
                'content': '<html><body><h1>Services</h1><p>Our comprehensive range of services includes consulting, development, and support.</p></body></html>',
                'markdown': '# Services\nOur comprehensive...'
            },
            {
                'url': 'https://www.example.com/contact',
                'content': '<html><body><h1>Contact</h1><p>Get in touch with us for any inquiries about our services.</p></body></html>',
                'markdown': '# Contact\nGet in touch...'
            }
        ],
        assets={},
        base_url='https://www.example.com',
        total_pages=4,
        failed_pages=1,  # Simulate one failed page
        output_dir='./test_output'
    )
    
    # Mock AI stats with mixed results
    ai_stats = {
        'total_classified': 4,
        'accepted': 3,
        'rejected': 1,
        'avg_confidence': 0.75
    }
    
    metrics = await monitor.assess_crawl_quality(test_data, ai_stats)
    
    print(f"PROXY-OPTIMIZED QUALITY METRICS:")
    print(f"   Content Discovery:     {metrics.content_completeness:.1%}")
    print(f"   Asset Coverage:        {metrics.asset_coverage:.1%} (Always 100% with proxy)")
    print(f"   Navigation Integrity:  {metrics.navigation_integrity:.1%} (Always 100% with proxy)")
    print(f"   Visual Fidelity:       {metrics.visual_fidelity:.1%} (Always 100% with proxy)")
    print(f"   Overall Score:         {metrics.overall_score:.1%}")
    print(f"")
    print(f"AI & COVERAGE METRICS:")
    print(f"   Site Coverage:         {metrics.site_coverage_score:.1%} (4/{50} = realistic 8%)")
    print(f"   AI Classification:     {metrics.ai_classification_score:.1%} (75% accepted)")
    print(f"   Processing Efficiency: {metrics.processing_score:.1%} (80% success rate)")
    print(f"")
    print(f"Recommendation: {monitor.get_quality_recommendation(metrics)}")
    print()


async def test_poor_quality_crawl():
    """Test quality metrics for poor quality crawl"""
    print("=== Testing Poor Quality Crawl ===")
    
    monitor = MockQualityMonitor()
    
    # Poor quality crawl data
    test_data = CrawlData(
        pages=[
            {
                'url': 'https://www.badsite.com/404',
                'content': '<html><body>404 Not Found</body></html>',
                'markdown': '404 Not Found'
            }
        ],
        assets={},
        base_url='https://www.badsite.com',
        total_pages=1,
        failed_pages=5,  # Many failed pages
        output_dir='./test_output'
    )
    
    # Poor AI stats
    ai_stats = {
        'total_classified': 1,
        'accepted': 0,
        'rejected': 1,
        'avg_confidence': 0.3
    }
    
    metrics = await monitor.assess_crawl_quality(test_data, ai_stats)
    
    print(f"PROXY-OPTIMIZED QUALITY METRICS:")
    print(f"   Content Discovery:     {metrics.content_completeness:.1%}")
    print(f"   Asset Coverage:        {metrics.asset_coverage:.1%} (Always 100% with proxy)")
    print(f"   Navigation Integrity:  {metrics.navigation_integrity:.1%} (Always 100% with proxy)")
    print(f"   Visual Fidelity:       {metrics.visual_fidelity:.1%} (Always 100% with proxy)")
    print(f"   Overall Score:         {metrics.overall_score:.1%}")
    print(f"")
    print(f"AI & COVERAGE METRICS:")
    print(f"   Site Coverage:         {metrics.site_coverage_score:.1%}")
    print(f"   AI Classification:     {metrics.ai_classification_score:.1%} (0% accepted)")
    print(f"   Processing Efficiency: {metrics.processing_score:.1%} (poor success rate)")
    print(f"")
    print(f"Recommendation: {monitor.get_quality_recommendation(metrics)}")
    print()


async def main():
    """Run all quality metrics tests"""
    print("PROXY-OPTIMIZED QUALITY METRICS TESTS")
    print("======================================")
    print()
    
    await test_single_page_crawl()
    await test_multi_page_crawl()
    await test_poor_quality_crawl()
    
    print("All tests completed!")
    print()
    print("KEY IMPROVEMENTS:")
    print("   - Visual Fidelity: Always 100% (proxy serves original assets)")
    print("   - Asset Coverage: Not applicable (proxy fetches on-demand)")
    print("   - Site Coverage: Realistic % based on estimated total pages")
    print("   - AI Classification: Shows acceptance ratio and confidence")
    print("   - Processing Efficiency: Success rate and content quality")


if __name__ == "__main__":
    asyncio.run(main())