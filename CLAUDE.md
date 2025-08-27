# Claude Context File

## Project Overview
AI Agent Demo Factory - Creates demo versions of client websites with integrated chatbot and search capabilities for presentations and client demonstrations.

## Architecture
- **Crawl4AI**: Web crawling with full JavaScript rendering for content extraction
- **Norconex**: Web Crawling solution of Crawl4AI doesn't work
- **Static Mirror**: Offline-browseable site replicas with local asset linking  
- **OpenSearch**: Content indexing for semantic search across all crawled content
- **Search Integration**: Custom search bar that surpasses original site navigation
- **Chatbot Integration**: AI assistant embedded in demo sites
- **AI Agent System**: Automated crawling/mirroring with 90% success rate target

## Current Implementation

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
- Two-round asset fetching: HTML assets first, then CSS dependencies

## Key Performance Targets

### Universal 90% Success Rate
**Goal**: 90% visual fidelity and content coverage for ALL site types (JS-heavy and static)

**Success Strategy**:
- Full JavaScript rendering during crawling
- Comprehensive content extraction for OpenSearch indexing
- Visual preservation with functional enhancement through search layer
- Superior content discovery vs original site navigation

### Quality Scoring System
Multi-dimensional scoring for crawl success assessment:
- **Content Completeness** (35%): Text volume, content depth
- **Asset Coverage** (25%): CSS, JS, images successfully downloaded
- **Navigation Integrity** (20%): Internal links, site structure
- **Visual Fidelity** (20%): Layout preservation, styling accuracy

**Score Ranges**:
- 0.9-1.0: Excellent - continue strategy
- 0.8-0.89: Good - minor tweaks
- 0.7-0.79: Acceptable - monitor
- 0.6-0.69: Poor - fallback strategy
- <0.6: Failed - major strategy change

## AI Agent System

### Single Adaptive Agent Architecture
**SmartMirrorAgent** with learning capabilities and memory system:

**Core Components**:
- **Site Memory**: Pattern database for similar sites and successful strategies
- **Quality Monitor**: Real-time assessment during crawling
- **Strategy Adaptor**: Dynamic parameter adjustment based on quality feedback
- **Learning System**: Stores successful patterns for future use

**Implementation Phases**:
1. **Week 1**: Core agent with basic strategy selection and quality assessment
2. **Week 2**: Learning system with pattern storage and similarity matching
3. **Future**: Real-time adaptation and specialist tools

### Agent Flow
```
URL Input → Check Memory → Quick Recon → Strategy Selection → 
Adaptive Crawl → Quality Monitoring → Mirror Build → Learning Storage
```

### Learning Database
Stores successful crawling patterns:
- Framework detection signatures
- Successful crawler configurations
- Quality metrics per site type
- Failure patterns and recovery strategies

## Technical Philosophy

### Demo-First Approach
- **Visual appearance > perfect functionality**
- **Content discovery excellence** through OpenSearch
- **Enhanced user experience** via integrated search/chatbot
- **Ignore robots.txt** for comprehensive demo coverage
- **Breadth over depth** - maximum page coverage for indexing

### Search Quality Priority
**Text extraction hierarchy**:
1. Fully-rendered HTML text (post-JavaScript execution)
2. Meta descriptions and structured data  
3. Image alt text and captions
4. Hidden/collapsed content revealed by interactions
5. PDF content if linked

## Development Timeline
**Target**: Functional AI agent system in 1-2 weeks

**Week 1**: Core agent MVP with basic strategy selection and quality scoring
**Week 2**: Learning system integration and testing across diverse sites

## Current Status
- Basic NAB crawler operational (static HTML approach)
- Static mirror generation working with asset localization
- Quality scoring system architecture defined
- Ready for AI agent implementation with enhanced JS rendering
- OpenSearch integration architecture planned

## Next Major Implementation
1. **SmartMirrorAgent core**: Single adaptive agent with reconnaissance and strategy selection
2. **Quality scoring integration**: Real-time assessment and fallback logic
3. **Learning system**: Pattern database for strategy optimization
4. **Enhanced crawling**: Full JavaScript rendering and dynamic content capture
5. **Demo interface integration**: Search bar + chatbot embedding

## Success Metrics
- **90% visual fidelity** across all site types (JS-heavy and static)
- **Superior search performance** vs original sites through OpenSearch
- **Comprehensive content coverage** including dynamically rendered content
- **Learning improvement** - success rate increases over time with pattern recognition
- **Speed targets**: Recon <10s, Strategy <5s, Full crawl 5-30min, Mirror <5min