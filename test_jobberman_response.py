"""
Standalone test script to check Jobberman Apify response structure
Run: python test_jobberman_response.py
"""
import os
import json
from apify_client import ApifyClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_jobberman_jobs():
    """Fetch 1 job from Jobberman and print the raw response"""

    # Get Apify token from environment
    apify_token = os.getenv("APIFY_API_TOKEN")
    if not apify_token:
        print("❌ ERROR: APIFY_API_TOKEN not found in .env file")
        return

    print("🚀 Testing Jobberman Jobs Scraper...")
    print(f"   Token: {apify_token[:10]}..." if apify_token else "   Token: Not found")

    # Initialize Apify client
    client = ApifyClient(apify_token)

    # Configure the input
    actor_id = "shahidirfan/jobberman-job-scraper"
    run_input = {
        "keyword": "Software Developer",  # Simple test query
        "location": "Lagos",
        "posted_date": "anytime",
        "collectDetails": True,  # Get full job details
        "results_wanted": 2,  # Fetch only 2 jobs for quick test
        "max_pages": 1,  # Only 1 page
        "proxyConfiguration": {
            "useApifyProxy": True
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
            print("\n⚠️  No items returned from Jobberman scraper")
            return

        print(f"\n✅ Fetched {len(items)} job(s)")

        # Print the FULL structure of the first item
        print("\n" + "="*80)
        print("🔍 RAW JOBBERMAN JOB RESPONSE - FIRST ITEM:")
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
        remote_fields = ['workType', 'workplaceType', 'locationType', 'remote', 'isRemote', 'workplace', 'job_type', 'jobType']
        found_fields = []

        for field in remote_fields:
            if field in items[0]:
                found_fields.append(field)
                print(f"   ✅ FOUND: {field} = {items[0][field]}")

        if not found_fields:
            print("   ❌ NO remote/workplace fields found in response")
            print("   💡 Location field value:", items[0].get('location', 'N/A'))

            # Check if "remote" appears in location or description
            location_str = str(items[0].get('location', '')).lower()
            description_str = str(items[0].get('description', ''))[:200].lower()

            if 'remote' in location_str:
                print("   🔍 'remote' found in LOCATION field!")
            if 'remote' in description_str:
                print("   🔍 'remote' found in DESCRIPTION field!")

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_jobberman_jobs()
