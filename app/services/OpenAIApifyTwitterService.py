import os
import asyncio
from typing import List, Dict, Any, Optional
from apify_client import ApifyClient
from openai import OpenAI
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class OpenAIApifyTwitterService:
    """
    Service to integrate OpenAI with Apify for Twitter data fetching and analysis.
    """

    def __init__(self):
        """
        Initialize the service with Apify and OpenAI clients using configuration settings.
        """
        # Initialize Apify client
        if not settings.APIFY_API_TOKEN:
            logger.warning("APIFY_API_TOKEN not configured. Some functionality may not work.")
            self.apify_client = None
        else:
            self.apify_client = ApifyClient(settings.APIFY_API_TOKEN)
        
        # Initialize OpenAI client
        if not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not configured. Some functionality may not work.")
            self.openai_client = None
        else:
            self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

    async def fetch_tweets_with_analysis(
        self, keyword: str, max_tweets: int = 10
    ) -> Dict[str, Any]:
        """
        Fetch tweets using Apify and analyze them with OpenAI.
        
        Args:
            keyword: The keyword to search for
            max_tweets: Maximum number of tweets to fetch
            
        Returns:
            Dictionary containing tweets and analysis results
        """
        try:
            # Check if clients are initialized
            if not self.apify_client:
                return {
                    "success": False,
                    "error_message": "Apify client not initialized. Please configure APIFY_API_TOKEN."
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
            
            # Analyze tweets with OpenAI
            analyzed_tweets = []
            for tweet in tweets:
                analysis = await self._analyze_tweet_sentiment(tweet["text"])
                analyzed_tweets.append({
                    "author": tweet["author"],
                    "text": tweet["text"],
                    "url": tweet.get("url", ""),
                    "created_at": tweet.get("created_at", ""),
                    "sentiment": analysis.get("sentiment", "neutral"),
                    "confidence": analysis.get("confidence", 0.5)
                })
            
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
        Fetch tweets from Apify using the Twitter scraper.
        
        Args:
            keyword: The keyword to search for
            max_tweets: Maximum number of tweets to fetch
            
        Returns:
            Dictionary containing the fetched tweets
        """
        try:
            # Use a popular Twitter scraper actor from Apify Store
            # This is a commonly used actor for Twitter scraping
            actor_id = "61RPP7dywgiy0JPD0"  # Twitter Scraper actor
            
            # Configure the input for the actor
            run_input = {
                "searchTerms": [keyword],
                "maxItems": max_tweets,  # Changed from maxTweets to maxItems (Apify's actual parameter)
                "includeSearchTerms": True,
                "onlyImage": False,
                "onlyQuote": False,
                "onlyTwitterBlue": False,
                "onlyVerified": False,
                "sort": "Latest"
            }
            
            # Run the actor
            logger.info(f"Starting Apify actor to fetch tweets for keyword: {keyword}")
            run = self.apify_client.actor(actor_id).call(run_input=run_input)
            
            # Check if the run was successful
            if run.get("status") != "SUCCEEDED":
                error_msg = f"Apify actor run failed with status: {run.get('status', 'Unknown')}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error_message": error_msg,
                    "tweets": []
                }
            
            # Get the results
            items = []
            try:
                for item in self.apify_client.dataset(run["defaultDatasetId"]).iterate_items():
                    items.append(item)

                # Log the first item structure for debugging
                if items:
                    logger.debug(f"Sample Apify item structure: {list(items[0].keys())}")

            except Exception as dataset_error:
                logger.error(f"Error reading dataset: {str(dataset_error)}")
                return {
                    "success": False,
                    "error_message": f"Failed to read results from Apify: {str(dataset_error)}",
                    "tweets": []
                }
            
            # Process the results
            tweets = []
            for item in items[:max_tweets]:
                # Extract author information
                author_data = item.get("author", {})
                author_username = author_data.get("userName", "Unknown")

                # Try multiple fields for URL, or construct it manually
                tweet_url = (
                    item.get("url") or
                    item.get("tweetUrl") or
                    item.get("link") or
                    f"https://twitter.com/{author_username}/status/{item.get('id', '')}" if item.get('id') else ""
                )

                # Log if URL is missing for debugging
                if not tweet_url:
                    logger.warning(f"Tweet URL missing for tweet from @{author_username}. Available fields: {list(item.keys())}")

                tweet = {
                    "author": author_username,
                    "text": item.get("text", ""),
                    "created_at": item.get("createdAt", ""),
                    "likes": item.get("likeCount", 0),
                    "retweets": item.get("retweetCount", 0),
                    "replies": item.get("replyCount", 0),
                    "url": tweet_url
                }
                tweets.append(tweet)
            
            logger.info(f"Successfully fetched {len(tweets)} tweets for keyword: {keyword}")
            
            return {
                "success": True,
                "tweets": tweets,
                "total_count": len(tweets)
            }
            
        except Exception as e:
            logger.error(f"Error fetching tweets from Apify: {str(e)}")
            return {
                "success": False,
                "error_message": f"Failed to fetch tweets: {str(e)}",
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