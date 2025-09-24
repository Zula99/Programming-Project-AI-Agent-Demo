#!/usr/bin/env python3
"""
Test script for OpenSearch integration with Crawl4AI

This script demonstrates how to use the OpenSearch integration utility:
1. Set up OpenSearch connection
2. Index crawled content from Crawl4AI
3. Perform searches on indexed content

Usage examples:
  python test_opensearch.py --index-crawl-data --crawl-dir "../crawl4ai-agent/output/nab"
  python test_opensearch.py --search "banking services" --index "demo-nab"
  python test_opensearch.py --full-demo --crawl-dir "../crawl4ai-agent/output/nab"
"""

import argparse
import sys
from pathlib import Path
import time

# Add the Utility directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from opensearch_integration import Crawl4AIOpenSearchIntegration, OpenSearchConfig, IndexConfig
    print(" OpenSearch integration module loaded successfully")
except ImportError as e:
    print(f" Failed to import OpenSearch integration: {e}")
    print("Make sure to install dependencies: pip install opensearch-py beautifulsoup4")
    sys.exit(1)

def test_connection(host: str = "localhost", port: int = 9200):
    """Test OpenSearch connection"""
    print(f"\n Testing connection to OpenSearch at {host}:{port}")
    try:
        # Simple HTTP connection without authentication (security disabled)
        config = OpenSearchConfig(host=host, port=port, scheme="http")
        integration = Crawl4AIOpenSearchIntegration(config)
        print(" Successfully connected to OpenSearch")
        return integration
    except Exception as e:
        print(f" Connection failed: {e}")
        print("Make sure OpenSearch is running. You can start it with Docker:")
        print("docker run -d -p 9200:9200 -e 'discovery.type=single-node' -e 'plugins.security.disabled=true' --name opensearch-demo opensearchproject/opensearch:2.11.0")
        return None

def index_crawl_data(integration: Crawl4AIOpenSearchIntegration,
                    crawl_dir: str, index_name: str = None):
    """Index crawl4ai data into OpenSearch"""
    crawl_path = Path(crawl_dir)
    if not crawl_path.exists():
        print(f" Crawl directory not found: {crawl_dir}")
        return None

    # Generate index name from crawl directory if not provided
    if not index_name:
        # Extract domain from path (e.g., "output/nab" -> "demo-nab")
        domain_part = crawl_path.name
        index_name = f"demo-{domain_part}"

    print(f"\n Indexing crawl data from {crawl_dir} into index '{index_name}'")

    try:
        start_time = time.time()
        stats = integration.index_crawl4ai_data(crawl_dir, index_name)
        end_time = time.time()

        print(f"\n Indexing completed successfully!")
        print(f"    Folders processed: {stats['total_folders_found']}")
        print(f"    Documents indexed: {stats['documents_indexed']}")
        print(f"    Processing time: {end_time - start_time:.2f}s")
        print(f"    Errors: {stats['errors']}")
        print(f"    Batch count: {stats['batch_count']}")

        # Get index statistics
        index_stats = integration.get_index_stats(index_name)
        if 'error' not in index_stats:
            print(f"    Index size: {index_stats['store_size']:,} bytes")

        return index_name

    except Exception as e:
        print(f" Indexing failed: {e}")
        return None

def test_search(integration: Crawl4AIOpenSearchIntegration,
                index_name: str, queries: list):
    """Test search functionality"""
    print(f"\n Testing search on index '{index_name}'")

    for query in queries:
        print(f"\n  Query: '{query}'")
        try:
            results = integration.search(query, index_name, size=5)

            if 'error' in results:
                print(f"     Search failed: {results['error']}")
                continue

            print(f"     Found {results['total_hits']} results (took {results['took']}ms)")

            for i, hit in enumerate(results['hits'][:3], 1):
                print(f"    {i}. {hit['title'][:60]}...")
                print(f"       URL: {hit['url']}")
                print(f"       Score: {hit['score']:.2f}")
                if hit.get('highlight', {}).get('content_md'):
                    snippet = hit['highlight']['content_md'][0][:100]
                    print(f"       Snippet: {snippet}...")
                print()

        except Exception as e:
            print(f"     Search error: {e}")

def run_full_demo(crawl_dir: str, host: str = "localhost", port: int = 9200):
    """Run complete demonstration workflow"""
    print(" Running full OpenSearch integration demo")
    print("=" * 60)

    # Step 1: Test connection
    integration = test_connection(host, port)
    if not integration:
        return False

    # Step 2: Index data
    index_name = index_crawl_data(integration, crawl_dir)
    if not index_name:
        return False

    # Step 3: Test searches
    test_queries = [
        "banking services",
        "home loans",
        "business accounts",
        "customer support",
        "mobile app"
    ]

    test_search(integration, index_name, test_queries)

    print(f"\n🎉 Demo completed successfully!")
    print(f"   Index '{index_name}' is ready for use")
    print(f"   You can now integrate this with your demo frontend")

    return True

def main():
    parser = argparse.ArgumentParser(
        description="Test OpenSearch integration for Crawl4AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test connection only
  python test_opensearch.py --test-connection

  # Index crawl data
  python test_opensearch.py --index-crawl-data --crawl-dir "../crawl4ai-agent/output/nab"

  # Search existing index
  python test_opensearch.py --search "banking" --index "demo-nab"

  # Full demonstration
  python test_opensearch.py --full-demo --crawl-dir "../crawl4ai-agent/output/nab"
        """)

    parser.add_argument("--host", default="localhost", help="OpenSearch host")
    parser.add_argument("--port", type=int, default=9200, help="OpenSearch port")
    parser.add_argument("--test-connection", action="store_true",
                       help="Test OpenSearch connection")
    parser.add_argument("--index-crawl-data", action="store_true",
                       help="Index crawl4ai data")
    parser.add_argument("--crawl-dir", help="Path to crawl4ai output directory")
    parser.add_argument("--index", help="Index name")
    parser.add_argument("--search", help="Search query to test")
    parser.add_argument("--full-demo", action="store_true",
                       help="Run complete demonstration")

    args = parser.parse_args()

    # Validate arguments
    if args.index_crawl_data or args.full_demo:
        if not args.crawl_dir:
            print(" --crawl-dir is required for indexing operations")
            sys.exit(1)

    if args.search and not args.index:
        print(" --index is required for search operations")
        sys.exit(1)

    # Execute requested operations
    if args.full_demo:
        success = run_full_demo(args.crawl_dir, args.host, args.port)
        sys.exit(0 if success else 1)

    if args.test_connection:
        integration = test_connection(args.host, args.port)
        if not integration:
            sys.exit(1)

    if args.index_crawl_data:
        integration = test_connection(args.host, args.port)
        if not integration:
            sys.exit(1)

        index_name = index_crawl_data(integration, args.crawl_dir, args.index)
        if not index_name:
            sys.exit(1)

    if args.search:
        integration = test_connection(args.host, args.port)
        if not integration:
            sys.exit(1)

        test_search(integration, args.index, [args.search])

    print("\n All operations completed successfully")

if __name__ == "__main__":
    main()