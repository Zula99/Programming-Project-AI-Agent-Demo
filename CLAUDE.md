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

### Learning System Implementation Strategy
**Problem**: Current learning system is conceptual - needs concrete implementation details
**Solution**: Structured learning database with pattern recognition and adaptive strategy selection

#### Phase 1: Basic Learning Infrastructure
```python
@dataclass
class SitePattern:
    domain: str
    site_type: str  # "banking", "ecommerce", "corporate", "news"
    framework_detected: List[str]  # ["react", "angular", "wordpress"]
    successful_config: Dict[str, Any]
    quality_score: float
    pages_crawled: int
    failure_patterns: List[str]
    timestamp: datetime
    
class LearningDatabase:
    def store_crawl_result(self, pattern: SitePattern):
        # Store successful/failed patterns
    def find_similar_sites(self, domain: str) -> List[SitePattern]:
        # Match by domain similarity, framework, structure
    def get_best_strategy(self, site_info: Dict) -> Dict[str, Any]:
        # Return optimized config based on learned patterns
```

#### Phase 2: Framework Detection & Site Fingerprinting
```python
def detect_site_characteristics(url: str, html_sample: str) -> Dict[str, Any]:
    return {
        "cms": detect_cms(html_sample),  # WordPress, Drupal, AEM
        "framework": detect_js_framework(html_sample),  # React, Vue, Angular
        "site_type": classify_site_type(url, html_sample),  # Banking, retail, corporate
        "complexity_score": assess_js_complexity(html_sample),
        "api_patterns": detect_api_endpoints(html_sample),
        "asset_structure": analyze_asset_patterns(html_sample)
    }
```

#### Phase 3: Adaptive Strategy Selection
```python
class StrategyLearner:
    def select_crawl_strategy(self, site_characteristics: Dict) -> CrawlConfig:
        # Query learning database for similar sites
        similar_sites = self.db.find_similar_sites(site_characteristics)
        
        if similar_sites:
            # Use weighted average of successful configs
            return self.blend_successful_configs(similar_sites)
        else:
            # Use conservative defaults for unknown site types
            return self.get_safe_defaults(site_characteristics)
    
    def update_from_results(self, config: CrawlConfig, results: Dict):
        # Store success/failure patterns for future learning
        pattern = SitePattern.from_crawl_results(config, results)
        self.db.store_pattern(pattern)
```

#### Phase 4: Real-time Learning & Adaptation
```python
class AdaptiveCrawler:
    def __init__(self):
        self.learner = StrategyLearner()
        self.quality_monitor = QualityMonitor()
    
    async def crawl_with_learning(self, url: str):
        # 1. Detect site characteristics
        site_info = await self.reconnaissance(url)
        
        # 2. Get learned strategy
        config = self.learner.select_crawl_strategy(site_info)
        
        # 3. Crawl with real-time monitoring
        results = await self.adaptive_crawl(config, site_info)
        
        # 4. Learn from results
        self.learner.update_from_results(config, results)
        
        return results
```

#### Implementation Benefits:
- **Faster strategy selection** - no manual tuning for new sites
- **Improving success rates** - learns from both successes and failures  
- **Site-type specialization** - banking sites vs e-commerce vs news
- **Failure recovery** - learns what doesn't work and avoids it
- **Configuration optimization** - fine-tunes parameters over time

### AI Enhancement Strategy (Hybrid Approach)
**Problem**: Current system is algorithmic/rule-based, not true "AI Agent" despite project name
**Solution**: Layer AI API calls on top of existing solid foundation - enhance rather than replace

#### Phase 1: AI Content Classification Layer
```python
class AIContentClassifier:
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.fallback_classifier = HeuristicClassifier()  # Keep existing logic
    
    async def is_page_demo_worthy(self, url: str, content: str, context: str = "business") -> tuple[bool, float, str]:
        try:
            prompt = f"""
            Analyze this webpage for demo site value:
            URL: {url}
            Content: {content[:1000]}
            Demo Context: {context}
            
            Rate worthiness (0-100), explain reasoning, focus on client impression value.
            Return: score, reasoning
            """
            
            response = await self.llm_client.classify(prompt)
            return self.parse_ai_response(response)
        except Exception:
            # Fallback to existing heuristic classification
            return self.fallback_classifier.classify(url, content)
```

#### Phase 2: AI Strategy Refinement Layer  
```python
class AIStrategyOptimizer:
    async def refine_crawl_strategy(self, base_strategy: Dict, site_info: Dict) -> Dict:
        prompt = f"""
        Base crawling strategy from pattern matching: {base_strategy}
        Site characteristics: {site_info}
        
        Optimize this strategy for maximum demo quality:
        - Adjust max_pages for site complexity
        - Optimize request_gap for site responsiveness  
        - Fine-tune JS rendering settings
        - Suggest priority URL patterns
        
        Return optimized JSON configuration.
        """
        
        ai_refinements = await self.llm_client.optimize(prompt)
        return self.merge_strategies(base_strategy, ai_refinements)
```

#### Phase 3: AI Site Analysis Layer
```python
class AISiteAnalyzer:
    async def analyze_site_characteristics(self, url: str, html_sample: str) -> Dict:
        # Combine existing detection with AI analysis
        heuristic_analysis = self.detect_site_characteristics(url, html_sample)
        
        ai_analysis = await self.llm_analyze_site(url, html_sample)
        
        return self.combine_analyses(heuristic_analysis, ai_analysis)
```

#### Hybrid Architecture Benefits:
- **True AI Agent** - uses LLM APIs for intelligent decision making
- **Reliability** - falls back to heuristics if AI fails
- **Cost Efficiency** - AI only where it adds most value
- **Incremental Migration** - can add AI layers gradually
- **Best of Both** - speed of algorithms + intelligence of AI

#### Learning Database Schema:
```sql
-- Site patterns table
CREATE TABLE site_patterns (
    id INTEGER PRIMARY KEY,
    domain TEXT,
    site_type TEXT,
    framework_detected TEXT,  -- JSON array
    successful_config TEXT,   -- JSON config
    quality_score REAL,
    pages_crawled INTEGER,
    failure_patterns TEXT,    -- JSON array  
    created_at TIMESTAMP
);

-- Performance metrics table  
CREATE TABLE crawl_metrics (
    pattern_id INTEGER REFERENCES site_patterns(id),
    metric_name TEXT,
    metric_value REAL,
    created_at TIMESTAMP
);
```

## Current Issues to Address

### Critical Issues (Must Fix)

#### Windows Encoding Errors → Mirror Visual Issues
**Problem**: `'charmap' codec can't encode character '\u2192'` causes crawl failures, resulting in broken mirrors with oversized background elements
**Root Cause**: Windows charmap codec can't handle Unicode characters (arrows, quotes, symbols) common in modern websites
**Impact**: 
- CommBank and other Unicode-heavy sites fail completely
- Partial crawls create broken mirrors with dominant fallback elements (yellow triangles)
- Demos look unprofessional for client presentations
**Solution**: Docker deployment provides UTF-8 consistency and eliminates Windows filesystem limitations
**Status**: 🔴 Critical - single fix resolves multiple symptoms

#### Hardcoded Dependencies (FIXED ✅)
**Problem**: build_static_mirror.py had hardcoded "nab.com.au" domain and output paths
**Solution**: Refactored to use dynamic domain/output parameters via new API functions
**Status**: ✅ Fixed - mirror builder now fully generic for any domain

### Enhancement Issues (AI Agent Alignment)

#### AI Integration Gap
**Problem**: Current system is algorithmic/rule-based, not true "AI Agent" despite project name
**Impact**: System doesn't use AI APIs for decision making, misaligned with project goals
**Solution**: Hybrid approach - layer AI API calls on existing solid foundation
**Implementation Plan**:
- Phase 1: AI content classification layer
- Phase 2: AI strategy refinement layer  
- Phase 3: AI site analysis layer
**Status**: 🔵 Enhancement - detailed implementation strategy documented

#### Learning System Implementation
**Problem**: Learning system is conceptual, lacks concrete data structures and algorithms
**Impact**: No improvement over time, requires manual strategy tuning for each new site type
**Solution**: Structured learning database with pattern recognition and adaptive strategy selection
**Implementation**: SitePattern dataclass, LearningDatabase, SQL schema defined
**Status**: 🔵 Enhancement - ready for implementation

### Performance Issues

#### Asset Download Reliability
**Problem**: CDN 403 errors, malformed URLs, robots.txt blocking reduce mirror visual fidelity
**Root Cause**: External CDN restrictions, Windows path separator issues in URLs
**Impact**: Missing CSS, images, fonts make demos look broken
**Solution**: Enhanced asset downloading with better URL normalization and error handling
**Status**: 🟡 Partially Fixed - improved but needs Docker deployment for full resolution

#### Content Classification Intelligence
**Problem**: Rule-based URL filtering too rigid, missing valuable business content
**Example**: NAB business pages like `/business/loans/commercial/agriculture` filtered out
**Impact**: Important demo-worthy content excluded, reducing completeness
**Solution**: AI-powered content worthiness classification (part of AI integration plan)
**Status**: 🔵 Future Enhancement - depends on AI integration

### Optimization Issues

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