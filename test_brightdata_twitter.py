"""
Test script for BrightDataTwitterService

This script tests:
1. Profile enrichment only (no posts)
2. Profile enrichment with posts
3. Real-time posts scraping (Scan Now)
4. Batch posts scraping (Origami)
5. Field extraction and normalization

Usage:
    python test_brightdata_twitter.py
"""
import asyncio
import sys
import os
from pprint import pprint

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.BrightDataTwitterService import BrightDataTwitterService


async def test_profile_enrichment_only():
    """Test enriching a Twitter profile without posts"""
    print("\n" + "=" * 80)
    print("TEST 1: Profile Enrichment Only (No Posts)")
    print("=" * 80)

    service = BrightDataTwitterService()

    # Test with a public Twitter profile
    test_url = "https://x.com/elonmusk"

    print(f"\nEnriching profile: {test_url}")
    print("Posts: Disabled (max_posts=0)")
    print("-" * 80)

    result = await service.enrich_profile(
        twitter_url=test_url,
        include_posts=False,
        timeout_seconds=90
    )

    if result["success"]:
        profile = result["profile"]
        posts = result["posts"]

        print("✅ SUCCESS")
        print("\nProfile Data:")
        print("-" * 80)
        print(f"Profile Name: {profile.get('profile_name')}")
        print(f"X ID: {profile.get('x_id')}")
        print(f"URL: {profile.get('url')}")
        print(f"Biography: {profile.get('biography')[:100]}..." if len(profile.get('biography', '')) > 100 else f"Biography: {profile.get('biography')}")
        print(f"Verified: {'✅ Yes' if profile.get('is_verified') else '❌ No'}")
        print(f"Profile Image: {profile.get('profile_image_link')[:50]}..." if profile.get('profile_image_link') else "Not found")
        print(f"External Link: {profile.get('external_link')}")
        print(f"Location: {profile.get('location')}")
        print(f"Date Joined: {profile.get('date_joined')}")
        print(f"Followers: {profile.get('followers'):,}")
        print(f"Following: {profile.get('following'):,}")
        print(f"Total Posts: {profile.get('posts_count'):,}")
        print(f"Posts Fetched: {len(posts)} (should be 0)")

        print("\n" + "-" * 80)
        print("Full profile structure:")
        print("-" * 80)
        pprint(profile, depth=2, width=120)
    else:
        print("❌ FAILED")
        print(f"Error: {result.get('error_message')}")

    return result


async def test_profile_with_posts():
    """Test enriching a Twitter profile WITH recent posts"""
    print("\n" + "=" * 80)
    print("TEST 2: Profile Enrichment WITH Posts")
    print("=" * 80)

    service = BrightDataTwitterService()

    # Test with a public Twitter profile
    test_url = "https://x.com/elonmusk"

    print(f"\nEnriching profile: {test_url}")
    print("Posts: Enabled (max_posts=5)")
    print("-" * 80)

    result = await service.enrich_profile(
        twitter_url=test_url,
        include_posts=True,
        max_posts=5,
        timeout_seconds=90
    )

    if result["success"]:
        profile = result["profile"]
        posts = result["posts"]

        print(f"✅ SUCCESS - Profile + {len(posts)} posts fetched")
        print("\nProfile:")
        print(f"  {profile.get('profile_name')} (@{profile.get('x_id')})")
        print(f"  Followers: {profile.get('followers'):,}")

        print(f"\nRecent Posts ({len(posts)}):")
        print("-" * 80)

        for i, post in enumerate(posts, 1):
            print(f"\nPost #{i}:")
            print(f"  Author: {post['name']} (@{post['user_posted']})")
            print(f"  Date: {post['date_posted']}")
            print(f"  Text: {post['text'][:100]}..." if len(post['text']) > 100 else f"  Text: {post['text']}")
            print(f"  URL: {post['url']}")
            print(f"  Engagement: {post['likes']:,} likes, {post['replies']:,} replies, {post['reposts']:,} retweets, {post['views']:,} views")
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


async def test_realtime_posts_scraping():
    """Test real-time posts scraping (for 'Scan Now' button)"""
    print("\n" + "=" * 80)
    print("TEST 3: Real-time Posts Scraping (Scan Now)")
    print("=" * 80)

    service = BrightDataTwitterService()

    test_url = "https://x.com/elonmusk"

    print(f"\nFetching posts from: {test_url}")
    print("Limit: 10 posts")
    print("Mode: Real-time (synchronous)")
    print("-" * 80)

    result = await service.fetch_posts_realtime(
        twitter_url=test_url,
        limit=10,
        timeout_seconds=60
    )

    if result["success"]:
        posts = result["posts"]
        profile = result.get("profile", {})

        print(f"✅ SUCCESS - Fetched {len(posts)} posts")
        print(f"\nProfile: {profile.get('profile_name', 'Unknown')}")
        print(f"Posts retrieved: {len(posts)}")
        print("-" * 80)

        # Show summary of all posts
        for i, post in enumerate(posts, 1):
            print(f"{i}. {post['date_posted'][:10]} - {post['text'][:60]}..." if len(post['text']) > 60 else f"{i}. {post['date_posted'][:10]} - {post['text']}")

        # Calculate engagement stats
        if posts:
            total_likes = sum(p.get('likes', 0) for p in posts)
            total_replies = sum(p.get('replies', 0) for p in posts)
            total_views = sum(p.get('views', 0) for p in posts)
            avg_engagement = (total_likes + total_replies) / len(posts)

            print("\n" + "-" * 80)
            print("Engagement Summary:")
            print(f"  Total likes: {total_likes:,}")
            print(f"  Total replies: {total_replies:,}")
            print(f"  Total views: {total_views:,}")
            print(f"  Avg engagement per post: {avg_engagement:.1f}")
    else:
        print("❌ FAILED")
        print(f"Error: {result.get('error_message')}")

    return result


async def test_batch_posts_scraping():
    """Test batch posts scraping (for Origami weekly scans)"""
    print("\n" + "=" * 80)
    print("TEST 4: Batch Posts Scraping (Origami)")
    print("=" * 80)

    service = BrightDataTwitterService()

    # Test with multiple public profiles
    test_urls = [
        "https://x.com/elonmusk",
        "https://x.com/BillGates",
        "https://x.com/SatyaNadella",
    ]

    print(f"\nFetching posts from {len(test_urls)} profiles in batch:")
    for i, url in enumerate(test_urls, 1):
        print(f"  {i}. {url}")
    print("\nLimit: 5 posts per profile")
    print("-" * 80)

    result = await service.fetch_posts_batch(
        twitter_urls=test_urls,
        limit_per_profile=5,
        timeout_seconds=180
    )

    if result["success"]:
        print(f"\n✅ Batch completed: {result['total_posts']} total posts fetched")
        print("-" * 80)

        for url, posts in result["posts_by_url"].items():
            username = url.split("/")[-1]
            print(f"\n📄 @{username}")
            print(f"   URL: {url}")
            print(f"   Posts found: {len(posts)}")

            if posts:
                # Show first post from each profile
                first_post = posts[0]
                print(f"   Latest tweet: {first_post['date_posted']}")
                print(f"   Content: {first_post['text'][:80]}..." if len(first_post['text']) > 80 else f"   Content: {first_post['text']}")
                print(f"   Engagement: {first_post['likes']:,} likes, {first_post['views']:,} views")

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
    print("TEST 5: Invalid URL Handling")
    print("=" * 80)

    service = BrightDataTwitterService()

    # Test with invalid URLs
    invalid_urls = [
        "https://example.com/not-twitter",
        "https://facebook.com/username",
        "",
        "not-a-url",
    ]

    print("\nTesting invalid URLs:")
    for i, url in enumerate(invalid_urls, 1):
        print(f"\n  Test {i}: {url or '(empty string)'}")
        result = await service.enrich_profile(url)

        if result["success"]:
            print(f"    ⚠️  Unexpectedly succeeded")
        else:
            print(f"    ✅ Correctly failed: {result.get('error_message')}")


async def test_field_extraction():
    """Test that all important fields are extracted correctly"""
    print("\n" + "=" * 80)
    print("TEST 6: Field Extraction Validation")
    print("=" * 80)

    service = BrightDataTwitterService()

    test_url = "https://x.com/elonmusk"

    print(f"\nValidating field extraction for: {test_url}")
    print("-" * 80)

    result = await service.enrich_profile(
        twitter_url=test_url,
        include_posts=True,
        max_posts=3
    )

    if result["success"]:
        profile = result["profile"]
        posts = result["posts"]

        print(f"\n✅ Profile enriched with {len(posts)} posts")

        # Required profile fields
        required_profile_fields = [
            "x_id", "url", "profile_name", "biography", "is_verified",
            "profile_image_link", "followers", "following", "posts_count",
            "scraped_at"
        ]

        print("\n📋 Required Profile Fields:")
        all_present = True
        for field in required_profile_fields:
            value = profile.get(field)
            if value is not None or value == 0 or value == False or value == "":
                status = "✅"
                display_value = value if isinstance(value, (str, int, bool)) else f"<{type(value).__name__}>"
                if isinstance(value, str) and len(value) > 50:
                    display_value = value[:50] + "..."
            else:
                status = "❌ MISSING"
                display_value = "None"
                all_present = False

            print(f"  {status} {field}: {display_value}")

        # Validate profile data types
        print("\n🔍 Profile Data Type Validation:")
        profile_type_checks = {
            "profile_name": str,
            "followers": int,
            "following": int,
            "is_verified": bool,
        }

        for field, expected_type in profile_type_checks.items():
            value = profile.get(field)
            if isinstance(value, expected_type):
                print(f"  ✅ {field}: {expected_type.__name__}")
            else:
                print(f"  ❌ {field}: Expected {expected_type.__name__}, got {type(value).__name__}")

        # Validate post fields if posts exist
        if posts:
            print("\n📋 Required Post Fields (checking first post):")
            required_post_fields = [
                "id", "user_posted", "name", "text", "date_posted", "url",
                "likes", "replies", "reposts", "views", "hashtags", "source"
            ]

            first_post = posts[0]
            for field in required_post_fields:
                value = first_post.get(field)
                if value is not None or value == 0 or value == [] or value == "":
                    status = "✅"
                    display_value = value if isinstance(value, (str, int)) else f"<{type(value).__name__}>"
                    if isinstance(value, str) and len(value) > 50:
                        display_value = value[:50] + "..."
                else:
                    status = "❌ MISSING"
                    display_value = "None"

                print(f"  {status} {field}: {display_value}")

            # Validate post data types
            print("\n🔍 Post Data Type Validation:")
            post_type_checks = {
                "text": str,
                "likes": int,
                "replies": int,
                "views": int,
                "hashtags": list,
            }

            for field, expected_type in post_type_checks.items():
                value = first_post.get(field)
                if isinstance(value, expected_type):
                    print(f"  ✅ {field}: {expected_type.__name__}")
                else:
                    print(f"  ❌ {field}: Expected {expected_type.__name__}, got {type(value).__name__}")

        if all_present:
            print("\n✅ All required profile fields present and valid")
        else:
            print("\n⚠️  Some required profile fields missing")

    else:
        print(f"❌ Test failed: {result.get('error_message')}")


async def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("BRIGHTDATA TWITTER SERVICE - TEST SUITE")
    print("=" * 80)

    try:
        # Run tests sequentially
        await test_profile_enrichment_only()
        await test_profile_with_posts()
        await test_realtime_posts_scraping()
        await test_invalid_url_handling()
        await test_field_extraction()

        # Uncomment to test batch scraping (costs more credits)
        # await test_batch_posts_scraping()

        print("\n" + "=" * 80)
        print("✅ ALL TESTS COMPLETED")
        print("=" * 80)
        print("\nNote: Batch test is commented out to save credits.")
        print("Uncomment it in the code to run full test suite.")

    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test suite failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
