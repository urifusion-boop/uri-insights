"""
CRM Sync Service
PRD Section 4.4: CRM Integration

Orchestrates syncing data from HubSpot and Salesforce:
- Auto-imports stalled deals/opportunities as focus contacts
- Auto-imports closed-lost deals/opportunities as focus contacts
- Auto-imports associated companies as company monitors
- Updates sync statistics
- Logs sync operations for tracking
"""
from typing import Dict, Any, List
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime

from app.services.HubSpotService import HubSpotService
from app.services.SalesforceService import SalesforceService
from app.services.LazarusService import LazarusService
from app.domain.schemas.lazarus_schema import FocusContactCreate, CompanyMonitorCreate
from app.repository.CRMSyncLogRepository import CRMSyncLogRepository


class CRMSyncService:
    """Service for syncing CRM data into Lazarus Protocol"""

    @staticmethod
    async def sync_crm_data(
        db: AsyncIOMotorDatabase,
        user_id: str,
        crm_type: str,
        connection: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Sync data from CRM to Lazarus Protocol with logging
        PRD: Auto-import stalled deals and closed-lost leads

        Args:
            db: Database connection
            user_id: User ID
            crm_type: "hubspot" or "salesforce"
            connection: CRM connection details with access token

        Returns:
            Success status with counts of contacts and companies added
        """
        # Create sync log entry
        log_id = await CRMSyncLogRepository.create_sync_log(db, user_id, crm_type)

        try:
            if crm_type == "hubspot":
                result = await CRMSyncService._sync_hubspot_data(db, user_id, connection)
            elif crm_type == "salesforce":
                result = await CRMSyncService._sync_salesforce_data(db, user_id, connection)
            else:
                error_msg = f"Unsupported CRM type: {crm_type}"
                if log_id:
                    await CRMSyncLogRepository.complete_sync_log(
                        db, log_id, "failed", {},
                        error_message=error_msg,
                        error_type="invalid_crm_type"
                    )
                return {
                    "success": False,
                    "message": error_msg,
                }

            # Update last sync time
            from app.repository.CRMRepository import CRMRepository
            await CRMRepository.update_last_sync(
                db,
                user_id,
                result.get("contacts_added", 0),
                result.get("companies_added", 0),
            )

            # Complete sync log with success
            if log_id:
                await CRMSyncLogRepository.complete_sync_log(
                    db,
                    log_id,
                    "success",
                    {
                        "contacts_added": result.get("contacts_added", 0),
                        "companies_added": result.get("companies_added", 0),
                        "deals_processed": result.get("deals_processed", 0),
                    }
                )

            return result

        except Exception as e:
            error_msg = f"CRM sync failed: {str(e)}"

            # Track error in CRM connection
            from app.repository.CRMRepository import CRMRepository
            await CRMRepository.update_error_tracking(
                db, user_id, error_msg, error_type="sync_error"
            )

            # Complete sync log with failure
            if log_id:
                await CRMSyncLogRepository.complete_sync_log(
                    db, log_id, "failed", {},
                    error_message=error_msg,
                    error_type="sync_error"
                )

            return {
                "success": False,
                "message": error_msg,
            }

    @staticmethod
    async def _sync_hubspot_data(
        db: AsyncIOMotorDatabase,
        user_id: str,
        connection: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Sync HubSpot deals and contacts

        Args:
            db: Database connection
            user_id: User ID
            connection: HubSpot connection with access token

        Returns:
            Counts of contacts and companies added
        """
        access_token = connection["access_token"]
        contacts_added = 0
        companies_added = 0

        try:
            # 1. Fetch stalled deals
            stalled_deals = await HubSpotService.fetch_stalled_deals(db, user_id, access_token)

            # 2. Fetch closed-lost deals
            closed_lost_deals = await HubSpotService.fetch_closed_lost_deals(db, user_id, access_token)

            # 3. Process all deals and add contacts
            all_deals = stalled_deals + closed_lost_deals

            for deal in all_deals:
                deal_id = deal.get("deal_id") or deal.get("id")

                # Fetch contacts from deal
                contacts = await HubSpotService.fetch_contacts_from_deal(
                    db, user_id, access_token, deal_id
                )

                # Add each contact to Lazarus
                for contact in contacts:
                    if not contact.get("email"):
                        continue  # Skip contacts without email

                    # Check if contact already exists
                    from app.repository.LazarusRepository import LazarusRepository
                    existing = await LazarusRepository.get_focus_contact_by_email(
                        db, user_id, contact["email"]
                    )

                    if existing:
                        continue  # Skip duplicates

                    # Create focus contact
                    focus_contact = FocusContactCreate(
                        first_name=contact.get("first_name", ""),
                        last_name=contact.get("last_name", ""),
                        email=contact["email"],
                        company_name=contact.get("company", ""),
                        linkedin_url=None,
                        notes=f"Auto-imported from HubSpot deal: {deal.get('deal_name', 'Unknown')}",
                    )

                    # Add to Lazarus
                    result = await LazarusService.add_focus_contact(
                        db,
                        user_id,
                        focus_contact,
                        source_lead_id=None,
                    )

                    if result["success"]:
                        contacts_added += 1

                    # Add company if not already monitored
                    if contact.get("company"):
                        company_existing = await LazarusRepository.get_company_monitor_by_name(
                            db, user_id, contact["company"]
                        )

                        if not company_existing:
                            company_monitor = CompanyMonitorCreate(
                                company_name=contact["company"],
                                domain=None,
                                linkedin_url=None,
                                notes=f"Auto-imported from HubSpot deal: {deal.get('deal_name', 'Unknown')}",
                            )

                            company_result = await LazarusService.add_company_monitor(
                                db,
                                user_id,
                                company_monitor,
                                source_lead_id=None,
                            )

                            if company_result["success"]:
                                companies_added += 1

            return {
                "success": True,
                "message": "HubSpot sync completed",
                "contacts_added": contacts_added,
                "companies_added": companies_added,
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"HubSpot sync failed: {str(e)}",
                "contacts_added": contacts_added,
                "companies_added": companies_added,
            }

    @staticmethod
    async def _sync_salesforce_data(
        db: AsyncIOMotorDatabase,
        user_id: str,
        connection: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Sync Salesforce opportunities and contacts

        Args:
            db: Database connection
            user_id: User ID
            connection: Salesforce connection with access token and instance URL

        Returns:
            Counts of contacts and companies added
        """
        access_token = connection["access_token"]
        instance_url = connection["instance_url"]
        contacts_added = 0
        companies_added = 0

        try:
            # 1. Fetch stalled opportunities
            stalled_opps = await SalesforceService.fetch_stalled_opportunities(
                db, user_id, access_token, instance_url
            )

            # 2. Fetch closed-lost opportunities
            closed_lost_opps = await SalesforceService.fetch_closed_lost_opportunities(
                db, user_id, access_token, instance_url
            )

            # 3. Process all opportunities and add contacts
            all_opps = stalled_opps + closed_lost_opps

            for opp in all_opps:
                opp_id = opp.get("opportunity_id") or opp.get("Id")

                # Fetch contacts from opportunity
                contacts = await SalesforceService.fetch_contacts_from_opportunity(
                    db, user_id, access_token, instance_url, opp_id
                )

                # Add each contact to Lazarus
                for contact in contacts:
                    if not contact.get("email"):
                        continue  # Skip contacts without email

                    # Check if contact already exists
                    from app.repository.LazarusRepository import LazarusRepository
                    existing = await LazarusRepository.get_focus_contact_by_email(
                        db, user_id, contact["email"]
                    )

                    if existing:
                        continue  # Skip duplicates

                    # Create focus contact
                    focus_contact = FocusContactCreate(
                        first_name=contact.get("first_name", ""),
                        last_name=contact.get("last_name", ""),
                        email=contact["email"],
                        company_name=contact.get("company", ""),
                        linkedin_url=None,
                        notes=f"Auto-imported from Salesforce opportunity: {opp.get('opportunity_name', 'Unknown')}",
                    )

                    # Add to Lazarus
                    result = await LazarusService.add_focus_contact(
                        db,
                        user_id,
                        focus_contact,
                        source_lead_id=None,
                    )

                    if result["success"]:
                        contacts_added += 1

                    # Add company if not already monitored
                    if contact.get("company"):
                        company_existing = await LazarusRepository.get_company_monitor_by_name(
                            db, user_id, contact["company"]
                        )

                        if not company_existing:
                            company_monitor = CompanyMonitorCreate(
                                company_name=contact["company"],
                                domain=None,
                                linkedin_url=None,
                                notes=f"Auto-imported from Salesforce opportunity: {opp.get('opportunity_name', 'Unknown')}",
                            )

                            company_result = await LazarusService.add_company_monitor(
                                db,
                                user_id,
                                company_monitor,
                                source_lead_id=None,
                            )

                            if company_result["success"]:
                                companies_added += 1

            return {
                "success": True,
                "message": "Salesforce sync completed",
                "contacts_added": contacts_added,
                "companies_added": companies_added,
            }

        except Exception as e:
            return {
                "success": False,
                "message": f"Salesforce sync failed: {str(e)}",
                "contacts_added": contacts_added,
                "companies_added": companies_added,
            }
