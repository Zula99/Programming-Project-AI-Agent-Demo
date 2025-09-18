# OpenSearch Integration Testing Guide

## Prerequisites

1. **Start OpenSearch Docker container:**
```bash
# From project root
docker-compose up -d opensearch-demo
```

2. **Verify OpenSearch is running:**
```bash
curl -X GET "localhost:9200/"
```

## Testing OpenSearch Integration

### 1. Install Dependencies

```bash
pip install opensearch-py beautifulsoup4
```

### 2. Index Existing Crawl Data

```bash
# Index NAB crawl data (if you have it)
python opensearch_integration.py --crawl-dir "../crawl4ai-agent/output/nab" --index-name "nab-demo" --host localhost --port 9200

# Or index any other crawl data
python opensearch_integration.py --crawl-dir "../crawl4ai-agent/output/your-site" --index-name "your-index" --host localhost --port 9200
```

### 3. Test Basic Functionality

```bash
# Test with search query
python opensearch_integration.py --crawl-dir "../crawl4ai-agent/output/nab" --index-name "nab-demo" --search "banking loans"
```

### 4. Manual Testing with curl

#### Check available indices:
```bash
curl -X GET "localhost:9200/_cat/indices?v"
```

#### Search all content:
```bash
curl -X GET "localhost:9200/_search" -H 'Content-Type: application/json' -d '{"query":{"match_all":{}},"_source":["title","url","meta_desc"],"size":5}'
```

#### Search for specific terms:
```bash
curl -X GET "localhost:9200/_search" -H 'Content-Type: application/json' -d '{"query":{"multi_match":{"query":"banking loans","fields":["title^3","content_md","meta_desc^2"]}},"_source":["title","url","meta_desc"],"size":10}'
```

#### Get document count:
```bash
curl -X GET "localhost:9200/_count"
```

### 5. Python Testing Script

Create a test script `test_search.py`:

```python
#!/usr/bin/env python3

from opensearch_integration import Crawl4AIOpenSearchIntegration, OpenSearchConfig
import json

def test_opensearch():
    # Connect to OpenSearch
    config = OpenSearchConfig(host="localhost", port=9200)
    integration = Crawl4AIOpenSearchIntegration(config)

    # Test search
    results = integration.search("banking", "nab-demo", size=5)

    print(f"Found {results['total_hits']} results:")
    for i, hit in enumerate(results['hits']):
        print(f"{i+1}. {hit['title']} - {hit['url']} (score: {hit['score']:.2f})")

    # Test index stats
    stats = integration.get_index_stats("nab-demo")
    print(f"\nIndex stats: {json.dumps(stats, indent=2)}")

if __name__ == "__main__":
    test_opensearch()
```

Run the test:
```bash
python test_search.py
```

## Expected Output

### Successful Indexing:
```
INFO:__main__:Starting indexing of ../crawl4ai-agent/output/nab into nab-demo
INFO:__main__:Indexed batch 1: 50 documents
INFO:__main__:Indexing complete: 150/150 documents indexed in 45.2s

Indexing Results:
  Documents indexed: 150
  Processing time: 45.20s
  Errors: 0
```

### Successful Search:
```
Testing search: 'banking loans'
  Found 23 results
  1. Business Banking Solutions - https://www.nab.com.au/business/loans - (score: 2.45)
  2. Personal Loans Overview - https://www.nab.com.au/personal/loans - (score: 1.88)
  3. Home Loans - https://www.nab.com.au/personal/home-loans - (score: 1.34)
```

## Troubleshooting

### OpenSearch not responding:
```bash
# Check if container is running
docker ps | grep opensearch

# Check logs
docker logs opensearch-demo

# Restart container
docker restart opensearch-demo
```

### Index not found error:
```bash
# Check what indices exist
curl -X GET "localhost:9200/_cat/indices?v"

# Create index manually if needed
curl -X PUT "localhost:9200/test-index"
```

### Connection refused:
- Verify OpenSearch is running on port 9200
- Check firewall settings
- Ensure Docker container has proper port mapping

## Cleanup

### Delete specific index:
```bash
curl -X DELETE "localhost:9200/nab-demo"
```

### Stop OpenSearch:
```bash
docker stop opensearch-demo
```

### Remove all Docker containers:
```bash
docker-compose down -v
```

## Integration with Crawl4AI

The OpenSearch integration automatically works with Crawl4AI output structure:
- Looks for `index.md` (markdown content)
- Reads `meta.json` (metadata)
- Optionally uses `raw.html` (for HTML parsing)

This allows seamless indexing of any Crawl4AI crawl results for immediate search capabilities.