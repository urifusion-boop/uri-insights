import requests
from http import HTTPStatus
from typing import Dict, Any, Optional
from fastapi import HTTPException


class XComplianceService:
    BASE_URL = "https://api.x.com/2"

    @staticmethod
    def get_compliance_job(job_id: str, access_token: str) -> Dict[str, Any]:
        """
        Fetch details of a single compliance job.

        :param job_id: The unique ID of the compliance job.
        :param access_token: Bearer token for authentication.
        :return: JSON response with job details.
        """
        url = f"{XComplianceService.BASE_URL}/compliance/jobs/{job_id}"
        headers = {"Authorization": f"Bearer {access_token}"}

        response = requests.get(url, headers=headers)
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to fetch compliance job with ID {job_id}: {response.text}",
            )
        return response.json()

    @staticmethod
    def list_compliance_jobs(
        job_type: str, status: Optional[str], access_token: str
    ) -> Dict[str, Any]:
        """
        Fetch a list of recent compliance jobs.

        :param job_type: Type of compliance jobs to filter ("tweets" or "users").
        :param status: Optional job status filter (e.g., "created", "in_progress").
        :param access_token: Bearer token for authentication.
        :return: JSON response with a list of compliance jobs.
        """
        url = f"{XComplianceService.BASE_URL}/compliance/jobs"
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"type": job_type}
        if status:
            params["status"] = status

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to fetch compliance jobs: {response.text}",
            )
        return response.json()

    @staticmethod
    def create_compliance_job(
        job_type: str, name: Optional[str], resumable: Optional[bool], access_token: str
    ) -> Dict[str, Any]:
        """
        Create a new compliance job for Tweet or User IDs.

        :param job_type: Type of compliance job ("tweets" or "users").
        :param name: Optional name for the job.
        :param resumable: Whether to enable resumable uploads.
        :param access_token: Bearer token for authentication.
        :return: JSON response with the created job details.
        """
        url = f"{XComplianceService.BASE_URL}/compliance/jobs"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload = {"type": job_type}
        if name:
            payload["name"] = name

        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != HTTPStatus.CREATED:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to create compliance job: {response.text}",
            )
        return response.json()
