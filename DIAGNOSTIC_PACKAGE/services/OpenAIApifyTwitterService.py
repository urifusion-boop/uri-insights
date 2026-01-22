import os
import asyncio
import hashlib
from typing import List, Dict, Any, Optional
from apify_client import ApifyClient
from openai import OpenAI
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class OpenAIApifyTwitterService:
    """
    Service to integrate OpenAI with Apify for Twitter data fetching and analysis.
    Supports automatic failover to backup Apify account on timeout.
    """

    def __init__(self):
        """
        Initialize the service with Apify and OpenAI clients using configuration settings.
        Initializes both primary and backup Apify clients for failover support.
        """
        # Initialize primary Apify client
        if not settings.APIFY_API_TOKEN:
            logger.warning("APIFY_API_TOKEN not configured. Some functionality may not work.")
            self.apify_client_primary = None
        else:
            self.apify_client_primary = ApifyClient(settings.APIFY_API_TOKEN)
            logger.info("Primary Apify client initialized")

        # Initialize backup Apify client for failover
        if not settings.APIFY_API_TOKEN_BACKUP:
            logger.warning("APIFY_API_TOKEN_BACKUP not configured. Failover will not be available.")
            self.apify_client_backup = None
        else:
            self.apify_client_backup = ApifyClient(settings.APIFY_API_TOKEN_BACKUP)
            logger.info("Backup Apify client initialized for failover")

        # Keep backward compatibility
        self.apify_client = self.apify_client_primary

        # Timeout configuration
        self.timeout_seconds = settings.APIFY_TIMEOUT_SECONDS
        
        # Initialize OpenAI client
        if not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not configured. Some functionality may not work.")
            self.openai_client = None
        else:
            self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

    async def fetch_tweets_with_analysis(
        self, keyword: str, max_tweets: int = 10, analyze_sentiment: bool = False
    ) -> Dict[str, Any]:
        """
        Fetch tweets using Apify and analyze them with OpenAI.

        Args:
            keyword: The keyword to search for
            max_tweets: Maximum number of tweets to fetch
            analyze_sentiment: Whether to analyze sentiment with OpenAI (default: False)

        Returns:
            Dictionary containing tweets and analysis results
        """
        try:
            # Check if at least one Apify client is initialized
            if not self.apify_client_primary and not self.apify_client_backup:
                return {
                    "success": False,
                    "error_message": "No Apify client initialized. Please configure APIFY_API_TOKEN or APIFY_API_TOKEN_BACKUP."
                }
            
            if not self.openai_client:
                return {
                    "success": False,
                    "error_message": "OpenAI client not initialized. Please configure OPENAI_API_KEY."
                }
            
            # Fetch tweets from Apify
            tweets_result = await self._fetch_tweets_from_apify(keyword, max_tweets)
            
            if not tweets_result["success"]:
                return tweets_result
            
            tweets = tweets_result["tweets"]

            # Analyze tweets with OpenAI if requested
            analyzed_tweets = []
            for tweet in tweets:
                tweet_data = {
                    "author": tweet["author"],
                    "text": tweet["text"],
                    "url": tweet.get("url", ""),
                    "created_at": tweet.get("created_at", ""),
                }

                if analyze_sentiment:
                    analysis = await self._analyze_tweet_sentiment(tweet["text"])
                    tweet_data["sentiment"] = analysis.get("sentiment", "neutral")
                    tweet_data["confidence"] = analysis.get("confidence", 0.5)

                analyzed_tweets.append(tweet_data)
            
            return {
                "success": True,
                "total_tweets": len(analyzed_tweets),
                "tweets": analyzed_tweets,
                "keyword": keyword
            }
            
        except Exception as e:
            logger.error(f"Error in fetch_tweets_with_analysis: {str(e)}")
            return {
                "success": False,
                "error_message": f"An error occurred: {str(e)}"
            }

    async def _fetch_tweets_from_apify(self, keyword: str, max_tweets: int) -> Dict[str, Any]:
        """
        Fetch tweets from Apify using the Twitter scraper with automatic failover.

        Args:
            keyword: The keyword to search for
            max_tweets: Maximum number of tweets to fetch

        Returns:
            Dictionary containing the fetched tweets
        """
        # Use a popular Twitter scraper actor from Apify Store
        actor_id = "61RPP7dywgiy0JPD0"  # Twitter Scraper actor

        # Configure the input for the actor
        run_input = {
            "searchTerms": [keyword],
            "maxItems": max_tweets,
            "includeSearchTerms": True,
            "onlyImage": False,
            "onlyQuote": False,
            "onlyTwitterBlue": False,
            "onlyVerified": False,
            "sort": "Latest"
        }

        # Build list of available clients for failover
        clients = []
        if self.apify_client_primary:
            clients.append(("primary", self.apify_client_primary))
        if self.apify_client_backup:
            clients.append(("backup", self.apify_client_backup))

        if not clients:
            return {
                "success": False,
                "error_message": "No Apify clients configured. Please set APIFY_API_TOKEN.",
                "tweets": []
            }

        last_error = None

        # Try each client with timeout
        for client_name, client in clients:
            try:
                logger.info(f"Starting Apify actor ({client_name}) to fetch tweets for keyword: {keyword}")

                # Run the actor call in a thread pool with timeout
                loop = asyncio.get_event_loop()
                run = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        lambda c=client: c.actor(actor_id).call(run_input=run_input)
                    ),
                    timeout=self.timeout_seconds
                )

                # Check if the run was successful
                if run.get("status") != "SUCCEEDED":
                    error_msg = f"Apify actor run ({client_name}) failed with status: {run.get('status', 'Unknown')}"
                    logger.warning(error_msg)
                    last_error = error_msg
                    continue  # Try next client

                # Get the results using the same client that made the request
                items = []
                try:
                    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                        items.append(item)

                    # Log the first item structure for debugging
                    if items:
                        logger.debug(f"Sample Apify item structure: {list(items[0].keys())}")

                except Exception as dataset_error:
                    logger.warning(f"Error reading dataset from {client_name}: {str(dataset_error)}")
                    last_error = f"Failed to read results from Apify ({client_name}): {str(dataset_error)}"
                    continue  # Try next client

                # Process the results
                tweets = []
                for item in items[:max_tweets]:
                    # Extract author information
                    author_data = item.get("author", {})
                    author_username = author_data.get("userName", "Unknown")
                    tweet_text = item.get("text", "")
                    tweet_id = item.get("id", "")
                    created_at = item.get("createdAt", "")

                    # Try multiple fields for URL, or construct it manually
                    tweet_url = (
                        item.get("url") or
                        item.get("tweetUrl") or
                        item.get("link")
                    )

                    # If still no URL, try to construct from ID
                    if not tweet_url and tweet_id:
                        tweet_url = f"https://twitter.com/{author_username}/status/{tweet_id}"

                    # Final fallback: create a hash-based identifier for deduplication
                    if not tweet_url:
                        # Create a unique hash from username, text, and timestamp
                        unique_string = f"{author_username}:{tweet_text[:100]}:{created_at}"
                        url_hash = hashlib.md5(unique_string.encode()).hexdigest()[:12]
                        tweet_url = f"https://twitter.com/{author_username}/tweet/{url_hash}"
                        logger.warning(
                            f"Tweet URL missing for @{author_username}, generated hash-based URL: {tweet_url}. "
                            f"Available fields: {list(item.keys())}"
                        )

                    tweet = {
                        "author": author_username,
                        "text": tweet_text,
                        "created_at": created_at,
                        "likes": item.get("likeCount", 0),
                        "retweets": item.get("retweetCount", 0),
                        "replies": item.get("replyCount", 0),
                        "url": tweet_url,
                        "tweet_id": tweet_id  # Include original ID for reference
                    }
                    tweets.append(tweet)

                logger.info(f"Successfully fetched {len(tweets)} tweets using {client_name} Apify client for keyword: {keyword}")

                return {
                    "success": True,
                    "tweets": tweets,
                    "total_count": len(tweets),
                    "client_used": client_name
                }

            except asyncio.TimeoutError:
                logger.warning(f"Timeout ({self.timeout_seconds}s) on {client_name} Apify client for keyword: {keyword}")
                last_error = f"Timeout on {client_name} Apify client after {self.timeout_seconds} seconds"
                continue  # Try next client

            except Exception as e:
                logger.warning(f"Error on {client_name} Apify client: {str(e)}")
                last_error = f"Failed on {client_name} client: {str(e)}"
                continue  # Try next client

        # All clients failed
        logger.error(f"All Apify clients failed for keyword: {keyword}. Last error: {last_error}")
        return {
            "success": False,
            "error_message": f"All Apify clients failed. Last error: {last_error}",
            "tweets": []
        }

    async def _analyze_tweet_sentiment(self, tweet_text: str) -> Dict[str, Any]:
        """
        Analyze tweet sentiment using OpenAI.
        """
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a sentiment analysis expert. Analyze the sentiment of the given tweet and provide a sentiment score from -1 (very negative) to 1 (very positive), along with a brief explanation."
                    },
                    {
                        "role": "user",
                        "content": f"Analyze the sentiment of this tweet: '{tweet_text}'"
                    }
                ],
                max_tokens=150,
                temperature=0.3
            )
            
            analysis_text = response.choices[0].message.content
            
            # Extract sentiment score (simple parsing - could be improved)
            sentiment_score = 0.0
            if "positive" in analysis_text.lower():
                sentiment_score = 0.5
            elif "negative" in analysis_text.lower():
                sentiment_score = -0.5
            elif "very positive" in analysis_text.lower():
                sentiment_score = 0.8
            elif "very negative" in analysis_text.lower():
                sentiment_score = -0.8
            
            return {
                "sentiment_score": sentiment_score,
                "analysis": analysis_text,
                "model_used": "gpt-3.5-turbo"
            }
            
        except Exception as e:
            logger.error(f"Error analyzing sentiment with OpenAI: {str(e)}")
            return {
                "sentiment_score": 0.0,
                "analysis": f"Error analyzing sentiment: {str(e)}",
                "model_used": "gpt-3.5-turbo"
            }

    async def generate_tweet_summary(self, tweets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a summary of tweets using OpenAI.
        
        Args:
            tweets: List of tweet dictionaries
            
        Returns:
            Dictionary containing the generated summary
        """
        try:
            if not self.openai_client:
                return {
                    "success": False,
                    "error_message": "OpenAI client not initialized. Please configure OPENAI_API_KEY."
                }
            
            if not tweets:
                return {
                    "success": False,
                    "error_message": "No tweets provided for summary generation."
                }
            
            # Prepare tweet texts for summarization
            tweet_texts = []
            for tweet in tweets:
                author = tweet.get("author", "Unknown")
                text = tweet.get("text", "")
                if text:
                    tweet_texts.append(f"@{author}: {text}")
            
            if not tweet_texts:
                return {
                    "success": False,
                    "error_message": "No valid tweet texts found for summarization."
                }
            
            # Create prompt for summarization
            tweets_content = "\n\n".join(tweet_texts[:10])  # Limit to first 10 tweets
            prompt = f"""
            Please analyze and summarize the following tweets. Provide:
            1. Main themes and topics discussed
            2. Overall sentiment
            3. Key insights or trends
            4. Notable opinions or perspectives
            
            Tweets:
            {tweets_content}
            
            Please provide a concise but comprehensive summary.
            """
            
            # Generate summary using OpenAI
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a social media analyst expert at summarizing Twitter conversations and identifying trends."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            summary = response.choices[0].message.content
            
            return {
                "success": True,
                "summary": summary,
                "tweets_analyzed": len(tweet_texts),
                "total_tweets_provided": len(tweets)
            }
            
        except Exception as e:
            logger.error(f"Error generating tweet summary: {str(e)}")
            return {
                "success": False,
                "error_message": f"Failed to generate summary: {str(e)}"
            }