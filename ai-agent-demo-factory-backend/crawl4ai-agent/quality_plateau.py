"""
Quality Plateau Detection System for Intelligent Crawling

This module implements quality-based stopping conditions for web crawling,
eliminating the need for arbitrary page limits by detecting when crawling
quality plateaus below acceptable thresholds.
"""

from collections import deque
from typing import Tuple, List, Dict, Any
from dataclasses import dataclass
import time


@dataclass
class QualityMetrics:
    """Container for quality assessment metrics"""
    is_worthy: bool
    confidence_score: float
    reasoning: str
    url: str
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class SimpleQualityBasedCrawling:
    """
    Quality plateau detection system that monitors crawling quality
    and provides intelligent stopping recommendations.
    
    Uses a sliding window approach to track recent page quality and
    detects when the percentage of worthy pages falls below threshold.
    """
    
    def __init__(self, window_size: int = 20, worthy_threshold: float = 0.3):
        """
        Initialize quality monitoring system.
        
        Args:
            window_size: Number of recent pages to monitor (default: 20)
            worthy_threshold: Minimum ratio of worthy pages (default: 0.3 = 30%)
        """
        self.window_size = window_size
        self.worthy_threshold = worthy_threshold
        self.recent_pages = deque(maxlen=window_size)
        self.total_pages_processed = 0
        self.total_worthy_pages = 0
        self.quality_history: List[QualityMetrics] = []
        
    def add_page_assessment(self, quality_metrics: QualityMetrics) -> None:
        """
        Add a new page quality assessment to the monitoring system.
        
        Args:
            quality_metrics: QualityMetrics object containing assessment results
        """
        # Add to sliding window (binary: 1 for worthy, 0 for not worthy)
        self.recent_pages.append(1 if quality_metrics.is_worthy else 0)
        
        # Update overall statistics
        self.total_pages_processed += 1
        if quality_metrics.is_worthy:
            self.total_worthy_pages += 1
            
        # Store detailed history for analysis
        self.quality_history.append(quality_metrics)
        
    def should_stop_crawling(self) -> Tuple[bool, str]:
        """
        Determine if crawling should stop based on quality plateau detection.
        
        Returns:
            Tuple of (should_stop: bool, reason: str)
        """
        if len(self.recent_pages) < self.window_size:
            return False, f"Need {self.window_size - len(self.recent_pages)} more pages for analysis"
            
        # Calculate worthy ratio in recent window
        worthy_ratio = sum(self.recent_pages) / len(self.recent_pages)
        
        if worthy_ratio < self.worthy_threshold:
            return True, f"Quality plateau detected: {worthy_ratio:.1%} worthy in last {self.window_size} pages (threshold: {self.worthy_threshold:.1%})"
            
        return False, f"Quality good: {worthy_ratio:.1%} worthy in recent pages"
        
    def get_quality_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive quality statistics for reporting.
        
        Returns:
            Dictionary containing current quality metrics and statistics
        """
        overall_worthy_ratio = (
            self.total_worthy_pages / self.total_pages_processed 
            if self.total_pages_processed > 0 else 0.0
        )
        
        recent_worthy_ratio = (
            sum(self.recent_pages) / len(self.recent_pages)
            if len(self.recent_pages) > 0 else 0.0
        )
        
        return {
            'total_pages_processed': self.total_pages_processed,
            'total_worthy_pages': self.total_worthy_pages,
            'overall_worthy_ratio': overall_worthy_ratio,
            'recent_worthy_ratio': recent_worthy_ratio,
            'window_size': len(self.recent_pages),
            'window_full': len(self.recent_pages) >= self.window_size,
            'worthy_threshold': self.worthy_threshold,
            'should_stop': self.should_stop_crawling()[0],
            'stop_reason': self.should_stop_crawling()[1]
        }
        
    def get_recent_assessments(self, count: int = 10) -> List[QualityMetrics]:
        """
        Get the most recent quality assessments.
        
        Args:
            count: Number of recent assessments to return
            
        Returns:
            List of recent QualityMetrics objects
        """
        return self.quality_history[-count:] if self.quality_history else []
        
    def reset(self) -> None:
        """Reset all quality monitoring state."""
        self.recent_pages.clear()
        self.total_pages_processed = 0
        self.total_worthy_pages = 0
        self.quality_history.clear()
        
    def export_quality_report(self) -> Dict[str, Any]:
        """
        Export detailed quality report for analysis and debugging.
        
        Returns:
            Comprehensive report of quality assessment history
        """
        stats = self.get_quality_stats()
        
        # Analyze quality trends
        if len(self.quality_history) >= 2:
            recent_10 = self.quality_history[-10:]
            worthy_in_recent_10 = sum(1 for q in recent_10 if q.is_worthy)
            recent_10_ratio = worthy_in_recent_10 / len(recent_10)
            
            # Compare first half vs second half of history for trend analysis
            mid_point = len(self.quality_history) // 2
            if mid_point > 0:
                first_half_worthy = sum(1 for q in self.quality_history[:mid_point] if q.is_worthy)
                second_half_worthy = sum(1 for q in self.quality_history[mid_point:] if q.is_worthy)
                
                first_half_ratio = first_half_worthy / mid_point
                second_half_ratio = second_half_worthy / (len(self.quality_history) - mid_point)
                quality_trend = second_half_ratio - first_half_ratio
            else:
                quality_trend = 0.0
        else:
            recent_10_ratio = 0.0
            quality_trend = 0.0
            
        return {
            **stats,
            'recent_10_worthy_ratio': recent_10_ratio,
            'quality_trend': quality_trend,
            'assessment_history': [
                {
                    'url': q.url,
                    'is_worthy': q.is_worthy,
                    'confidence_score': q.confidence_score,
                    'reasoning': q.reasoning,
                    'timestamp': q.timestamp
                }
                for q in self.quality_history
            ]
        }


class ContentDiversityMonitor:
    """
    Secondary quality system that monitors content diversity
    to detect when crawling becomes repetitive.
    """
    
    def __init__(self, similarity_threshold: float = 0.8, window_size: int = 15):
        """
        Initialize content diversity monitoring.
        
        Args:
            similarity_threshold: Content similarity threshold (0.8 = 80% similar)
            window_size: Number of recent pages to check for similarity
        """
        self.similarity_threshold = similarity_threshold
        self.window_size = window_size
        self.content_hashes: deque = deque(maxlen=window_size)
        self.url_patterns: deque = deque(maxlen=window_size)
        
    def add_content(self, content_hash: str, url: str) -> None:
        """Add content for diversity analysis."""
        self.content_hashes.append(content_hash)
        
        # Extract URL pattern for pattern-based duplicate detection
        url_pattern = self._extract_url_pattern(url)
        self.url_patterns.append(url_pattern)
        
    def is_content_repetitive(self) -> Tuple[bool, str]:
        """
        Check if recent content is becoming too repetitive.
        
        Returns:
            Tuple of (is_repetitive: bool, reason: str)
        """
        if len(self.content_hashes) < self.window_size:
            return False, "Not enough content for diversity analysis"
            
        # Check for hash-based duplicates
        unique_hashes = len(set(self.content_hashes))
        hash_diversity_ratio = unique_hashes / len(self.content_hashes)
        
        # Check for URL pattern repetition
        unique_patterns = len(set(self.url_patterns))
        pattern_diversity_ratio = unique_patterns / len(self.url_patterns)
        
        if hash_diversity_ratio < (1 - self.similarity_threshold):
            return True, f"Content too similar: {hash_diversity_ratio:.1%} unique content in recent pages"
            
        if pattern_diversity_ratio < 0.3:  # Less than 30% unique URL patterns
            return True, f"URL patterns repetitive: {pattern_diversity_ratio:.1%} unique patterns"
            
        return False, f"Content diverse: {hash_diversity_ratio:.1%} unique content, {pattern_diversity_ratio:.1%} unique patterns"
        
    def _extract_url_pattern(self, url: str) -> str:
        """Extract URL pattern by replacing numbers with placeholders."""
        import re
        # Replace numeric IDs with placeholder to detect pattern duplicates
        pattern = re.sub(r'/\d+', '/{id}', url)
        pattern = re.sub(r'[?&]\w*=\d+', '&param={id}', pattern)
        return pattern


class HybridQualityMonitor:
    """
    Combined quality monitoring system that uses both quality plateau
    detection and content diversity monitoring for comprehensive assessment.
    """
    
    def __init__(self, 
                 quality_window_size: int = 20,
                 worthy_threshold: float = 0.3,
                 diversity_threshold: float = 0.8,
                 diversity_window_size: int = 15):
        """
        Initialize hybrid quality monitoring system.
        
        Args:
            quality_window_size: Window size for quality plateau detection
            worthy_threshold: Minimum ratio of worthy pages
            diversity_threshold: Content similarity threshold
            diversity_window_size: Window size for diversity monitoring
        """
        self.quality_monitor = SimpleQualityBasedCrawling(
            window_size=quality_window_size,
            worthy_threshold=worthy_threshold
        )
        
        self.diversity_monitor = ContentDiversityMonitor(
            similarity_threshold=diversity_threshold,
            window_size=diversity_window_size
        )
        
    def assess_page(self, quality_metrics: QualityMetrics, content_hash: str) -> None:
        """Add page assessment to both monitoring systems."""
        self.quality_monitor.add_page_assessment(quality_metrics)
        self.diversity_monitor.add_content(content_hash, quality_metrics.url)
        
    def should_stop_crawling(self) -> Tuple[bool, str]:
        """
        Comprehensive stopping decision based on both quality and diversity.
        
        Returns:
            Tuple of (should_stop: bool, reason: str)
        """
        # Check quality plateau
        quality_stop, quality_reason = self.quality_monitor.should_stop_crawling()
        
        # Check content diversity
        diversity_stop, diversity_reason = self.diversity_monitor.is_content_repetitive()
        
        if quality_stop and diversity_stop:
            return True, f"Both quality plateau and content repetition detected: {quality_reason}; {diversity_reason}"
        elif quality_stop:
            return True, quality_reason
        elif diversity_stop:
            return True, diversity_reason
        else:
            return False, f"Continuing crawl: {quality_reason}; {diversity_reason}"
            
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get statistics from both monitoring systems."""
        quality_stats = self.quality_monitor.get_quality_stats()
        diversity_stop, diversity_reason = self.diversity_monitor.is_content_repetitive()
        
        return {
            **quality_stats,
            'diversity_assessment': diversity_reason,
            'diversity_suggests_stop': diversity_stop
        }