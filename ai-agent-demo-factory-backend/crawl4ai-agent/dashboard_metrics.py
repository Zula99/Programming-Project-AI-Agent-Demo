"""
Dashboard Metrics - Clean metric calculations for frontend integration

Provides real-time coverage tracking and dashboard data without cluttering
crawler internals. Frontend devs get clean APIs without digging through
crawler implementation details.

US-53: Intelligent Site Coverage Monitoring & Visualization
"""

import time
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import logging


class CrawlPhase(Enum):
    """Current phase of the crawling process"""
    INITIALIZING = "initializing"
    SITEMAP_ANALYSIS = "sitemap_analysis" 
    CRAWLING = "crawling"
    QUALITY_PLATEAU = "quality_plateau"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CoverageSnapshot:
    """Real-time coverage metrics snapshot for frontend"""
    run_id: str
    timestamp: float
    phase: CrawlPhase
    
    # Core coverage metrics
    coverage_percentage: float
    pages_crawled: int
    total_known_urls: int
    
    # Discovery tracking
    initial_sitemap_urls: int
    discovered_urls: int
    
    # Quality metrics
    recent_quality_score: float
    overall_quality_trend: str  # "improving", "stable", "declining"
    
    # Performance metrics
    crawl_velocity: float  # pages per minute
    estimated_time_remaining: Optional[int]  # seconds
    
    # Status information
    current_url: Optional[str]
    quality_plateau_detected: bool
    stop_reason: Optional[str]


class CoverageCalculator:
    """
    Dynamic coverage calculation that adapts as new URLs are discovered.
    
    Handles both sitemap and progressive crawls:
    - Sitemap: Start with known URLs, add discovered URLs dynamically
    - Progressive: Build URL inventory as we discover links
    """
    
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.start_time = time.time()
        self.logger = logging.getLogger(__name__)
        
        # URL tracking
        self.initial_sitemap_urls: Set[str] = set()
        self.discovered_urls: Set[str] = set()
        self.crawled_urls: Set[str] = set()
        self.failed_urls: Set[str] = set()
        
        # Quality tracking
        self.quality_scores: List[float] = []
        self.quality_timestamps: List[float] = []
        
        # Phase tracking
        self.current_phase = CrawlPhase.INITIALIZING
        self.current_url: Optional[str] = None
        self.quality_plateau_detected = False
        self.stop_reason: Optional[str] = None
        
        # Performance tracking
        self.crawl_start_time: Optional[float] = None
        self.last_update_time = time.time()
    
    def initialize_sitemap_urls(self, sitemap_urls: List[str]):
        """Initialize with sitemap URLs if available"""
        self.initial_sitemap_urls = set(sitemap_urls)
        self.logger.info(f"Initialized with {len(sitemap_urls)} sitemap URLs")
    
    def set_phase(self, phase: CrawlPhase):
        """Update current crawl phase"""
        self.current_phase = phase
        if phase == CrawlPhase.CRAWLING and not self.crawl_start_time:
            self.crawl_start_time = time.time()
        self.last_update_time = time.time()
    
    def add_discovered_urls(self, new_urls: List[str]):
        """Add newly discovered URLs during crawling"""
        before_count = len(self.discovered_urls)
        self.discovered_urls.update(new_urls)
        after_count = len(self.discovered_urls)
        
        if after_count > before_count:
            self.logger.debug(f"Discovered {after_count - before_count} new URLs")
        self.last_update_time = time.time()
    
    def mark_url_crawled(self, url: str, success: bool, quality_score: Optional[float] = None):
        """Mark URL as crawled and update quality tracking"""
        if success:
            self.crawled_urls.add(url)
        else:
            self.failed_urls.add(url)
        
        self.current_url = url
        
        # Track quality if provided
        if quality_score is not None:
            self.quality_scores.append(quality_score)
            self.quality_timestamps.append(time.time())
            
            # Keep only recent quality scores (last 20 pages)
            if len(self.quality_scores) > 20:
                self.quality_scores = self.quality_scores[-20:]
                self.quality_timestamps = self.quality_timestamps[-20:]
        
        self.last_update_time = time.time()
    
    def set_quality_plateau(self, detected: bool, reason: Optional[str] = None):
        """Update quality plateau status"""
        self.quality_plateau_detected = detected
        if detected and reason:
            self.stop_reason = reason
            self.set_phase(CrawlPhase.QUALITY_PLATEAU)
        self.last_update_time = time.time()
    
    def calculate_coverage_percentage(self) -> float:
        """
        Calculate dynamic coverage percentage
        
        Returns:
            Percentage of known URLs that have been crawled
        """
        total_known = len(self.initial_sitemap_urls | self.discovered_urls)
        crawled_count = len(self.crawled_urls)
        
        if total_known == 0:
            return 0.0
        
        return (crawled_count / total_known) * 100
    
    def calculate_crawl_velocity(self) -> float:
        """Calculate pages per minute crawling rate"""
        if not self.crawl_start_time or len(self.crawled_urls) == 0:
            return 0.0
        
        elapsed_time = time.time() - self.crawl_start_time
        if elapsed_time == 0:
            return 0.0
        
        return (len(self.crawled_urls) / elapsed_time) * 60  # pages per minute
    
    def estimate_time_remaining(self) -> Optional[int]:
        """Estimate remaining crawl time in seconds"""
        velocity = self.calculate_crawl_velocity()
        if velocity <= 0:
            return None
        
        total_known = len(self.initial_sitemap_urls | self.discovered_urls)
        remaining_pages = total_known - len(self.crawled_urls)
        
        if remaining_pages <= 0:
            return 0
        
        return int((remaining_pages / velocity) * 60)  # Convert to seconds
    
    def get_quality_trend(self) -> str:
        """Analyze recent quality trend"""
        if len(self.quality_scores) < 3:
            return "insufficient_data"
        
        recent_scores = self.quality_scores[-5:]  # Last 5 scores
        if len(recent_scores) < 3:
            return "insufficient_data"
        
        # Simple trend analysis
        first_half = sum(recent_scores[:len(recent_scores)//2]) / (len(recent_scores)//2)
        second_half = sum(recent_scores[len(recent_scores)//2:]) / (len(recent_scores) - len(recent_scores)//2)
        
        diff = second_half - first_half
        if diff > 0.05:
            return "improving"
        elif diff < -0.05:
            return "declining"
        else:
            return "stable"
    
    def get_current_snapshot(self) -> CoverageSnapshot:
        """Get current coverage snapshot for frontend"""
        total_known = len(self.initial_sitemap_urls | self.discovered_urls)
        recent_quality = self.quality_scores[-1] if self.quality_scores else 0.0
        
        return CoverageSnapshot(
            run_id=self.run_id,
            timestamp=time.time(),
            phase=self.current_phase,
            coverage_percentage=self.calculate_coverage_percentage(),
            pages_crawled=len(self.crawled_urls),
            total_known_urls=total_known,
            initial_sitemap_urls=len(self.initial_sitemap_urls),
            discovered_urls=len(self.discovered_urls),
            recent_quality_score=recent_quality,
            overall_quality_trend=self.get_quality_trend(),
            crawl_velocity=self.calculate_crawl_velocity(),
            estimated_time_remaining=self.estimate_time_remaining(),
            current_url=self.current_url,
            quality_plateau_detected=self.quality_plateau_detected,
            stop_reason=self.stop_reason
        )
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get comprehensive stats for final reporting"""
        total_time = time.time() - self.start_time
        crawl_time = time.time() - self.crawl_start_time if self.crawl_start_time else 0
        
        return {
            'run_id': self.run_id,
            'final_coverage_percentage': self.calculate_coverage_percentage(),
            'total_pages_crawled': len(self.crawled_urls),
            'total_pages_failed': len(self.failed_urls),
            'total_urls_discovered': len(self.initial_sitemap_urls | self.discovered_urls),
            'initial_sitemap_urls': len(self.initial_sitemap_urls),
            'discovered_during_crawl': len(self.discovered_urls),
            'average_quality_score': sum(self.quality_scores) / len(self.quality_scores) if self.quality_scores else 0.0,
            'quality_trend': self.get_quality_trend(),
            'average_crawl_velocity': self.calculate_crawl_velocity(),
            'total_execution_time': total_time,
            'pure_crawl_time': crawl_time,
            'quality_plateau_detected': self.quality_plateau_detected,
            'stop_reason': self.stop_reason,
            'final_phase': self.current_phase.value
        }


# Global registry for active crawls
active_coverage_calculators: Dict[str, CoverageCalculator] = {}


def create_coverage_calculator(run_id: str) -> CoverageCalculator:
    """Create and register a new coverage calculator"""
    calculator = CoverageCalculator(run_id)
    active_coverage_calculators[run_id] = calculator
    return calculator


def get_coverage_calculator(run_id: str) -> Optional[CoverageCalculator]:
    """Get existing coverage calculator by run_id"""
    return active_coverage_calculators.get(run_id)


def remove_coverage_calculator(run_id: str):
    """Remove coverage calculator when crawl completes"""
    if run_id in active_coverage_calculators:
        del active_coverage_calculators[run_id]


def get_all_active_runs() -> List[str]:
    """Get list of all active crawl run IDs"""
    return list(active_coverage_calculators.keys())