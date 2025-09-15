[09:25:16] 🔍 Crawl logging started - saving to: output/logs/nab.com.au_crawl_20250914_092516.log
[09:25:16] 📊 INITIALIZATION: Target: https://www.nab.com.au
[09:25:16]  Processing website...
[09:25:16] 📊 CRAWLING: Starting autonomous crawl process
[09:25:16] Starting crawl of https://www.nab.com.au (max 1 pages)
[09:25:16] Output: /app/backend/crawl4ai-agent/output/agent_crawls/nab.com.au
[09:25:17] [1;36m[[0m[36mINIT[0m[1;36m][0m[36m...[0m[36m. → Crawl4AI [0m[1;36m0.7[0m[36m.[0m[1;36m4[0m[36m [0m
[09:25:18] [1;32m[[0m[32mFETCH[0m[1;32m][0m[32m...[0m[32m ↓ [0m[4;32mhttps://www.nab.com.au[0m[32m                                                                               | [0m[32m✓[0m[32m | ⏱: [0m[1;32m1.[0m[32m11s [0m
[09:25:18] [1;32m[[0m[32mSCRAPE[0m[1;32m][0m[32m.. ◆ [0m[4;32mhttps://www.nab.com.au[0m[32m                                                                               | [0m[32m✓[0m[32m | ⏱: [0m[1;32m0.[0m[32m20s [0m
[09:25:18] [1;32m[[0m[32mCOMPLETE[0m[1;32m][0m[32m ● [0m[4;32mhttps://www.nab.com.au[0m[32m                                                                               | [0m[32m✓[0m[32m | ⏱: [0m[1;32m1.[0m[32m32s [0m
[09:25:18]  Using rendered HTML (post-JS) for https://www.nab.com.au
[09:25:19]  [1/1] https://www.nab.com.au -> index.md
[09:25:19]   found 259 links, queued 239 worthy ones (queue: 239)
[09:25:19] Content deduplication summary: 0.0% duplicates filtered
[09:25:19] Quality plateau summary: 100.0% recent quality, 100.0% overall
[09:25:19] Done. Crawled 1 quality page(s), filtered 0 junk URLs
[09:25:19] URL Quality Ratio: 100.0% (higher is better)
[09:25:19] Output in: /app/backend/crawl4ai-agent/output/agent_crawls/nab.com.au
[09:25:19] Crawl completed: 1/1 successful
[09:25:19] 💰 Cost tracking initialized for nab.com.au
[09:25:19] 📊 Session log: output/cost_logs/cost_session_nab_com_au_20250914_092519.json
[09:25:19] AI classification enabled for intelligent URL filtering
[09:25:19] Robots.txt intelligence gathered: 1 sitemaps, 0 interesting sections, complexity: medium
[09:25:19] Processing 1 sitemaps with AI enhancement...
[09:25:19]   -> Processing sitemap: https://www.nab.com.au/sitemap.xml
[09:25:20]      ...extracted 2 URLs (LIMITED by max_urls=2)
[09:25:20] Applying AI classification to 2 URLs...
[09:25:20] 💰 Cost tracking initialized for nab.com.au
[09:25:20] 📊 Session log: output/agent_crawls/nab.com.au/temp_sitemap_analysis/cost_logs/cost_session_nab_com_au_20250914_092520.json
[09:25:22]         💰 $0.000125 | Total session: $0.0001
[09:25:22]   [   1/2] WORTHY (0.90) - https://www.nab.com.au...
[09:25:22]         AI: AI: WORTHY: true, CONFIDENCE: 0.9, REASONING: The NAB website provides a comprehensive range of banking services and inf...
[09:25:24]         💰 $0.000119 | Total session: $0.0002
[09:25:24]   [   2/2] WORTHY (0.80) - https://www.nab.com.au/important-information...
[09:25:24]         AI: AI: WORTHY: true, CONFIDENCE: 0.8, REASONING: The page likely contains important terms and conditions relevant to users,...
[09:25:24] URL classification complete. Top 10 URLs by confidence:
[09:25:24]   1. 0.90 - https://www.nab.com.au... (AI: WORTHY: true, CONFIDENCE: 0.9, REASONING: The ...)
[09:25:24]   2. 0.80 - https://www.nab.com.au/important-information... (AI: WORTHY: true, CONFIDENCE: 0.8, REASONING: The ...)
[09:25:24] 
============================================================
[09:25:24] 💰 AI COST TRACKING SUMMARY
[09:25:24] ============================================================
[09:25:24] 📊 Domain: nab.com.au
[09:25:24] 🔗 URLs processed: 2
[09:25:24] 🤖 AI classifications: 2
[09:25:24] 📋 Cached results: 0
[09:25:24] 🔧 Heuristic fallbacks: 0
[09:25:24] 💸 Total cost: $0.0002
[09:25:24] 🎯 Tokens used: 1,081
[09:25:24] 📈 Avg cost/URL: $0.000122
[09:25:24] 💎 Avg cost/AI call: $0.000122
[09:25:24] ✅ Worthy content: 100.0%
[09:25:24] ⏱️  Session duration: 4.6s
[09:25:24] ============================================================
[09:25:24] 💾 Detailed cost log saved: output/agent_crawls/nab.com.au/temp_sitemap_analysis/cost_logs/cost_session_nab_com_au_20250914_092520.json
[09:25:24] 📅 Daily summary updated: $0.0002 total today
[09:25:24] Limited output to top 2 URLs by AI confidence
[09:25:24] 
Sitemap processing complete:
[09:25:24]   - Total URLs discovered: 2
[09:25:24]   - URLs after domain filtering: 2
[09:25:24]   - Final URLs returned: 2
[09:25:24]   - Processing time: 5.05s
[09:25:24] Could not analyze robots.txt for www.nab.com.au: Invalid URL '/robots.txt': No scheme supplied. Perhaps you meant https:///robots.txt?
[09:25:24] AI classification enabled for intelligent URL filtering
[09:25:25] Robots.txt intelligence gathered: 1 sitemaps, 0 interesting sections, complexity: medium
[09:25:25] Processing 1 sitemaps with AI enhancement...
[09:25:25]   -> Processing sitemap: https://www.nab.com.au/sitemap.xml
[09:25:25]      ...extracted 2 URLs (LIMITED by max_urls=2)
[09:25:25] Applying AI classification to 2 URLs...
[09:25:25] 💰 Cost tracking initialized for nab.com.au
[09:25:25] 📊 Session log: output/agent_crawls/nab.com.au/temp_sitemap_analysis/cost_logs/cost_session_nab_com_au_20250914_092525.json
[09:25:25]         📋 CACHED ($0.000000) | Total session: $0.0000
[09:25:25]   [   1/2] WORTHY (0.90) - https://www.nab.com.au...
[09:25:25]         CACHE: WORTHY: true, CONFIDENCE: 0.9, REASONING: The NAB website provides a comprehensive range of banking services and informa...
[09:25:25]         📋 CACHED ($0.000000) | Total session: $0.0000
[09:25:25]   [   2/2] WORTHY (0.80) - https://www.nab.com.au/important-information...
[09:25:25]         CACHE: WORTHY: true, CONFIDENCE: 0.8, REASONING: The page likely contains important terms and conditions relevant to users, whi...
[09:25:25] URL classification complete. Top 10 URLs by confidence:
[09:25:25]   1. 0.90 - https://www.nab.com.au... (WORTHY: true, CONFIDENCE: 0.9, REASONING: The NAB ...)
[09:25:25]   2. 0.80 - https://www.nab.com.au/important-information... (WORTHY: true, CONFIDENCE: 0.8, REASONING: The page...)
[09:25:25] 
============================================================
[09:25:25] 💰 AI COST TRACKING SUMMARY
[09:25:25] ============================================================
[09:25:25] 📊 Domain: nab.com.au
[09:25:25] 🔗 URLs processed: 2
[09:25:25] 🤖 AI classifications: 0
[09:25:25] 📋 Cached results: 2
[09:25:25] 🔧 Heuristic fallbacks: 0
[09:25:25] 💸 Total cost: $0.0000
[09:25:25] 🎯 Tokens used: 0
[09:25:25] 📈 Avg cost/URL: $0.000000
[09:25:25] ✅ Worthy content: 100.0%
[09:25:25] ⏱️  Session duration: 0.4s
[09:25:25] ============================================================
[09:25:25] 💾 Detailed cost log saved: output/agent_crawls/nab.com.au/temp_sitemap_analysis/cost_logs/cost_session_nab_com_au_20250914_092525.json
[09:25:25] 📅 Daily summary updated: $0.0000 total today
[09:25:25] Limited output to top 2 URLs by AI confidence
[09:25:25] 
Sitemap processing complete:
[09:25:25]   - Total URLs discovered: 2
[09:25:25]   - URLs after domain filtering: 2
[09:25:25]   - Final URLs returned: 2
[09:25:25]   - Processing time: 0.88s
[09:25:25] Could not analyze robots.txt for www.nab.com.au: Invalid URL '/robots.txt': No scheme supplied. Perhaps you meant https:///robots.txt?
[09:25:26] [1;36m[[0m[36mINIT[0m[1;36m][0m[36m...[0m[36m. → Crawl4AI [0m[1;36m0.7[0m[36m.[0m[1;36m4[0m[36m [0m
[09:25:28] [1;32m[[0m[32mFETCH[0m[1;32m][0m[32m...[0m[32m ↓ [0m[4;32mhttps://www.nab.com.au[0m[32m                                                                               | [0m[32m✓[0m[32m | ⏱: [0m[1;32m1.[0m[32m20s [0m
[09:25:28] [1;32m[[0m[32mSCRAPE[0m[1;32m][0m[32m.. ◆ [0m[4;32mhttps://www.nab.com.au[0m[32m                                                                               | [0m[32m✓[0m[32m | ⏱: [0m[1;32m0.[0m[32m16s [0m
[09:25:28] [1;32m[[0m[32mCOMPLETE[0m[1;32m][0m[32m ● [0m[4;32mhttps://www.nab.com.au[0m[32m                                                                               | [0m[32m✓[0m[32m | ⏱: [0m[1;32m1.[0m[32m36s [0m
[09:25:28]  Using rendered HTML (post-JS) for https://www.nab.com.au
[09:25:28]         📋 CACHED ($0.000000) | Total session: $0.0000
[09:25:29]  [1/4] https://www.nab.com.au -> index.md
[09:25:29]   found 260 links, queued 240 worthy ones (queue: 240)
[09:25:31] [1;32m[[0m[32mFETCH[0m[1;32m][0m[32m...[0m[32m ↓ [0m[4;32mhttps://www.nab.com.au/about-us/careers[0m[32m                                                              | [0m[32m✓[0m[32m | ⏱: [0m[1;32m1.[0m[32m13s [0m
[09:25:31] [1;32m[[0m[32mSCRAPE[0m[1;32m][0m[32m.. ◆ [0m[4;32mhttps://www.nab.com.au/about-us/careers[0m[32m                                                              | [0m[32m✓[0m[32m | ⏱: [0m[1;32m0.[0m[32m16s [0m
[09:25:31] [1;32m[[0m[32mCOMPLETE[0m[1;32m][0m[32m ● [0m[4;32mhttps://www.nab.com.au/about-us/careers[0m[32m                                                              | [0m[32m✓[0m[32m | ⏱: [0m[1;32m1.[0m[32m30s [0m
[09:25:31]  Using rendered HTML (post-JS) for https://www.nab.com.au/about-us/careers
[09:25:31]         📋 CACHED ($0.000000) | Total session: $0.0000
[09:25:31]  [2/4] https://www.nab.com.au/about-us/careers -> index.md
[09:25:31]   found 240 links, queued 6 worthy ones (queue: 245)
[09:25:34] [1;32m[[0m[32mFETCH[0m[1;32m][0m[32m...[0m[32m ↓ [0m[4;32mhttps://www.nab.com.au/personal/trading-investments/online-investing[0m[32m                                 | [0m[32m✓[0m[32m | ⏱: [0m[1;32m2.[0m[32m01s [0m
[09:25:34] [1;32m[[0m[32mSCRAPE[0m[1;32m][0m[32m.. ◆ [0m[4;32mhttps://www.nab.com.au/personal/trading-investments/online-investing[0m[32m                                 | [0m[32m✓[0m[32m | ⏱: [0m[1;32m0.[0m[32m07s [0m
[09:25:34] [1;32m[[0m[32mCOMPLETE[0m[1;32m][0m[32m ● [0m[4;32mhttps://www.nab.com.au/personal/trading-investments/online-investing[0m[32m                                 | [0m[32m✓[0m[32m | ⏱: [0m[1;32m2.[0m[32m09s [0m
[09:25:34]  Using rendered HTML (post-JS) for https://www.nab.com.au/personal/trading-investments/online-investing
[09:25:34]         📋 CACHED ($0.000000) | Total session: $0.0000
[09:25:34]   Error on https://www.nab.com.au/personal/trading-investments/online-investing: AI classified as not demo-worthy: WORTHY: false, CONFIDENCE: 0.9, REASONING: The content primarily addresses a security alert regarding scam text messages, which is important for customer awareness but does not provide comprehensive banking information or services relevant for a search solution demo. It lacks the depth of content needed for users seeking various banking services and investment products.
[09:25:36] [1;32m[[0m[32mFETCH[0m[1;32m][0m[32m...[0m[32m ↓ [0m[4;32mhttps://www.nab.com.au/about-us/accessibility-inclusion/interpreter-services[0m[32m                         | [0m[32m✓[0m[32m | ⏱: [0m[1;32m1.[0m[32m09s [0m
[09:25:36] [1;32m[[0m[32mSCRAPE[0m[1;32m][0m[32m.. ◆ [0m[4;32mhttps://www.nab.com.au/about-us/accessibility-inclusion/interpreter-services[0m[32m                         | [0m[32m✓[0m[32m | ⏱: [0m[1;32m0.[0m[32m12s [0m
[09:25:36] [1;32m[[0m[32mCOMPLETE[0m[1;32m][0m[32m ● [0m[4;32mhttps://www.nab.com.au/about-us/accessibility-inclusion/interpreter-services[0m[32m                         | [0m[32m✓[0m[32m | ⏱: [0m[1;32m1.[0m[32m21s [0m
[09:25:36]  Using rendered HTML (post-JS) for https://www.nab.com.au/about-us/accessibility-inclusion/interpreter-services
[09:25:36]         📋 CACHED ($0.000000) | Total session: $0.0000
[09:25:37]  [3/4] https://www.nab.com.au/about-us/accessibility-inclusion/interpreter-services -> index.md
[09:25:37]   found 242 links, queued 10 worthy ones (queue: 253)
[09:25:39] [1;32m[[0m[32mFETCH[0m[1;32m][0m[32m...[0m[32m ↓ [0m[4;32mhttps://www.nab.com.au/about-us/accessibility-inclusion/interpreter-services/ita[0m[32m                     | [0m[32m✓[0m[32m | ⏱: [0m[1;32m1.[0m[32m18s [0m
[09:25:39] [1;32m[[0m[32mSCRAPE[0m[1;32m][0m[32m.. ◆ [0m[4;32mhttps://www.nab.com.au/about-us/accessibility-inclusion/interpreter-services/ita[0m[32m                     | [0m[32m✓[0m[32m | ⏱: [0m[1;32m0.[0m[32m14s [0m
[09:25:39] [1;32m[[0m[32mCOMPLETE[0m[1;32m][0m[32m ● [0m[4;32mhttps://www.nab.com.au/about-us/accessibility-inclusion/interpreter-services/ita[0m[32m                     | [0m[32m✓[0m[32m | ⏱: [0m[1;32m1.[0m[32m32s [0m
[09:25:39]  Using rendered HTML (post-JS) for https://www.nab.com.au/about-us/accessibility-inclusion/interpreter-services/ita
[09:25:40]         💰 $0.000141 | Total session: $0.0001
[09:25:41]  [4/4] https://www.nab.com.au/about-us/accessibility-inclusion/interpreter-services/ita -> index.md
[09:25:41]   found 228 links, queued 0 worthy ones (queue: 252)
[09:25:41] Content deduplication summary: 0.0% duplicates filtered
[09:25:41] Quality plateau summary: 100.0% recent quality, 100.0% overall
[09:25:41] Done. Crawled 4 quality page(s), filtered 0 junk URLs
[09:25:41] URL Quality Ratio: 100.0% (higher is better)
[09:25:41] Output in: /app/backend/crawl4ai-agent/output/agent_crawls/nab.com.au/www_nab_com_au
[09:25:41] 
============================================================
[09:25:41] 💰 AI COST TRACKING SUMMARY
[09:25:41] ============================================================
[09:25:41] 📊 Domain: nab.com.au
[09:25:41] 🔗 URLs processed: 5
[09:25:41] 🤖 AI classifications: 1
[09:25:41] 📋 Cached results: 4
[09:25:41] 🔧 Heuristic fallbacks: 0
[09:25:41] 💸 Total cost: $0.0001
[09:25:41] 🎯 Tokens used: 697
[09:25:41] 📈 Avg cost/URL: $0.000028
[09:25:41] 💎 Avg cost/AI call: $0.000141
[09:25:41] ✅ Worthy content: 80.0%
[09:25:41] ⏱️  Session duration: 21.9s
[09:25:41] ============================================================
[09:25:41] 💾 Detailed cost log saved: output/cost_logs/cost_session_nab_com_au_20250914_092519.json
[09:25:41] ⚠️  Failed to update daily summary: 'dict' object has no attribute 'append'
[09:25:41] ✅ Cost tracking completed successfully
[09:25:41] 📊 QUALITY_ASSESSMENT: Analyzing crawl quality
[09:25:41] 📊 RESULTS: Displaying crawl results
QUALITY METRICS:
2025-09-14 09:25:41 - INFO -   success: False
2025-09-14 09:25:41 - INFO -   content_completeness: 0.0
2025-09-14 09:25:41 - INFO -   asset_coverage: 0.0
2025-09-14 09:25:41 - INFO -   navigation_integrity: 0.0
2025-09-14 09:25:41 - INFO -   visual_fidelity: 0.0
2025-09-14 09:25:41 - INFO -   overall_score: 0.0
2025-09-14 09:25:41 - INFO -   site_coverage: 0.0
2025-09-14 09:25:41 - INFO -   output_path: N/A
2025-09-14 09:25:41 - INFO - PHASE: RESULTS - Displaying crawl results
2025-09-14 09:25:41 - INFO - ================================================================================
2025-09-14 09:25:41 - INFO - CRAWL SESSION ENDED
2025-09-14 09:25:41 - INFO - Status: SUCCESS
2025-09-14 09:25:41 - INFO - Duration: 24.75 seconds
2025-09-14 09:25:41 - INFO - End time: 2025-09-14 09:25:41
2025-09-14 09:25:41 - INFO - ================================================================================
