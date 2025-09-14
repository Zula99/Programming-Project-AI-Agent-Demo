[07:08:09] 🔍 Crawl logging started - saving to: output/logs/example.com_crawl_20250914_070809.log
[07:08:09] 📊 INITIALIZATION: Target: https://www.example.com
[07:08:09]  Processing website...
[07:08:09] 📊 CRAWLING: Starting autonomous crawl process
[07:08:09] Starting crawl of https://www.example.com (max 1 pages)
[07:08:09] Output: /app/backend/crawl4ai-agent/output/agent_crawls/example.com
[07:08:09] [1;36m[[0m[36mINIT[0m[1;36m][0m[36m...[0m[36m. → Crawl4AI [0m[1;36m0.7[0m[36m.[0m[1;36m4[0m[36m [0m
[07:08:10] [1;32m[[0m[32mFETCH[0m[1;32m][0m[32m...[0m[32m ↓ [0m[4;32mhttps://www.example.com[0m[32m                                                                              | [0m[32m✓[0m[32m | ⏱: [0m[1;32m0.[0m[32m39s [0m
[07:08:10] [1;32m[[0m[32mSCRAPE[0m[1;32m][0m[32m.. ◆ [0m[4;32mhttps://www.example.com[0m[32m                                                                              | [0m[32m✓[0m[32m | ⏱: [0m[1;32m0.[0m[32m00s [0m
[07:08:10] [1;32m[[0m[32mCOMPLETE[0m[1;32m][0m[32m ● [0m[4;32mhttps://www.example.com[0m[32m                                                                              | [0m[32m✓[0m[32m | ⏱: [0m[1;32m0.[0m[32m39s [0m
[07:08:10]  Using rendered HTML (post-JS) for https://www.example.com
[07:08:12]   Error on https://www.example.com: AI classified as not demo-worthy: AI: WORTHY: false, CONFIDENCE: 0.9, REASONING: The content provided is minimal and primarily serves as a placeholder domain for illustrative purposes. It does not contain any substantial information about services, products, or any other valuable content that users might realistically search for in a business demo context.
[07:08:12] Content deduplication summary: 0.0% duplicates filtered
[07:08:12]   Breakdown: 0 exact, 0 URL pattern, 0 text similarity, 0 template
[07:08:12] Quality plateau summary: 0.0% recent quality, 0.0% overall
[07:08:12] Done. Crawled 0 quality page(s), filtered 0 junk URLs
[07:08:12] URL Quality Ratio: 0.0% (higher is better)
[07:08:12] Output in: /app/backend/crawl4ai-agent/output/agent_crawls/example.com
[07:08:12] Crawl completed: 0/0 successful
[07:08:12] 💰 Cost tracking initialized for example.com
[07:08:12] 📊 Session log: output/cost_logs/cost_session_example_com_20250914_070812.json
[07:08:12] [1;36m[[0m[36mINIT[0m[1;36m][0m[36m...[0m[36m. → Crawl4AI [0m[1;36m0.7[0m[36m.[0m[1;36m4[0m[36m [0m
[07:08:13] [1;32m[[0m[32mFETCH[0m[1;32m][0m[32m...[0m[32m ↓ [0m[4;32mhttps://www.example.com[0m[32m                                                                              | [0m[32m✓[0m[32m | ⏱: [0m[1;32m0.[0m[32m33s [0m
[07:08:13] [1;32m[[0m[32mSCRAPE[0m[1;32m][0m[32m.. ◆ [0m[4;32mhttps://www.example.com[0m[32m                                                                              | [0m[32m✓[0m[32m | ⏱: [0m[1;32m0.[0m[32m00s [0m
[07:08:13] [1;32m[[0m[32mCOMPLETE[0m[1;32m][0m[32m ● [0m[4;32mhttps://www.example.com[0m[32m                                                                              | [0m[32m✓[0m[32m | ⏱: [0m[1;32m0.[0m[32m33s [0m
[07:08:13]  Using rendered HTML (post-JS) for https://www.example.com
[07:08:13]         📋 CACHED ($0.000000) | Total session: $0.0000
[07:08:13]   Error on https://www.example.com: AI classified as not demo-worthy: WORTHY: false, CONFIDENCE: 0.9, REASONING: The content provided is minimal and primarily serves as a placeholder domain for illustrative purposes. It does not contain any substantial information about services, products, or any other valuable content that users might realistically search for in a business demo context.
[07:08:14] Content deduplication summary: 0.0% duplicates filtered
[07:08:14]   Breakdown: 0 exact, 0 URL pattern, 0 text similarity, 0 template
[07:08:14] Quality plateau summary: 0.0% recent quality, 0.0% overall
[07:08:14] Done. Crawled 0 quality page(s), filtered 0 junk URLs
[07:08:14] URL Quality Ratio: 0.0% (higher is better)
[07:08:14] Output in: /app/backend/crawl4ai-agent/output/agent_crawls/example.com/www_example_com
[07:08:14] 
============================================================
[07:08:14] 💰 AI COST TRACKING SUMMARY
[07:08:14] ============================================================
[07:08:14] 📊 Domain: example.com
[07:08:14] 🔗 URLs processed: 1
[07:08:14] 🤖 AI classifications: 0
[07:08:14] 📋 Cached results: 1
[07:08:14] 🔧 Heuristic fallbacks: 0
[07:08:14] 💸 Total cost: $0.0000
[07:08:14] 🎯 Tokens used: 0
[07:08:14] 📈 Avg cost/URL: $0.000000
[07:08:14] ✅ Worthy content: 0.0%
[07:08:14] ⏱️  Session duration: 1.8s
[07:08:14] ============================================================
[07:08:14] 💾 Detailed cost log saved: output/cost_logs/cost_session_example_com_20250914_070812.json
[07:08:14] ⚠️  Failed to update daily summary: 'dict' object has no attribute 'append'
[07:08:14] ✅ Cost tracking completed successfully
[07:08:14] 📊 QUALITY_ASSESSMENT: Analyzing crawl quality
[07:08:14] 📊 RESULTS: Displaying crawl results
QUALITY METRICS:
2025-09-14 07:08:14 - INFO -   success: False
2025-09-14 07:08:14 - INFO -   content_completeness: 0.0
2025-09-14 07:08:14 - INFO -   asset_coverage: 0.0
2025-09-14 07:08:14 - INFO -   navigation_integrity: 0.0
2025-09-14 07:08:14 - INFO -   visual_fidelity: 0.0
2025-09-14 07:08:14 - INFO -   overall_score: 0.0
2025-09-14 07:08:14 - INFO -   site_coverage: 0.0
2025-09-14 07:08:14 - INFO -   output_path: N/A
2025-09-14 07:08:14 - INFO - PHASE: RESULTS - Displaying crawl results
2025-09-14 07:08:14 - INFO - ================================================================================
2025-09-14 07:08:14 - INFO - CRAWL SESSION ENDED
2025-09-14 07:08:14 - INFO - Status: SUCCESS
2025-09-14 07:08:14 - INFO - Duration: 5.05 seconds
2025-09-14 07:08:14 - INFO - End time: 2025-09-14 07:08:14
2025-09-14 07:08:14 - INFO - ================================================================================
