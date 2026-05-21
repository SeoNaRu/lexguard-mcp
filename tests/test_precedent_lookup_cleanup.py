"""
precedent_lookup_tool — 자연어 시간 조건 추출 + 판례 마커 cleanup 검증.

legal_qa_tool 내부 흐름에만 적용되던 cleanup을 direct precedent_lookup_tool에도
일관되게 적용한다. case_number 우선 사용 시에는 cleanup 하지 않는다.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

from src.services.smart_search_service import SmartSearchService


@pytest.fixture
def svc_with_spy(monkeypatch):
    """precedent_repo.search_precedent를 spy로 교체한 서비스."""
    svc = SmartSearchService()
    spy = AsyncMock(return_value={"total": 0, "precedents": []})
    monkeypatch.setattr(svc.precedent_repo, "search_precedent", spy)
    return svc, spy


@pytest.mark.asyncio
async def test_strips_recent_n_years_and_extracts_date_range(svc_with_spy):
    """'최근 3년 부당해고 판례' → query 'N년'/'판례' 제거, date_from/date_to 3년 범위."""
    svc, spy = svc_with_spy
    await svc.precedent_lookup(keyword="최근 3년 부당해고 판례")

    args = spy.await_args
    sent_query = args.args[0]
    date_from = args.args[4]
    date_to = args.args[5]

    assert "최근" not in sent_query and "년" not in sent_query and "판례" not in sent_query
    assert "부당해고" in sent_query
    assert date_from is not None and date_to is not None
    today = datetime.now()
    expected_from = (today - timedelta(days=3 * 365)).strftime("%Y%m%d")
    assert date_from == expected_from
    assert date_to == today.strftime("%Y%m%d")


@pytest.mark.asyncio
async def test_user_supplied_date_range_overrides_inference(svc_with_spy):
    """사용자가 date_from/date_to 명시 → 자연어 시간 조건 무시하고 명시값 그대로."""
    svc, spy = svc_with_spy
    await svc.precedent_lookup(
        keyword="최근 5년 부당해고",
        date_from="20200101",
        date_to="20201231",
    )
    args = spy.await_args
    assert args.args[4] == "20200101"
    assert args.args[5] == "20201231"
    assert "5년" not in args.args[0]


@pytest.mark.asyncio
async def test_strips_precedent_markers_without_time(svc_with_spy):
    """시간 조건 없어도 '판례'/'관련 판례'/'유사 사례' 마커는 제거."""
    svc, spy = svc_with_spy
    await svc.precedent_lookup(keyword="부당해고 관련 판례")
    sent_query = spy.await_args.args[0]
    assert sent_query.strip() == "부당해고"
    assert spy.await_args.args[4] is None
    assert spy.await_args.args[5] is None


@pytest.mark.asyncio
async def test_case_number_skips_cleanup(svc_with_spy):
    """case_number가 있으면 그 값 그대로 검색 (cleanup 안 함)."""
    svc, spy = svc_with_spy
    await svc.precedent_lookup(
        keyword="최근 3년 판례",
        case_number="2023다12345",
    )
    args = spy.await_args
    assert args.args[0] == "2023다12345"
    assert args.args[4] is None and args.args[5] is None


@pytest.mark.asyncio
async def test_year_range_pattern_extracted(svc_with_spy):
    """'2020년부터 2023년까지' 패턴 → date_from=20200101, date_to=20231231."""
    svc, spy = svc_with_spy
    await svc.precedent_lookup(keyword="2020년부터 2023년까지 부당해고 판례")
    args = spy.await_args
    assert args.args[4] == "20200101"
    assert args.args[5] == "20231231"
    assert "2020년" not in args.args[0] and "2023년" not in args.args[0]


@pytest.mark.asyncio
async def test_year_after_pattern_extracted(svc_with_spy):
    """'2022년 이후' → date_from=20220101, date_to=today."""
    svc, spy = svc_with_spy
    await svc.precedent_lookup(keyword="2022년 이후 산재 판례")
    args = spy.await_args
    assert args.args[4] == "20220101"
    assert args.args[5] == datetime.now().strftime("%Y%m%d")
    assert "2022년" not in args.args[0]


@pytest.mark.asyncio
async def test_clean_query_falls_back_to_raw_when_empty(svc_with_spy):
    """cleanup 결과가 빈 문자열이면 원본 keyword 그대로 전송 (overshoot 방지)."""
    svc, spy = svc_with_spy
    await svc.precedent_lookup(keyword="판례")
    sent_query = spy.await_args.args[0]
    assert sent_query == "판례"
