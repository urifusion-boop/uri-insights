"""
Twitter Content Parser
Extracts and structures tweet data from scraped Twitter pages.
"""
from typing import Dict, List, Optional
from datetime import datetime
from playwright.async_api import Page, ElementHandle
import logging
import re

logger = logging.getLogger(__name__)


class TwitterContentParser:
    """Parse and extract structured data from Twitter pages."""

    @staticmethod
    async def parse_tweet(tweet_element: ElementHandle) -> Optional[Dict]:
        """
        Parse a single tweet element and extract all relevant data.

        Args:
            tweet_element: Playwright ElementHandle for a tweet

        Returns:
            Dict with tweet data or None if parsing fails
        """
        try:
            tweet_data = {}

            # Extract tweet text/content
            tweet_data["content"] = await TwitterContentParser._extract_tweet_text(tweet_element)

            # Extract author information
            author_info = await TwitterContentParser._extract_author_info(tweet_element)
            tweet_data.update(author_info)

            # Extract tweet metadata
            metadata = await TwitterContentParser._extract_metadata(tweet_element)
            tweet_data.update(metadata)

            # Extract engagement metrics
            engagement = await TwitterContentParser._extract_engagement_metrics(tweet_element)
            tweet_data["engagement_metrics"] = engagement

            # Generate tweet URL
            if tweet_data.get("author_handle") and tweet_data.get("tweet_id"):
                tweet_data["url"] = f"https://twitter.com/{tweet_data['author_handle']}/status/{tweet_data['tweet_id']}"

            return tweet_data

        except Exception as e:
            logger.error(f"Error parsing tweet: {e}")
            return None

    @staticmethod
    async def _extract_tweet_text(tweet_element: ElementHandle) -> str:
        """Extract the main text content of the tweet."""
        try:
            # Twitter uses different selectors for tweet text
            selectors = [
                '[data-testid="tweetText"]',
                'div[lang]',
                '[class*="tweet-text"]'
            ]

            for selector in selectors:
                text_element = await tweet_element.query_selector(selector)
                if text_element:
                    text = await text_element.text_content()
                    return text.strip() if text else ""

            return ""

        except Exception as e:
            logger.error(f"Error extracting tweet text: {e}")
            return ""

    @staticmethod
    async def _extract_author_info(tweet_element: ElementHandle) -> Dict:
        """Extract author name, handle, and profile URL."""
        try:
            author_data = {
                "author_name": "",
                "author_handle": "",
                "author_url": ""
            }

            # Extract author name
            name_element = await tweet_element.query_selector('[data-testid="User-Name"]')
            if name_element:
                name_text = await name_element.text_content()
                # Parse name and handle from format: "Display Name @username"
                if name_text:
                    parts = name_text.split('@')
                    if len(parts) >= 2:
                        author_data["author_name"] = parts[0].strip()
                        author_data["author_handle"] = parts[1].split()[0].strip()

            # Alternative: Extract handle from link
            if not author_data["author_handle"]:
                handle_link = await tweet_element.query_selector('a[href^="/"][role="link"]')
                if handle_link:
                    href = await handle_link.get_attribute('href')
                    if href:
                        author_data["author_handle"] = href.strip('/').split('/')[0]

            # Build author URL
            if author_data["author_handle"]:
                author_data["author_url"] = f"https://twitter.com/{author_data['author_handle']}"

            return author_data

        except Exception as e:
            logger.error(f"Error extracting author info: {e}")
            return {"author_name": "", "author_handle": "", "author_url": ""}

    @staticmethod
    async def _extract_metadata(tweet_element: ElementHandle) -> Dict:
        """Extract tweet metadata like timestamp and tweet ID."""
        try:
            metadata = {
                "posted_at": None,
                "tweet_id": ""
            }

            # Extract timestamp
            time_element = await tweet_element.query_selector('time')
            if time_element:
                datetime_str = await time_element.get_attribute('datetime')
                if datetime_str:
                    try:
                        metadata["posted_at"] = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
                    except Exception:
                        metadata["posted_at"] = datetime.utcnow()

            # Extract tweet ID from link
            link_element = await tweet_element.query_selector('a[href*="/status/"]')
            if link_element:
                href = await link_element.get_attribute('href')
                if href:
                    match = re.search(r'/status/(\d+)', href)
                    if match:
                        metadata["tweet_id"] = match.group(1)

            return metadata

        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
            return {"posted_at": datetime.utcnow(), "tweet_id": ""}

    @staticmethod
    async def _extract_engagement_metrics(tweet_element: ElementHandle) -> Dict:
        """Extract likes, retweets, replies, and views counts."""
        try:
            metrics = {
                "likes": 0,
                "retweets": 0,
                "replies": 0,
                "views": 0
            }

            # Twitter engagement buttons have data-testid attributes
            engagement_selectors = {
                "replies": '[data-testid="reply"]',
                "retweets": '[data-testid="retweet"]',
                "likes": '[data-testid="like"]',
                "views": '[data-testid="views"]'
            }

            for metric, selector in engagement_selectors.items():
                element = await tweet_element.query_selector(selector)
                if element:
                    text = await element.text_content()
                    if text:
                        # Extract number from text (e.g., "123" or "1.2K")
                        count = TwitterContentParser._parse_count(text)
                        metrics[metric] = count

            return metrics

        except Exception as e:
            logger.error(f"Error extracting engagement metrics: {e}")
            return {"likes": 0, "retweets": 0, "replies": 0, "views": 0}

    @staticmethod
    def _parse_count(count_str: str) -> int:
        """Parse engagement count strings like '1.2K', '3M' to integers."""
        try:
            count_str = count_str.strip().upper()

            # Remove any non-numeric characters except K, M, B, .
            count_str = re.sub(r'[^\d.KMB]', '', count_str)

            if not count_str:
                return 0

            multipliers = {
                'K': 1000,
                'M': 1000000,
                'B': 1000000000
            }

            for suffix, multiplier in multipliers.items():
                if suffix in count_str:
                    number = float(count_str.replace(suffix, ''))
                    return int(number * multiplier)

            return int(float(count_str))

        except Exception:
            return 0

    @staticmethod
    async def extract_tweets_from_page(page: Page) -> List[Dict]:
        """
        Extract all tweets from a Twitter page (search results, timeline, etc.).

        Args:
            page: Playwright Page object

        Returns:
            List of parsed tweet dictionaries
        """
        try:
            tweets = []

            # Wait for tweets to load
            await page.wait_for_selector('[data-testid="tweet"]', timeout=10000)

            # Get all tweet elements
            tweet_elements = await page.query_selector_all('[data-testid="tweet"]')

            logger.info(f"Found {len(tweet_elements)} tweets on page")

            for tweet_element in tweet_elements:
                tweet_data = await TwitterContentParser.parse_tweet(tweet_element)
                if tweet_data and tweet_data.get("content"):
                    tweets.append(tweet_data)

            return tweets

        except Exception as e:
            logger.error(f"Error extracting tweets from page: {e}")
            return []

    @staticmethod
    def match_keywords(content: str, keywords: List[str]) -> List[str]:
        """
        Match keywords in tweet content (case-insensitive).

        Args:
            content: Tweet text content
            keywords: List of keywords to match

        Returns:
            List of matched keywords
        """
        content_lower = content.lower()
        matched = []

        for keyword in keywords:
            if keyword.lower() in content_lower:
                matched.append(keyword)

        return matched

    @staticmethod
    def match_buying_signals(content: str, signals: List[str]) -> List[str]:
        """
        Match buying signals in tweet content (case-insensitive).

        Args:
            content: Tweet text content
            signals: List of buying signals to match

        Returns:
            List of matched buying signals
        """
        return TwitterContentParser.match_keywords(content, signals)
