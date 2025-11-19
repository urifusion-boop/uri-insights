from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.routers import openai_apify_tiktok


class _FakeService:
    async def fetch_posts_with_analysis(self, keyword: str, max_posts: int = 2, analyze_sentiment: bool = False):
        return {"success": True, "posts": [{"author": "alice", "text": "hello", "url": "u", "created_at": 1730000000}], "total_posts": 1}


def test_fetch_posts_endpoint(monkeypatch):
    monkeypatch.setattr(openai_apify_tiktok, "OpenAIApifyTiktokService", lambda: _FakeService())
    app = FastAPI()
    app.include_router(openai_apify_tiktok.router, prefix="/openai-apify-tiktok")
    client = TestClient(app)
    r = client.get("/openai-apify-tiktok/fetch-posts", params={"keyword": "k", "max_posts": 1})
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") is True
    assert data.get("responseData")