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
2. Enter a target URL (e.g., `https://example.com`)
3. Click "Start Crawl"
4. Monitor real-time progress in the Active Crawl section

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