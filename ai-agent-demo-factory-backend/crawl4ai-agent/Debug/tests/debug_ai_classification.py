#!/usr/bin/env python3

import asyncio
from ai_content_classifier import AIContentClassifier
from ai_config import get_ai_config

async def debug_ai_classification():
    """Debug why AI classification is failing"""
    print("=== AI Classification Debug Test ===")
    
    config = get_ai_config()
    print(f"✓ API key available: {bool(config.openai_api_key)}")
    print(f"✓ Preferred model: {config.preferred_model}")
    
    if not config.openai_api_key:
        print(" No OpenAI API key found!")
        return
    
    try:
        print("\n1. Initializing AI classifier...")
        classifier = AIContentClassifier(
            api_key=config.openai_api_key,
            model='gpt-4o-mini'
        )
        print("✓ AI classifier initialized successfully")
        
        print("\n2. Testing AI classification...")
        result = await classifier.classify_content(
            url='https://www.nab.com.au/business/business-bank-accounts',
            content='Business banking services and accounts for small and medium enterprises. Features include transaction accounts, term deposits, and business loans.',
            title='NAB Business Banking Accounts'
        )
        
        print("✓ AI classification successful!")
        print(f"   Method used: {result.method_used}")
        print(f"   Is worthy: {result.is_worthy}")
        print(f"   Confidence: {result.confidence}")
        print(f"   Reasoning: {result.reasoning}")
        
        if hasattr(result, 'estimated_cost'):
            print(f"   Estimated cost: ${result.estimated_cost:.6f}")
            print(f"   Total tokens: {result.total_tokens}")
        
    except Exception as e:
        print(f" AI classification failed: {e}")
        import traceback
        traceback.print_exc()
        
        print("\n3. Testing fallback to heuristic...")
        try:
            # Test heuristic method directly
            result = classifier._classify_with_heuristics('https://www.nab.com.au/business/business-bank-accounts')
            print(f"✓ Heuristic fallback working: {result.method_used}")
        except Exception as e2:
            print(f" Even heuristic failed: {e2}")

if __name__ == "__main__":
    asyncio.run(debug_ai_classification())