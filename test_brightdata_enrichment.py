"""
Test script for BrightDataProfileEnrichmentService

This script tests:
1. Single profile enrichment
2. Batch profile enrichment
3. Error handling for invalid URLs
4. Field extraction and normalization

Usage:
    python test_brightdata_enrichment.py
"""
import asyncio
import sys
import os
from pprint import pprint

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.BrightDataProfileEnrichmentService import BrightDataProfileEnrichmentService


async def test_single_profile_enrichment():
    """Test enriching a single LinkedIn profile"""
    print("\n" + "=" * 80)
    print("TEST 1: Single Profile Enrichment")
    print("=" * 80)

    service = BrightDataProfileEnrichmentService()

    # Test with a public LinkedIn profile
    test_url = "https://www.linkedin.com/in/shahar-cohen-a667a218a/"

    print(f"\nEnriching profile: {test_url}")
    print("-" * 80)

    result = await service.enrich_profile(test_url, timeout_seconds=90)

    if result["success"]:
        print("✅ SUCCESS")
        print("\nProfile Data:")
        print("-" * 80)
        profile = result["profile"]

        # Print key fields
        print(f"Full Name: {profile.get('full_name')}")
        print(f"Headline: {profile.get('headline')}")
        print(f"Location: {profile.get('location')}")
        print(f"Current Company: {profile.get('current_company')}")
        print(f"Current Position: {profile.get('current_position')}")
        print(f"Email: {profile.get('email') or 'Not found'}")
        print(f"Phone: {profile.get('phone') or 'Not found'}")
        print(f"Connections: {profile.get('connections_count')}")
        print(f"Profile Photo: {profile.get('profile_photo_url')[:50]}..." if profile.get('profile_photo_url') else "Not found")
        print(f"\nAbout: {profile.get('about')[:100]}..." if profile.get('about') else "Not found")

        # Print work experience
        experience = profile.get('work_experience', [])
        print(f"\nWork Experience ({len(experience)} entries):")
        for i, job in enumerate(experience[:3], 1):  # Show first 3
            print(f"  {i}. {job.get('title', 'N/A')} at {job.get('company', 'N/A')}")

        # Print education
        education = profile.get('education', [])
        print(f"\nEducation ({len(education)} entries):")
        for i, edu in enumerate(education[:3], 1):  # Show first 3
            print(f"  {i}. {edu.get('school', 'N/A')} - {edu.get('degree', 'N/A')}")

        # Print skills
        skills = profile.get('skills', [])
        print(f"\nSkills ({len(skills)} total): {', '.join(skills[:10])}")

        print("\n" + "-" * 80)
        print("Full response structure:")
        print("-" * 80)
        pprint(result, depth=2, width=120)
    else:
        print("❌ FAILED")
        print(f"Error: {result.get('error_message')}")

    return result


async def test_batch_profile_enrichment():
    """Test enriching multiple LinkedIn profiles in batch"""
    print("\n" + "=" * 80)
    print("TEST 2: Batch Profile Enrichment")
    print("=" * 80)

    service = BrightDataProfileEnrichmentService()

    # Test with multiple public LinkedIn profiles
    test_urls = [
        "https://www.linkedin.com/in/shahar-cohen-a667a218a/",
        "https://www.linkedin.com/in/williamhgates/",  # Bill Gates (if public)
        "https://www.linkedin.com/in/satyanadella/",   # Satya Nadella (if public)
    ]

    print(f"\nEnriching {len(test_urls)} profiles in batch:")
    for i, url in enumerate(test_urls, 1):
        print(f"  {i}. {url}")
    print("-" * 80)

    results = await service.batch_enrich_profiles(test_urls, timeout_seconds=180)

    print(f"\n✅ Batch completed: {len(results)} results")
    print("-" * 80)

    for url, result in results.items():
        if result["success"]:
            profile = result["profile"]
            print(f"\n✅ {profile.get('full_name')}")
            print(f"   URL: {url}")
            print(f"   Headline: {profile.get('headline')}")
            print(f"   Company: {profile.get('current_company')}")
            print(f"   Email: {profile.get('email') or 'Not found'}")
            print(f"   Phone: {profile.get('phone') or 'Not found'}")
        else:
            print(f"\n❌ Failed: {url}")
            print(f"   Error: {result.get('error_message')}")

    return results


async def test_invalid_url_handling():
    """Test error handling for invalid URLs"""
    print("\n" + "=" * 80)
    print("TEST 3: Invalid URL Handling")
    print("=" * 80)

    service = BrightDataProfileEnrichmentService()

    # Test with invalid URLs
    invalid_urls = [
        "https://example.com/not-linkedin",
        "https://linkedin.com/company/invalid",  # Company URL instead of profile
        "",  # Empty string
        "not-a-url",
    ]

    print("\nTesting invalid URLs:")
    for i, url in enumerate(invalid_urls, 1):
        print(f"\n  Test {i}: {url or '(empty string)'}")
        result = await service.enrich_profile(url)

        if result["success"]:
            print(f"    ⚠️  Unexpectedly succeeded")
        else:
            print(f"    ✅ Correctly failed: {result.get('error_message')}")


async def test_field_extraction():
    """Test that all important fields are extracted correctly"""
    print("\n" + "=" * 80)
    print("TEST 4: Field Extraction Validation")
    print("=" * 80)

    service = BrightDataProfileEnrichmentService()

    # Use a known public profile for testing
    test_url = "https://www.linkedin.com/in/shahar-cohen-a667a218a/"

    print(f"\nValidating field extraction for: {test_url}")
    print("-" * 80)

    result = await service.enrich_profile(test_url)

    if result["success"]:
        profile = result["profile"]

        # Required fields
        required_fields = [
            "full_name",
            "headline",
            "location",
            "current_company",
            "current_position",
            "profile_photo_url",
            "about",
            "connections_count",
            "work_experience",
            "education",
            "skills",
            "languages",
            "certifications",
            "scraped_at"
        ]

        # Optional but important fields
        optional_fields = ["email", "phone"]

        print("\n✅ Required Fields:")
        for field in required_fields:
            value = profile.get(field)
            if value or value == 0 or value == []:  # Allow empty lists/0
                status = "✅"
                display_value = value if isinstance(value, (str, int)) else f"<{type(value).__name__}>"
                if isinstance(value, str) and len(value) > 50:
                    display_value = value[:50] + "..."
            else:
                status = "❌ MISSING"
                display_value = "None"

            print(f"  {status} {field}: {display_value}")

        print("\n📧 Optional Contact Fields:")
        for field in optional_fields:
            value = profile.get(field)
            if value:
                print(f"  ✅ {field}: {value}")
            else:
                print(f"  ⚠️  {field}: Not found (may not be available)")

        # Validate data types
        print("\n🔍 Data Type Validation:")
        type_checks = {
            "full_name": str,
            "connections_count": int,
            "work_experience": list,
            "education": list,
            "skills": list,
        }

        for field, expected_type in type_checks.items():
            value = profile.get(field)
            if isinstance(value, expected_type):
                print(f"  ✅ {field}: {expected_type.__name__}")
            else:
                print(f"  ❌ {field}: Expected {expected_type.__name__}, got {type(value).__name__}")
    else:
        print(f"❌ Test failed: {result.get('error_message')}")


async def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("BRIGHTDATA PROFILE ENRICHMENT SERVICE - TEST SUITE")
    print("=" * 80)

    try:
        # Run tests sequentially
        await test_single_profile_enrichment()
        await test_invalid_url_handling()

        # Uncomment to test batch enrichment (costs more credits)
        # await test_batch_profile_enrichment()

        await test_field_extraction()

        print("\n" + "=" * 80)
        print("✅ ALL TESTS COMPLETED")
        print("=" * 80)

    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test suite failed with error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
