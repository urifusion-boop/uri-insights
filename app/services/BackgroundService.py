import asyncio
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

        scheduler.add_job(
            func=LeadService.run_lead_generation_chain,
            trigger="interval",
            hours=settings.LEAD_GENERATION_INTERVAL,
            kwargs={"db": db},
            id="generate_leads_job",
            replace_existing=False,
        )

        # TODO: TESTING MODE - Change to minutes=1 for testing, then back to hours=1
        # Testing: runs every 1 minute | Production: runs every 1 hour
        testing_mode = settings.ENV.lower() != "production"

        scheduler.add_job(
            func=LeadService.fetch_and_save_conversational_twitter_leads,
            trigger="interval",
            minutes=1 if testing_mode else 60,  # 1 min for testing, 60 min for production
            kwargs={"db": db},
            id="conversational_twitter_fetch_job",
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
