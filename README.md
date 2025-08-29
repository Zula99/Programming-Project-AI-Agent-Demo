# Web Scraping Platform - Operation Guide

A full-stack web scraping platform that allows users to crawl target websites using Norconex, store results in OpenSearch, and display searchable results through a Next.js frontend.

## Quick Start

### Prerequisites
- Docker and Docker Compose
- 8GB+ RAM recommended for large crawls
- Ports 3000, 8000, 9200 available

### Launch the Platform
```bash
# Clone and navigate to project
cd Programming-Project-AI-Agent-Demo

# Start all services
docker-compose up -d

# Verify services are running
docker-compose ps
```

### Access the Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **OpenSearch**: http://localhost:9200

## How to Use

### 1. Start a Website Crawl
1. Open http://localhost:3000 in your browser
2. Enter a target URL (see sample sites below)
3. Click "Start Crawl"
4. Monitor real-time progress in the Active Crawl section

#### Sample Sites for Testing
**Small Sites (Good for Testing)**
- `https://httpbin.org/` - HTTP testing service with various endpoints
- `https://example.com/` - Simple single-page site
- `https://httpstat.us/` - HTTP status code testing site
- `https://jsonplaceholder.typicode.com/` - Fake REST API for testing

**Documentation Sites (Rich Content)**
- `https://docs.python.org/3/tutorial/` - Python tutorial documentation
- `https://developer.mozilla.org/en-US/docs/Web/HTML` - MDN HTML documentation
- `https://www.w3schools.com/html/` - W3Schools HTML tutorial
- `https://fastapi.tiangolo.com/` - FastAPI documentation

**News & Content Sites (More Pages)**
- `https://news.ycombinator.com/` - Hacker News (tech news)
- `https://www.reuters.com/technology/` - Reuters technology section
- `https://httparchive.org/` - HTTP Archive reports

**E-commerce (Complex Structure)**
- `https://books.toscrape.com/` - Fake bookstore for scraping practice
- `https://scrapeme.live/shop/` - Pokemon e-commerce site for testing

⚠️ **Important Notes:**
- Start with small sites (httpbin.org, example.com) for initial testing
- Respect robots.txt and website terms of service
- Some sites may have rate limiting or anti-bot measures
- Current config limits: 50 pages max, 2 levels deep, 15-minute timeout

### 2. Search Crawled Content
1. Use the search box in the "Crawled Data from OpenSearch" section
2. Enter keywords to find specific content
3. Click "Show All" to view all indexed documents
4. Results show with relevance scores and highlighted matches

### 3. Monitor Crawl Progress
- **Status**: Shows pending → running → complete/failed
- **Progress Bar**: Visual progress indicator (0-100%)
- **Duration**: Real-time crawl duration
- **Pages Indexed**: Count of documents processed

### 4. Clear OpenSearch Index and Norconex State (Re-crawl Same Sites)

⚠️ **IMPORTANT**: To re-crawl the same websites, you must clear BOTH the OpenSearch index AND Norconex's internal state. Clearing only the OpenSearch index will NOT work because Norconex remembers which URLs it has already processed in its workdir.

#### Complete Clear (Recommended - Required for Re-crawling Same Sites)
```bash
# Step 1: Clear Norconex workdir in Docker container
docker exec programming-project-ai-agent-demo-norconex-maven-1 rm -rf /opt/norconex/data/workdir/*

# Step 2: Clear local repository workdir (CRITICAL - often missed!)
sudo rm -rf norconex-runner/data/workdir/*
sudo rm -rf norconex/norconex/workdir/*

# Step 3: Delete OpenSearch index
curl -X DELETE http://localhost:9200/demo_factory

# Verification
echo "=== OpenSearch index status ==="
curl http://localhost:9200/_cat/indices?v

echo -e "\n=== Local workdir contents (should be empty) ==="
ls -la norconex-runner/data/workdir/ 2>/dev/null || echo "Directory empty"

echo -e "\n=== Docker workdir contents (should be empty) ==="
docker exec programming-project-ai-agent-demo-norconex-maven-1 ls -la /opt/norconex/data/workdir/
```

#### Option A: Delete Entire Index Only (Limited - Won't Work for Re-crawling)
```bash
# Delete the demo_factory index completely
curl -X DELETE http://localhost:9200/demo_factory

# Verify deletion
curl http://localhost:9200/_cat/indices?v
```
⚠️ **Note**: This alone will NOT allow re-crawling the same sites. Norconex will still skip URLs it thinks were already processed.

#### Option B: Delete All Documents (Keep Index Structure)  
```bash
# Delete all documents but preserve index mapping
curl -X POST http://localhost:9200/demo_factory/_delete_by_query \
  -H "Content-Type: application/json" \
  -d '{"query": {"match_all": {}}}'

# Check document count (should be 0)
curl http://localhost:9200/demo_factory/_count
```

#### Option C: Delete Specific Domain Documents
```bash
# Delete documents from a specific domain only
curl -X POST http://localhost:9200/demo_factory/_delete_by_query \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "wildcard": {
        "url": "*example.com*"
      }
    }
  }'
```

#### Option D: Nuclear Reset (Complete System Reset)
```bash
# Stop all services, remove data, restart
docker-compose down
docker volume rm $(docker volume ls -q | grep opensearch) 2>/dev/null || true
sudo rm -rf norconex-runner/data/workdir/*
sudo rm -rf norconex/norconex/workdir/*
docker-compose up -d
```

## Architecture Overview

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Next.js   │───▶│   FastAPI   │───▶│   Norconex  │───▶│ OpenSearch  │
│  Frontend   │    │   Backend   │    │   Crawler   │    │   Engine    │
│ Port 3000   │    │  Port 8000  │    │  Maven/Java │    │  Port 9200  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

## API Reference

### Start Crawl
```bash
curl -X POST http://localhost:8000/crawl \
  -H "Content-Type: application/json" \
  -d '{"target_url": "https://example.com"}'
```

### Check Crawl Status
```bash
curl http://localhost:8000/status/{run_id}
```

### Search Documents
```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "search terms", "size": 50}'
```

## Debugging and Monitoring

### Check Service Status
```bash
# View all running containers
docker-compose ps

# Check service health
curl http://localhost:8000/    # Backend health
curl http://localhost:9200/    # OpenSearch health
```

### View Service Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f frontend
docker-compose logs -f backend  
docker-compose logs -f norconex-runner
docker-compose logs -f opensearch
```

### Monitor Active Crawls

#### 1. Check Backend Crawl Status
```bash
# List all crawl jobs (requires direct backend access)
docker-compose exec backend python -c "
from main import crawl_jobs
import json
print(json.dumps(crawl_jobs, indent=2, default=str))
"
```

#### 2. Check Norconex Config Files
```bash
# View generated crawler configurations
ls -la norconex-runner/configs/crawler-*.xml

# View completion status files
ls -la norconex-runner/configs/completed-*.json

# View latest config
cat norconex-runner/configs/crawler-$(ls -t norconex-runner/configs/crawler-*.xml | head -1 | cut -d- -f2 | cut -d. -f1).xml
```

#### 3. Monitor OpenSearch Index
```bash
# Check if demo_factory index exists
curl http://localhost:9200/_cat/indices?v

# Count documents in index
curl http://localhost:9200/demo_factory/_count

# View sample documents
curl http://localhost:9200/demo_factory/_search?size=5 | jq .

# Check index mapping
curl http://localhost:9200/demo_factory/_mapping | jq .
```

### Troubleshooting Common Issues

#### Crawl Stuck in "Running" State
```bash
# Check if Norconex container is processing
docker-compose logs norconex-runner | tail -20

# Look for completion files
ls -la norconex-runner/configs/completed-*.json

# Check for Java process errors
docker-compose exec norconex-runner ps aux | grep java
```

#### No Search Results
```bash
# Verify documents are indexed
curl http://localhost:9200/demo_factory/_count

# Check if ElasticsearchCommitter is configured
cat norconex-runner/configs/crawler-*.xml | grep -A5 -B5 "ElasticsearchCommitter"

# Manual document search
curl -X POST http://localhost:9200/demo_factory/_search \
  -H "Content-Type: application/json" \
  -d '{"query": {"match_all": {}}, "size": 5}' | jq .
```

#### Frontend Not Loading
```bash
# Check frontend container
docker-compose logs frontend

# Verify port accessibility
netstat -tlnp | grep :3000

# Check CORS configuration
curl -H "Origin: http://localhost:3000" \
     -H "Access-Control-Request-Method: POST" \
     -X OPTIONS http://localhost:8000/crawl
```

#### Backend API Errors
```bash
# Check backend logs
docker-compose logs backend | grep ERROR

# Test direct API access
curl http://localhost:8000/

# Check OpenSearch connectivity from backend
docker-compose exec backend curl http://opensearch:9200/
```

### Performance Monitoring

#### Resource Usage
```bash
# Monitor container resource usage
docker stats

# Check disk space for crawl data
du -sh norconex-runner/configs/
```

#### Crawl Performance
```bash
# Monitor crawl speed (pages per minute)
# Check backend logs for progress updates
docker-compose logs backend | grep -E "(progress|pages|indexed)"

# OpenSearch performance
curl http://localhost:9200/_nodes/stats/indices | jq .nodes[].indices.indexing
```

## Configuration

### Crawler Limits
Default crawl settings (configurable in `main.py:create_config_from_nab_template()`):
- **Max Documents**: 50 (test limit)
- **Max Depth**: 2 levels
- **Domain Restriction**: Stay on target domain only
- **Timeout**: 15 minutes maximum
- **Excluded Files**: CSS, JS, images, media files

### OpenSearch Index
- **Index Name**: `demo_factory`
- **Document Fields**: title, content, url, lastModified, contentType, size
- **Search Fields**: title (boosted 2x), content, url

### Environment Variables
```bash
# Optional overrides in docker-compose.yml
OPENSEARCH_HOST=opensearch:9200
NORCONEX_MODE=maven
LOG_LEVEL=INFO
```

## Data Persistence

### Crawl Configurations
- Location: `norconex-runner/configs/`
- Format: `crawler-{run_id}.xml` (generated configs)
- Format: `completed-{run_id}.json` (completion markers)

### OpenSearch Data
- Index: `demo_factory`
- Documents persist until manually deleted
- No automatic cleanup (implement retention policy if needed)

## Scaling and Production Notes

### Resource Requirements
- **Light Usage**: 2GB RAM, 1 CPU core
- **Heavy Crawling**: 8GB+ RAM, 4+ CPU cores
- **Storage**: 1GB per 10,000 crawled pages

### Security Considerations
- No authentication implemented (add for production)
- OpenSearch accessible without credentials
- CORS allows all origins (restrict for production)

### Performance Tuning
- Increase Norconex thread count for faster crawling
- Tune OpenSearch heap size for large indexes
- Implement crawl queues for multiple concurrent crawls