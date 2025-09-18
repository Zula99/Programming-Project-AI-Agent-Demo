# Complete OpenSearch & Proxy Server Testing Guide

## Overview
This guide provides step-by-step instructions to test the complete search injection system:
1. OpenSearch integration for indexing crawled content
2. Proxy server with API replacement search injection (US-63)
3. End-to-end testing of search functionality

---

## Quick Start (All-in-One Testing)

### Step 1: Start OpenSearch Container
```bash
# From project root directory
cd "H:/Bachelor Sem 2/Programming Project/Project/Programming-Project-AI-Agent-Demo"
docker-compose up -d opensearch-demo

# Verify OpenSearch is running (wait ~10 seconds)
curl -X GET "localhost:9200/"
```

**Expected Response:**
```json
{
  "name" : "opensearch-demo",
  "cluster_name" : "docker-cluster",
  "version" : {
    "number" : "2.11.0"
  }
}
```

### Step 2: Index Your Existing Crawl Data
```bash
# Navigate to Utility directory
cd ai-agent-demo-factory-backend/Utility

# Index NAB crawl data (you have 753+ pages ready)
python opensearch_integration.py --crawl-dir "../crawl4ai-agent/output/agent_crawls/nab.com.au" --index-name "demo-nab" --host localhost --port 9200

# Verify indexing worked
curl -X GET "localhost:9200/demo-nab/_count"
```

**Expected Output:**
```
INFO:__main__:Starting indexing of ../crawl4ai-agent/output/agent_crawls/nab.com.au into demo-nab
INFO:__main__:Indexed batch 1: 100 documents
INFO:__main__:Indexed batch 2: 100 documents
...
INFO:__main__:Indexing complete: 753/753 documents indexed in 45.2s

Indexing Results:
  Documents indexed: 753
  Processing time: 45.20s
  Errors: 0
```

### Step 3: Start Proxy Server (Separate from Crawler)
```bash
# In a NEW terminal/command prompt (separate from your crawling container)
cd ai-agent-demo-factory-backend/Proxy

# Start proxy server
python proxy_server.py
```

**Expected Output:**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Step 4: Configure Proxy for NAB
```bash
# In another terminal, configure proxy to point to NAB with search injection
curl -X POST "http://localhost:8000/auto-configure" \
  -H "Content-Type: application/json" \
  -d '{
    "target_url": "https://www.nab.com.au",
    "run_id": "test-search-injection",
    "enabled": true
  }'
```

**Expected Response:**
```json
{
  "message": "Auto-proxy configured from crawl completion",
  "proxy_url": "http://localhost:8000/proxy/",
  "config": {
    "target_url": "https://www.nab.com.au",
    "enabled": true,
    "search_injection_enabled": true
  },
  "search_injection": true,
  "opensearch_index": "demo-nab"
}
```

### Step 5: Test Search API Interception
```bash
# Test search API call that would be intercepted
curl -X GET "http://localhost:8000/proxy/search/api?q=business+loans"

# Test another search pattern
curl -X GET "http://localhost:8000/proxy/api/search?query=home+mortgage"

# Test with different search parameter
curl -X GET "http://localhost:8000/proxy/find?term=banking+services"
```

**Expected Search Response:**
```json
{
  "query": "business loans",
  "total": 45,
  "results": [
    {
      "title": "Business Banking Solutions",
      "url": "https://www.nab.com.au/business/loans",
      "description": "Complete banking solutions for business...",
      "score": 2.45,
      "snippet": "...business <em>loans</em> for commercial..."
    }
  ],
  "took": 15,
  "source": "opensearch"
}
```

### Step 6: Test Normal Proxy (Non-Search)
```bash
# Test that normal pages still proxy correctly
curl -I "http://localhost:8000/proxy/"
curl -I "http://localhost:8000/proxy/about-us"
```

---

## Detailed Testing Scenarios

### A. Search Detection Testing
Test which requests trigger search interception:

```bash
# ✅ SHOULD be intercepted (has search path + search params)
curl "http://localhost:8000/proxy/search?q=test"
curl "http://localhost:8000/proxy/api/search?query=test"
curl "http://localhost:8000/proxy/find?term=test"
curl "http://localhost:8000/proxy/lookup?search=test"

# ❌ SHOULD NOT be intercepted (missing search params)
curl "http://localhost:8000/proxy/search"
curl "http://localhost:8000/proxy/api/search"

# ❌ SHOULD NOT be intercepted (missing search path)
curl "http://localhost:8000/proxy/about?q=test"
curl "http://localhost:8000/proxy/contact?query=test"
```

### B. OpenSearch Direct Testing
Test OpenSearch directly (bypassing proxy):

```bash
# Search all content
curl -X GET "localhost:9200/demo-nab/_search" -H 'Content-Type: application/json' -d '{
  "query": {"match_all": {}},
  "_source": ["title", "url", "meta_desc"],
  "size": 5
}'

# Search for specific terms
curl -X GET "localhost:9200/demo-nab/_search" -H 'Content-Type: application/json' -d '{
  "query": {
    "multi_match": {
      "query": "banking loans",
      "fields": ["title^3", "content_md", "meta_desc^2"]
    }
  },
  "_source": ["title", "url", "meta_desc"],
  "size": 10
}'

# Get index statistics
curl -X GET "localhost:9200/demo-nab/_stats"
curl -X GET "localhost:9200/demo-nab/_count"
```

### C. Full Browser Testing
1. **Configure your browser proxy** to use `localhost:8000`
2. **Navigate to** `nab.com.au`
3. **Use any search functionality** on the site
4. **Verify** that search requests are intercepted and return OpenSearch results

---

## Expected Results Summary

| Test | Expected Behavior |
|------|-------------------|
| `proxy/search?q=loans` | Returns OpenSearch results |
| `proxy/about-us` | Returns proxied NAB page |
| `proxy/api/search?query=banking` | Returns OpenSearch results |
| `proxy/contact` | Returns proxied NAB page |

## Troubleshooting

### OpenSearch Issues
```bash
# Check if OpenSearch is running
docker ps | grep opensearch
curl -X GET "localhost:9200/_cluster/health"

# View OpenSearch logs
docker logs opensearch-demo

# Restart OpenSearch
docker restart opensearch-demo
```

### Proxy Server Issues
```bash
# Check if proxy is responding
curl -X GET "http://localhost:8000/"

# Check proxy configuration
curl -X GET "http://localhost:8000/config"

# View proxy logs (check terminal where proxy_server.py is running)
```

### Indexing Issues
```bash
# Check if index exists
curl -X GET "localhost:9200/_cat/indices?v"

# Check index document count
curl -X GET "localhost:9200/demo-nab/_count"

# Delete and recreate index
curl -X DELETE "localhost:9200/demo-nab"
python opensearch_integration.py --crawl-dir "../crawl4ai-agent/output/agent_crawls/nab.com.au" --index-name "demo-nab" --recreate
```

### Search Not Working
1. **Verify index has data**: `curl "localhost:9200/demo-nab/_count"`
2. **Check proxy configuration**: `curl "localhost:8000/config"`
3. **Test search detection**: Use exact URLs from Section A above
4. **Check logs**: Both proxy server logs and OpenSearch logs

---

## Cleanup

### Stop Services
```bash
# Stop proxy server (Ctrl+C in proxy terminal)

# Stop OpenSearch
docker stop opensearch-demo

# Or stop all containers
docker-compose down
```

### Remove Test Data
```bash
# Delete search index
curl -X DELETE "localhost:9200/demo-nab"

# Remove OpenSearch container
docker rm -f opensearch-demo
```

---

## Integration Notes

### Search API Detection Patterns
The system detects search APIs using these patterns:
- **Path indicators**: `search`, `find`, `query`, `lookup`, `results`, `api/search`, `search/api`
- **Parameter names**: `q`, `query`, `search`, `term`, `keyword`, `text`
- **Requirement**: Must have BOTH path indicator AND search parameter

### OpenSearch Integration
- **Index naming**: `demo-{domain}` (e.g., `demo-nab`, `demo-commbank`)
- **Document structure**: Uses `title`, `content_md`, `url`, `meta_desc`, `h1`, `h2`, `h3`
- **Search scoring**: Title (3x), H1 (2x), meta description (2x), content (1x)

This system provides enhanced search capabilities that surpass the original site's search functionality while maintaining full compatibility with existing site navigation.