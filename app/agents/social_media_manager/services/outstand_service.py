import httpx
from typing import List, Optional, Dict, Any
from app.core.config import settings

OUTSTAND_BASE_URL = "https://api.outstand.so"

# Maps our internal platform names → Outstand network identifiers
PLATFORM_TO_NETWORK: Dict[str, str] = {
    "facebook":       "facebook",
    "instagram":      "instagram",
    "linkedin":       "linkedin",
    "twitter":        "x",
    "x":              "x",
    "tiktok":         "tiktok",
    "youtube":        "youtube",
    "pinterest":      "pinterest",
    "threads":        "threads",
    "bluesky":        "bluesky",
    "google_business": "google_business",
}

SUPPORTED_PLATFORMS = set(PLATFORM_TO_NETWORK.keys())


class OutstandService:
    """Thin async wrapper around the Outstand REST API."""

    def __init__(self):
        self.api_key = settings.OUTSTAND_API_KEY
        self.base_url = OUTSTAND_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        self.timeout = 30.0

    # -------------------------------------------------------------------------
    # Social network configuration (one-time admin setup, not per-user)
    # -------------------------------------------------------------------------

    async def configure_network(
        self,
        network: str,
        client_key: str,
        client_secret: str,
    ) -> Dict[str, Any]:
        """
        Register platform OAuth credentials with Outstand (BYOK).
        Called once per platform during initial setup — not per user.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/v1/social-networks",
                headers=self.headers,
                json={"network": network, "client_key": client_key, "client_secret": client_secret},
            )
            resp.raise_for_status()
            return resp.json()

    # -------------------------------------------------------------------------
    # Per-user OAuth flow
    # -------------------------------------------------------------------------

    async def get_auth_url(
        self,
        network: str,
        tenant_id: str,
        redirect_uri: str,
    ) -> str:
        """
        Get the OAuth URL for a user to connect a social account.
        tenant_id = URI user_id, used to associate the account with the user.
        Returns the auth_url string.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/v1/social-networks/{network}/auth-url",
                headers=self.headers,
                json={"tenant_id": tenant_id, "redirect_uri": redirect_uri},
            )
            resp.raise_for_status()
            data = resp.json()
            return data["data"]["auth_url"]

    async def get_pending_connection(self, session_token: str) -> Dict[str, Any]:
        """
        After OAuth redirect, retrieve the available pages/accounts the user can connect.
        Returns { network, expiresAt, availablePages: [{id, type, name, username, profilePictureUrl}] }
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                f"{self.base_url}/v1/social-accounts/pending/{session_token}",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    async def finalize_connection(
        self,
        session_token: str,
        selected_page_ids: List[str],
    ) -> Dict[str, Any]:
        """
        Complete the OAuth flow by selecting which pages/accounts to connect.
        Returns the created social account records.
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/v1/social-accounts/pending/{session_token}/finalize",
                headers=self.headers,
                json={"selectedPageIds": selected_page_ids},
            )
            resp.raise_for_status()
            return resp.json()

    # -------------------------------------------------------------------------
    # Account management
    # -------------------------------------------------------------------------

    async def list_accounts(
        self,
        tenant_id: str,
        network: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        List all social accounts connected by a specific user (tenant_id = user_id).
        """
        params: Dict[str, Any] = {"tenantId": tenant_id, "limit": limit}
        if network:
            params["network"] = network

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(
                f"{self.base_url}/v1/social-accounts",
                headers=self.headers,
                params=params,
            )
            resp.raise_for_status()
            return resp.json()

    async def delete_account(self, outstand_account_id: str) -> Dict[str, Any]:
        """Permanently disconnect a social account from Outstand."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.delete(
                f"{self.base_url}/v1/social-accounts/{outstand_account_id}",
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    # -------------------------------------------------------------------------
    # Publishing
    # -------------------------------------------------------------------------

    async def publish_post(
        self,
        outstand_account_ids: List[str],
        content: str,
        scheduled_at: Optional[str] = None,
        media_urls: Optional[List[str]] = None,
        tweets: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Publish content to one or more connected accounts.
        outstand_account_ids: list of Outstand social account IDs (not platform names).
        scheduled_at: ISO 8601 datetime string if scheduling.
        media_urls: optional list of publicly accessible image/video URLs (attached to first container).
        tweets: optional list of tweet strings for X/Twitter threads — each becomes its own container.
        """
        # For X/Twitter threads, each tweet is its own container.
        # For all other platforms (or single tweets), use one container.
        if tweets and len(tweets) > 1:
            containers = [{"content": t} for t in tweets]
            # Attach media to the first tweet only
            if media_urls:
                containers[0]["media"] = [{"url": u} for u in media_urls]
        else:
            container: Dict[str, Any] = {"content": content}
            if media_urls:
                container["media"] = [{"url": u} for u in media_urls]
            containers = [container]

        payload: Dict[str, Any] = {
            "accounts": outstand_account_ids,
            "containers": containers,
        }
        if scheduled_at:
            payload["scheduledAt"] = scheduled_at

        print(f"📡 Outstand POST /v1/posts/ payload keys={list(payload.keys())} containers={len(containers)} media={media_urls}")
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/v1/posts/",
                headers=self.headers,
                json=payload,
            )
            print(f"📡 Outstand response status: {resp.status_code} body: {resp.text[:500]}")
            resp.raise_for_status()
            return resp.json()
