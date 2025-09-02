"""
AI Content Classifier for Demo Worthiness
Replaces rigid rule-based URL filtering with intelligent content assessment.
"""
import asyncio
import logging
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

@dataclass
class ClassificationResult:
    """Result of AI content classification"""
    is_worthy: bool
    confidence: float  # 0.0 to 1.0
    reasoning: str
    method_used: str  # "ai", "heuristic", "cache"
    
class HeuristicClassifier:
    """Fallback classifier using enhanced heuristic rules"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def classify(self, url: str, content: str = "", title: str = "") -> ClassificationResult:
        """Enhanced heuristic classification for demo worthiness"""
        score = 0.5  # baseline
        text = f"{url} {title} {content}".lower()
        reasoning_parts = []
        
        # Universal high-value indicators
        demo_value_terms = [
            'product', 'service', 'about', 'contact', 'pricing', 'solution',
            'feature', 'benefit', 'overview', 'home', 'main', 'landing',
            'business', 'commercial', 'corporate', 'professional'
        ]
        
        # Boost for demo-worthy content
        for term in demo_value_terms:
            if term in text:
                score += 0.15
                reasoning_parts.append(f"Contains valuable term: {term}")
                break
        
        # Smart PDF classification
        if url.endswith('.pdf'):
            if any(keyword in text for keyword in 
                  ['report', 'guide', 'brochure', 'whitepaper', 'manual', 'overview']):
                score += 0.3
                reasoning_parts.append("Valuable business document PDF")
            elif any(keyword in text for keyword in 
                    ['debug', 'log', 'temp', 'cache', 'backup']):
                score -= 0.4
                reasoning_parts.append("Technical junk PDF")
        
        # Penalize technical/admin content
        junk_indicators = ['debug', 'admin', 'internal', '_temp', 'cache', 'log', 'api/v', 'ajax']
        for term in junk_indicators:
            if term in text:
                score -= 0.3
                reasoning_parts.append(f"Contains junk indicator: {term}")
                break
        
        # URL structure analysis
        if '/business/' in url or '/commercial/' in url or '/corporate/' in url:
            score += 0.2
            reasoning_parts.append("Business/commercial content path")
            
        if any(pattern in url for pattern in ['/404', '/error', '/test', '/dev']):
            score -= 0.5
            reasoning_parts.append("Error/test page pattern")
        
        # Normalize score
        final_score = max(0.0, min(1.0, score))
        is_worthy = final_score >= 0.5  # Lower threshold - more permissive for demo content
        
        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "Default scoring applied"
        
        return ClassificationResult(
            is_worthy=is_worthy,
            confidence=final_score,
            reasoning=f"Heuristic: {reasoning}",
            method_used="heuristic"
        )

class AIContentClassifier:
    """AI-powered content classifier for demo worthiness"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo", 
                 cache_dir: Optional[Path] = None):
        self.api_key = api_key
        self.model = model
        self.logger = logging.getLogger(__name__)
        self.fallback_classifier = HeuristicClassifier()
        
        # Simple cache for repeated URLs
        self.cache_dir = cache_dir or Path("output/ai_cache")
        self.cache_dir.mkdir(exist_ok=True, parents=True)
        self.cache = {}
        self._load_cache()
        
        # Rate limiting
        self.last_api_call = 0
        self.min_api_interval = 1.0  # seconds between API calls
        
    def _load_cache(self):
        """Load cached classifications"""
        cache_file = self.cache_dir / "classification_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    self.cache = json.load(f)
                self.logger.info(f"Loaded {len(self.cache)} cached classifications")
            except Exception as e:
                self.logger.warning(f"Could not load cache: {e}")
                self.cache = {}
    
    def _save_cache(self):
        """Save classification cache"""
        cache_file = self.cache_dir / "classification_cache.json"
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.warning(f"Could not save cache: {e}")
    
    def _get_cache_key(self, url: str, content: str, title: str) -> str:
        """Generate cache key for URL + content"""
        content_hash = hashlib.md5(f"{url}:{title}:{content[:500]}".encode()).hexdigest()
        return content_hash
    
    async def _call_ai_api(self, prompt: str) -> Tuple[bool, float, str]:
        """Call OpenAI API for content classification"""
        try:
            import openai
        except ImportError:
            raise Exception("openai package not installed. Install with: pip install openai")
        
        if not self.api_key or not self.api_key.startswith('sk-'):
            raise Exception("Invalid or missing OpenAI API key")
        
        client = openai.AsyncOpenAI(api_key=self.api_key)
        
        try:
            response = await client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert at determining if web content is valuable for business demos. Respond with WORTHY: true/false, CONFIDENCE: 0.0-1.0, REASONING: brief explanation."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=150,
                temperature=0.1
            )
            
            content = response.choices[0].message.content.strip()
            self.logger.info(f"OpenAI response: {content}")  # Debug logging
            
            # Parse the response more safely
            is_worthy = True  # default to worthy
            confidence = 0.7  # default confidence
            reasoning = content  # use full response as reasoning
            
            try:
                # Look for WORTHY: true/false - be more explicit about parsing
                if "worthy:" in content.lower():
                    worthy_part = content.lower().split("worthy:")[1].strip()
                    # Extract just the first word after "worthy:"
                    worthy_word = worthy_part.split()[0] if worthy_part.split() else ""
                    
                    if worthy_word in ['false', 'no', '0']:
                        is_worthy = False
                        self.logger.info(f"Parsed WORTHY as FALSE from: {worthy_word}")
                    elif worthy_word in ['true', 'yes', '1']:
                        is_worthy = True  
                        self.logger.info(f"Parsed WORTHY as TRUE from: {worthy_word}")
                    else:
                        self.logger.warning(f"Unclear WORTHY value: {worthy_word}, defaulting to TRUE")
                
                # Look for CONFIDENCE: number
                if "confidence:" in content.lower():
                    try:
                        conf_line = content.lower().split("confidence:")[1].strip()
                        # Extract first number found
                        import re
                        conf_match = re.search(r'(\d*\.?\d+)', conf_line)
                        if conf_match:
                            confidence = float(conf_match.group(1))
                            # Ensure confidence is in 0-1 range
                            if confidence > 1.0:
                                confidence = confidence / 100.0
                            self.logger.info(f"Parsed CONFIDENCE as {confidence} from: {conf_match.group(1)}")
                    except (ValueError, IndexError) as e:
                        self.logger.warning(f"Failed to parse confidence: {e}")
                        pass  # Keep default
                
                # Extract reasoning (everything after REASONING:)
                if "reasoning:" in content.lower():
                    try:
                        reasoning = content.split("reasoning:", 1)[1].strip()
                        if not reasoning:
                            reasoning = content
                    except IndexError:
                        pass  # Keep full content as reasoning
                        
            except Exception as parse_error:
                self.logger.warning(f"Failed to parse OpenAI response: {parse_error}")
                # Use simple heuristic on the response content
                response_lower = content.lower()
                if any(word in response_lower for word in ['not worthy', 'not valuable', 'skip', 'filter', 'exclude']):
                    is_worthy = False
                    confidence = 0.3
                else:
                    is_worthy = True
                    confidence = 0.7
                reasoning = f"Parsed from AI response: {content}"
            
            # Final debug logging
            self.logger.info(f"Final AI result: WORTHY={is_worthy}, CONFIDENCE={confidence}")
            
            return is_worthy, confidence, reasoning
            
        except openai.RateLimitError as e:
            raise Exception(f"OpenAI rate limit exceeded: {e}")
        except openai.AuthenticationError as e:
            raise Exception(f"OpenAI authentication failed: {e}")
        except Exception as e:
            raise Exception(f"OpenAI API call failed: {e}")
    
    async def classify_content(self, url: str, content: str = "", title: str = "") -> ClassificationResult:
        """Main classification method"""
        
        # Check cache first
        cache_key = self._get_cache_key(url, content, title)
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            return ClassificationResult(
                is_worthy=cached['is_worthy'],
                confidence=cached['confidence'], 
                reasoning=cached['reasoning'],
                method_used="cache"
            )
        
        # Try AI classification if API key available
        if self.api_key:
            try:
                # Rate limiting
                import time
                now = time.time()
                if now - self.last_api_call < self.min_api_interval:
                    await asyncio.sleep(self.min_api_interval - (now - self.last_api_call))
                
                self.last_api_call = time.time()
                
                # Prepare AI prompt
                prompt = self._create_ai_prompt(url, content, title)
                is_worthy, confidence, reasoning = await self._call_ai_api(prompt)
                
                result = ClassificationResult(
                    is_worthy=is_worthy,
                    confidence=confidence,
                    reasoning=f"AI: {reasoning}",
                    method_used="ai"
                )
                
                # Cache the result
                self.cache[cache_key] = {
                    'is_worthy': is_worthy,
                    'confidence': confidence,
                    'reasoning': reasoning
                }
                self._save_cache()
                
                return result
                
            except Exception as e:
                self.logger.warning(f"AI classification failed for {url}: {e}")
                # Fall through to heuristic
        
        # Fallback to enhanced heuristic
        return self.fallback_classifier.classify(url, content, title)
    
    def _create_ai_prompt(self, url: str, content: str, title: str) -> str:
        """Create AI prompt for content classification"""
        content_preview = content[:1000] if content else "No content provided"
        
        return f"""
        Analyze this content for CLIENT DEMO value. This is for showcasing a website to potential clients/customers:
        URL: {url}
        Title: {title}
        Content Preview: {content_preview}
        
        DEMO PERSPECTIVE: What would impress someone evaluating this website/service?
        
        HIGH VALUE for demos:
        - Products, services, solutions (core business offerings)
        - Customer support features (contact methods, help systems, FAQs)
        - User experience features (app functionality, digital tools, convenience)
        - Business information (company info, case studies, success stories)
        - Educational content (guides, resources, how-to information)
        - About pages, investor info, newsroom (credibility and transparency)
        - Main navigation and key landing pages
        - ANY content that shows capabilities, features, or customer value
        
        LOW VALUE for demos:
        - Technical/admin content (API docs, debug pages, internal tools)
        - Legal boilerplate (terms, privacy - unless specifically requested)
        - Error pages, maintenance pages
        - Duplicate/spam content
        - Pure navigation with no content
        
        BIAS TOWARD INCLUSION: When in doubt, include it. Better to have too much demo content than miss valuable features.
        
        Respond with:
        WORTHY: true/false
        CONFIDENCE: 0.0-1.0
        REASONING: brief explanation focusing on demo/client value
        """

# Convenience functions for easy integration
async def classify_url_for_demo(url: str, content: str = "", title: str = "", 
                              api_key: Optional[str] = None) -> bool:
    """Quick classification function that returns just true/false"""
    classifier = AIContentClassifier(api_key=api_key)
    result = await classifier.classify_content(url, content, title)
    return result.is_worthy

def classify_url_sync(url: str, content: str = "", title: str = "") -> bool:
    """Synchronous version using heuristics only"""
    classifier = HeuristicClassifier()
    result = classifier.classify(url, content, title)
    return result.is_worthy