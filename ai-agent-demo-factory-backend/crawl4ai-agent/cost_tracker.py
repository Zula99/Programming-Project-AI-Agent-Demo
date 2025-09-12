"""
AI API Cost Tracking System

Tracks exact costs for OpenAI API usage with detailed breakdowns,
budget monitoring, and persistent cost logging.
"""

import json
import time
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import threading
from urllib.parse import urlparse


@dataclass
class APICall:
    """Single API call cost record"""
    timestamp: float
    url: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float
    method_used: str  # "ai", "cache", "heuristic"
    is_worthy: bool
    confidence: float
    reasoning: str


@dataclass
class SessionSummary:
    """Summary of costs for a crawl session"""
    domain: str
    session_start: float
    session_end: float
    total_urls: int
    ai_calls: int
    cached_calls: int
    heuristic_calls: int
    total_cost: float
    total_tokens: int
    average_cost_per_url: float
    worthy_percentage: float


class CostTracker:
    """
    Real-time AI cost tracking with budget monitoring and persistent logging.
    
    Features:
    - Real-time cost tracking per URL
    - Session summaries
    - Daily/monthly budget monitoring
    - Detailed cost breakdowns
    - Cost analytics and reporting
    """
    
    def __init__(self, domain: str, output_dir: str = "./output/cost_logs"):
        self.domain = domain
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Session tracking
        self.session_start = time.time()
        self.api_calls: List[APICall] = []
        self.lock = threading.Lock()
        
        # Cost tracking
        self.total_session_cost = 0.0
        self.total_session_tokens = 0
        
        # Counters
        self.total_urls = 0
        self.ai_calls = 0
        self.cached_calls = 0
        self.heuristic_calls = 0
        self.worthy_urls = 0
        
        # File paths
        self.session_file = self._generate_session_filename()
        self.daily_summary_file = self.output_dir / f"daily_costs_{date.today().strftime('%Y%m%d')}.json"
        
        # GPT-4o-mini pricing (as of 2024)
        self.pricing = {
            'gpt-4o-mini': {
                'input_cost_per_1k': 0.00015,   # $0.00015 per 1K input tokens
                'output_cost_per_1k': 0.0006    # $0.0006 per 1K output tokens
            },
            'gpt-3.5-turbo': {
                'input_cost_per_1k': 0.0015,    # $0.0015 per 1K input tokens
                'output_cost_per_1k': 0.002     # $0.002 per 1K output tokens
            }
        }
        
        print(f"💰 Cost tracking initialized for {domain}")
        print(f"📊 Session log: {self.session_file}")
    
    def _generate_session_filename(self) -> Path:
        """Generate unique session cost log filename"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        clean_domain = self.domain.replace('.', '_').replace('/', '_')
        return self.output_dir / f"cost_session_{clean_domain}_{timestamp}.json"
    
    def track_classification(self, url: str, result, content_length: int = 0):
        """
        Track a single URL classification with exact cost.
        
        Args:
            url: The URL that was classified
            result: ClassificationResult from AI classifier
            content_length: Length of content analyzed (for context)
        """
        with self.lock:
            self.total_urls += 1
            
            if result.method_used == "ai":
                # Real AI call - track exact costs
                call = APICall(
                    timestamp=time.time(),
                    url=url,
                    model="gpt-4o-mini",  # Could get from result if needed
                    prompt_tokens=result.prompt_tokens,
                    completion_tokens=result.completion_tokens,
                    total_tokens=result.total_tokens,
                    cost=result.estimated_cost,
                    method_used=result.method_used,
                    is_worthy=result.is_worthy,
                    confidence=result.confidence,
                    reasoning=result.reasoning[:100]  # Truncated for storage
                )
                
                self.api_calls.append(call)
                self.total_session_cost += result.estimated_cost
                self.total_session_tokens += result.total_tokens
                self.ai_calls += 1
                
                # Real-time cost display
                print(f"        💰 ${result.estimated_cost:.6f} | Total session: ${self.total_session_cost:.4f}")
                
            elif result.method_used == "cache":
                self.cached_calls += 1
                print(f"        📋 CACHED (${0:.6f}) | Total session: ${self.total_session_cost:.4f}")
                
            else:  # heuristic
                self.heuristic_calls += 1
                print(f"        🔧 HEURISTIC (${0:.6f}) | Total session: ${self.total_session_cost:.4f}")
            
            if result.is_worthy:
                self.worthy_urls += 1
                
            # Save incremental update every 10 URLs to prevent data loss
            if self.total_urls % 10 == 0:
                self._save_incremental_update()
    
    def _save_incremental_update(self):
        """Save incremental session data to prevent data loss"""
        try:
            # Ensure directory exists
            self.session_file.parent.mkdir(parents=True, exist_ok=True)
            
            session_data = {
                'domain': self.domain,
                'session_start': self.session_start,
                'last_update': time.time(),
                'urls_processed': self.total_urls,
                'current_cost': self.total_session_cost,
                'current_tokens': self.total_session_tokens,
                'ai_calls': self.ai_calls,
                'cached_calls': self.cached_calls,
                'heuristic_calls': self.heuristic_calls,
                'api_calls': [asdict(call) for call in self.api_calls[-10:]]  # Last 10 calls
            }
            
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
                
        except Exception as e:
            print(f"⚠️  Failed to save incremental cost update: {e}")
    
    def get_session_stats(self) -> Dict:
        """Get current session statistics"""
        worthy_percentage = (self.worthy_urls / self.total_urls * 100) if self.total_urls > 0 else 0
        avg_cost_per_url = self.total_session_cost / self.total_urls if self.total_urls > 0 else 0
        avg_cost_per_ai_call = self.total_session_cost / self.ai_calls if self.ai_calls > 0 else 0
        
        return {
            'domain': self.domain,
            'urls_processed': self.total_urls,
            'ai_calls': self.ai_calls,
            'cached_calls': self.cached_calls,
            'heuristic_calls': self.heuristic_calls,
            'total_cost': self.total_session_cost,
            'total_tokens': self.total_session_tokens,
            'average_cost_per_url': avg_cost_per_url,
            'average_cost_per_ai_call': avg_cost_per_ai_call,
            'worthy_percentage': worthy_percentage,
            'session_duration': time.time() - self.session_start
        }
    
    def print_session_summary(self):
        """Print detailed session cost summary"""
        stats = self.get_session_stats()
        
        print("\n" + "="*60)
        print("💰 AI COST TRACKING SUMMARY")
        print("="*60)
        print(f"📊 Domain: {stats['domain']}")
        print(f"🔗 URLs processed: {stats['urls_processed']}")
        print(f"🤖 AI classifications: {stats['ai_calls']}")
        print(f"📋 Cached results: {stats['cached_calls']}")
        print(f"🔧 Heuristic fallbacks: {stats['heuristic_calls']}")
        print(f"💸 Total cost: ${stats['total_cost']:.4f}")
        print(f"🎯 Tokens used: {stats['total_tokens']:,}")
        print(f"📈 Avg cost/URL: ${stats['average_cost_per_url']:.6f}")
        if stats['ai_calls'] > 0:
            print(f"💎 Avg cost/AI call: ${stats['average_cost_per_ai_call']:.6f}")
        print(f"✅ Worthy content: {stats['worthy_percentage']:.1f}%")
        print(f"⏱️  Session duration: {stats['session_duration']:.1f}s")
        print("="*60)
    
    def save_final_session(self) -> SessionSummary:
        """Save complete session data and return summary"""
        session_end = time.time()
        
        # Create session summary
        summary = SessionSummary(
            domain=self.domain,
            session_start=self.session_start,
            session_end=session_end,
            total_urls=self.total_urls,
            ai_calls=self.ai_calls,
            cached_calls=self.cached_calls,
            heuristic_calls=self.heuristic_calls,
            total_cost=self.total_session_cost,
            total_tokens=self.total_session_tokens,
            average_cost_per_url=self.total_session_cost / self.total_urls if self.total_urls > 0 else 0,
            worthy_percentage=self.worthy_urls / self.total_urls * 100 if self.total_urls > 0 else 0
        )
        
        # Save detailed session log
        session_data = {
            'summary': asdict(summary),
            'detailed_calls': [asdict(call) for call in self.api_calls],
            'pricing_used': self.pricing,
            'session_metadata': {
                'generated_at': datetime.now().isoformat(),
                'python_version': f"3.x",
                'total_duration_seconds': session_end - self.session_start
            }
        }
        
        # Save session file
        try:
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            print(f"💾 Detailed cost log saved: {self.session_file}")
        except Exception as e:
            print(f"⚠️  Failed to save session log: {e}")
        
        # Update daily summary
        self._update_daily_summary(summary)
        
        return summary
    
    def _update_daily_summary(self, summary: SessionSummary):
        """Update daily cost summary"""
        try:
            # Load existing daily data
            daily_data = []
            if self.daily_summary_file.exists():
                with open(self.daily_summary_file, 'r') as f:
                    daily_data = json.load(f)
            
            # Add this session
            daily_data.append({
                'session_summary': asdict(summary),
                'session_file': str(self.session_file)
            })
            
            # Calculate daily totals
            daily_totals = {
                'date': date.today().isoformat(),
                'total_sessions': len(daily_data),
                'total_cost': sum(session['session_summary']['total_cost'] for session in daily_data),
                'total_urls': sum(session['session_summary']['total_urls'] for session in daily_data),
                'total_tokens': sum(session['session_summary']['total_tokens'] for session in daily_data),
                'sessions': daily_data
            }
            
            # Save updated daily summary
            with open(self.daily_summary_file, 'w') as f:
                json.dump(daily_totals, f, indent=2)
                
            print(f"📅 Daily summary updated: ${daily_totals['total_cost']:.4f} total today")
            
        except Exception as e:
            print(f"⚠️  Failed to update daily summary: {e}")
    
    @classmethod
    def load_session(cls, session_file: Path) -> Dict:
        """Load a previous session for analysis"""
        try:
            with open(session_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load session {session_file}: {e}")
            return {}
    
    @classmethod
    def analyze_daily_costs(cls, daily_file: Path) -> Dict:
        """Analyze daily cost patterns"""
        try:
            with open(daily_file, 'r') as f:
                daily_data = json.load(f)
            
            sessions = daily_data.get('sessions', [])
            if not sessions:
                return {}
            
            # Analysis
            costs = [s['session_summary']['total_cost'] for s in sessions]
            urls_per_session = [s['session_summary']['total_urls'] for s in sessions]
            
            return {
                'total_cost': daily_data.get('total_cost', 0),
                'total_sessions': len(sessions),
                'average_session_cost': sum(costs) / len(costs),
                'max_session_cost': max(costs),
                'min_session_cost': min(costs),
                'average_urls_per_session': sum(urls_per_session) / len(urls_per_session),
                'cost_efficiency': daily_data.get('total_cost', 0) / daily_data.get('total_urls', 1)
            }
            
        except Exception as e:
            print(f"Failed to analyze daily costs: {e}")
            return {}


# Context manager for easy cost tracking
class CostTrackingSession:
    """Context manager for automatic cost tracking"""
    
    def __init__(self, domain: str, output_dir: str = "./output/cost_logs"):
        self.tracker = CostTracker(domain, output_dir)
    
    def __enter__(self) -> CostTracker:
        return self.tracker
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.tracker.print_session_summary()
        summary = self.tracker.save_final_session()
        
        if exc_type is None:
            print("✅ Cost tracking completed successfully")
        else:
            print(f"⚠️  Cost tracking ended with error: {exc_val}")
        
        return False  # Don't suppress exceptions


# Integration helper for existing systems
def track_classification_cost(tracker: CostTracker, url: str, result, content_length: int = 0):
    """Helper function to track classification costs"""
    if tracker:
        tracker.track_classification(url, result, content_length)


# Example usage and testing
async def test_cost_tracking():
    """Test the cost tracking system"""
    from ai_content_classifier import AIContentClassifier, ClassificationResult
    from ai_config import get_ai_config
    
    config = get_ai_config()
    
    with CostTrackingSession("test.com") as tracker:
        # Simulate some classifications
        if config.openai_api_key:
            classifier = AIContentClassifier(
                api_key=config.openai_api_key,
                model="gpt-4o-mini"
            )
            
            test_urls = [
                "https://test.com/about",
                "https://test.com/products", 
                "https://test.com/contact"
            ]
            
            for url in test_urls:
                try:
                    result = await classifier.classify_content(
                        url=url,
                        content="Test business content for demo classification",
                        title="Test Business Page"
                    )
                    tracker.track_classification(url, result, 100)
                    
                except Exception as e:
                    print(f"Test classification failed: {e}")
        
        # Print intermediate stats
        stats = tracker.get_session_stats()
        print(f"Intermediate stats: {stats['total_cost']:.4f} for {stats['urls_processed']} URLs")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_cost_tracking())