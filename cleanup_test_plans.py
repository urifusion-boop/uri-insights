"""
Cleanup script to remove test/mock subscription plans from lead forms

This removes the test_subscription_plan field that was added during testing,
so the system will use the real subscription plan from Task Manager service.

Usage:
    # Remove mock plan from specific user
    python3 cleanup_test_plans.py <user_id>

    # Remove mock plans from ALL users
    python3 cleanup_test_plans.py --all

    # Preview what would be removed (dry run)
    python3 cleanup_test_plans.py <user_id> --dry-run
    python3 cleanup_test_plans.py --all --dry-run
"""

import asyncio
import sys
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


async def remove_test_plan(user_id: str, dry_run: bool = False):
    """Remove test subscription plan from a specific user's form"""
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DB]

    # Find the form first
    form = await db["lead_form"].find_one({
        "user_id": user_id,
        "form_type": LeadFormTypeEnum.CONVERSATIONAL.value
    })

    if not form:
        print(f"{Colors.RED}❌ No conversational form found for user: {user_id}{Colors.END}")
        client.close()
        return False

    # Check if test plan exists
    test_plan = form.get('settings', {}).get('test_subscription_plan')

    if not test_plan:
        print(f"{Colors.YELLOW}⚠️  No test plan found for user: {user_id}{Colors.END}")
        print(f"   Form ID: {form.get('lead_form_id')}")
        print(f"   Nothing to clean up!")
        client.close()
        return True

    print(f"\n{Colors.CYAN}Found test plan for user: {user_id}{Colors.END}")
    print(f"   Form ID: {form.get('lead_form_id')}")
    print(f"   Form Title: {form.get('form_title')}")
    print(f"   Test Plan: {Colors.BOLD}{test_plan}{Colors.END}")

    if dry_run:
        print(f"\n{Colors.YELLOW}[DRY RUN] Would remove test plan (not actually removing){Colors.END}")
        client.close()
        return True

    # Remove the test plan
    result = await db["lead_form"].update_one(
        {
            "user_id": user_id,
            "form_type": LeadFormTypeEnum.CONVERSATIONAL.value
        },
        {
            "$unset": {
                "settings.test_subscription_plan": ""
            }
        }
    )

    if result.modified_count > 0:
        print(f"{Colors.GREEN}✅ Successfully removed test plan{Colors.END}")
        print(f"   System will now use real subscription plan from Task Manager")
    else:
        print(f"{Colors.YELLOW}⚠️  No changes made (already removed?){Colors.END}")

    client.close()
    return True


async def remove_all_test_plans(dry_run: bool = False):
    """Remove test subscription plans from ALL users"""
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DB]

    # Find all forms with test plans
    forms_with_test_plans = await db["lead_form"].find({
        "form_type": LeadFormTypeEnum.CONVERSATIONAL.value,
        "settings.test_subscription_plan": {"$exists": True}
    }).to_list(length=None)

    if not forms_with_test_plans:
        print(f"{Colors.YELLOW}⚠️  No forms with test plans found{Colors.END}")
        print(f"   Nothing to clean up!")
        client.close()
        return True

    print(f"\n{Colors.CYAN}Found {len(forms_with_test_plans)} form(s) with test plans:{Colors.END}\n")

    for i, form in enumerate(forms_with_test_plans, 1):
        test_plan = form.get('settings', {}).get('test_subscription_plan')
        print(f"{i}. User: {form.get('user_id')}")
        print(f"   Form ID: {form.get('lead_form_id')}")
        print(f"   Title: {form.get('form_title')}")
        print(f"   Test Plan: {Colors.BOLD}{test_plan}{Colors.END}\n")

    if dry_run:
        print(f"{Colors.YELLOW}[DRY RUN] Would remove test plans from {len(forms_with_test_plans)} form(s){Colors.END}")
        print(f"{Colors.YELLOW}           (not actually removing){Colors.END}")
        client.close()
        return True

    # Confirm before bulk deletion
    if len(forms_with_test_plans) > 1:
        confirmation = input(f"\n{Colors.YELLOW}Remove test plans from {len(forms_with_test_plans)} forms? (yes/no): {Colors.END}").strip().lower()
        if confirmation != 'yes':
            print(f"{Colors.RED}❌ Cancelled by user{Colors.END}")
            client.close()
            return False

    # Remove all test plans
    result = await db["lead_form"].update_many(
        {
            "form_type": LeadFormTypeEnum.CONVERSATIONAL.value,
            "settings.test_subscription_plan": {"$exists": True}
        },
        {
            "$unset": {
                "settings.test_subscription_plan": ""
            }
        }
    )

    print(f"\n{Colors.GREEN}✅ Successfully removed test plans from {result.modified_count} form(s){Colors.END}")
    print(f"   System will now use real subscription plans from Task Manager")

    client.close()
    return True


async def show_forms_with_test_plans():
    """Show all forms that currently have test plans"""
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DB]

    forms = await db["lead_form"].find({
        "form_type": LeadFormTypeEnum.CONVERSATIONAL.value,
        "settings.test_subscription_plan": {"$exists": True}
    }).to_list(length=None)

    if not forms:
        print(f"{Colors.GREEN}✅ No forms with test plans found{Colors.END}")
        print(f"   All clean!")
        client.close()
        return

    print(f"\n{Colors.CYAN}Forms with test plans:{Colors.END}\n")

    for i, form in enumerate(forms, 1):
        test_plan = form.get('settings', {}).get('test_subscription_plan')
        print(f"{i}. User: {form.get('user_id')}")
        print(f"   Form ID: {form.get('lead_form_id')}")
        print(f"   Title: {form.get('form_title')}")
        print(f"   Test Plan: {Colors.BOLD}{test_plan}{Colors.END}")
        print(f"   Auto-generate: {form.get('auto_generate')}\n")

    print(f"{Colors.CYAN}Total: {len(forms)} form(s) with test plans{Colors.END}")

    client.close()


def print_usage():
    """Print usage instructions"""
    print(__doc__)
    print(f"\n{Colors.BOLD}Examples:{Colors.END}")
    print(f"  {Colors.CYAN}# Remove test plan from specific user{Colors.END}")
    print(f"  python3 cleanup_test_plans.py 507f1f77bcf86cd799439011")
    print(f"\n  {Colors.CYAN}# Remove test plans from ALL users{Colors.END}")
    print(f"  python3 cleanup_test_plans.py --all")
    print(f"\n  {Colors.CYAN}# Preview changes without removing (dry run){Colors.END}")
    print(f"  python3 cleanup_test_plans.py 507f1f77bcf86cd799439011 --dry-run")
    print(f"  python3 cleanup_test_plans.py --all --dry-run")
    print(f"\n  {Colors.CYAN}# Show all forms with test plans{Colors.END}")
    print(f"  python3 cleanup_test_plans.py --list")


async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    arg1 = sys.argv[1]
    dry_run = "--dry-run" in sys.argv

    print(f"\n{Colors.BOLD}{Colors.CYAN}")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║        Cleanup Test Subscription Plans                   ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print(f"{Colors.END}")

    if arg1 == "--list":
        await show_forms_with_test_plans()
    elif arg1 == "--all":
        await remove_all_test_plans(dry_run)
    elif arg1.startswith("--"):
        print(f"{Colors.RED}❌ Unknown option: {arg1}{Colors.END}")
        print_usage()
        sys.exit(1)
    else:
        user_id = arg1
        await remove_test_plan(user_id, dry_run)

    print(f"\n{Colors.GREEN}Done!{Colors.END}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Cancelled by user{Colors.END}")
    except Exception as e:
        print(f"\n{Colors.RED}Error: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
