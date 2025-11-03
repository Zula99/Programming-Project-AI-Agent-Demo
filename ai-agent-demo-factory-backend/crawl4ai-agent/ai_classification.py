# ai_classification.py - AI-powered content classification
import logging
from typing import Optional, Dict, Any, Tuple

# AI Classification imports
try:
    from ai_content_classifier import AIContentClassifier, HeuristicClassifier, ClassificationResult
    from ai_config import get_ai_config
    AI_AVAILABLE = True
except ImportError as e:
    AI_AVAILABLE = False
    logging.warning(f"AI classification not available: {e}")

from url_utils import is_demo_worthy_url

_ai_classifier = None  # Global classifier instance
_logger = logging.getLogger(__name__)

def get_ai_classifier(domain: Optional[str] = None) -> Optional[AIContentClassifier]:
    """Get or create an AI classifier instance, optionally domain-specific"""
    global _ai_classifier
    if not AI_AVAILABLE:
        return None

    # For domain-specific classifiers, create a new instance each time
    # (since each domain needs its own cache)
    if domain:
        try:
            config = get_ai_config()
            return AIContentClassifier(
                api_key=config.openai_api_key or config.anthropic_api_key,
                model=config.preferred_model,
                domain=domain
            )
        except Exception as e:
            _logger.warning(f"Could not initialize domain-specific AI classifier for {domain}: {e}")
            return None

    # For backwards compatibility, maintain global classifier
    if _ai_classifier is None:
        try:
            config = get_ai_config()
            _ai_classifier = AIContentClassifier(
                api_key=config.openai_api_key or config.anthropic_api_key,
                model=config.preferred_model
            )
        except Exception as e:
            _logger.warning(f"Could not initialize AI classifier: {e}")
            return None

    return _ai_classifier

async def is_demo_worthy_url_ai_cached(url: str, cost_tracker=None, domain: Optional[str] = None) -> tuple[bool, str, dict]:
    """
    Fast URL-only classification using persistent domain-specific cache for sitemap and discovered links.
    This avoids re-classifying the same URLs across different crawl sessions.

    Args:
        url: URL to classify (no content needed)
        cost_tracker: Cost tracking instance
        domain: Domain for cache organization (e.g., 'nab.com.au')

    Returns:
        (is_worthy, reason, classification_details)
    """
    classification_details = {
        'method': 'unknown',
        'confidence': 0.0,
        'reasoning': '',
        'ai_available': AI_AVAILABLE
    }

    # First, check basic technical filters (these are still useful)
    basic_worthy, basic_reason = is_demo_worthy_url(url)
    if not basic_worthy:
        classification_details.update({
            'method': 'basic_filter',
            'confidence': 0.9,
            'reasoning': f'Failed basic filter: {basic_reason}'
        })
        return False, basic_reason, classification_details

    # Try AI URL-only classification if available
    ai_classifier = get_ai_classifier(domain=domain)
    if ai_classifier:
        try:
            result: ClassificationResult = await ai_classifier.classify_url_only(url)

            # Track costs if cost_tracker provided
            if cost_tracker:
                cost_tracker.track_classification(url, result, 0)  # 0 content length for URL-only

            classification_details.update({
                'method': result.method_used,
                'confidence': result.confidence,
                'reasoning': result.reasoning
            })

            return result.is_worthy, result.reasoning if not result.is_worthy else "", classification_details

        except Exception as e:
            _logger.warning(f"AI URL-only classification failed for {url}: {e}")
            # Fall through to heuristic

    # Fallback to enhanced heuristic (better than just basic filters)
    if AI_AVAILABLE:
        try:
            heuristic_classifier = HeuristicClassifier()
            result = heuristic_classifier.classify(url, "", "")  # URL only
            classification_details.update({
                'method': result.method_used,
                'confidence': result.confidence,
                'reasoning': result.reasoning
            })

            return result.is_worthy, result.reasoning if not result.is_worthy else "", classification_details

        except Exception as e:
            _logger.warning(f"Heuristic classification failed for {url}: {e}")

    # Final fallback to basic filters (already passed above)
    classification_details.update({
        'method': 'basic_only',
        'confidence': 0.7,
        'reasoning': 'Only basic filtering applied'
    })

    return True, "", classification_details

async def is_demo_worthy_url_ai(url: str, content: str = "", title: str = "", cost_tracker=None, classification_cache=None, domain: Optional[str] = None) -> tuple[bool, str, dict]:
    """
    AI-enhanced URL worthiness check with fallback to heuristics and session cache

    Args:
        url: URL to classify
        content: Page content (if available)
        title: Page title (if available)
        cost_tracker: Cost tracking instance
        classification_cache: Session cache dict to avoid duplicate classifications
        domain: Domain for cache organization (e.g., 'nab.com.au')

    Returns:
        (is_worthy, reason, classification_details)
    """
    # Check classification cache first (avoid duplicate AI calls)
    if classification_cache and url in classification_cache:
        cached_result = classification_cache[url]
        _logger.debug(f"Session cache hit for {url}: {'WORTHY' if cached_result['is_worthy'] else 'NOT WORTHY'}")
        return cached_result['is_worthy'], cached_result['reasoning'], cached_result['details']

    classification_details = {
        'method': 'unknown',
        'confidence': 0.0,
        'reasoning': '',
        'ai_available': AI_AVAILABLE
    }

    # First, check basic technical filters (these are still useful)
    basic_worthy, basic_reason = is_demo_worthy_url(url)
    if not basic_worthy:
        classification_details.update({
            'method': 'basic_filter',
            'confidence': 0.9,
            'reasoning': f'Failed basic filter: {basic_reason}'
        })
        result = (False, basic_reason, classification_details)

        # Cache basic filter results too
        if classification_cache is not None:
            classification_cache[url] = {
                'is_worthy': False,
                'reasoning': basic_reason,
                'details': classification_details
            }

        return result

    # Try AI classification if available
    ai_classifier = get_ai_classifier(domain=domain)
    if ai_classifier:
        try:
            result: ClassificationResult = await ai_classifier.classify_content(url, content, title)

            # Track costs if cost_tracker provided
            if cost_tracker:
                content_length = len(content + title)
                cost_tracker.track_classification(url, result, content_length)

            classification_details.update({
                'method': result.method_used,
                'confidence': result.confidence,
                'reasoning': result.reasoning
            })

            final_result = (result.is_worthy, result.reasoning if not result.is_worthy else "", classification_details)

            # Cache AI classification result in session cache (takes priority)
            if classification_cache is not None:
                classification_cache[url] = {
                    'is_worthy': result.is_worthy,
                    'reasoning': result.reasoning if not result.is_worthy else "",
                    'details': classification_details
                }
                _logger.debug(f"Cached classification for {url}: {'WORTHY' if result.is_worthy else 'NOT WORTHY'}")

            return final_result

        except Exception as e:
            _logger.error(f"AI classification EXCEPTION for {url}: {e}", exc_info=True)
            # Fall through to heuristic
    else:
        _logger.error(f"AI classifier is None for domain={domain}, AI_AVAILABLE={AI_AVAILABLE}")

    # Fallback to enhanced heuristic (better than just basic filters)
    if AI_AVAILABLE:
        try:
            heuristic_classifier = HeuristicClassifier()
            result = heuristic_classifier.classify(url, content, title)
            classification_details.update({
                'method': result.method_used,
                'confidence': result.confidence,
                'reasoning': result.reasoning
            })

            final_result = (result.is_worthy, result.reasoning if not result.is_worthy else "", classification_details)

            # Cache heuristic classification result
            if classification_cache is not None:
                classification_cache[url] = {
                    'is_worthy': result.is_worthy,
                    'reasoning': result.reasoning if not result.is_worthy else "",
                    'details': classification_details
                }

            return final_result

        except Exception as e:
            _logger.warning(f"Heuristic classification failed for {url}: {e}")

    # Final fallback to basic filters (already passed above)
    classification_details.update({
        'method': 'basic_only',
        'confidence': 0.7,
        'reasoning': 'Only basic filtering applied'
    })

    final_result = (True, "", classification_details)

    # Cache fallback result
    if classification_cache is not None:
        classification_cache[url] = {
            'is_worthy': True,
            'reasoning': "",
            'details': classification_details
        }

    return final_result
