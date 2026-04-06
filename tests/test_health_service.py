"""
HealthService — API 키 마스킹 등 순수/경량 검증
"""
import pytest
from src.services.health_service import HealthService


@pytest.mark.asyncio
async def test_health_never_exposes_raw_api_key(monkeypatch):
    raw = "abcdefghijklmnopqr_stuvwxyz"
    monkeypatch.setenv("LAW_API_KEY", raw)
    out = await HealthService.check_health()
    preview = out["environment"]["law_api_key"]["preview"]
    assert preview is not None
    assert raw not in preview
    nested = out["environment"]["env_vars"]["LAW_API_KEY"]["preview"]
    assert nested is not None
    assert raw not in nested


@pytest.mark.asyncio
async def test_health_without_key_no_preview(monkeypatch):
    monkeypatch.delenv("LAW_API_KEY", raising=False)
    out = await HealthService.check_health()
    assert out["environment"]["law_api_key"]["preview"] is None
