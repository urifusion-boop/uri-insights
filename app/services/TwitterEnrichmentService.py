"""
Twitter Enrichment Service for Lazarus Protocol

Handles Twitter profile enrichment using Bright Data API.
- Profile enrichment: Get profile data + 5 recent posts
- Activity monitoring: Get profile data + 20 recent posts for resurrection detection
"""

import os
import httpx
from typing import Optional, Dict, List, Any
from datetime import datetime


class TwitterEnrichmentService:
    """Service for enriching Twitter profiles using Bright Data"""

    BRIGHTDATA_API_URL = "https://api.brightdata.com/datasets/v3/scrape"
    BRIGHTDATA_DATASET_ID = "gd_lwxmeb2u1cniijd7t4"  # Twitter dataset
    BRIGHTDATA_API_KEY = os.getenv("BRIGHTDATA_API_KEY", "a3d28160-14ca-4c9a-842b-a505050241ff")

    @staticmethod
    def extract_twitter_handle(url_or_handle: str) -> Optional[str]:
        """
        Extract Twitter handle from URL or handle string

        Examples:
            https://twitter.com/elonmusk -> elonmusk
            https://x.com/elonmusk -> elonmusk
            @elonmusk -> elonmusk
            elonmusk -> elonmusk
        """
        if not url_or_handle:
            return None

        # Remove whitespace
        url_or_handle = url_or_handle.strip()

        # If it's a URL, extract handle
        if "twitter.com/" in url_or_handle or "x.com/" in url_or_handle:
            # Extract handle after last slash
            parts = url_or_handle.rstrip("/").split("/")
            handle = parts[-1]
            # Remove query params if any
            handle = handle.split("?")[0]
            return handle.lstrip("@")

        # If it starts with @, remove it
        if url_or_handle.startswith("@"):
            return url_or_handle[1:]

        # Otherwise assume it's already a clean handle
        return url_or_handle

    @staticmethod
    def build_twitter_url(handle: str) -> str:
        """Build full Twitter URL from handle"""
        clean_handle = TwitterEnrichmentService.extract_twitter_handle(handle)
        return f"https://x.com/{clean_handle}"

    @staticmethod
    async def enrich_profile(
        twitter_url_or_handle: str,
        max_posts: int = 5
    ) -> Optional[Dict[str, Any]]:
        """
        Enrich a single Twitter profile

        Args:
            twitter_url_or_handle: Twitter URL or handle
            max_posts: Number of recent posts to fetch (5 for enrichment, 20 for monitoring)

        Returns:
            Enriched profile data or None if failed
        """
        # Build full URL if needed
        if not twitter_url_or_handle.startswith("http"):
            twitter_url = TwitterEnrichmentService.build_twitter_url(twitter_url_or_handle)
        else:
            twitter_url = twitter_url_or_handle

        # Call Bright Data API
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    TwitterEnrichmentService.BRIGHTDATA_API_URL,
                    params={
                        "dataset_id": TwitterEnrichmentService.BRIGHTDATA_DATASET_ID,
                        "notify": "false",
                        "include_errors": "true"
                    },
                    headers={
                        "Authorization": f"Bearer {TwitterEnrichmentService.BRIGHTDATA_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "input": [{
                            "url": twitter_url,
                            "max_number_of_posts": max_posts
                        }]
                    }
                )

                if response.status_code == 200:
                    # Parse response (returns NDJSON - newline delimited JSON)
                    lines = response.text.strip().split("\n")
                    if lines:
                        import json
                        profile_data = json.loads(lines[0])  # First line is the profile
                        return profile_data
                else:
                    print(f"Bright Data API error: {response.status_code} - {response.text}")
                    return None

            except Exception as e:
                print(f"Error enriching Twitter profile: {e}")
                return None

    @staticmethod
    async def enrich_multiple_profiles(
        twitter_urls: List[str],
        max_posts: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Enrich multiple Twitter profiles in batch (for monitoring)

        Args:
            twitter_urls: List of Twitter URLs
            max_posts: Number of recent posts per profile

        Returns:
            List of enriched profile data
        """
        # Build batch request
        input_data = [
            {"url": url, "max_number_of_posts": max_posts}
            for url in twitter_urls
        ]

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    TwitterEnrichmentService.BRIGHTDATA_API_URL,
                    params={
                        "dataset_id": TwitterEnrichmentService.BRIGHTDATA_DATASET_ID,
                        "notify": "false",
                        "include_errors": "true"
                    },
                    headers={
                        "Authorization": f"Bearer {TwitterEnrichmentService.BRIGHTDATA_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={"input": input_data}
                )

                if response.status_code == 200:
                    # Parse NDJSON response
                    lines = response.text.strip().split("\n")
                    import json
                    profiles = [json.loads(line) for line in lines if line.strip()]
                    return profiles
                else:
                    print(f"Bright Data batch API error: {response.status_code} - {response.text}")
                    return []

            except Exception as e:
                print(f"Error enriching multiple Twitter profiles: {e}")
                return []

    @staticmethod
    def transform_to_focus_contact_data(profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform Bright Data Twitter profile to FocusContact format

        Args:
            profile: Raw profile data from Bright Data

        Returns:
            Transformed data ready for FocusContact creation
        """
        posts = profile.get("posts") or []  # Handle None or missing posts

        return {
            "name": profile.get("profile_name", ""),
            "twitter_handle": profile.get("id", ""),
            "twitter_id": profile.get("x_id", ""),
            "twitter_url": profile.get("url", ""),
            "profile_photo": profile.get("profile_image_link", ""),
            "about": profile.get("biography", ""),
            "location": profile.get("location", ""),

            # Twitter enrichment data
            "twitter_data": {
                "followers": profile.get("followers", 0),
                "following": profile.get("following", 0),
                "verified": profile.get("is_verified", False),
                "posts_count": profile.get("posts_count", 0),
                "joined_date": profile.get("date_joined", None),
                "banner_image": profile.get("banner_image", None),
                "website": profile.get("external_link", None),

                # Enrichment snapshot
                "enrichment_snapshot": {
                    "last_post_id": posts[0]["post_id"] if posts and len(posts) > 0 else None,
                    "posts": posts[:5],  # Store first 5 posts
                    "enriched_at": datetime.utcnow().isoformat()
                },

                # Activity tracking
                "last_scanned": None,
                "last_activity_detected": None,
                "new_posts_since_last_scan": 0
            },

            "enriched_at": datetime.utcnow(),
            "enrichment_status": "completed"
        }

    @staticmethod
    def detect_new_activity(
        profile: Dict[str, Any],
        last_known_post_id: Optional[str]
    ) -> Dict[str, Any]:
        """
        Detect new Twitter activity since last scan

        Args:
            profile: Fresh profile data from Bright Data
            last_known_post_id: Last post ID from previous scan

        Returns:
            Activity detection result with new posts
        """
        posts = profile.get("posts", [])

        if not posts:
            return {
                "has_new_activity": False,
                "new_posts": [],
                "new_posts_count": 0
            }

        # If no last known post, all posts are new
        if not last_known_post_id:
            return {
                "has_new_activity": True,
                "new_posts": posts,
                "new_posts_count": len(posts)
            }

        # Find new posts (posts before last_known_post_id)
        new_posts = []
        for post in posts:
            if post["post_id"] == last_known_post_id:
                break  # Found last known post, stop
            new_posts.append(post)

        return {
            "has_new_activity": len(new_posts) > 0,
            "new_posts": new_posts,
            "new_posts_count": len(new_posts),
            "latest_post": new_posts[0] if new_posts else None
        }
