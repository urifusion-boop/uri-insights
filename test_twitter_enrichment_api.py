#!/usr/bin/env python3
"""
Test script for Twitter Enrichment API
Tests the Bright Data integration for Twitter profile enrichment
"""

import asyncio
import sys
sys.path.append('/Users/apple/Desktop/URI/uri-insights')

from app.services.TwitterEnrichmentService import TwitterEnrichmentService


async def test_twitter_enrichment():
    """Test Twitter profile enrichment"""

    print("\n" + "="*60)
    print("🐦 TWITTER ENRICHMENT API TEST")
    print("="*60)

    # Test cases
    test_cases = [
        {"input": "https://x.com/elonmusk", "name": "Elon Musk"},
        {"input": "@BillGates", "name": "Bill Gates"},
        {"input": "cnn", "name": "CNN"},
    ]

    twitter_service = TwitterEnrichmentService()

    for test in test_cases:
        print(f"\n{'─'*60}")
        print(f"Testing: {test['input']} (Expected: {test['name']})")
        print(f"{'─'*60}")

        # Test handle extraction
        handle = twitter_service.extract_twitter_handle(test['input'])
        url = twitter_service.build_twitter_url(test['input'])

        print(f"  Extracted handle: @{handle}")
        print(f"  Built URL: {url}")

        # Enrich profile
        print(f"  🔄 Enriching profile...")
        profile = await twitter_service.enrich_profile(
            twitter_url_or_handle=test['input'],
            max_posts=5
        )

        if profile:
            print(f"  ✅ SUCCESS!")
            print(f"  📊 Profile Data:")
            print(f"     Name: {profile.get('profile_name')}")
            print(f"     Handle: @{profile.get('id')}")
            print(f"     ID: {profile.get('x_id')}")
            print(f"     Followers: {profile.get('followers', 0):,}")
            print(f"     Following: {profile.get('following', 0):,}")
            print(f"     Verified: {'✓' if profile.get('is_verified') else '✗'}")
            print(f"     Posts Count: {profile.get('posts_count', 0):,}")
            bio = profile.get('biography') or ''
            print(f"     Bio: {bio[:60]}..." if bio else "     Bio: (none)")

            posts = profile.get('posts', [])
            print(f"     Recent Posts: {len(posts)}")

            if posts:
                print(f"\n  📝 Latest Post:")
                latest = posts[0]
                print(f"     Date: {latest.get('date_posted')}")
                print(f"     Text: {latest.get('description', '')[:80]}...")
                print(f"     Likes: {latest.get('likes', 0):,}")
                print(f"     Retweets: {latest.get('reposts', 0):,}")
                print(f"     Replies: {latest.get('replies', 0):,}")

            # Test transformation
            print(f"\n  🔄 Testing transformation to FocusContact format...")
            contact_data = twitter_service.transform_to_focus_contact_data(profile)

            print(f"  ✅ Transformed Data:")
            print(f"     Name: {contact_data.get('name')}")
            print(f"     Twitter Handle: @{contact_data.get('twitter_handle')}")
            print(f"     Twitter ID: {contact_data.get('twitter_id')}")
            print(f"     Profile Photo: {contact_data.get('profile_photo')[:50]}...")
            print(f"     Enrichment Status: {contact_data.get('enrichment_status')}")

            twitter_data = contact_data.get('twitter_data', {})
            snapshot = twitter_data.get('enrichment_snapshot', {})
            print(f"     Last Post ID: {snapshot.get('last_post_id')}")
            print(f"     Stored Posts: {len(snapshot.get('posts', []))}")

        else:
            print(f"  ❌ FAILED - Could not enrich profile")

    print(f"\n{'='*60}")
    print("✅ TWITTER ENRICHMENT TEST COMPLETED")
    print(f"{'='*60}\n")


async def test_activity_detection():
    """Test new activity detection"""

    print("\n" + "="*60)
    print("🔍 TWITTER ACTIVITY DETECTION TEST")
    print("="*60)

    twitter_service = TwitterEnrichmentService()

    # Get fresh profile
    print("\n  🔄 Fetching fresh profile for @elonmusk...")
    profile = await twitter_service.enrich_profile("elonmusk", max_posts=20)

    if not profile:
        print("  ❌ Failed to fetch profile")
        return

    posts = profile.get('posts', [])
    if len(posts) < 3:
        print("  ❌ Not enough posts for testing")
        return

    print(f"  ✅ Got {len(posts)} posts")

    # Simulate scenarios
    print(f"\n  📊 Testing Activity Detection Scenarios:")

    # Scenario 1: No last known post (first scan)
    print(f"\n  1️⃣  First Scan (no last_known_post_id):")
    activity1 = twitter_service.detect_new_activity(profile, None)
    print(f"     Has New Activity: {activity1['has_new_activity']}")
    print(f"     New Posts Count: {activity1['new_posts_count']}")

    # Scenario 2: No new activity (last post is the latest)
    print(f"\n  2️⃣  No New Activity (last_post_id = latest):")
    latest_post_id = posts[0]['post_id']
    activity2 = twitter_service.detect_new_activity(profile, latest_post_id)
    print(f"     Has New Activity: {activity2['has_new_activity']}")
    print(f"     New Posts Count: {activity2['new_posts_count']}")

    # Scenario 3: New activity (simulate 3 new posts)
    print(f"\n  3️⃣  New Activity (3 new posts since last scan):")
    old_post_id = posts[3]['post_id']  # 4th post as "last known"
    activity3 = twitter_service.detect_new_activity(profile, old_post_id)
    print(f"     Has New Activity: {activity3['has_new_activity']}")
    print(f"     New Posts Count: {activity3['new_posts_count']}")
    if activity3['latest_post']:
        print(f"     Latest Post: {activity3['latest_post']['description'][:60]}...")

    print(f"\n{'='*60}")
    print("✅ ACTIVITY DETECTION TEST COMPLETED")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    print("\n🚀 Starting Twitter Enrichment Tests...\n")

    # Run enrichment test
    asyncio.run(test_twitter_enrichment())

    # Run activity detection test
    asyncio.run(test_activity_detection())

    print("\n✅ All tests completed!\n")
