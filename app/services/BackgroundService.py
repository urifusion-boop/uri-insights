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

        if test_minutes:
            scheduler.add_job(
                func=LeadService.fetch_and_save_conversational_twitter_leads,
                trigger="interval",
                minutes=test_minutes,
                next_run_time=datetime.utcnow(),
                kwargs={"db": db},
                id="conversational_twitter_fetch_job",
                replace_existing=False,
            )
        else:
            scheduler.add_job(
                func=LeadService.fetch_and_save_conversational_twitter_leads,
                trigger="interval",
                hours=1,
                kwargs={"db": db},
                id="conversational_twitter_fetch_job",
                replace_existing=False,
            )

        if test_minutes:
            scheduler.add_job(
                func=LeadService.fetch_and_save_conversational_tiktok_leads,
                trigger="interval",
                minutes=test_minutes,
                next_run_time=datetime.utcnow(),
                kwargs={"db": db},
                id="conversational_tiktok_fetch_job",
                replace_existing=False,
            )
        else:
            scheduler.add_job(
                func=LeadService.fetch_and_save_conversational_tiktok_leads,
                trigger="interval",
                hours=1,
                kwargs={"db": db},
                id="conversational_tiktok_fetch_job",
                replace_existing=False,
            )

        scheduler.add_job(
            SocialMediaPostService.post_scheduled_posts,
            trigger="interval",
            minutes=5,
            kwargs={"db": db},
            id="post_scheduled_posts",
            replace_existing=False,
        )

        return scheduler
