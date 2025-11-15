"""
Test Script for Conversational Twitter Leads Auto-Generation
Tests all subscription plans: LEAD_ONLY, BUSINESS, PROFESSIONAL, STANDARD

Prerequisites:
1. Set ENV to non-production in .env (e.g., ENV=development)
2. Have APIFY_API_TOKEN configured
3. Have a test user with conversational lead form
4. Have authorization token ready
"""

import asyncio
import sys
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.services.LeadService import LeadService
from app.repository.LeadFormRepository import LeadFormRepository
from app.repository.LeadRepository import LeadRepository
from app.domain.enums.leadform_enum import LeadFormTypeEnum


class TestColors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


async def get_db():
    """Get database connection"""
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    return client[settings.MONGODB_DB]


async def test_plan_configuration(db, test_user_id: str, plan_name: str):
    """Test a specific subscription plan configuration"""
    print(f"\n{TestColors.HEADER}{'='*60}{TestColors.ENDC}")
    print(f"{TestColors.BOLD}Testing Plan: {plan_name}{TestColors.ENDC}")
    print(f"{TestColors.HEADER}{'='*60}{TestColors.ENDC}")

    # Get the conversational form for this user
    form_response = await LeadFormRepository.get_by_filters(
        db=db,
        filters={
            "user_id": test_user_id,
            "form_type": LeadFormTypeEnum.CONVERSATIONAL.value,
        }
    )

    forms = form_response.get("responseData", [])
    if not forms:
        print(f"{TestColors.FAIL}❌ No conversational form found for user {test_user_id}{TestColors.ENDC}")
        return False

    form = forms[0]
    print(f"{TestColors.OKGREEN}✓ Found form: {form.get('form_title')}{TestColors.ENDC}")
    print(f"  Form ID: {form.get('lead_form_id')}")
    print(f"  Auto-generate: {form.get('auto_generate')}")
    print(f"  Keywords: {form.get('keywords', [])}")

    # Check current settings
    tw_settings = form.get('settings', {}).get('conversational_twitter_fetch', {})
    if tw_settings:
        print(f"\n{TestColors.OKCYAN}Previous Fetch Info:{TestColors.ENDC}")
        print(f"  Last fetched: {tw_settings.get('last_fetched_at')}")
        print(f"  Last count: {tw_settings.get('last_fetch_count')}")
        print(f"  Plan: {tw_settings.get('plan')}")
        print(f"  Interval: {tw_settings.get('interval_hours')} hours")
        print(f"  Max tweets: {tw_settings.get('max_tweets')}")

    # Count leads before
    leads_before = await LeadRepository.get_leads_by_filters(
        db=db,
        filters={"assigned_to": test_user_id, "lead_type": LeadFormTypeEnum.CONVERSATIONAL.value}
    )
    count_before = len(leads_before.get("responseData", {}).get("data", []))

    print(f"\n{TestColors.OKCYAN}Leads Count Before: {count_before}{TestColors.ENDC}")

    # Trigger the fetch
    print(f"\n{TestColors.WARNING}⏳ Triggering fetch for {plan_name}...{TestColors.ENDC}")
    start_time = datetime.utcnow()

    try:
        await LeadService.fetch_and_save_conversational_twitter_leads(db)
        print(f"{TestColors.OKGREEN}✓ Fetch completed successfully{TestColors.ENDC}")
    except Exception as e:
        print(f"{TestColors.FAIL}❌ Fetch failed: {e}{TestColors.ENDC}")
        return False

    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()

    # Check updated settings
    updated_form_response = await LeadFormRepository.get_by_filters(
        db=db,
        filters={
            "user_id": test_user_id,
            "form_type": LeadFormTypeEnum.CONVERSATIONAL.value,
        }
    )
    updated_form = updated_form_response.get("responseData", [])[0]
    updated_tw_settings = updated_form.get('settings', {}).get('conversational_twitter_fetch', {})

    # Count leads after
    leads_after = await LeadRepository.get_leads_by_filters(
        db=db,
        filters={"assigned_to": test_user_id, "lead_type": LeadFormTypeEnum.CONVERSATIONAL.value}
    )
    count_after = len(leads_after.get("responseData", {}).get("data", []))
    new_leads = count_after - count_before

    # Display results
    print(f"\n{TestColors.OKGREEN}{'='*60}{TestColors.ENDC}")
    print(f"{TestColors.BOLD}Test Results:{TestColors.ENDC}")
    print(f"{TestColors.OKGREEN}{'='*60}{TestColors.ENDC}")
    print(f"  Duration: {duration:.2f} seconds")
    print(f"  Leads Before: {count_before}")
    print(f"  Leads After: {count_after}")
    print(f"  New Leads: {TestColors.OKGREEN}{new_leads}{TestColors.ENDC}")

    if updated_tw_settings:
        print(f"\n{TestColors.OKCYAN}Updated Settings:{TestColors.ENDC}")
        print(f"  Last fetched: {updated_tw_settings.get('last_fetched_at')}")
        print(f"  Fetch count: {updated_tw_settings.get('last_fetch_count')}")
        print(f"  Plan: {TestColors.BOLD}{updated_tw_settings.get('plan')}{TestColors.ENDC}")
        print(f"  Interval: {updated_tw_settings.get('interval_hours')} hours")
        print(f"  Max tweets: {updated_tw_settings.get('max_tweets')}")
        print(f"  Keyword: {updated_tw_settings.get('keyword')}")

    # Verify plan-specific configuration
    expected_config = {
        "LEAD_ONLY": {"max_tweets": 5, "interval": 2/60},  # Testing mode
        "BUSINESS": {"max_tweets": 5, "interval": 2/60},
        "PROFESSIONAL": {"max_tweets": 4, "interval": 4/60},
        "STANDARD": {"max_tweets": 3, "interval": 6/60},
    }

    if settings.ENV.lower() == "production":
        expected_config = {
            "LEAD_ONLY": {"max_tweets": 40, "interval": 1},
            "BUSINESS": {"max_tweets": 40, "interval": 1},
            "PROFESSIONAL": {"max_tweets": 30, "interval": 3},
            "STANDARD": {"max_tweets": 20, "interval": 7},
        }

    expected = expected_config.get(plan_name, {})
    actual_max = updated_tw_settings.get('max_tweets')
    actual_interval = updated_tw_settings.get('interval_hours')

    print(f"\n{TestColors.OKCYAN}Configuration Check:{TestColors.ENDC}")
    print(f"  Expected max_tweets: {expected.get('max_tweets')}")
    print(f"  Actual max_tweets: {actual_max}")
    print(f"  Match: {TestColors.OKGREEN if actual_max == expected.get('max_tweets') else TestColors.FAIL}{'✓' if actual_max == expected.get('max_tweets') else '✗'}{TestColors.ENDC}")

    return new_leads > 0


async def test_interval_enforcement(db, test_user_id: str):
    """Test that interval enforcement works (shouldn't fetch twice in quick succession)"""
    print(f"\n{TestColors.HEADER}{'='*60}{TestColors.ENDC}")
    print(f"{TestColors.BOLD}Testing Interval Enforcement{TestColors.ENDC}")
    print(f"{TestColors.HEADER}{'='*60}{TestColors.ENDC}")

    # First fetch
    print(f"{TestColors.WARNING}⏳ First fetch...{TestColors.ENDC}")
    await LeadService.fetch_and_save_conversational_twitter_leads(db)

    # Get leads count
    leads_response1 = await LeadRepository.get_leads_by_filters(
        db=db,
        filters={"assigned_to": test_user_id, "lead_type": LeadFormTypeEnum.CONVERSATIONAL.value}
    )
    count1 = len(leads_response1.get("responseData", {}).get("data", []))

    # Immediate second fetch (should be skipped)
    print(f"{TestColors.WARNING}⏳ Immediate second fetch (should be skipped)...{TestColors.ENDC}")
    await LeadService.fetch_and_save_conversational_twitter_leads(db)

    # Get leads count again
    leads_response2 = await LeadRepository.get_leads_by_filters(
        db=db,
        filters={"assigned_to": test_user_id, "lead_type": LeadFormTypeEnum.CONVERSATIONAL.value}
    )
    count2 = len(leads_response2.get("responseData", {}).get("data", []))

    if count1 == count2:
        print(f"{TestColors.OKGREEN}✓ Interval enforcement working! No duplicate fetch.{TestColors.ENDC}")
        return True
    else:
        print(f"{TestColors.FAIL}✗ Interval enforcement failed! Duplicate fetch occurred.{TestColors.ENDC}")
        return False


async def main():
    """Main test runner"""
    print(f"\n{TestColors.BOLD}{TestColors.HEADER}")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  Conversational Twitter Leads - Auto-Generation Test     ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print(f"{TestColors.ENDC}")

    # Check environment
    print(f"\n{TestColors.OKCYAN}Environment Check:{TestColors.ENDC}")
    print(f"  ENV: {settings.ENV}")
    print(f"  Testing Mode: {settings.ENV.lower() != 'production'}")
    print(f"  APIFY_API_TOKEN: {'✓ Configured' if settings.APIFY_API_TOKEN else '✗ Missing'}")
    print(f"  OPENAI_API_KEY: {'✓ Configured' if settings.OPENAI_API_KEY else '✗ Missing'}")

    if not settings.APIFY_API_TOKEN:
        print(f"\n{TestColors.FAIL}❌ APIFY_API_TOKEN not configured. Please set it in .env{TestColors.ENDC}")
        return

    # Get test user ID
    test_user_id = input(f"\n{TestColors.BOLD}Enter test user ID: {TestColors.ENDC}").strip()
    if not test_user_id:
        print(f"{TestColors.FAIL}❌ User ID required{TestColors.ENDC}")
        return

    db = await get_db()

    # Test each plan
    plans_to_test = ["STANDARD", "PROFESSIONAL", "BUSINESS", "LEAD_ONLY"]

    print(f"\n{TestColors.WARNING}Note: You need to manually change the user's subscription plan in the database{TestColors.ENDC}")
    print(f"{TestColors.WARNING}      or via your task manager service between tests.{TestColors.ENDC}")

    for plan in plans_to_test:
        input(f"\n{TestColors.BOLD}Press Enter when user is set to {plan} plan...{TestColors.ENDC}")
        await test_plan_configuration(db, test_user_id, plan)

        if plan == plans_to_test[0]:  # Only test interval enforcement once
            await test_interval_enforcement(db, test_user_id)

    print(f"\n{TestColors.OKGREEN}{TestColors.BOLD}")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║                  Testing Complete!                        ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print(f"{TestColors.ENDC}")

    print(f"\n{TestColors.WARNING}Remember to:{TestColors.ENDC}")
    print(f"  1. Remove testing mode code after testing")
    print(f"  2. Set ENV=production in production environment")
    print(f"  3. Check the leads in your frontend dashboard")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{TestColors.WARNING}Test interrupted by user{TestColors.ENDC}")
    except Exception as e:
        print(f"\n{TestColors.FAIL}Test failed with error: {e}{TestColors.ENDC}")
        import traceback
        traceback.print_exc()
