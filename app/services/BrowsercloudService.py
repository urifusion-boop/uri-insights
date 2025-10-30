import httpx
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio
from app.core.config import settings
from app.domain.schemas.browsercloud_schema import (
    BrowsercloudTaskCreate,
    BrowsercloudTaskResponse,
    BrowsercloudTaskStatus,
    BrowsercloudSocialPost,
)


class BrowsercloudService:
    """Service for interacting with Browsercloud API for real-time social media monitoring."""

    def __init__(self):
        self.api_key = settings.BROWSERCLOUD_API_KEY
        self.base_url = settings.BROWSERCLOUD_API_URL
        self.webhook_secret = settings.BROWSERCLOUD_WEBHOOK_SECRET
        self.max_concurrent_tasks = settings.BROWSERCLOUD_MAX_CONCURRENT_TASKS
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def _make_request(
        self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to Browsercloud API."""
        from app.core.config.browsercloud_platform_config import BrowsercloudPlatformConfig
        
        url = f"{self.base_url}/{endpoint}"
        rate_limit_config = BrowsercloudPlatformConfig.get_rate_limit_config()
        retries = 0
        
        while retries < rate_limit_config["max_retries"]:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.request(
                        method,
                        url,
                        headers=self.headers,
                        json=data,
                        timeout=30.0
                    )
                    
                    if response.status_code == 429:  # Too Many Requests
                        retry_after = int(response.headers.get("Retry-After", rate_limit_config["retry_after"]))
                        await asyncio.sleep(retry_after)
                        retries += 1
                        continue
                        
                    response.raise_for_status()
                    return response.json()
                    
            except httpx.TimeoutException:
                if retries < rate_limit_config["max_retries"] - 1:
                    await asyncio.sleep(rate_limit_config["retry_after"])
                    retries += 1
                    continue
                raise
                
            except Exception as e:
                if retries < rate_limit_config["max_retries"] - 1:
                    await asyncio.sleep(rate_limit_config["retry_after"])
                    retries += 1
                    continue
                raise
                
        raise Exception(f"Max retries ({rate_limit_config['max_retries']}) exceeded")

    async def create_monitoring_task(self, task: BrowsercloudTaskCreate) -> BrowsercloudTaskResponse:
        """Create a new social media monitoring task."""
        response = await self._make_request(
            "POST",
            "tasks/create",
            data=task.dict()
        )
        return BrowsercloudTaskResponse(**response)

    async def get_task_status(self, task_id: str) -> BrowsercloudTaskResponse:
        """Get the status and results of a monitoring task."""
        response = await self._make_request("GET", f"tasks/{task_id}")
        return BrowsercloudTaskResponse(**response)

    async def stop_task(self, task_id: str) -> bool:
        """Stop a running monitoring task."""
        try:
            await self._make_request("POST", f"tasks/{task_id}/stop")
            return True
        except httpx.HTTPError:
            return False

    async def validate_webhook_signature(self, signature: str, payload: bytes) -> bool:
        """Validate the webhook signature from Browsercloud."""
        import hmac
        import hashlib
        from app.core.config.browsercloud_platform_config import BrowsercloudPlatformConfig

        webhook_config = BrowsercloudPlatformConfig.get_webhook_config()
        
        # Check payload size
        if len(payload) > webhook_config["max_payload_size"]:
            raise ValueError("Webhook payload exceeds maximum size limit")

        # Validate signature
        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)

    @staticmethod
    def process_social_post(post_data: dict) -> BrowsercloudSocialPost:
        """Process and validate a social media post from Browsercloud."""
        return BrowsercloudSocialPost(**post_data)

    async def handle_webhook_payload(
        self, payload: Dict[str, Any], signature: str
    ) -> List[BrowsercloudSocialPost]:
        """Handle incoming webhook payload from Browsercloud."""
        if not await self.validate_webhook_signature(signature, str(payload).encode()):
            raise ValueError("Invalid webhook signature")

        posts = []
        for post_data in payload.get("results", []):
            try:
                post = self.process_social_post(post_data)
                posts.append(post)
            except Exception as e:
                print(f"Error processing post: {e}")
                continue

        return posts

    async def start_platform_monitoring(
        self,
        keywords: List[str],
        buying_signals: List[str],
        excluded_keywords: Optional[List[str]] = None,
        location: Optional[str] = None,
        webhook_url: Optional[str] = None,
    ) -> List[BrowsercloudTaskResponse]:
        """
        Start monitoring tasks for all configured platforms.
        Returns list of created task responses.
        """
        from app.domain.schemas.browsercloud_schema import BrowsercloudPlatformEnum
        from app.core.config.browsercloud_platform_config import BrowsercloudPlatformConfig

        if not webhook_url:
            webhook_url = f"{settings.URI_BACKEND_BASE_URL}/webhooks/browsercloud"

        tasks = []
        for platform in BrowsercloudPlatformEnum:
            # Get platform-specific query configuration
            query_config = BrowsercloudPlatformConfig.get_platform_specific_query(
                platform=platform,
                keywords=keywords,
                buying_signals=buying_signals,
                excluded_keywords=excluded_keywords,
                location=location
            )
            
            # Create task with platform-specific configuration
            task = BrowsercloudTaskCreate(
                platform=platform,
                keywords=query_config["keywords"],
                buying_signals=query_config["buying_signals"],
                excluded_keywords=query_config["excluded_keywords"],
                location=query_config["location"],
                webhook_url=webhook_url,
            )
            tasks.append(self.create_monitoring_task(task))

        return await asyncio.gather(*tasks)