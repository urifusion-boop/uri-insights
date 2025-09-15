from http import HTTPStatus
from typing import Optional
from fastapi import APIRouter, Depends
from app.domain.responses.uri_response import UriResponse
from app.domain.responses.uri_response import UriResponse
from app.core.auth_handler import get_x_access_token
from app.services.XComplianceService import XComplianceService


router = APIRouter(prefix="/api/v1/x_compliance", tags=["XCompliance"])


@router.get("/jobs/{job_id}", tags=["Compliance"])
async def get_compliance_job(job_id: str, access_token=Depends(get_x_access_token)):
    """
    Fetch a single compliance job by ID.

    - **job_id**: The unique identifier of the compliance job.
    """
    result = XComplianceService.get_compliance_job(job_id, access_token)
    return UriResponse.get_status_response(result, HTTPStatus.OK)


@router.get("/jobs", tags=["Compliance"])
async def list_compliance_jobs(
    job_type: str,
    status: Optional[str] = None,
    access_token=Depends(get_x_access_token),
):
    """
    Fetch a list of compliance jobs.

    - **job_type**: Filter jobs by type ("tweets" or "users").
    - **status**: Filter jobs by status ("created", "in_progress", "completed", "failed").
    """
    result = XComplianceService.list_compliance_jobs(job_type, status, access_token)
    return UriResponse.get_status_response(result, HTTPStatus.OK)


@router.post("/jobs", tags=["Compliance"])
async def create_compliance_job(
    job_type: str,
    name: Optional[str] = None,
    resumable: Optional[bool] = None,
    access_token=Depends(get_x_access_token),
):
    """
    Create a new compliance job.

    - **job_type**: Specify the type of the job ("tweets" or "users").
    - **name**: (Optional) Name for identifying the job.
    - **resumable**: (Optional) Enable resumable uploads if true.
    """
    result = XComplianceService.create_compliance_job(
        job_type, name, resumable, access_token
    )
    return UriResponse.get_status_response(result, HTTPStatus.CREATED)
