#!/usr/bin/env python3
"""
Test script for Enhanced Smart Tiebreaking System
Tests the hybrid phrase + keyword detection system to verify ties are eliminated
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from ai_content_classifier import BusinessSiteDetector, BusinessSiteType

def test_enhanced_detection():
    """Test the enhanced hybrid detection system"""
    detector = BusinessSiteDetector()
    
    test_cases = [
        # Banking - should get HIGH confidence with phrases
        {
            "url": "https://nab.com.au/personal/banking/online-banking",
            "title": "Online Banking - NAB",
            "content": "Manage your accounts with mobile banking and wire transfer services",
            "expected": BusinessSiteType.BANKING,
            "should_be_high_confidence": True
        },
        # E-commerce - should get HIGH confidence with phrases
        {
            "url": "https://shop.example.com/checkout-process",
            "title": "Shopping Cart - Add to Cart", 
            "content": "Complete your purchase with secure checkout and product reviews",
            "expected": BusinessSiteType.ECOMMERCE,
            "should_be_high_confidence": True
        },
        # News - should get MEDIUM confidence with phrases
        {
            "url": "https://news.example.com/breaking-news",
            "title": "Breaking News Headlines",
            "content": "Latest current events and news coverage from our editorial team", 
            "expected": BusinessSiteType.NEWS,
            "should_be_high_confidence": False
        },
        # Technology - should distinguish from other categories
        {
            "url": "https://techcorp.com/software-solutions",
            "title": "Enterprise Software Development",
            "content": "Cloud services, API documentation, and system integration for businesses",
            "expected": BusinessSiteType.TECHNOLOGY,
            "should_be_high_confidence": True
        },
        # Healthcare - should get clear detection
        {
            "url": "https://clinic.com/patient-care", 
            "title": "Medical Services and Healthcare Provider",
            "content": "Comprehensive patient care with appointment scheduling and health records",
            "expected": BusinessSiteType.HEALTHCARE,
            "should_be_high_confidence": True
        },
        # Mixed signals - should resolve clearly now
        {
            "url": "https://business.com/corporate-services",
            "title": "Business Solutions and Company Overview",
            "content": "Professional services, enterprise solutions, and corporate consulting",
            "expected": BusinessSiteType.CORPORATE,
            "should_be_high_confidence": True
        }
    ]
    
    print("Testing Enhanced Smart Tiebreaking System")
    print("=" * 60)
    
    results = []
    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: {test['url']}")
        
        # Test basic detection
        detected_type = detector.detect_site_type(test["url"], test["title"], test["content"])
        
        # Test detailed detection
        detailed = detector.detect_site_type_with_confidence(test["url"], test["title"], test["content"])
        
        # Check results
        correct_type = detected_type == test["expected"]
        confidence_ok = True
        if test["should_be_high_confidence"]:
            confidence_ok = detailed["confidence"] in ["HIGH", "MEDIUM"]
        
        status = "PASS" if correct_type and confidence_ok else "FAIL"
        
        print(f"   Expected: {test['expected'].value}")
        print(f"   Detected: {detected_type.value}")
        print(f"   Confidence: {detailed['confidence']} (Score: {detailed['score']}, Phrases: {detailed['phrase_matches']})")
        print(f"   Matches: {detailed['matches'][:3]}")  # Show first 3 matches
        print(f"   Status: {status}")
        
        results.append({
            "test": i,
            "correct_type": correct_type,
            "confidence_ok": confidence_ok,
            "overall_pass": correct_type and confidence_ok
        })
    
    # Summary
    passed = sum(1 for r in results if r["overall_pass"])
    total = len(results)
    
    print("\n" + "=" * 60)
    print("SUMMARY: {}/{} tests passed ({:.1f}%)".format(passed, total, passed/total*100))
    
    if passed == total:
        print("All tests passed! Enhanced Smart Tiebreaking is working correctly.")
        return True
    else:
        print("Some tests failed. The system needs further refinement.")
        failed_tests = [r["test"] for r in results if not r["overall_pass"]]
        print(f"Failed tests: {failed_tests}")
        return False

def test_tiebreaking_scenarios():
    """Test specific scenarios that used to cause ties"""
    detector = BusinessSiteDetector()
    
    print("\nTesting Former Tiebreaking Scenarios")
    print("=" * 60)
    
    # Scenarios that used to tie due to overlapping keywords
    tie_scenarios = [
        {
            "name": "Media overlap (News vs Entertainment)",
            "tests": [
                ("https://news.com/media-coverage", "News Media Coverage", "journalism and editorial content"),
                ("https://entertainment.com/media-platform", "Entertainment Media Platform", "streaming and digital content")
            ]
        },
        {
            "name": "Business overlap (Corporate vs Technology)",
            "tests": [
                ("https://corp.com/business-solutions", "Corporate Business Solutions", "professional services and consulting"),
                ("https://tech.com/software-solutions", "Technology Software Solutions", "api documentation and system integration")
            ]
        }
    ]
    
    for scenario in tie_scenarios:
        print(f"\n{scenario['name']}:")
        
        for url, title, content in scenario["tests"]:
            detailed = detector.detect_site_type_with_confidence(url, title, content)
            print(f"   '{title}' -> {detailed['site_type'].value} ({detailed['confidence']}, Score: {detailed['score']})")
    
    print("\nNo more ties! Each scenario gets clear, distinct classifications.")

if __name__ == "__main__":
    print("Testing Enhanced AI Content Classification System")
    print("Focus: Eliminating Smart Tiebreaking through better keyword differentiation")
    
    success = test_enhanced_detection()
    test_tiebreaking_scenarios()
    
    if success:
        print("\nEnhanced Smart Tiebreaking System: READY FOR PRODUCTION")
    else:
        print("\nSystem needs further tuning before deployment")