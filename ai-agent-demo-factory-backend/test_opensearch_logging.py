#!/usr/bin/env python3
"""
Simple test script to verify OpenSearch logging integration
"""

import asyncio
import sys
from pathlib import Path

# Add crawl4ai-agent to path
sys.path.append(str(Path(__file__).parent / "crawl4ai-agent"))

from opensearch_logger import log_to_opensearch, OpenSearchCrawlLogger
from ai_content_classifier import AIContentClassifier


async def test_simple_log_entry():
    """Test basic log entry to OpenSearch"""
    print("Testing simple log entry...")

    success = log_to_opensearch(
        service="test-service",
        component="test_script",
        level="INFO",
        message="Test log entry from OpenSearch logging integration",
        metadata={
            "test_type": "integration_test",
            "component_tested": "opensearch_logger",
            "test_timestamp": "2024-01-15T10:30:00Z"
        }
    )

    if success:
        print("Simple log entry test passed")
    else:
        print("Simple log entry test failed")

    return success


async def test_ai_classifier_logging():
    """Test AI content classifier with OpenSearch logging"""
    print("Testing AI classifier with OpenSearch logging...")

    try:
        # Initialize classifier (this will use fake content, no real API call)
        classifier = AIContentClassifier("example.com")

        # Test with fake content
        result = await classifier.classify_content(
            url="https://example.com/test-page",
            content="This is test content for OpenSearch logging integration",
            title="Test Page Title"
        )

        print(f"   AI classifier test completed - Method: {result.method_used}")
        print(f"   Classification: {'WORTHY' if result.is_worthy else 'NOT_WORTHY'}")
        print(f"   Confidence: {result.confidence:.2f}")

        return True

    except Exception as e:
        print(f" AI classifier test failed: {e}")
        return False


async def test_opensearch_crawl_logger():
    """Test enhanced crawl logger with OpenSearch integration"""
    print(" Testing OpenSearch-enhanced crawl logger...")

    try:
        # Create enhanced logger
        logger = OpenSearchCrawlLogger("https://example.com/test")
        logger.start_logging()

        # Test various logging methods
        logger.log_phase("TEST_PHASE", "Testing OpenSearch integration")

        # Test AI classification logging
        logger.log_ai_classification(
            url="https://example.com/test",
            classification="WORTHY",
            confidence=0.85,
            cost=0.002
        )

        # Test metrics logging
        logger.log_metrics({
            "test_metric_1": "value_1",
            "test_metric_2": 42,
            "test_metric_3": 3.14
        })

        logger.stop_logging(success=True, final_message="OpenSearch logging test completed")

        print(" OpenSearch crawl logger test passed")
        return True

    except Exception as e:
        print(f" OpenSearch crawl logger test failed: {e}")
        return False


async def main():
    """Run all OpenSearch logging tests"""
    print(" Starting OpenSearch Logging Integration Tests")
    print("=" * 50)

    tests = [
        ("Simple Log Entry", test_simple_log_entry),
        ("AI Classifier Logging", test_ai_classifier_logging),
        ("Enhanced Crawl Logger", test_opensearch_crawl_logger)
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n Running: {test_name}")
        try:
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f" {test_name} failed with exception: {e}")
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 50)
    print(" Test Results Summary:")

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = " PASS" if success else " FAIL"
        print(f"  {status} - {test_name}")

    print(f"\n Overall: {passed}/{total} tests passed")

    if passed == total:
        print(" All tests passed! OpenSearch logging integration is working.")
    else:
        print("  Some tests failed. Check OpenSearch connection and configuration.")

    return passed == total


if __name__ == "__main__":
    asyncio.run(main())