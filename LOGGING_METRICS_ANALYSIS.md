# Comprehensive Logging & Metrics Analysis
## AI Agent Demo Factory - Backend vs Frontend Capabilities

---

## Executive Summary

The **backend has extensive logging and metrics capabilities** that are **largely untapped by the frontend**. We have rich data collection but minimal visualization, creating significant opportunities for enhanced user experience and system transparency.

### Key Findings:
- ✅ **Backend**: Comprehensive metrics (cost, quality, coverage, AI decisions)
- ❌ **Frontend**: Only basic progress and logs displayed
- 🚀 **Opportunity**: 70%+ of backend metrics not surfaced to users

---

## Current Backend Capabilities ✅

### 1. **Cost Tracking System** 📊
**File**: `cost_tracker.py`
**Status**: ✅ **Fully Implemented**

**What We Log**:
- Real-time API costs per call ($0.00015/$0.0006 per 1K tokens)
- Token usage (prompt/completion/total)
- Method breakdown (AI/cache/heuristic)
- Daily cost summaries and session reports
- Budget monitoring with monthly limits

**Example Output**:
```
💰 $0.000234 | Total session: $0.0245
💰 $0.0245 | 42 calls, 18 cached | 78.3% worthy
```

### 2. **Quality Scoring System** 🎯
**File**: `quality_monitor.py`
**Status**: ✅ **Fully Implemented**

**Metrics Tracked**:
- Content Discovery Score (85%)
- AI Classification Score (92%)
- Site Coverage Score (78%)
- Processing Efficiency (95%)
- Overall Quality Score (87.5%)

### 3. **AI Classification Intelligence** 🤖
**File**: `ai_content_classifier.py`
**Status**: ✅ **Advanced System**

**Classification Data**:
- 12+ site-specific prompt templates
- Confidence scores (0.0-1.0)
- Decision reasoning text
- Site type detection (banking, e-commerce, tech, etc.)
- Classification method used (AI/cache/heuristic)

**Models Supported**:
- OpenAI: `gpt-4o-mini`, `gpt-4`, `gpt-3.5-turbo`
- Anthropic: `claude-3-haiku`, `claude-3-sonnet`
- Fallback: `heuristic` (no cost)

### 4. **Coverage Analytics** 📈
**Files**: `dashboard_metrics.py`, `coverage_api.py`
**Status**: ✅ **Real-time Tracking**

**Data Collected**:
- Dynamic coverage percentage
- URL discovery tracking (sitemap vs discovered)
- Phase tracking (initializing, crawling, quality_plateau)
- Crawl velocity (pages/minute)
- Estimated time remaining

### 5. **Comprehensive Logging** 📝
**Files**: `crawl_logger.py`, `main.py` (WebSocket handler)
**Status**: ✅ **Multi-layered System**

**Logging Capabilities**:
- Domain-based file naming with timestamps
- Phase-based structured logging
- Real-time WebSocket broadcasting to frontend
- Multi-source log separation (crawler, classifier, parser)
- UTF-8 support for international content

---

## Current Frontend Display ❌

### 1. **Basic Progress Panel**
**File**: `CrawlProgressPanel.tsx`
**Status**: ⚠️ **Limited Display**

**What's Shown**:
- Progress bar (percentage)
- Pages crawled/remaining counts
- Crawl speed (pages/minute)
- Time remaining estimate

**Missing**:
- Cost information
- Quality metrics
- AI classification details
- Coverage analytics

### 2. **Simple Log Display**
**Files**: `AgentOutputCard.tsx`, `BackendLogsDropdown.tsx`
**Status**: ⚠️ **Basic Terminal View**

**What's Shown**:
- Color-coded log entries
- Real-time WebSocket streaming
- Basic log level filtering (info, warning, error)

**Missing**:
- Cost per operation
- AI decision reasoning
- Quality trend visualization
- Classification confidence display

---

## Critical Gaps 🚨

### **Gap 1: Cost Transparency**
- **Backend Has**: Real-time cost tracking, token usage, budget monitoring
- **Frontend Missing**: No cost display anywhere
- **Impact**: Users unaware of API spend, no budget visibility

### **Gap 2: Quality Insights**
- **Backend Has**: Multi-dimensional quality scoring, trend analysis
- **Frontend Missing**: No quality metrics visualization
- **Impact**: Users can't assess crawl effectiveness or optimize strategies

### **Gap 3: AI Decision Visibility**
- **Backend Has**: Classification reasoning, confidence scores, model performance
- **Frontend Missing**: AI decision blackbox to users
- **Impact**: Users can't understand or improve AI classifications

### **Gap 4: Configuration Control**
- **Backend Has**: Model selection, prompt templates, cost controls
- **Frontend Missing**: No settings interface
- **Impact**: Users stuck with default configurations, can't optimize for their needs

### **Gap 5: Cache Management**
- **Backend Has**: Domain caching, hit/miss ratios, cache efficiency
- **Frontend Missing**: No cache visibility or controls
- **Impact**: Users can't manage cached results or force fresh crawls

---

## New User Stories 📋

### **EPIC-05: Advanced UI Controls & Transparency**
**Status**: NEW REQUIREMENT
**Priority**: HIGH
**Description**: Enhanced UI controls for AI prompt editing, model selection, and crawl management

---

### **US-060: AI Classification Prompt Editor** 🎨
**Title**: AI Classification Prompt Customization Interface
**Priority**: HIGH

**User Story**:
As a demo factory operator I want to view and edit the AI classification prompts So that I can adjust the classifier when it's too strict or too permissive for my specific demo needs

**Acceptance Criteria**:
- ✅ Display current classification prompts from `ai_content_classifier.py`
- ✅ Show 12+ site-specific prompt templates (Banking, E-commerce, Tech, etc.)
- ✅ Allow real-time prompt editing with syntax highlighting
- ✅ Preview prompt changes before applying
- ✅ Save custom prompts per domain/project
- ✅ Reset to default prompts option
- ✅ Validate prompt format and required placeholders
- ✅ Show prompt effectiveness metrics (classification accuracy)

**UI Components**:
- **Prompt Library**: Tabbed interface for different site types
- **Prompt Editor**: Monaco/CodeMirror editor with syntax highlighting
- **Preview Panel**: Test prompt against sample content
- **Metrics Dashboard**: Show classification accuracy with current vs custom prompts
- **Import/Export**: Save prompt sets as JSON files

**Technical Requirements**:
- New API endpoint: `GET /api/prompts/templates` and `POST /api/prompts/update`
- Prompt validation against required template variables
- Hot-reload classification system with new prompts
- Backup/restore functionality for prompt changes

---

### **US-061: AI Model & Company Selection** 🤖
**Title**: Dynamic AI Model and Provider Selection Interface
**Priority**: HIGH

**User Story**:
As a demo factory operator I want to select different AI models and companies (GPT-4o, Claude, Gemini) So that I can optimize cost, speed, and classification quality for different projects

**Acceptance Criteria**:
- ✅ **Model Selection Dropdown**:
  - OpenAI: GPT-4o, GPT-4, GPT-4o-mini, GPT-3.5-turbo
  - Anthropic: Claude-3-Sonnet, Claude-3-Haiku
  - Google: Gemini-1.5-Pro, Gemini-1.5-Flash (future)
- ✅ **Provider Toggle Interface**: Easy switching between OpenAI, Anthropic, Google
- ✅ **Real-time Cost Calculator**: Show cost differences between models
- ✅ **Performance Metrics**: Speed, accuracy, token efficiency per model
- ✅ **API Key Management**: Secure API key input/validation interface
- ✅ **Model Availability Status**: Live status indicator (available/unavailable/rate-limited)
- ✅ **Fallback Configuration**: Auto-fallback to cheaper models when primary unavailable

**UI Components**:
- **Model Selector**: Two-level dropdown (Company → Model)
- **Cost Comparison Table**: Real-time pricing comparison
- **Performance Dashboard**: Speed/accuracy/cost metrics per model
- **API Key Manager**: Secure credential input with validation
- **Model Status Indicators**: Live availability with error descriptions

**Technical Requirements**:
- Extended `ai_config.py` with new model definitions
- API key validation endpoints for each provider
- Model performance tracking and comparison
- Graceful fallback logic when primary models unavailable
- Cost estimation API for different model combinations

---

### **US-062: Crawl History & Cache Management** 🗂️
**Title**: Previous Crawl Display and Cache Control System
**Priority**: MEDIUM

**User Story**:
As a demo factory operator I want to view previous crawls and delete their cache/recrawl with new settings So that I can test different AI prompts and models without cache interference

**Acceptance Criteria**:
- ✅ **Crawl History Table**: Display last 50 crawl sessions with metadata
  - Domain, timestamp, quality score, cost, model used, status
  - Sortable columns with search/filter capability
- ✅ **Cache Status Display**: Show cache hit ratio and cache size per domain
- ✅ **Delete Cache Button**: Clear domain-specific cache with confirmation
- ✅ **Recrawl with New Settings**: One-click recrawl with updated prompts/models
- ✅ **Cache Management**:
  - View cache contents (URLs cached, classification results)
  - Selective cache deletion (specific URLs or date ranges)
  - Cache efficiency metrics (hit rate, storage size, age)
- ✅ **Settings Comparison**: Compare current settings vs previous crawl settings
- ✅ **Export Results**: Download crawl results and metrics as CSV/JSON

**UI Components**:
- **History Table**: DataTable with sorting, filtering, pagination
- **Cache Viewer**: Expandable sections showing cached classifications
- **Cache Controls**: Delete buttons with confirmation dialogs
- **Settings Comparison**: Side-by-side comparison of crawl configurations
- **Export Options**: Format selection and download triggers

**Technical Requirements**:
- New API endpoints: `GET /api/crawls/history`, `DELETE /api/cache/{domain}`, `POST /api/crawls/recrawl`
- Enhanced cache tracking with metadata (timestamp, model used, prompt version)
- Cache analysis functionality (size, hit rates, age distribution)
- Secure deletion with confirmation steps
- Export functionality for audit trails and analysis

---

### **US-063: Real-time Cost & Quality Dashboard** 💰
**Title**: Comprehensive Metrics Dashboard for Cost and Quality Monitoring
**Priority**: HIGH

**User Story**:
As a demo factory operator I want to see real-time cost tracking, quality metrics, and AI decision insights during crawls So that I can monitor efficiency and optimize my configurations

**Acceptance Criteria**:
- ✅ **Real-time Cost Display**:
  - Current session cost with running total
  - Cost per URL and cost per AI call
  - Daily/monthly spend tracking with budget alerts
  - Token usage breakdown (prompt/completion tokens)
- ✅ **Quality Metrics Visualization**:
  - Overall quality score with trend indicator
  - Quality component breakdown (content, coverage, AI classification)
  - Quality plateau detection with stopping recommendations
- ✅ **AI Decision Transparency**:
  - Classification confidence scores per URL
  - AI reasoning display for each decision
  - Model performance metrics (accuracy, speed, cost)
  - Cache vs AI vs heuristic decision breakdown
- ✅ **Coverage Analytics**:
  - Dynamic coverage percentage with projections
  - URL discovery visualization (sitemap vs discovered)
  - Site structure analysis and coverage recommendations

**UI Components**:
- **Cost Widget**: Real-time cost counter with budget progress bar
- **Quality Dashboard**: Multi-metric quality visualization with trends
- **AI Decisions Panel**: Expandable list of recent classifications with reasoning
- **Coverage Map**: Visual representation of site coverage with gap identification

**Technical Requirements**:
- Enhanced WebSocket integration for real-time metric streaming
- New endpoints for historical metric data and trends
- Integration with existing cost_tracker.py and quality_monitor.py
- Dashboard state management for real-time updates

---

### **US-064: Advanced Log Management & Search** 🔍
**Title**: Enhanced Logging Interface with Filtering and Search
**Priority**: MEDIUM

**User Story**:
As a demo factory operator I want to filter, search, and export logs from crawl sessions So that I can debug issues and analyze system performance

**Acceptance Criteria**:
- ✅ **Advanced Filtering**:
  - Filter by log level (INFO, WARNING, ERROR, DEBUG)
  - Filter by source (crawler, classifier, parser, network)
  - Date/time range filtering
  - Custom keyword search with highlighting
- ✅ **Log Export Options**:
  - Download logs as plain text, JSON, or CSV
  - Export filtered results with custom date ranges
  - Include metrics data in exports for comprehensive analysis
- ✅ **Log Analytics**:
  - Error frequency analysis and categorization
  - Performance bottleneck identification
  - Success rate trends over time
- ✅ **Real-time Log Streaming**:
  - Enhanced WebSocket log streaming with better buffering
  - Log level configuration without restart
  - Multiple log stream subscriptions

**UI Components**:
- **Advanced Filter Panel**: Multi-criteria filtering with saved filter presets
- **Search Interface**: Full-text search with regex support and highlighting
- **Export Controls**: Format selection and custom export options
- **Log Analytics Dashboard**: Visual analysis of log patterns and trends

---

### **US-065: Logstash-OpenSearch Centralized Logging System** 📊
**Title**: Complete ELK Stack Integration for Centralized Log Management
**Priority**: HIGH - **CURRENT IMPLEMENTATION FOCUS**
**Epic**: EPIC-06: Centralized Logging & Observability

**User Story**:
As a demo factory operator I want all system logs (backend services, AI decisions, frontend events, proxy operations) centralized in OpenSearch via Logstash So that I can search, analyze, and monitor system behavior comprehensively from a single interface

## 🎯 **CURRENT IMPLEMENTATION STRATEGY**

### **Architecture Overview**
```
Backend Services → Logstash → OpenSearch → Frontend Dashboard
     ↓                ↓           ↓            ↓
Python Logging → JSON Format → Daily Indices → Real-time UI
WebSocket Logs → HTTP Input  → Log Categories → Historical Search
```

### **Dual Log Display Design**
1. **AgentOutputCard** (Top Panel): Clean user-friendly status updates via WebSocket
   - "Starting crawl", "Analyzing sitemap", "Crawling page 15/50"
   - Real-time progress without technical noise

2. **BackendLogsDropdown** (Bottom Panel): Comprehensive technical logs via OpenSearch
   - All backend logs indexed in OpenSearch
   - Historical search across sessions
   - Advanced filtering and export capabilities

**Acceptance Criteria**:

**Backend Log Integration** ✅:
- ✅ **Logstash Pipeline**: Process logs from all backend services (main.py, proxy_server.py, smart_mirror_agent.py, ai_content_classifier.py, learning_system.py)
- ✅ **Structured Log Format**: Convert existing Python logging to structured JSON format with @timestamp, level, service, component, message, metadata
- ✅ **WebSocket Log Streaming**: Extend current WebSocketLogHandler to dual-stream (frontend + Logstash)
- ✅ **File Log Collection**: Process existing CrawlLogger file outputs through Logstash Filebeat
- ✅ **AI Decision Logging**: Capture AI classification decisions, confidence scores, costs, and reasoning
- ✅ **Correlation IDs**: Link related log entries across services (crawl sessions, API requests)

**Frontend Log Integration** ✅:
- ✅ **Client-Side Logging**: Structured browser console logs sent to Logstash
- ✅ **WebSocket Event Logging**: Connection status, message parsing, API errors
- ✅ **User Interaction Logging**: Crawl starts, search queries, UI navigation
- ✅ **Performance Logging**: Component render times, API response times, WebSocket latency

**OpenSearch Index Management** ✅:
- ✅ **Log Index Structure**: Separate indices for different log types (backend-logs, frontend-logs, ai-decisions, system-metrics)
- ✅ **Index Templates**: Automated mapping for structured log fields with proper data types
- ✅ **Retention Policies**: 30-day log retention with automated cleanup
- ✅ **Index Rotation**: Daily index rotation for optimal performance

**Enhanced Log Search & Analytics** ✅:
- ✅ **Advanced Search Interface**: Time range, service, component, severity filtering
- ✅ **Real-time Log Dashboard**: Live log streaming from OpenSearch with filtering
- ✅ **Log Export Capabilities**: Download filtered logs as JSON/CSV for analysis
- ✅ **Error Tracking**: Automated error detection and alerting
- ✅ **Performance Monitoring**: API response times, crawl performance metrics
- ✅ **AI Cost Analytics**: Track AI API usage and costs across sessions

**UI Components**:
- **AgentOutputCard** (Top): Keep current design - WebSocket real-time status updates for clean UX
- **Enhanced BackendLogsDropdown** (Bottom): Comprehensive technical log viewer with:
  - **OpenSearch Integration**: Historical log search across all crawl sessions
  - **Advanced Filtering**: By time range, log level, component, correlation ID
  - **Real-time + Historical**: Current session logs + previous session access
  - **Export Controls**: Download filtered logs as JSON/CSV
  - **AI Decision Insights**: Show AI classification reasoning and confidence scores
  - **Performance Tracking**: Response times, error rates, cost analytics
  - **Search Capabilities**: Full-text search within technical logs

**Technical Requirements**:

**Docker Infrastructure**:
- **Logstash Container**: Add logstash:8.11.0 to docker-compose.yml
- **Logstash Configuration**: Pipeline for parsing Python logs, JSON logs, and frontend logs
- **Beats Integration**: Filebeat for log file collection from backend services
- **OpenSearch Integration**: Logstash output to existing OpenSearch container

**Backend Changes**:
- **Enhanced WebSocketLogHandler**: Dual output (WebSocket + Logstash)
- **Structured Logging Configuration**: JSON formatter for all Python loggers
- **Correlation ID System**: Add correlation IDs for tracking related operations
- **Log API Endpoints**: New endpoints for historical log retrieval from OpenSearch

**Frontend Changes**:
- **Dual Log Display Architecture**:
  - **AgentOutputCard** (Top): Keep current WebSocket for clean user-friendly status ("Crawl started", "Analyzing sitemap")
  - **BackendLogsDropdown** (Bottom): Upgrade to OpenSearch backend for comprehensive technical logs
- **Enhanced BackendLogsDropdown**: OpenSearch-powered search, filtering, historical access, export
- **LogstashLogger**: Client-side structured logging to Logstash endpoint
- **Export Functionality**: Download filtered technical logs as JSON/CSV for debugging

**Configuration Files**:
- **logstash.conf**: Complete pipeline configuration
- **index-templates.json**: OpenSearch mapping templates
- **filebeat.yml**: File log collection configuration
- **log-retention.json**: Automated cleanup policies

**Security & Performance**:
- **Authentication**: Secure Logstash endpoints with API keys
- **Rate Limiting**: Prevent log flooding from frontend
- **Compression**: Gzip compression for log transport
- **Buffering**: Logstash buffering for high-volume periods

**Integration Points**:
- **Existing WebSocket System**: Extend for Logstash dual-streaming
- **Current OpenSearch**: Add log indices alongside existing content indices
- **CrawlLogger System**: Maintain file logging + add Logstash shipping
- **Frontend Log Display**: Enhance with OpenSearch backend queries

**Success Metrics**:
- **Dual Log Architecture**: AgentOutputCard maintains <100ms real-time updates, BackendLogsDropdown provides comprehensive technical access
- **Log Centralization**: 100% of backend technical logs captured in OpenSearch via Logstash
- **Search Performance**: <500ms technical log search response times in BackendLogsDropdown
- **Historical Access**: Users can search previous crawl sessions and compare performance
- **Export Performance**: Handle 50,000+ technical log export without UI freezing
- **User Experience**: Clean status updates (top) + power-user technical access (bottom)

---

### **US-066: Enhanced Backend Logs Interface with OpenSearch Integration** 📱
**Title**: Upgrade BackendLogsDropdown with OpenSearch Backend While Preserving Clean Agent Status Display
**Priority**: HIGH
**Epic**: EPIC-06: Centralized Logging & Observability

**User Story**:
As a demo factory operator I want the Backend Logs dropdown to show comprehensive technical logs from OpenSearch (current + historical sessions) while keeping the Agent Output card clean and real-time So that I have both user-friendly status updates and power-user technical access when needed

**Acceptance Criteria**:

**Dual Log Architecture** ✅:
- ✅ **AgentOutputCard (Top)**: Keep current WebSocket implementation unchanged
  - Real-time status: "Crawl started", "Analyzing sitemap", "Crawling page 15/50"
  - Clean, user-friendly progress narrative
  - <100ms latency for status updates
  - No technical noise or overwhelming details
- ✅ **BackendLogsDropdown (Bottom)**: Upgrade to OpenSearch backend
  - All technical logs from Logstash processing
  - Historical logs from previous crawl sessions
  - Advanced search and filtering capabilities

**Enhanced BackendLogsDropdown Features** ✅:
- ✅ **OpenSearch Integration**: Query logs from all OpenSearch indices (ai-decisions, errors, performance, system-logs)
- ✅ **Real-time + Historical**: Current session logs + access to previous sessions
- ✅ **Advanced Filtering**:
  - Time range picker (last hour, today, last week, custom range)
  - Log level filtering (INFO, WARNING, ERROR, DEBUG)
  - Component filtering (ai_content_classifier, smart_mirror_agent, crawler, etc.)
  - Log category filtering (ai_decision, error, performance, crawl_session)
- ✅ **Search Capabilities**: Full-text search within log messages with highlighting
- ✅ **Correlation ID Linking**: Click correlation ID to see all related logs from same crawl session
- ✅ **AI Decision Insights**: Expandable AI classification details with confidence scores and reasoning
- ✅ **Performance Tracking**: Show response times, error counts, cost analytics
- ✅ **Export Functionality**: Download filtered logs as JSON/CSV for debugging

**UI/UX Enhancements** ✅:
- ✅ **Collapsible Design**: Maintain current dropdown behavior, expand for power-user features
- ✅ **Tabbed Interface**: Separate tabs for Current Session, Historical Logs, AI Decisions, Errors
- ✅ **Color Coding**: Enhanced color coding for different log sources and levels
- ✅ **Pagination**: Handle large result sets with lazy loading
- ✅ **Loading States**: Show loading indicators during OpenSearch queries
- ✅ **Error Handling**: Graceful fallback when OpenSearch unavailable

**Technical Implementation** ✅:
- ✅ **New API Endpoints**:
  - `GET /api/logs/search` - OpenSearch query with filters
  - `GET /api/logs/session/{run_id}` - All logs for specific crawl session
  - `GET /api/logs/export` - Download filtered logs
- ✅ **Frontend Components**:
  - Upgrade existing `BackendLogsDropdown.tsx` with OpenSearch integration
  - Add `LogFilterPanel.tsx` for advanced filtering controls
  - Add `LogExportButton.tsx` for download functionality
- ✅ **State Management**: Handle real-time logs + historical query results
- ✅ **Performance**: Efficient OpenSearch queries with proper indexing

**Integration Points** ✅:
- ✅ **Preserve Current UX**: AgentOutputCard remains unchanged for clean user experience
- ✅ **WebSocket Compatibility**: BackendLogsDropdown shows current session real-time logs + historical access
- ✅ **OpenSearch Backend**: All historical and searchable functionality powered by Logstash indices
- ✅ **Correlation Tracking**: Link logs across services using correlation IDs

**Success Metrics**:
- **User Experience**: Clean status display (top) + comprehensive technical access (bottom)
- **Search Performance**: <500ms response time for historical log queries
- **Real-time Performance**: Current session logs still update in <100ms
- **Export Performance**: Handle 10,000+ log entries export without UI freezing
- **Historical Access**: Users can search and compare previous crawl sessions
- **Power User Features**: Advanced filtering reduces time to find specific issues by 80%

---

## Implementation Priority 🎯

### **🚀 CURRENT PHASE: Centralized Logging Infrastructure** (Week 1-2)
1. **US-065**: Logstash-OpenSearch Centralized Logging System ⭐ **IN PROGRESS**
2. **US-066**: Enhanced Backend Logs Interface with OpenSearch Integration ⭐ **IN PROGRESS**
3. **US-064**: Advanced Log Management & Search (Enhanced with OpenSearch)

### **Phase 2: Essential Transparency** (Week 3-4)
4. **US-063**: Real-time Cost & Quality Dashboard
5. **US-060**: AI Classification Prompt Editor
6. **US-061**: AI Model & Company Selection

### **Phase 3: Advanced Controls** (Week 5-6)
7. **US-062**: Crawl History & Cache Management
8. Frontend log analytics dashboard integration

### **Phase 4: Polish & Enhancement** (Week 7)
9. UI/UX refinements
10. Performance optimization
11. Integration testing

---

## 🎯 **IMMEDIATE NEXT STEPS**

### **Week 1: Backend Logging Infrastructure**
1. ✅ Set up Docker Logstash container
2. ✅ Configure Logstash pipeline for Python logs
3. ✅ Enhance WebSocketLogHandler for dual-stream (WebSocket + Logstash)
4. ✅ Add structured logging format with correlation IDs
5. ✅ Create OpenSearch index templates for log categories

### **Week 2: Frontend Integration**
1. ✅ Keep AgentOutputCard unchanged (clean UX)
2. ✅ Upgrade BackendLogsDropdown with OpenSearch backend
3. ✅ Add log search, filtering, and export capabilities
4. ✅ Implement real-time + historical log access
5. ✅ Test end-to-end logging flow

---

## Technical Architecture Notes 🔧

### **New API Endpoints Required**:
- `/api/prompts/templates` - Get/set classification prompts
- `/api/models/available` - List available AI models with status
- `/api/crawls/history` - Crawl history with pagination
- `/api/cache/status/{domain}` - Cache information and management
- `/api/metrics/realtime` - Enhanced WebSocket metrics streaming
- `/api/logs/search` - OpenSearch-powered log search with filtering
- `/api/logs/export` - Download filtered logs as JSON/CSV
- `/api/logs/metrics` - Aggregated log analytics and statistics
- `/api/logs/stream` - Real-time log streaming from OpenSearch

### **Database Schema Extensions**:
- **CrawlSession** table: Store historical crawl data
- **PromptTemplates** table: Custom prompt storage
- **CacheMetadata** table: Enhanced cache tracking
- **ModelPerformance** table: Model comparison metrics

### **Security Considerations**:
- Secure API key storage and validation
- Rate limiting on prompt updates and model changes
- Audit logging for configuration changes
- User permission levels for advanced features

---

## Success Metrics 📈

### **User Experience Goals**:
- **Transparency**: Users understand AI decisions and costs
- **Control**: Users can optimize configurations for their needs
- **Efficiency**: Faster identification of issues and optimization opportunities
- **Cost Management**: Clear visibility into API spend with budget controls

### **System Performance Goals**:
- **Real-time Updates**: < 100ms latency for metric updates
- **Export Performance**: Handle 10,000+ log entries without UI freeze
- **Cache Management**: Efficient cache operations with minimal impact
- **Model Switching**: < 2 second model change response time

This comprehensive analysis reveals significant opportunities to enhance user experience by surfacing the rich backend capabilities through improved frontend interfaces.