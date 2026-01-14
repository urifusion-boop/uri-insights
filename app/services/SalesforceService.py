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
import jwt
import secrets
from typing import Dict, List, Any, Optional
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta


class SalesforceService:
    """Service for Salesforce OAuth and API operations"""

    # OAuth Configuration
    CLIENT_ID = os.getenv("SALESFORCE_CLIENT_ID", "")
    CLIENT_SECRET = os.getenv("SALESFORCE_CLIENT_SECRET", "")
    REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI", "https://api.uricreative.com:8443/api/lazarus/crm/connect/salesforce/callback")
    AUTH_URL = "https://login.salesforce.com/services/oauth2/authorize"
    TOKEN_URL = "https://login.salesforce.com/services/oauth2/token"
    JWT_SECRET = os.getenv("JWT_SECRET", "")  # Use same JWT secret as main app

    # API Configuration
    API_VERSION = "v59.0"
    SCOPES = ["api", "refresh_token", "offline_access"]

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
        return jwt.encode(payload, SalesforceService.JWT_SECRET, algorithm="HS256")

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
                SalesforceService.JWT_SECRET,
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
        Generate Salesforce OAuth authorization URL with secure state token

        Args:
            user_id: User ID to pass in state parameter

        Returns:
            Authorization URL for OAuth popup
        """
        scope = " ".join(SalesforceService.SCOPES)
        state_token = SalesforceService.generate_oauth_state(user_id)

        params = {
            "response_type": "code",
            "client_id": SalesforceService.CLIENT_ID,
            "redirect_uri": SalesforceService.REDIRECT_URI,
            "scope": scope,
            "state": state_token,  # JWT-based state for CSRF protection
        }

        # Build URL with query parameters
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{SalesforceService.AUTH_URL}?{query_string}"

    @staticmethod
    async def fetch_account_info(access_token: str, instance_url: str) -> Dict[str, Any]:
        """
        Fetch Salesforce organization information

        Args:
            access_token: Salesforce access token
            instance_url: Salesforce instance URL

        Returns:
            Account info with org_id, org_name, instance_url
        """
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient() as client:
                # Fetch org info from Salesforce API
                response = await client.get(
                    f"{instance_url}/services/data/{SalesforceService.API_VERSION}/sobjects/Organization",
                    headers=headers,
                )

                if response.status_code != 200:
                    return {"instance_url": instance_url}

                # Query for organization details
                query = "SELECT Id, Name, OrganizationType, IsSandbox FROM Organization LIMIT 1"
                org_response = await client.get(
                    f"{instance_url}/services/data/{SalesforceService.API_VERSION}/query",
                    headers=headers,
                    params={"q": query}
                )

                if org_response.status_code == 200:
                    org_data = org_response.json()
                    if org_data.get("records"):
                        org = org_data["records"][0]
                        return {
                            "org_id": org.get("Id"),
                            "org_name": org.get("Name"),
                            "org_type": org.get("OrganizationType"),
                            "is_sandbox": org.get("IsSandbox", False),
                            "instance_url": instance_url,
                        }

                return {"instance_url": instance_url}

        except Exception as e:
            print(f"Error fetching Salesforce account info: {str(e)}")
            return {"instance_url": instance_url}

    @staticmethod
    async def handle_oauth_callback(
        db: AsyncIOMotorDatabase, user_id: str, code: str
    ) -> Dict[str, Any]:
        """
        Handle OAuth callback - exchange code for access token and fetch account info

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

            # Fetch account info
            instance_url = token_data["instance_url"]
            account_info = await SalesforceService.fetch_account_info(
                token_data["access_token"], instance_url
            )

            # Store connection in database
            from app.repository.CRMRepository import CRMRepository

            connection = {
                "user_id": user_id,
                "crm_type": "salesforce",
                "access_token": token_data["access_token"],
                "refresh_token": token_data["refresh_token"],
                "instance_url": instance_url,
                "token_type": token_data["token_type"],
                "connected_at": datetime.utcnow(),
                "last_sync_at": None,
                "contacts_synced": 0,
                "companies_synced": 0,
                # Account info fields
                "org_id": account_info.get("org_id"),
                "org_name": account_info.get("org_name"),
                "org_type": account_info.get("org_type"),
                "is_sandbox": account_info.get("is_sandbox", False),
                # Metadata
                "scopes": SalesforceService.SCOPES,
                "auth_type": "oauth2",
                "api_version": SalesforceService.API_VERSION,
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

            # Query OpportunityContactRole to get associated contacts (with phone fallbacks)
            query = f"""
                SELECT ContactId, Contact.FirstName, Contact.LastName, Contact.Email,
                       Contact.Phone, Contact.MobilePhone, Contact.Title, Contact.Account.Name
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

            # Process contacts with field mapping fallbacks (Priority 3)
            contacts = []
            for record in data.get("records", []):
                contact = record.get("Contact", {})
                account = contact.get("Account", {})

                # Phone field fallback: try Phone first, then MobilePhone
                phone = contact.get("Phone") or contact.get("MobilePhone") or ""

                contacts.append({
                    "contact_id": record.get("ContactId"),
                    "first_name": contact.get("FirstName", ""),
                    "last_name": contact.get("LastName", ""),
                    "email": contact.get("Email", ""),
                    "phone": phone,  # With fallback
                    "job_title": contact.get("Title", ""),
                    "company": account.get("Name", ""),
                })

            return contacts

        except Exception as e:
            print(f"Error fetching contacts from opportunity: {str(e)}")
            return []

    @staticmethod
    async def create_task_on_contact(
        db: AsyncIOMotorDatabase,
        user_id: str,
        access_token: str,
        instance_url: str,
        contact_email: str,
        task_description: str
    ) -> Dict[str, Any]:
        """
        Create a task on a Salesforce contact
        PRD: "Syncs insights back to the CRM (notifications / notes)"

        Args:
            db: Database connection
            user_id: User ID
            access_token: Salesforce access token
            instance_url: Salesforce instance URL
            contact_email: Email of contact to add task to
            task_description: Task description (Lazarus alert details)

        Returns:
            Success status and message
        """
        try:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            # First, find contact by email
            query = f"SELECT Id FROM Contact WHERE Email = '{contact_email}' LIMIT 1"

            async with httpx.AsyncClient() as client:
                search_response = await client.get(
                    f"{instance_url}/services/data/{SalesforceService.API_VERSION}/query",
                    headers=headers,
                    params={"q": query}
                )

                if search_response.status_code != 200 or not search_response.json().get("records"):
                    return {
                        "success": False,
                        "message": f"Contact not found in Salesforce: {contact_email}"
                    }

                contact_id = search_response.json()["records"][0]["Id"]

                # Create task associated with contact
                task_response = await client.post(
                    f"{instance_url}/services/data/{SalesforceService.API_VERSION}/sobjects/Task",
                    headers=headers,
                    json={
                        "Subject": "🧬 Lazarus Buying Signal Detected",
                        "Description": task_description,
                        "WhoId": contact_id,  # Associate with contact
                        "Status": "Not Started",
                        "Priority": "High",
                        "ActivityDate": datetime.utcnow().strftime("%Y-%m-%d")
                    }
                )

                if task_response.status_code in [200, 201]:
                    return {
                        "success": True,
                        "message": "Task created in Salesforce"
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Failed to create task: {task_response.text}"
                    }

        except Exception as e:
            return {
                "success": False,
                "message": f"Error creating Salesforce task: {str(e)}"
            }
