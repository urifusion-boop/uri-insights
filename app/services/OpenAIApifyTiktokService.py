from typing import Dict, Any, List
import hashlib
from apify_client import ApifyClient
from app.core.config import settings


class OpenAIApifyTiktokService:
    def __init__(self):
        self.apify_client = ApifyClient(settings.APIFY_API_TOKEN) if settings.APIFY_API_TOKEN else None

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
                (it.get("authorMeta") or {}).get("name")
                or (it.get("authorMeta") or {}).get("nickName")
                or it.get("author")
                or it.get("username")
                or "TikTok User"
            )
            text = it.get("text") or it.get("desc") or ""
            created = it.get("createTime") or it.get("created_at")
            url = it.get("webVideoUrl") or it.get("url") or it.get("video_url")
            if not url:
                unique = f"{author}:{text[:100]}:{created}"
                url_hash = hashlib.md5(unique.encode()).hexdigest()[:12]
                url = f"https://www.tiktok.com/@{author}/video/{url_hash}"
            data = {"author": author, "text": text, "url": url, "created_at": created}
            analyzed.append(data)
        return {"success": True, "posts": analyzed, "total_posts": len(analyzed), "keyword": keyword}

    async def _fetch_posts_from_apify(self, keyword: str, max_posts: int) -> Dict[str, Any]:
        try:
            run_input = {"searchTerms": [keyword], "maxItems": max_posts}
            run = self.apify_client.actor("clockworks/tiktok-scraper").call(run_input=run_input)
            if run.get("status") != "SUCCEEDED":
                return {"success": False, "error_message": f"Apify actor failed: {run.get('status')}", "posts": []}
            items: List[Dict[str, Any]] = []
            for item in self.apify_client.dataset(run["defaultDatasetId"]).iterate_items():
                items.append(item)
            return {"success": True, "posts": items, "total_count": len(items)}
        except Exception as e:
            return {"success": False, "error_message": f"Failed to fetch posts: {str(e)}", "posts": []}