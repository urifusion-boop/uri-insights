from typing import Dict, Any, List
import hashlib
import logging
from apify_client import ApifyClient
from openai import OpenAI
from app.core.config import settings


logger = logging.getLogger(__name__)


class OpenAIApifyFacebookService:
    def __init__(self):
        self.apify_client = ApifyClient(settings.APIFY_API_TOKEN) if settings.APIFY_API_TOKEN else None
        self.openai_client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None

    async def fetch_posts_with_analysis(self, keyword: str, max_posts: int = 10, analyze_sentiment: bool = False) -> Dict[str, Any]:
        if not self.apify_client:
            return {"success": False, "error_message": "Apify client not initialized.", "posts": []}

        posts_result = await self._fetch_posts_from_apify(keyword, max_posts)
        if not posts_result.get("success"):
            return posts_result

        items: List[Dict[str, Any]] = posts_result.get("posts", [])
        analyzed: List[Dict[str, Any]] = []
        for it in items:
            author = (
                (it.get("author") or {})
                if isinstance(it.get("author"), str)
                else (it.get("author") or {}).get("name")
            ) or it.get("username") or it.get("pageName") or it.get("ownerName") or "Facebook User"

            # Try multiple possible field names for post content
            text = (
                it.get("text")
                or it.get("message")
                or it.get("title")
                or it.get("content")
                or it.get("description")
                or it.get("caption")
                or it.get("post_text")
                or it.get("postText")
                or ""
            )

            created = it.get("created_time") or it.get("createdAt") or it.get("publishedAt") or it.get("timestamp")
            url = it.get("url") or it.get("permalink_url") or it.get("postUrl") or it.get("link")
            if not url:
                unique = f"{author}:{text[:120]}:{created}"
                url_hash = hashlib.md5(unique.encode()).hexdigest()[:12]
                url = f"https://www.facebook.com/posts/{url_hash}"

            data = {"author": author, "text": text, "url": url, "created_at": created}
            if analyze_sentiment and self.openai_client:
                sentiment = await self._analyze_post_sentiment(text)
                data.update({
                    "sentiment": sentiment.get("sentiment"),
                    "confidence": sentiment.get("confidence"),
                })
            analyzed.append(data)

        return {"success": True, "posts": analyzed, "total_posts": len(analyzed), "keyword": keyword}

    async def _fetch_posts_from_apify(self, keyword: str, max_posts: int) -> Dict[str, Any]:
        try:
            run_input = {
                "query": keyword,
                "resultsCount": max_posts,
            }
            run = self.apify_client.actor("scraper_one/facebook-posts-search").call(run_input=run_input)
            if run.get("status") != "SUCCEEDED":
                return {"success": False, "error_message": f"Apify actor failed: {run.get('status')}", "posts": []}

            items: List[Dict[str, Any]] = []
            for item in self.apify_client.dataset(run["defaultDatasetId"]).iterate_items():
                items.append(item)

            # Log the first item structure for debugging
            if items:
                logger.debug(f"Sample Apify Facebook item structure: {list(items[0].keys())}")
                logger.debug(f"Sample Apify Facebook item data: {items[0]}")

            logger.info(f"Fetched {len(items)} Facebook posts for keyword: {keyword}")
            return {"success": True, "posts": items[:max_posts], "total_count": len(items)}
        except Exception as e:
            return {"success": False, "error_message": f"Failed to fetch posts: {str(e)}", "posts": []}

    async def generate_post_summary(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            if not self.openai_client:
                return {"success": False, "error_message": "OpenAI client not initialized."}

            post_texts: List[str] = []
            for post in posts:
                author = post.get("author") or "Unknown"
                text = post.get("text") or ""
                if text:
                    post_texts.append(f"{author}: {text}")

            if not post_texts:
                return {"success": False, "error_message": "No valid posts provided for summarization."}

            content = "\n\n".join(post_texts[:10])
            prompt = (
                "Analyze and summarize the following Facebook posts. Provide: \n"
                "1. Main themes and topics \n"
                "2. Overall sentiment \n"
                "3. Key insights or trends \n"
                "4. Notable opinions or perspectives \n\n"
                f"Posts:\n{content}\n\n"
                "Provide a concise but comprehensive summary."
            )

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a social media analyst summarizing Facebook conversations and trends."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=500,
                temperature=0.7,
            )

            summary = response.choices[0].message.content
            return {"success": True, "summary": summary, "posts_analyzed": len(post_texts), "total_posts_provided": len(posts)}
        except Exception as e:
            return {"success": False, "error_message": f"Failed to generate summary: {str(e)}"}

    async def _analyze_post_sentiment(self, text: str) -> Dict[str, Any]:
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a sentiment analysis expert. Analyze the sentiment of the given Facebook post and provide a label (positive, neutral, negative) and a confidence score between 0 and 1."
                    },
                    {
                        "role": "user",
                        "content": f"Analyze the sentiment of this post: '{text}'"
                    }
                ],
                max_tokens=120,
                temperature=0.2,
            )
            analysis_text = response.choices[0].message.content.lower()
            sentiment = "neutral"
            if "very positive" in analysis_text or "strongly positive" in analysis_text or "positive" in analysis_text:
                sentiment = "positive"
            elif "very negative" in analysis_text or "strongly negative" in analysis_text or "negative" in analysis_text:
                sentiment = "negative"

            confidence = 0.5
            if "high confidence" in analysis_text:
                confidence = 0.9
            elif "medium confidence" in analysis_text:
                confidence = 0.7
            elif "low confidence" in analysis_text:
                confidence = 0.4

            return {"sentiment": sentiment, "confidence": confidence, "analysis": analysis_text}
        except Exception:
            return {"sentiment": "neutral", "confidence": 0.5}