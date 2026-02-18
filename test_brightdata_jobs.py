#!/usr/bin/env python3
"""
Quick test script for BrightDataLinkedInJobsService
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.BrightDataLinkedInJobsService import BrightDataLinkedInJobsService


async def test_fetch_jobs():
    """Test fetching jobs by keyword"""
    service = BrightDataLinkedInJobsService()

    print("=" * 80)
    print("🧪 Testing Bright Data LinkedIn Jobs Service")
    print("=" * 80)

    # Test 1: Basic keyword search
    print("\n📝 Test 1: Search for 'Python Developer' jobs in Lagos")
    result = await service.fetch_job_postings(
        search_query="Python Developer",
        location="Lagos",
        max_jobs=5,
        published_at="Past Month"
    )

    if result["success"]:
        print(f"✅ Success! Found {result['total_jobs']} jobs")
        for i, job in enumerate(result["jobs"][:3], 1):
            print(f"\n   Job {i}:")
            print(f"   Title: {job['title']}")
            print(f"   Company: {job['company']}")
            print(f"   Location: {job['location']}")
            print(f"   URL: {job['url'][:60]}...")
    else:
        print(f"❌ Failed: {result.get('error_message')}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(test_fetch_jobs())
