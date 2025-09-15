import asyncio
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.domain.enums.lead_enum import LeadStatusEnum
from app.domain.responses.uri_response import UriResponse
from app.repository.LeadFormSnapshotRepository import LeadFormSnapshotRepository
from app.repository.LeadRepository import LeadRepository


class LeadFormSnapshotService:
    """
    Service to handle lead form snapshots.
    """

    @staticmethod
    async def get_by_filters(
        db: AsyncIOMotorDatabase, filters: dict, skip: int = 0, limit: int = 10
    ):
        results = await LeadFormSnapshotRepository.get_by_filters(
            db, filters, skip, limit
        )

        lead_form_snapshots = results.get("responseData", {}).get("data", [])

        # Launch concurrent metadata fetches
        enriched_snapshots = await asyncio.gather(
            *[
                LeadFormSnapshotService._get_metadata_for_snapshot(db, snapshot)
                for snapshot in lead_form_snapshots
            ]
        )

        return UriResponse.get_paged_data_response(
            "Lead form snapshot",
            enriched_snapshots,
            results.get("responseData", {}).get("total", 0),
            skip + 1,
            limit,
        )

    @staticmethod
    async def _get_metadata_for_snapshot(
        db: AsyncIOMotorDatabase, lead_form_snapshot: dict
    ):
        lead_form_snapshot_id = lead_form_snapshot.get("lead_form_snapshot_id", "")
        snapshot = await LeadFormSnapshotRepository.get_by_id(db, lead_form_snapshot_id)
        if not snapshot:
            return UriResponse.get_single_data_response("Lead form snapshot", None)

        total_leads_for_snapshot = (
            await LeadRepository.get_leads_count_by_filter(
                db, {"lead_form_snapshot_id": lead_form_snapshot_id}
            )
        ).get("responseData", 0)

        total_new_leads_for_snapshot = (
            await LeadRepository.get_leads_count_by_filter(
                db,
                {
                    "lead_form_snapshot_id": lead_form_snapshot_id,
                    "lead_status": LeadStatusEnum.NEW.value,
                },
            )
        ).get("responseData", 0)

        lead_form_snapshot["metadata"] = {
            "total_leads": total_leads_for_snapshot,
            "new_leads": total_new_leads_for_snapshot,
        }

        return lead_form_snapshot
