"""
Learning System with Pattern Storage

Stores successful crawling patterns and provides similarity matching
for strategy optimization. Implements memory database for pattern recognition
and success rate improvement over time.

Learning Database stores:
- Framework detection signatures
- Successful crawler configurations  
- Quality metrics per site type
- Failure patterns and recovery strategies
"""

import sqlite3
import json
import time
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from dataclasses import dataclass, asdict
import hashlib
from urllib.parse import urlparse
import numpy as np
from datetime import datetime, timedelta
import logging

from smart_mirror_agent import SiteType, CrawlStrategy, QualityMetrics, SitePattern
from reconnaissance import ReconResults


@dataclass
class LearningPattern:
    """Enhanced pattern with learning metrics"""
    id: str
    url_domain: str
    site_type: str
    strategy: str
    success_metrics: Dict[str, float]
    crawl_config: Dict[str, Any]
    frameworks_detected: List[str]
    timestamp: str
    success_count: int = 1
    total_attempts: int = 1
    avg_quality_score: float = 0.0
    last_used: str = ""


class PatternDatabase:
    """SQLite database for pattern storage and retrieval"""
    
    def __init__(self, db_path: str = "agent_learning.db"):
        self.db_path = Path(db_path)
        self.logger = logging.getLogger(__name__)
        self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS patterns (
                    id TEXT PRIMARY KEY,
                    url_domain TEXT NOT NULL,
                    site_type TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    success_metrics TEXT NOT NULL,
                    crawl_config TEXT NOT NULL,
                    frameworks_detected TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    success_count INTEGER DEFAULT 1,
                    total_attempts INTEGER DEFAULT 1,
                    avg_quality_score REAL DEFAULT 0.0,
                    last_used TEXT DEFAULT ""
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS domain_stats (
                    domain TEXT PRIMARY KEY,
                    total_crawls INTEGER DEFAULT 0,
                    successful_crawls INTEGER DEFAULT 0,
                    avg_quality REAL DEFAULT 0.0,
                    best_strategy TEXT DEFAULT "",
                    last_crawl TEXT DEFAULT ""
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS framework_patterns (
                    framework TEXT,
                    site_type TEXT,
                    preferred_strategy TEXT,
                    success_rate REAL,
                    avg_quality REAL,
                    sample_count INTEGER,
                    PRIMARY KEY (framework, site_type)
                )
            ''')
            
            # Create indexes for faster lookups
            conn.execute('CREATE INDEX IF NOT EXISTS idx_domain ON patterns(url_domain)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_frameworks ON patterns(frameworks_detected)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_site_type ON patterns(site_type)')
            
            conn.commit()
    
    def store_pattern(self, pattern: LearningPattern) -> bool:
        """Store or update a learning pattern"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO patterns 
                    (id, url_domain, site_type, strategy, success_metrics, crawl_config,
                     frameworks_detected, timestamp, success_count, total_attempts, 
                     avg_quality_score, last_used)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    pattern.id, pattern.url_domain, pattern.site_type, pattern.strategy,
                    json.dumps(pattern.success_metrics), json.dumps(pattern.crawl_config),
                    json.dumps(pattern.frameworks_detected), pattern.timestamp,
                    pattern.success_count, pattern.total_attempts,
                    pattern.avg_quality_score, pattern.last_used
                ))
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to store pattern: {e}")
            return False
    
    def get_patterns_by_domain(self, domain: str) -> List[LearningPattern]:
        """Get all patterns for a specific domain"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT * FROM patterns WHERE url_domain = ? 
                    ORDER BY avg_quality_score DESC, last_used DESC
                ''', (domain,))
                
                return [self._row_to_pattern(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Failed to get patterns for domain {domain}: {e}")
            return []
    
    def get_patterns_by_frameworks(self, frameworks: List[str]) -> List[LearningPattern]:
        """Get patterns that match any of the detected frameworks"""
        if not frameworks:
            return []
            
        try:
            with sqlite3.connect(self.db_path) as conn:
                patterns = []
                
                for framework in frameworks:
                    cursor = conn.execute('''
                        SELECT * FROM patterns WHERE frameworks_detected LIKE ?
                        ORDER BY avg_quality_score DESC
                    ''', (f'%{framework}%',))
                    
                    patterns.extend([self._row_to_pattern(row) for row in cursor.fetchall()])
                
                # Remove duplicates and sort by quality
                unique_patterns = {p.id: p for p in patterns}.values()
                return sorted(unique_patterns, key=lambda x: x.avg_quality_score, reverse=True)
                
        except Exception as e:
            self.logger.error(f"Failed to get patterns for frameworks {frameworks}: {e}")
            return []
    
    def get_best_strategy_for_site_type(self, site_type: SiteType) -> Optional[Tuple[CrawlStrategy, float]]:
        """Get the best performing strategy for a site type"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT strategy, AVG(avg_quality_score) as avg_score, COUNT(*) as count
                    FROM patterns 
                    WHERE site_type = ? AND avg_quality_score > 0.7
                    GROUP BY strategy
                    ORDER BY avg_score DESC, count DESC
                    LIMIT 1
                ''', (site_type.value,))
                
                row = cursor.fetchone()
                if row:
                    return CrawlStrategy(row[0]), row[1]
                    
        except Exception as e:
            self.logger.error(f"Failed to get best strategy for {site_type}: {e}")
            
        return None
    
    def update_pattern_success(self, pattern_id: str, quality_score: float) -> bool:
        """Update pattern success metrics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get current pattern
                cursor = conn.execute('SELECT * FROM patterns WHERE id = ?', (pattern_id,))
                row = cursor.fetchone()
                
                if row:
                    pattern = self._row_to_pattern(row)
                    
                    # Update metrics
                    pattern.total_attempts += 1
                    if quality_score >= 0.7:  # Consider as success
                        pattern.success_count += 1
                    
                    # Update average quality score
                    pattern.avg_quality_score = (
                        (pattern.avg_quality_score * (pattern.total_attempts - 1) + quality_score) /
                        pattern.total_attempts
                    )
                    
                    pattern.last_used = datetime.now().isoformat()
                    
                    # Store updated pattern
                    return self.store_pattern(pattern)
                    
        except Exception as e:
            self.logger.error(f"Failed to update pattern success: {e}")
            
        return False
    
    def _row_to_pattern(self, row) -> LearningPattern:
        """Convert database row to LearningPattern"""
        return LearningPattern(
            id=row[0],
            url_domain=row[1],
            site_type=row[2],
            strategy=row[3],
            success_metrics=json.loads(row[4]),
            crawl_config=json.loads(row[5]),
            frameworks_detected=json.loads(row[6]),
            timestamp=row[7],
            success_count=row[8],
            total_attempts=row[9],
            avg_quality_score=row[10],
            last_used=row[11]
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get learning database statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Total patterns
                total_patterns = conn.execute('SELECT COUNT(*) FROM patterns').fetchone()[0]
                
                # Success rate by strategy
                cursor = conn.execute('''
                    SELECT strategy, 
                           AVG(CAST(success_count AS REAL) / total_attempts) as success_rate,
                           AVG(avg_quality_score) as avg_quality,
                           COUNT(*) as pattern_count
                    FROM patterns 
                    GROUP BY strategy
                ''')
                strategy_stats = {row[0]: {
                    'success_rate': row[1],
                    'avg_quality': row[2], 
                    'pattern_count': row[3]
                } for row in cursor.fetchall()}
                
                # Top performing domains
                cursor = conn.execute('''
                    SELECT url_domain, AVG(avg_quality_score) as avg_quality, COUNT(*) as crawl_count
                    FROM patterns
                    GROUP BY url_domain
                    ORDER BY avg_quality DESC
                    LIMIT 10
                ''')
                top_domains = [{'domain': row[0], 'avg_quality': row[1], 'crawl_count': row[2]} 
                              for row in cursor.fetchall()]
                
                return {
                    'total_patterns': total_patterns,
                    'strategy_stats': strategy_stats,
                    'top_domains': top_domains
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {}


class LearningSystem:
    """Main learning system for pattern storage and similarity matching"""
    
    def __init__(self, db_path: str = "agent_learning.db"):
        self.db = PatternDatabase(db_path)
        self.logger = logging.getLogger(__name__)
        
        # Similarity thresholds
        self.domain_similarity_threshold = 0.8
        self.framework_similarity_threshold = 0.6
        self.pattern_decay_days = 30  # Patterns older than this get lower weights
    
    async def store_successful_pattern(self, url: str, recon_results: ReconResults, 
                                     strategy: CrawlStrategy, quality_metrics: QualityMetrics,
                                     crawl_config: Dict[str, Any]) -> str:
        """Store a successful crawling pattern"""
        
        domain = urlparse(url).netloc
        pattern_id = self._generate_pattern_id(url, strategy, recon_results.frameworks)
        
        # Create learning pattern
        pattern = LearningPattern(
            id=pattern_id,
            url_domain=domain,
            site_type=recon_results.site_type.value,
            strategy=strategy.value,
            success_metrics={
                'content_completeness': quality_metrics.content_completeness,
                'asset_coverage': quality_metrics.asset_coverage,
                'navigation_integrity': quality_metrics.navigation_integrity,
                'visual_fidelity': quality_metrics.visual_fidelity,
                'overall_score': quality_metrics.overall_score
            },
            crawl_config=crawl_config,
            frameworks_detected=recon_results.frameworks,
            timestamp=datetime.now().isoformat(),
            avg_quality_score=quality_metrics.overall_score
        )
        
        # Check if pattern already exists
        existing_patterns = self.db.get_patterns_by_domain(domain)
        existing_pattern = next((p for p in existing_patterns if p.id == pattern_id), None)
        
        if existing_pattern:
            # Update existing pattern
            success = self.db.update_pattern_success(pattern_id, quality_metrics.overall_score)
            self.logger.info(f"Updated existing pattern: {pattern_id}")
        else:
            # Store new pattern
            success = self.db.store_pattern(pattern)
            self.logger.info(f"Stored new pattern: {pattern_id}")
        
        return pattern_id if success else ""
    
    async def find_similar_patterns(self, url: str, recon_results: ReconResults) -> List[LearningPattern]:
        """Find similar patterns for strategy recommendation"""
        
        domain = urlparse(url).netloc
        similar_patterns = []
        
        # 1. Exact domain match (highest priority)
        domain_patterns = self.db.get_patterns_by_domain(domain)
        similar_patterns.extend(domain_patterns)
        
        # 2. Framework-based similarity
        if recon_results.frameworks:
            framework_patterns = self.db.get_patterns_by_frameworks(recon_results.frameworks)
            similar_patterns.extend(framework_patterns)
        
        # 3. Site type similarity
        best_strategy = self.db.get_best_strategy_for_site_type(recon_results.site_type)
        if best_strategy:
            # This would need additional query to get actual patterns
            pass
        
        # Remove duplicates and apply decay weighting
        unique_patterns = {p.id: p for p in similar_patterns}.values()
        weighted_patterns = self._apply_pattern_weighting(list(unique_patterns))
        
        # Sort by weighted score
        return sorted(weighted_patterns, key=lambda p: p.avg_quality_score, reverse=True)[:10]
    
    async def recommend_strategy(self, url: str, recon_results: ReconResults) -> Optional[Tuple[CrawlStrategy, Dict[str, Any], float]]:
        """Recommend best strategy based on learned patterns"""
        
        similar_patterns = await self.find_similar_patterns(url, recon_results)
        
        if not similar_patterns:
            # No similar patterns, use default recommendations
            return self._get_default_strategy(recon_results)
        
        # Get the best performing pattern
        best_pattern = similar_patterns[0]
        
        strategy = CrawlStrategy(best_pattern.strategy)
        config = best_pattern.crawl_config
        confidence = best_pattern.avg_quality_score
        
        # Adjust confidence based on similarity
        domain_match = urlparse(url).netloc == best_pattern.url_domain
        framework_overlap = len(set(recon_results.frameworks) & set(best_pattern.frameworks_detected))
        
        if domain_match:
            confidence *= 1.2  # Boost for exact domain match
        
        if framework_overlap > 0:
            confidence *= (1.0 + 0.1 * framework_overlap)  # Boost for framework overlap
        
        confidence = min(1.0, confidence)
        
        self.logger.info(f"Recommended strategy {strategy} with confidence {confidence:.2f}")
        
        return strategy, config, confidence
    
    def _generate_pattern_id(self, url: str, strategy: CrawlStrategy, frameworks: List[str]) -> str:
        """Generate unique pattern ID"""
        domain = urlparse(url).netloc
        framework_str = ','.join(sorted(frameworks))
        id_string = f"{domain}_{strategy.value}_{framework_str}"
        return hashlib.md5(id_string.encode()).hexdigest()[:12]
    
    def _apply_pattern_weighting(self, patterns: List[LearningPattern]) -> List[LearningPattern]:
        """Apply decay weighting to patterns based on age and success"""
        
        current_time = datetime.now()
        
        for pattern in patterns:
            pattern_time = datetime.fromisoformat(pattern.timestamp.replace('Z', '+00:00').replace('+00:00', ''))
            age_days = (current_time - pattern_time).days
            
            # Apply decay weighting
            if age_days > self.pattern_decay_days:
                decay_factor = max(0.5, 1.0 - (age_days - self.pattern_decay_days) / 365)
                pattern.avg_quality_score *= decay_factor
            
            # Apply success rate weighting
            success_rate = pattern.success_count / pattern.total_attempts
            pattern.avg_quality_score *= success_rate
        
        return patterns
    
    def _get_default_strategy(self, recon_results: ReconResults) -> Optional[Tuple[CrawlStrategy, Dict[str, Any], float]]:
        """Get default strategy when no patterns are available"""
        
        # Simple rule-based defaults
        if recon_results.js_complexity > 0.7:
            return CrawlStrategy.FULL_BROWSER, {'timeout': 45, 'headless': True}, 0.5
        elif recon_results.js_complexity > 0.4:
            return CrawlStrategy.JAVASCRIPT_RENDER, {'timeout': 30, 'wait_for': 'networkidle'}, 0.6
        else:
            return CrawlStrategy.BASIC_HTTP, {'timeout': 10, 'delay': 0.5}, 0.7
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        """Get comprehensive learning statistics"""
        return self.db.get_statistics()


# Example usage and testing
async def test_learning_system():
    learning = LearningSystem()
    
    # Mock data for testing
    from reconnaissance import SiteRecon
    from smart_mirror_agent import QualityMetrics
    
    # Test pattern storage
    mock_recon = ReconResults(
        site_type=SiteType.BANKING,
        frameworks=['React'],
        js_complexity=0.8,
        page_load_time=2.5,
        asset_count=45,
        recommended_strategy=CrawlStrategy.JAVASCRIPT_RENDER
    )
    
    mock_quality = QualityMetrics(
        content_completeness=0.85,
        asset_coverage=0.78,
        navigation_integrity=0.82,
        visual_fidelity=0.80,
        overall_score=0.81
    )
    
    pattern_id = await learning.store_successful_pattern(
        "https://www.nab.com.au",
        mock_recon,
        CrawlStrategy.JAVASCRIPT_RENDER,
        mock_quality,
        {'timeout': 30, 'delay': 1.0}
    )
    
    print(f"Stored pattern: {pattern_id}")
    
    # Test pattern retrieval
    similar_patterns = await learning.find_similar_patterns("https://www.nab.com.au", mock_recon)
    print(f"Found {len(similar_patterns)} similar patterns")
    
    # Test strategy recommendation
    recommendation = await learning.recommend_strategy("https://www.anz.com.au", mock_recon)
    if recommendation:
        strategy, config, confidence = recommendation
        print(f"Recommended: {strategy} with confidence {confidence:.2f}")
    
    # Get statistics
    stats = learning.get_learning_statistics()
    print(f"Learning Statistics: {stats}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_learning_system())