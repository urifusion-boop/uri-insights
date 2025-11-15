"""
Manual test to trigger conversational Twitter fetch and see detailed errors
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.services.LeadService import LeadService

async def test_fetch():
    """Manually trigger the fetch job - with detailed exception handling"""
    client = AsyncIOMotorClient(settings.MONGODB_URI)
    db = client[settings.MONGODB_DB]

    print("Starting manual fetch...")
    print("="*60)

    # Import needed to call _process directly
    from app.repository.LeadFormRepository import LeadFormRepository
    from app.domain.enums.leadform_enum import LeadFormTypeEnum

    try:
        # Get forms manually so we can see exceptions
        forms = await db[LeadFormRepository.COLLECTION_NAME].find({
            "form_type": LeadFormTypeEnum.CONVERSATIONAL.value
        }).to_list(length=10)

        print(f"\nFound {len(forms)} conversational forms")

        for i, form in enumerate(forms, 1):
            print(f"\n--- Processing form {i}/{len(forms)} ---")
            print(f"User: {form.get('user_id')}")
            print(f"Title: {form.get('form_title')}")
            print(f"Keywords: {form.get('keywords', [])}")

            try:
                await LeadService._process_conversational_twitter_fetch(db, form)
                print(f"✅ Successfully processed form {i}")
            except Exception as e:
                print(f"❌ Error processing form {i}: {e}")
                import traceback
                traceback.print_exc()

        print("\n" + "="*60)
        print("✅ Fetch completed")
    except Exception as e:
        print("\n" + "="*60)
        print(f"❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()

if __name__ == "__main__":
    asyncio.run(test_fetch())
