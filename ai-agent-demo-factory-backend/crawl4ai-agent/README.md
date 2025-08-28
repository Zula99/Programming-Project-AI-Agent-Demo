# SmartMirrorAgent - AI Demo Factory Crawler

## Overview

The SmartMirrorAgent is a single adaptive agent with learning capabilities designed to achieve **90% visual fidelity and content coverage** across all website types. It combines intelligent reconnaissance, adaptive crawling strategies, real-time quality monitoring, and learning-based optimization.

## Architecture

### Core Components

1. **SmartMirrorAgent Core** (`smart_mirror_agent.py`)
   - Main orchestration and flow control
   - Pattern storage and memory management
   - Quality metrics definitions

2. **Site Reconnaissance** (`reconnaissance.py`) 
   - Quick site analysis (<10s target)
   - Framework detection (React, Angular, Vue, WordPress, etc.)
   - JavaScript complexity assessment
   - Site type classification (Banking, E-commerce, News, SPA, etc.)

3. **Adaptive Crawler** (`adaptive_crawler.py`)
   - Multi-strategy crawling with real-time adaptation
   - Strategies: Basic HTTP, JavaScript Render, Full Browser, Hybrid
   - Quality monitoring checkpoints during crawling
   - Asset extraction and categorization

4. **Quality Monitor** (`quality_monitor.py`)
   - Multi-dimensional scoring system
   - Content Completeness (35% weight)
   - Asset Coverage (25% weight) 
   - Navigation Integrity (20% weight)
   - Visual Fidelity (20% weight)

5. **Learning System** (`learning_system.py`)
   - SQLite-based pattern database
   - Similarity matching for strategy recommendation
   - Success rate tracking and improvement over time
   - Framework-based pattern recognition

## Agent Flow

```
URL Input → Check Memory → Quick Recon → Strategy Selection → 
Adaptive Crawl → Quality Monitoring → Mirror Build → Learning Storage
```

### Performance Targets

- **Universal 90% Success Rate**: 90% visual fidelity and content coverage for ALL site types
- **Speed Targets**: 
  - Reconnaissance: <10s
  - Strategy Selection: <5s  
  - Full Crawl: 5-30min
  - Mirror Building: <5min

### Quality Score Ranges

- **0.9-1.0**: Excellent - continue strategy
- **0.8-0.89**: Good - minor tweaks
- **0.7-0.79**: Acceptable - monitor
- **0.6-0.69**: Poor - fallback strategy  
- **<0.6**: Failed - major strategy change

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Install additional browser dependencies:
```bash
# For Playwright (Full Browser strategy)
playwright install

# For Crawl4AI
pip install crawl4ai
```

## Usage

### Single URL Processing

```bash
python agent_main.py "https://www.example.com" --max-pages 50
```

### Batch Processing

```bash
python agent_main.py "https://www.nab.com.au" "https://www.anz.com.au" --batch-mode --max-pages 30
```

### Programmatic Usage

```python
from agent_main import SmartMirrorAgentIntegrated

# Initialize agent
agent = SmartMirrorAgentIntegrated(
    output_dir="./output", 
    memory_db="agent_memory.db"
)

# Process single URL
result = await agent.process_url("https://www.example.com", max_pages=50)

# Process multiple URLs
results = await agent.process_multiple_urls([
    "https://www.site1.com",
    "https://www.site2.com"
], max_pages_per_url=30)
```

## Configuration

### Crawling Strategies

1. **BASIC_HTTP**: Simple HTTP requests
   - Best for: Static HTML sites, WordPress
   - Speed: Fastest
   - Compatibility: Static content only

2. **JAVASCRIPT_RENDER**: JavaScript execution with crawl4ai
   - Best for: Modern websites with moderate JS
   - Speed: Medium
   - Compatibility: Most dynamic content

3. **FULL_BROWSER**: Complete browser automation
   - Best for: Complex SPAs, banking sites
   - Speed: Slowest  
   - Compatibility: Highest

4. **HYBRID**: Adaptive combination approach
   - Best for: Unknown site types
   - Speed: Variable
   - Compatibility: Adaptive

### Site Type Detection

The agent automatically detects and classifies sites:

- **Banking**: Financial institutions requiring careful handling
- **E-commerce**: Shopping sites with dynamic content
- **SPA (React/Angular/Vue)**: Single-page applications
- **WordPress**: CMS-based sites
- **News**: Content-heavy news sites
- **Static HTML**: Traditional static websites

## Output Structure

```
agent_output/
├── mirrors/
│   ├── mirror_1640995200/
│   │   ├── crawl_data.json
│   │   └── static_files/
├── agent.log
└── agent_learning.db
```

## Learning System

The agent learns from successful crawls and improves over time:

- **Pattern Storage**: Stores successful strategies by domain/framework
- **Similarity Matching**: Finds similar sites for strategy recommendation  
- **Success Tracking**: Monitors and improves success rates
- **Memory Decay**: Applies time-based weighting to patterns

## Quality Metrics

### Content Completeness (35%)
- Text volume across pages
- Content depth and variety
- Successful page extraction rate

### Asset Coverage (25%) 
- CSS files successfully downloaded
- JavaScript files downloaded
- Images and media assets
- Font files

### Navigation Integrity (20%)
- Internal link coverage
- Site structure preservation
- Breadth vs depth balance

### Visual Fidelity (20%)
- CSS preservation and loading
- Layout structure integrity
- Asset availability for rendering

## Development Status

- ✅ Core agent architecture
- ✅ Reconnaissance system
- ✅ Multi-strategy crawler
- ✅ Quality monitoring
- ✅ Learning system with SQLite
- 🔄 Static mirror building (integration needed)
- 🔄 OpenSearch integration
- 🔄 Chatbot embedding

## Integration Points

This agent integrates with existing project components:

- **Crawl4AI**: Uses existing crawl implementations as strategies
- **Static Mirror Builder**: Will integrate `build_static_mirror.py`
- **OpenSearch**: Content indexing for search capabilities
- **Frontend**: API endpoints for demo factory interface

## API Integration

The agent can be exposed via FastAPI endpoints:

```python
from fastapi import FastAPI
from agent_main import SmartMirrorAgentIntegrated

app = FastAPI()
agent = SmartMirrorAgentIntegrated()

@app.post("/crawl")
async def crawl_url(url: str, max_pages: int = 50):
    return await agent.process_url(url, max_pages)
```

## Monitoring

The agent provides comprehensive monitoring:

- Real-time quality assessment
- Strategy effectiveness tracking
- Processing time metrics
- Success rate monitoring
- Learning progress indicators

## Target Achievement

The agent is designed to achieve the **Universal 90% Success Rate** through:

1. **Intelligent Strategy Selection**: Uses reconnaissance + learning
2. **Real-time Adaptation**: Adjusts based on quality monitoring  
3. **Learning Optimization**: Improves over time through pattern storage
4. **Multi-dimensional Quality**: Comprehensive success measurement
5. **Fallback Strategies**: Handles failures gracefully

## Next Steps

1. **Integration Testing**: Test with existing crawl4ai implementations
2. **Mirror Building**: Integrate static mirror generation
3. **OpenSearch Connection**: Add content indexing
4. **Performance Tuning**: Optimize for speed targets
5. **Learning Enhancement**: Add more sophisticated pattern matching