import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.core.config import settings
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.services.SocialMediaPostService import SocialMediaPostService
from app.services.LeadService import LeadService


class BackgroundService:
    # APScheduler setup
    @staticmethod
    def start_scheduler(db: AsyncIOMotorDatabase):
        """
        Start the APScheduler and add the job for tracking keywords.
        """
        scheduler = AsyncIOScheduler()
        scheduler.start()

        test_minutes = getattr(settings, "LEAD_GENERATION_INTERVAL_MINUTES_FOR_TEST", None)
        if test_minutes:
            scheduler.add_job(
                func=LeadService.run_lead_generation_chain,
                trigger="interval",
                minutes=test_minutes,
                next_run_time=datetime.utcnow(),
                kwargs={"db": db},
                id="generate_leads_job",
                replace_existing=False,
            )
        else:
            scheduler.add_job(
                func=LeadService.run_lead_generation_chain,
                trigger="interval",
                hours=settings.LEAD_GENERATION_INTERVAL,
                kwargs={"db": db},
                id="generate_leads_job",
                replace_existing=False,
            )

        # DISABLED: Old global scheduler jobs for Twitter/TikTok/Facebook
        # These jobs have been replaced by the new per-user queue-based architecture
        # using ConversationalLeadJobService + workers.
        #
        # Why disabled:
        # 1. Old jobs don't track trial usage (trialLeadsGenerated counter)
        # 2. Old jobs run globally for ALL users at fixed intervals (no per-user control)
        # 3. Old jobs run in uri-insights web server (should only run in workers)
        # 4. New architecture supports per-user monitoring_interval_hours from frontend
        # 5. New architecture properly increments lead count via UriBackendService.increment_trial_usage()
        #
        # Real-time monitoring is now handled by:
        # - User submits form with monitoring_interval_hours (1, 3, 6, 12, 24 hours)
        # - Backend queues job via Azure Service Bus
        # - Workers process via LeadGenerationConsumer → ConversationalLeadJobService
        # - Job is re-queued based on user's monitoring_interval_hours setting
        #
        # if test_minutes:
        #     scheduler.add_job(
        #         func=LeadService.fetch_and_save_conversational_twitter_leads,
        #         trigger="interval",
        #         minutes=test_minutes,
        #         next_run_time=datetime.utcnow(),
        #         kwargs={"db": db},
        #         id="conversational_twitter_fetch_job",
        #         replace_existing=False,
        #     )
        # else:
        #     scheduler.add_job(
        #         func=LeadService.fetch_and_save_conversational_twitter_leads,
        #         trigger="interval",
        #         hours=1,
        #         kwargs={"db": db},
        #         id="conversational_twitter_fetch_job",
        #         replace_existing=False,
        #     )
        #
        # if test_minutes:
        #     scheduler.add_job(
        #         func=LeadService.fetch_and_save_conversational_tiktok_leads,
        #         trigger="interval",
        #         minutes=test_minutes,
        #         next_run_time=datetime.utcnow(),
        #         kwargs={"db": db},
        #         id="conversational_tiktok_fetch_job",
        #         replace_existing=False,
        #     )
        # else:
        #     scheduler.add_job(
        #         func=LeadService.fetch_and_save_conversational_tiktok_leads,
        #         trigger="interval",
        #         hours=1,
        #         kwargs={"db": db},
        #         id="conversational_tiktok_fetch_job",
        #         replace_existing=False,
        #     )
        #
        # if test_minutes:
        #     scheduler.add_job(
        #         func=LeadService.fetch_and_save_conversational_facebook_leads,
        #         trigger="interval",
        #         minutes=test_minutes,
        #         next_run_time=datetime.utcnow(),
        #         kwargs={"db": db},
        #         id="conversational_facebook_fetch_job",
        #         replace_existing=False,
        #     )
        # else:
        #     scheduler.add_job(
        #         func=LeadService.fetch_and_save_conversational_facebook_leads,
        #         trigger="interval",
        #         hours=1,
        #         kwargs={"db": db},
        #         id="conversational_facebook_fetch_job",
        #         replace_existing=False,
        #     )

        scheduler.add_job(
            SocialMediaPostService.post_scheduled_posts,
            trigger="interval",
            minutes=5,
            kwargs={"db": db},
            id="post_scheduled_posts",
            replace_existing=False,
        )

        from app.agents.social_media_manager.services.approval_workflow_service import ApprovalWorkflowService
        scheduler.add_job(
            ApprovalWorkflowService.publish_scheduled_content,
            trigger="interval",
            minutes=1,
            kwargs={"db": db},
            id="publish_scheduled_social_posts",
            replace_existing=True,
        )

        from app.agents.social_media_manager.services.auto_content_service import AutoContentService
        scheduler.add_job(
            AutoContentService.run_scheduled_auto_generation,
            trigger="cron",
            hour=9,
            minute=0,
            kwargs={"db": db},
            id="auto_content_generation",
            replace_existing=True,
        )

        # Lazarus Auto-Detection: Scan for dead leads daily at 2 AM
        scheduler.add_job(
            func=BackgroundService.run_auto_dead_lead_detection,
            trigger="cron",
            hour=2,
            minute=0,
            kwargs={"db": db},
            id="auto_dead_lead_detection",
            replace_existing=True,
        )

        return scheduler

    @staticmethod
    async def run_auto_dead_lead_detection(db: AsyncIOMotorDatabase):
        """
        Background job to auto-detect and mark dead leads
        Runs daily at 2 AM for all users with auto-detection enabled
        """
        from app.services.AutoDeadLeadDetectionService import AutoDeadLeadDetectionService

        print(f"[{datetime.utcnow()}] Starting auto-dead-lead-detection job...")

        try:
            # Get all users with auto-detection enabled
            rules_collection = db["dead_lead_detection_rules"]
            enabled_users = await rules_collection.find({"enabled": True}).to_list(None)

            total_users = len(enabled_users)
            total_marked = 0
            total_added_to_lazarus = 0

            print(f"Found {total_users} users with auto-detection enabled")

            for user_rule in enabled_users:
                user_id = user_rule["user_id"]
                detection_rules = user_rule.get("detection_rules", {})
                next_scan_date = user_rule.get("next_scan_date")

                # Check if scan is due based on next_scan_date
                if next_scan_date and datetime.utcnow() < next_scan_date:
                    print(f"  Skipping user {user_id} - next scan not due until {next_scan_date}")
                    continue

                print(f"  Scanning user {user_id}...")

                try:
                    # Run scan for this user
                    scan_result = await AutoDeadLeadDetectionService.scan_for_dead_leads(
                        db, user_id, detection_rules
                    )

                    # Save to history
                    await AutoDeadLeadDetectionService.save_scan_result(
                        db, user_id, scan_result
                    )

                    total_marked += scan_result["marked_dead"]
                    total_added_to_lazarus += scan_result["added_to_lazarus"]

                    print(f"    ✓ Marked {scan_result['marked_dead']} leads as dead, "
                          f"added {scan_result['added_to_lazarus']} to Lazarus")

                    # Update next scan date based on schedule
                    schedule = user_rule.get("schedule", "weekly")
                    if schedule == "daily":
                        next_scan = datetime.utcnow() + timedelta(days=1)
                    elif schedule == "weekly":
                        next_scan = datetime.utcnow() + timedelta(weeks=1)
                    else:  # monthly
                        next_scan = datetime.utcnow() + timedelta(days=30)

                    await rules_collection.update_one(
                        {"user_id": user_id},
                        {"$set": {
                            "last_scan_date": datetime.utcnow(),
                            "next_scan_date": next_scan
                        }}
                    )

                except Exception as user_error:
                    print(f"    ✗ Error scanning user {user_id}: {str(user_error)}")
                    continue

            print(f"[{datetime.utcnow()}] Auto-dead-lead-detection job completed: "
                  f"{total_marked} total leads marked dead, "
                  f"{total_added_to_lazarus} added to Lazarus")

        except Exception as e:
            print(f"[{datetime.utcnow()}] ERROR in auto-dead-lead-detection job: {str(e)}")
