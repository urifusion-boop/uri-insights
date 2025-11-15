"""
Setup script to create a test user and conversational form for Twitter leads testing

This creates:
1. A test user in the users collection
2. A conversational lead form with auto_generate enabled
3. Twitter fetch settings with keywords

Usage:
    python3 setup_test_user_and_form.py
"""

import asyncio
import sys
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.domain.enums.leadform_enum import LeadFormTypeEnum


class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'


async def create_test_user(db):
    """Create a test user"""
    user_id = "6735e2e02a610392a70e934b"

    # Check if user already exists
    existing_user = await db.users.find_one({"_id": user_id})
    if existing_user:
        print(f"{Colors.YELLOW}⚠️  User already exists: {user_id}{Colors.END}")
        print(f"   Email: {existing_user.get('email')}")
        return user_id

    # Create test user
    test_user = {
        "_id": user_id,
        "email": "test@example.com",
        "full_name": "Test User",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "is_active": True,
    }

    await db.users.insert_one(test_user)
    print(f"{Colors.GREEN}✅ Created test user: {user_id}{Colors.END}")
    print(f"   Email: {test_user['email']}")
    print(f"   Name: {test_user['full_name']}")

    return user_id


async def create_conversational_form(db, user_id: str):
    """Create a conversational lead form for Twitter testing"""

    # Check if form already exists
    existing_form = await db.lead_form.find_one({
        "user_id": user_id,
        "form_type": LeadFormTypeEnum.CONVERSATIONAL.value
    })

    if existing_form:
        print(f"\n{Colors.YELLOW}⚠️  Conversational form already exists{Colors.END}")
        print(f"   Form ID: {existing_form.get('lead_form_id')}")
        print(f"   Title: {existing_form.get('form_title')}")
        print(f"   Auto-generate: {existing_form.get('auto_generate')}")

        keywords = existing_form.get('settings', {}).get('conversational_twitter_fetch', {}).get('keywords', [])
        print(f"   Keywords: {keywords}")

        return existing_form.get('lead_form_id')

    # Create new conversational form
    form_id = "68a6eb1d16c444056cee6a96"

    conversational_form = {
        "lead_form_id": form_id,
        "user_id": user_id,
        "form_type": LeadFormTypeEnum.CONVERSATIONAL.value,
        "form_title": "Twitter Lead Generation Form",
        "auto_generate": True,
        "created_date": datetime.utcnow(),
        "updated_date": datetime.utcnow(),
        "settings": {
            "conversational_twitter_fetch": {
                "keywords": [
                    "hiring software engineer",
                    "looking for developer",
                    "need programmer"
                ],
                "enabled": True,
                "last_fetched_at": None,
                "fetch_count": 0
            }
        }
    }

    await db.lead_form.insert_one(conversational_form)

    print(f"\n{Colors.GREEN}✅ Created conversational form: {form_id}{Colors.END}")
    print(f"   User ID: {user_id}")
    print(f"   Title: {conversational_form['form_title']}")
    print(f"   Auto-generate: {conversational_form['auto_generate']}")
    print(f"   Keywords: {conversational_form['settings']['conversational_twitter_fetch']['keywords']}")

    return form_id


async def setup_test_plan(db, user_id: str, plan: str = "BUSINESS"):
    """Set the test subscription plan"""

    result = await db.lead_form.update_one(
        {
            "user_id": user_id,
            "form_type": LeadFormTypeEnum.CONVERSATIONAL.value
        },
        {
            "$set": {
                "settings.test_subscription_plan": plan.upper()
            }
        }
    )

    if result.modified_count > 0:
        print(f"\n{Colors.GREEN}✅ Set test subscription plan: {plan.upper()}{Colors.END}")
        print(f"   This allows testing without Task Manager service")
    else:
        print(f"\n{Colors.YELLOW}⚠️  Could not set test plan (form might not exist yet){Colors.END}")


async def verify_setup(db, user_id: str):
    """Verify the setup is complete"""

    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}Verification{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}\n")

    # Check user
    user = await db.users.find_one({"_id": user_id})
    if user:
        print(f"{Colors.GREEN}✅ User exists{Colors.END}")
        print(f"   ID: {user_id}")
        print(f"   Email: {user.get('email')}")
    else:
        print(f"{Colors.RED}❌ User not found{Colors.END}")
        return False

    # Check form
    form = await db.lead_form.find_one({
        "user_id": user_id,
        "form_type": LeadFormTypeEnum.CONVERSATIONAL.value
    })

    if form:
        print(f"\n{Colors.GREEN}✅ Conversational form exists{Colors.END}")
        print(f"   Form ID: {form.get('lead_form_id')}")
        print(f"   Title: {form.get('form_title')}")
        print(f"   Auto-generate: {form.get('auto_generate')}")

        settings = form.get('settings', {})
        twitter_settings = settings.get('conversational_twitter_fetch', {})
        test_plan = settings.get('test_subscription_plan')

        print(f"   Keywords: {twitter_settings.get('keywords', [])}")

        if test_plan:
            print(f"   Test Plan: {Colors.BOLD}{test_plan}{Colors.END}")
        else:
            print(f"   Test Plan: {Colors.YELLOW}Not set (will use Task Manager){Colors.END}")
    else:
        print(f"\n{Colors.RED}❌ Conversational form not found{Colors.END}")
        return False

    print(f"\n{Colors.GREEN}{'='*60}{Colors.END}")
    print(f"{Colors.GREEN}Setup Complete! Ready to test.{Colors.END}")
    print(f"{Colors.GREEN}{'='*60}{Colors.END}\n")

    return True


async def main():
    """Main setup function"""

    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}Twitter Lead Generation - Test Setup{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}\n")

    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DB]

    print(f"Database: {Colors.BOLD}{settings.MONGODB_DB}{Colors.END}\n")

    try:
        # Create test user
        user_id = await create_test_user(db)

        # Create conversational form
        form_id = await create_conversational_form(db, user_id)

        # Set test plan
        await setup_test_plan(db, user_id, "BUSINESS")

        # Verify everything
        success = await verify_setup(db, user_id)

        if success:
            print(f"\n{Colors.CYAN}Next Steps:{Colors.END}")
            print(f"1. Start the server:")
            print(f"   {Colors.BOLD}uvicorn app.main:app --reload{Colors.END}")
            print(f"\n2. Monitor the logs for tweet fetches:")
            print(f"   {Colors.BOLD}tail -f logs/app.log | grep 'conversational_twitter_fetch'{Colors.END}")
            print(f"\n3. Check leads in database after 1-2 minutes:")
            print(f"   {Colors.BOLD}./venv/bin/python3 -c \"")
            print(f"   from motor.motor_asyncio import AsyncIOMotorClient")
            print(f"   import asyncio")
            print(f"   from app.core.config import settings")
            print(f"   async def check():")
            print(f"       client = AsyncIOMotorClient(settings.MONGODB_URI)")
            print(f"       db = client[settings.MONGODB_DB]")
            print(f"       count = await db.leads.count_documents({{'assigned_to': '{user_id}', 'lead_type': 'CONVERSATIONAL'}})")
            print(f"       print(f'Total conversational leads: {{count}}')")
            print(f"   asyncio.run(check())")
            print(f"   \"{Colors.END}")
            print(f"\n{Colors.YELLOW}Note: Testing mode is enabled (ENV != 'production'){Colors.END}")
            print(f"{Colors.YELLOW}      Scheduler runs every 1 minute{Colors.END}")
            print(f"{Colors.YELLOW}      BUSINESS plan: 5 tweets every 2 minutes{Colors.END}\n")

    except Exception as e:
        print(f"\n{Colors.RED}❌ Error during setup: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Cancelled by user{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
