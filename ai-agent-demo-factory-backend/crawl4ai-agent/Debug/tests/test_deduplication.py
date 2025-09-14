#!/usr/bin/env python3
"""
Test script for the Content Deduplication System (US-045)

This script demonstrates the four types of duplicate detection:
1. Exact content hash matching
2. URL pattern recognition (e.g., /product/123 vs /product/456)
3. Text similarity using cosine similarity
4. Template-based page identification

Usage:
    python test_deduplication.py
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from content_deduplicator import ContentDeduplicator


def test_content_deduplication():
    """Test the content deduplication system with various scenarios"""
    print("🧪 Testing Content Deduplication System (US-045)")
    print("=" * 60)

    # Initialize deduplicator
    deduplicator = ContentDeduplicator(
        similarity_threshold=0.85,
        min_content_length=50
    )

    # Test data with various duplication scenarios
    test_pages = [
        # Original unique content
        {
            'url': 'https://example.com/about',
            'title': 'About Our Company',
            'content': 'We are a leading technology company focused on innovative solutions. Our mission is to transform the digital landscape through cutting-edge software development.'
        },
        # Exact duplicate (same content hash)
        {
            'url': 'https://example.com/about-copy',
            'title': 'About Our Company',
            'content': 'We are a leading technology company focused on innovative solutions. Our mission is to transform the digital landscape through cutting-edge software development.'
        },
        # URL pattern duplicate (/product/123 vs /product/456)
        {
            'url': 'https://example.com/product/123',
            'title': 'Product Alpha',
            'content': 'Product Alpha is our flagship offering with advanced features and excellent performance.'
        },
        {
            'url': 'https://example.com/product/456',
            'title': 'Product Beta',
            'content': 'Product Beta is our premium solution designed for enterprise customers.'
        },
        {
            'url': 'https://example.com/product/789',
            'title': 'Product Gamma',
            'content': 'Product Gamma offers specialized functionality for niche markets.'
        },
        {
            'url': 'https://example.com/product/999',  # This should be detected as URL pattern duplicate
            'title': 'Product Delta',
            'content': 'Product Delta provides innovative features for modern workflows.'
        },
        # Text similarity duplicate (85%+ similar content)
        {
            'url': 'https://example.com/services',
            'title': 'Our Services',
            'content': 'We provide comprehensive technology consulting services to help businesses transform their digital operations and achieve sustainable growth.'
        },
        {
            'url': 'https://example.com/consulting',
            'title': 'Technology Consulting',
            'content': 'We offer comprehensive technology consulting services to help organizations transform their digital operations and achieve sustainable growth.'  # Very similar
        },
        # Template-based duplicate (same structure, different data)
        {
            'url': 'https://example.com/team/john-doe',
            'title': 'John Doe - CEO',
            'content': '''# John Doe - CEO

            ## Experience
            - 10 years in technology
            - Former CTO at TechCorp

            ## Contact
            Email: john@example.com
            Phone: +1-555-0123

            © 2024 Example Company. All rights reserved.
            '''
        },
        {
            'url': 'https://example.com/team/jane-smith',
            'title': 'Jane Smith - CTO',
            'content': '''# Jane Smith - CTO

            ## Experience
            - 8 years in software development
            - Former Lead Engineer at DevCorp

            ## Contact
            Email: jane@example.com
            Phone: +1-555-0124

            © 2024 Example Company. All rights reserved.
            '''
        },
        # More template duplicates to trigger the limit
        {
            'url': 'https://example.com/team/bob-wilson',
            'title': 'Bob Wilson - CFO',
            'content': '''# Bob Wilson - CFO

            ## Experience
            - 12 years in finance
            - Former VP Finance at FinCorp

            ## Contact
            Email: bob@example.com
            Phone: +1-555-0125

            © 2024 Example Company. All rights reserved.
            '''
        },
        {
            'url': 'https://example.com/team/alice-brown',
            'title': 'Alice Brown - CMO',
            'content': '''# Alice Brown - CMO

            ## Experience
            - 9 years in marketing
            - Former Director at MarketCorp

            ## Contact
            Email: alice@example.com
            Phone: +1-555-0126

            © 2024 Example Company. All rights reserved.
            '''
        },
        # Unique content (different structure)
        {
            'url': 'https://example.com/news/latest-update',
            'title': 'Latest Company News',
            'content': 'Breaking news: We have secured $50M in Series B funding to accelerate our growth and expand into new markets.'
        }
    ]

    print(f"Testing with {len(test_pages)} pages...\n")

    # Process each page and track results
    results = []
    for i, page in enumerate(test_pages, 1):
        is_duplicate, reason = deduplicator.is_duplicate(
            url=page['url'],
            content=page['content'],
            title=page['title']
        )

        status = "🔍 DUPLICATE" if is_duplicate else "✅ UNIQUE"
        print(f"{i:2d}. {status} - {page['url']}")
        if is_duplicate:
            print(f"    Reason: {reason}")
        print(f"    Title: {page['title']}")
        print()

        results.append({
            'url': page['url'],
            'title': page['title'],
            'is_duplicate': is_duplicate,
            'reason': reason
        })

    # Display comprehensive statistics
    print("=" * 60)
    print("📊 DEDUPLICATION SUMMARY")
    print("=" * 60)

    stats = deduplicator.get_deduplication_summary()
    print(f"Total pages processed: {stats['total_processed']}")
    print(f"Unique pages kept: {stats['unique_kept']}")
    print(f"Duplicate pages filtered: {stats['total_duplicates']}")
    print(f"Duplicate rate: {stats['duplicate_rate']}")
    print()

    print("Breakdown by type:")
    for dup_type, count in stats['breakdown'].items():
        if count > 0:
            print(f"  {dup_type.replace('_', ' ').title()}: {count}")

    if stats['examples']:
        print("\nExample duplicate URLs by category:")
        for category, urls in stats['examples'].items():
            if urls:
                print(f"  {category.replace('_', ' ').title()}:")
                for url in urls[:3]:  # Show first 3 examples
                    print(f"    - {url}")

    print("\n🎯 Expected Results:")
    print("  - Exact duplicates: 1 (about-copy should match about)")
    print("  - URL pattern duplicates: 1 (4th product page should be filtered)")
    print("  - Text similarity duplicates: 1 (consulting should match services)")
    print("  - Template duplicates: 2+ (team pages should be detected as same template)")

    # Verify expected behavior
    duplicate_count = sum(1 for r in results if r['is_duplicate'])
    print(f"\n✓ Actual duplicates found: {duplicate_count}")

    if duplicate_count >= 4:
        print("🎉 SUCCESS: Content deduplication system is working correctly!")
    else:
        print("⚠️  WARNING: Expected more duplicates. Check deduplication logic.")

    return deduplicator, results


if __name__ == "__main__":
    try:
        deduplicator, results = test_content_deduplication()
        print(f"\n✅ Content Deduplication System (US-045) test completed!")

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)