#!/usr/bin/env python3
"""
Quick test for AI parsing bug fix
Tests confidence 1.0 scenarios
"""
import asyncio
import logging
from ai_content_classifier import AIContentClassifier

# Setup logging to see debug output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def test_parsing_fix():
    """Test the AI parsing fix with various confidence scenarios"""
    print("Testing AI Parsing Fix")
    print("=" * 50)
    
    from ai_config import get_ai_config
    config = get_ai_config()
    
    if not config.openai_api_key:
        print("No OpenAI API key found - test requires API key")
        return
    
    classifier = AIContentClassifier(api_key=config.openai_api_key)
    
    # Test cases that should return high confidence + worthy
    test_cases = [
        {
            "url": "https://www.nab.com.au/business/loans",
            "title": "Business Loans - NAB",
            "content": "Explore our range of business loans designed to help your business grow. Competitive rates, flexible terms.",
            "expect": "Should be WORTHY=True with high confidence"
        },
        {
            "url": "https://www.nab.com.au/contact-us",
            "title": "Contact Us - Customer Support",
            "content": "Get in touch with our customer service team. Phone, email, or visit a branch near you.",
            "expect": "Should be WORTHY=True (contact us is valuable for demos)"
        },
        {
            "url": "https://www.nab.com.au/api/v2/debug/session-logs",
            "title": "Debug Session Logs - Internal",
            "content": "Internal debug logs for session tracking. Error codes: 404, 500, timeout exceptions. Internal use only.",
            "expect": "Should be WORTHY=False (debug/internal content not valuable for demos)"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {case['url']}")
        print(f"Expected: {case['expect']}")
        print("-" * 40)
        
        try:
            result = await classifier.classify_content(
                url=case["url"],
                content=case["content"],
                title=case["title"]
            )
            
            print(f"Result: WORTHY={result.is_worthy}, CONFIDENCE={result.confidence:.2f}")
            print(f"Method: {result.method_used}")
            print(f"Reasoning: {result.reasoning}")
            
            # Check results - confidence means certainty of the decision, not worthiness
            if result.confidence >= 0.8:
                if result.is_worthy:
                    print(f"✅ CORRECT: AI is {result.confidence:.1%} confident this IS worthy for demos")
                else:
                    print(f"✅ CORRECT: AI is {result.confidence:.1%} confident this is NOT worthy for demos")
            else:
                print(f"⚠️  LOW CONFIDENCE: AI is only {result.confidence:.1%} certain about this decision")
                
        except Exception as e:
            print(f"ERROR: {e}")
    
    print("\n" + "=" * 50)
    print("Parsing Fix Test Complete")

if __name__ == "__main__":
    asyncio.run(test_parsing_fix())