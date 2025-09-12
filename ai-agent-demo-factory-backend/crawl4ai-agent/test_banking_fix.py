#!/usr/bin/env python3

import asyncio
from ai_content_classifier import AIContentClassifier
from ai_config import get_ai_config

async def test_banking_classification_fixes():
    """Test the updated banking prompts on the failing cases"""
    print("Testing Banking AI Classification Fixes")
    print("=" * 50)
    
    config = get_ai_config()
    classifier = AIContentClassifier(
        api_key=config.openai_api_key,
        model='gpt-4o-mini'
    )
    
    # Test the specific failing cases mentioned
    test_cases = [
        {
            'url': 'https://www.nab.com.au/personal/bank-accounts/cheque-payments',
            'title': 'Cheque Payments - NAB Personal Banking',
            'content': 'Information about cheque payments, processing times, and how to make cheque payments through NAB banking services.',
            'expected': 'WORTHY (needed for search functionality)'
        },
        {
            'url': 'https://www.nab.com.au/personal/tax/first-tax-return',
            'title': 'Lodging Your First Tax Return - NAB',
            'content': 'Guide for young adults on how to lodge their first tax return, including banking considerations and financial planning.',
            'expected': 'WORTHY (personal finance guidance)'
        },
        {
            'url': 'https://www.nab.com.au/personal/credit-cards/how-to-apply',
            'title': 'How to Apply for a Credit Card - NAB',
            'content': 'Step-by-step guide on applying for a NAB credit card, including eligibility requirements and application process.',
            'expected': 'WORTHY (crucial banking service)'
        },
        {
            'url': 'https://www.nab.com.au/personal/banking/youth-banking',
            'title': 'Youth Banking Services - NAB',
            'content': 'Banking services designed for young people, including youth accounts, financial education, and budgeting tools.',
            'expected': 'WORTHY (specialized banking services)'
        }
    ]
    
    results = []
    total_cost = 0
    
    for i, case in enumerate(test_cases):
        print(f"\nTest {i+1}: {case['url']}")
        print(f"Expected: {case['expected']}")
        
        try:
            result = await classifier.classify_content(
                url=case['url'],
                content=case['content'],
                title=case['title']
            )
            
            total_cost += result.estimated_cost
            
            status = "WORTHY" if result.is_worthy else "FILTERED"
            success = "✓ CORRECT" if result.is_worthy else "✗ WRONG"
            
            print(f"Result: {status} (confidence: {result.confidence:.2f}) - {success}")
            print(f"Cost: ${result.estimated_cost:.6f}")
            print(f"Reasoning: {result.reasoning[:100]}...")
            
            results.append({
                'case': case,
                'result': result,
                'correct': result.is_worthy
            })
            
        except Exception as e:
            print(f"ERROR: {e}")
            results.append({
                'case': case,
                'result': None,
                'correct': False
            })
    
    # Summary
    print("\n" + "=" * 50)
    print("SUMMARY")
    print("=" * 50)
    correct = sum(1 for r in results if r['correct'])
    print(f"Correct classifications: {correct}/{len(results)}")
    print(f"Total cost: ${total_cost:.4f}")
    
    if correct == len(results):
        print("✓ ALL BANKING FIXES WORKING!")
    else:
        print("✗ Some banking content still being filtered incorrectly")
        print("\nFailed cases:")
        for r in results:
            if not r['correct']:
                print(f"- {r['case']['url']}")

if __name__ == "__main__":
    asyncio.run(test_banking_classification_fixes())