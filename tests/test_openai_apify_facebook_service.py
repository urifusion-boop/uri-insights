import pytest
from app.services.OpenAIApifyFacebookService import OpenAIApifyFacebookService


class _FakeDataset:
    def iterate_items(self):
        return [
            {
                "author": {"name": "bob"},
                "message": "great product launch",
                "created_time": "2025-11-20T10:00:00Z",
                "permalink_url": "https://facebook.com/posts/123",
            }
        ]


class _FakeActor:
    def call(self, run_input=None):
        return {"status": "SUCCEEDED", "defaultDatasetId": "ds1"}


class _FakeClient:
    def actor(self, actor_id):
        return _FakeActor()

    def dataset(self, dataset_id):
        return _FakeDataset()


@pytest.mark.asyncio
async def test_fetch_posts_with_analysis_success():
    svc = OpenAIApifyFacebookService()
    svc.apify_client = _FakeClient()
    res = await svc.fetch_posts_with_analysis(keyword="test", max_posts=1)
    assert res.get("success") is True
    assert res.get("total_posts") == 1
    p = res.get("posts")[0]
    assert p.get("author") == "bob"
    assert p.get("url")
    assert p.get("text") == "great product launch"


@pytest.mark.asyncio
async def test_fetch_posts_with_analysis_no_client():
    svc = OpenAIApifyFacebookService()
    svc.apify_client = None
    res = await svc.fetch_posts_with_analysis(keyword="test")
    assert res.get("success") is False