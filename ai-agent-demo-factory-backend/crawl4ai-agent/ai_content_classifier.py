"""
AI Content Classifier for Demo Worthiness
Two-stage system: Site type detection + site-specific content evaluation
"""
import asyncio
import logging
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from enum import Enum

class BusinessSiteType(Enum):
    """Business-focused site categories for demo content evaluation"""
    BANKING = "banking"
    ECOMMERCE = "ecommerce" 
    NEWS = "news"
    CORPORATE = "corporate"
    EDUCATIONAL = "educational"
    HEALTHCARE = "healthcare"
    GOVERNMENT = "government"
    NON_PROFIT = "nonprofit"
    ENTERTAINMENT = "entertainment"
    REAL_ESTATE = "realestate"
    LEGAL = "legal"
    RESTAURANT = "restaurant"
    TECHNOLOGY = "technology"
    UNKNOWN = "unknown"

@dataclass
class ClassificationResult:
    """Result of AI content classification"""
    is_worthy: bool
    confidence: float  # 0.0 to 1.0
    reasoning: str
    method_used: str  # "ai", "heuristic", "cache"
    
class BusinessSiteDetector:
    """Detects business site type using heuristics for targeted content evaluation"""
    
    # Enhanced hybrid patterns: phrases (high confidence) + keywords (supporting evidence)
    ENHANCED_BUSINESS_PATTERNS = {
        BusinessSiteType.BANKING: {
            "high_confidence_phrases": [  # 5 points each
                "online banking", "mobile banking", "account balance", "wire transfer",
                "loan application", "mortgage calculator", "investment banking", "wealth management",
                "checking account", "savings account", "credit score", "financial planning",
                "personal banking", "business banking", "commercial lending", "atm locator"
            ],
            "supporting_keywords": [  # 1 point each
                "bank", "banking", "financial", "loan", "mortgage", "credit", "investment",
                "finance", "funds", "account", "lending", "wealth", "treasury"
            ]
        },
        BusinessSiteType.ECOMMERCE: {
            "high_confidence_phrases": [  # 5 points each
                "add to cart", "shopping cart", "checkout process", "product catalog", 
                "customer reviews", "payment gateway", "shipping information", "return policy",
                "product details", "wishlist", "compare products", "order tracking",
                "online store", "product search", "shopping experience", "secure checkout"
            ],
            "supporting_keywords": [  # 1 point each
                "shop", "store", "cart", "checkout", "product", "buy", "marketplace", "retail",
                "purchase", "order", "shipping", "payment", "catalog", "inventory"
            ]
        },
        BusinessSiteType.NEWS: {
            "high_confidence_phrases": [  # 5 points each
                "breaking news", "news headlines", "current events", "news article",
                "press release", "editorial content", "investigative journalism", "news feed",
                "local news", "world news", "news archive", "news categories",
                "live updates", "news analysis", "reporter byline", "news coverage"
            ],
            "supporting_keywords": [  # 1 point each
                "news", "article", "journalism", "reporter", "editorial", "headline",
                "story", "press", "media", "coverage", "update", "breaking"
            ]
        },
        BusinessSiteType.HEALTHCARE: {
            "high_confidence_phrases": [  # 5 points each
                "medical services", "patient care", "health information", "medical practice",
                "healthcare provider", "patient portal", "appointment scheduling", "health records",
                "medical specialties", "treatment options", "health insurance", "wellness programs",
                "medical equipment", "clinical services", "health screening", "patient resources"
            ],
            "supporting_keywords": [  # 1 point each
                "health", "medical", "doctor", "clinic", "hospital", "dentist", "pharmacy",
                "patient", "treatment", "care", "wellness", "medicine", "healthcare"
            ]
        },
        BusinessSiteType.EDUCATIONAL: {
            "high_confidence_phrases": [  # 5 points each
                "course catalog", "academic programs", "student services", "faculty profiles",
                "admission requirements", "online learning", "educational resources", "degree programs",
                "class schedule", "student portal", "academic calendar", "learning management",
                "continuing education", "professional development", "certification programs", "campus life"
            ],
            "supporting_keywords": [  # 1 point each
                "school", "university", "course", "learning", "education", "training",
                "student", "academic", "program", "degree", "certification", "campus"
            ]
        },
        BusinessSiteType.GOVERNMENT: {
            "high_confidence_phrases": [  # 5 points each
                "government services", "public records", "citizen services", "government programs",
                "elected officials", "public information", "government forms", "tax information",
                "public safety", "community services", "government meetings", "policy information",
                "public resources", "government contact", "municipal services", "federal agency"
            ],
            "supporting_keywords": [  # 1 point each
                "government", "gov", "federal", "state", "municipal", "council", "public",
                "citizen", "official", "agency", "department", "policy", "service"
            ]
        },
        BusinessSiteType.LEGAL: {
            "high_confidence_phrases": [  # 5 points each
                "legal services", "law firm", "attorney profiles", "practice areas",
                "legal consultation", "case results", "legal resources", "legal expertise",
                "court representation", "legal advice", "law practice", "legal specialization",
                "client testimonials", "legal experience", "attorney credentials", "legal process"
            ],
            "supporting_keywords": [  # 1 point each
                "law", "legal", "attorney", "lawyer", "court", "justice", "litigation",
                "counsel", "practice", "firm", "case", "representation", "advice"
            ]
        },
        BusinessSiteType.REAL_ESTATE: {
            "high_confidence_phrases": [  # 5 points each
                "property listings", "real estate agent", "home search", "property management",
                "market analysis", "real estate services", "home valuation", "property details",
                "neighborhood information", "buying process", "selling process", "real estate expertise",
                "property investment", "home inspection", "mortgage assistance", "property photos"
            ],
            "supporting_keywords": [  # 1 point each
                "property", "realestate", "homes", "rent", "housing", "agent",
                "listings", "market", "buy", "sell", "investment", "residential"
            ]
        },
        BusinessSiteType.RESTAURANT: {
            "high_confidence_phrases": [  # 5 points each
                "restaurant menu", "dining experience", "food service", "chef specialties",
                "restaurant location", "table reservation", "catering services", "special events",
                "restaurant hours", "food ordering", "restaurant atmosphere", "culinary team",
                "private dining", "takeout menu", "restaurant reviews", "wine selection"
            ],
            "supporting_keywords": [  # 1 point each
                "restaurant", "food", "dining", "menu", "cafe", "bar", "catering",
                "chef", "cuisine", "meal", "reservation", "takeout", "delivery"
            ]
        },
        BusinessSiteType.TECHNOLOGY: {
            "high_confidence_phrases": [  # 5 points each
                "software solutions", "technology platform", "cloud services", "api documentation",
                "technical support", "software development", "system integration", "enterprise software",
                "data analytics", "artificial intelligence", "machine learning", "cybersecurity solutions",
                "scientific instruments", "life sciences", "biotechnology solutions", "engineering services",
                "research development", "innovation center", "technology consulting", "digital transformation"
            ],
            "supporting_keywords": [  # 1 point each
                "tech", "software", "saas", "api", "cloud", "app", "platform", "digital",
                "system", "solution", "data", "analytics", "ai", "ml", "cyber", "security",
                "scientific", "instruments", "diagnostics", "biotechnology", "engineering", "innovation"
            ]
        },
        BusinessSiteType.NON_PROFIT: {
            "high_confidence_phrases": [  # 5 points each
                "nonprofit organization", "charitable foundation", "volunteer opportunities", "donation process",
                "community programs", "social impact", "fundraising events", "nonprofit mission",
                "charitable giving", "volunteer services", "community outreach", "social cause",
                "nonprofit board", "impact stories", "charitable programs", "community support"
            ],
            "supporting_keywords": [  # 1 point each
                "nonprofit", "charity", "foundation", "donate", "volunteer", "cause",
                "community", "impact", "mission", "giving", "support", "social"
            ]
        },
        BusinessSiteType.ENTERTAINMENT: {
            "high_confidence_phrases": [  # 5 points each
                "entertainment content", "streaming service", "movie catalog", "music platform",
                "gaming platform", "entertainment news", "artist profiles", "content library",
                "subscription service", "entertainment events", "live streaming", "digital content",
                "media platform", "entertainment industry", "content creation", "user experience"
            ],
            "supporting_keywords": [  # 1 point each
                "entertainment", "movie", "music", "game", "streaming", "content",
                "artist", "show", "video", "audio", "platform", "digital", "media"
            ]
        },
        BusinessSiteType.CORPORATE: {
            "high_confidence_phrases": [  # 5 points each
                "corporate services", "business solutions", "company overview", "corporate team",
                "business consulting", "enterprise solutions", "corporate clients", "professional services",
                "company leadership", "business strategy", "corporate culture", "industry expertise",
                "client success", "business process", "corporate responsibility", "company values"
            ],
            "supporting_keywords": [  # 1 point each
                "corporate", "business", "company", "enterprise", "professional", "services",
                "solutions", "consulting", "strategy", "leadership", "team", "clients"
            ]
        }
    }
    
    def detect_site_type(self, url: str, title: str = "", content: str = "") -> BusinessSiteType:
        """
        Detect business site type using enhanced hybrid phrase + keyword scoring system
        High-confidence phrases (5pts) + supporting keywords (1pt) + context weighting
        """
        url_lower = url.lower()
        title_lower = title.lower() 
        content_lower = content.lower()
        
        # Initialize scores for each site type
        scores = {site_type: 0 for site_type in BusinessSiteType}
        
        # Score each site type based on hybrid patterns
        for site_type, pattern_dict in self.ENHANCED_BUSINESS_PATTERNS.items():
            # High-confidence phrase matching (5 points each)
            for phrase in pattern_dict["high_confidence_phrases"]:
                # URL matches get highest weight (3x multiplier)
                if phrase in url_lower:
                    scores[site_type] += 5 * 3  # 15 points
                # Title matches get medium weight (2x multiplier)  
                elif phrase in title_lower:
                    scores[site_type] += 5 * 2  # 10 points
                # Content matches get base weight
                elif phrase in content_lower:
                    scores[site_type] += 5      # 5 points
            
            # Supporting keyword matching (1 point each)
            for keyword in pattern_dict["supporting_keywords"]:
                # URL matches get highest weight (3x multiplier)
                if keyword in url_lower:
                    scores[site_type] += 1 * 3  # 3 points
                # Title matches get medium weight (2x multiplier)
                elif keyword in title_lower:
                    scores[site_type] += 1 * 2  # 2 points
                # Content matches get base weight  
                elif keyword in content_lower:
                    scores[site_type] += 1      # 1 point
        
        # Find the site type with highest score
        max_score = max(scores.values()) if scores.values() else 0
        
        # Require minimum threshold for confidence (at least one phrase or multiple keywords)
        if max_score >= 3:  # At least one keyword in URL or multiple matches
            winning_types = [site_type for site_type, score in scores.items() if score == max_score]
            
            # Single clear winner - no tiebreaking needed
            if len(winning_types) == 1:
                return winning_types[0]
            
            # Multiple winners - use confidence-based tiebreaking instead of arbitrary priority
            # Find the winner with the most high-confidence phrase matches
            phrase_counts = {}
            for site_type in winning_types:
                phrase_count = 0
                pattern_dict = self.ENHANCED_BUSINESS_PATTERNS[site_type]
                for phrase in pattern_dict["high_confidence_phrases"]:
                    if phrase in url_lower or phrase in title_lower or phrase in content_lower:
                        phrase_count += 1
                phrase_counts[site_type] = phrase_count
            
            # Return the site type with most phrase matches
            max_phrases = max(phrase_counts.values())
            if max_phrases > 0:
                phrase_winners = [st for st, count in phrase_counts.items() if count == max_phrases]
                if len(phrase_winners) == 1:
                    return phrase_winners[0]
                # If still tied on phrases, return first one (rare case)
                return phrase_winners[0]
            
            # Fallback: return first winning type (should be very rare now)
            return winning_types[0]
        
        # Fallback to domain extension analysis
        if url_lower.endswith('.edu') or 'university' in title_lower or 'college' in title_lower:
            return BusinessSiteType.EDUCATIONAL
        elif url_lower.endswith('.gov') or '.gov/' in url_lower:
            return BusinessSiteType.GOVERNMENT
        elif url_lower.endswith('.org') or 'nonprofit' in content_lower:
            return BusinessSiteType.NON_PROFIT
        
        # Secondary content analysis for low-score cases
        combined_text = f"{url_lower} {title_lower} {content_lower}"
        if any(word in combined_text for word in ["company", "business", "services", "solutions", "corporate"]):
            return BusinessSiteType.CORPORATE
        
        return BusinessSiteType.UNKNOWN
    
    def detect_site_type_with_confidence(self, url: str, title: str = "", content: str = "") -> dict:
        """
        Enhanced detection that returns site type with confidence and score details
        Uses hybrid phrase + keyword system with detailed match tracking
        """
        url_lower = url.lower()
        title_lower = title.lower() 
        content_lower = content.lower()
        
        # Initialize scores for each site type
        scores = {site_type: 0 for site_type in BusinessSiteType}
        match_details = {site_type: [] for site_type in BusinessSiteType}
        phrase_counts = {site_type: 0 for site_type in BusinessSiteType}
        
        # Score each site type based on hybrid patterns
        for site_type, pattern_dict in self.ENHANCED_BUSINESS_PATTERNS.items():
            # High-confidence phrase matching (5 points each)
            for phrase in pattern_dict["high_confidence_phrases"]:
                # URL matches get highest weight (3x multiplier)
                if phrase in url_lower:
                    scores[site_type] += 5 * 3  # 15 points
                    match_details[site_type].append(f"URL_PHRASE:{phrase}")
                    phrase_counts[site_type] += 1
                # Title matches get medium weight (2x multiplier)  
                elif phrase in title_lower:
                    scores[site_type] += 5 * 2  # 10 points
                    match_details[site_type].append(f"TITLE_PHRASE:{phrase}")
                    phrase_counts[site_type] += 1
                # Content matches get base weight
                elif phrase in content_lower:
                    scores[site_type] += 5      # 5 points
                    match_details[site_type].append(f"CONTENT_PHRASE:{phrase}")
                    phrase_counts[site_type] += 1
            
            # Supporting keyword matching (1 point each)
            for keyword in pattern_dict["supporting_keywords"]:
                # URL matches get highest weight (3x multiplier)
                if keyword in url_lower:
                    scores[site_type] += 1 * 3  # 3 points
                    match_details[site_type].append(f"URL_KEYWORD:{keyword}")
                # Title matches get medium weight (2x multiplier)
                elif keyword in title_lower:
                    scores[site_type] += 1 * 2  # 2 points
                    match_details[site_type].append(f"TITLE_KEYWORD:{keyword}")
                # Content matches get base weight  
                elif keyword in content_lower:
                    scores[site_type] += 1      # 1 point
                    match_details[site_type].append(f"CONTENT_KEYWORD:{keyword}")
        
        # Find the site type with highest score
        max_score = max(scores.values()) if scores.values() else 0
        
        # Apply same logic as detect_site_type but with more detail
        if max_score >= 3:
            winning_types = [site_type for site_type, score in scores.items() if score == max_score]
            
            if len(winning_types) == 1:
                final_type = winning_types[0]
            else:
                # Use confidence-based tiebreaking (same as detect_site_type)
                max_phrases = max(phrase_counts[st] for st in winning_types)
                if max_phrases > 0:
                    phrase_winners = [st for st in winning_types if phrase_counts[st] == max_phrases]
                    final_type = phrase_winners[0]  # Take first if still tied
                else:
                    final_type = winning_types[0]  # Fallback to first winner
        else:
            # Apply fallback logic
            final_type = self.detect_site_type(url, title, content)
            # Update max_score if fallback found something
            if final_type != BusinessSiteType.UNKNOWN:
                max_score = max(1, max_score)  # At least 1 for fallback detection
        
        # Enhanced confidence calculation based on score and phrase matches
        phrase_match_count = phrase_counts.get(final_type, 0)
        
        if max_score >= 10 or phrase_match_count >= 2:  # Multiple phrases or strong URL phrase
            confidence = "HIGH"
        elif max_score >= 5 or phrase_match_count >= 1:  # Single phrase match
            confidence = "MEDIUM" 
        elif max_score >= 3:  # Multiple keywords or URL keyword
            confidence = "LOW"
        else:
            confidence = "FALLBACK"
        
        return {
            'site_type': final_type,
            'confidence': confidence,
            'score': max_score,
            'phrase_matches': phrase_match_count,
            'all_scores': scores,
            'matches': match_details[final_type] if final_type in match_details else []
        }

class HeuristicClassifier:
    """Fallback classifier using enhanced heuristic rules"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.site_detector = BusinessSiteDetector()
        
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
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini", 
                 cache_dir: Optional[Path] = None):
        self.api_key = api_key
        self.model = model
        self.logger = logging.getLogger(__name__)
        self.site_detector = BusinessSiteDetector()
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
                    # Extract just the first word after "worthy:" and clean punctuation
                    worthy_word = worthy_part.split()[0] if worthy_part.split() else ""
                    worthy_word = worthy_word.replace(',', '').replace('.', '').replace(';', '')
                    
                    if worthy_word in ['false', 'no', '0']:
                        is_worthy = False
                        self.logger.info(f"Parsed WORTHY as FALSE from: {worthy_word}")
                    elif worthy_word in ['true', 'yes', '1']:
                        is_worthy = True  
                        self.logger.info(f"Parsed WORTHY as TRUE from: {worthy_word}")
                    else:
                        self.logger.warning(f"Unclear WORTHY value: {worthy_word}, defaulting to FALSE for safety")
                        is_worthy = False  # Default to FALSE for safety
                
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
        """Create site-specific AI prompt for content classification"""
        content_preview = content[:800] if content else "No content provided"
        
        # Detect site type first
        site_type = self.site_detector.detect_site_type(url, title, content)
        # Get detailed detection info for debugging
        detection_info = self.site_detector.detect_site_type_with_confidence(url, title, content)
        site_type = detection_info['site_type']
        confidence = detection_info['confidence'] 
        score = detection_info['score']
        
        self.logger.info(f"🔍 Site type detected for {url}: {site_type.value} (confidence: {confidence}, score: {score})")
        
        # Get site-specific prompt
        return self._get_site_specific_prompt(site_type, url, title, content_preview)
    
    def _get_site_specific_prompt(self, site_type: BusinessSiteType, url: str, title: str, content: str) -> str:
        """Generate specialized prompts based on detected site type"""
        
        base_info = f"""
        URL: {url}
        Title: {title}
        Content Preview: {content}
        Site Type: {site_type.value}
        """
        
        if site_type == BusinessSiteType.BANKING:
            return base_info + """
        BANKING SITE DEMO EVALUATION:
        This is a financial/banking website. Focus on professional demonstration value.
        
        HIGH VALUE for banking demos:
        - Core banking services (accounts, loans, mortgages, credit cards)
        - Business banking solutions (commercial lending, corporate accounts)
        - Digital banking features (online banking, mobile apps, security)
        - Investment and financial advisory services
        - Customer support and branch information
        - About us, careers, investor relations (credibility)
        
        LOW VALUE for banking demos:
        - Legal compliance pages (unless main regulatory info)
        - Technical documentation, API docs
        - Individual rate pages without context
        - Generic marketing fluff without substance
        
        Respond with: WORTHY: true/false, CONFIDENCE: 0.0-1.0, REASONING: brief explanation
        """
        
        elif site_type == BusinessSiteType.ECOMMERCE:
            return base_info + """
        E-COMMERCE SITE DEMO EVALUATION:
        This is an online retail/shopping website. Focus on shopping experience and features.
        
        HIGH VALUE for e-commerce demos:
        - Product categories and main collections (not individual products)
        - Shopping features (cart, checkout, search, filters)
        - Customer service (returns, shipping, support)
        - About us, company story, brand information
        - Customer reviews and testimonials systems
        - Account/profile management features
        
        LOW VALUE for e-commerce demos:
        - Individual product pages (unless showcasing key products)
        - Specific pricing without context
        - Legal pages, shipping details only
        - Duplicate product variants
        
        Respond with: WORTHY: true/false, CONFIDENCE: 0.0-1.0, REASONING: brief explanation
        """
        
        elif site_type == BusinessSiteType.CORPORATE:
            return base_info + """
        CORPORATE WEBSITE DEMO EVALUATION:
        This is a business/corporate website. Focus on company capabilities and professionalism.
        
        HIGH VALUE for corporate demos:
        - Services and solutions offered
        - Company information and leadership
        - Case studies, client success stories
        - Industry expertise and insights
        - Contact information and locations
        - Careers and company culture
        
        LOW VALUE for corporate demos:
        - Legal compliance pages only
        - Press releases without context
        - Internal employee resources
        - Generic contact forms without content
        
        Respond with: WORTHY: true/false, CONFIDENCE: 0.0-1.0, REASONING: brief explanation
        """
        
        
        elif site_type == BusinessSiteType.TECHNOLOGY:
            return base_info + """
        TECHNOLOGY & SCIENCE COMPANY DEMO EVALUATION:
        This is a technology, science, or engineering company. Evaluate for professional demonstration value across all tech sectors.
        
        HIGH VALUE for technology/science demos:
        - Products, instruments, and solutions (software, hardware, scientific equipment)
        - Technology platforms, services, and capabilities
        - Research & development innovations and breakthroughs
        - Industry applications (life sciences, diagnostics, chemical, medical, manufacturing)
        - Case studies, customer success stories, and applications
        - Scientific publications, whitepapers, and technical resources
        - About us, leadership, expertise, and company capabilities
        - Support, training, and service offerings
        
        LOW VALUE for technology demos:
        - Pure API documentation without business context
        - Legal compliance pages only
        - Internal developer tools without explanation
        - Generic marketing fluff without technical substance
        
        STRONG BIAS TOWARD INCLUSION: Technology and science companies should showcase their innovations and capabilities.
        Most technical content has demonstration value.
        
        Respond with: WORTHY: true/false, CONFIDENCE: 0.0-1.0, REASONING: brief explanation
        """
        
        elif site_type == BusinessSiteType.NEWS:
            return base_info + """
        NEWS & MEDIA SITE DEMO EVALUATION:
        This is a news, media, or journalism website. Focus on content diversity and editorial quality.
        
        HIGH VALUE for news/media demos:
        - Diverse article topics and news categories (politics, business, sports, lifestyle, technology)
        - Editorial sections, opinion pieces, and investigative journalism
        - Multimedia content (videos, podcasts, interactive content)
        - Breaking news and current events coverage
        - Local news and community coverage
        - About us, editorial team, and journalism standards
        - Archive sections showing content breadth
        
        LOW VALUE for news demos:
        - Duplicate or very similar stories
        - Purely promotional content without news value
        - Outdated news without historical significance
        - Pure social media feeds without editorial content
        
        MODERATE BIAS TOWARD INCLUSION: Include diverse content types that showcase editorial range and quality.
        
        Respond with: WORTHY: true/false, CONFIDENCE: 0.0-1.0, REASONING: brief explanation
        """
        
        
        elif site_type == BusinessSiteType.EDUCATIONAL:
            return base_info + """
        EDUCATIONAL INSTITUTION DEMO EVALUATION:
        This is a school, university, training program, or educational service. Focus on educational offerings and institutional credibility.
        
        HIGH VALUE for educational demos:
        - Course catalogs, programs, and curricula
        - Faculty profiles, expertise, and credentials
        - Admission information and requirements
        - Research programs and academic achievements
        - Student services and campus resources
        - Educational resources and learning materials
        - About the institution, accreditation, and history
        
        LOW VALUE for educational demos:
        - Internal student portals and grade systems
        - Administrative forms without context
        - Purely promotional content without educational substance
        - Generic contact forms without program information
        
        MODERATE BIAS TOWARD INCLUSION: Educational content that shows institutional quality and offerings is valuable.
        
        Respond with: WORTHY: true/false, CONFIDENCE: 0.0-1.0, REASONING: brief explanation
        """
        
        elif site_type == BusinessSiteType.HEALTHCARE:
            return base_info + """
        HEALTHCARE PROVIDER DEMO EVALUATION:
        This is a healthcare provider, medical practice, hospital, or health services website. Focus on patient care and medical expertise.
        
        HIGH VALUE for healthcare demos:
        - Medical services and specialties offered
        - Provider profiles, credentials, and expertise
        - Patient resources and health education
        - Treatment options and medical procedures
        - Facility information and technology capabilities
        - Insurance and appointment information
        - Health and wellness resources
        
        LOW VALUE for healthcare demos:
        - Patient portals and private medical information
        - Billing and administrative systems
        - Purely regulatory compliance pages without patient value
        - Generic appointment forms without service context
        
        MODERATE BIAS TOWARD INCLUSION: Healthcare information that helps patients understand services is valuable.
        
        Respond with: WORTHY: true/false, CONFIDENCE: 0.0-1.0, REASONING: brief explanation
        """
        
        elif site_type == BusinessSiteType.GOVERNMENT:
            return base_info + """
        GOVERNMENT SITE DEMO EVALUATION:
        This is a government agency, public service, or official website. Focus on citizen services and public information.
        
        HIGH VALUE for government demos:
        - Public services and citizen resources
        - Policy information and government programs
        - Contact information and office locations
        - Public records and transparency information
        - Elected officials and department leadership
        - Community resources and public programs
        - Forms and processes for citizen services
        
        LOW VALUE for government demos:
        - Internal administrative tools
        - Purely bureaucratic processes without citizen context
        - Outdated information without historical significance
        - Generic contact information without service details
        
        MODERATE BIAS TOWARD INCLUSION: Government services and citizen resources are important to showcase.
        
        Respond with: WORTHY: true/false, CONFIDENCE: 0.0-1.0, REASONING: brief explanation
        """
        
        elif site_type == BusinessSiteType.NON_PROFIT:
            return base_info + """
        NON-PROFIT ORGANIZATION DEMO EVALUATION:
        This is a charity, foundation, advocacy group, or non-profit organization. Focus on mission and impact.
        
        HIGH VALUE for non-profit demos:
        - Mission, vision, and cause information
        - Programs and services offered
        - Impact stories and success metrics
        - Volunteer opportunities and ways to help
        - Donation information and funding transparency
        - About the organization, leadership, and history
        - Community involvement and partnerships
        
        LOW VALUE for non-profit demos:
        - Internal member areas and private content
        - Purely fundraising appeals without mission context
        - Administrative content without public relevance
        - Generic donation forms without cause explanation
        
        STRONG BIAS TOWARD INCLUSION: Non-profits want to showcase their mission and impact broadly.
        
        Respond with: WORTHY: true/false, CONFIDENCE: 0.0-1.0, REASONING: brief explanation
        """
        
        elif site_type == BusinessSiteType.ENTERTAINMENT:
            return base_info + """
        ENTERTAINMENT SITE DEMO EVALUATION:
        This is an entertainment, media, gaming, or content website. Focus on content offerings and user experience.
        
        HIGH VALUE for entertainment demos:
        - Content offerings (shows, movies, games, music, books)
        - Artist profiles and entertainment personalities
        - Event listings and entertainment news
        - Platform features and user experience
        - Reviews, ratings, and community features
        - Subscription or access information
        - About the platform and content strategy
        
        LOW VALUE for entertainment demos:
        - User account areas and personal settings
        - Purely promotional content without substance
        - Generic marketing without content details
        - Technical streaming information without context
        
        MODERATE BIAS TOWARD INCLUSION: Entertainment content that showcases offerings and experience is valuable.
        
        Respond with: WORTHY: true/false, CONFIDENCE: 0.0-1.0, REASONING: brief explanation
        """
        
        elif site_type == BusinessSiteType.REAL_ESTATE:
            return base_info + """
        REAL ESTATE SITE DEMO EVALUATION:
        This is a real estate agency, property website, or real estate services. Focus on property services and market expertise.
        
        HIGH VALUE for real estate demos:
        - Property listings and market information
        - Agent profiles and real estate expertise
        - Market analysis and neighborhood information
        - Real estate services offered (buying, selling, property management)
        - Company information and track record
        - Client testimonials and success stories
        - Contact information and consultation process
        
        LOW VALUE for real estate demos:
        - Individual property details without broader context
        - Purely transactional forms and MLS data dumps
        - Generic property photos without descriptive content
        - Administrative tools without client relevance
        
        MODERATE BIAS TOWARD INCLUSION: Real estate content that shows market knowledge and services is valuable.
        
        Respond with: WORTHY: true/false, CONFIDENCE: 0.0-1.0, REASONING: brief explanation
        """
        
        elif site_type == BusinessSiteType.LEGAL:
            return base_info + """
        LEGAL SERVICES DEMO EVALUATION:
        This is a law firm, attorney, or legal services website. Focus on legal expertise and practice areas.
        
        HIGH VALUE for legal demos:
        - Practice areas and legal specializations
        - Attorney profiles, credentials, and experience
        - Legal resources and educational content
        - Case types handled and legal expertise
        - Firm information and legal philosophy
        - Client testimonials and case results (where appropriate)
        - Contact information and consultation process
        
        LOW VALUE for legal demos:
        - Client portals and confidential case information
        - Generic legal disclaimers without substantive content
        - Purely administrative forms without practice context
        - Legal jargon without client-facing explanation
        
        MODERATE BIAS TOWARD INCLUSION: Legal content that demonstrates expertise and helps clients is valuable.
        
        Respond with: WORTHY: true/false, CONFIDENCE: 0.0-1.0, REASONING: brief explanation
        """
        
        elif site_type == BusinessSiteType.RESTAURANT:
            return base_info + """
        RESTAURANT & FOOD SERVICE DEMO EVALUATION:
        This is a restaurant, food service, catering, or hospitality website. Focus on dining experience and food offerings.
        
        HIGH VALUE for restaurant demos:
        - Menus, food offerings, and specialties
        - Restaurant information, atmosphere, and dining experience
        - Chef profiles and culinary expertise
        - Location, hours, and contact information
        - Catering and special event services
        - Reviews, awards, and recognition
        - Reservation and ordering information
        
        LOW VALUE for restaurant demos:
        - Internal ordering systems without menu context
        - Generic promotional content without food/service details
        - Administrative content without customer relevance
        - Purely transactional pages without dining information
        
        STRONG BIAS TOWARD INCLUSION: Restaurants want to showcase their food, atmosphere, and services.
        
        Respond with: WORTHY: true/false, CONFIDENCE: 0.0-1.0, REASONING: brief explanation
        """
        
        else:  # UNKNOWN, NEWS, HEALTHCARE, GOVERNMENT, etc.
            return base_info + """
        GENERAL SITE DEMO EVALUATION:
        Evaluate this content for demonstration value. For simple/minimal sites, be very permissive.
        
        HIGH VALUE for demos:
        - Main services, products, or information offered
        - About us, company/organization information
        - Key features or capabilities
        - Contact information and locations
        - Educational or informational content
        - User-facing functionality
        - Any substantial content that shows the site's purpose
        
        LOW VALUE for demos:
        - Technical documentation or admin pages
        - Legal boilerplate without substance
        - Error or maintenance pages
        - Pure navigation without content
        
        STRONG BIAS TOWARD INCLUSION: For simple sites with minimal content, accept most pages. 
        Better to include than exclude. When in doubt, mark as WORTHY.
        
        Respond with: WORTHY: true/false, CONFIDENCE: 0.0-1.0, REASONING: brief explanation
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