"""
HubSpot OAuth and API Integration Service
PRD Section 4.4: CRM Integration

Handles:
- OAuth 2.0 authentication flow
- Token refresh and management
- Fetching contacts and deals from HubSpot
- Identifying stalled deals and closed-lost opportunities
"""
import os
import httpx
from typing import Dict, List, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime


class HubSpotService:
    """Service for HubSpot OAuth and API operations"""

    # OAuth Configuration
    CLIENT_ID = os.getenv("HUBSPOT_CLIENT_ID", "")
    CLIENT_SECRET = os.getenv("HUBSPOT_CLIENT_SECRET", "")
    REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "https://api.uricreative.com:8443/api/lazarus/crm/connect/hubspot/callback")
    AUTH_URL = "https://app.hubspot.com/oauth/authorize"
    TOKEN_URL = "https://api.hubapi.com/oauth/v1/token"

    # API Configuration
    API_BASE = "https://api.hubapi.com"
    SCOPES = [
        "crm.objects.contacts.read",
        "crm.objects.deals.read",
        "crm.objects.companies.read",
    ]

    @staticmethod
    def get_authorization_url(user_id: str) -> str:
        """
        Generate HubSpot OAuth authorization URL

        Args:
            user_id: User ID to pass in state parameter

        Returns:
            Authorization URL for OAuth popup
        """
        scope = " ".join(HubSpotService.SCOPES)
        params = {
            "client_id": HubSpotService.CLIENT_ID,
            "redirect_uri": HubSpotService.REDIRECT_URI,
            "scope": scope,
            "state": user_id,  # Pass user_id to retrieve in callback
        }

        # Build URL with query parameters
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{HubSpotService.AUTH_URL}?{query_string}"

    @staticmethod
    async def handle_oauth_callback(
        db: AsyncIOMotorDatabase, user_id: str, code: str
    ) -> Dict[str, Any]:
        """
        Handle OAuth callback - exchange code for access token

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
        Fetch stalled deals from HubSpot
        PRD: "Stalled" = No activity in 30+ days OR deal stage hasn't changed in 60+ days

        Args:
            db: Database connection
            user_id: User ID
            access_token: HubSpot access token

        Returns:
            List of stalled deals with contact information
        """
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            # Fetch deals with specific properties
            async with httpx.AsyncClient() as client:
                # Get deals
                deals_response = await client.get(
                    f"{HubSpotService.API_BASE}/crm/v3/objects/deals",
                    headers=headers,
                    params={
                        "properties": "dealname,dealstage,amount,closedate,notes_last_contacted,hs_lastmodifieddate",
                        "limit": 100,
                    },
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
                        deals_response = await client.get(
                            f"{HubSpotService.API_BASE}/crm/v3/objects/deals",
                            headers=headers,
                            params={
                                "properties": "dealname,dealstage,amount,closedate,notes_last_contacted,hs_lastmodifieddate",
                                "limit": 100,
                            },
                        )

                deals_data = deals_response.json()

            # Filter stalled deals
            stalled_deals = []
            now = datetime.utcnow()

            for deal in deals_data.get("results", []):
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
        Fetch closed-lost deals from HubSpot
        PRD: Automatically monitor contacts from closed-lost opportunities

        Args:
            db: Database connection
            user_id: User ID
            access_token: HubSpot access token

        Returns:
            List of closed-lost deals with contact information
        """
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            # Fetch deals with dealstage = "closedlost"
            async with httpx.AsyncClient() as client:
                deals_response = await client.post(
                    f"{HubSpotService.API_BASE}/crm/v3/objects/deals/search",
                    headers=headers,
                    json={
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
                    },
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
                        deals_response = await client.post(
                            f"{HubSpotService.API_BASE}/crm/v3/objects/deals/search",
                            headers=headers,
                            json={
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
                            },
                        )

                deals_data = deals_response.json()

            return deals_data.get("results", [])

        except Exception as e:
            print(f"Error fetching closed-lost deals: {str(e)}")
            return []

    @staticmethod
    async def fetch_contacts_from_deal(
        db: AsyncIOMotorDatabase, user_id: str, access_token: str, deal_id: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch contacts associated with a specific deal

        Args:
            db: Database connection
            user_id: User ID
            access_token: HubSpot access token
            deal_id: Deal ID

        Returns:
            List of contacts with name, email, company, job title
        """
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            # Get associations
            async with httpx.AsyncClient() as client:
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
                    contact_response = await client.get(
                        f"{HubSpotService.API_BASE}/crm/v3/objects/contacts/{contact_id}",
                        headers=headers,
                        params={"properties": "firstname,lastname,email,company,jobtitle"},
                    )

                    if contact_response.status_code == 200:
                        contact_data = contact_response.json()
                        properties = contact_data.get("properties", {})
                        contacts.append({
                            "contact_id": contact_id,
                            "first_name": properties.get("firstname", ""),
                            "last_name": properties.get("lastname", ""),
                            "email": properties.get("email", ""),
                            "company": properties.get("company", ""),
                            "job_title": properties.get("jobtitle", ""),
                        })

                return contacts

        except Exception as e:
            print(f"Error fetching contacts from deal: {str(e)}")
            return []
