import httpx
from typing import Dict, List
from urllib.parse import urlencode

from app.core.config import settings

FACEBOOK_OAUTH_URL = "https://www.facebook.com/dialog/oauth"
_GRAPH = f"https://graph.facebook.com/{settings.FACEBOOK_API_VERSION}"

# Permissions needed for page publishing and basic analytics
REQUIRED_SCOPES = ",".join([
    "pages_manage_posts",
    "pages_read_engagement",
    "pages_show_list",
    "read_insights",
])


class FacebookOAuthService:

    @staticmethod
    def build_oauth_url(redirect_uri: str, state: str) -> str:
        """Build the Facebook OAuth authorization URL to redirect the user to."""
        params = {
            "client_id": settings.META_APP_ID,
            "redirect_uri": redirect_uri,
            "scope": REQUIRED_SCOPES,
            "response_type": "code",
            "state": state,
        }
        return f"{FACEBOOK_OAUTH_URL}?{urlencode(params)}"

    @staticmethod
    async def exchange_code_for_token(code: str, redirect_uri: str) -> Dict:
        """
        Exchange the authorization code for a short-lived user access token.
        Returns the full token response dict (includes access_token, token_type).
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{_GRAPH}/oauth/access_token",
                params={
                    "client_id": settings.META_APP_ID,
                    "client_secret": settings.META_APP_SECRET,
                    "redirect_uri": redirect_uri,
                    "code": code,
                },
            )
            response.raise_for_status()
            return response.json()

    @staticmethod
    async def extend_user_token(short_lived_token: str) -> str:
        """
        Exchange a short-lived user token for a long-lived one (~60 days).
        Returns just the access_token string.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{_GRAPH}/oauth/access_token",
                params={
                    "grant_type": "fb_exchange_token",
                    "client_id": settings.META_APP_ID,
                    "client_secret": settings.META_APP_SECRET,
                    "fb_exchange_token": short_lived_token,
                },
            )
            response.raise_for_status()
            return response.json()["access_token"]

    @staticmethod
    async def get_user_pages(user_access_token: str) -> List[Dict]:
        """
        Return the Facebook Pages managed by this user.
        Each page dict includes id, name, access_token (page-level), category.
        Page-level tokens derived from a long-lived user token never expire.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{_GRAPH}/me/accounts",
                params={
                    "fields": "id,name,access_token,category,fan_count",
                    "access_token": user_access_token,
                },
            )
            response.raise_for_status()
            return response.json().get("data", [])

    @staticmethod
    async def verify_page_token(page_id: str, page_access_token: str) -> bool:
        """Return True if the stored page access token is still valid."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{_GRAPH}/{page_id}",
                    params={
                        "fields": "id,name",
                        "access_token": page_access_token,
                    },
                )
                return response.status_code == 200
        except Exception:
            return False
