"""전용 MCP 툴용 SmartSearchService 조회 메서드 (API 없음)."""

import pytest

from src.services.smart_search_service import SmartSearchService


@pytest.mark.asyncio
async def test_precedent_lookup_requires_query():
    svc = SmartSearchService()
    r = await svc.precedent_lookup(keyword=None, case_number=None)
    assert r.get("error_code") == "INVALID_INPUT"


@pytest.mark.asyncio
async def test_interpretation_lookup_requires_query():
    svc = SmartSearchService()
    r = await svc.interpretation_lookup(query="   ")
    assert r.get("error_code") == "INVALID_INPUT"


@pytest.mark.asyncio
async def test_administrative_appeal_lookup_requires_query():
    svc = SmartSearchService()
    r = await svc.administrative_appeal_lookup(query="")
    assert r.get("error_code") == "INVALID_INPUT"


@pytest.mark.asyncio
async def test_committee_decision_lookup_invalid_committee():
    svc = SmartSearchService()
    r = await svc.committee_decision_lookup(
        committee_type="없는위원회",
        query="테스트",
    )
    assert r.get("error_code") == "INVALID_COMMITTEE"


@pytest.mark.asyncio
async def test_special_appeal_lookup_invalid_tribunal():
    svc = SmartSearchService()
    r = await svc.special_administrative_appeal_lookup(
        tribunal_type="없는원",
        query="테스트",
    )
    assert r.get("error_code") == "INVALID_TRIBUNAL"


@pytest.mark.asyncio
async def test_local_ordinance_lookup_requires_query_or_region():
    svc = SmartSearchService()
    r = await svc.local_ordinance_lookup(query=None, local_government=None)
    assert r.get("error_code") == "INVALID_INPUT"


@pytest.mark.asyncio
async def test_administrative_rule_lookup_requires_query_or_agency():
    svc = SmartSearchService()
    r = await svc.administrative_rule_lookup(query=None, agency=None)
    assert r.get("error_code") == "INVALID_INPUT"
