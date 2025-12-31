"""
Standalone test script to check LinkedIn Jobs Apify response structure
Run: python test_linkedin_response.py
"""
import os
import json
from apify_client import ApifyClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_linkedin_jobs():
    """Fetch 1 job from LinkedIn and print the raw response"""

    # Get Apify token from environment
    apify_token = os.getenv("APIFY_API_TOKEN")
    if not apify_token:
        print("❌ ERROR: APIFY_API_TOKEN not found in .env file")
        return

    print("🚀 Testing LinkedIn Jobs Scraper...")
    print(f"   Token: {apify_token[:10]}..." if apify_token else "   Token: Not found")

    # Initialize Apify client
    client = ApifyClient(apify_token)

    # Configure the input
    actor_id = "bebity/linkedin-jobs-scraper"
    run_input = {
        "title": "Software Engineer",  # Simple test query
        "location": "United States",
        "rows": 2,  # Fetch only 2 jobs for quick test
        "proxy": {
            "useApifyProxy": True,
            "apifyProxyGroups": ["RESIDENTIAL"]
        }
    }

    print(f"\n📤 Sending request to Apify actor: {actor_id}")
    print(f"   Input: {json.dumps(run_input, indent=2)}")

    try:
        # Run the actor
        print("\n⏳ Running actor (this may take 10-20 seconds)...")
        run = client.actor(actor_id).call(run_input=run_input)

        # Check status
        status = run.get("status")
        print(f"\n✅ Actor run status: {status}")

        if status != "SUCCEEDED":
            print(f"❌ Actor failed with status: {status}")
            return

        # Get the results
        dataset_id = run["defaultDatasetId"]
        print(f"📦 Dataset ID: {dataset_id}")

        items = list(client.dataset(dataset_id).iterate_items())

        if not items:
            print("\n⚠️  No items returned from LinkedIn scraper")
            return

        print(f"\n✅ Fetched {len(items)} job(s)")

        # Print the FULL structure of the first item
        print("\n" + "="*80)
        print("🔍 RAW LINKEDIN JOB RESPONSE - FIRST ITEM:")
        print("="*80)
        print(json.dumps(items[0], indent=2, default=str))
        print("="*80)

        # Print all available keys
        print("\n📋 Available fields in response:")
        for key in sorted(items[0].keys()):
            value = items[0][key]
            value_preview = str(value)[:100] if value else "None"
            print(f"   • {key}: {value_preview}")

        # Check for remote/workplace type fields
        print("\n🎯 CHECKING FOR REMOTE/WORKPLACE TYPE FIELDS:")
        remote_fields = ['workType', 'workplaceType', 'locationType', 'remote', 'isRemote', 'workplace']
        found_fields = []

        for field in remote_fields:
            if field in items[0]:
                found_fields.append(field)
                print(f"   ✅ FOUND: {field} = {items[0][field]}")

        if not found_fields:
            print("   ❌ NO remote/workplace fields found in response")
            print("   💡 Location field value:", items[0].get('location', 'N/A'))

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_linkedin_jobs()
