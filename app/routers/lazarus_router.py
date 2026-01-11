from fastapi import APIRouter, Depends, Query, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, List
from fastapi.encoders import jsonable_encoder

from app.dependencies import get_db_dependency
from app.domain.responses.uri_response import UriResponse
from app.services.LazarusService import LazarusService
from app.services.LazarusMonitoringService import LazarusMonitoringService
from app.domain.schemas.lazarus_schema import (
    FocusContactCreate,
    CompanyMonitorCreate,
    LazarusMonitoringStatusEnum,
    LazarusAlertStatusEnum,
    CSVUploadRow,
)


router = APIRouter()


# ============ FOCUS CONTACTS ============
@router.post("/focus-contacts/add")
async def add_focus_contact(
    contact: FocusContactCreate,
    user_id: str = Query(...),
    source_lead_id: Optional[str] = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Add a new focus contact to monitor
    PRD Section 4.1: Focus Contact Monitoring
    """
    result = await LazarusService.add_focus_contact(
        db, user_id, contact, source_lead_id
    )

    if not result["success"]:
        return UriResponse.custom_response(result["message"], 400)

    return UriResponse.custom_response(
        result["message"],
        200,
        {
            "focus_id": result.get("focus_id"),
            "slots_used": result.get("slots_used"),
            "slots_available": result.get("slots_available"),
        },
    )


@router.get("/focus-contacts")
async def get_focus_contacts(
    user_id: str = Query(...),
    status: Optional[LazarusMonitoringStatusEnum] = Query(None),
    skip: int = Query(0),
    limit: int = Query(50),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Get all focus contacts for a user"""
    from app.repository.LazarusRepository import LazarusRepository

    contacts = await LazarusRepository.get_focus_contacts_by_user(
        db, user_id, status, skip, limit
    )

    return UriResponse.custom_response(
        "Focus contacts retrieved successfully",
        200,
        [jsonable_encoder(c) for c in contacts],
    )


@router.delete("/focus-contacts/{focus_id}")
async def remove_focus_contact(
    focus_id: str,
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Remove a focus contact"""
    result = await LazarusService.remove_focus_contact(db, user_id, focus_id)

    if not result["success"]:
        return UriResponse.custom_response(result["message"], 404)

    return UriResponse.custom_response(result["message"], 200)


@router.patch("/focus-contacts/{focus_id}/pause")
async def pause_focus_contact(
    focus_id: str,
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Pause monitoring for a focus contact"""
    result = await LazarusService.pause_focus_contact(db, user_id, focus_id)

    if not result["success"]:
        return UriResponse.custom_response(result["message"], 404)

    return UriResponse.custom_response(result["message"], 200)


@router.patch("/focus-contacts/{focus_id}/resume")
async def resume_focus_contact(
    focus_id: str,
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Resume monitoring for a paused focus contact"""
    result = await LazarusService.resume_focus_contact(db, user_id, focus_id)

    if not result["success"]:
        return UriResponse.custom_response(result["message"], 404)

    return UriResponse.custom_response(result["message"], 200)


# ============ COMPANY MONITORS ============
@router.post("/company-monitors/add")
async def add_company_monitor(
    monitor: CompanyMonitorCreate,
    user_id: str = Query(...),
    source_lead_id: Optional[str] = Query(None),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Add a new company monitor
    PRD Section 3 Track A: Company Monitoring
    """
    result = await LazarusService.add_company_monitor(
        db, user_id, monitor, source_lead_id
    )

    if not result["success"]:
        return UriResponse.custom_response(result["message"], 400)

    return UriResponse.custom_response(
        result["message"],
        200,
        {
            "monitor_id": result.get("monitor_id"),
            "slots_used": result.get("slots_used"),
            "slots_available": result.get("slots_available"),
        },
    )


@router.get("/company-monitors")
async def get_company_monitors(
    user_id: str = Query(...),
    status: Optional[LazarusMonitoringStatusEnum] = Query(None),
    skip: int = Query(0),
    limit: int = Query(50),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Get all company monitors for a user"""
    from app.repository.LazarusRepository import LazarusRepository

    monitors = await LazarusRepository.get_company_monitors_by_user(
        db, user_id, status, skip, limit
    )

    return UriResponse.custom_response(
        "Company monitors retrieved successfully",
        200,
        [jsonable_encoder(m) for m in monitors],
    )


@router.delete("/company-monitors/{monitor_id}")
async def remove_company_monitor(
    monitor_id: str,
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Remove a company monitor"""
    result = await LazarusService.remove_company_monitor(db, user_id, monitor_id)

    if not result["success"]:
        return UriResponse.custom_response(result["message"], 404)

    return UriResponse.custom_response(result["message"], 200)


# ============ BULK CSV UPLOAD ============
@router.post("/bulk-upload")
async def bulk_upload_csv(
    csv_rows: List[CSVUploadRow],
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Bulk upload focus contacts/companies from CSV
    PRD Section 4.2: Bulk Upload via CSV
    """
    result = await LazarusService.bulk_upload_from_csv(db, user_id, csv_rows)

    return UriResponse.custom_response(
        result["message"],
        200,
        {
            "added_count": result.get("added_count"),
            "failed_count": result.get("failed_count"),
            "errors": result.get("errors", []),
        },
    )


# ============ ALERTS ============
@router.get("/alerts")
async def get_alerts(
    user_id: str = Query(...),
    status: Optional[LazarusAlertStatusEnum] = Query(None),
    skip: int = Query(0),
    limit: int = Query(50),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Get Lazarus alerts for a user"""
    alerts = await LazarusService.get_alerts(db, user_id, status, skip, limit)

    return UriResponse.custom_response(
        "Alerts retrieved successfully",
        200,
        [jsonable_encoder(a) for a in alerts],
    )


@router.patch("/alerts/{alert_id}/contacted")
async def mark_alert_contacted(
    alert_id: str,
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Mark an alert as contacted"""
    result = await LazarusService.mark_alert_contacted(db, user_id, alert_id)

    if not result["success"]:
        return UriResponse.custom_response(result["message"], 404)

    return UriResponse.custom_response(result["message"], 200)


@router.patch("/alerts/{alert_id}/dismiss")
async def dismiss_alert(
    alert_id: str,
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Dismiss an alert"""
    result = await LazarusService.dismiss_alert(db, user_id, alert_id)

    if not result["success"]:
        return UriResponse.custom_response(result["message"], 404)

    return UriResponse.custom_response(result["message"], 200)


# ============ SLOTS & METRICS ============
@router.get("/slots")
async def get_user_slots(
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Get user's slot information"""
    slots = await LazarusService.get_user_slots(db, user_id)

    return UriResponse.custom_response(
        "Slots retrieved successfully", 200, jsonable_encoder(slots)
    )


@router.get("/metrics")
async def get_user_metrics(
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Get comprehensive Lazarus metrics for a user
    PRD Section 7: Success Metrics
    """
    metrics = await LazarusService.get_user_metrics(db, user_id)

    return UriResponse.custom_response(
        "Metrics retrieved successfully", 200, jsonable_encoder(metrics)
    )


@router.post("/upgrade-to-pro")
async def upgrade_to_pro(
    user_id: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Upgrade user from BASIC (50 slots) to PRO (500 slots)"""
    result = await LazarusService.upgrade_to_pro(db, user_id)

    if not result["success"]:
        return UriResponse.custom_response(result["message"], 400)

    return UriResponse.custom_response(
        result["message"],
        200,
        {
            "max_slots": result.get("max_slots"),
            "plan_type": result.get("plan_type"),
        },
    )


# ============ LEAD INTEGRATION ============
@router.patch("/leads/{lead_id}/mark-dead")
async def mark_lead_as_dead(
    lead_id: str,
    user_id: str = Query(...),
    reason: str = Query(...),
    auto_monitor: bool = Query(False),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Mark a lead as DEAD
    Optionally auto-add to Lazarus monitoring
    """
    result = await LazarusService.mark_lead_as_dead(
        db, user_id, lead_id, reason, auto_monitor
    )

    if not result["success"]:
        return UriResponse.custom_response(result["message"], 404)

    return UriResponse.custom_response(result["message"], 200, result)


@router.patch("/leads/{lead_id}/resurrect")
async def resurrect_lead(
    lead_id: str,
    user_id: str = Query(...),
    alert_type: str = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Resurrect a DEAD lead
    PRD Section 5.2: Resurrection
    """
    result = await LazarusService.resurrect_lead(db, user_id, lead_id, alert_type)

    if not result["success"]:
        return UriResponse.custom_response(result["message"], 404)

    return UriResponse.custom_response(result["message"], 200, result)


# ============ BACKGROUND SCANNING ============
@router.post("/scan/run-weekly")
async def run_weekly_scan(
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """
    Trigger weekly background scan manually
    PRD Section 6: Origami Method
    NOTE: This should normally be triggered by APScheduler cron job
    """
    result = await LazarusMonitoringService.run_weekly_scan(db)

    return UriResponse.custom_response(
        "Weekly scan completed",
        200,
        result,
    )


@router.post("/scan/focus-contacts")
async def scan_focus_contacts(
    batch_size: int = Query(100),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Manually trigger focus contact scan"""
    result = await LazarusMonitoringService.scan_focus_contacts(db, batch_size)

    return UriResponse.custom_response(
        "Focus contact scan completed",
        200,
        result,
    )


@router.post("/scan/company-monitors")
async def scan_company_monitors(
    batch_size: int = Query(100),
    db: AsyncIOMotorDatabase = Depends(get_db_dependency),
):
    """Manually trigger company monitor scan"""
    result = await LazarusMonitoringService.scan_company_monitors(db, batch_size)

    return UriResponse.custom_response(
        "Company monitor scan completed",
        200,
        result,
    )
