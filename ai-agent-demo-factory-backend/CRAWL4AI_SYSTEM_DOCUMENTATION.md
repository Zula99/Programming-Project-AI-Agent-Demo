# AI Agent Demo Factory - Crawl4AI System Documentation

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [System Architecture](#system-architecture)
3. [Module Reference](#module-reference)
4. [Data Flow](#data-flow)
5. [API Reference](#api-reference)
6. [Developer Guide](#developer-guide)
7. [Configuration](#configuration)
8. [Integration Guide](#integration-guide)
9. [Code Examples](#code-examples)
10. [Performance & Optimization](#performance--optimization)
11. [Error Handling](#error-handling)
12. [Deployment](#deployment)
13. [Troubleshooting](#troubleshooting)

---

## Executive Summary

The AI Agent Demo Factory Backend is a sophisticated web crawling and demo generation system built on Crawl4AI. It intelligently crawls websites, classifies content using AI, generates static mirrors, and provides live proxy serving with integrated search capabilities. The system achieves **90% demo quality** through adaptive crawling strategies and AI-powered content classification.

### Key Architecture Points

**IMPORTANT: How Strategies Work**

1. **Discovery Strategy** (The Real Strategy):
   - **SITEMAP_FIRST**: Site has sitemap.xml → Extract all URLs → AI classify → Crawl in priority order
   - **PROGRESSIVE**: No sitemap → Start with homepage → Discover links during crawl → AI classify on-the-fly

2. **Crawl4AI Browser Configuration** (Default settings, overridable per strategy):
   - **javascript=True** (full JavaScript rendering - default)
   - **wait_for='networkidle'** (wait for all network activity - default)
   - **headless=True** (headless Chrome - default)
   - **timeout=30s** (per page - default, can be increased for JS-heavy sites)
   - **request_gap=0.6-4.0s** (default 0.6s, adaptive based on site type)

3. **Crawling Architecture**:
   - `CrawlStrategy` enum in `smart_mirror_agent.py` is used during reconnaissance to configure browser settings
   - `DiscoveryStrategy` enum in `hybrid_crawler.py` determines URL discovery approach (SITEMAP_FIRST vs PROGRESSIVE)
   - SmartMirrorAgent **orchestrates** the workflow: reconnaissance → strategy selection → HybridCrawler execution → quality assessment
   - HybridCrawler **executes** the crawl: sitemap analysis → AI classification → URL discovery → content extraction

### Key Features

- **Intelligent Crawling**: AI-powered content classification for optimal demo content selection
- **Hybrid Discovery**: Sitemap-first discovery with fallback to progressive discovery (no sitemap)
- **Real-time Updates**: WebSocket-based progress streaming to frontend
- **Quality Plateau Detection**: Intelligent stopping when quality stops improving
- **Graceful Cancellation**: Multi-layer stop flag propagation for clean shutdown
- **OpenSearch Integration**: Semantic search capabilities across all crawled content
- **Live Proxy Serving**: Dynamic content serving with search bar injection
- **Full Browser Crawling**: All pages crawled with JavaScript rendering (headless Chrome, networkidle wait)

### Technology Stack

- **FastAPI**: REST API and WebSocket server
- **Crawl4AI**: AsyncWebCrawler for content extraction
- **OpenAI GPT-4o-mini**: AI content classification
- **OpenSearch**: Content indexing and search
- **AsyncIO**: Concurrent crawling and task management

---

## System Architecture

### High-Level Components

```
┌─────────────────────────────────────────────────────────────────┐
│                      Frontend (React/WebSocket)                  │
└───────────────────────┬─────────────────────────────────────────┘
                        │ WebSocket + REST API
┌───────────────────────▼─────────────────────────────────────────┐
│                    FastAPI Backend (main.py)                     │
│  - Crawl Automation API                                          │
│  - WebSocket Log Broadcasting                                    │
│  - Task Management                                               │
│  - Session Management                                            │
└───────────────────────┬─────────────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        ▼                               ▼
┌─────────────────┐            ┌──────────────────┐
│ SmartMirrorAgent│            │  Proxy Server    │
│  - Strategy     │            │  - Live Serving  │
│  - Quality      │            │  - Search Inject │
│  - Learning     │            │  - Cache Serving │
└────────┬────────┘            └──────────────────┘
         │
         ▼
┌─────────────────┐
│ HybridCrawler   │
│  - Sitemap      │
│  - AI Filter    │
│  - Dedup        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Crawler Utils   │
│  - generic_crawl│
│  - Crawl4AI     │
│  - Progress     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Crawl4AI Library│
│ AsyncWebCrawler │
└─────────────────┘
```

### Request Flow

```
1. Frontend → POST /crawl4ai/start → main.py
2. main.py → create_task() → TaskManager
3. TaskManager → SmartMirrorAgent.process_url()
4. SmartMirrorAgent → HybridCrawler.analyze_and_crawl()
5. HybridCrawler → LinkExtractor.process_sitemap_with_ai()
6. HybridCrawler → crawler_utils.generic_crawl()
7. generic_crawl() → AsyncWebCrawler.arun() [Crawl4AI]
8. Results saved to output/{domain}/ directory
```

### Progress Flow

```
1. AsyncWebCrawler → progress callback
2. crawler_utils.generic_crawl() → progress_callback()
3. HybridCrawler → update_progress()
4. main.py → update_progress()
5. WebSocket → broadcast_to_websockets()
6. Frontend → updates UI (progress bar, logs)
```

---

## Module Reference

### 1. main.py - FastAPI Backend

**Purpose**: Central API server for crawl automation, task management, and WebSocket communication.

**Key Endpoints**:

```python
# Start Crawl
POST /crawl4ai/start
Request: {
    "target_url": "https://example.com",
    "max_pages": 50  # Optional
}
Response: {
    "run_id": "abc123",
    "message": "Crawl4AI agent started",
    "status": "pending"
}

# Stop Crawl
POST /crawl4ai/stop/{run_id}
Response: {
    "message": "Crawl force stopped",
    "summary": {
        "pages_crawled": 25,
        "total_pages": 50,
        "elapsed_time": "5m 30s"
    }
}

# Get Status
GET /crawl4ai/status/{run_id}
Response: {
    "session": {
        "run_id": "abc123",
        "target_url": "https://example.com",
        "status": "running"
    },
    "logs": [...],
    "progress": {
        "pages_crawled": 25,
        "total_pages": 50,
        "percentage": 50.0,
        "crawl_speed": 5.2  # pages/minute
    }
}

# WebSocket Logs
WS /crawl4ai/ws/{run_id}
Messages: Real-time log events
```

**Key Functions**:

- **`run_crawl4ai_agent_real()`**: Background task that executes SmartMirrorAgent
- **`update_progress()`**: Updates and broadcasts crawl progress
- **`add_agent_log()`**: Adds log entry and broadcasts to WebSocket clients
- **`broadcast_to_websockets()`**: Sends messages to all connected WebSocket clients

**Session Management**:
```python
crawl4ai_sessions[run_id] = {
    "run_id": str,
    "target_url": str,
    "status": str,  # "pending", "running", "completed", "stopped", "error"
    "started_at": float,
    "logs": List[dict],
    "current_url": str,
    "max_pages": Optional[int],
    "progress": {
        "percentage": float,
        "pages_crawled": int,
        "pages_remaining": int,
        "total_pages": int,
        "crawl_speed": float,
        "ai_classifications": int,
        "cache_hits": int
    }
}
```

---

### 2. SmartMirrorAgent (crawl4ai-agent/smart_mirror_agent.py)

**Purpose**: High-level orchestrator that manages reconnaissance, strategy selection, and quality assessment. SmartMirrorAgent analyzes site characteristics and selects optimal browser configurations before delegating execution to HybridCrawler.

**Public API**:

```python
class SmartMirrorAgent:
    def __init__(self, memory_path: str = "agent_memory.json"):
        """Initialize agent with memory for learning"""

    async def process_url(self, url: str, run_id: str = None,
                         max_pages: int = None) -> Tuple[bool, QualityMetrics, str]:
        """
        Main entry point - crawl a URL and return results

        Returns:
            success: bool - Whether crawl completed successfully
            metrics: QualityMetrics - Quality assessment
            output_path: str - Path to output directory
        """
```

**SmartMirrorAgent Workflow**:

1. **Reconnaissance**: Analyzes site characteristics (type, frameworks, JS complexity)
2. **Strategy Selection**: Chooses optimal browser configuration (CrawlStrategy)
3. **Initialize HybridCrawler**: Creates crawler instance with configuration
4. **Execute Hybrid Crawl**: Delegates to HybridCrawler.crawl() for URL discovery and crawling
5. **Quality Assessment**: Evaluates results against 90% quality targets
6. **Learning**: Stores successful patterns for future crawls

**Architecture**: SmartMirrorAgent orchestrates the complete workflow (reconnaissance → strategy → execution → quality), while HybridCrawler executes the actual crawling (sitemap analysis → AI classification → URL discovery → content extraction).

---

### 3. HybridCrawler (crawl4ai-agent/hybrid_crawler.py) - THE CORE CRAWLER

**Purpose**: **This is the actual crawler that does all the work**. Implements intelligent URL discovery using a two-strategy approach based on sitemap availability.

**Public API**:

```python
class HybridCrawler:
    def __init__(self, output_dir: str = "./hybrid_crawl_output"):
        """Initialize hybrid crawler"""

    async def crawl(self, start_url: str, run_id: Optional[str] = None,
                   max_pages: Optional[int] = None,
                   crawl_config: Optional[CrawlConfig] = None) -> Tuple[bool, Dict[str, Any]]:
        """
        Main entry point - executes hybrid crawl strategy

        Returns:
            success: bool - Whether crawl completed
            results: Dict - Crawl results and statistics
        """
```

**Discovery Strategy Selection** (The Real Strategy):

```python
class DiscoveryStrategy(Enum):
    SITEMAP_FIRST = "sitemap_first"    # Sites WITH accessible sitemaps
    PROGRESSIVE = "progressive"        # Sites WITHOUT sitemaps (progressive link discovery)

# Strategy is automatically selected based on sitemap availability
if sitemap_found:
    strategy = DiscoveryStrategy.SITEMAP_FIRST
else:
    strategy = DiscoveryStrategy.PROGRESSIVE
```

**Fixed Crawl4AI Configuration** (Used for ALL sites):

```python
# Every page is crawled with FULL BROWSER capabilities:
CrawlConfig(
    javascript=True,              # Enable JavaScript rendering
    wait_for='networkidle',       # Wait for all network activity to finish
    timeout=30,                   # 30 second timeout per page
    headless=True,                # Run Chrome in headless mode
    request_gap=0.8               # 0.8 second delay between requests
)
```

**Crawl Workflow**:

```
Phase 1: Site Analysis
├─ Try to fetch sitemap.xml
├─ Analyze robots.txt for intelligence
└─ Determine: SITEMAP_FIRST or PROGRESSIVE

Phase 2: AI URL Classification (if sitemap found)
├─ Extract all URLs from sitemap
├─ AI classify each URL for demo worthiness
├─ Build prioritized crawl plan
└─ Cache classifications for later use

Phase 3: Crawl Plan Generation
├─ If SITEMAP_FIRST: Use AI-classified sitemap URLs
└─ If PROGRESSIVE: Start with homepage, discover links as we crawl

Phase 4: Execute Crawl (generic_crawl in crawler_utils.py)
├─ For each URL in priority queue:
│   ├─ Check stop flag
│   ├─ Crawl with Crawl4AI (FULL BROWSER: headless Chrome, networkidle)
│   ├─ Extract content and links
│   ├─ Deduplicate content
│   └─ Check quality plateau
└─ Stop when: max_pages reached, quality plateau, or stop flag set

Phase 5: Quality Assessment
├─ Calculate coverage metrics
├─ Evaluate content completeness
└─ Generate quality scores
```

**Key Features**:

- **Sitemap-First Discovery**: Analyzes entire sitemap upfront, AI-filters URLs, crawls in priority order
- **Progressive Discovery**: No sitemap? Starts with homepage, discovers links during crawling
- **AI Classification**: GPT-4o-mini filters URLs by demo worthiness (cached during sitemap phase)
- **Link Discovery**: Extracts links from crawled pages and adds worthy ones to queue
- **Deduplication**: Content hash and similarity-based duplicate detection
- **Coverage Tracking**: Monitors section coverage to ensure comprehensive demos
- **Quality Plateau Detection**: Stops when quality stops improving (30+ pages with no improvement)

---

### 4. Crawler Utils (crawl4ai-agent/crawler_utils.py)

**Purpose**: Core crawling utilities that interface directly with Crawl4AI's AsyncWebCrawler. This is where the actual page-by-page crawling happens.

**Public API**:

```python
@dataclass
class CrawlConfig:
    # Core settings (fixed for all crawls)
    timeout: int = 30
    request_gap: float = 0.8
    headless: bool = True
    wait_for: str = 'networkidle'  # Always networkidle for JS rendering
    screenshot: bool = False
    javascript: bool = True         # Always True - full browser rendering
    max_concurrent: int = 1

    # Session management
    run_id: Optional[str] = None
    progress_callback: Optional[Callable] = None
    classification_cache: Dict = None  # AI classifications from sitemap phase

async def generic_crawl(config: CrawlConfig) -> Tuple[List[CrawlResult], Dict]:
    """
    Main crawl loop - processes URLs from priority queue

    Returns:
        results: List of successfully crawled pages
        stats: Crawl statistics and metrics
    """
```

**Crawl4AI Integration**:

```python
async with AsyncWebCrawler(
    headless=config.headless,
    verbose=True,
    browser_type="chromium"
) as crawler:

    result = await crawler.arun(
        url=url,
        timeout=config.timeout,
        wait_for=config.wait_for,
        screenshot=config.screenshot,
        word_count_threshold=10,
        bypass_cache=True
    )

    # Extract content
    markdown_content = result.markdown
    html_content = result.html
    metadata = result.metadata

    # Save to disk
    save_crawl_output(output_dir, url, markdown_content, html_content, metadata)
```

**Output Structure**:

```
output/{domain}/
├── {url_hash_1}/
│   ├── index.md          # Markdown content
│   ├── meta.json         # Metadata (title, URL, timestamps)
│   ├── raw.html          # Original HTML
│   └── screenshot.png    # Optional screenshot
├── {url_hash_2}/
│   └── ...
└── crawl_metadata.json   # Overall crawl statistics
```

**Progress Callback**:

```python
if progress_callback:
    await progress_callback(
        pages_crawled=current_count,
        total_known=total_discovered,
        discovered_urls=len(discovered_queue),
        crawl_speed=pages_per_minute,
        ai_classifications=ai_call_count,
        cache_hits=cache_hit_count,
        current_url=url
    )
```

**Stop Signal Checking**:

```python
# Check stop flag in main crawl loop
if config.run_id:
    from task_manager import task_manager
    if task_manager.should_stop(config.run_id):
        logger.info("FORCE STOP detected - terminating crawl")
        break
```

---

### 5. AI Content Classifier (crawl4ai-agent/ai_content_classifier.py)

**Purpose**: AI-powered content classification for intelligent demo content selection.

**Public API**:

```python
class AIContentClassifier:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """Initialize with OpenAI API key"""

    async def classify_url_only(self, url: str) -> ClassificationResult:
        """
        Fast URL-only classification for sitemap analysis
        Cost: ~$0.0002 per URL
        """

    async def classify_content(self, url: str, content: str = "",
                              title: str = "") -> ClassificationResult:
        """
        Full content classification with AI
        Cost: ~$0.002 per page
        """

@dataclass
class ClassificationResult:
    is_worthy: bool           # True if page is demo-worthy
    confidence: float         # 0.0-1.0 confidence score
    reasoning: str            # AI's reasoning for decision
    method_used: str          # "ai", "heuristic", "cache"
    estimated_cost: float     # Cost in USD
```

**Site Type Detection**:

```python
class BusinessSiteType(Enum):
    BANKING = "banking"
    ECOMMERCE = "ecommerce"
    CORPORATE = "corporate"
    NEWS = "news"
    EDUCATIONAL = "educational"
    HEALTHCARE = "healthcare"
    GOVERNMENT = "government"
    TECHNOLOGY = "technology"

def detect_site_type(url: str, content: str, title: str) -> BusinessSiteType:
    """
    Detects site type using domain keywords and content analysis
    Caches result for domain-level reuse
    """
```

**Hybrid Classification System**:

```
┌─────────────┐
│ Input: URL  │
└──────┬──────┘
       │
       ▼
   ┌───────────┐
   │Cache Hit? │
   └─────┬─────┘
         │ No
         ▼
   ┌─────────────┐
   │Detect Site  │
   │    Type     │
   └──────┬──────┘
          │
          ▼
   ┌─────────────┐
   │Create Site- │
   │Specific     │
   │Prompt       │
   └──────┬──────┘
          │
          ▼
   ┌─────────────┐
   │OpenAI API   │
   │GPT-4o-mini  │
   └──────┬──────┘
          │
          ▼ (If fails)
   ┌─────────────┐
   │ Heuristic   │
   │  Fallback   │
   └──────┬──────┘
          │
          ▼
   ┌─────────────┐
   │Cache Result │
   │Return Result│
   └─────────────┘
```

**Site-Specific Prompts**:

**For Banking Sites**:
```
MARK AS WORTHY - Banking customers search for:
- Personal banking (accounts, savings, loans, credit cards)
- Business banking (commercial lending, cash management)
- Investment services (wealth management, trading)
- Digital banking tools (mobile app, online banking, calculators)
- Branch/ATM locations and contact information
- Interest rates and fees
- Financial planning and advice

MARK AS NOT WORTHY:
- Terms and conditions, privacy policies
- Press releases without product information
- Internal HR/careers pages
- Legal disclaimers
```

**Cost Tracking**:

```python
# GPT-4o-mini pricing (as of 2024)
input_cost = (prompt_tokens / 1000) * 0.00015
output_cost = (completion_tokens / 1000) * 0.0006
estimated_cost = input_cost + output_cost

# Average costs:
# URL-only classification: ~$0.0002
# Full content classification: ~$0.002
```

**Caching Strategy**:

```python
# Domain-level cache
output/{domain}/ai_cache/
├── classification_cache.json    # URL → classification results
└── domain_site_type.json        # Domain → detected site type

# Cache key generation
cache_key = hashlib.md5(f"{url}:{content_hash}".encode()).hexdigest()
```

---

### 6. Task Manager (task_manager.py)

**Purpose**: Manages asyncio background tasks for crawl sessions with clean cancellation support.

**Public API**:

```python
class TaskManager:
    def register_task(self, run_id: str, task: asyncio.Task):
        """Register a running task"""

    def should_stop(self, run_id: str) -> bool:
        """Check if task should stop"""

    async def cancel_task(self, run_id: str) -> bool:
        """Force cancel a running task immediately"""

    def cleanup_task(self, run_id: str):
        """Remove task from tracking"""

    def is_running(self, run_id: str) -> bool:
        """Check if task is currently running"""
```

**Stop Flag Mechanism**:

```python
# Global task manager instance
task_manager = TaskManager()

# Checked throughout crawl pipeline:
# 1. HybridCrawler - before each URL
# 2. LinkExtractor - during sitemap processing
# 3. generic_crawl - in main crawl loop
# 4. SmartMirrorAgent - before quality assessment

if task_manager.should_stop(run_id):
    logger.info("Stop flag detected - graceful shutdown")
    save_partial_results()
    return
```

**Stop Propagation Flow**:

```
User clicks "Stop"
    ↓
POST /crawl4ai/stop/{run_id}
    ↓
task_manager.cancel_task(run_id)
    ↓
stop_flags[run_id] = True
    ↓
task.cancel() (asyncio)
    ↓
Multiple check points:
  - HybridCrawler.crawl()
  - LinkExtractor.process_sitemap()
  - generic_crawl() loop
  - SmartMirrorAgent.process_url()
    ↓
Graceful cleanup & save partial results
```

---

### 5.5 AI Classification Cache Strategy

**Purpose**: Optimize AI costs by pre-classifying sitemap URLs and reusing classifications during crawl.

**Two-Level Caching System**:

**1. Persistent Domain Cache** (`output/{domain}/ai_cache/`)
- Stores AI classifications across crawl sessions
- Cache key: `md5(url + content_hash)`
- Survives application restarts
- Reduces costs for repeated crawls of same domain

**2. Session Classification Cache** (In-memory dict)
- Populated during sitemap analysis phase
- Passed to `generic_crawl()` via `config.classification_cache`
- Reused when discovered links match sitemap URLs
- Cleared after crawl completion

**Cache Flow**:

```
Phase 1: Sitemap Analysis (hybrid_crawler.py:178-194)
    ↓
LinkExtractor.process_sitemap_with_ai()
    ↓
AI classifies ALL sitemap URLs upfront
    ↓
Results stored in metadata['ai_classifications']
    ↓
Phase 2: Session Cache Population (hybrid_crawler.py:404-413)
classification_cache = {}
for url, is_worthy, confidence, reasoning in ai_classifications:
    classification_cache[url] = {
        'is_worthy': is_worthy,
        'confidence': confidence,
        'reasoning': reasoning
    }
    ↓
Phase 3: Cache Injection (hybrid_crawler.py:411)
config.classification_cache = classification_cache
    ↓
Passed to generic_crawl(config)
    ↓
Phase 4: Cache Lookup During Crawl (crawler_utils.py:483-486)
if url in config.classification_cache:
    return cached_result  # $0 cost
else:
    ai_result = await ai_classifier.classify()  # ~$0.002 cost
```

**Cost Savings Example**:

```
Sitemap with 500 URLs:
- Upfront AI classification: 500 × $0.0002 = $0.10
- During crawl (without cache): 400 pages × $0.002 = $0.80
- During crawl (with cache):
  - 320 cache hits × $0 = $0
  - 80 new discoveries × $0.002 = $0.16
- Total cost WITH cache: $0.26
- Total cost WITHOUT cache: $0.90
- Savings: $0.64 (71% reduction)
```

**Cache Hit Rates**:
- Sitemap-based crawls: 80-90% cache hit rate
- Progressive discovery: 0-30% cache hit rate (no sitemap to pre-populate)
- Repeat crawls (persistent cache): 90-95% cache hit rate

---

### 7. WebSocket Log Handler (websocket_log_handler.py)

**Purpose**: Captures Python logging output and broadcasts it to WebSocket clients in real-time.

**Public API**:

```python
class WebSocketLogHandler(logging.Handler):
    def emit(self, record: logging.LogRecord):
        """Capture log record and broadcast to WebSocket clients"""

def setup_websocket_logging():
    """Initialize WebSocket logging handler for root logger"""

# Context variable for run_id tracking
current_run_id: ContextVar[str] = ContextVar('run_id', default='global')
```

**Log Flow**:

```
Python logger.info("Crawling page 1")
    ↓
WebSocketLogHandler.emit(record)
    ↓
Format log entry:
{
    "timestamp": "2024-01-15T10:30:00",
    "level": "INFO",
    "message": "Crawling page 1",
    "run_id": "abc123"
}
    ↓
broadcast_to_websockets(run_id, log_entry)
    ↓
WebSocket client receives:
{
    "type": "log",
    "log": {
        "timestamp": "10:30:00",
        "message": "Crawling page 1",
        "type": "info"
    }
}
    ↓
Frontend updates log console
```

**OpenSearch Integration** (Optional):

```python
# Logs can also be sent to OpenSearch for searchable history
def emit(self, record):
    # 1. Broadcast to WebSocket
    broadcast_to_websockets(run_id, log_entry)

    # 2. Index in OpenSearch (async)
    if opensearch_enabled:
        index_log_entry(log_entry)
```

---

### 8. Link Extractor (Utility/link_extractor.py)

**Purpose**: Sitemap processing, URL discovery, and AI-powered URL filtering.

**Public API**:

```python
class LinkExtractor:
    def __init__(self, sitemap_url: str, domain: str,
                 use_ai: bool = True, run_id: str = None):
        """Initialize link extractor"""

    async def process_sitemap_with_ai(
        self, max_urls: int = None
    ) -> Tuple[List[str], Dict[str, Any]]:
        """
        Process sitemap with AI classification

        Returns:
            urls: List of prioritized URLs to crawl
            stats: Statistics about sitemap processing
        """
```

**Sitemap Processing**:

```python
# 1. Fetch sitemap
response = requests.get(sitemap_url)
soup = BeautifulSoup(response.content, "lxml-xml")

# 2. Handle sitemap index vs direct sitemap
if soup.find("sitemapindex"):
    # Sitemap index - process each sub-sitemap
    for sitemap_loc in soup.find_all("sitemap"):
        sub_sitemap_url = sitemap_loc.find("loc").text
        urls.extend(process_sub_sitemap(sub_sitemap_url))
else:
    # Direct sitemap - extract URLs
    for url_loc in soup.find_all("url"):
        url = url_loc.find("loc").text
        urls.append(url)

# 3. AI classification and prioritization
prioritized_urls = await ai_classify_and_prioritize(urls)
```

**AI URL Filtering**:

```python
async def ai_classify_urls(urls: List[str]) -> List[Tuple[str, float, str]]:
    """
    Classify URLs in parallel using AI

    Returns: List of (url, confidence, reasoning)
    """
    results = []

    # Batch process for efficiency
    for batch in chunk_list(urls, batch_size=10):
        tasks = [
            ai_classifier.classify_url_only(url)
            for url in batch
        ]
        batch_results = await asyncio.gather(*tasks)

        for url, result in zip(batch, batch_results):
            confidence = result.confidence
            if not result.is_worthy:
                confidence *= 0.5  # Deprioritize unworthy URLs

            results.append((url, confidence, result.reasoning))

    # Sort by confidence (highest first)
    results.sort(key=lambda x: x[1], reverse=True)

    return results
```

**Robots.txt Intelligence** (Not Restriction):

```python
def analyze_robots_txt(domain: str) -> Dict[str, Any]:
    """
    Gather intelligence from robots.txt
    NOTE: We ignore restrictions for demo purposes
    """
    intelligence = {
        'sitemaps': [],           # Extract sitemap locations
        'suggested_delay': 0.6,   # Respectful crawl delay
        'hidden_sections': [],    # Disallowed paths (for reference)
        'complexity_estimate': 'unknown'
    }

    # Extract sitemap URLs
    for line in robots_content.split('\n'):
        if line.lower().startswith('sitemap:'):
            sitemap_url = line.split(':', 1)[1].strip()
            intelligence['sitemaps'].append(sitemap_url)

    return intelligence
```

---

### 9. OpenSearch Integration (Utility/opensearch_integration.py)

**Purpose**: Index crawled content for semantic search and log management.

**Public API**:

```python
class OpenSearchIntegration:
    def __init__(self, host: str = "opensearch-demo", port: int = 9200):
        """Initialize OpenSearch client"""

    def create_content_index(self, index_name: str) -> bool:
        """Create index optimized for crawled content"""

    def index_crawled_content(self, crawl_output_dir: str,
                             index_name: str) -> Dict[str, Any]:
        """Index all content from crawl output directory"""

    def search(self, query: str, index_name: str,
              size: int = 10) -> Dict[str, Any]:
        """Search indexed content"""
```

**Index Mapping for Content**:

```json
{
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "analysis": {
      "analyzer": {
        "content_analyzer": {
          "type": "standard",
          "stopwords": "_english_"
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "url": {"type": "keyword"},
      "title": {
        "type": "text",
        "analyzer": "content_analyzer",
        "fields": {"keyword": {"type": "keyword"}}
      },
      "content_md": {
        "type": "text",
        "analyzer": "content_analyzer"
      },
      "meta_desc": {"type": "text"},
      "h1": {"type": "text"},
      "h2": {"type": "text"},
      "h3": {"type": "text"},
      "tags": {"type": "keyword"},
      "fetched_at": {"type": "date"},
      "indexed_at": {"type": "date"}
    }
  }
}
```

**Bulk Indexing**:

```python
def index_crawled_content(crawl_output_dir: str, index_name: str):
    documents = []

    # Walk output directory
    for root, dirs, files in os.walk(crawl_output_dir):
        if "index.md" in files and "meta.json" in files:
            # Read content and metadata
            with open(os.path.join(root, "index.md")) as f:
                content = f.read()
            with open(os.path.join(root, "meta.json")) as f:
                metadata = json.load(f)

            # Create document
            doc = {
                "url": metadata["url"],
                "title": metadata.get("title", ""),
                "content_md": content,
                "meta_desc": metadata.get("description", ""),
                "fetched_at": metadata.get("fetched_at"),
                "indexed_at": datetime.now().isoformat()
            }
            documents.append(doc)

            # Batch index every 100 documents
            if len(documents) >= 100:
                bulk_index(documents, index_name)
                documents = []

    # Index remaining documents
    if documents:
        bulk_index(documents, index_name)
```

**Search with Boosting**:

```python
def search(query: str, index_name: str, size: int = 10):
    search_body = {
        "query": {
            "multi_match": {
                "query": query,
                "fields": [
                    "title^3",          # Title boosted 3x
                    "h1^2",             # H1 boosted 2x
                    "meta_desc^1.5",    # Meta description boosted 1.5x
                    "content_md^1"      # Content base weight
                ],
                "type": "best_fields",
                "fuzziness": "AUTO"
            }
        },
        "highlight": {
            "fields": {
                "content_md": {"fragment_size": 150},
                "title": {}
            }
        },
        "size": size
    }

    return client.search(index=index_name, body=search_body)
```

---

### 10. Proxy Server (Proxy/proxy_server.py)

**Purpose**: Live proxy serving of crawled content with search injection and dynamic asset handling.

**Key Routes**:

```python
# Proxy content serving
GET /proxy{path:path}
# Example: GET /proxy/about-us

# Search endpoint
POST /search
Request: {"query": "banking products"}

# Configure proxy target
POST /configure-proxy
Request: {"target_url": "https://example.com"}

# WebSocket search updates
WS /ws/search
```

**Request Interception**:

```python
@app.get("/proxy{path:path}")
async def proxy_request(path: str, request: Request):
    # 1. Check if cached
    cached_content = get_from_cache(domain, path)
    if cached_content:
        # Inject search bar
        html = inject_search_bar(cached_content)
        return HTMLResponse(html)

    # 2. Fallback to live site
    target_url = f"{proxy_config['target_url']}{path}"
    response = await forward_request(target_url)
    return response
```

**Search Bar Injection**:

```python
def inject_search_bar(html_content: str) -> str:
    """Inject search bar into HTML before </body>"""

    search_html = """
    <div id="injected-search-bar" style="position: fixed; top: 20px; right: 20px;">
        <input type="text" id="search-input" placeholder="Search demo content...">
        <div id="search-results"></div>
    </div>
    <script>
        document.getElementById('search-input').addEventListener('input', async (e) => {
            const query = e.target.value;
            const response = await fetch('/search', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({query})
            });
            const results = await response.json();
            displayResults(results);
        });
    </script>
    """

    if '</body>' in html_content:
        html_content = html_content.replace('</body>', f'{search_html}</body>')

    return html_content
```

**Cache Lookup**:

```python
def get_from_cache(domain: str, path: str) -> Optional[str]:
    """Get cached content for domain and path"""

    # Generate cache key from path
    cache_key = hashlib.md5(path.encode()).hexdigest()

    # Check output directory
    cache_file = f"output/{domain}/{cache_key}/raw.html"
    if os.path.exists(cache_file):
        with open(cache_file) as f:
            return f.read()

    return None
```

---

## Data Flow

### Complete Crawl Request Flow

```
┌─────────────┐
│  Frontend   │
│  User Input │
└──────┬──────┘
       │ POST /crawl4ai/start {"target_url": "..."}
       ▼
┌─────────────────┐
│   main.py       │
│ start_crawl4ai()│
└─────────┬───────┘
          │ Create background task
          ▼
┌──────────────────────┐
│ run_crawl4ai_agent_  │
│       real()         │
│  run_id: abc123      │
└──────────┬───────────┘
           │ Initialize agent
           ▼
┌────────────────────────┐
│  SmartMirrorAgent      │
│  .process_url()        │
└──────────┬─────────────┘
           │ 1. Detect site type
           │ 2. Select strategy
           ▼
┌────────────────────────┐
│   HybridCrawler        │
│  .crawl()              │
└──────────┬─────────────┘
           │ 1. Sitemap analysis
           │ 2. AI URL filtering
           ▼
┌────────────────────────┐
│   LinkExtractor        │
│  .process_sitemap()    │
└──────────┬─────────────┘
           │ Returns prioritized URLs
           ▼
┌────────────────────────┐
│   HybridCrawler        │
│   Crawl loop           │
└──────────┬─────────────┘
           │ For each URL
           ▼
┌────────────────────────┐
│   crawler_utils        │
│   generic_crawl()      │
└──────────┬─────────────┘
           │ Call Crawl4AI
           ▼
┌────────────────────────┐
│   Crawl4AI             │
│  AsyncWebCrawler.arun()│
└──────────┬─────────────┘
           │ Returns CrawlResult
           ▼
┌────────────────────────┐
│   Save to disk         │
│  output/{domain}/      │
└────────────────────────┘
```

### Progress Update Flow

```
AsyncWebCrawler (Crawling...)
    ↓
crawler_utils.generic_crawl()
    ↓ Call progress_callback
HybridCrawler.update_progress()
    ↓ Call agent's progress callback
main.py.update_progress()
    ↓ Update session progress
main.py.broadcast_to_websockets()
    ↓ Send to all WebSocket clients
WebSocket Client (Frontend)
    ↓ Update UI
Progress Bar + Log Console Updated
```

### Stop Signal Flow

```
User clicks "Stop" button
    ↓
Frontend: POST /crawl4ai/stop/{run_id}
    ↓
main.py: stop_crawl4ai_agent()
    ↓
task_manager.cancel_task(run_id)
    ├─ Set stop_flags[run_id] = True
    └─ task.cancel() (asyncio)
    ↓
Check points detect stop:
├─ SmartMirrorAgent: if stop_check(): return
├─ HybridCrawler: if should_stop(): break
├─ LinkExtractor: if should_stop(): break
└─ generic_crawl: if should_stop(): return
    ↓
Graceful cleanup:
├─ Save partial results
├─ Update status to "stopped"
└─ task_manager.cleanup_task()
```

---

## API Reference

### REST Endpoints

#### POST /crawl4ai/start

Start a new crawl job.

**Request**:
```json
{
    "target_url": "https://www.nab.com.au",
    "max_pages": 100  // Optional - defaults to intelligent stopping
}
```

**Response** (202 Accepted):
```json
{
    "run_id": "550e8400-e29b-41d4-a716-446655440000",
    "message": "Crawl4AI agent started",
    "status": "pending"
}
```

---

#### GET /crawl4ai/status/{run_id}

Get current crawl status and progress.

**Response**:
```json
{
    "session": {
        "run_id": "550e8400-e29b-41d4-a716-446655440000",
        "target_url": "https://www.nab.com.au",
        "status": "running",
        "started_at": 1705315800.0,
        "current_question": null
    },
    "logs": [
        {
            "timestamp": "10:30:00",
            "message": "Crawl4AI SmartMirrorAgent initialized",
            "type": "info"
        },
        {
            "timestamp": "10:30:05",
            "message": "Starting site reconnaissance...",
            "type": "info"
        }
    ],
    "progress": {
        "percentage": 45.0,
        "pages_crawled": 45,
        "pages_remaining": 55,
        "total_pages": 100,
        "estimated_time_remaining": 300,  // seconds
        "crawl_speed": 5.2,  // pages per minute
        "ai_classifications": 12,
        "cache_hits": 33,
        "loaded_caches": 33
    }
}
```

**Status Values**:
- `"pending"`: Crawl queued but not started
- `"running"`: Actively crawling
- `"waiting_for_input"`: Waiting for user input (rare)
- `"completed"`: Successfully completed
- `"stopped"`: User-initiated stop
- `"error"`: Failed with error

---

#### POST /crawl4ai/stop/{run_id}

Force stop a running crawl immediately.

**Response**:
```json
{
    "message": "Crawl force stopped",
    "run_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "stopped",
    "summary": {
        "pages_crawled": 45,
        "total_pages": 100,
        "percentage": 45.0,
        "pages_remaining": 55,
        "elapsed_time": "5m 30s",
        "elapsed_seconds": 330,
        "cache_hits": 33,
        "ai_classifications": 12,
        "current_url": "https://www.nab.com.au/business/loans",
        "target_url": "https://www.nab.com.au"
    }
}
```

---

#### WebSocket: /crawl4ai/ws/{run_id}

Real-time log streaming for a crawl job.

**Connection**: `ws://localhost:8000/crawl4ai/ws/{run_id}`

**Message Types**:

**Log Message**:
```json
{
    "type": "log",
    "log": {
        "timestamp": "10:30:05",
        "message": "Crawling page 45 of 100",
        "type": "info"  // "info", "success", "warning", "error"
    }
}
```

**Status Update**:
```json
{
    "type": "status",
    "status": "running",
    "question": null
}
```

**Progress Update**:
```json
{
    "type": "progress",
    "progress": {
        "percentage": 45.0,
        "pages_crawled": 45,
        "total_pages": 100,
        "crawl_speed": 5.2
    }
}
```

---

### Proxy Server Endpoints

#### GET /proxy{path}

Proxy requests to cached or live content with injected search.

**Example**: `GET /proxy/about-us`

**Response**: HTML content with injected search bar

---

#### POST /search

Search indexed content.

**Request**:
```json
{
    "query": "banking products",
    "filters": {
        "domain": "nab.com.au"
    }
}
```

**Response**:
```json
{
    "total_hits": 15,
    "hits": [
        {
            "score": 2.5,
            "url": "/products/banking",
            "title": "Banking Products - NAB",
            "meta_desc": "Explore our range of banking products...",
            "highlight": {
                "content_md": [
                    "Our <em>banking</em> <em>products</em> include..."
                ]
            }
        }
    ]
}
```

---

## Developer Guide

### Adding a New Crawl Strategy

**1. Define Strategy Enum**:

```python
# In smart_mirror_agent.py
class CrawlStrategy(Enum):
    CUSTOM_STRATEGY = "custom_strategy"
```

**2. Add Configuration Mapping**:

```python
def strategy_to_config(strategy: CrawlStrategy) -> CrawlConfig:
    if strategy == CrawlStrategy.CUSTOM_STRATEGY:
        return CrawlConfig(
            timeout=60,
            request_gap=1.5,
            wait_for='networkidle',
            screenshot=True,
            javascript=True
        )
```

**3. Add Detection Logic**:

```python
def detect_site_type(url: str) -> CrawlStrategy:
    domain = urlparse(url).netloc

    if "custom-pattern" in domain:
        return CrawlStrategy.CUSTOM_STRATEGY

    # Existing logic...
```

---

### Extending AI Classification

**1. Add New Site Type**:

```python
# In ai_content_classifier.py
class BusinessSiteType(Enum):
    CUSTOM_TYPE = "custom_type"
```

**2. Add Detection Patterns**:

```python
ENHANCED_BUSINESS_PATTERNS = {
    BusinessSiteType.CUSTOM_TYPE: {
        "high_confidence_phrases": [
            "custom phrase 1",
            "custom phrase 2"
        ],
        "supporting_keywords": [
            "keyword1", "keyword2"
        ]
    }
}
```

**3. Add Custom Prompt**:

```python
def _get_site_specific_prompt(site_type: BusinessSiteType, url: str) -> str:
    if site_type == BusinessSiteType.CUSTOM_TYPE:
        return """
        CUSTOM SITE EVALUATION:

        MARK AS WORTHY:
        - Criteria 1
        - Criteria 2

        MARK AS NOT WORTHY:
        - Exclusion 1
        - Exclusion 2
        """
```

---

### Custom Progress Callbacks

**1. Define Callback**:

```python
async def custom_progress_callback(
    pages_crawled: int,
    total_known: int,
    discovered_urls: int = 0,
    crawl_speed: float = 0,
    ai_classifications: int = 0,
    cache_hits: int = 0,
    current_url: str = None
):
    # Custom logic
    logger.info(f"Progress: {pages_crawled}/{total_known} at {crawl_speed:.1f} pages/min")

    # Send to external monitoring system
    await send_to_monitoring_system({
        "pages_crawled": pages_crawled,
        "total_known": total_known,
        "current_url": current_url,
        "crawl_speed": crawl_speed
    })
```

**2. Inject into Crawler**:

```python
agent = SmartMirrorAgent(...)
agent.crawler.progress_callback = custom_progress_callback
```

---

### Adding Custom Filters

**In HybridCrawler**:

```python
def should_crawl_url(self, url: str) -> bool:
    # Custom filtering logic
    if "exclude-pattern" in url:
        return False

    if custom_business_logic(url):
        return False

    # Call existing filters
    return super().should_crawl_url(url)
```

---

## Configuration

### Environment Variables

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-...              # Required for AI classification
PREFERRED_MODEL=gpt-4o-mini        # AI model (default: gpt-4o-mini)

# OpenSearch Configuration
OPENSEARCH_HOST=opensearch-demo    # OpenSearch hostname
OPENSEARCH_PORT=9200               # OpenSearch port

# Server Configuration
HOST=0.0.0.0                       # FastAPI host
PORT=8000                          # FastAPI port

# Logging
LOG_LEVEL=INFO                     # DEBUG, INFO, WARNING, ERROR
```

---

### CrawlConfig Options

```python
@dataclass
class CrawlConfig:
    timeout: int = 30                    # Request timeout (seconds)
    request_gap: float = 0.6             # Delay between requests (seconds)
    headless: bool = True                # Run browser headless
    wait_for: str = 'domcontentloaded'   # Wait condition
    screenshot: bool = False             # Take screenshots
    javascript: bool = False             # Enable JavaScript execution
    max_concurrent: int = 1              # Max concurrent requests
    run_id: Optional[str] = None         # For stop signal checking
```

**Wait Conditions**:
- `'domcontentloaded'`: Wait for DOM ready (fastest)
- `'networkidle'`: Wait for network idle (most reliable for JS)
- `'load'`: Wait for full page load

---

### Crawl Configuration (Fixed for All Sites)

**All sites use the same FULL BROWSER configuration**:

| Setting | Value | Purpose |
|---------|-------|---------|
| **javascript** | True | Enable JavaScript rendering |
| **wait_for** | networkidle | Wait for all network activity to complete |
| **timeout** | 30s | Maximum time per page |
| **headless** | True | Run Chrome in headless mode |
| **request_gap** | 0.8s | Respectful delay between requests |

**Note**: The CrawlStrategy enum (FULL_BROWSER, JAVASCRIPT_RENDER, BASIC_HTTP) in smart_mirror_agent.py is **legacy code** and not used. The real strategy is **DiscoveryStrategy** (SITEMAP_FIRST vs PROGRESSIVE) in HybridCrawler.

---

### AI Classification Settings

```python
# Model selection
MODEL = "gpt-4o-mini"  # Cost-effective, fast
# MODEL = "gpt-4"      # Higher quality, higher cost

# Classification thresholds
WORTHY_THRESHOLD = 0.5         # Minimum confidence for worthy classification
CACHE_EXPIRY_DAYS = 30         # Cache validity period (days)
BATCH_SIZE = 10                # URLs to classify in parallel

# Cost limits (optional)
MAX_COST_PER_DOMAIN = 10.0     # Max spend per domain (USD)
```

---

## Integration Guide

### Crawl4AI Integration

Uses **Crawl4AI's AsyncWebCrawler** as the core engine:

```python
from crawl4ai import AsyncWebCrawler

async with AsyncWebCrawler(
    headless=True,
    verbose=True,
    browser_type="chromium"
) as crawler:

    result = await crawler.arun(
        url=url,
        timeout=30,
        wait_for='networkidle',
        word_count_threshold=10,
        bypass_cache=True
    )

    # Extract content
    markdown = result.markdown
    html = result.html
    metadata = result.metadata
```

**Key Crawl4AI Features Used**:
- Async crawling for performance
- JavaScript rendering support
- Markdown extraction
- Screenshot capture
- Link extraction
- Metadata extraction

---

### OpenAI Integration

AI classification uses **OpenAI's Chat Completions API**:

```python
import openai

client = openai.AsyncOpenAI(api_key=api_key)

response = await client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": "You are an expert content evaluator..."},
        {"role": "user", "content": prompt}
    ],
    max_tokens=150,
    temperature=0.1  # Low temperature for consistency
)

# Parse response
is_worthy = "WORTHY: true" in response.choices[0].message.content
```

**Cost Optimization**:
- URL-only classification for sitemap analysis (~$0.0002/URL)
- Domain-level caching
- Fallback to heuristics on API failures
- Batch processing with asyncio.gather()

---

### OpenSearch Integration

Search functionality uses **OpenSearch**:

```python
from opensearchpy import OpenSearch

client = OpenSearch(
    hosts=[{'host': 'opensearch-demo', 'port': 9200}],
    http_compress=True,
    use_ssl=False
)

# Index content
client.index(
    index="demo-nab",
    body={
        "url": url,
        "title": title,
        "content_md": content
    }
)

# Search
results = client.search(
    index="demo-nab",
    body={
        "query": {
            "multi_match": {
                "query": "banking products",
                "fields": ["title^3", "content_md"]
            }
        }
    }
)
```

**Index Strategy**:
- One index per domain: `demo-{domain}`
- Monthly log indices: `ai-agent-logs-2024-01`
- Optimized analyzers for content types

---

### Frontend WebSocket Integration

Real-time updates via **WebSocket**:

```javascript
// Connect to WebSocket
const runId = "550e8400-e29b-41d4-a716-446655440000";
const ws = new WebSocket(`ws://localhost:8000/crawl4ai/ws/${runId}`);

// Receive events
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.type === "log") {
        addLogEntry(data.log);
    } else if (data.type === "progress") {
        updateProgressBar(data.progress);
    } else if (data.type === "status") {
        updateStatus(data.status);
    }
};

// Handle disconnection
ws.onclose = () => {
    console.log("WebSocket disconnected");
};
```

---

## Code Examples

### Basic Crawl Usage

```python
from smart_mirror_agent import SmartMirrorAgent

# Initialize agent
agent = SmartMirrorAgent(memory_path="agent_memory.json")

# Start crawl
success, metrics, output_path = await agent.process_url(
    url="https://www.nab.com.au",
    run_id="test-run-123",
    max_pages=100
)

if success:
    print(f"Crawl completed!")
    print(f"Quality score: {metrics.overall_score * 100:.1f}%")
    print(f"Pages crawled: {metrics.pages_crawled}")
    print(f"Output: {output_path}")
else:
    print("Crawl failed")
```

---

### Custom AI Classification

```python
from ai_content_classifier import AIContentClassifier
import os

# Initialize
classifier = AIContentClassifier(
    api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4o-mini"
)

# Classify URL
result = await classifier.classify_url_only(
    url="https://www.nab.com.au/business/loans"
)

print(f"Worthy: {result.is_worthy}")
print(f"Confidence: {result.confidence:.2f}")
print(f"Reasoning: {result.reasoning}")
print(f"Cost: ${result.estimated_cost:.6f}")
print(f"Method: {result.method_used}")
```

---

### OpenSearch Indexing

```python
from opensearch_integration import OpenSearchIntegration

# Initialize
integration = OpenSearchIntegration(
    host="opensearch-demo",
    port=9200
)

# Create index
integration.create_content_index("demo-nab")

# Index crawled content
stats = integration.index_crawled_content(
    crawl_output_dir="output/nab.com.au",
    index_name="demo-nab"
)

print(f"Indexed {stats['documents_indexed']} documents")

# Search
results = integration.search(
    query="business loans",
    index_name="demo-nab",
    size=10
)

for hit in results["hits"]:
    print(f"{hit['title']}: {hit['url']}")
```

---

### Proxy Server Usage

```python
from proxy_server import app, initialize_opensearch

# Configure proxy
initialize_opensearch(domain="nab.com.au")

# Run proxy server
# Requests to http://localhost:8000/proxy/about-us
# will serve cached content or fallback to live site
```

---

## Performance & Optimization

### Async Patterns

**Concurrent URL Classification**:

```python
# Process URLs in batches
async def classify_batch(urls: List[str]):
    tasks = [classifier.classify_url_only(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results

# Use in sitemap processing
for batch in chunk_list(urls, batch_size=10):
    results = await classify_batch(batch)
```

**Parallel Crawling (with concurrency limit)**:

```python
semaphore = asyncio.Semaphore(max_concurrent=3)

async def crawl_with_limit(url: str):
    async with semaphore:
        return await generic_crawl(url, ...)

# Crawl multiple URLs concurrently
tasks = [crawl_with_limit(url) for url in urls]
results = await asyncio.gather(*tasks)
```

---

### Caching Strategies

**AI Classification Cache**:
- Domain-specific cache directories
- URL-based cache keys with content hashing
- Persistent JSON storage
- 30-day cache validity
- Reduces repeat API calls by ~80%

**Crawl Output Cache**:
- Hash-based file naming
- Incremental updates via checksums
- Deduplication before save
- Skip re-crawling unchanged pages

---

### Resource Cleanup

```python
# Crawler cleanup
async with AsyncWebCrawler() as crawler:
    # Automatically closes browser on exit
    result = await crawler.arun(url)

# Task cleanup
try:
    results = await agent.process_url(url)
finally:
    task_manager.cleanup_task(run_id)
```

---

## Error Handling

### Error Propagation

```python
# Layer 1: Crawl4AI errors
try:
    result = await crawler.arun(url)
except Exception as crawl_error:
    logger.error(f"Crawl4AI error: {crawl_error}")
    raise CrawlError(f"Failed to crawl {url}")

# Layer 2: Crawler utils errors
try:
    page_data = await generic_crawl(url, ...)
except CrawlError as e:
    logger.warning(f"Page crawl failed: {e}")
    return {"status": "failed", "error": str(e)}

# Layer 3: HybridCrawler errors
try:
    results = await crawler.crawl(...)
except Exception as e:
    logger.error(f"Crawler error: {e}")
    return {"status": "error", "partial_results": partial_data}

# Layer 4: API errors
try:
    await run_crawl4ai_agent_real(...)
except Exception as e:
    logger.exception("Task failed")
    await update_agent_status(run_id, "error")
```

---

### Edge Cases

**Empty Sitemaps**:
```python
if not sitemap_urls:
    logger.warning("No sitemap found - using homepage only")
    crawl_plan = [homepage_url]
```

**AI API Failures**:
```python
try:
    result = await ai_classifier.classify_content(...)
except Exception as ai_error:
    logger.warning("AI failed - using heuristic fallback")
    result = heuristic_classifier.classify(...)
```

**Network Timeouts**:
```python
try:
    result = await crawler.arun(url, timeout=30)
except asyncio.TimeoutError:
    logger.warning(f"Timeout for {url} - skipping")
    continue
```

**Duplicate Content**:
```python
content_hash = hashlib.md5(content.encode()).hexdigest()
if content_hash in seen_hashes:
    logger.debug(f"Duplicate detected: {url}")
    continue
seen_hashes.add(content_hash)
```

---

## Deployment

### Docker Deployment

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port
EXPOSE 8000

# Run server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**docker-compose.yml**:
```yaml
version: '3.8'

services:
  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPENSEARCH_HOST=opensearch-demo
      - OPENSEARCH_PORT=9200
    volumes:
      - ./output:/app/output
    depends_on:
      - opensearch-demo

  opensearch-demo:
    image: opensearchproject/opensearch:2.11.0
    ports:
      - "9200:9200"
    environment:
      - discovery.type=single-node
      - plugins.security.disabled=true
      - OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m
```

**Start Services**:
```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

---

### Production Configuration

**.env File**:
```bash
# OpenAI
OPENAI_API_KEY=sk-prod-...
PREFERRED_MODEL=gpt-4o-mini

# OpenSearch
OPENSEARCH_HOST=opensearch.production.com
OPENSEARCH_PORT=9200
OPENSEARCH_USE_SSL=true
OPENSEARCH_USERNAME=admin
OPENSEARCH_PASSWORD=...

# Server
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=INFO

# Performance
MAX_CONCURRENT_CRAWLS=3
REQUEST_TIMEOUT=60
```

---

## Troubleshooting

### Common Issues

**Issue: "OpenAI API key not found"**

```bash
# Solution 1: Set environment variable
export OPENAI_API_KEY=sk-...

# Solution 2: Add to .env file
echo "OPENAI_API_KEY=sk-..." >> .env

# Solution 3: Check if loaded
python -c "import os; print(os.getenv('OPENAI_API_KEY'))"
```

---

**Issue: "OpenSearch connection refused"**

```bash
# Check if OpenSearch is running
docker ps | grep opensearch

# Test connection
curl http://localhost:9200

# Check logs
docker logs opensearch-demo

# Restart OpenSearch
docker-compose restart opensearch-demo
```

---

**Issue: "Crawl stuck on loading screen"**

```python
# Solution: Increase timeout for JS-heavy sites
config = CrawlConfig(
    timeout=60,  # Increase from default 30s
    wait_for='networkidle',  # Wait for network idle
    request_gap=2.0  # Longer delay between requests
)
```

---

**Issue: "AI classification too expensive"**

```python
# Solution 1: Use URL-only classification (cheaper)
result = await classifier.classify_url_only(url)  # ~$0.0002 vs ~$0.002

# Solution 2: Increase cache expiry
CACHE_EXPIRY_DAYS = 90  # Default is 30

# Solution 3: Use heuristic fallback more aggressively
USE_AI_THRESHOLD = 0.8  # Only use AI for uncertain cases
```

---

**Issue: "WebSocket disconnecting frequently"**

```javascript
// Solution: Add reconnection logic
function connectWebSocket(runId) {
    const ws = new WebSocket(`ws://localhost:8000/crawl4ai/ws/${runId}`);

    ws.onclose = () => {
        console.log("WebSocket closed - reconnecting in 1s...");
        setTimeout(() => connectWebSocket(runId), 1000);
    };

    return ws;
}
```

---

**Issue: "Crawl not stopping when requested"**

```python
# Check stop flag propagation
# Ensure run_id is passed to all layers:

# 1. SmartMirrorAgent
await agent.process_url(url, run_id=run_id)

# 2. HybridCrawler
crawler = HybridCrawler(..., run_id=run_id)

# 3. CrawlConfig
config = CrawlConfig(..., run_id=run_id)

# 4. Verify task manager
task_manager.should_stop(run_id)  # Should return True
```

---

**Issue: "Out of memory during large crawls"**

```python
# Solution 1: Limit concurrent crawls
MAX_CONCURRENT = 1  # Process one page at a time

# Solution 2: Clean up resources
async with AsyncWebCrawler() as crawler:
    # Auto-cleanup on exit
    pass

# Solution 3: Reduce max_pages
max_pages = 50  # Start smaller

# Solution 4: Monitor memory
import psutil
process = psutil.Process()
logger.info(f"Memory: {process.memory_info().rss / 1024 / 1024} MB")
```

---

## Summary

This documentation covers the complete Crawl4AI backend system, including:

- **Architecture**: FastAPI → SmartMirrorAgent → HybridCrawler → Crawl4AI
- **AI Integration**: GPT-4o-mini for intelligent content classification
- **Real-time Updates**: WebSocket-based progress streaming
- **Task Management**: Multi-layer stop flag propagation
- **Search Integration**: OpenSearch for semantic search
- **Proxy Serving**: Live content serving with search injection

The system achieves **90% demo quality** through adaptive strategies, AI-powered filtering, and intelligent crawling patterns.

For questions or issues, refer to the troubleshooting section or check the module-specific documentation above.
