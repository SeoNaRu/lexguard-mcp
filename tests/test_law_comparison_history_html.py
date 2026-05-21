"""
law_comparison_tool — 연혁(lsHistory) API의 HTML 응답에 대한 명확한 안내 검증.

라이브 검증에서 발견: 민법 연혁, 주민등록법 연혁 등 일부 법령에서 lsHistory가
HTML 안내 페이지를 반환. 기본 API_ERROR_HTML 메시지("API 키 설정 또는 정책/차단
여부를 확인하세요")는 사용자에게 잘못된 안내를 준다(키는 정상이고 다른 비교
타입은 잘 동작). 연혁+HTML 조합일 때만 더 정확한 안내로 교체.
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from src.repositories.law_comparison_repository import LawComparisonRepository
from src.repositories.base import search_cache, failure_cache


@pytest.fixture(autouse=True)
def _clear_cache():
    """각 테스트 시작 전 캐시 비움 (다른 테스트의 캐시 오염 방지)."""
    search_cache.clear()
    failure_cache._cache.clear()
    yield
    search_cache.clear()
    failure_cache._cache.clear()


def make_search_response() -> MagicMock:
    """법령 검색(target=law) 정상 응답 — 법령 ID 추출 가능."""
    body = {
        "LawSearch": {
            "law": [{"법령명한글": "테스트법", "법령일련번호": "123456"}]
        }
    }
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"Content-Type": "application/json"}
    mock_resp.text = json.dumps(body, ensure_ascii=False)
    mock_resp.json = MagicMock(return_value=body)
    mock_resp.url = "https://www.law.go.kr/DRF/lawSearch.do"
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def make_html_response(status_code: int = 200) -> MagicMock:
    """lsHistory/oldAndNew/thdCmp API의 HTML 안내 페이지 응답 모사."""
    html_body = "<!doctype html><html><body>안내 페이지</body></html>"
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.headers = {"Content-Type": "text/html"}
    mock_resp.text = html_body
    mock_resp.json = MagicMock(side_effect=ValueError("not json"))
    mock_resp.url = "https://www.law.go.kr/DRF/lawService.do"
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


def make_json_response(body: dict) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"Content-Type": "application/json"}
    mock_resp.text = json.dumps(body, ensure_ascii=False)
    mock_resp.json = MagicMock(return_value=body)
    mock_resp.url = "https://www.law.go.kr/DRF/lawService.do"
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


@pytest.mark.asyncio
async def test_history_html_response_replaces_error_with_specific_guide():
    """연혁 + HTML 응답 → 메시지가 '연혁 API 지원 안 함' 안내로 교체."""
    repo = LawComparisonRepository()

    async def fake_aget(url, params=None, timeout=None):
        if params and params.get("target") == "law":
            return make_search_response()
        return make_html_response()

    with patch("src.repositories.law_comparison_repository.aget", side_effect=fake_aget):
        result = await repo.compare_laws(
            law_name="민법", compare_type="연혁",
            arguments={"env": {"LAW_API_KEY": "testkey123"}},
        )

    assert result.get("error_code") == "API_ERROR_HTML"
    assert "연혁 API" in result.get("error", "")
    assert "API 키 설정" not in result.get("error", "")
    assert "신구법" in result.get("recovery_guide", "") or "3단비교" in result.get("recovery_guide", "")
    assert result.get("law_name") == "민법"
    assert result.get("compare_type") == "연혁"


@pytest.mark.asyncio
async def test_oldandnew_html_response_keeps_generic_guide():
    """신구법 + HTML 응답 → 보강 안 됨 (기본 안내 유지). 연혁 한정 특수 처리."""
    repo = LawComparisonRepository()

    async def fake_aget(url, params=None, timeout=None):
        if params and params.get("target") == "law":
            return make_search_response()
        return make_html_response()

    with patch("src.repositories.law_comparison_repository.aget", side_effect=fake_aget):
        result = await repo.compare_laws(
            law_name="민법", compare_type="신구법",
            arguments={"env": {"LAW_API_KEY": "testkey123"}},
        )

    assert result.get("error_code") == "API_ERROR_HTML"
    assert "연혁 API" not in result.get("error", "")  # 신구법은 보강 안 됨
    assert "법령 연혁" not in result.get("recovery_guide", "")


@pytest.mark.asyncio
async def test_thdcmp_html_response_keeps_generic_guide():
    """3단비교 + HTML 응답 → 보강 안 됨."""
    repo = LawComparisonRepository()

    async def fake_aget(url, params=None, timeout=None):
        if params and params.get("target") == "law":
            return make_search_response()
        return make_html_response()

    with patch("src.repositories.law_comparison_repository.aget", side_effect=fake_aget):
        result = await repo.compare_laws(
            law_name="민법", compare_type="3단비교",
            arguments={"env": {"LAW_API_KEY": "testkey123"}},
        )

    assert result.get("error_code") == "API_ERROR_HTML"
    assert "연혁 API" not in result.get("error", "")


@pytest.mark.asyncio
async def test_history_json_response_unchanged():
    """연혁 + 정상 JSON → 보강 로직 우회. 정상 결과 반환."""
    repo = LawComparisonRepository()
    history_body = {"LawHistoryService": {"history": []}}

    async def fake_aget(url, params=None, timeout=None):
        if params and params.get("target") == "law":
            return make_search_response()
        return make_json_response(history_body)

    with patch("src.repositories.law_comparison_repository.aget", side_effect=fake_aget):
        result = await repo.compare_laws(
            law_name="민법", compare_type="연혁",
            arguments={"env": {"LAW_API_KEY": "testkey123"}},
        )

    assert "error" not in result
    assert result.get("law_name") == "민법"
    assert result.get("compare_type") == "연혁"
    assert result.get("comparison") == history_body


@pytest.mark.asyncio
async def test_history_auth_error_keeps_auth_guide():
    """연혁 + 401 auth 에러 → HTML이 아니므로 인증 안내 그대로 유지."""
    repo = LawComparisonRepository()

    async def fake_aget(url, params=None, timeout=None):
        if params and params.get("target") == "law":
            return make_search_response()
        # 401 status로 인증 에러 응답
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.headers = {"Content-Type": "application/json"}
        mock_resp.text = '{"error": "unauthorized"}'
        mock_resp.url = "https://www.law.go.kr/DRF/lawService.do"
        return mock_resp

    with patch("src.repositories.law_comparison_repository.aget", side_effect=fake_aget):
        result = await repo.compare_laws(
            law_name="민법", compare_type="연혁",
            arguments={"env": {"LAW_API_KEY": "testkey123"}},
        )

    # auth 에러는 보강 대상 아님 (API_ERROR_AUTH로 떨어짐, 보강 조건 안 맞음)
    assert result.get("error_code") == "API_ERROR_AUTH"
    assert "연혁 API" not in result.get("error", "")


@pytest.mark.asyncio
async def test_history_html_response_preserves_error_code():
    """보강 후에도 error_code 필드는 그대로 유지 (다운스트림 분기용)."""
    repo = LawComparisonRepository()

    async def fake_aget(url, params=None, timeout=None):
        if params and params.get("target") == "law":
            return make_search_response()
        return make_html_response()

    with patch("src.repositories.law_comparison_repository.aget", side_effect=fake_aget):
        result = await repo.compare_laws(
            law_name="주민등록법", compare_type="연혁",
            arguments={"env": {"LAW_API_KEY": "testkey123"}},
        )

    assert result["error_code"] == "API_ERROR_HTML"
    assert "law_history_tool" in result.get("recovery_guide", "")
