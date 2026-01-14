from fastapi import APIRouter, Depends, Query, HTTPException, Request, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi.responses import RedirectResponse
from typing import Optional
from datetime import datetime

from app.dependencies import get_db_dependency
from app.domain.responses.uri_response import UriResponse
from app.services.HubSpotService import HubSpotService
from app.services.SalesforceService import SalesforceService
from app.services.CRMSyncService import CRMSyncService


router = APIRouter()


# ============ CRM CONNECTION ============
@router.post("/connect/initiate")
async def initiate_crm_connection(
    user_id: str = Query(...),
    crm_type: str = Query(..., description="hubspot or salesforce"),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Initiate OAuth flow for HubSpot or Salesforce
    PRD Section 4.4: CRM Integration

    Returns authorization URL for OAuth popup
    """
    if crm_type not in ["hubspot", "salesforce"]:
        raise HTTPException(status_code=400, detail="Invalid CRM type. Must be 'hubspot' or 'salesforce'")

    try:
        if crm_type == "hubspot":
            auth_url = HubSpotService.get_authorization_url(user_id)
        else:  # salesforce
            auth_url = SalesforceService.get_authorization_url(user_id)

        return UriResponse.custom_response(
            f"{crm_type.capitalize()} OAuth initiated",
            200,
            {"authorization_url": auth_url}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initiate {crm_type} OAuth: {str(e)}")


# ============ PRIVATE APP CONNECTION (Priority 3) ============
@router.post("/connect/private-app")
async def connect_private_app(
    user_id: str = Query(...),
    crm_type: str = Query(..., description="hubspot or salesforce"),
    access_token: str = Query(..., description="Private app access token"),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Connect CRM using Private App token (simpler alternative to OAuth)
    Priority 3: Private App support

    Use Case: Server-to-server integration without OAuth popup
    HubSpot: Settings > Integrations > Private Apps
    Salesforce: Create Connected App with JWT or username-password flow

    Body Parameters:
    - access_token: Private app access token from CRM
    """
    from app.repository.CRMRepository import CRMRepository

    if crm_type not in ["hubspot", "salesforce"]:
        raise HTTPException(status_code=400, detail="Invalid CRM type")

    try:
        # Validate token by fetching account info
        if crm_type == "hubspot":
            account_info = await HubSpotService.fetch_account_info(access_token)
            if not account_info or not account_info.get("hub_id"):
                raise HTTPException(status_code=401, detail="Invalid HubSpot access token")

            connection_data = {
                "user_id": user_id,
                "crm_type": "hubspot",
                "access_token": access_token,
                "refresh_token": None,  # Private apps don't have refresh tokens
                "expires_in": None,  # Private app tokens don't expire
                "token_type": "private_app",
                "connected_at": datetime.utcnow(),
                "last_sync_at": None,
                "contacts_synced": 0,
                "companies_synced": 0,
                # Account info
                "hub_id": account_info.get("hub_id"),
                "hub_domain": account_info.get("hub_domain"),
                "portal_url": account_info.get("portal_url"),
                "account_name": account_info.get("account_name"),
                "time_zone": account_info.get("time_zone"),
                # Metadata
                "scopes": ["private_app"],  # Private apps have all scopes
                "auth_type": "private_app",
                "api_version": "v3",
                # Sync stats
                "total_syncs": 0,
                "successful_syncs": 0,
                "failed_syncs": 0,
                "avg_sync_duration_seconds": 0,
                "last_sync_duration_seconds": None,
            }

        else:  # salesforce
            # Note: Salesforce private app requires instance_url
            raise HTTPException(
                status_code=501,
                detail="Salesforce private app support requires instance_url parameter. Use OAuth instead."
            )

        # Save connection
        result = await CRMRepository.save_crm_connection(db, user_id, connection_data)

        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["message"])

        return UriResponse.custom_response(
            f"{crm_type.title()} connected successfully via Private App",
            200,
            {
                "success": True,
                "crm_type": crm_type,
                "auth_type": "private_app",
                "account_name": account_info.get("account_name", ""),
                "hub_id": account_info.get("hub_id")
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect private app: {str(e)}")


@router.get("/connect/hubspot/callback")
async def hubspot_oauth_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Handle HubSpot OAuth callback with state validation
    Exchanges code for access token and stores connection
    """
    try:
        # Verify and decode state token (CSRF protection)
        user_id = HubSpotService.verify_oauth_state(state)

        if not user_id:
            return RedirectResponse(url="/crm-callback?crm_error=Invalid or expired OAuth state token")

        # Exchange code for tokens
        result = await HubSpotService.handle_oauth_callback(db, user_id, code)

        if not result["success"]:
            # Redirect to callback page with error
            return RedirectResponse(url=f"/crm-callback?crm_error={result['message']}")

        # Redirect to callback page with success (will trigger postMessage and close popup)
        return RedirectResponse(url="/crm-callback?crm_connected=hubspot")

    except Exception as e:
        return RedirectResponse(url=f"/crm-callback?crm_error={str(e)}")


@router.get("/connect/salesforce/callback")
async def salesforce_oauth_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Handle Salesforce OAuth callback with state validation
    Exchanges code for access token and stores connection
    """
    try:
        # Verify and decode state token (CSRF protection)
        user_id = SalesforceService.verify_oauth_state(state)

        if not user_id:
            return RedirectResponse(url="/crm-callback?crm_error=Invalid or expired OAuth state token")

        # Exchange code for tokens
        result = await SalesforceService.handle_oauth_callback(db, user_id, code)

        if not result["success"]:
            return RedirectResponse(url=f"/crm-callback?crm_error={result['message']}")

        return RedirectResponse(url="/crm-callback?crm_connected=salesforce")

    except Exception as e:
        return RedirectResponse(url=f"/crm-callback?crm_error={str(e)}")


# ============ CRM STATUS ============
@router.get("/status")
async def get_crm_status(
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Check if user has connected CRM and get connection details
    """
    from app.repository.CRMRepository import CRMRepository

    connection = await CRMRepository.get_crm_connection(db, user_id)

    if not connection:
        return UriResponse.custom_response(
            "No CRM connected",
            200,
            {
                "connected": False,
                "crm_type": None,
                "last_sync": None,
            }
        )

    return UriResponse.custom_response(
        "CRM connection found",
        200,
        {
            "connected": True,
            "crm_type": connection.get("crm_type"),
            "last_sync": connection.get("last_sync_at"),
            "contacts_synced": connection.get("contacts_synced", 0),
            "companies_synced": connection.get("companies_synced", 0),
        }
    )


# ============ CRM DISCONNECT ============
@router.delete("/disconnect")
async def disconnect_crm(
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Disconnect CRM integration
    Removes OAuth tokens and connection data
    """
    from app.repository.CRMRepository import CRMRepository

    result = await CRMRepository.remove_crm_connection(db, user_id)

    if not result["success"]:
        return UriResponse.custom_response(result["message"], 404)

    return UriResponse.custom_response(
        "CRM disconnected successfully",
        200,
        {"success": True, "message": "CRM connection removed"}
    )


# ============ CRM SYNC LOGS ============
@router.get("/sync-logs")
async def get_sync_logs(
    user_id: str = Query(...),
    limit: int = Query(10, description="Number of logs to return"),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Get CRM sync history logs
    Priority 2: Sync logs viewer

    Returns recent sync operations with stats and errors
    """
    from app.repository.CRMSyncLogRepository import CRMSyncLogRepository

    logs = await CRMSyncLogRepository.get_sync_logs_for_user(db, user_id, limit)

    return UriResponse.custom_response(
        "Sync logs retrieved",
        200,
        logs
    )


# ============ CRM SYNC ============
@router.post("/sync")
async def sync_crm(
    user_id: str = Query(...),
    background: Optional[bool] = Query(False, description="Run sync in background for large datasets"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Manually trigger CRM sync (Priority 3: Background task support)
    PRD: Auto-imports stalled deals and closed-lost leads

    Query Parameters:
    - background: Set to true for large syncs (1000+ contacts)

    Returns count of contacts and companies added
    """
    from app.repository.CRMRepository import CRMRepository

    # Get CRM connection
    connection = await CRMRepository.get_crm_connection(db, user_id)

    if not connection:
        raise HTTPException(status_code=404, detail="No CRM connected. Please connect a CRM first.")

    crm_type = connection.get("crm_type")

    # If background mode requested, queue the sync
    if background:
        background_tasks.add_task(
            CRMSyncService.sync_crm_data,
            db, user_id, crm_type, connection
        )

        return UriResponse.custom_response(
            f"{crm_type.title()} sync started in background",
            202,
            {
                "success": True,
                "status": "processing",
                "message": "Sync running in background. Check sync logs for results."
            }
        )

    # Otherwise run sync synchronously
    try:
        # Trigger sync based on CRM type
        result = await CRMSyncService.sync_crm_data(db, user_id, crm_type, connection)

        if not result["success"]:
            return UriResponse.custom_response(result["message"], 400)

        return UriResponse.custom_response(
            "CRM sync completed successfully",
            200,
            {
                "contacts_added": result.get("contacts_added", 0),
                "companies_added": result.get("companies_added", 0),
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CRM sync failed: {str(e)}")


# ============ SYNC INSIGHTS BACK TO CRM ============
@router.post("/sync-alert-to-crm")
async def sync_alert_to_crm(
    user_id: str = Query(...),
    alert_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Sync Lazarus alert back to CRM as a note/activity
    PRD: "Syncs insights back to the CRM (notifications / notes)"

    When a buying signal is detected, this writes it back to the user's CRM
    so they can see it in HubSpot/Salesforce alongside the deal/contact.
    """
    from app.repository.CRMRepository import CRMRepository
    from app.repository.LazarusRepository import LazarusRepository

    try:
        # Get CRM connection
        connection = await CRMRepository.get_crm_connection(db, user_id)
        if not connection:
            raise HTTPException(status_code=404, detail="No CRM connected")

        # Get alert details
        alert = await LazarusRepository.get_alert_by_id(db, user_id, alert_id)
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        crm_type = connection.get("crm_type")
        access_token = connection.get("access_token")

        # Format note content
        note_content = f"""
🧬 Lazarus Signal Detected

Type: {alert.get('alert_type')}
Signal: {alert.get('alert_message')}

Suggested Action:
{alert.get('suggested_pitch', 'Review this opportunity')}

Detected: {alert.get('created_at')}
        """.strip()

        # Sync to CRM
        if crm_type == "hubspot":
            result = await HubSpotService.create_note_on_contact(
                db, user_id, access_token, alert.get('contact_email'), note_content
            )
        elif crm_type == "salesforce":
            result = await SalesforceService.create_task_on_contact(
                db, user_id, access_token, connection.get('instance_url'),
                alert.get('contact_email'), note_content
            )
        else:
            raise HTTPException(status_code=400, detail="Unsupported CRM type")

        if result.get("success"):
            return UriResponse.custom_response(
                "Alert synced to CRM successfully",
                200,
                {"synced": True, "crm_type": crm_type}
            )
        else:
            raise HTTPException(status_code=500, detail=result.get("message", "Failed to sync"))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync alert to CRM: {str(e)}")
