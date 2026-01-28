"""
Migration script to fix skills data in focus_contacts collection
Converts {'title': 'Skill Name'} objects to just 'Skill Name' strings
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings


async def fix_skills_data():
    """Fix skills data in all focus contacts"""

    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.DATABASE_NAME]

    print("=" * 80)
    print("FIXING SKILLS DATA IN FOCUS CONTACTS")
    print("=" * 80)

    # Find all contacts with skills field
    contacts = await db["focus_contacts"].find({"skills": {"$exists": True}}).to_list(None)

    print(f"\n📋 Found {len(contacts)} contacts with skills field")

    fixed_count = 0
    skipped_count = 0

    for contact in contacts:
        skills = contact.get("skills")

        # Check if skills need fixing
        if not skills or not isinstance(skills, list):
            continue

        needs_fixing = False
        for skill in skills:
            if isinstance(skill, dict):
                needs_fixing = True
                break

        if not needs_fixing:
            skipped_count += 1
            continue

        # Convert skills objects to strings
        fixed_skills = []
        for skill in skills:
            if isinstance(skill, dict) and 'title' in skill:
                fixed_skills.append(skill['title'])
            elif isinstance(skill, str):
                fixed_skills.append(skill)

        # Update the contact
        result = await db["focus_contacts"].update_one(
            {"focus_id": contact["focus_id"]},
            {"$set": {"skills": fixed_skills}}
        )

        if result.modified_count > 0:
            fixed_count += 1
            print(f"✅ Fixed skills for: {contact.get('name')} ({len(fixed_skills)} skills)")

    print(f"\n📊 Summary:")
    print(f"   Fixed: {fixed_count}")
    print(f"   Skipped (already correct): {skipped_count}")
    print(f"   Total processed: {len(contacts)}")

    print("\n" + "=" * 80)
    print("MIGRATION COMPLETE")
    print("=" * 80)

    client.close()


if __name__ == "__main__":
    asyncio.run(fix_skills_data())
