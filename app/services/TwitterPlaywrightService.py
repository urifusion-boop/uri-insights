"""
Twitter Playwright Service
Manages Twitter scraping using Playwright via Browsercloud remote browsers.
"""
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
import logging
import random

from app.services.BrowsercloudConnectionManager import BrowsercloudConnectionManager
from app.services.TwitterContentParser import TwitterContentParser
from app.domain.schemas.browsercloud_schema import (
    BrowsercloudSocialPost,
    BrowsercloudPlatformEnum
)

logger = logging.getLogger(__name__)


class TwitterPlaywrightService:
    """Service for scraping Twitter using Playwright."""

    def __init__(self):
        self.connection_manager = BrowsercloudConnectionManager()
        self.parser = TwitterContentParser()
        self.is_logged_in = False
        self.current_page: Optional[Page] = None

    async def initialize(self):
        """Initialize browser connection."""
        try:
            await self.connection_manager.connect()
            await self.connection_manager.create_context()
            self.current_page = await self.connection_manager.new_page()
            logger.info("Twitter Playwright Service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Twitter service: {e}")
            raise

    async def login_to_twitter(self, username: str, password: str) -> bool:
        """
        Login to Twitter account.

        Args:
            username: Twitter username or email
            password: Twitter password

        Returns:
            True if login successful, False otherwise
        """
        try:
            if not self.current_page:
                await self.initialize()

            logger.info("Navigating to Twitter login page...")
            await self.current_page.goto("https://twitter.com/i/flow/login", wait_until="networkidle")

            # Wait for login form
            await self.current_page.wait_for_selector('input[autocomplete="username"]', timeout=10000)

            # Enter username
            await self.current_page.fill('input[autocomplete="username"]', username)
            await self._random_delay(1, 2)
            await self.current_page.press('input[autocomplete="username"]', 'Enter')

            # Wait for password field
            await self.current_page.wait_for_selector('input[name="password"]', timeout=10000)
            await self._random_delay(1, 2)

            # Enter password
            await self.current_page.fill('input[name="password"]', password)
            await self._random_delay(1, 2)
            await self.current_page.press('input[name="password"]', 'Enter')

            # Wait for login to complete
            await self.current_page.wait_for_url("**/home", timeout=30000)

            self.is_logged_in = True
            logger.info("Successfully logged in to Twitter")
            return True

        except PlaywrightTimeoutError:
            logger.error("Login timeout - possible 2FA or incorrect credentials")
            return False
        except Exception as e:
            logger.error(f"Error during Twitter login: {e}")
            return False

    async def search_twitter(
        self,
        keywords: List[str],
        max_results: int = 50,
        search_type: str = "Latest"
    ) -> List[Dict]:
        """
        Search Twitter for tweets matching keywords.

        Args:
            keywords: List of keywords to search for
            max_results: Maximum number of tweets to retrieve
            search_type: "Latest" or "Top"

        Returns:
            List of tweet dictionaries
        """
        try:
            if not self.is_logged_in:
                logger.warning("Not logged in to Twitter, search may be limited")

            if not self.current_page:
                await self.initialize()

            all_tweets = []

            for keyword in keywords:
                logger.info(f"Searching Twitter for: {keyword}")

                # Build search URL
                search_query = keyword.replace(' ', '%20')
                search_url = f"https://twitter.com/search?q={search_query}&src=typed_query"

                if search_type == "Latest":
                    search_url += "&f=live"

                # Navigate to search page
                await self.current_page.goto(search_url, wait_until="networkidle")
                await self._random_delay(2, 4)

                # Scroll and collect tweets
                tweets = await self._scroll_and_collect_tweets(max_results)
                all_tweets.extend(tweets)

                logger.info(f"Found {len(tweets)} tweets for keyword: {keyword}")

                # Rate limiting between searches
                await self._random_delay(3, 6)

            return all_tweets

        except Exception as e:
            logger.error(f"Error searching Twitter: {e}")
            return []

    async def _scroll_and_collect_tweets(self, max_results: int) -> List[Dict]:
        """
        Scroll through Twitter feed and collect tweets.

        Args:
            max_results: Maximum number of tweets to collect

        Returns:
            List of tweet dictionaries
        """
        collected_tweets = []
        seen_tweet_ids = set()
        scroll_attempts = 0
        max_scroll_attempts = 20

        try:
            while len(collected_tweets) < max_results and scroll_attempts < max_scroll_attempts:
                # Extract tweets from current view
                tweets = await self.parser.extract_tweets_from_page(self.current_page)

                # Add new tweets (avoid duplicates)
                for tweet in tweets:
                    tweet_id = tweet.get("tweet_id")
                    if tweet_id and tweet_id not in seen_tweet_ids:
                        collected_tweets.append(tweet)
                        seen_tweet_ids.add(tweet_id)

                        if len(collected_tweets) >= max_results:
                            break

                # Scroll down to load more tweets
                await self.current_page.evaluate("window.scrollBy(0, window.innerHeight)")
                await self._random_delay(1, 2)

                scroll_attempts += 1

            logger.info(f"Collected {len(collected_tweets)} unique tweets after {scroll_attempts} scrolls")
            return collected_tweets[:max_results]

        except Exception as e:
            logger.error(f"Error during scroll and collect: {e}")
            return collected_tweets

    async def monitor_twitter_realtime(
        self,
        keywords: List[str],
        buying_signals: List[str],
        excluded_keywords: Optional[List[str]] = None,
        callback=None,
        poll_interval: int = 60
    ):
        """
        Continuously monitor Twitter for new tweets matching criteria.

        Args:
            keywords: Keywords to search for
            buying_signals: Buying signals to match
            excluded_keywords: Keywords to exclude
            callback: Async function to call with new tweets
            poll_interval: Seconds between polls (default 60)
        """
        excluded_keywords = excluded_keywords or []
        last_tweet_ids = set()

        logger.info(f"Starting real-time Twitter monitoring (poll interval: {poll_interval}s)")

        while True:
            try:
                # Check if browser connection is alive
                if not await self.connection_manager.is_browser_alive():
                    logger.warning("Browser connection lost, reconnecting...")
                    await self.connection_manager.reconnect()
                    await self.initialize()

                # Search for tweets
                tweets = await self.search_twitter(keywords, max_results=100)

                # Filter and process new tweets
                new_tweets = []
                for tweet in tweets:
                    tweet_id = tweet.get("tweet_id")

                    # Skip if already seen
                    if tweet_id in last_tweet_ids:
                        continue

                    # Check if tweet matches criteria
                    if self._matches_criteria(tweet, keywords, buying_signals, excluded_keywords):
                        new_tweets.append(tweet)
                        last_tweet_ids.add(tweet_id)

                # Process new tweets
                if new_tweets:
                    logger.info(f"Found {len(new_tweets)} new matching tweets")

                    # Convert to BrowsercloudSocialPost format
                    social_posts = self._convert_to_social_posts(new_tweets, keywords, buying_signals)

                    # Call callback if provided
                    if callback:
                        await callback(social_posts)

                # Clean up old tweet IDs (keep last 1000)
                if len(last_tweet_ids) > 1000:
                    last_tweet_ids = set(list(last_tweet_ids)[-1000:])

                # Wait before next poll
                logger.info(f"Waiting {poll_interval}s before next poll...")
                await asyncio.sleep(poll_interval)

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(poll_interval)

    def _matches_criteria(
        self,
        tweet: Dict,
        keywords: List[str],
        buying_signals: List[str],
        excluded_keywords: List[str]
    ) -> bool:
        """Check if tweet matches search criteria."""
        content = tweet.get("content", "").lower()

        # Check excluded keywords
        for excluded in excluded_keywords:
            if excluded.lower() in content:
                return False

        # Check if has at least one keyword or buying signal
        has_keyword = any(kw.lower() in content for kw in keywords)
        has_signal = any(signal.lower() in content for signal in buying_signals)

        return has_keyword or has_signal

    def _convert_to_social_posts(
        self,
        tweets: List[Dict],
        keywords: List[str],
        buying_signals: List[str]
    ) -> List[BrowsercloudSocialPost]:
        """Convert tweet dictionaries to BrowsercloudSocialPost objects."""
        social_posts = []

        for tweet in tweets:
            content = tweet.get("content", "")

            # Match keywords and signals
            matched_keywords = self.parser.match_keywords(content, keywords)
            matched_signals = self.parser.match_buying_signals(content, buying_signals)

            post = BrowsercloudSocialPost(
                platform=BrowsercloudPlatformEnum.TWITTER,
                post_id=tweet.get("tweet_id", ""),
                content=content,
                url=tweet.get("url", ""),
                author_name=tweet.get("author_name", ""),
                author_handle=tweet.get("author_handle", ""),
                author_url=tweet.get("author_url", ""),
                posted_at=tweet.get("posted_at", datetime.utcnow()),
                engagement_metrics=tweet.get("engagement_metrics", {}),
                matched_keywords=matched_keywords,
                matched_signals=matched_signals
            )

            social_posts.append(post)

        return social_posts

    async def _random_delay(self, min_seconds: float = 1, max_seconds: float = 3):
        """Add random delay to mimic human behavior."""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)

    async def cleanup(self):
        """Clean up browser resources."""
        try:
            if self.current_page:
                await self.current_page.close()
                self.current_page = None

            await self.connection_manager.disconnect()
            logger.info("Twitter Playwright Service cleaned up")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def __aenter__(self):
        """Context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.cleanup()
