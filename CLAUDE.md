# Claude Context File

## Project Overview
AI Agent Demo Factory - Creates demo versions of client websites with integrated chatbot and search capabilities for presentations and client demonstrations.

## Architecture
- **Crawl4AI**: Web crawling with full JavaScript rendering for content extraction
- **Static Mirror**: Offline-browseable site replicas with local asset linking  
- **OpenSearch**: Content indexing for semantic search across all crawled content
- **Search Integration**: Custom search bar that surpasses original site navigation
- **Chatbot Integration**: AI assistant embedded in demo sites
- **AI Agent System**: Automated crawling/mirroring with 90% success rate target

## Current Implementation Status

### Working Components ✅
- **Basic NAB crawler** operational (static HTML approach)
- **Static mirror generation** working with asset localization
- **Docker deployment** - Windows encoding issues resolved
- **Quality scoring system** architecture defined
- **UTF-8 support** verified in containerized environment
- **AI Content Classification** - OpenAI integration for intelligent demo content selection

### Crawling (`crawl4ai/`)
- `crawl_nab.py`: NAB bank crawler (80 pages max, 0.6s delays)
- Uses AsyncWebCrawler for content extraction
- Saves raw HTML, markdown, and metadata in folder structure
- Currently respects robots.txt (but will ignore for demo purposes)

### Static Mirroring (`crawl4ai/build_static_mirror.py`)
- Converts crawled content to offline-browseable mirror
- Downloads and localizes assets (CSS, JS, images, fonts) 
- Rewrites URLs to point to local files
- Handles CSS dependencies and @import statements
- Creates index.html files in folder structure matching URLs

## Key Performance Targets

### Dual 90% Success Targets

#### 90% Demo Mirror Quality
**Goal**: Achieve 90% quality score for demo mirror across all site types (JS-heavy and static)

**Quality Components**:
- **Content Completeness** (35%): Representative content depth and coverage
- **Asset Coverage** (25%): CSS, JS, images successfully downloaded and functional
- **Navigation Integrity** (20%): Internal links working, site structure preserved
- **Visual Fidelity** (20%): Layout preservation, styling accuracy matching original

#### 90% Site Coverage
**Goal**: Intelligent crawling to capture 90% of important site content for comprehensive demos

**Smart Coverage Strategy**:
- **Structural Analysis**: Identify key sections, main navigation paths
- **Content Sampling**: Representative pages from each major section
- **Dynamic Discovery**: Follow important link patterns, avoid duplicate content types
- **Quality-Driven Stopping**: Stop when additional pages provide diminishing demo value
- **Breadth over Depth**: Cover all major areas rather than exhaustive page crawling

## AI Agent System (Next Priority)

### Current Gap
System is algorithmic/rule-based, not true "AI Agent" despite project name. Needs AI API integration for intelligent decision making.

### SmartMirrorAgent Architecture
**Core Components Needed**:
- **AI Content Classification**: Replace rigid URL filtering with intelligent demo worthiness detection
- **Learning System**: Pattern database for similar sites and successful strategies
- **Quality Monitor**: Real-time assessment during crawling
- **Strategy Adaptor**: Dynamic parameter adjustment based on quality feedback

### Agent Flow
```
URL Input → AI Site Analysis → Strategy Selection → 
Adaptive Crawl → Quality Monitoring → Mirror Build → Learning Storage
```

## Current Active Issues

### Enhancement Issues (Priority)

#### AI Integration Gap - ✅ RESOLVED
**Problem**: Current system is algorithmic/rule-based, not true "AI Agent" despite project name
**Impact**: System doesn't use AI APIs for decision making, misaligned with project goals
**Solution**: Hybrid approach - layer AI API calls on existing solid foundation
**Status**: ✅ COMPLETED - AI content classification integrated with OpenAI GPT-3.5-turbo

#### Learning System Implementation
**Problem**: Learning system is conceptual, lacks concrete data structures and algorithms
**Impact**: No improvement over time, requires manual strategy tuning for each new site type
**Solution**: Structured learning database with pattern recognition and adaptive strategy selection
**Next Step**: Create SitePattern dataclass and LearningDatabase implementation

### Performance Issues

#### Asset Download Reliability 
**Problem**: CDN 403 errors, malformed URLs, robots.txt blocking reduce mirror visual fidelity
**Impact**: Missing CSS, images, fonts make demos look broken
**Status**: 🟡 Partially Fixed - improved but needs further enhancement
● Perfect! Now let's verify the complete implementation:

  ✅ Strategy Implementation Complete

  What We Fixed:

  1. Extended CrawlConfig - Added browser settings: timeout, wait_for, headless, screenshot,      
  javascript, max_concurrent
  2. Enhanced AgentCrawler - Updated crawl_website() to accept and pass browser configuration     
  parameters
  3. Completed SmartMirrorAgent Strategy Config - Updated strategy_to_config() with your
  complete browser settings:
    - FULL_BROWSER: timeout=45s, delay=2.0s, wait_for='networkidle', headless=True,
  screenshot=True
    - JAVASCRIPT_RENDER: timeout=30s, wait_for='networkidle', javascript=True
    - BASIC_HTTP: Basic settings for static sites
  4. Updated Crawler Integration - Browser settings now flow through: SmartMirrorAgent →
  AgentCrawler → generic_crawl → crawl_page → AsyncWebCrawler.arun()

  For CommBank (JS-Heavy Sites):

  Strategy Selection Logic ✅ Working:
  - Banking site + High JS complexity → CrawlStrategy.FULL_BROWSER
  - Settings: 45s timeout, 2.0s delays, networkidle wait, headless mode, screenshots enabled      

  This should fix the loader screen issue because:
  - wait_for='networkidle' - Waits for all JS/network activity to finish
  - timeout=45s - Plenty of time for heavy apps to load completely
  - delay=2.0s - Respectful spacing between requests
  - Screenshots enabled - Can verify what content we're actually capturing

  The next step is testing this with CommBank to confirm the loader screen issue is resolved!   

#### Content Classification Intelligence - ✅ RESOLVED
**Problem**: Rule-based URL filtering too rigid, missing valuable business content
**Example**: NAB business pages like `/business/loans/commercial/agriculture` filtered out
**Impact**: Important demo-worthy content excluded, reducing completeness
**Solution**: AI-powered content worthiness classification 
**Status**: ✅ COMPLETED - AI analyzes actual page content for demo value instead of rigid URL patterns

## Technical Philosophy

### Demo-First Approach
- **Visual appearance > perfect functionality**
- **Content discovery excellence** through OpenSearch
- **Enhanced user experience** via integrated search/chatbot
- **Ignore robots.txt** for comprehensive demo coverage
- **Smart coverage** - 90% of important content rather than exhaustive crawling
- **Quality-driven decisions** - prioritize demo effectiveness over page count

### Success Metrics
- **90% demo mirror quality score** across all site types (JS-heavy and static)
- **90% important site coverage** through intelligent content discovery
- **Superior search performance** vs original sites through OpenSearch
- **Learning improvement** - success rates increase over time with pattern recognition

## Development Status
**Current**: Basic crawler operational, Docker encoding issues resolved
**Next Priority**: AI integration for intelligent content classification and strategy selection
**Timeline**: Functional AI agent system in 1-2 weeks

## Usage (Docker - Recommended)
```bash
# Quick start
docker-compose up -d
docker-compose exec ai-agent-demo python run_agent.py

# Test UTF-8 support
docker-compose exec ai-agent-demo python -c "print('UTF-8 test: → ← ↑ ↓ © ®')"
```

---

## Completed Work Archive

### ✅ Windows Encoding Issues - RESOLVED
**Problem**: `'charmap' codec can't encode character '\u2192'` causing crawl failures
**Solution**: Docker deployment with UTF-8 environment
**Status**: Docker successfully tested with CommBank crawling 49+ pages without Unicode errors

### ✅ Hardcoded Dependencies - FIXED  
**Problem**: build_static_mirror.py had hardcoded "nab.com.au" domain and output paths
**Solution**: Refactored to use dynamic domain/output parameters via new API functions
**Status**: Mirror builder now fully generic for any domain

### ✅ AI Content Classification - COMPLETED
**Problem**: Rule-based URL filtering too rigid, missing valuable business content
**Solution**: OpenAI GPT-3.5-turbo integration for intelligent content worthiness assessment
**Implementation**: Hybrid AI + heuristic + basic filtering with real-time page content analysis
**Status**: True AI Agent system using LLM APIs for intelligent demo content curation (~$0.02/page)
**Future Note**: AI prompt may need adjustment if valuable content is incorrectly filtered as WORTHY=False



**User Stories:**

**US-044: Docker Deployment Solution**
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
- US-35: Learning System with Pattern Storage (0% complete)
- US-36: FastAPI Backend Integration (0% complete)
- US-38: Real-time Quality Adaptation (0% complete)
- US-39: Batch Processing and Statistics (0% complete)
- US-40: Performance Targets and Monitoring (30% complete)
- US-33: Adaptive Crawling Strategies (40% complete)

**New AI-Powered User Stories:**

**US-049: AI Content Classification Layer** ✅ COMPLETED
As a demo factory operator I want AI-powered content worthiness assessment So that the system intelligently selects the most demo-valuable pages
- ✅ Replaces rigid URL filtering with AI content analysis
- ✅ Analyzes page content for client demonstration value
- ✅ Provides confidence scores and reasoning for page selection decisions
- ✅ Falls back to heuristic classification if AI fails
- 🔄 Learns from successful demo outcomes to improve classification (future enhancement)

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

**Implementation Phases:**
- **Phase 1**: AI Content Classification Layer (US-049) ✅ COMPLETED
- **Phase 2**: AI Strategy Optimization Layer (US-050) 🔄 NEXT PRIORITY  
- **Phase 3**: AI Site Analysis Layer (US-051)
- **Phase 4**: Complete Hybrid System Integration (US-052)

**Success Criteria:**
- 90% demo mirror quality score across all site types
- 90% important site coverage through intelligent content discovery
- True AI Agent functionality using LLM APIs for decisions
- Learning improvement in success rates over time
- Reliable fallback during AI service issues