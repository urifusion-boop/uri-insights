"""
Social URL Helper - Intelligent URL detection and parsing

Detects and parses social media URLs to determine platform type
and extract relevant identifiers.
"""
import re
from typing import Optional, Dict, Any
from urllib.parse import urlparse


class SocialURLHelper:
    """Helper for detecting and parsing social media URLs"""

    @staticmethod
    def detect_url_type(url_or_handle: str) -> str:
        """
        Detect the type of social media URL/handle

        Args:
            url_or_handle: URL or handle string (e.g., "@user", "linkedin.com/in/user", etc.)

        Returns:
            One of: "linkedin", "twitter", "facebook", "instagram", "unknown"
        """
        if not url_or_handle:
            return "unknown"

        url_lower = url_or_handle.lower().strip()

        # LinkedIn patterns
        if "linkedin.com" in url_lower:
            return "linkedin"

        # Twitter/X patterns
        if "twitter.com" in url_lower or "x.com" in url_lower:
            return "twitter"

        # Handle @ mentions (assume Twitter)
        if url_lower.startswith("@"):
            return "twitter"

        # Facebook patterns
        if "facebook.com" in url_lower or "fb.com" in url_lower:
            return "facebook"

        # Instagram patterns
        if "instagram.com" in url_lower:
            return "instagram"

        return "unknown"

    @staticmethod
    def normalize_url(url_or_handle: str, url_type: Optional[str] = None) -> Optional[str]:
        """
        Normalize a social media URL or handle to a full URL

        Args:
            url_or_handle: URL or handle string
            url_type: Optional pre-detected type, if None will auto-detect

        Returns:
            Normalized full URL or None if unable to normalize
        """
        if not url_or_handle:
            return None

        url_str = url_or_handle.strip()

        # Auto-detect type if not provided
        if not url_type:
            url_type = SocialURLHelper.detect_url_type(url_str)

        # Already a full URL
        if url_str.startswith("http://") or url_str.startswith("https://"):
            return url_str

        # Twitter handle -> URL
        if url_type == "twitter":
            handle = url_str.replace("@", "").replace("twitter.com/", "").replace("x.com/", "")
            handle = handle.split("/")[0]  # Get first part before any slashes
            return f"https://twitter.com/{handle}"

        # LinkedIn partial URL -> full URL
        if url_type == "linkedin":
            if "/in/" in url_str or "/company/" in url_str:
                return f"https://www.linkedin.com{url_str}" if not url_str.startswith("linkedin.com") else f"https://{url_str}"

        # Can't normalize
        return url_str if "." in url_str else None

    @staticmethod
    def parse_social_handle(social_handle: Optional[str]) -> Dict[str, Optional[str]]:
        """
        Parse a social_handle field into separate platform URLs

        Args:
            social_handle: The social_handle string (could be LinkedIn URL, Twitter handle, etc.)

        Returns:
            Dictionary with keys: linkedin_url, twitter_url, facebook_url, instagram_url
        """
        result = {
            "linkedin_url": None,
            "twitter_url": None,
            "facebook_url": None,
            "instagram_url": None,
            "social_handle": social_handle  # Keep original
        }

        if not social_handle:
            return result

        # Detect URL type
        url_type = SocialURLHelper.detect_url_type(social_handle)

        # Normalize to full URL
        normalized_url = SocialURLHelper.normalize_url(social_handle, url_type)

        if not normalized_url:
            return result

        # Assign to appropriate field
        if url_type == "linkedin":
            result["linkedin_url"] = normalized_url
        elif url_type == "twitter":
            result["twitter_url"] = normalized_url
        elif url_type == "facebook":
            result["facebook_url"] = normalized_url
        elif url_type == "instagram":
            result["instagram_url"] = normalized_url

        return result

    @staticmethod
    def extract_linkedin_profile_id(linkedin_url: Optional[str]) -> Optional[str]:
        """
        Extract LinkedIn profile ID from URL

        Args:
            linkedin_url: LinkedIn URL

        Returns:
            Profile ID (e.g., "satyanadella") or None
        """
        if not linkedin_url:
            return None

        # Match /in/{profile_id}
        match = re.search(r'/in/([^/?#]+)', linkedin_url)
        if match:
            return match.group(1)

        return None

    @staticmethod
    def extract_twitter_handle(twitter_url: Optional[str]) -> Optional[str]:
        """
        Extract Twitter handle from URL or @mention

        Args:
            twitter_url: Twitter URL or @mention

        Returns:
            Handle without @ (e.g., "elonmusk") or None
        """
        if not twitter_url:
            return None

        # Remove @ if present
        handle = twitter_url.replace("@", "")

        # Extract from URL
        match = re.search(r'(?:twitter\.com|x\.com)/([^/?#]+)', handle)
        if match:
            return match.group(1)

        # Already just a handle
        if "/" not in handle and "." not in handle:
            return handle

        return None

    @staticmethod
    def is_valid_linkedin_url(url: str) -> bool:
        """Check if URL is a valid LinkedIn profile or company page"""
        if not url:
            return False
        return "linkedin.com" in url.lower() and ("/in/" in url or "/company/" in url)

    @staticmethod
    def is_valid_twitter_url(url: str) -> bool:
        """Check if URL is a valid Twitter/X profile"""
        if not url:
            return False
        return ("twitter.com" in url.lower() or "x.com" in url.lower()) and "/" in url
