"""
Test the new two-stage AI classification system
"""
import sys
import asyncio
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from ai_content_classifier import AIContentClassifier, BusinessSiteDetector, BusinessSiteType

async def test_two_stage_system():
    """Test the two-stage classification with different site types"""
    
    # Initialize components
    site_detector = BusinessSiteDetector()
    ai_classifier = AIContentClassifier()  # Will use heuristic fallback if no API key
    
    # Test cases
    test_cases = [
        {
            "url": "https://example.com",
            "title": "Example Domain",
            "content": "This domain is for use in illustrative examples in documents."
        },
        {
            "url": "https://nab.com.au/business/loans", 
            "title": "Business Loans - NAB",
            "content": "Commercial lending solutions for your business growth"
        },
        {
            "url": "https://amazon.com/products",
            "title": "Products - Amazon", 
            "content": "Shop our wide selection of products"
        }
    ]
    
    print("=== Testing Two-Stage AI Classification System ===\n")
    
    for i, case in enumerate(test_cases, 1):
        print(f"Test {i}: {case['url']}")
        print(f"Title: {case['title']}")
        
        # Stage 1: Site type detection
        detected_type = site_detector.detect_site_type(
            case['url'], case['title'], case['content']
        )
        print(f"🔍 Detected Site Type: {detected_type.value}")
        
        # Stage 2: Content classification  
        try:
            result = await ai_classifier.classify_content(
                case['url'], case['content'], case['title']
            )
            
            print(f"✅ Classification Result:")
            print(f"   Worthy: {result.is_worthy}")
            print(f"   Confidence: {result.confidence}")
            print(f"   Method: {result.method_used}")
            print(f"   Reasoning: {result.reasoning}")
            
        except Exception as e:
            print(f"❌ Classification failed: {e}")
        
        print("-" * 50)

if __name__ == "__main__":
    asyncio.run(test_two_stage_system())