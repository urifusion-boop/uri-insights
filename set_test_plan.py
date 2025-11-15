"""
Helper script to set test subscription plan in MongoDB
Use this when testing WITHOUT the Task Manager service running

Usage:
    python3 set_test_plan.py <user_id> <plan>

Examples:
    python3 set_test_plan.py 507f1f77bcf86cd799439011 BUSINESS
    python3 set_test_plan.py 507f1f77bcf86cd799439011 PROFESSIONAL
    python3 set_test_plan.py 507f1f77bcf86cd799439011 STANDARD
    python3 set_test_plan.py 507f1f77bcf86cd799439011 LEAD_ONLY
"""

import asyncio
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.domain.enums.leadform_enum import LeadFormTypeEnum


async def set_test_plan(user_id: str, plan: str):
    """Set test subscription plan in conversational lead form"""
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DB]

    # Valid plans
    valid_plans = ["STANDARD", "PROFESSIONAL", "BUSINESS", "LEAD_ONLY"]
    plan_upper = plan.upper()

    if plan_upper not in valid_plans:
        print(f"❌ Invalid plan: {plan}")
        print(f"   Valid plans: {', '.join(valid_plans)}")
        return False

    # Update the conversational form
    result = await db["lead_form"].update_one(
        {
            "user_id": user_id,
            "form_type": LeadFormTypeEnum.CONVERSATIONAL.value
        },
        {
            "$set": {
                "settings.test_subscription_plan": plan_upper
            }
        }
    )

    if result.matched_count == 0:
        print(f"❌ No conversational form found for user: {user_id}")
        print(f"   Create a conversational form first!")
        return False

    if result.modified_count == 0:
        print(f"⚠️  Form already has plan: {plan_upper}")
        return True

    print(f"✅ Successfully set test plan to: {plan_upper}")
    print(f"   User ID: {user_id}")
    print(f"   Form type: CONVERSATIONAL")

    # Show the updated form
    form = await db["lead_form"].find_one({
        "user_id": user_id,
        "form_type": LeadFormTypeEnum.CONVERSATIONAL.value
    })

    if form:
        print(f"\n📋 Form details:")
        print(f"   Form ID: {form.get('lead_form_id')}")
        print(f"   Title: {form.get('form_title')}")
        print(f"   Auto-generate: {form.get('auto_generate')}")
        print(f"   Test Plan: {form.get('settings', {}).get('test_subscription_plan')}")
        print(f"   Keywords: {form.get('keywords', [])}")

    client.close()
    return True


async def show_current_plan(user_id: str):
    """Show current test plan for user"""
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DB]

    form = await db["lead_form"].find_one({
        "user_id": user_id,
        "form_type": LeadFormTypeEnum.CONVERSATIONAL.value
    })

    if not form:
        print(f"❌ No conversational form found for user: {user_id}")
        client.close()
        return

    test_plan = form.get('settings', {}).get('test_subscription_plan')
    auto_generate = form.get('auto_generate', False)

    print(f"📋 Current settings for user: {user_id}")
    print(f"   Form ID: {form.get('lead_form_id')}")
    print(f"   Title: {form.get('form_title')}")
    print(f"   Auto-generate: {auto_generate}")
    print(f"   Test Plan: {test_plan or 'Not set (will use STANDARD)'}")
    print(f"   Keywords: {form.get('keywords', [])}")

    tw_settings = form.get('settings', {}).get('conversational_twitter_fetch', {})
    if tw_settings:
        print(f"\n🐦 Last fetch info:")
        print(f"   Last fetched: {tw_settings.get('last_fetched_at')}")
        print(f"   Last count: {tw_settings.get('last_fetch_count')}")
        print(f"   Plan used: {tw_settings.get('plan')}")
        print(f"   Interval: {tw_settings.get('interval_hours')} hours")
        print(f"   Max tweets: {tw_settings.get('max_tweets')}")

    client.close()


def print_usage():
    """Print usage instructions"""
    print(__doc__)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    user_id = sys.argv[1]

    if len(sys.argv) == 2:
        # Show current plan
        asyncio.run(show_current_plan(user_id))
    elif len(sys.argv) == 3:
        # Set plan
        plan = sys.argv[2]
        success = asyncio.run(set_test_plan(user_id, plan))
        sys.exit(0 if success else 1)
    else:
        print_usage()
        sys.exit(1)
