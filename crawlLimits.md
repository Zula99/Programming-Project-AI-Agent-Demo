  1. hybrid_crawler.py - Line 166 & 176:

  # BEFORE:
  max_urls=10,  # Limit to 10 URLs for testing
  # TEMPORARY TEST LIMIT: Only use first 10 sitemap URLs
  analysis.sitemap_urls = urls[:10]
  self.logger.info(f"LIMIT: Using {len(analysis.sitemap_urls)} URLs from {len(urls)} total sitemap URLs (max_urls=10)")

  # AFTER:
  max_urls=None,  # No limit - process full sitemap
  # Use all sitemap URLs
  analysis.sitemap_urls = urls
  self.logger.info(f"SUCCESS: Using all {len(analysis.sitemap_urls)} URLs from sitemap (no limit applied)")

  2. hybrid_crawler.py - Line 268:

  # BEFORE:
  max_pages = min(500, len(analysis.sitemap_urls) * 2)  # Allow for additional discovered URLs

  # AFTER:
  max_pages = len(analysis.sitemap_urls) * 3  # Allow for additional discovered URLs (no 500 limit)

  3. hybrid_crawler.py - Line 279:

  # BEFORE:
  max_pages = 300  # Reasonable limit for progressive discovery with plateau detection

  # AFTER:
  max_pages = 1000  # Higher limit for full testing (was 300)

  4. hybrid_crawler.py - Line 372-373:

  # BEFORE:
  #max_pages=plan.max_pages_recommendation,
  max_pages=2,  # Test with just 2 pages

  # AFTER:
  max_pages=plan.max_pages_recommendation,  # Use full recommendation
  #max_pages=2,  # LIMIT DISABLED FOR FULL TESTINGw