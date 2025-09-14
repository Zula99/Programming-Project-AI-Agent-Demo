#!/usr/bin/env python3

import asyncio
import tempfile
import sys
from pathlib import Path

# Add the Utility directory to path
sys.path.append(str(Path(__file__).parent.parent / 'Utility'))

async def test_linkextractor_ai_fix():
    """Test that LinkExtractor now uses real AI classification"""
    print("=== LinkExtractor AI Classification Fix Test ===")
    
    try:
        from link_extractor import LinkExtractor
        
        with tempfile.TemporaryDirectory() as temp_dir:
            print("1. Creating LinkExtractor with AI enabled...")
            
            extractor = LinkExtractor(
                sitemap_url='https://www.nab.com.au/sitemap.xml',
                file_name='test_nab',
                output_file='test_output.txt',
                file_path=temp_dir,
                use_ai=True
            )
            
            print(f"   AI enabled: {extractor.use_ai}")
            print(f"   Has AI classifier: {hasattr(extractor, 'ai_classifier')}")
            
            if hasattr(extractor, 'ai_classifier'):
                print(f"   AI classifier API key: {bool(extractor.ai_classifier.api_key)}")
                print(f"   AI classifier model: {extractor.ai_classifier.model}")
            
            print("\n2. Testing AI classification on sample URLs...")
            
            test_urls = [
                'https://www.nab.com.au/business/business-bank-accounts',
                'https://www.nab.com.au/personal/home-loans',
                'https://www.nab.com.au/privacy-policy'
            ]
            
            try:
                results = await extractor.intelligent_url_filtering(test_urls, sample_content=True)
                
                print(f"\n✓ Classification completed!")
                print(f"   Processed {len(results)} URLs")
                
                print("\n3. Results Summary:")
                for i, (url, confidence, reasoning) in enumerate(results[:3]):
                    print(f"   {i+1}. {confidence:.3f} - {url}")
                    print(f"      Method: {'AI' if 'AI:' in reasoning else 'HEURISTIC'}")
                    print(f"      Reasoning: {reasoning[:100]}...")
                    print()
                
                ai_count = sum(1 for _, _, reasoning in results if 'AI:' in reasoning)
                heuristic_count = len(results) - ai_count
                
                print(f"📊 Final Results:")
                print(f"   AI Classifications: {ai_count}")
                print(f"   Heuristic Fallbacks: {heuristic_count}")
                
                if ai_count > 0:
                    print("✅ SUCCESS: AI classification is working!")
                    return True
                else:
                    print("❌ ISSUE: Still using only heuristics")
                    return False
                    
            except Exception as classify_error:
                print(f"❌ Classification error: {classify_error}")
                import traceback
                traceback.print_exc()
                return False
                
    except Exception as e:
        print(f"❌ Test setup error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_linkextractor_ai_fix())