import asyncio
import pytest
from app.services.BackgroundService import BackgroundService
from app.services.LeadService import LeadService


class _DummyDB:
    def __getitem__(self, name):
        class _C:
            async def update_one(self, *args, **kwargs):
                return None
        return _C()


@pytest.mark.asyncio
async def test_scheduler_adds_tiktok_job(monkeypatch):
    calls = {"tiktok_fetch": 0}

    async def _fake_tiktok_fetch(db=None):
        calls["tiktok_fetch"] += 1

    monkeypatch.setattr("app.services.LeadService.LeadService.fetch_and_save_conversational_tiktok_leads", _fake_tiktok_fetch)

    from app.core import config
    config.settings.LEAD_GENERATION_INTERVAL_MINUTES_FOR_TEST = 1

    scheduler = BackgroundService.start_scheduler(_DummyDB())

    await asyncio.sleep(0.1)

    job = scheduler.get_job("conversational_tiktok_fetch_job")
    assert job is not None

    scheduler.shutdown()