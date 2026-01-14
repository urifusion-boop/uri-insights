from fastapi import APIRouter, Depends, Query, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorDatabase
from fastapi.responses import RedirectResponse
from typing import Optional

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


@router.get("/connect/hubspot/callback")
async def hubspot_oauth_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Handle HubSpot OAuth callback
    Exchanges code for access token and stores connection
    """
    try:
        # Extract user_id from state parameter
        user_id = state

        # Exchange code for tokens
        result = await HubSpotService.handle_oauth_callback(db, user_id, code)

        if not result["success"]:
            # Redirect to error page
            return RedirectResponse(url=f"/lazarus?crm_error={result['message']}")

        # Redirect to success page with postMessage to close popup
        return RedirectResponse(url="/lazarus?crm_connected=hubspot")

    except Exception as e:
        return RedirectResponse(url=f"/lazarus?crm_error={str(e)}")


@router.get("/connect/salesforce/callback")
async def salesforce_oauth_callback(
    request: Request,
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Handle Salesforce OAuth callback
    Exchanges code for access token and stores connection
    """
    try:
        # Extract user_id from state parameter
        user_id = state

        # Exchange code for tokens
        result = await SalesforceService.handle_oauth_callback(db, user_id, code)

        if not result["success"]:
            return RedirectResponse(url=f"/lazarus?crm_error={result['message']}")

        return RedirectResponse(url="/lazarus?crm_connected=salesforce")

    except Exception as e:
        return RedirectResponse(url=f"/lazarus?crm_error={str(e)}")


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


# ============ CRM SYNC ============
@router.post("/sync")
async def sync_crm(
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Manually trigger CRM sync
    PRD: Auto-imports stalled deals and closed-lost leads

    Returns count of contacts and companies added
    """
    from app.repository.CRMRepository import CRMRepository

    # Get CRM connection
    connection = await CRMRepository.get_crm_connection(db, user_id)

    if not connection:
        raise HTTPException(status_code=404, detail="No CRM connected. Please connect a CRM first.")

    crm_type = connection.get("crm_type")

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
