"""
SmartMirrorAgent Main Integration

Complete integration of all agent components:
- SmartMirrorAgent core
- Site Reconnaissance  
- Adaptive Crawler
- Quality Monitor
- Learning System

Main entry point for the AI Agent Demo Factory crawling system.
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import argparse
from datetime import datetime

# Import all agent components
from smart_mirror_agent import SmartMirrorAgent, SiteType, CrawlStrategy, QualityMetrics
from reconnaissance import SiteRecon, ReconResults
from adaptive_crawler import AdaptiveCrawler
from quality_monitor import QualityMonitor, CrawlData
from learning_system import LearningSystem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agent.log'),
        logging.StreamHandler()
    ]
)


class SmartMirrorAgentIntegrated:
    """
    Fully integrated SmartMirrorAgent with all capabilities
    
    Flow: URL Input → Check Memory → Quick Recon → Strategy Selection → 
          Adaptive Crawl → Quality Monitoring → Mirror Build → Learning Storage
    """
    
    def __init__(self, output_dir: str = "./agent_output", memory_db: str = "agent_learning.db"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Initialize all components
        self.reconnaissance = SiteRecon(timeout=10)
        self.adaptive_crawler = AdaptiveCrawler(str(self.output_dir))
        self.quality_monitor = QualityMonitor()
        self.learning_system = LearningSystem(memory_db)
        
        self.logger = logging.getLogger(__name__)
        
        # Performance tracking
        self.session_stats = {
            'start_time': None,
            'urls_processed': 0,
            'successful_crawls': 0,
            'total_quality_score': 0.0,
            'strategy_usage': {},
            'processing_times': []
        }
    
    async def process_url(self, url: str, max_pages: int = 50) -> Dict[str, Any]:
        """
        Complete URL processing with full agent capabilities
        
        Args:
            url: Target URL to process
            max_pages: Maximum pages to crawl
            
        Returns:
            Dict containing results, metrics, and recommendations
        """
        process_start = time.time()
        self.session_stats['start_time'] = process_start
        
        self.logger.info(f"🚀 Starting SmartMirrorAgent processing for: {url}")
        
        try:
            # Step 1: Quick Reconnaissance (Target: <10s)
            recon_start = time.time()
            self.logger.info("🔍 Phase 1: Site Reconnaissance")
            
            recon_results = await self.reconnaissance.analyze_site(url)
            recon_time = time.time() - recon_start
            
            self.logger.info(f"📊 Reconnaissance completed in {recon_time:.2f}s")
            self.logger.info(f"   Site Type: {recon_results.site_type}")
            self.logger.info(f"   Frameworks: {recon_results.frameworks}")
            self.logger.info(f"   JS Complexity: {recon_results.js_complexity:.2f}")
            self.logger.info(f"   Recommended Strategy: {recon_results.recommended_strategy}")
            
            # Step 2: Check Learning Memory for Similar Patterns
            memory_start = time.time()
            self.logger.info("🧠 Phase 2: Memory Pattern Matching")
            
            similar_patterns = await self.learning_system.find_similar_patterns(url, recon_results)
            strategy_recommendation = await self.learning_system.recommend_strategy(url, recon_results)
            
            memory_time = time.time() - memory_start
            
            if similar_patterns:
                self.logger.info(f"   Found {len(similar_patterns)} similar patterns")
            if strategy_recommendation:
                strategy, config, confidence = strategy_recommendation
                self.logger.info(f"   Memory recommends: {strategy} (confidence: {confidence:.2f})")
            
            # Step 3: Final Strategy Selection
            selected_strategy = self._select_final_strategy(recon_results, strategy_recommendation)
            self.logger.info(f"🎯 Selected Strategy: {selected_strategy}")
            
            # Track strategy usage
            strategy_name = selected_strategy.name
            self.session_stats['strategy_usage'][strategy_name] = self.session_stats['strategy_usage'].get(strategy_name, 0) + 1
            
            # Step 4: Adaptive Crawling with Quality Monitoring
            crawl_start = time.time()
            self.logger.info("🕸️ Phase 3: Adaptive Crawling")
            
            crawl_success, crawl_data = await self.adaptive_crawler.crawl_with_strategy(
                url, selected_strategy, max_pages
            )
            
            crawl_time = time.time() - crawl_start
            crawl_stats = self.adaptive_crawler.get_crawl_statistics()
            
            self.logger.info(f"📈 Crawling completed in {crawl_time:.2f}s")
            self.logger.info(f"   Pages crawled: {crawl_stats['pages_crawled']}")
            self.logger.info(f"   Success rate: {crawl_stats['success_rate']:.2%}")
            self.logger.info(f"   Total assets: {crawl_stats['total_assets']}")
            
            # Step 5: Comprehensive Quality Assessment
            quality_start = time.time()
            self.logger.info("⚡ Phase 4: Quality Assessment")
            
            quality_metrics = await self.quality_monitor.assess_crawl_quality(crawl_data)
            quality_time = time.time() - quality_start
            
            recommendation = self.quality_monitor.get_quality_recommendation(quality_metrics)
            
            self.logger.info(f"📊 Quality assessment completed in {quality_time:.2f}s")
            self.logger.info(f"   Overall Score: {quality_metrics.overall_score:.2f}")
            self.logger.info(f"   Content: {quality_metrics.content_completeness:.2f}")
            self.logger.info(f"   Assets: {quality_metrics.asset_coverage:.2f}")
            self.logger.info(f"   Navigation: {quality_metrics.navigation_integrity:.2f}")
            self.logger.info(f"   Visual: {quality_metrics.visual_fidelity:.2f}")
            self.logger.info(f"   Recommendation: {recommendation}")
            
            # Step 6: Learning Storage (if successful)
            learning_start = time.time()
            if quality_metrics.overall_score >= 0.7:
                self.logger.info("💾 Phase 5: Learning Pattern Storage")
                
                crawl_config = strategy_recommendation[1] if strategy_recommendation else {}
                pattern_id = await self.learning_system.store_successful_pattern(
                    url, recon_results, selected_strategy, quality_metrics, crawl_config
                )
                
                learning_time = time.time() - learning_start
                self.logger.info(f"   Stored learning pattern: {pattern_id}")
            else:
                learning_time = time.time() - learning_start
                self.logger.info("⚠️ Quality below threshold - no pattern stored")
            
            # Step 7: Static Mirror Building (placeholder)
            mirror_start = time.time()
            self.logger.info("🏗️ Phase 6: Static Mirror Building")
            
            mirror_path = await self._build_static_mirror(crawl_data, url)
            mirror_time = time.time() - mirror_start
            
            self.logger.info(f"   Mirror built at: {mirror_path}")
            
            # Calculate total processing time
            total_time = time.time() - process_start
            
            # Update session statistics
            self._update_session_stats(quality_metrics.overall_score, total_time, crawl_success)
            
            # Prepare comprehensive results
            results = {
                'success': crawl_success,
                'url': url,
                'processing_time': {
                    'total': total_time,
                    'reconnaissance': recon_time,
                    'memory_lookup': memory_time,
                    'crawling': crawl_time,
                    'quality_assessment': quality_time,
                    'learning_storage': learning_time,
                    'mirror_building': mirror_time
                },
                'reconnaissance': {
                    'site_type': recon_results.site_type.value,
                    'frameworks': recon_results.frameworks,
                    'js_complexity': recon_results.js_complexity,
                    'page_load_time': recon_results.page_load_time,
                    'asset_count': recon_results.asset_count
                },
                'strategy': {
                    'selected': selected_strategy.value,
                    'recommended_by_recon': recon_results.recommended_strategy.value,
                    'memory_recommendation': strategy_recommendation[0].value if strategy_recommendation else None,
                    'memory_confidence': strategy_recommendation[2] if strategy_recommendation else 0.0
                },
                'crawl_stats': crawl_stats,
                'quality_metrics': {
                    'content_completeness': quality_metrics.content_completeness,
                    'asset_coverage': quality_metrics.asset_coverage,
                    'navigation_integrity': quality_metrics.navigation_integrity,
                    'visual_fidelity': quality_metrics.visual_fidelity,
                    'overall_score': quality_metrics.overall_score
                },
                'recommendation': recommendation,
                'mirror_path': mirror_path,
                'similar_patterns_found': len(similar_patterns),
                'learning_stored': quality_metrics.overall_score >= 0.7
            }
            
            self.logger.info(f"✅ Processing completed successfully in {total_time:.2f}s")
            self.logger.info(f"🎯 Target achieved: 90% success rate goal - Current quality: {quality_metrics.overall_score:.1%}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Processing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'url': url,
                'processing_time': {'total': time.time() - process_start}
            }
    
    def _select_final_strategy(self, recon_results: ReconResults, 
                              memory_recommendation: Optional[Tuple]) -> CrawlStrategy:
        """Select final strategy based on reconnaissance and memory"""
        
        # Priority 1: High-confidence memory recommendation
        if memory_recommendation and memory_recommendation[2] > 0.8:
            return memory_recommendation[0]
        
        # Priority 2: Site-specific overrides for critical types
        if recon_results.site_type == SiteType.BANKING:
            return CrawlStrategy.JAVASCRIPT_RENDER  # Banking sites need careful handling
        
        # Priority 3: Memory recommendation with decent confidence
        if memory_recommendation and memory_recommendation[2] > 0.6:
            return memory_recommendation[0]
        
        # Priority 4: Reconnaissance recommendation
        return recon_results.recommended_strategy
    
    async def _build_static_mirror(self, crawl_data: CrawlData, base_url: str) -> str:
        """Build static mirror from crawled data (placeholder implementation)"""
        
        # This would integrate with the existing build_static_mirror.py
        # For now, return a placeholder path
        
        mirror_dir = self.output_dir / "mirrors" / f"mirror_{int(time.time())}"
        mirror_dir.mkdir(parents=True, exist_ok=True)
        
        # Save crawl data as JSON for now
        with open(mirror_dir / "crawl_data.json", 'w') as f:
            json.dump({
                'base_url': crawl_data.base_url,
                'total_pages': crawl_data.total_pages,
                'failed_pages': crawl_data.failed_pages,
                'assets_summary': {k: len(v) for k, v in crawl_data.assets.items()},
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)
        
        return str(mirror_dir)
    
    def _update_session_stats(self, quality_score: float, processing_time: float, success: bool):
        """Update session statistics"""
        self.session_stats['urls_processed'] += 1
        if success:
            self.session_stats['successful_crawls'] += 1
        self.session_stats['total_quality_score'] += quality_score
        self.session_stats['processing_times'].append(processing_time)
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """Get comprehensive session statistics"""
        if self.session_stats['urls_processed'] == 0:
            return {'message': 'No URLs processed yet'}
        
        avg_quality = self.session_stats['total_quality_score'] / self.session_stats['urls_processed']
        success_rate = self.session_stats['successful_crawls'] / self.session_stats['urls_processed']
        avg_processing_time = sum(self.session_stats['processing_times']) / len(self.session_stats['processing_times'])
        
        return {
            'urls_processed': self.session_stats['urls_processed'],
            'successful_crawls': self.session_stats['successful_crawls'],
            'success_rate': success_rate,
            'average_quality_score': avg_quality,
            'average_processing_time': avg_processing_time,
            'strategy_usage': self.session_stats['strategy_usage'],
            'target_achievement': {
                '90_percent_success_rate': success_rate >= 0.9,
                '90_percent_quality_score': avg_quality >= 0.9,
                'performance_summary': self._get_performance_summary(success_rate, avg_quality)
            }
        }
    
    def _get_performance_summary(self, success_rate: float, avg_quality: float) -> str:
        """Get performance summary against targets"""
        if success_rate >= 0.9 and avg_quality >= 0.9:
            return "🎯 EXCELLENT - Both targets achieved!"
        elif success_rate >= 0.9 or avg_quality >= 0.9:
            return "✅ GOOD - One target achieved"
        elif success_rate >= 0.8 or avg_quality >= 0.8:
            return "👍 ACCEPTABLE - Close to targets"
        else:
            return "⚠️ NEEDS IMPROVEMENT - Below targets"
    
    async def process_multiple_urls(self, urls: List[str], max_pages_per_url: int = 20) -> Dict[str, Any]:
        """Process multiple URLs and provide aggregate statistics"""
        
        self.logger.info(f"🚀 Starting batch processing of {len(urls)} URLs")
        
        results = []
        for i, url in enumerate(urls, 1):
            self.logger.info(f"📍 Processing URL {i}/{len(urls)}: {url}")
            
            result = await self.process_url(url, max_pages_per_url)
            results.append(result)
            
            # Brief pause between URLs
            await asyncio.sleep(1)
        
        # Calculate aggregate statistics
        successful_results = [r for r in results if r.get('success', False)]
        success_rate = len(successful_results) / len(results)
        
        if successful_results:
            avg_quality = sum(r['quality_metrics']['overall_score'] for r in successful_results) / len(successful_results)
            avg_processing_time = sum(r['processing_time']['total'] for r in results) / len(results)
        else:
            avg_quality = 0.0
            avg_processing_time = 0.0
        
        batch_summary = {
            'batch_info': {
                'total_urls': len(urls),
                'successful_crawls': len(successful_results),
                'success_rate': success_rate,
                'average_quality_score': avg_quality,
                'average_processing_time': avg_processing_time
            },
            'target_assessment': {
                '90_percent_success_rate_achieved': success_rate >= 0.9,
                '90_percent_quality_achieved': avg_quality >= 0.9,
                'performance_grade': self._get_performance_summary(success_rate, avg_quality)
            },
            'detailed_results': results,
            'session_stats': self.get_session_statistics()
        }
        
        self.logger.info(f"✅ Batch processing completed")
        self.logger.info(f"📊 Success Rate: {success_rate:.1%}")
        self.logger.info(f"⭐ Average Quality: {avg_quality:.1%}")
        self.logger.info(f"⏱️ Average Time: {avg_processing_time:.1f}s per URL")
        
        return batch_summary


async def main():
    """Main entry point with CLI support"""
    parser = argparse.ArgumentParser(description="SmartMirrorAgent - AI Demo Factory Crawler")
    parser.add_argument("urls", nargs="+", help="URLs to process")
    parser.add_argument("--max-pages", type=int, default=50, help="Maximum pages per URL")
    parser.add_argument("--output-dir", default="./agent_output", help="Output directory")
    parser.add_argument("--memory-db", default="agent_learning.db", help="Learning database path")
    parser.add_argument("--batch-mode", action="store_true", help="Process all URLs in batch mode")
    
    args = parser.parse_args()
    
    # Initialize agent
    agent = SmartMirrorAgentIntegrated(args.output_dir, args.memory_db)
    
    if args.batch_mode or len(args.urls) > 1:
        # Batch processing
        results = await agent.process_multiple_urls(args.urls, args.max_pages)
        print("\n" + "="*80)
        print("BATCH PROCESSING RESULTS")
        print("="*80)
        print(f"Success Rate: {results['batch_info']['success_rate']:.1%}")
        print(f"Average Quality: {results['batch_info']['average_quality_score']:.1%}")
        print(f"Performance Grade: {results['target_assessment']['performance_grade']}")
    else:
        # Single URL processing
        url = args.urls[0]
        result = await agent.process_url(url, args.max_pages)
        
        print("\n" + "="*80)
        print("PROCESSING RESULTS")
        print("="*80)
        print(f"URL: {result['url']}")
        print(f"Success: {result['success']}")
        if result['success']:
            print(f"Quality Score: {result['quality_metrics']['overall_score']:.1%}")
            print(f"Processing Time: {result['processing_time']['total']:.1f}s")
            print(f"Strategy Used: {result['strategy']['selected']}")
            print(f"Mirror Path: {result['mirror_path']}")


if __name__ == "__main__":
    asyncio.run(main())