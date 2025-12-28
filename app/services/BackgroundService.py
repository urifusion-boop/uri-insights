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

        return scheduler
