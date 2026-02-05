"""
Apollo Lead Job Service - Worker Handler for Apollo Individual & Organizational Lead Generation

This service handles Apollo lead generation jobs (PERSON and ORGANIZATION form types)
that are queued to Azure Service Bus. It replaces the old APScheduler global jobs
with a per-user, per-form queue-based architecture.

Key Features:
- Per-user frequency control (monitoring_interval_hours)
- Automatic re-queuing for recurring monitoring
- Progress tracking via LeadGenerationJobRepository
- Runs in worker process, not web server
- Supports trial usage tracking via UriBackendService

Architecture:
    Frontend → LeadFormService.create() → Azure Service Bus Queue → ApolloLeadJobService.process_apollo_job()
    After completion, if monitoring_interval_hours > 0, re-queue for next cycle.

Usage:
    Called by LeadGenerationConsumer when it receives Apollo job from queue.
"""
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.services.ApolloService import ApolloService
from app.repository.LeadGenerationJobRepository import LeadGenerationJobRepository
from app.services.uri_microservices.UriBackendService import UriBackendService


class ApolloLeadJobService:
    """
    Worker service for Apollo lead generation jobs (Individual and Organizational leads)
    """

    @staticmethod
    async def process_apollo_job(
        db: AsyncIOMotorDatabase,
        lead_form: dict,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a single Apollo lead generation job from the queue.

        Args:
            db: MongoDB database instance
            lead_form: Lead form data including:
                - form_type: "PERSON" or "ORGANIZATION"
                - user_id: User who created the form
                - lead_form_id: Form ID
                - monitoring_interval_hours: 0 = one-time, >0 = recurring
                - auto_generate: Must be True for recurring jobs
                - [Other Apollo search parameters]
            job_id: Job tracking ID from LeadGenerationJobRepository

        Returns:
            dict: {
                "success": bool,
                "leads_generated": int,
                "duplicates_skipped": int,
                "error": str (if failed)
            }
        """
        lead_form_id = lead_form.get("lead_form_id")
        user_id = lead_form.get("user_id")
        form_type = lead_form.get("form_type")
        monitoring_interval_hours = lead_form.get("monitoring_interval_hours", 0)

        print("=" * 80)
        print(f"🎯 Apollo Lead Job Processing Started")
        print(f"   Form Type: {form_type}")
        print(f"   Lead Form ID: {lead_form_id}")
        print(f"   User ID: {user_id}")
        print(f"   Job ID: {job_id}")
        print(f"   Monitoring Interval: {monitoring_interval_hours}h")
        print(f"   Recurring: {'Yes' if monitoring_interval_hours > 0 else 'No (One-time)'}")
        print("=" * 80)

        stats = {
            "success": False,
            "leads_generated": 0,
            "duplicates_skipped": 0,
            "error": None
        }

        async def update_progress(progress: int, message: str):
            """Helper to update job progress"""
            if job_id:
                await LeadGenerationJobRepository.update_job(
                    db=db,
                    job_id=job_id,
                    status="processing",
                    progress=progress,
                    message=message
                )

        try:
            # Update job to processing state
            if job_id:
                await update_progress(5, "Initializing Apollo search...")

            # Validate form type
            if form_type not in ["PERSON", "ORGANIZATION"]:
                raise ValueError(f"Invalid form_type: {form_type}. Must be PERSON or ORGANIZATION.")

            await update_progress(10, f"Calling Apollo API for {form_type} search...")

            # Call Apollo API based on form type
            if form_type == "PERSON":
                print(f"📞 Calling Apollo People Search API...")
                result = await ApolloService.handle_people_leads_gen(lead_form, user_id, db)
            else:  # ORGANIZATION
                print(f"📞 Calling Apollo Organization Search API...")
                result = await ApolloService.handle_organization_leads_gen(lead_form, user_id, db)

            await update_progress(70, "Processing Apollo search results...")

            # Parse result
            if not result or not result.get("status"):
                error_msg = result.get("message", "Apollo API returned no data") if result else "No response from Apollo"
                raise Exception(error_msg)

            response_data = result.get("responseData", {})
            leads = response_data.get("leads", [])
            duplicates = response_data.get("duplicates_skipped", 0)

            stats["leads_generated"] = len(leads)
            stats["duplicates_skipped"] = duplicates
            stats["success"] = True

            print(f"✅ Apollo search completed:")
            print(f"   New leads: {stats['leads_generated']}")
            print(f"   Duplicates skipped: {stats['duplicates_skipped']}")

            await update_progress(90, "Updating trial usage...")

            # Update trial usage counter (for trial users)
            # This increments the trialLeadsGenerated counter in uri-backend
            try:
                if stats["leads_generated"] > 0:
                    await UriBackendService.increment_trial_usage(
                        user_id=user_id,
                        leads_count=stats["leads_generated"]
                    )
                    print(f"   Trial usage updated: +{stats['leads_generated']} leads")
            except Exception as trial_error:
                # Don't fail the job if trial tracking fails
                print(f"⚠️ Failed to update trial usage: {trial_error}")

            await update_progress(100, "Completed successfully")

            # Mark job as completed
            if job_id:
                message = f"Generated {stats['leads_generated']} new leads"
                if stats["duplicates_skipped"] > 0:
                    message += f". {stats['duplicates_skipped']} duplicates were already in your database."

                await LeadGenerationJobRepository.update_job(
                    db=db,
                    job_id=job_id,
                    status="completed",
                    progress=100,
                    message=message,
                    stats=stats
                )
                print(f"✅ Job {job_id} completed: {message}")

            # RE-QUEUE FOR RECURRING MONITORING (if enabled)
            if monitoring_interval_hours and monitoring_interval_hours > 0:
                try:
                    from app.services.azure.producers.LeadGenerationProducer import LeadGenerationProducer

                    print(f"🔄 Recurring monitoring enabled: scheduling next run in {monitoring_interval_hours} hour(s)")

                    # Create a NEW job_id for the next monitoring cycle
                    # CRITICAL: Don't reuse the old job_id - workers will skip it as "completed"
                    next_job_id = await LeadGenerationJobRepository.create_job(
                        db=db,
                        lead_form_id=lead_form_id,
                        user_id=user_id,
                        status="queued",
                        progress=0,
                        message=f"Scheduled recurring Apollo monitoring (every {monitoring_interval_hours}h)"
                    )

                    # Create a fresh lead_form copy with the NEW job_id
                    next_lead_form = {**lead_form, "job_id": next_job_id}

                    # Schedule the next job execution using Azure Service Bus scheduled messages
                    await LeadGenerationProducer.schedule_lead_generation_job(
                        lead_form_id=lead_form_id,
                        user_id=user_id,
                        lead_form=next_lead_form,  # Use fresh copy with new job_id
                        delay_hours=monitoring_interval_hours
                    )
                    print(f"✅ Next Apollo monitoring job {next_job_id} scheduled for {monitoring_interval_hours} hour(s) from now")
                except Exception as schedule_error:
                    # Don't fail the entire job if scheduling fails
                    print(f"⚠️ Failed to schedule next monitoring job: {schedule_error}")
                    print(f"   Current job completed successfully, but recurring monitoring stopped.")
            else:
                print(f"✨ One-time execution completed. No recurring monitoring scheduled (monitoring_interval_hours={monitoring_interval_hours}).")

        except Exception as e:
            error_msg = str(e)
            stats["error"] = error_msg
            stats["success"] = False

            print(f"❌ Apollo Lead Job Failed: {error_msg}")

            if job_id:
                await LeadGenerationJobRepository.update_job(
                    db=db,
                    job_id=job_id,
                    status="failed",
                    progress=0,
                    message=f"Failed: {error_msg}",
                    stats=stats
                )

        print("=" * 80)
        print(f"🏁 Apollo Lead Job Processing Complete")
        print(f"   Success: {stats['success']}")
        print(f"   Leads Generated: {stats['leads_generated']}")
        print(f"   Duplicates Skipped: {stats['duplicates_skipped']}")
        if stats["error"]:
            print(f"   Error: {stats['error']}")
        print("=" * 80)

        return stats
