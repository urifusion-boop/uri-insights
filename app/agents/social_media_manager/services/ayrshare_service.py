# app/agents/social_media_manager/services/ayrshare_service.py

import httpx
import json
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
from app.core.config import settings
from app.domain.responses.uri_response import UriResponse


class AyrshareService:
    """
    Ayrshare integration service for multi-platform social media publishing
    
    This service handles:
    - OAuth URL generation for platform connections
    - Content publishing to multiple platforms simultaneously  
    - Analytics retrieval from published posts
    - Profile management for users
    
    Integrates with existing URI infrastructure:
    - Uses existing UriResponse format
    - Follows URI service patterns
    - Integrates with existing settings and config
    """
    
    def __init__(self):
        # Use your existing settings pattern
        self.api_key = getattr(settings, 'AYRSHARE_API_KEY', None)
        if not self.api_key:
            raise ValueError("AYRSHARE_API_KEY not found in settings. Please add to .env file")
            
        self.base_url = "https://app.ayrshare.com/api"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.timeout = 30.0
    
    async def create_profile(self, user_id: str) -> Dict[str, str]:
        """
        Create an Ayrshare profile for the user
        Each URI user gets their own Ayrshare profile to manage their social connections
        NOTE: Requires Ayrshare Business Plan. In dev mode a mock profile key is returned.
        """
        if self.is_local_development():
            mock_key = f"mock_profile_{user_id}"
            print(f"🔧 LOCAL DEV: Mock Ayrshare profile created for user {user_id}: {mock_key}")
            return UriResponse.get_single_data_response(
                "ayrshare_profile",
                {"profile_key": mock_key}
            )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/profiles",
                    headers=self.headers,
                    json={"title": f"URI_User_{user_id}"}
                )

                if response.status_code == 200:
                    data = response.json()
                    return UriResponse.get_single_data_response(
                        "ayrshare_profile",
                        {"profile_key": data['profileKey']}
                    )
                else:
                    error_msg = f"Failed to create Ayrshare profile: {response.text}"
                    print(error_msg)
                    return UriResponse.error_response(error_msg, code=response.status_code)

        except httpx.TimeoutException:
            return UriResponse.error_response("Ayrshare API timeout", code=408)
        except Exception as e:
            return UriResponse.error_response(f"Ayrshare profile creation failed: {str(e)}", code=500)
    
    async def get_auth_urls(self, profile_key: str, platforms: List[str]) -> Dict[str, str]:
        """
        Get OAuth URLs for connecting social platforms
        Returns a dictionary with platform names as keys and auth URLs as values
        NOTE: Requires Ayrshare Business Plan. In dev mode mock URLs are returned.
        """
        # Platform mapping - Ayrshare uses these exact names
        platform_mapping = {
            'twitter': 'twitter',
            'linkedin': 'linkedin',
            'facebook': 'facebook',
            'instagram': 'instagram',
            'tiktok': 'tiktok'
        }

        if self.is_local_development():
            auth_urls = {
                p: f"https://mock-oauth.ayrshare.com/connect/{p}?profile={profile_key}"
                for p in platforms
                if p in platform_mapping
            }
            print(f"🔧 LOCAL DEV: Mock auth URLs generated for {platforms}")
            return UriResponse.get_single_data_response("auth_urls", auth_urls)

        auth_urls = {}

        try:
            for platform in platforms:
                if platform not in platform_mapping:
                    print(f"Unsupported platform: {platform}")
                    continue

                ayrshare_platform = platform_mapping[platform]

                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(
                        f"{self.base_url}/profiles/{profile_key}/generateAuthURL",
                        headers=self.headers,
                        params={"platform": ayrshare_platform}
                    )

                    if response.status_code == 200:
                        data = response.json()
                        auth_urls[platform] = data['url']
                    else:
                        print(f"Failed to get auth URL for {platform}: {response.text}")

            return UriResponse.get_single_data_response("auth_urls", auth_urls)

        except Exception as e:
            return UriResponse.error_response(f"Failed to generate auth URLs: {str(e)}", code=500)
    
    async def publish_content(
        self, 
        profile_key: str,
        content: str,
        platforms: List[str],
        media_urls: Optional[List[str]] = None,
        schedule_date: Optional[datetime] = None,
        hashtags: Optional[List[str]] = None
    ) -> Dict:
        """
        Publish content to multiple platforms simultaneously
        
        Args:
            profile_key: Ayrshare profile key for the user
            content: Text content to publish
            platforms: List of platforms to publish to
            media_urls: Optional list of image/video URLs to attach
            schedule_date: Optional datetime to schedule post
            hashtags: Optional list of hashtags to append
        """
        
        # Check for local development mode (uses your existing pattern)
        if self.is_local_development():
            return await self.mock_publish_for_development(content, platforms)
        
        try:
            # Prepare the post content
            final_content = content
            if hashtags:
                hashtag_string = " " + " ".join([f"#{tag.strip('#')}" for tag in hashtags])
                final_content += hashtag_string
            
            payload = {
                "post": final_content,
                "platforms": platforms,
                "profileKey": profile_key
            }
            
            # Add media if provided
            if media_urls:
                payload["mediaUrls"] = media_urls
                
            # Add scheduling if provided
            if schedule_date:
                payload["scheduleDate"] = schedule_date.isoformat()
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/post",
                    headers=self.headers,
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return UriResponse.get_single_data_response("publish_result", {
                        "success": True,
                        "post_id": data.get('id'),
                        "platforms": platforms,
                        "scheduled": schedule_date is not None,
                        "schedule_date": schedule_date.isoformat() if schedule_date else None,
                        "ayrshare_response": data
                    })
                else:
                    error_data = response.json() if response.status_code != 500 else {"error": response.text}
                    return UriResponse.error_response(
                        f"Publishing failed: {error_data.get('error', 'Unknown error')}", 
                        code=response.status_code
                    )
                    
        except Exception as e:
            return UriResponse.error_response(f"Content publishing failed: {str(e)}", code=500)
    
    async def get_post_analytics(self, post_id: str, profile_key: str) -> Dict:
        """
        Get analytics for a published post
        Returns engagement metrics from all platforms where the post was published
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/analytics/post/{post_id}",
                    headers=self.headers,
                    params={"profileKey": profile_key}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Process the analytics data
                    analytics_summary = {
                        "total_views": 0,
                        "total_likes": 0,
                        "total_shares": 0,
                        "total_comments": 0,
                        "total_clicks": 0,
                        "platforms": {},
                        "last_updated": datetime.utcnow().isoformat()
                    }
                    
                    # Aggregate data from all platforms
                    for platform_data in data.get('platforms', []):
                        platform = platform_data.get('platform')
                        stats = platform_data.get('analytics', {})
                        
                        analytics_summary["total_views"] += stats.get('views', 0)
                        analytics_summary["total_likes"] += stats.get('likes', 0)
                        analytics_summary["total_shares"] += stats.get('shares', 0)
                        analytics_summary["total_comments"] += stats.get('comments', 0)
                        analytics_summary["total_clicks"] += stats.get('clicks', 0)
                        
                        analytics_summary["platforms"][platform] = stats
                    
                    # Calculate engagement rate
                    total_impressions = analytics_summary["total_views"]
                    total_engagement = (
                        analytics_summary["total_likes"] + 
                        analytics_summary["total_shares"] + 
                        analytics_summary["total_comments"] + 
                        analytics_summary["total_clicks"]
                    )
                    
                    if total_impressions > 0:
                        analytics_summary["engagement_rate"] = round(total_engagement / total_impressions, 4)
                    else:
                        analytics_summary["engagement_rate"] = 0
                    
                    return UriResponse.get_single_data_response("analytics", analytics_summary)
                else:
                    return UriResponse.error_response(
                        f"Failed to get analytics: {response.text}", 
                        code=response.status_code
                    )
                    
        except Exception as e:
            return UriResponse.error_response(f"Analytics retrieval failed: {str(e)}", code=500)
    
    async def verify_connection(self, profile_key: str, platform: str) -> bool:
        """
        Verify that a platform connection is still valid
        Used to check if OAuth tokens are still working
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/profiles/{profile_key}/platforms",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    connected_platforms = [p.get('platform') for p in data.get('platforms', [])]
                    return platform in connected_platforms
                else:
                    return False
                    
        except Exception as e:
            print(f"Connection verification failed: {str(e)}")
            return False
    
    async def get_connected_platforms(self, profile_key: str) -> List[str]:
        """
        Get list of platforms currently connected for a profile
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/profiles/{profile_key}/platforms",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    platforms = []
                    
                    for platform_data in data.get('platforms', []):
                        platform_info = {
                            'platform': platform_data.get('platform'),
                            'username': platform_data.get('username'),
                            'connected_at': platform_data.get('connectedAt'),
                            'status': 'active' if platform_data.get('active') else 'inactive'
                        }
                        platforms.append(platform_info)
                    
                    return UriResponse.get_single_data_response("connected_platforms", platforms)
                else:
                    return UriResponse.error_response(f"Failed to get platforms: {response.text}")
                    
        except Exception as e:
            return UriResponse.error_response(f"Platform retrieval failed: {str(e)}")
    
    @staticmethod
    def is_local_development() -> bool:
        """
        Check if running in local development mode
        Uses the same pattern as your existing services
        """
        import os
        local_dev_mode = os.getenv("LOCAL_DEV_MODE", "").lower() in ["true", "1", "yes"]
        env_type = os.getenv("ENV", "").lower()
        dev_env = os.getenv("DEV_ENV", "").lower()
        
        return (
            local_dev_mode or 
            env_type == "development" or 
            dev_env == "development"
        )
    
    async def mock_publish_for_development(self, content: str, platforms: List[str]) -> Dict:
        """
        Mock publishing for development/testing
        Returns fake success response without actually publishing
        Follows your existing local dev pattern
        """
        print(f"🔧 LOCAL DEV: Mock publishing to {platforms}")
        print(f"Content: {content[:100]}...")
        
        mock_response = {
            "success": True,
            "post_id": f"mock_post_{int(datetime.now().timestamp())}",
            "platforms": platforms,
            "scheduled": False,
            "schedule_date": None,
            "ayrshare_response": {
                "id": f"mock_post_{int(datetime.now().timestamp())}",
                "status": "success",
                "platforms": {platform: {"status": "success", "postId": f"mock_{platform}_123"} for platform in platforms}
            }
        }
        
        return UriResponse.get_single_data_response("publish_result", mock_response)