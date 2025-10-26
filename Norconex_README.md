# Norconex Web Crawler Platform - README

A full-stack web crawling platform powered by Norconex HTTP Collector v3, with real-time WebSocket logging, Search365 schema processing, and Next.js frontend UI.

## Quick Start

### Prerequisites
- Docker and Docker Compose
- 8GB+ RAM recommended for large crawls
- Ports 3000, 5000, 9200, 5601 available

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
- **Frontend UI**: http://localhost:3000
- **Backend API**: http://localhost:5000 (FastAPI)
- **OpenSearch**: http://localhost:9200
- **OpenSearch Dashboards**: http://localhost:5601

## Architecture Overview

```
┌─────────────────┐    WebSocket     ┌──────────────────┐
│   Next.js UI    │◀───────────────▶│   FastAPI        │
│   Port 3000     │    REST API      │   Backend        │
│                 │────────────────▶│   Port 5000      │
└─────────────────┘                  └──────────────────┘
                                              │
                                              ▼
                          ┌────────────────────────────────┐
                          │   Norconex HTTP Collector v3   │
                          │   (Docker: norconex-runner)    │
                          │   - Dynamic config generation  │
                          │   - CMS template support       │
                          └────────────────────────────────┘
                                              │
                                              ▼
                          ┌────────────────────────────────┐
                          │      OpenSearch (Port 9200)    │
                          │  ┌──────────────────────────┐  │
                          │  │  demo_factory_raw        │  │
                          │  │  (Raw crawl data)        │  │
                          │  └──────────────────────────┘  │
                          │              │                 │
                          │              ▼                 │
                          │  ┌──────────────────────────┐  │
                          │  │  Schema Processor        │  │
                          │  │  (Auto-enrichment)       │  │
                          │  └──────────────────────────┘  │
                          │              │                 │
                          │              ▼                 │
                          │  ┌──────────────────────────┐  │
                          │  │  demo_factory            │  │
                          │  │  (Search365 enriched)    │  │
                          │  └──────────────────────────┘  │
                          └────────────────────────────────┘
```

## Norconex Runner Directory Structure

The `norconex-runner/` directory contains the Java-based Norconex crawler implementation and all related configuration files.

```
norconex-runner/
├── pom.xml                        # Parent Maven configuration
├── mvnw / mvnw.cmd                # Maven wrapper scripts
├── .mvn/wrapper/                  # Maven wrapper configuration
├── Dockerfile                     # Container image definition
├── trigger-crawler.sh             # Shell script to trigger crawler execution
├── README.md                      # Module-specific documentation
├── runner/                        # Main executable module
│   ├── pom.xml                    # Runner module POM with shade plugin
│   ├── src/main/java/
│   │   └── io/demo/nx/
│   │       └── Runner.java        # Main application entry point
│   ├── src/main/resources/
│   │   └── logback.xml            # Logging configuration
│   ├── src/test/java/             # Unit tests
│   └── target/                    # Build output directory (generated)
│       └── runner-1.0.0-SNAPSHOT.jar  # Executable fat JAR with dependencies
├── configs/                       # Crawler configuration files
│   ├── base-crawl-template.xml    # Base template for crawler configuration
│   ├── search365-basic-template.xml  # Search365-specific template
│   ├── working-example.xml        # Working example configuration
│   ├── crawler-helper.sh          # Helper script for crawler operations
│   ├── crawler-{run_id}.xml       # Generated crawler configs with unique IDs
│   ├── completed-{run_id}.json    # Status files for completed crawls
│   ├── stop-{run_id}.json         # Stop signal files for crawler instances
│   └── failed-{run_id}.json       # Status files for failed crawls
├── logs/                          # Runtime log files
│   ├── norconex-runner.log        # Main application log with rotation
│   └── trigger.log                # Logs from the trigger script
└── data/                          # Crawler working directory and output
    ├── workdir/                   # Norconex working dir (state, queue, cache, MD5)
    └── xml-output/                # Output directory for crawled data in XML
```


## How to Use

### 1. Start a Website Crawl

1. Open http://localhost:3000 in your browser
2. Enter a target URL
3. (Optional) Select a CMS template for optimized crawling
4. Click "Start Crawl"
5. Monitor real-time progress:
   - **Active Crawl Status**: Shows crawl state (pending/running/completed)
   - **Backend Logs**: Live WebSocket logs from Norconex crawler
   - **Progress Tracking**: Pages indexed count

### 2. CMS Template Support

The platform includes pre-configured templates for common CMS platforms:

- **WordPress** - Optimized for WP sites
- **Joomla** - Joomla-specific extraction
- **Drupal** - Drupal content patterns
- **Magento** - E-commerce focused
- **Custom** - Blank template for custom configuration

Each template includes:
- Optimized URL filters
- CMS-specific metadata extraction
- Performance tuning for that platform

### 3. Real-Time WebSocket Logs

The **Backend Logs** dropdown shows live crawler output:
- Connection status (Live/Disconnected)
- Real-time log streaming from Norconex
- Per-run_id filtering (no cross-contamination)
- Search functionality to filter logs
- Auto-scroll with manual override

### 4. Search Crawled Content

Use the **Crawled Data from OpenSearch** section:
1. Enter search terms in the search box
2. Results show enriched Search365 fields:
   - Title, content, description
   - URL, metadata, dates
   - Social media tags (Open Graph, Twitter cards)
   - Technical metadata (content type, encoding, size)
3. Click "Show All" to view all indexed documents

### 5. Schema Processing

After crawl completion, the **Schema Processor** automatically:
- Reads raw data from `demo_factory_raw` index
- Enriches with all critical Search365 fields from 229-field schema
- Indexes to `demo_factory` for searching
- Populates all critical fields (title, content, metadata, HTML structure) with additional fields when available

**Populated Fields Include:**
- Core: id, url, title, content, description
- Metadata: contenttype, encoding, docsize
- Social: Open Graph, Twitter cards
- Dates: crawltime, lastmodified, created
- HTML: h2 headings, extracted elements
- Location: state, suburb, postcode
- Contact: email, phone, address

## Sample Sites for Testing

**Small Sites (Quick Testing)**
- `https://httpbin.org/` - HTTP testing service
- `https://example.com/` - Simple single page
- `https://jsonplaceholder.typicode.com/` - JSON API

**Documentation Sites (Rich Content)**
- `https://docs.python.org/3/tutorial/`
- `https://developer.mozilla.org/en-US/docs/Web/HTML`
- `https://www.w3schools.com/html/`
- `https://fastapi.tiangolo.com/`

**News Sites**
- `https://news.ycombinator.com/`
- `https://www.reuters.com/technology/`

**E-commerce (Testing)**
- `https://books.toscrape.com/` - Fake bookstore
- `https://scrapeme.live/shop/` - Pokemon shop

**Important:**
- Start with small sites for initial testing
- Respect robots.txt and website ToS
- Current limits: 50 pages max, 2 levels deep, 15-minute timeout

## API Reference

### Norconex Crawl Endpoints

#### Start Crawl
```bash
POST http://localhost:5000/norconex/start
Content-Type: application/json

{
  "target_url": "https://example.com",
  "cms_template": "wordpress",  # Optional: wordpress, joomla, drupal, magento
  "max_pages": 50,              # Optional: default 50
  "max_depth": 2                # Optional: default 2
}

Response:
{
  "run_id": "abc123...",
  "status": "pending",
  "target_url": "https://example.com",
  "config_file": "crawler-abc123.xml"
}
```

#### Check Crawl Status
```bash
GET http://localhost:5000/norconex/status/{run_id}

Response:
{
  "run_id": "abc123...",
  "status": "running",        # pending, running, completed, failed
  "progress": 45,             # 0-100
  "pages_indexed": 23,
  "target_url": "https://example.com",
  "started_at": "2025-10-06T12:00:00"
}
```

#### Stop Crawl
```bash
POST http://localhost:5000/norconex/stop/{run_id}
```

#### WebSocket Logs (Real-time)
```javascript
const ws = new WebSocket(`ws://localhost:5000/norconex/ws/${run_id}`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  // Log message format:
  {
    "type": "backend_log",
    "log": {
      "timestamp": "12:34:56",
      "level": "INFO",
      "source": "uvicorn",
      "message": "[run_id] Crawling https://example.com"
    }
  }
};
```

### Search Endpoints

#### Search Documents
```bash
POST http://localhost:5000/search
Content-Type: application/json

{
  "query": "search terms",
  "size": 50,
  "index": "demo_factory"  # Optional: defaults to demo_factory
}

Response:
{
  "hits": [...],
  "total": 42,
  "took": 5
}
```

#### Get All Documents
```bash
GET http://localhost:5000/documents?size=100
```

### CMS Detection

#### Detect CMS
```bash
POST http://localhost:5000/detect-cms
Content-Type: application/json

{
  "url": "https://example.com"
}

Response:
{
  "cms": "WordPress",
  "version": "6.2",
  "confidence": 0.95,
  "indicators": [...]
}
```

## Configuration Files

### Norconex Crawler Config
Generated dynamically per crawl in `norconex-runner/configs/`:
- `crawler-{run_id}.xml` - Norconex HTTP Collector v3 config
- `completed-{run_id}.json` - Completion marker
- `failed-{run_id}.json` - Failure marker (if crawl fails)
- `stop-{run_id}.json` - Stop signal file

### CMS Templates
Located in `ai-agent-demo-factory-backend/services/cms_templates/`:
- `base-crawl-template.xml` - Generic crawler template
- `wordpress-template.xml` - WordPress optimized
- `joomla-template.xml` - Joomla optimized
- (Others as needed)

### OpenSearch Indexes

#### demo_factory_raw
- Raw crawl data from Norconex
- Direct OpenSearch committer output
- All metadata preserved

#### demo_factory
- Enriched Search365 schema (98 fields)
- Auto-generated by schema processor
- Optimized for search

#### crawl_logs
- Crawl execution logs
- Status tracking
- Error recording

## WebSocket Implementation

### Connection Per Run
Each crawl gets its own WebSocket connection:
```javascript
const ws = new WebSocket(`ws://localhost:5000/norconex/ws/${run_id}`);
```

### Log Broadcasting
Backend logs are filtered by run_id:
- Logs formatted as `[run_id] message`
- Only sent to matching WebSocket connections
- No cross-contamination between crawls

### Auto-reconnection
Frontend handles disconnections gracefully:
- Shows connection status indicator
- Attempts reconnection on disconnect
- Buffers recent logs (last 100 per run)

## Debugging and Monitoring

### Service Status
```bash
# All services
docker-compose ps

# Service health checks
curl http://localhost:5000/           # Backend
curl http://localhost:9200/           # OpenSearch
curl http://localhost:3000/           # Frontend
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f norconex-runner
docker-compose logs -f opensearch
docker-compose logs -f frontend
```

### Monitor Crawls

#### Check Active Crawls
```bash
# Via API
curl http://localhost:5000/norconex/status/{run_id}

# Check config files
ls -la norconex-runner/configs/crawler-*.xml
ls -la norconex-runner/configs/completed-*.json
```

#### Monitor OpenSearch Indexes
```bash
# List all indexes
curl http://localhost:9200/_cat/indices?v

# Count documents
curl http://localhost:9200/demo_factory/_count
curl http://localhost:9200/demo_factory_raw/_count

# View sample documents
curl http://localhost:9200/demo_factory/_search?size=5 | jq .

# Check schema mapping
curl http://localhost:9200/demo_factory/_mapping | jq .
```

#### WebSocket Logs
View real-time logs in the UI:
1. Start a crawl
2. Expand "Backend Logs" dropdown
3. Watch live Norconex output
4. Use search to filter logs

### Troubleshooting

#### Crawl Stuck in "Running"
```bash
# Check Norconex logs
docker-compose logs norconex-runner | tail -50

# Look for completion marker
ls -la norconex-runner/configs/completed-*.json

# Check for Java process
docker-compose exec norconex-runner ps aux | grep java
```

#### No Search Results
```bash
# Verify raw index has data
curl http://localhost:9200/demo_factory_raw/_count

# Check if schema processor ran
docker-compose logs backend | grep "Schema processing"

# Verify enriched index exists
curl http://localhost:9200/demo_factory/_count
```

#### WebSocket Not Connecting
```bash
# Check backend logs
docker-compose logs backend | grep WebSocket

# Verify uvicorn has WebSocket support
docker-compose exec backend pip list | grep -E "uvicorn|websockets"

# Test WebSocket endpoint
wscat -c ws://localhost:5000/norconex/ws/test-run-id
```

#### Schema Processor Issues
```bash
# Check for indexing errors
docker-compose logs backend | grep -E "\[INDEXING|Schema"

# Verify OpenSearch authentication
curl -u admin:admin http://localhost:9200/_cluster/health

# Check processor logs
docker-compose logs backend | grep schema_processor
```

## Re-crawling Same Sites

**IMPORTANT**: Norconex uses MD5 checksums to detect duplicate URLs. To re-crawl the same site:

### Option 1: Clear Norconex Cache (Recommended)
```bash
# Delete checksums and workdir (use norconex-maven container name)
docker exec norconex-maven rm -rf /opt/norconex/data/workdir/*
docker exec norconex-maven rm -rf /opt/norconex/data/xml-output/*

# Delete OpenSearch indexes
curl -X DELETE http://localhost:9200/demo_factory
curl -X DELETE http://localhost:9200/demo_factory_raw

# Verify cleanup
curl http://localhost:9200/_cat/indices?v
```

### Option 2: Use Different URL
```bash
# If the site has multiple entry points:
# First crawl:  https://example.com/
# Second crawl: https://example.com/about
```

### Option 3: Nuclear Reset (Clean Everything)
**Use this when you have conflicting volumes from multiple repo copies or need a complete fresh start:**

```bash
# Stop all containers
docker-compose down

# Clean old volumes from previous repo instances
docker volume rm programming-project-ai-agent-demo_opensearch-data 2>/dev/null
docker volume rm programming-project-ai-agent-demo_opensearch_data 2>/dev/null
docker volume rm programming-project-ai-agent-demo_elasticsearch-data 2>/dev/null

# Clean local Norconex data (may require sudo if files are root-owned)
sudo rm -rf norconex-runner/data/workdir/*
sudo rm -rf norconex-runner/data/xml-output/*

# Start fresh
docker-compose up -d

# Verify all services are running
docker-compose ps
```

**When to use Nuclear Reset:**
- Copied repo to a new location and volumes are conflicting
- Data not appearing in OpenSearch after successful crawls
- Multiple repo instances causing volume name conflicts
- Complete fresh start needed for testing/demo

## Data Persistence

### Crawl Configurations
- **Location**: `norconex-runner/configs/`
- **Generated**: `crawler-{run_id}.xml`
- **Markers**: `completed-{run_id}.json`, `failed-{run_id}.json`
- **Stop signals**: `stop-{run_id}.json` (gitignored)

### OpenSearch Data
- **Indexes**: `demo_factory`, `demo_factory_raw`, `crawl_logs`
- **Persistence**: Docker volume `opensearch-data`
- **Retention**: Manual cleanup required

### Norconex Workdir
- **Location**: `norconex-runner/data/workdir/`
- **Contents**: Checksums, crawl state, queues
- **Purpose**: Duplicate detection, resume capability

## Security Notes

**Current Setup is Development-Only**

**Not Implemented (Add for Production):**
- OpenSearch authentication (currently admin:admin)
- Backend API authentication
- CORS restrictions (currently allows all origins)
- Rate limiting
- Input validation/sanitization
- HTTPS/SSL certificates

## Technology Stack

### Frontend
- **Framework**: Next.js 14 (React 18)
- **Styling**: Tailwind CSS
- **Icons**: React Icons
- **WebSocket**: Native WebSocket API

### Backend
- **Framework**: FastAPI (Python 3.12)
- **ASGI Server**: Uvicorn with WebSocket support
- **HTTP Client**: Requests
- **Async**: asyncio

### Crawler
- **Engine**: Norconex HTTP Collector v3
- **Runtime**: Java/Maven
- **Config**: XML (dynamically generated)
- **Committer**: OpenSearch REST API

### Database
- **Search Engine**: OpenSearch 2.x
- **UI**: OpenSearch Dashboards
- **Authentication**: Basic auth (admin:admin)

## Performance Tuning

### Norconex Settings
- **Threads**: 2 (configurable in XML)
- **Max Depth**: 2 levels
- **Max Documents**: 50 (test limit)
- **Timeout**: 15 minutes

### OpenSearch Settings
- **Heap**: 1GB (configurable in docker-compose.yml)
- **Shards**: 1 (single node)
- **Replicas**: 0 (single node)

### Backend Settings
- **Workers**: 1 (Uvicorn)
- **WebSocket Connections**: Unlimited
- **Log Buffer**: 100 logs per run_id

## Known Limitations

1. **Duplicate Detection**: Norconex caches URLs - requires manual cache clearing for re-crawls
2. **Schema Mapping**: Populates all critical Search365 fields; some optional fields not extracted (H1 extraction improvements pending, publication date parsing)
3. **Concurrent Crawls**: Limited by Norconex container resources
4. **WebSocket Scaling**: In-memory connections don't scale across multiple backend instances
5. **No Authentication**: Development setup only
6. **Error Handling**: Basic error reporting, needs improvement

## Roadmap

### High Priority
- [ ] Add H1/H3 extraction to schema processor
- [ ] Extract publication dates (datepub, datepublished)
- [ ] Implement cache clearing endpoint
- [ ] Add authentication/authorization
- [ ] Improve error handling

### Medium Priority
- [ ] Support for JavaScript-heavy sites (integrate Crawl4AI)
- [ ] Multi-crawler support (concurrent crawls)
- [ ] Crawl scheduling/automation
- [ ] Export functionality (CSV, JSON)
- [ ] Advanced search filters

### Low Priority
- [ ] AI-assisted configuration
- [ ] Content categorization
- [ ] Duplicate content detection
- [ ] Custom field extraction rules
