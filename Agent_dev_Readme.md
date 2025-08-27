# AI Agent Development - Mirror Creation System

## 1-2 Week Implementation Plan

**Goal**: Single Adaptive Agent that automatically creates 90% fidelity website mirrors

## Architecture Overview

### SmartMirrorAgent
Single point of entry that handles the entire pipeline from URL input to mirror creation with learning capabilities.

```python
class SmartMirrorAgent:
    def __init__(self):
        self.site_memory = SitePatternDatabase()
        self.quality_monitor = QualityScorer()
        
    async def create_mirror(self, target_url: str) -> MirrorResult:
        """URL → 90% fidelity mirror in one call"""
```

## Week 1: Adaptive Intelligence MVP

**Priority**: Real-time failure diagnosis and strategy adaptation - the core intelligence that makes this actually smart.

### Day 1-2: Failure Diagnosis System
```python
class FailureDiagnostic:
    def diagnose_failure(self, result: CrawlResult, strategy: Strategy) -> Diagnosis:
        """Analyze WHY the crawl was poor quality"""
        
        issues = []
        
        # Content extraction issues
        if len(result.markdown) < 500:
            if "Loading..." in result.raw_html or "spinner" in result.raw_html:
                issues.append("js_timing_insufficient")
            elif result.load_time < 2.0:
                issues.append("page_not_fully_loaded")
            elif "Please enable JavaScript" in result.raw_html:
                issues.append("js_execution_failed")
        
        # Asset loading issues  
        broken_assets = self._count_broken_assets(result)
        if broken_assets > 10:
            if strategy.headless and "blocked" in result.errors:
                issues.append("headless_detected_blocked")
            elif result.network_errors > 5:
                issues.append("network_timeout_assets")
        
        # Bot detection issues
        if "403" in result.errors or "bot" in str(result.errors).lower():
            issues.append("bot_detection_active")
        
        # Navigation/crawling issues
        if self._count_crawled_pages(result) < self._expected_minimum(result):
            if result.internal_links > 50 but len(result.pages) < 10:
                issues.append("crawl_depth_blocked")
        
        return Diagnosis(
            primary_issue=issues[0] if issues else "unknown",
            all_issues=issues,
            suggested_fix=self._get_fix_description(issues[0] if issues else "unknown")
        )
```

### Day 3-4: Strategy Adaptation Logic
```python
class AdaptiveCrawlAgent:
    async def create_mirror_with_adaptation(self, url: str) -> MirrorResult:
        """Real-time adaptation: diagnose → adapt → retry"""
        
        attempts = []
        current_strategy = self._get_initial_strategy(url)
        
        for attempt in range(3):  # Max 3 adaptive attempts
            
            # Try current strategy
            result = await self._crawl_with_monitoring(url, current_strategy)
            quality = self.quality_scorer.calculate_score(result)
            attempts.append((current_strategy, result, quality))
            
            if quality >= 0.9:
                break  # Success!
            
            # Diagnose what went wrong
            diagnosis = self.diagnostic.diagnose_failure(result, current_strategy)
            
            # Adapt strategy based on diagnosis
            current_strategy = self._adapt_strategy(current_strategy, diagnosis)
            print(f"Attempt {attempt+1} quality: {quality:.2f} - {diagnosis.primary_issue}")
            print(f"Adapting: {diagnosis.suggested_fix}")
        
        # Build mirror from best attempt
        best_result = max(attempts, key=lambda x: x[2])  # Highest quality
        mirror = await self._build_static_mirror(best_result[1])
        
        return MirrorResult(
            mirror_path=mirror.path,
            quality_score=best_result[2],
            strategy_used=best_result[0].name,
            pages_crawled=len(best_result[1].pages),
            adaptation_applied=len(attempts) > 1
        )

    def _adapt_strategy(self, current: Strategy, diagnosis: Diagnosis) -> Strategy:
        """Intelligently modify strategy based on failure analysis"""
        
        new_strategy = current.copy()
        
        if diagnosis.primary_issue == "js_timing_insufficient":
            new_strategy.wait_for *= 2
            new_strategy.js_code = "await new Promise(r => setTimeout(r, 5000));"
            
        elif diagnosis.primary_issue == "bot_detection_active":
            new_strategy.user_agent = random.choice(REALISTIC_USER_AGENTS)
            new_strategy.headless = False  # Use visible browser
            new_strategy.request_delay = random.uniform(1.5, 3.0)
            
        elif diagnosis.primary_issue == "headless_detected_blocked":
            new_strategy.headless = False
            new_strategy.browser_type = "chromium"
            
        elif diagnosis.primary_issue == "network_timeout_assets":
            new_strategy.timeout *= 1.5
            new_strategy.request_delay += 1.0
        
        return new_strategy
```

### Day 5-7: Integration & Quality Monitoring
```python
class QualityScorer:
    def calculate_score(self, crawl_result: CrawlResult) -> float:
        """Multi-dimensional quality assessment"""
        
        # Content completeness (35%)
        content_score = self._score_content_completeness(crawl_result)
        
        # Asset coverage (25%) 
        asset_score = self._score_asset_coverage(crawl_result)
        
        # Navigation integrity (20%)
        nav_score = self._score_navigation_integrity(crawl_result)
        
        # Visual fidelity (20%)
        visual_score = self._score_visual_fidelity(crawl_result)
        
        return (content_score * 0.35 + asset_score * 0.25 + 
                nav_score * 0.20 + visual_score * 0.20)

    async def _crawl_with_monitoring(self, url: str, strategy: Strategy) -> CrawlResult:
        """Monitor crawl quality in real-time"""
        
        async with AsyncWebCrawler(**strategy.to_dict()) as crawler:
            result = await crawler.arun(url)
            
            # Quick quality check for immediate adaptation
            if self._detect_common_failures(result):
                # Try immediate fixes during this crawl session
                await self._apply_immediate_fixes(crawler, result)
                result = await crawler.arun(url)  # Re-crawl
            
            return result
```

## Week 2: Learning System

### Day 8-10: Pattern Database
```python
class SitePatternDatabase:
    """Simple JSON-based learning storage"""
    
    def __init__(self):
        self.db_path = Path("agent_memory/site_patterns.json")
        self.patterns = self._load_patterns()
    
    async def find_similar(self, url: str) -> List[SitePattern]:
        """Find similar sites from past successful crawls"""
        
        domain = extract_domain(url)
        
        # Exact domain match first
        exact_matches = [p for p in self.patterns if p.domain == domain]
        if exact_matches:
            return sorted(exact_matches, key=lambda x: x.success_rate, reverse=True)
        
        # Framework/technology similarity
        site_info = await self._quick_recon(url)
        similar = []
        
        for pattern in self.patterns:
            similarity_score = self._calculate_similarity(site_info, pattern)
            if similarity_score > 0.7:
                similar.append((pattern, similarity_score))
        
        return [p[0] for p in sorted(similar, key=lambda x: x[1], reverse=True)]
    
    async def store_success_pattern(self, url: str, strategy: Strategy, quality: float):
        """Learn from successful crawl"""
        
        pattern = SitePattern(
            domain=extract_domain(url),
            url_sample=url,
            frameworks=strategy.detected_frameworks,
            successful_strategy=strategy.to_dict(),
            success_rate=quality,
            crawl_count=1,
            last_updated=datetime.now()
        )
        
        # Update existing or add new
        existing = next((p for p in self.patterns if p.domain == pattern.domain), None)
        if existing:
            existing.update_success_rate(quality)
            existing.crawl_count += 1
        else:
            self.patterns.append(pattern)
        
        self._save_patterns()

@dataclass 
class SitePattern:
    domain: str
    url_sample: str
    frameworks: List[str]
    successful_strategy: dict
    success_rate: float
    crawl_count: int
    last_updated: datetime
    
    def update_success_rate(self, new_score: float):
        """Running average of success rates"""
        total = self.success_rate * (self.crawl_count - 1) + new_score
        self.success_rate = total / self.crawl_count
```

### Day 11-14: Integration & Testing

**Enhanced Main Flow:**
```python
class SmartMirrorAgent:
    async def create_mirror(self, target_url: str) -> MirrorResult:
        
        # 1. Check memory for similar sites
        similar_sites = await self.site_memory.find_similar(target_url)
        
        if similar_sites:
            # Use proven strategy from similar site
            strategy = Strategy.from_dict(similar_sites[0].successful_strategy)
            print(f"Using proven strategy from similar site: {similar_sites[0].domain}")
        else:
            # Reconnaissance for new site type
            site_info = await self._quick_recon(target_url)
            strategy = self._select_strategy(site_info)
            print(f"New site type, using strategy: {strategy.name}")
        
        # 2. Crawl with quality monitoring
        result = await self._crawl_with_strategy(target_url, strategy)
        quality = self.quality_scorer.calculate_score(result)
        
        # 3. Retry if quality insufficient
        if quality < 0.7:
            fallback = self._get_fallback_strategy(strategy, quality)
            result = await self._crawl_with_strategy(target_url, fallback)
            quality = self.quality_scorer.calculate_score(result)
            strategy = fallback
        
        # 4. Build mirror
        mirror = await self._build_static_mirror(result)
        
        # 5. Learn from this crawl
        await self.site_memory.store_success_pattern(target_url, strategy, quality)
        
        return MirrorResult(
            mirror_path=mirror.path,
            quality_score=quality,
            strategy_used=strategy.name,
            pages_crawled=len(result.pages),
            learning_applied=bool(similar_sites)
        )
```

## Implementation Shortcuts for Speed

### Week 1 MVP Focus
- **Rule-based strategy selection** (faster than LLM integration)
- **Simple quality metrics** (page count, content length, asset success rate)
- **Basic retry logic** (one fallback attempt)
- **Enhance existing crawlers** instead of building from scratch

### Week 2 Learning Focus  
- **JSON file storage** (faster than database setup)
- **Domain-based similarity** (simpler than content analysis)
- **Success rate tracking** (basic learning metric)

### Future Enhancements (Post-MVP)
- Real-time strategy adaptation during crawling
- LLM integration for complex strategy selection
- Visual quality assessment via screenshots
- Specialist tool integration (ecommerce, SPA handlers)

## Success Metrics

### Week 1 Targets
- **Agent responds to URL input** with working mirror
- **Basic quality scoring** operational
- **Retry logic** improves success rate
- **80% success rate** across test sites

### Week 2 Targets
- **Learning system** stores and reuses successful patterns
- **Similar site detection** works accurately
- **85% success rate** with learning improvements
- **Performance**: <30 min total time for most sites

### Testing Strategy
**Test Site Types:**
- Static sites (corporate, portfolio)
- WordPress blogs/news sites
- E-commerce (Shopify, WooCommerce)  
- Modern JS (React/Vue SPAs)
- Complex sites (banking, enterprise)

**Success Criteria:**
- Visual fidelity assessment via manual review
- Content completeness via search indexing quality
- Asset loading success via broken link checking
- Navigation integrity via internal link verification

This aggressive timeline focuses on **working functionality first**, **learning second**, **optimization third**.