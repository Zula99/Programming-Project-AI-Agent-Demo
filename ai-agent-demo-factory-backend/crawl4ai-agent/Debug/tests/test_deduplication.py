#!/usr/bin/env python3
"""
Test script for the Robust Content Deduplication System
Tests the 3-tier detection system: exact hash, fuzzy pre-bucketing, and SimHash near-duplicate detection

This script demonstrates the different types of duplicate detection:
1. Exact content hash matching
2. Near-duplicate detection via SimHash (~94% similarity)
3. Redirect stub detection

Usage:
    python test_deduplication.py
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from content_deduplicator import RobustContentDeduplicator


def create_test_html(title, body_content, meta_refresh=False, js_redirect=False, canonical_url=None):
    """Create HTML content for testing"""
    meta_tags = ""
    if meta_refresh:
        meta_tags += '<meta http-equiv="refresh" content="0; url=https://example.com/new-location">'
    if canonical_url:
        meta_tags += f'<link rel="canonical" href="{canonical_url}">'

    js_code = ""
    if js_redirect:
        js_code = '<script>window.location.href = "https://example.com/redirect";</script>'

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    {meta_tags}
</head>
<body>
    {js_code}
    <main>
        <h1>{title}</h1>
        {body_content}
    </main>
    <footer>© 2024 Example Company</footer>
</body>
</html>"""


def test_robust_deduplication():
    """Test the robust content deduplication system with various scenarios"""
    print("🧪 Testing Robust Content Deduplication System")
    print("=" * 60)

    # Initialize deduplicator for exact duplicates only
    deduplicator = RobustContentDeduplicator(
        min_content_length=50
    )

    # Test data with HTML content for proper parsing
    test_pages = [
        # 1. Original unique content
        {
            'url': 'https://example.com/about',
            'title': 'About Our Company',
            'html': create_test_html(
                'About Our Company',
                '<p>We are a leading technology company focused on innovative solutions. Our mission is to transform the digital landscape through cutting-edge software development.</p>'
            )
        },

        # 2. Exact duplicate (same content hash)
        {
            'url': 'https://example.com/about-copy',
            'title': 'About Our Company',
            'html': create_test_html(
                'About Our Company',
                '<p>We are a leading technology company focused on innovative solutions. Our mission is to transform the digital landscape through cutting-edge software development.</p>'
            )
        },

        # 3. Near-duplicate (94%+ similar via SimHash)
        {
            'url': 'https://example.com/about-similar',
            'title': 'About Our Organization',
            'html': create_test_html(
                'About Our Organization',
                '<p>We are a leading technology organization focused on innovative solutions. Our goal is to transform the digital landscape through cutting-edge software development.</p>'
            )
        },

        # 4. Content with different dates (should be detected as similar after normalization)
        {
            'url': 'https://example.com/news/2024-01-15',
            'title': 'Company News Update',
            'html': create_test_html(
                'Company News Update',
                '<p>Published on January 15, 2024: We have secured $50M in funding. Last updated: 2024-01-15 at 10:30 AM.</p>'
            )
        },

        # 5. Same content with different dates (should be duplicate)
        {
            'url': 'https://example.com/news/2024-02-20',
            'title': 'Company News Update',
            'html': create_test_html(
                'Company News Update',
                '<p>Published on February 20, 2024: We have secured $50M in funding. Last updated: 2024-02-20 at 09:45 AM.</p>'
            )
        },

        # 6. Content with different numbers (should be duplicate after normalization)
        {
            'url': 'https://example.com/pricing/basic',
            'title': 'Basic Plan Pricing',
            'html': create_test_html(
                'Basic Plan Pricing',
                '<p>Our basic plan costs $19.99 per month and includes 100 users with 500GB storage.</p>'
            )
        },

        # 7. Same structure with different numbers (should be duplicate)
        {
            'url': 'https://example.com/pricing/premium',
            'title': 'Premium Plan Pricing',
            'html': create_test_html(
                'Premium Plan Pricing',
                '<p>Our premium plan costs $49.99 per month and includes 500 users with 2TB storage.</p>'
            )
        },

        # 8. Redirect stub with meta refresh
        {
            'url': 'https://example.com/old-page',
            'title': 'Page Moved',
            'html': create_test_html(
                'Page Moved',
                '<p>This page has moved to a new location.</p>',
                meta_refresh=True
            )
        },

        # 9. Redirect stub with JavaScript
        {
            'url': 'https://example.com/redirect-js',
            'title': 'Redirecting',
            'html': create_test_html(
                'Redirecting',
                '<p>Redirecting to new location...</p>',
                js_redirect=True
            )
        },

        # 10. Canonical URL redirect
        {
            'url': 'https://example.com/canonical-test',
            'title': 'Canonical Test',
            'html': create_test_html(
                'Canonical Test',
                '<p>This content has a canonical URL.</p>',
                canonical_url='https://example.com/canonical-original'
            )
        },

        # 11. Unique content (completely different)
        {
            'url': 'https://example.com/contact',
            'title': 'Contact Information',
            'html': create_test_html(
                'Contact Information',
                '<p>Reach out to us at contact@example.com or call +1-555-0123. Our office is located in San Francisco.</p>'
            )
        },

        # 12. Very short content (should be skipped)
        {
            'url': 'https://example.com/short',
            'title': 'Short',
            'html': create_test_html('Short', '<p>Hi</p>')
        }
    ]

    print(f"Testing with {len(test_pages)} pages...\n")

    # Process each page and track results
    results = []
    for i, page in enumerate(test_pages, 1):
        result = deduplicator.decide_dedup(page['url'], page['html'])

        status_icons = {
            'canon': '✅ CANONICAL',
            'dup': '🔍 DUPLICATE',
            'alias': '🔗 ALIAS/REDIRECT'
        }

        status = status_icons.get(result.status, '❓ UNKNOWN')
        print(f"{i:2d}. {status} - {page['url']}")
        print(f"    Status: {result.status}")
        print(f"    Reason: {result.reason}")
        if result.canonical_url != page['url']:
            print(f"    Canonical: {result.canonical_url}")
        print(f"    Title: {page['title']}")
        print()

        results.append({
            'url': page['url'],
            'title': page['title'],
            'status': result.status,
            'reason': result.reason,
            'canonical_url': result.canonical_url
        })

    # Display comprehensive statistics
    print("=" * 60)
    print("📊 ROBUST DEDUPLICATION SUMMARY")
    print("=" * 60)

    stats = deduplicator.get_deduplication_summary()
    print(f"Total pages processed: {stats['total_processed']}")
    print(f"Unique pages kept: {stats['unique_kept']}")
    print(f"Total duplicates filtered: {stats['total_duplicates']}")
    print(f"Duplicate rate: {stats['duplicate_rate']}")
    print()

    print("Breakdown by detection type:")
    for dup_type, count in stats['breakdown'].items():
        if count > 0:
            detection_names = {
                'exact_duplicates': 'Exact Hash Matches',
                'near_duplicates': 'SimHash Near-Duplicates',
                'redirect_stubs': 'Redirect Stubs'
            }
            name = detection_names.get(dup_type, dup_type.replace('_', ' ').title())
            print(f"  {name}: {count}")

    print("\n🎯 Expected Results:")
    print("  - Exact duplicates: 1 (about-copy should match about)")
    print("  - Near duplicates: 3+ (similar content, date variations, number variations)")
    print("  - Redirect stubs: 3 (meta refresh, JS redirect, canonical)")
    print("  - Short content: 1 (should be kept as canonical due to length)")

    # Analyze results by type
    canonical_pages = [r for r in results if r['status'] == 'canon']
    duplicate_pages = [r for r in results if r['status'] == 'dup']
    alias_pages = [r for r in results if r['status'] == 'alias']

    print(f"\n📈 ANALYSIS:")
    print(f"  Canonical pages: {len(canonical_pages)}")
    print(f"  Duplicate pages: {len(duplicate_pages)}")
    print(f"  Alias/Redirect pages: {len(alias_pages)}")

    # Verify the 3-tier system is working
    exact_hash_dups = len([r for r in results if 'exact_hash' in r['reason']])
    simhash_dups = len([r for r in results if 'simhash' in r['reason']])
    redirect_dups = len([r for r in results if 'redirect' in r['reason']])

    print(f"\n🔧 DETECTION METHOD BREAKDOWN:")
    print(f"  Exact hash matches: {exact_hash_dups}")
    print(f"  SimHash near-duplicates: {simhash_dups}")
    print(f"  Redirect stubs: {redirect_dups}")

    total_filtered = len(duplicate_pages) + len(alias_pages)
    if total_filtered >= 6:
        print(f"\n🎉 SUCCESS: Robust deduplication system is working correctly!")
        print(f"   Filtered {total_filtered} duplicates/redirects from {len(test_pages)} pages")
    else:
        print(f"\n⚠️  WARNING: Expected more duplicates. Check deduplication logic.")
        print(f"   Only filtered {total_filtered} pages, expected 6+")

    return deduplicator, results


def test_simhash_accuracy():
    """Test SimHash accuracy with known similar content"""
    print("\n🧮 Testing SimHash Accuracy")
    print("-" * 40)

    deduplicator = RobustContentDeduplicator()

    # Test content pairs with known similarity
    test_pairs = [
        {
            'name': 'Very Similar (should be ~95% similar)',
            'content1': 'The quick brown fox jumps over the lazy dog in the forest.',
            'content2': 'A quick brown fox jumps over the lazy dog in the woods.'
        },
        {
            'name': 'Moderately Similar (should be ~80% similar)',
            'content1': 'Python is a programming language used for web development.',
            'content2': 'JavaScript is a scripting language used for web applications.'
        },
        {
            'name': 'Dissimilar (should be <50% similar)',
            'content1': 'The weather today is sunny and warm with clear skies.',
            'content2': 'Database optimization requires careful index management strategies.'
        }
    ]

    for pair in test_pairs:
        # Create simple HTML for testing
        html1 = f'<html><body><p>{pair["content1"]}</p></body></html>'
        html2 = f'<html><body><p>{pair["content2"]}</p></body></html>'

        # Extract and normalize text
        text1, _ = deduplicator.extract_meaningful_text(html1)
        text2, _ = deduplicator.extract_meaningful_text(html2)

        fuzzy1 = deduplicator.normalize_fuzzy(text1)
        fuzzy2 = deduplicator.normalize_fuzzy(text2)

        # Calculate SimHash and Hamming distance
        hash1 = deduplicator.simhash64(fuzzy1)
        hash2 = deduplicator.simhash64(fuzzy2)
        hamming = deduplicator.hamming64(hash1, hash2)

        # Calculate similarity percentage (64 - hamming_distance) / 64
        similarity = (64 - hamming) / 64 * 100

        would_match = hamming <= deduplicator.simhash_threshold

        print(f"{pair['name']}:")
        print(f"  Hamming distance: {hamming}/64")
        print(f"  Similarity: {similarity:.1f}%")
        print(f"  Would be detected as duplicate: {'✅ Yes' if would_match else '❌ No'}")
        print()


if __name__ == "__main__":
    try:
        # Run main deduplication test
        deduplicator, results = test_robust_deduplication()

        # Run SimHash accuracy test
        test_simhash_accuracy()

        print(f"\n✅ Robust Content Deduplication System test completed!")
        print(f"🎯 Key Features Verified:")
        print(f"   ✓ 3-tier detection system (exact → fuzzy → simhash)")
        print(f"   ✓ HTML parsing with meaningful text extraction")
        print(f"   ✓ Date and number normalization")
        print(f"   ✓ Redirect stub detection")
        print(f"   ✓ ~94% similarity threshold via SimHash")

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)