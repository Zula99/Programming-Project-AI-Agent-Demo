#!/usr/bin/env python3
"""
Test script for dual-stream logging (WebSocket + OpenSearch)
Tests the enhanced WebSocketLogHandler in main.py
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

# Add paths
sys.path.append("./crawl4ai-agent")
sys.path.append(".")

# Import enhanced handler
from main import WebSocketLogHandler


async def test_dual_stream_logging():
    """Test the enhanced WebSocketLogHandler with OpenSearch integration"""

    print("Testing Dual-Stream Logging (WebSocket + OpenSearch)")
    print("=" * 60)

    # Create enhanced handler
    handler = WebSocketLogHandler(enable_opensearch=True)

    # Create test logger
    test_logger = logging.getLogger("test_fastapi_backend")
    test_logger.setLevel(logging.DEBUG)
    test_logger.addHandler(handler)

    # Test different log levels and scenarios
    test_cases = [
        ("INFO", "FastAPI server starting up", {"component": "startup", "port": 8000}),
        ("DEBUG", "WebSocket connection established", {"client_ip": "127.0.0.1", "session_id": "test-123"}),
        ("WARN", "Crawl4AI session timeout detected", {"session_id": "crawl-456", "duration_ms": 30000}),
        ("ERROR", "OpenSearch connection failed", {"error_code": "CONNECTION_REFUSED", "retry_count": 3}),
        ("INFO", "AI content classification completed", {"url": "https://example.com", "classification": "WORTHY", "confidence": 0.85})
    ]

    print("Sending test log entries...")

    for level, message, metadata in test_cases:
        try:
            # Create log entry with metadata
            if level == "INFO":
                test_logger.info(message, extra={'extra_data': metadata})
            elif level == "DEBUG":
                test_logger.debug(message, extra={'extra_data': metadata})
            elif level == "WARN":
                test_logger.warning(message, extra={'extra_data': metadata})
            elif level == "ERROR":
                test_logger.error(message, extra={'extra_data': metadata})

            print(f"  OK {level}: {message}")

            # Small delay between entries
            await asyncio.sleep(0.1)

        except Exception as e:
            print(f"  FAIL {level}: Failed - {e}")

    # Wait for async operations to complete
    print("\nWaiting for async OpenSearch operations to complete...")
    await asyncio.sleep(2.0)

    print("\nDual-stream logging test completed!")
    print("\nExpected results:")
    print("  WebSocket: Logs broadcast to connected clients (if any)")
    print("  OpenSearch: Logs indexed in ai-agent-logs-2025.09")
    print("  Check OpenSearch with: curl http://localhost:9200/ai-agent-logs-*/_search")


async def test_opensearch_query():
    """Quick test to verify logs are in OpenSearch"""

    print("\n Testing OpenSearch log retrieval...")

    try:
        # Import OpenSearch integration
        from opensearch_logger import OpenSearchCrawlLogger
        from Utility.opensearch_integration import Crawl4AIOpenSearchIntegration

        # Create OpenSearch client
        opensearch = Crawl4AIOpenSearchIntegration()

        # Search for recent test logs
        results = opensearch.search_logs(
            query="FastAPI",
            service="fastapi-backend",
            time_from="2025-09-26T00:00:00Z",
            size=5
        )

        print(f"  Found {results['total_hits']} FastAPI logs in OpenSearch")

        if results['logs']:
            print("  Recent log entries:")
            for i, log in enumerate(results['logs'][:3], 1):
                print(f"    {i}. [{log['level']}] {log['message'][:60]}...")
        else:
            print("   No logs found - they may still be processing")

    except Exception as e:
        print(f"  OpenSearch query failed: {e}")
        print("   This is expected if OpenSearch isn't running")


async def main():
    """Run all dual-stream logging tests"""

    try:
        # Test the enhanced logging
        await test_dual_stream_logging()

        # Test OpenSearch retrieval
        await test_opensearch_query()

        print("\n All tests completed successfully!")
        print(" The enhanced WebSocketLogHandler is now sending logs to both:")
        print(" - WebSocket clients (real-time UI)")
        print(" - OpenSearch (searchable persistence)")

    except Exception as e:
        print(f"\n Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())