"""
Salesforce OAuth and API Integration Service
PRD Section 4.4: CRM Integration

Handles:
- OAuth 2.0 authentication flow
- Token refresh and management
- Fetching leads and opportunities from Salesforce
- Identifying stalled opportunities and closed-lost leads
"""
import os
import httpx
from typing import Dict, List, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime


class SalesforceService:
    """Service for Salesforce OAuth and API operations"""

    # OAuth Configuration
    CLIENT_ID = os.getenv("SALESFORCE_CLIENT_ID", "")
    CLIENT_SECRET = os.getenv("SALESFORCE_CLIENT_SECRET", "")
    REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "https://api.uricreative.com:8443/api/lazarus/crm/connect/salesforce/callback")
    AUTH_URL = "https://login.salesforce.com/services/oauth2/authorize"
    TOKEN_URL = "https://login.salesforce.com/services/oauth2/token"

    # API Configuration
    API_VERSION = "v59.0"
    SCOPES = ["api", "refresh_token", "offline_access"]

    @staticmethod
    def get_authorization_url(user_id: str) -> str:
        """
        Generate Salesforce OAuth authorization URL

        Args:
            user_id: User ID to pass in state parameter

        Returns:
            Authorization URL for OAuth popup
        """
        scope = " ".join(SalesforceService.SCOPES)
        params = {
            "response_type": "code",
            "client_id": SalesforceService.CLIENT_ID,
            "redirect_uri": SalesforceService.REDIRECT_URI,
            "scope": scope,
            "state": user_id,  # Pass user_id to retrieve in callback
        }

        # Build URL with query parameters
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{SalesforceService.AUTH_URL}?{query_string}"

    @staticmethod
    async def handle_oauth_callback(
        db: AsyncIOMotorDatabase, user_id: str, code: str
    ) -> Dict[str, Any]:
        """
        Handle OAuth callback - exchange code for access token

        Args:
            db: Database connection
            user_id: User ID from state parameter
            code: Authorization code from Salesforce

        Returns:
            Success status and message
        """
        try:
            # Exchange code for access token
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    SalesforceService.TOKEN_URL,
                    data={
                        "grant_type": "authorization_code",
                        "client_id": SalesforceService.CLIENT_ID,
                        "client_secret": SalesforceService.CLIENT_SECRET,
                        "redirect_uri": SalesforceService.REDIRECT_URI,
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
                "crm_type": "salesforce",
                "access_token": token_data["access_token"],
                "refresh_token": token_data["refresh_token"],
                "instance_url": token_data["instance_url"],
                "token_type": token_data["token_type"],
                "connected_at": datetime.utcnow(),
                "last_sync_at": None,
                "contacts_synced": 0,
                "companies_synced": 0,
            }

            await CRMRepository.save_crm_connection(db, user_id, connection)

            return {
                "success": True,
                "message": "Salesforce connected successfully",
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
        Refresh Salesforce access token using refresh token

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
                    SalesforceService.TOKEN_URL,
                    data={
                        "grant_type": "refresh_token",
                        "client_id": SalesforceService.CLIENT_ID,
                        "client_secret": SalesforceService.CLIENT_SECRET,
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
                refresh_token,  # Salesforce doesn't always return new refresh token
                3600,  # Default expiry
            )

            return token_data["access_token"]

        except Exception:
            return None

    @staticmethod
    async def fetch_stalled_opportunities(
        db: AsyncIOMotorDatabase, user_id: str, access_token: str, instance_url: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch stalled opportunities from Salesforce
        PRD: "Stalled" = No activity in 30+ days OR stage hasn't changed in 60+ days

        Args:
            db: Database connection
            user_id: User ID
            access_token: Salesforce access token
            instance_url: Salesforce instance URL

        Returns:
            List of stalled opportunities
        """
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            # Query stalled opportunities using SOQL
            # LastActivityDate < 30 days ago OR (LastModifiedDate < 60 days ago AND StageName unchanged)
            query = """
                SELECT Id, Name, StageName, Amount, CloseDate, LastActivityDate, LastModifiedDate, AccountId
                FROM Opportunity
                WHERE (LastActivityDate < LAST_N_DAYS:30 OR LastModifiedDate < LAST_N_DAYS:60)
                AND IsClosed = false
                LIMIT 100
            """

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{instance_url}/services/data/{SalesforceService.API_VERSION}/query",
                    headers=headers,
                    params={"q": query},
                )

                if response.status_code != 200:
                    # Try to refresh token
                    from app.repository.CRMRepository import CRMRepository
                    connection = await CRMRepository.get_crm_connection(db, user_id)
                    new_token = await SalesforceService.refresh_access_token(
                        db, user_id, connection["refresh_token"]
                    )
                    if new_token:
                        headers["Authorization"] = f"Bearer {new_token}"
                        response = await client.get(
                            f"{instance_url}/services/data/{SalesforceService.API_VERSION}/query",
                            headers=headers,
                            params={"q": query},
                        )

                data = response.json()

            # Process results
            stalled_opps = []
            now = datetime.utcnow()

            for opp in data.get("records", []):
                last_activity = opp.get("LastActivityDate") or opp.get("LastModifiedDate")
                if last_activity:
                    try:
                        last_activity_date = datetime.fromisoformat(last_activity.replace("Z", "+00:00"))
                        days_stalled = (now - last_activity_date).days

                        stalled_opps.append({
                            "opportunity_id": opp["Id"],
                            "opportunity_name": opp.get("Name"),
                            "stage": opp.get("StageName"),
                            "amount": opp.get("Amount"),
                            "account_id": opp.get("AccountId"),
                            "days_stalled": days_stalled,
                        })
                    except Exception:
                        continue

            return stalled_opps

        except Exception as e:
            print(f"Error fetching stalled opportunities: {str(e)}")
            return []

    @staticmethod
    async def fetch_closed_lost_opportunities(
        db: AsyncIOMotorDatabase, user_id: str, access_token: str, instance_url: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch closed-lost opportunities from Salesforce
        PRD: Automatically monitor contacts from closed-lost opportunities

        Args:
            db: Database connection
            user_id: User ID
            access_token: Salesforce access token
            instance_url: Salesforce instance URL

        Returns:
            List of closed-lost opportunities
        """
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            # Query closed-lost opportunities
            query = """
                SELECT Id, Name, StageName, Amount, CloseDate, AccountId
                FROM Opportunity
                WHERE IsWon = false AND IsClosed = true
                ORDER BY CloseDate DESC
                LIMIT 100
            """

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{instance_url}/services/data/{SalesforceService.API_VERSION}/query",
                    headers=headers,
                    params={"q": query},
                )

                if response.status_code != 200:
                    # Try token refresh
                    from app.repository.CRMRepository import CRMRepository
                    connection = await CRMRepository.get_crm_connection(db, user_id)
                    new_token = await SalesforceService.refresh_access_token(
                        db, user_id, connection["refresh_token"]
                    )
                    if new_token:
                        headers["Authorization"] = f"Bearer {new_token}"
                        response = await client.get(
                            f"{instance_url}/services/data/{SalesforceService.API_VERSION}/query",
                            headers=headers,
                            params={"q": query},
                        )

                data = response.json()

            return data.get("records", [])

        except Exception as e:
            print(f"Error fetching closed-lost opportunities: {str(e)}")
            return []

    @staticmethod
    async def fetch_contacts_from_opportunity(
        db: AsyncIOMotorDatabase, user_id: str, access_token: str, instance_url: str, opportunity_id: str
    ) -> List[Dict[str, Any]]:
        """
        Fetch contacts associated with a specific opportunity

        Args:
            db: Database connection
            user_id: User ID
            access_token: Salesforce access token
            instance_url: Salesforce instance URL
            opportunity_id: Opportunity ID

        Returns:
            List of contacts with name, email, job title, company
        """
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            # Query OpportunityContactRole to get associated contacts
            query = f"""
                SELECT ContactId, Contact.FirstName, Contact.LastName, Contact.Email, Contact.Title, Contact.Account.Name
                FROM OpportunityContactRole
                WHERE OpportunityId = '{opportunity_id}'
            """

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{instance_url}/services/data/{SalesforceService.API_VERSION}/query",
                    headers=headers,
                    params={"q": query},
                )

                if response.status_code != 200:
                    return []

                data = response.json()

            # Process contacts
            contacts = []
            for record in data.get("records", []):
                contact = record.get("Contact", {})
                account = contact.get("Account", {})
                contacts.append({
                    "contact_id": record.get("ContactId"),
                    "first_name": contact.get("FirstName", ""),
                    "last_name": contact.get("LastName", ""),
                    "email": contact.get("Email", ""),
                    "job_title": contact.get("Title", ""),
                    "company": account.get("Name", ""),
                })

            return contacts

        except Exception as e:
            print(f"Error fetching contacts from opportunity: {str(e)}")
            return []
