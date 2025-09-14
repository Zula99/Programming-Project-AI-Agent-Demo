# Crawler Limits Removal Guide

Here's a guide to revert the temporary limits and restore full crawling:

## Removing Sitemap URL Limits

**File**: `ai-agent-demo-factory-backend/Utility/link_extractor.py`

**Current**: Lines ~139-145 have temporary 10 URL limits:
```python
# Temporary test limit of 10 URLs
if max_urls and len(all_urls) + len(urls) > max_urls:
    remaining_quota = max_urls - len(all_urls)
    urls = urls[:remaining_quota]
```

**To Remove**: Delete the URL limiting logic or set `max_urls=None` when calling `extract_sitemap_urls()`:

```python
# Change this:
all_urls = extract_sitemap_urls(domain, max_urls=10)

# To this:
all_urls = extract_sitemap_urls(domain)  # No limits
```

## Removing Crawl Page Limits

**File**: `ai-agent-demo-factory-backend/crawl4ai-agent/hybrid_crawler.py`

**Current**: Line ~293 has temporary 10-page limit:
```python
max_pages=10,  # Temporary test limit
```

**To Remove**: Change to your desired limit or default:
```python
max_pages=100,  # Or whatever limit you want
```

## Removing Sitemap Processing Limits

**File**: `ai-agent-demo-factory-backend/crawl4ai-agent/hybrid_crawler.py` 

**Current**: The sitemap analysis had a limit removed, but if you see any `[:10]` slicing:
```python
for url in analysis.sitemap_urls[:10]:  # Remove this limit
```

**To Remove**: Change to:
```python
for url in analysis.sitemap_urls:  # Process all URLs
```

## Quick Search & Replace

Use these commands to find and remove limits:

```bash
# Find all temporary limits
grep -r "Temporary.*limit" .
grep -r "max_urls.*10" .
grep -r "max_pages.*10" .
grep -r "\[:10\]" .

# Look for test-related comments
grep -r "TESTING ONLY" .
grep -r "test limit" .
```

## Full Production Settings

**For sitemap extraction**:
```python
all_urls = extract_sitemap_urls(domain)  # No URL limits
```

**For crawling**:
```python
max_pages=100,  # Standard limit, or higher for production
```

**Remove any slicing**:
```python
# Change [:10] to no slicing
for url in analysis.sitemap_urls:  # Process all
```

This will restore full crawling capacity for production runs.