"""
Test script for BrightDataLinkedInPostsService

This script tests:
1. Single profile posts scraping (real-time)
2. Batch profile posts scraping
3. Date range filtering
4. Field extraction and normalization

Usage:
    python test_brightdata_posts.py
"""
import asyncio
import sys
import os
from pprint import pprint

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.BrightDataLinkedInPostsService import BrightDataLinkedInPostsService


async def test_single_profile_posts():
    """Test fetching posts from a single LinkedIn profile (real-time)"""
    print("\n" + "=" * 80)
    print("TEST 1: Single Profile Posts - Real-time Scan")
    print("=" * 80)

    service = BrightDataLinkedInPostsService()

    # Test with a public LinkedIn profile
    test_url = "https://www.linkedin.com/in/bettywliu/"

    print(f"\nFetching posts from: {test_url}")
    print("Date range: Last 90 days")
    print("Limit: 10 posts")
    print("-" * 80)

    result = await service.fetch_posts_realtime(
        linkedin_url=test_url,
        limit=10,
        days_back=90,
        timeout_seconds=60
    )

    if result["success"]:
        posts = result["posts"]
        print(f"✅ SUCCESS - Fetched {len(posts)} posts")
        print("-" * 80)

        for i, post in enumerate(posts, 1):
            print(f"\nPost #{i}:")
            print(f"  Author: {post['author']}")
            print(f"  Date: {post['created_at']}")
            print(f"  Text: {post['text'][:100]}..." if len(post['text']) > 100 else f"  Text: {post['text']}")
            print(f"  URL: {post['url']}")
            print(f"  Engagement: {post['likes']} likes, {post['comments']} comments, {post['shares']} shares")
            print(f"  Hashtags: {', '.join(post['hashtags']) if post['hashtags'] else 'None'}")

        print("\n" + "-" * 80)
        print("Sample post structure:")
        print("-" * 80)
        if posts:
            pprint(posts[0], depth=2, width=120)
    else:
        print("❌ FAILED")
        print(f"Error: {result.get('error_message')}")

    return result


async def test_batch_profile_posts():
    """Test fetching posts from multiple profiles in batch"""
    print("\n" + "=" * 80)
    print("TEST 2: Batch Profile Posts - Origami Scan")
    print("=" * 80)

    service = BrightDataLinkedInPostsService()

    # Test with multiple public LinkedIn profiles
    test_urls = [
        "https://www.linkedin.com/in/bettywliu/",
        "https://www.linkedin.com/in/williamhgates/",  # Bill Gates (if posts are public)
        "https://www.linkedin.com/in/satyanadella/",   # Satya Nadella (if posts are public)
    ]

    print(f"\nFetching posts from {len(test_urls)} profiles in batch:")
    for i, url in enumerate(test_urls, 1):
        print(f"  {i}. {url}")
    print("\nDate range: Last 7 days (weekly scan)")
    print("Limit: 10 posts per profile")
    print("-" * 80)

    result = await service.fetch_posts_batch(
        linkedin_urls=test_urls,
        limit_per_source=10,
        days_back=7,
        timeout_seconds=180
    )

    if result["success"]:
        print(f"\n✅ Batch completed: {result['total_posts']} total posts fetched")
        print("-" * 80)

        for url, posts in result["posts_by_url"].items():
            print(f"\n📄 {url}")
            print(f"   Posts found: {len(posts)}")

            if posts:
                # Show first post from each profile
                first_post = posts[0]
                print(f"   Latest post: {first_post['created_at']}")
                print(f"   Content: {first_post['text'][:80]}..." if len(first_post['text']) > 80 else f"   Content: {first_post['text']}")
                print(f"   Engagement: {first_post['likes']} likes")

        print("\n" + "-" * 80)
        print(f"Summary:")
        print(f"  Total profiles: {len(test_urls)}")
        print(f"  Total posts: {result['total_posts']}")
        print(f"  Average posts per profile: {result['total_posts'] / len(test_urls):.1f}")
    else:
        print("❌ FAILED")
        print(f"Error: {result.get('error_message')}")

    return result


async def test_invalid_url_handling():
    """Test error handling for invalid URLs"""
    print("\n" + "=" * 80)
    print("TEST 3: Invalid URL Handling")
    print("=" * 80)

    service = BrightDataLinkedInPostsService()

    # Test with invalid URLs
    invalid_urls = [
        "https://example.com/not-linkedin",
        "https://linkedin.com/company/invalid",  # Company URL (should fail - we need profiles)
        "",  # Empty string
        "not-a-url",
    ]

    print("\nTesting invalid URLs:")
    for i, url in enumerate(invalid_urls, 1):
        print(f"\n  Test {i}: {url or '(empty string)'}")
        result = await service.fetch_posts_realtime(url)

        if result["success"]:
            print(f"    ⚠️  Unexpectedly succeeded")
        else:
            print(f"    ✅ Correctly failed: {result.get('error_message')}")


async def test_field_extraction():
    """Test that all important fields are extracted correctly"""
    print("\n" + "=" * 80)
    print("TEST 4: Field Extraction Validation")
    print("=" * 80)

    service = BrightDataLinkedInPostsService()

    # Use a known public profile for testing
    test_url = "https://www.linkedin.com/in/bettywliu/"

    print(f"\nValidating field extraction for: {test_url}")
    print("-" * 80)

    result = await service.fetch_posts_realtime(
        linkedin_url=test_url,
        limit=5,
        days_back=90
    )

    if result["success"] and result["posts"]:
        posts = result["posts"]
        print(f"\n✅ Fetched {len(posts)} posts for validation")

        # Required fields in each post
        required_fields = [
            "text",
            "url",
            "created_at",
            "author",
            "author_url",
            "likes",
            "comments",
            "shares",
            "hashtags",
            "source",
            "scraped_at"
        ]

        # Check first post for all required fields
        first_post = posts[0]
        print("\n📋 Required Fields (checking first post):")

        all_present = True
        for field in required_fields:
            value = first_post.get(field)
            if value is not None or value == 0 or value == [] or value == "":  # Allow empty values
                status = "✅"
                display_value = value if isinstance(value, (str, int)) else f"<{type(value).__name__}>"
                if isinstance(value, str) and len(value) > 50:
                    display_value = value[:50] + "..."
            else:
                status = "❌ MISSING"
                display_value = "None"
                all_present = False

            print(f"  {status} {field}: {display_value}")

        # Validate data types
        print("\n🔍 Data Type Validation:")
        type_checks = {
            "text": str,
            "likes": int,
            "comments": int,
            "shares": int,
            "hashtags": list,
        }

        for field, expected_type in type_checks.items():
            value = first_post.get(field)
            if isinstance(value, expected_type):
                print(f"  ✅ {field}: {expected_type.__name__}")
            else:
                print(f"  ❌ {field}: Expected {expected_type.__name__}, got {type(value).__name__}")

        # Check for buying signals in posts (just validation, not analysis)
        print("\n💬 Content Analysis:")
        print(f"  Total posts: {len(posts)}")
        posts_with_hashtags = sum(1 for p in posts if p.get('hashtags'))
        print(f"  Posts with hashtags: {posts_with_hashtags}")
        avg_engagement = sum(p.get('likes', 0) + p.get('comments', 0) for p in posts) / len(posts)
        print(f"  Average engagement per post: {avg_engagement:.1f}")

        if all_present:
            print("\n✅ All required fields present and valid")
        else:
            print("\n⚠️  Some required fields missing")

    elif result["success"] and not result["posts"]:
        print("⚠️  No posts found (profile may have no recent posts or posts are private)")
    else:
        print(f"❌ Test failed: {result.get('error_message')}")


async def test_date_range_filtering():
    """Test that date range filtering works correctly"""
    print("\n" + "=" * 80)
    print("TEST 5: Date Range Filtering")
    print("=" * 80)

    service = BrightDataLinkedInPostsService()
    test_url = "https://www.linkedin.com/in/bettywliu/"

    # Test different date ranges
    date_ranges = [
        ("Last 7 days", 7),
        ("Last 30 days", 30),
        ("Last 90 days", 90),
    ]

    print(f"\nTesting different date ranges for: {test_url}")
    print("-" * 80)

    for label, days_back in date_ranges:
        print(f"\n📅 {label} ({days_back} days back):")

        result = await service.fetch_posts_realtime(
            linkedin_url=test_url,
            limit=10,
            days_back=days_back
        )

        if result["success"]:
            posts = result["posts"]
            print(f"  ✅ Fetched {len(posts)} posts")

            if posts:
                # Show date range of fetched posts
                dates = [p['created_at'] for p in posts if p.get('created_at')]
                if dates:
                    print(f"  Oldest post: {min(dates)}")
                    print(f"  Newest post: {max(dates)}")
        else:
            print(f"  ❌ Failed: {result.get('error_message')}")

        # Small delay between requests
        await asyncio.sleep(2)


async def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("BRIGHTDATA LINKEDIN POSTS SERVICE - TEST SUITE")
    print("=" * 80)

    try:
        # Run tests sequentially
        await test_single_profile_posts()
        await test_invalid_url_handling()
        await test_field_extraction()

        # Uncomment to test batch and date filtering (costs more credits)
        # await test_batch_profile_posts()
        # await test_date_range_filtering()

        print("\n" + "=" * 80)
        print("✅ ALL TESTS COMPLETED")
        print("=" * 80)
        print("\nNote: Batch and date range tests are commented out to save credits.")
        print("Uncomment them in the code to run full test suite.")

    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test suite failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
