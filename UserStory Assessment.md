UserStory Assessment

US-31: SmartMirrorAgent core System ML based
As a demo factory operator I want an intelligent AI agent that can automatically crawl and mirror websites So that I can create high-quality demo versions with 90% visual fidelity

- Agent processes URLs through complete flow: Memory Check → Reconnaissance → Strategy - Selection → Crawl → Quality Assessment → Mirror Build → Learning Storage

- Maintains session statistics and performance tracking

- Supports both single URL and batch processing modes

- Provides comprehensive result reporting with processing times and quality metrics

- Stores and retrieves patterns from memory database for learning optimization

US-32: Site Reconnaissance System ML based
As a demo factory operator I want the agent to quickly analyze target websites So that it can select optimal crawling strategies based on site characteristics
- Completes reconnaissance analysis in under 10 seconds
- Detects site types: Banking, E-commerce, SPA (React/Angular/Vue), WordPress, News, Static HTML
- Identifies JavaScript frameworks and complexity levels
- Measures page load times and asset counts
- Recommends appropriate crawling strategy based on analysis
- Provides confidence scores for recommendations

US-33: Adaptive Crawling Strategies
As a demo factory operator I want multiple crawling strategies available So that the agent can handle different website technologies effectively
- Implements Basic HTTP strategy for static HTML sites

- Implements JavaScript Render strategy using Crawl4AI for dynamic content

- Implements Full Browser strategy with complete browser automation for complex SPAs

- Implements Hybrid strategy that adapts based on real-time quality feedback

- Switches strategies dynamically if quality drops below thresholds

- Tracks success rates and performance metrics per strategy

US-34: Quality Monitoring System
As a demo factory operator I want comprehensive quality assessment of crawled content So that I can ensure demo sites meet 90% visual fidelity standards
- ✅ Content Discovery assessment based on successful page crawling, content extraction quality, and variety
- ✅ Asset Coverage: Always 100% (proxy serves original assets on-demand - obsolete for proxy architecture)
- ✅ Navigation Integrity: Always 100% (proxy preserves original site navigation structure)
- ✅ Visual Fidelity: Always 100% (proxy serves original CSS, JS, and assets in real-time)
- ✅ AI Classification scoring with acceptance ratios and confidence levels
- ✅ Realistic Site Coverage calculation based on estimated total site pages vs crawled pages
- ✅ Processing Efficiency assessment with success rates and meaningful content quality
- ✅ Overall weighted quality score from 0.0 to 1.0 adapted for proxy system
- ✅ Proxy-optimized recommendations: "Excellent proxy crawl - demo ready" (0.9-1.0), "Good crawl quality" (0.8-0.89), etc.
- ✅ Comprehensive testing suite with single-page, multi-page, and poor-quality crawl scenarios
- 🔄 Integration testing with live proxy system

US-35: Learning System with Pattern Storage
As a demo factory operator I want the agent to learn from successful crawls So that it  improves performance over time and reuses successful strategies

- Stores successful patterns (quality score ≥ 0.7) in SQLite database

- Records domain, site type, strategy used, quality metrics, and crawl configuration

- Finds similar patterns based on domain, frameworks, and site characteristics

- Recommends strategies with confidence scores based on historical success

- Applies time-based weighting to patterns (newer patterns weighted higher)

- Tracks improvement in success rates over time

US-36: FastAPI Backend Integration

As a frontend developer I want REST API endpoints for the AI agent system So that I can integrate crawling capabilities into the demo factory interface

- Provides POST /crawl endpoint to initiate crawling jobs

- Provides GET /status/{run_id} endpoint to check crawl progress

- Provides GET /results/{run_id} endpoint to retrieve crawl results

- Supports background task processing for non-blocking operations

- Includes CORS configuration for frontend integration

- Returns appropriate HTTP status codes and error messages

US-37: Multi-Strategy Site Type Handling

As a demo factory operator I want specialized handling for different site types So that banking, e-commerce, and SPA sites are crawled with appropriate methods

- Banking sites automatically use JavaScript Render or Full Browser strategies

- E-commerce sites handle dynamic product catalogs and shopping cart functionality

- React/Angular/Vue SPAs use Full Browser strategy for complete rendering

- WordPress sites optimize for CMS structure and content extraction

- News sites prioritize content extraction and article structure

- Static HTML sites use fast Basic HTTP strategy


**US-38: Real-time Quality Adaptation**
As a demo factory operator I want the agent to adapt crawling parameters in real-time So that quality issues are detected and corrected during the crawling process
- ✅ Quality monitoring system refactored for proxy architecture with realistic metrics
- ✅ AI classification performance tracking integrated for intelligent adaptation decisions
- ✅ Processing efficiency metrics implemented for real-time feedback
- ✅ Proxy-optimized quality assessment framework ready for real-time use
- 🔄 Adjusts crawling parameters (delays, timeouts, rendering settings) based on quality feedback
- 🔄 Switches to fallback strategies if quality drops below 0.6
- 🔄 Provides quality checkpoints throughout crawling process
- 🔄 Stops crawling early if quality cannot be improved
- 🔄 Logs adaptation decisions for learning system

**US:39 - Batch Processing and Statistics**
As a demo factory operator I want to process multiple URLs simultaneously So that I can efficiently create demos for multiple client websites
- Provides aggregate statistics across all processed URLs
- Calculates batch success rate and average quality scores

**US-40: Performance Targets and Monitoring**
As a demo factory operator I want the agent to meet specific performance targets So that the system is efficient and meets quality standards
- ✅ Comprehensive quality assessment system adapted for proxy architecture
- ✅ Realistic site coverage calculations (eliminates nonsensical "70% for 1 page" metrics)
- ✅ AI classification performance metrics with acceptance ratios and confidence scores
- ✅ Processing efficiency tracking with success rates and content quality assessment
- ✅ Proxy-appropriate performance indicators (Visual Fidelity always 100%, Asset Coverage always 100%)
- ✅ Quality recommendation system with proxy-optimized recommendations
- ✅ Performance testing framework with comprehensive test scenarios
- 🔄 Reconnaissance completes in under 10 seconds per URL
- 🔄 Strategy selection completes in under 5 seconds
- 🔄 Full crawling completes within 5-30 minutes depending on site size
- 🔄 Mirror building completes in under 5 minutes (replaced by proxy serving < 200ms)
- 🔄 Achieves 90% success rate across all site types
- 🔄 Achieves 90% average quality score across processed sites
- ❌ Real-time performance monitoring and target achievement tracking (not implemented)
- ❌ Performance dashboard/reporting system (not implemented)






### EPIC-01: Core Crawling Infrastructure (COMPLETED)
**Status:**  DONE  
**Description:** Foundational crawling and mirror generation capabilities for creating static demo websites

**Completed User Stories:**
- Basic web crawling with Crawl4AI AsyncWebCrawler
- Static mirror generation with offline asset localization
- Domain-agnostic mirror builder (generic for any website)
- Two-round asset fetching (HTML assets first, then CSS dependencies)
- URL rewriting and localization for offline browsing
- Basic quality scoring architecture framework

**Technical Achievements:**
- Crawl4AI integration for JavaScript rendering
- Asset downloading and localization pipeline
- CSS dependency resolution and @import handling
- Folder structure matching URL hierarchy
- Working demo: NAB bank crawler (80 pages, 0.6s delays)

**Current Limitations:**
- Windows encoding issues with Unicode characters
- Fixed crawling strategies (no dynamic adaptation)
- No learning or pattern recognition
- Manual configuration required per site

### EPIC-02: Production Deployment & Reliability (FUTURE)
**Status:**  CRITICAL  
**Description:** Address critical Windows encoding issues and production deployment requirements

**Future User Stories:**

**US-044: Docker Deployment Solution** (COMPLETED)
As a demo factory operator I want the system to run in Docker containers So that Windows encoding issues are eliminated and deployment is consistent across platforms
- Eliminates Windows path length limits causing content loss
- Fixes Windows charmap codec errors with Unicode characters  
- Provides UTF-8 encoding by default for all operations
- Enables consistent cross-platform deployment
- Supports easy demo deployment: `docker run smart-mirror-agent nab.com.au`

**US-045: Content Deduplication System**
As a demo factory operator I want the system to detect and skip duplicate content So that demos contain only unique, valuable content
- Implements text similarity detection using cosine similarity
- Detects URL pattern duplicates (e.g., /product/123 vs /product/456)
- Uses content hash comparison for exact duplicates
- Identifies template-based pages with different data
- Improves demo quality by focusing on diverse content

**US-046: Dynamic Stopping Conditions**
As a demo factory operator I want intelligent crawling that stops based on quality metrics So that the system achieves optimal coverage without arbitrary page limits
- Replaces fixed page limits with quality-based stopping
- Implements section coverage threshold (90% of main sections)
- Stops when quality plateaus for 30+ consecutive pages
- Early stopping when target quality score achieved
- Monitors content diversity and stops when becoming repetitive

### EPIC-03: Search & AI Integration (FUTURE)
**Status:**  ENHANCEMENT  
**Description:** Add OpenSearch indexing and chatbot capabilities to enhance demo value

**US-047: OpenSearch Integration**
As a demo user I want semantic search capabilities across all crawled content So that I can find information more effectively than the original site navigation
- Indexes all crawled content in OpenSearch for semantic search
- Provides custom search bar that surpasses original site navigation
- Implements full-text search with relevance ranking
- Supports faceted search and content filtering
- Creates search-enhanced demo experience

**US-048: Chatbot Integration**
As a demo user I want an AI chatbot embedded in demo sites So that I can interact with site content intelligently
- Embeds AI assistant in all demo sites
- Provides context-aware responses based on crawled content
- Supports natural language queries about site information
- Integrates with OpenSearch for comprehensive content access
- Enhances demo presentation value for client meetings

### EPIC-04: Hybrid AI Agent System (CORE IMPLEMENTATION)
**Status:**  IN PROGRESS  
**Description:** True AI Agent system that layers AI API calls on existing foundation for intelligent decision making

**Existing User Stories (To Complete):**
- US-31: SmartMirrorAgent core System ML based (20% complete)
- US-34: Quality Monitoring System (95% complete) ✅ Proxy-optimized quality framework completed  
- US-35: Learning System with Pattern Storage (0% complete)
- US-36: FastAPI Backend Integration (0% complete)
- US-38: Real-time Quality Adaptation (75% complete) ✅ Quality monitoring framework completed
- US-39: Batch Processing and Statistics (0% complete)
- US-40: Performance Targets and Monitoring (60% complete) ✅ Quality assessment framework completed, ❌ Real-time monitoring missing
- US-33: Adaptive Crawling Strategies (40% complete)

**New AI-Powered User Stories:**

**US-049: AI Content Classification Layer** ✅ COMPLETED
As a demo factory operator I want AI-powered content worthiness assessment So that the system intelligently selects the most demo-valuable pages
- ✅ Replaces rigid URL filtering with AI content analysis
- ✅ Analyzes page content for client demonstration value  
- ✅ Provides confidence scores and reasoning for page selection decisions
- ✅ Falls back to heuristic classification if AI fails
- ✅ **Two-Stage Classification System**: Site type detection + site-specific AI prompts
- ✅ **16 Site-Specific AI Prompts**: Banking, E-commerce, Technology, Healthcare, Government, Legal, etc.
- ✅ **Enhanced Site Detection**: Keyword scoring system with weighted context (URL > Title > Content)
- ✅ **Confidence Scoring**: HIGH/MEDIUM/LOW/FALLBACK confidence levels with detailed match tracking
- ✅ **Smart Tiebreakers**: Priority-based resolution for tied classifications
- ✅ **Parsing Bug Fixes**: Robust response parsing with safety defaults
- ✅ **Comprehensive Pattern Matching**: 150+ keywords across all business categories
- 🔄 Learns from successful demo outcomes to improve classification (future enhancement)


  **Step 3: Smart Tiebreaking - TO BE DELETED/REPLACED**
  If multiple categories tie, the system uses priority ordering:
  1. Banking, Healthcare, Legal (high-stakes industries)
  2. Technology, E-commerce (business-focused)
  3. Entertainment, Personal (lower priority)


**US-050: AI Strategy Optimization Layer**
As a demo factory operator I want AI-enhanced crawling strategy refinement So that the system optimizes parameters for maximum demo quality
- Uses AI to refine base strategies from pattern matching
- Optimizes max_pages, request_gap, and JS rendering settings per site
- Suggests priority URL patterns based on site analysis
- Combines algorithmic speed with AI intelligence
- Provides reasoning for strategy adjustments

**US-051: AI Site Analysis Layer**  
As a demo factory operator I want intelligent site characteristic detection So that the system understands website structure and technology stack
- Combines heuristic detection with AI analysis of site characteristics
- Detects CMS, frameworks, and site complexity automatically
- Identifies optimal crawling approaches per technology stack
- Provides comprehensive site fingerprinting for strategy selection
- Maintains reliability through hybrid approach (AI + algorithms)

**US-052: Hybrid Architecture Implementation**
As a system architect I want a reliable hybrid AI system So that we get AI intelligence with algorithmic reliability
- Implements AI API integration with fallback to heuristics
- Ensures cost efficiency by using AI only where it adds most value
- Provides incremental AI migration capability
- Maintains system reliability during AI service outages
- Combines speed of algorithms with intelligence of AI decision making

**US-058: Persistent AI Classification Cache** 
As a demo factory operator I want AI classification results cached between sessions So that I can rerun crawls without paying AI costs for previously analyzed content
- Implements persistent disk-based cache storage for AI classification results
- Cache key generation based on content hash + URL pattern for reliable matching
- Automatic cache loading on system startup and saving on shutdown
- Cache invalidation policies with configurable TTL (time-to-live) settings
- Significant cost savings for repeat crawls of same or similar sites
- In-memory cache for session performance + persistent storage for cross-session savings
- Cache statistics and monitoring: hit/miss rates, cost savings, cache size management

**US-059: High-Performance Parallel AI Classification System**
As a demo factory operator I want AI classification to process URLs concurrently So that sitemap analysis completes in minutes instead of hours
- Implement concurrent/parallel processing for AI URL classification (5-8x speed improvement)
- Batch processing of 8-10 URLs simultaneously using asyncio.gather() for optimal throughput
- Aggressive heuristic pre-filtering to skip obvious junk URLs before expensive AI calls (30-50% cost reduction)
- Smart URL pattern caching to reuse classifications for similar URL structures
- Batch API calls to OpenAI for processing multiple URLs in single requests where possible
- Rate limiting and error handling for concurrent API requests to prevent throttling
- Progress monitoring and ETA calculation for large sitemap processing (5,000+ URLs)
- Reduce sitemap classification time from 2.5 hours to 30-45 minutes for comprehensive sites

**Implementation Phases:**
- **Phase 1**: AI Content Classification Layer (US-049)  COMPLETED
- **Phase 2**: Search Bar Integration (US-56)  NEXT PRIORITY
- **Phase 3**: AI Strategy Optimization Layer (US-050)  
- **Phase 4**: AI Site Analysis Layer (US-051)
- **Phase 5**: Complete Hybrid System Integration (US-052)

**Success Criteria:**
- 90% demo mirror quality score across all site types
- 90% important site coverage through intelligent content discovery
- True AI Agent functionality using LLM APIs for decisions
- Learning improvement in success rates over time
- Reliable fallback during AI service issues

**US-57: Set Up and Configure Reverse Proxy** ✅ COMPLETED
As a demo factory operator, I want to set up a reverse proxy that dynamically forwards requests to any target site so that I can easily inject our overlay without needing to create static mirrors.
- ✅ The reverse proxy routes incoming requests to the specified target site based on a configurable target URL
- 🔄 The proxy supports HTML response modification for search bar and chatbot overlay injection (ready for implementation)
- ✅ We can change the target site easily without restarting the proxy via `/auto-configure` endpoint
- ✅ The proxy operates with minimal latency overhead and includes security measures like CSP removal and CORS handling
- ✅ Docker integration allows automatic proxy startup on `docker-compose up`
- ✅ Auto-configuration integration triggers when crawler completes successfully
- ✅ Universal URL rewriting ensures proper styling and navigation across all site types

**US-56: Injecting Search Bar with Indexed Data**
As a demo factory operator, I want to inject a search bar into the proxied site that uses the indexed data from the scrape so that users can search the mirrored content directly.
- We need to ensure the search bar appears on every proxied page at a predefined location in the DOM.
- The search bar must be connected to the indexed data gathered from the site so that all search queries return results from the scraped content.
- We need to verify that when a user enters a query, the search bar returns accurate results from the scraped index and displays them properly.
- The injected search functionality should not noticeably slow down the loading or performance of the proxied site.


**US-53: Intelligent Site Coverage Monitoring & Visualization** ✅ COMPLETED
As a demo factory operator I want comprehensive site completeness tracking with real-time visualization So that I can ensure optimal site content coverage during crawling with live dashboard monitoring

Implemented Features:

  1. ✅ Dynamic Coverage Calculation (dashboard_metrics.py)
  -  Real-time coverage percentage calculation: (pages_crawled / total_known_urls) * 100
  -  Adapts dynamically as new URLs are discovered during crawling (sitemap + discovered URLs)
  -  Coverage snapshots with phase tracking (initializing, crawling, completed)
  -  Quality trend analysis (improving/stable/declining) based on recent crawl results
  -  Crawl velocity calculation (pages per minute) and ETA estimation
  -  Session management with run_id tracking and comprehensive final statistics

  2. ✅ WebSocket Real-time Updates (websocket_manager.py)
  -  Live WebSocket broadcasting at /ws/coverage/{run_id} for frontend dashboard integration
  -  Real-time notifications: page crawled, URLs discovered, quality plateau alerts, crawl completion
  -  Multiple client support per crawl run with connection management and cleanup
  -  Heartbeat system and error handling for robust WebSocket connections
  -  Event broadcasting for crawl lifecycle (start, progress, plateau detection, completion)

  3. ✅ Smart Completion Logic Integration
  -  Leverages existing quality plateau detection from quality_plateau.py (no arbitrary stopping)
  -  Manual override capability through quality plateau "continue crawling?" prompts
  -  Intelligent stopping when quality stops improving rather than fixed page limits
  -  Integration with existing AI classification confidence scoring for quality assessment

  4. ✅ Frontend API & Performance (coverage_api.py)
  -  REST endpoints: GET /coverage/{run_id}, GET /coverage/{run_id}/summary, GET /active-runs
  -  WebSocket endpoint: /ws/coverage/{run_id} for live updates
  -  FastAPI + Pydantic models for type-safe API responses
  -  <2 second response times for coverage calculations with async architecture
  -  Health check endpoint and run cleanup management
  -  Export-ready JSON format for all coverage data

  5. ✅ Crawler Integration (hybrid_crawler.py, crawler_utils.py)
  -  Seamless integration with existing hybrid crawler and quality monitoring systems
  -  Run ID tracking throughout crawl lifecycle with coverage initialization and finalization
  -  Real-time notifications during crawling: notify_page_crawled(), notify_urls_discovered()
  -  Extended CrawlConfig with coverage tracking fields (run_id, classification_cache)
  -  Background coverage tracking with graceful fallback if components unavailable

    Implemented Files:
  - dashboard_metrics.py - Core coverage calculation logic and snapshot generation
  - websocket_manager.py - WebSocket connection management and real-time broadcasting  
  - coverage_api.py - FastAPI REST endpoints and WebSocket handlers
  - test_coverage_tracking.py - Comprehensive test suite (4/5 tests passing)
  - Updated hybrid_crawler.py - Coverage tracking integration with run_id support
  - Updated crawler_utils.py - Real-time notifications and extended configuration
  - Updated requirements.txt - Added websockets dependency for WebSocket functionality

    Technical Implementation:
  - Dynamic coverage calculation handles both sitemap-first and progressive discovery scenarios
  - Real-time WebSocket updates enable live dashboard visualization during crawling
  - Integration with existing quality plateau detection for intelligent stopping
  - Clean separation of concerns: crawler logic vs. frontend monitoring APIs
  - Session-scoped coverage tracking with proper cleanup and error handling

    Usage Examples:
  - Frontend connects to /ws/coverage/{run_id} for live crawling progress
  - GET /coverage/{run_id} returns current coverage snapshot with percentage, velocity, ETA
  - GET /coverage/{run_id}/summary provides final statistics and comprehensive results
  - Coverage calculator automatically tracks sitemap URLs + dynamically discovered URLs
  - Quality plateau integration provides intelligent stopping without arbitrary page limits

**US-61: Frontend Dashboard Integration for Real-time Coverage Monitoring**
As a demo factory operator I want a live dashboard interface So that I can visually monitor crawling progress in real-time

Acceptance Criteria:

  1. Live Coverage Display
  -  WebSocket connection to /ws/coverage/{run_id} for real-time updates
  -  Dynamic coverage percentage with progress bar: "45/120 pages (37.5%)"
  -  Crawl velocity and ETA: "12.5 pages/min, 6 minutes remaining"
  -  Current crawl phase and status indicators

  2. Quality Monitoring
  -  Real-time quality trend display (improving/stable/declining)
  -  Quality plateau alerts with manual override option
  -  Current URL being crawled with success/failure status

  3. Multi-Run Dashboard
  -  Active crawls overview from GET /active-runs
  -  Switch between multiple concurrent crawl monitoring
  -  Final results display with export functionality

    Technical Requirements:
  - React/Vue.js with WebSocket integration
  - Chart.js for coverage visualization
  - WebSocket auto-reconnection handling
  - Mobile-responsive design

    Integration:
  - WebSocket: /ws/coverage/{run_id}
  - REST APIs: /coverage/{run_id}, /coverage/{run_id}/summary, /active-runs
  - Backend: US-53 coverage tracking system

**US-54: Intelligent Site Structure Discovery & Coverage Planning** ✅ COMPLETED
As a demo factory operator I want comprehensive site architecture analysis during reconnaissance So that I can plan optimal crawling coverage with intelligent strategy selection

Implemented Features:

  ✅ **Hybrid Discovery Strategy Implementation** (hybrid_crawler.py)
  - **Scenario A: Sitemap-First Discovery** - Sites with accessible sitemaps get comprehensive URL inventory
  - **Scenario B: Progressive Discovery** - Sites without sitemaps use homepage + link following
  - Automatic strategy selection based on sitemap availability and accessibility
  - Integration with existing quality plateau detection for intelligent stopping

  ✅ **Sitemap Analysis & Processing**
  - Automatic sitemap detection: tests 5 common sitemap URL patterns (/sitemap.xml, /sitemap_index.xml, etc.)
  - LinkExtractor integration for sitemap parsing with AI classification support
  - AI-powered URL classification during sitemap processing (worthy vs filtered URLs)
  - Robots.txt intelligence gathering for crawling constraints
  - Fallback to progressive discovery when sitemaps unavailable/inaccessible

  ✅ **Intelligent Strategy Selection Logic**
  - Site type detection integration (Banking, E-commerce, etc.) for quality thresholds
  - AI classification of sitemap URLs with confidence scoring and reasoning
  - Priority URL ordering based on AI worthiness assessment
  - Dynamic max_pages recommendation based on discovered URL count
  - Quality threshold configuration per site type (Banking=strict, E-commerce=permissive)

  ✅ **Coverage Planning Integration**
  - Creates comprehensive CrawlPlan with strategy reasoning and priority URLs
  - Estimated coverage targets based on sitemap analysis (sitemap URLs + expected discoveries)
  - Integration with US-53 coverage monitoring for real-time progress tracking
  - Quality plateau integration for intelligent stopping without arbitrary limits
  - Session-scoped planning with run_id tracking and comprehensive results

    Technical Implementation:
  - **SitemapAnalysis dataclass**: Captures sitemap availability, URLs, AI classifications, robots intelligence
  - **CrawlPlan dataclass**: Strategic crawling plan with priority URLs and reasoning
  - **DiscoveryStrategy enum**: SITEMAP_FIRST vs PROGRESSIVE strategy types
  - **LinkExtractor integration**: Uses ../Utility/LinkExtractor for sitemap processing with AI support
  - **Quality threshold mapping**: Site-specific thresholds (BusinessSiteType → plateau settings)

    Actual Implementation Results:
  - Sitemap detection tests 5 common URL patterns automatically
  - AI classification during sitemap analysis for intelligent URL prioritization  
  - Limited to 10 URLs during testing (configurable max_urls parameter)
  - Comprehensive metadata collection: analysis timestamps, fallback reasons, discovery counts
  - Seamless fallback: sitemap failure → progressive discovery (no crawl interruption)
  - Integration with existing reconnaissance and quality monitoring systems

    Modified Files:
  - hybrid_crawler.py - Complete US-54 implementation with two-scenario strategy selection
  - (LinkExtractor in ../Utility/ handles sitemap parsing - separate component)

    Usage Examples:
  - Banking sites with sitemaps: Scenario A with AI-prioritized comprehensive URL inventory
  - Sites without sitemaps: Scenario B with homepage-based progressive discovery
  - Automatic fallback ensures crawling proceeds regardless of sitemap availability
  - Quality plateau detection provides intelligent stopping in both scenarios

S

**US-64: Fallback Floating Search Injection**
As a demo factory operator I want a floating search overlay as universal fallback So that every proxied site gets search capabilities regardless of their existing search implementation

Approach Benefits:
- **Universal Compatibility**: Works on any site regardless of existing search
- **No Layout Disruption**: Floating overlay doesn't affect original page structure
- **Visual Mimicry**: Copies styling from existing search elements when available
- **Always Available**: Guaranteed search injection when API replacement isn't possible
- **Flexible Positioning**: Adaptable placement (corner, top, side) based on page layout

Technical Implementation:
- **CSS Style Extraction**: Clone appearance of existing search elements
- **Intelligent Positioning**: Analyze page layout for optimal overlay placement
- **Responsive Design**: Adapt to mobile/desktop viewports
- **DOM Injection**: JavaScript creates search overlay after page load
- **Fallback Triggers**:
  - No search API endpoints detected
  - Form-based search (non-AJAX)
  - Complex/proprietary search systems
  - Sites with no existing search functionality

Search Functionality:
- **OpenSearch Integration**: Queries routed to our indexed content
- **Results Interface**: Custom results popup/panel with site-appropriate styling
- **Clickable Results**: Direct links to proxied pages
- **Auto-complete**: Optional suggestions based on indexed content
- **Search History**: Session-based search tracking

Acceptance Criteria:
- Floating search appears on all proxied pages when API replacement unavailable
- Search overlay matches site's visual design when possible
- Results return clickable links to relevant indexed content
- Overlay positioning doesn't interfere with site navigation
- Search functionality works across desktop and mobile viewports
- Fallback gracefully handles sites with existing search

**US-63: API Replacement Search Injection** ✅ COMPLETED
As a demo factory operator I want to intercept and replace site search APIs with OpenSearch results So that users get enhanced search capabilities powered by our comprehensive indexed content

✅ **Implemented Features:**
- **Universal API Detection**: Detects search APIs using path indicators (search, find, query, lookup, results, api/search) + search parameters (q, query, search, term, keyword, text)
- **Request Interception**: Proxy server intercepts matching requests before forwarding to target site
- **OpenSearch Integration**: Queries routed to indexed crawl content with relevance scoring
- **Response Formatting**: Returns results in standard search API JSON format
- **Container Integration**: Works in Docker with opensearch-demo service networking

✅ **Working Implementation:**
- Path `/search?term=about` successfully intercepted and returns OpenSearch results
- 270+ NAB pages indexed and searchable via demo-nab index
- JSON response format with query, total, results, source fields
- Universal detection works across all target sites

❌ **Current Issue: Raw JSON Response**
- Search returns raw JSON instead of styled HTML results page
- Links in results point to original site URLs instead of proxy URLs
- No visual integration with target site's search results styling

**US-65: HTML Search Results Rendering & URL Rewriting**
As a demo factory operator I want search API responses to return properly formatted HTML pages with proxy-rewritten URLs So that users get a seamless search experience that looks native to the target site

**Implementation Approach:**
- **Smart Template System**: Fetch target site's search results page once, extract styling/structure, cache template
- **Dynamic HTML Generation**: Fill cached template with OpenSearch results using site-appropriate styling
- **URL Rewriting**: Convert all result URLs from `https://nab.com.au/page` to `http://localhost:8000/proxy/page`
- **Universal Compatibility**: Template system works with any target site automatically
- **Response Format**: Return HTMLResponse instead of JSONResponse for browser compatibility

**Technical Implementation:**
```python
async def handle_search_request(query: str, original_path: str) -> HTMLResponse:
    # 1. Get cached search template for target site
    template = await get_search_template(proxy_config["target_url"])

    # 2. Get OpenSearch results
    results = opensearch_integration.search(query, index_name)

    # 3. Rewrite URLs to proxy
    for result in results["hits"]:
        result["url"] = rewrite_to_proxy_url(result["url"])

    # 4. Generate HTML page using template + results
    html = render_search_results(template, results, query)

    return HTMLResponse(content=html)
```

**Acceptance Criteria:**
- Search requests return styled HTML pages that match target site design
- All result links point to proxy URLs (localhost:8000/proxy/...) and are clickable
- Search results page integrates seamlessly with target site navigation
- Template system automatically adapts to different target sites (NAB, CommBank, etc.)
- Search functionality maintains target site's look and feel
- Page loading performance remains fast (<500ms for search results)

