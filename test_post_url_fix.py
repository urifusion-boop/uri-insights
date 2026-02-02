"""
Test script to verify post URL fix is working correctly
Run this to manually test a focus contact scan and verify the post URLs are correct
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from motor.motor_asyncio import AsyncIOMotorClient
from app.services.LazarusMonitoringService import LazarusMonitoringService
from app.repository.LazarusRepository import LazarusRepository
from app.core.config import settings


async def test_post_url_fix():
    """Test that the post URL fix is working"""

    # Connect to database
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.DATABASE_NAME]

    print("=" * 80)
    print("POST URL FIX - TEST SCRIPT")
    print("=" * 80)

    # Get Precious Zino's contact
    user_id = "69778bb722f097739b7716f6"  # Your user ID

    # Find all focus contacts
    contacts = await LazarusRepository.get_focus_contacts_by_user(db, user_id)

    print(f"\n📋 Found {len(contacts)} focus contacts for user {user_id}")

    # Find Precious Zino
    precious_contact = None
    for contact in contacts:
        if "precious" in contact.name.lower() and "zino" in contact.name.lower():
            precious_contact = contact
            break

    if not precious_contact:
        print("❌ Could not find Precious Zino in focus contacts")
        print("\nAvailable contacts:")
        for contact in contacts[:5]:
            print(f"   - {contact.name}")
        return

    print(f"\n✅ Found contact: {precious_contact.name}")
    print(f"   Focus ID: {precious_contact.focus_id}")
    print(f"   LinkedIn URL: {precious_contact.linkedin_url}")
    print(f"   Twitter URL: {precious_contact.twitter_url}")
    print(f"   Keywords: {precious_contact.industry_keywords}")

    # Trigger a scan
    print(f"\n🔍 Triggering scan for {precious_contact.name}...")
    print("   (This will call Apify LinkedIn scraper and AI analysis)")

    try:
        result = await LazarusMonitoringService.scan_single_focus_contact(
            db, user_id, precious_contact.focus_id
        )

        print(f"\n📊 Scan Result:")
        print(f"   Success: {result.get('success')}")
        print(f"   Message: {result.get('message')}")

        if result.get('alert_created'):
            print(f"\n🚨 ALERT CREATED!")
            alert_data = result.get('alert_data', {})
            evidence = alert_data.get('evidence', {})

            print(f"\n📝 Alert Details:")
            print(f"   Alert Type: {alert_data.get('alert_type')}")
            print(f"   Signal Type: {evidence.get('signal_type')}")
            print(f"   Confidence: {evidence.get('confidence')}")

            print(f"\n🔗 POST INFORMATION:")
            print(f"   Platform: {evidence.get('post_platform')}")
            print(f"   URL: {evidence.get('post_url')}")
            print(f"   Text Preview: {evidence.get('post_text', '')[:100]}...")
            print(f"   Author: {evidence.get('post_author')}")
            print(f"   Likes: {evidence.get('post_likes')}")
            print(f"   Comments: {evidence.get('post_comments')}")

            print(f"\n✅ TEST VERIFICATION:")
            print(f"   1. Check that post_url is not empty: {bool(evidence.get('post_url'))}")
            print(f"   2. Check that post_text matches what you see on LinkedIn")
            print(f"   3. Open the URL and verify it's the correct post:")
            print(f"      {evidence.get('post_url')}")

        else:
            print(f"\n⚠️ No alert was created")
            print(f"   This might mean:")
            print(f"   - No buying signals detected in recent posts")
            print(f"   - AI confidence was too low (<0.7)")
            print(f"   - No new posts since last scan")

    except Exception as e:
        print(f"\n❌ Error during scan: {str(e)}")
        import traceback
        traceback.print_exc()

    # Check the database for recent alerts
    print(f"\n📦 Checking recent alerts from database...")
    recent_alerts = await db["lazarus_alerts"].find({
        "user_id": user_id,
        "source_id": precious_contact.focus_id
    }).sort("created_date", -1).limit(3).to_list(None)

    if recent_alerts:
        print(f"\n   Found {len(recent_alerts)} recent alerts for this contact:")
        for i, alert in enumerate(recent_alerts, 1):
            evidence = alert.get("evidence", {})
            print(f"\n   Alert #{i}:")
            print(f"      Created: {alert.get('created_date')}")
            print(f"      Type: {alert.get('alert_type')}")
            print(f"      Post URL: {evidence.get('post_url')}")
            print(f"      Post Text: {evidence.get('post_text', '')[:80]}...")
    else:
        print(f"   No alerts found for this contact yet")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

    # Close database connection
    client.close()


if __name__ == "__main__":
    asyncio.run(test_post_url_fix())
