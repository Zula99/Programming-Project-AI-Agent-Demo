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

**Success Strategy**:
- Full JavaScript rendering during crawling
- Intelligent page prioritization based on site structure
- Content extraction optimized for OpenSearch indexing
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
- **Smart coverage** - 90% of important content rather than exhaustive crawling
- **Quality-driven decisions** - prioritize demo effectiveness over page count

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

### Quality Targets
- **90% demo mirror quality score** across all site types (JS-heavy and static)
- **90% important site coverage** through intelligent content discovery
- **Superior search performance** vs original sites through OpenSearch
- **Comprehensive content representation** including dynamically rendered content

### Performance Targets
- **Learning improvement** - success rates increase over time with pattern recognition
- **Speed targets**: Recon <10s, Strategy <5s, Smart crawl 5-30min, Mirror <5min
- **Intelligent stopping** - agent decides when sufficient coverage achieved for quality demos

### Dont's
- **Don't write emoji's into code.** - please dont 

## Future Implementation Ideas

### Docker Deployment Solution
**Problem**: Windows path length limits causing content loss and Windows script encoding errors
**Solution**: Containerized deployment eliminates filesystem limitations and character encoding issues
```dockerfile
FROM python:3.11-slim
# Linux filesystem = no Windows path limits!
# UTF-8 encoding by default = no Windows charmap codec errors
# Consistent cross-platform deployment
# Easy demo: docker run smart-mirror-agent nab.com.au
```

**Additional Benefits**:
- Fixes Windows charmap codec errors with Unicode characters
- Eliminates Windows-specific script execution issues
- Consistent UTF-8 encoding across all operations
- Better handling of special characters in crawled content

### AI-Powered Content Classification
**Problem**: Rule-based URL filtering too rigid - missing valuable content
**Current Issue**: NAB business pages like `/business/loans/commercial/agriculture` filtered out
**Smart Solution**: Replace hardcoded rules with AI content worthiness classifier

#### Phase 1: Hybrid AI Approach
```python
async def is_url_demo_worthy(url, title, meta_description) -> (worthy, confidence, reasoning):
    # AI judges: "92% worthy: Key business lending product, perfect for B2B demos"
    # Learn from: URL structure + page title + content + demo context
    # Site-specific learning: NAB patterns vs generic e-commerce
```

#### Phase 2: Full Content AI
- Extract page content snippet during crawl
- Classify based on actual content not just URL patterns  
- Dynamic thresholds per site type
- Demo context awareness: "What would impress a client?"

#### Phase 3: Smart Learning Agent
- Multi-factor analysis: URL + Title + Content + User behavior
- User feedback integration: "Was this useful in demo?"
- Confidence scoring for manual review of borderline cases
- Site-specific pattern learning and adaptation

**Target**: Most intelligent demo site builder with AI-driven content curation

## Current Issues to Address

### Duplicate Content Detection
**Problem**: Agent may crawl similar/duplicate pages reducing demo quality
**Solution**: Implement content similarity detection to avoid redundant pages

#### Implementation Strategy:
```python
def detect_duplicate_content(new_content: str, existing_pages: List[str]) -> bool:
    # Text similarity using cosine similarity or fuzzy matching
    # URL pattern similarity (e.g., /product/123 vs /product/456)
    # Content hash comparison for exact duplicates
    # Template detection (same layout, different data)
```

#### Benefits:
- **Higher quality demos** - unique content only
- **Better 90% coverage** - diverse content representation  
- **Faster crawling** - skip redundant pages
- **Improved metrics** - focus on meaningful content variety

#### Triggers for Duplicate Detection:
- Similar URL patterns (product pages, news articles)
- High text similarity scores (>85%)
- Same page templates with different data
- Paginated content series

### Dynamic Stopping Conditions
**Problem**: Fixed page limits (e.g., 200 pages) ignore actual coverage quality
**Current Issue**: Agent stops at arbitrary limit regardless of content quality or section coverage
**Solution**: Replace fixed limits with intelligent stopping based on quality metrics

#### Implementation Strategy:
```python
@dataclass
class StoppingConditions:
    min_pages: int = 15  # Minimum before considering stopping
    section_coverage_threshold: float = 0.9  # 90% sections covered
    quality_plateau_pages: int = 30  # Pages with no improvement
    content_diversity_threshold: int = 20  # Pages with similar content
    max_empty_worthy_streak: int = 50  # Max pages with 0 worthy links
    target_quality_score: float = 0.85  # Early stopping if achieved
```

#### Dynamic Stopping Logic:
- **Section Coverage**: Stop when 90% of main sections have content
- **Quality Plateau**: Stop if quality score hasn't improved in 30 pages
- **Content Exhaustion**: Stop if no worthy links found in 50 consecutive pages
- **Early Success**: Stop if quality target achieved before limit
- **Diversity Check**: Stop if content becomes repetitive

#### Better Progress Display:
```
[47 pages | 14/15 sections | 87% quality | continuing...]
[190 pages | 15/15 sections | 91% quality | stopping - target achieved]
```