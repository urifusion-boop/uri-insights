"""
HubSpot OAuth and API Integration Service
PRD Section 4.4: CRM Integration

Handles:
- OAuth 2.0 authentication flow
- Token refresh and management
- Fetching contacts and deals from HubSpot
- Identifying stalled deals and closed-lost opportunities
- Rate limiting to prevent API throttling
"""
import os
import httpx
import jwt
import secrets
from typing import Dict, List, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta
from app.utils.rate_limiter import get_hubspot_rate_limiter


class HubSpotService:
    """Service for HubSpot OAuth and API operations"""

    # OAuth Configuration
    CLIENT_ID = os.getenv("HUBSPOT_CLIENT_ID", "")
    CLIENT_SECRET = os.getenv("HUBSPOT_CLIENT_SECRET", "")
    REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "https://api.uricreative.com:8443/api/lazarus/crm/connect/hubspot/callback")
    AUTH_URL = "https://app.hubspot.com/oauth/authorize"
    TOKEN_URL = "https://api.hubapi.com/oauth/v1/token"
    JWT_SECRET = os.getenv("JWT_SECRET", "")  # Use same JWT secret as main app

    # API Configuration
    API_BASE = "https://api.hubapi.com"
    SCOPES = [
        "crm.objects.contacts.read",
        "crm.objects.deals.read",
        "crm.objects.companies.read",
    ]

    @staticmethod
    def generate_oauth_state(user_id: str) -> str:
        """
        Generate JWT-based OAuth state token for CSRF protection

        Args:
            user_id: User ID to encode in state

        Returns:
            Signed JWT token containing user_id and nonce
        """
        nonce = secrets.token_urlsafe(32)
        payload = {
            "user_id": user_id,
            "nonce": nonce,
            "exp": datetime.utcnow() + timedelta(minutes=10),  # Expire in 10 minutes
            "iat": datetime.utcnow(),
        }
        return jwt.encode(payload, HubSpotService.JWT_SECRET, algorithm="HS256")

    @staticmethod
    def verify_oauth_state(state_token: str) -> Optional[str]:
        """
        Verify and decode OAuth state token

        Args:
            state_token: JWT state token from callback

        Returns:
            user_id if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                state_token,
                HubSpotService.JWT_SECRET,
                algorithms=["HS256"]
            )
            return payload.get("user_id")
        except jwt.ExpiredSignatureError:
            print("OAuth state token expired")
            return None
        except jwt.InvalidTokenError:
            print("Invalid OAuth state token")
            return None

    @staticmethod
    def get_authorization_url(user_id: str) -> str:
        """
        Generate HubSpot OAuth authorization URL with secure state token

        Args:
            user_id: User ID to pass in state parameter

        Returns:
            Authorization URL for OAuth popup
        """
        scope = " ".join(HubSpotService.SCOPES)
        state_token = HubSpotService.generate_oauth_state(user_id)

        params = {
            "client_id": HubSpotService.CLIENT_ID,
            "redirect_uri": HubSpotService.REDIRECT_URI,
            "scope": scope,
            "state": state_token,  # JWT-based state for CSRF protection
        }

        # Build URL with query parameters
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{HubSpotService.AUTH_URL}?{query_string}"

    @staticmethod
    async def fetch_account_info(access_token: str) -> Dict[str, Any]:
        """
        Fetch HubSpot account information with rate limiting

        Args:
            access_token: HubSpot access token

        Returns:
            Account info with hub_id, hub_domain, portal_url
        """
        try:
            rate_limiter = get_hubspot_rate_limiter()
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient() as client:
                # Apply rate limiting before API call
                await rate_limiter.acquire()

                # Fetch account info from HubSpot API
                response = await client.get(
                    f"{HubSpotService.API_BASE}/account-info/v3/details",
                    headers=headers,
                )

                if response.status_code != 200:
                    return {}

                account_data = response.json()

                return {
                    "hub_id": account_data.get("portalId"),
                    "hub_domain": account_data.get("domain"),
                    "portal_url": f"https://app.hubspot.com/contacts/{account_data.get('portalId')}",
                    "account_name": account_data.get("companyName", ""),
                    "time_zone": account_data.get("timeZone", ""),
                }

        except Exception as e:
            print(f"Error fetching HubSpot account info: {str(e)}")
            return {}

    @staticmethod
    async def handle_oauth_callback(
        db: AsyncIOMotorDatabase, user_id: str, code: str
    ) -> Dict[str, Any]:
        """
        Handle OAuth callback - exchange code for access token and fetch account info

        Args:
            db: Database connection
            user_id: User ID from state parameter
            code: Authorization code from HubSpot

        Returns:
            Success status and message
        """
        try:
            # Exchange code for access token
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    HubSpotService.TOKEN_URL,
                    data={
                        "grant_type": "authorization_code",
                        "client_id": HubSpotService.CLIENT_ID,
                        "client_secret": HubSpotService.CLIENT_SECRET,
                        "redirect_uri": HubSpotService.REDIRECT_URI,
                        "code": code,
                    },
                )

                if response.status_code != 200:
                    return {
                        "success": False,
                        "message": f"Failed to exchange code for token: {response.text}",
                    }

                token_data = response.json()

            # Fetch account info
            account_info = await HubSpotService.fetch_account_info(token_data["access_token"])

            # Store connection in database
            from app.repository.CRMRepository import CRMRepository

            connection = {
                "user_id": user_id,
                "crm_type": "hubspot",
                "access_token": token_data["access_token"],
                "refresh_token": token_data["refresh_token"],
                "expires_in": token_data["expires_in"],
                "token_type": token_data["token_type"],
                "connected_at": datetime.utcnow(),
                "last_sync_at": None,
                "contacts_synced": 0,
                "companies_synced": 0,
                # Account info fields
                "hub_id": account_info.get("hub_id"),
                "hub_domain": account_info.get("hub_domain"),
                "portal_url": account_info.get("portal_url"),
                "account_name": account_info.get("account_name"),
                "time_zone": account_info.get("time_zone"),
                # Metadata
                "scopes": HubSpotService.SCOPES,
                "auth_type": "oauth2",
                "api_version": "v3",
                # Sync stats
                "total_syncs": 0,
                "successful_syncs": 0,
                "failed_syncs": 0,
                "avg_sync_duration_seconds": 0,
                "last_sync_duration_seconds": None,
            }

            await CRMRepository.save_crm_connection(db, user_id, connection)

            return {
                "success": True,
                "message": "HubSpot connected successfully",
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"OAuth callback failed: {str(e)}",
            }

    @staticmethod
    async def refresh_access_token(
        db: AsyncIOMotorDatabase, user_id: str, refresh_token: str
    ) -> Optional[str]:
        """
        Refresh HubSpot access token using refresh token

        Args:
            db: Database connection
            user_id: User ID
            refresh_token: Refresh token

        Returns:
            New access token or None if refresh failed
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    HubSpotService.TOKEN_URL,
                    data={
                        "grant_type": "refresh_token",
                        "client_id": HubSpotService.CLIENT_ID,
                        "client_secret": HubSpotService.CLIENT_SECRET,
                        "refresh_token": refresh_token,
                    },
                )

                if response.status_code != 200:
                    return None

                token_data = response.json()

            # Update stored tokens
            from app.repository.CRMRepository import CRMRepository

            await CRMRepository.update_crm_tokens(
                db,
                user_id,
                token_data["access_token"],
                token_data["refresh_token"],
                token_data["expires_in"],
            )

            return token_data["access_token"]

        except Exception:
            return None

    @staticmethod
    async def fetch_stalled_deals(
        db: AsyncIOMotorDatabase, user_id: str, access_token: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch stalled deals from HubSpot with pagination and rate limiting
        PRD: "Stalled" = No activity in 30+ days OR deal stage hasn't changed in 60+ days

        Args:
            db: Database connection
            user_id: User ID
            access_token: HubSpot access token

        Returns:
            List of stalled deals with contact information
        """
        try:
            rate_limiter = get_hubspot_rate_limiter()
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            all_deals = []
            cursor = None

            # Fetch ALL deals with pagination
            async with httpx.AsyncClient() as client:
                while True:
                    params = {
                        "properties": "dealname,dealstage,amount,closedate,notes_last_contacted,hs_lastmodifieddate",
                        "limit": 100,
                    }

                    if cursor:
                        params["after"] = cursor

                    # Apply rate limiting before API call
                    await rate_limiter.acquire()

                    deals_response = await client.get(
                        f"{HubSpotService.API_BASE}/crm/v3/objects/deals",
                        headers=headers,
                        params=params,
                    )

                    if deals_response.status_code != 200:
                        # Try to refresh token
                        from app.repository.CRMRepository import CRMRepository
                        connection = await CRMRepository.get_crm_connection(db, user_id)
                        new_token = await HubSpotService.refresh_access_token(
                            db, user_id, connection["refresh_token"]
                        )
                        if new_token:
                            headers["Authorization"] = f"Bearer {new_token}"
                            # Apply rate limiting before retry
                            await rate_limiter.acquire()
                            deals_response = await client.get(
                                f"{HubSpotService.API_BASE}/crm/v3/objects/deals",
                                headers=headers,
                                params=params,
                            )

                    deals_data = deals_response.json()
                    all_deals.extend(deals_data.get("results", []))

                    # Check for next page
                    paging = deals_data.get("paging")
                    if paging and paging.get("next"):
                        cursor = paging["next"]["after"]
                    else:
                        break  # No more pages

            # Filter stalled deals from ALL fetched deals
            stalled_deals = []
            now = datetime.utcnow()

            for deal in all_deals:
                properties = deal.get("properties", {})
                last_modified = properties.get("hs_lastmodifieddate")
                last_contacted = properties.get("notes_last_contacted")

                # Check if stalled (no activity in 30+ days)
                if last_modified or last_contacted:
                    last_activity = last_modified or last_contacted
                    try:
                        last_activity_date = datetime.fromisoformat(last_activity.replace("Z", "+00:00"))
                        days_since_activity = (now - last_activity_date).days

                        if days_since_activity >= 30:
                            stalled_deals.append({
                                "deal_id": deal["id"],
                                "deal_name": properties.get("dealname"),
                                "deal_stage": properties.get("dealstage"),
                                "amount": properties.get("amount"),
                                "days_stalled": days_since_activity,
                            })
                    except Exception:
                        continue

            return stalled_deals

        except Exception as e:
            print(f"Error fetching stalled deals: {str(e)}")
            return []

    @staticmethod
    async def fetch_closed_lost_deals(
        db: AsyncIOMotorDatabase, user_id: str, access_token: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch closed-lost deals from HubSpot with pagination and rate limiting
        PRD: Automatically monitor contacts from closed-lost opportunities

        Args:
            db: Database connection
            user_id: User ID
            access_token: HubSpot access token

        Returns:
            List of closed-lost deals with contact information
        """
        try:
            rate_limiter = get_hubspot_rate_limiter()
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            all_deals = []
            after_cursor = None

            # Fetch ALL closed-lost deals with pagination
            async with httpx.AsyncClient() as client:
                while True:
                    search_body = {
                        "filterGroups": [
                            {
                                "filters": [
                                    {
                                        "propertyName": "dealstage",
                                        "operator": "EQ",
                                        "value": "closedlost",
                                    }
                                ]
                            }
                        ],
                        "properties": ["dealname", "dealstage", "amount", "closedate", "associatedcompanyid"],
                        "limit": 100,
                    }

                    if after_cursor:
                        search_body["after"] = after_cursor

                    # Apply rate limiting before API call
                    await rate_limiter.acquire()

                    deals_response = await client.post(
                        f"{HubSpotService.API_BASE}/crm/v3/objects/deals/search",
                        headers=headers,
                        json=search_body,
                    )

                    if deals_response.status_code != 200:
                        # Try token refresh
                        from app.repository.CRMRepository import CRMRepository
                        connection = await CRMRepository.get_crm_connection(db, user_id)
                        new_token = await HubSpotService.refresh_access_token(
                            db, user_id, connection["refresh_token"]
                        )
                        if new_token:
                            headers["Authorization"] = f"Bearer {new_token}"
                            # Apply rate limiting before retry
                            await rate_limiter.acquire()
                            deals_response = await client.post(
                                f"{HubSpotService.API_BASE}/crm/v3/objects/deals/search",
                                headers=headers,
                                json=search_body,
                            )

                    deals_data = deals_response.json()
                    all_deals.extend(deals_data.get("results", []))

                    # Check for next page
                    paging = deals_data.get("paging")
                    if paging and paging.get("next"):
                        after_cursor = paging["next"]["after"]
                    else:
                        break  # No more pages

            return all_deals

        except Exception as e:
            print(f"Error fetching closed-lost deals: {str(e)}")
            return []

    @staticmethod
    async def fetch_contacts_from_deal(
        db: AsyncIOMotorDatabase, user_id: str, access_token: str, deal_id: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch contacts associated with a specific deal with rate limiting

        Args:
            db: Database connection
            user_id: User ID
            access_token: HubSpot access token
            deal_id: Deal ID

        Returns:
            List of contacts with name, email, company, job title
        """
        try:
            rate_limiter = get_hubspot_rate_limiter()
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            # Get associations
            async with httpx.AsyncClient() as client:
                # Apply rate limiting before API call
                await rate_limiter.acquire()

                associations_response = await client.get(
                    f"{HubSpotService.API_BASE}/crm/v3/objects/deals/{deal_id}/associations/contacts",
                    headers=headers,
                )

                if associations_response.status_code != 200:
                    return []

                associations = associations_response.json()
                contact_ids = [assoc["id"] for assoc in associations.get("results", [])]

                # Fetch contact details
                contacts = []
                for contact_id in contact_ids:
                    # Apply rate limiting before each contact fetch
                    await rate_limiter.acquire()

                    contact_response = await client.get(
                        f"{HubSpotService.API_BASE}/crm/v3/objects/contacts/{contact_id}",
                        headers=headers,
                        params={"properties": "firstname,lastname,email,phone,mobilephone,company,jobtitle"},
                    )

                    if contact_response.status_code == 200:
                        contact_data = contact_response.json()
                        properties = contact_data.get("properties", {})

                        # Field mapping with fallbacks (Priority 3)
                        phone = properties.get("phone") or properties.get("mobilephone") or ""

                        contacts.append({
                            "contact_id": contact_id,
                            "first_name": properties.get("firstname", ""),
                            "last_name": properties.get("lastname", ""),
                            "email": properties.get("email", ""),
                            "phone": phone,  # With fallback
                            "company": properties.get("company", ""),
                            "job_title": properties.get("jobtitle", ""),
                        })

                return contacts

        except Exception as e:
            print(f"Error fetching contacts from deal: {str(e)}")
            return []

    @staticmethod
    async def create_note_on_contact(
        db: AsyncIOMotorDatabase,
        user_id: str,
        access_token: str,
        contact_email: str,
        note_content: str
    ) -> Dict[str, Any]:
        """
        Create a note on a HubSpot contact
        PRD: "Syncs insights back to the CRM (notifications / notes)"

        Args:
            db: Database connection
            user_id: User ID
            access_token: HubSpot access token
            contact_email: Email of contact to add note to
            note_content: Note content (Lazarus alert details)

        Returns:
            Success status and message
        """
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            # First, find contact by email
            async with httpx.AsyncClient() as client:
                search_response = await client.post(
                    f"{HubSpotService.API_BASE}/crm/v3/objects/contacts/search",
                    headers=headers,
                    json={
                        "filterGroups": [{
                            "filters": [{
                                "propertyName": "email",
                                "operator": "EQ",
                                "value": contact_email
                            }]
                        }],
                        "properties": ["email"],
                        "limit": 1
                    }
                )

                if search_response.status_code != 200 or not search_response.json().get("results"):
                    return {
                        "success": False,
                        "message": f"Contact not found in HubSpot: {contact_email}"
                    }

                contact_id = search_response.json()["results"][0]["id"]

                # Create engagement (note) associated with contact
                note_response = await client.post(
                    f"{HubSpotService.API_BASE}/crm/v3/objects/notes",
                    headers=headers,
                    json={
                        "properties": {
                            "hs_note_body": note_content,
                            "hs_timestamp": datetime.utcnow().isoformat() + "Z"
                        },
                        "associations": [{
                            "to": {"id": contact_id},
                            "types": [{"associationCategory": "HUBSPOT_DEFINED", "associationTypeId": 202}]
                        }]
                    }
                )

                if note_response.status_code in [200, 201]:
                    return {
                        "success": True,
                        "message": "Note created in HubSpot"
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Failed to create note: {note_response.text}"
                    }

        except Exception as e:
            return {
                "success": False,
                "message": f"Error creating HubSpot note: {str(e)}"
            }
