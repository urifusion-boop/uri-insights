"""
Twitter Monitoring Orchestrator
Coordinates Twitter monitoring tasks and integrates with lead processing pipeline.
"""
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

from app.services.TwitterPlaywrightService import TwitterPlaywrightService
from app.services.RealtimeLeadProcessor import RealtimeLeadProcessor
from app.repository.LeadFormRepository import LeadFormRepository
from app.domain.schemas.browsercloud_schema import BrowsercloudSocialPost

logger = logging.getLogger(__name__)


class TwitterMonitoringTask:
    """Represents a single Twitter monitoring task."""

    def __init__(
        self,
        task_id: str,
        lead_form_id: str,
        user_id: str,
        keywords: List[str],
        buying_signals: List[str],
        excluded_keywords: Optional[List[str]] = None,
        poll_interval: int = 60
    ):
        self.task_id = task_id
        self.lead_form_id = lead_form_id
        self.user_id = user_id
        self.keywords = keywords
        self.buying_signals = buying_signals
        self.excluded_keywords = excluded_keywords or []
        self.poll_interval = poll_interval
        self.is_running = False
        self.created_at = datetime.utcnow()
        self.last_run = None
        self.tweets_processed = 0
        self.leads_generated = 0


class TwitterMonitoringOrchestrator:
    """
    Orchestrates Twitter monitoring tasks using Playwright.
    Manages multiple monitoring tasks and integrates with lead processing.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.twitter_service = TwitterPlaywrightService()
        self.lead_processor = RealtimeLeadProcessor()
        self.active_tasks: Dict[str, TwitterMonitoringTask] = {}
        self.monitoring_loop_task: Optional[asyncio.Task] = None
        self.is_initialized = False

    async def initialize(self, twitter_username: str, twitter_password: str):
        """
        Initialize the orchestrator and login to Twitter.

        Args:
            twitter_username: Twitter account username
            twitter_password: Twitter account password
        """
        try:
            logger.info("Initializing Twitter Monitoring Orchestrator...")
            await self.twitter_service.initialize()

            # Login to Twitter
            success = await self.twitter_service.login_to_twitter(
                twitter_username,
                twitter_password
            )

            if not success:
                raise Exception("Failed to login to Twitter")

            self.is_initialized = True
            logger.info("Twitter Monitoring Orchestrator initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize orchestrator: {e}")
            raise

    async def start_monitoring_for_lead_form(self, lead_form_id: str) -> str:
        """
        Start Twitter monitoring for a specific lead form.

        Args:
            lead_form_id: ID of the lead form to monitor

        Returns:
            Task ID
        """
        try:
            # Fetch lead form from database
            lead_form = await LeadFormRepository.get_by_id(self.db, lead_form_id)

            if not lead_form or not lead_form.get("data"):
                raise ValueError(f"Lead form {lead_form_id} not found")

            form_data = lead_form["data"]

            # Extract monitoring parameters
            task = TwitterMonitoringTask(
                task_id=f"twitter_monitor_{lead_form_id}_{datetime.utcnow().timestamp()}",
                lead_form_id=lead_form_id,
                user_id=form_data.get("user_id", ""),
                keywords=form_data.get("keywords", []),
                buying_signals=form_data.get("buying_signals", []),
                excluded_keywords=form_data.get("excluded_keywords", []),
                poll_interval=60  # Poll every 60 seconds
            )

            # Add to active tasks
            self.active_tasks[task.task_id] = task

            logger.info(f"Started Twitter monitoring task: {task.task_id} for lead form: {lead_form_id}")

            # Start monitoring loop if not already running
            if not self.monitoring_loop_task or self.monitoring_loop_task.done():
                self.monitoring_loop_task = asyncio.create_task(self._monitoring_loop())

            return task.task_id

        except Exception as e:
            logger.error(f"Error starting monitoring for lead form {lead_form_id}: {e}")
            raise

    async def stop_monitoring_task(self, task_id: str) -> bool:
        """
        Stop a specific monitoring task.

        Args:
            task_id: ID of the task to stop

        Returns:
            True if stopped successfully
        """
        try:
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                task.is_running = False
                del self.active_tasks[task_id]
                logger.info(f"Stopped monitoring task: {task_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error stopping task {task_id}: {e}")
            return False

    async def _monitoring_loop(self):
        """Main monitoring loop that processes all active tasks."""
        logger.info("Starting Twitter monitoring loop...")

        while self.active_tasks:
            try:
                # Process each active task
                for task_id, task in list(self.active_tasks.items()):
                    try:
                        await self._process_monitoring_task(task)
                    except Exception as e:
                        logger.error(f"Error processing task {task_id}: {e}")

                # Wait before next iteration
                await asyncio.sleep(10)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(30)

        logger.info("Monitoring loop stopped - no active tasks")

    async def _process_monitoring_task(self, task: TwitterMonitoringTask):
        """
        Process a single monitoring task.

        Args:
            task: TwitterMonitoringTask to process
        """
        try:
            # Check if enough time has passed since last run
            if task.last_run:
                elapsed = (datetime.utcnow() - task.last_run).total_seconds()
                if elapsed < task.poll_interval:
                    return

            task.is_running = True
            task.last_run = datetime.utcnow()

            logger.info(f"Processing monitoring task: {task.task_id}")

            # Search Twitter for matching tweets
            tweets = await self.twitter_service.search_twitter(
                keywords=task.keywords,
                max_results=50
            )

            # Filter tweets by criteria
            matching_tweets = [
                tweet for tweet in tweets
                if self._tweet_matches_criteria(
                    tweet,
                    task.keywords,
                    task.buying_signals,
                    task.excluded_keywords
                )
            ]

            if matching_tweets:
                logger.info(f"Found {len(matching_tweets)} matching tweets for task {task.task_id}")

                # Convert to BrowsercloudSocialPost format
                social_posts = self._convert_tweets_to_posts(
                    matching_tweets,
                    task.keywords,
                    task.buying_signals
                )

                # Process leads through existing pipeline
                await self._process_leads(social_posts, task)

                task.tweets_processed += len(matching_tweets)

        except Exception as e:
            logger.error(f"Error processing task {task.task_id}: {e}")
        finally:
            task.is_running = False

    def _tweet_matches_criteria(
        self,
        tweet: Dict,
        keywords: List[str],
        buying_signals: List[str],
        excluded_keywords: List[str]
    ) -> bool:
        """Check if tweet matches the monitoring criteria."""
        content = tweet.get("content", "").lower()

        # Exclude tweets with excluded keywords
        for excluded in excluded_keywords:
            if excluded.lower() in content:
                return False

        # Must have at least one keyword or buying signal
        has_keyword = any(kw.lower() in content for kw in keywords)
        has_signal = any(signal.lower() in content for signal in buying_signals)

        return has_keyword or has_signal

    def _convert_tweets_to_posts(
        self,
        tweets: List[Dict],
        keywords: List[str],
        buying_signals: List[str]
    ) -> List[BrowsercloudSocialPost]:
        """Convert tweet dictionaries to BrowsercloudSocialPost objects."""
        return self.twitter_service._convert_to_social_posts(tweets, keywords, buying_signals)

    async def _process_leads(self, social_posts: List[BrowsercloudSocialPost], task: TwitterMonitoringTask):
        """
        Process social posts through the lead generation pipeline.

        Args:
            social_posts: List of social posts to process
            task: The monitoring task
        """
        try:
            # Create mock webhook payload
            payload = {
                "task_id": task.task_id,
                "platform": "twitter",
                "results": [post.dict() for post in social_posts]
            }

            # Process through existing RealtimeLeadProcessor
            # Note: We'll bypass signature validation for internal calls
            result = await self.lead_processor.process_browsercloud_webhook(
                self.db,
                payload,
                signature="",
                skip_validation=True  # Internal call, skip signature validation
            )

            if result.get("status"):
                leads_created = result.get("leads_created", 0)
                task.leads_generated += leads_created
                logger.info(f"Created {leads_created} leads from task {task.task_id}")
            else:
                logger.warning(f"Lead processing failed for task {task.task_id}: {result.get('message')}")

        except Exception as e:
            logger.error(f"Error processing leads for task {task.task_id}: {e}")

    async def get_task_status(self, task_id: str) -> Optional[Dict]:
        """
        Get status of a monitoring task.

        Args:
            task_id: ID of the task

        Returns:
            Task status dictionary or None
        """
        task = self.active_tasks.get(task_id)
        if not task:
            return None

        return {
            "task_id": task.task_id,
            "lead_form_id": task.lead_form_id,
            "user_id": task.user_id,
            "is_running": task.is_running,
            "created_at": task.created_at.isoformat(),
            "last_run": task.last_run.isoformat() if task.last_run else None,
            "tweets_processed": task.tweets_processed,
            "leads_generated": task.leads_generated,
            "poll_interval": task.poll_interval
        }

    async def get_all_tasks_status(self) -> List[Dict]:
        """Get status of all active monitoring tasks."""
        return [
            await self.get_task_status(task_id)
            for task_id in self.active_tasks.keys()
        ]

    async def cleanup(self):
        """Clean up resources and stop all tasks."""
        try:
            logger.info("Cleaning up Twitter Monitoring Orchestrator...")

            # Stop all tasks
            for task_id in list(self.active_tasks.keys()):
                await self.stop_monitoring_task(task_id)

            # Cancel monitoring loop
            if self.monitoring_loop_task and not self.monitoring_loop_task.done():
                self.monitoring_loop_task.cancel()

            # Cleanup Twitter service
            await self.twitter_service.cleanup()

            logger.info("Twitter Monitoring Orchestrator cleaned up")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
