"""
LawDetailRepository.get_single_article — efYd 추출 경로 단위 테스트

API 호출 없이 aget 을 모킹하여 법령.기본정보.시행일자 경로 포함
다양한 응답 구조에서 efYd 가 올바르게 추출되는지 검증.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from src.repositories.law_detail import LawDetailRepository


# ---------------------------------------------------------------------------
# 공통 헬퍼
# ---------------------------------------------------------------------------

def _make_response(json_body: dict, status_code: int = 200):
    """httpx.Response 모사 객체를 반환한다."""
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.headers = {"Content-Type": "application/json"}
    mock_resp.text = json.dumps(json_body, ensure_ascii=False)
    mock_resp.json = MagicMock(return_value=json_body)
    mock_resp.url = "https://www.law.go.kr/DRF/lawService.do?target=law&MST=273437&type=JSON&OC=****"
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


# 법령 detail API(target=law) — 실제 DRF JSON 구조를 모사
_DETAIL_BASICINFO = {
    "법령": {
        "기본정보": {
            "법령명_한글": "건축법",
            "시행일자": "20260227",
            "법령ID": "273437",
        },
        "조문": []
    }
}

# eflawjosub 성공 응답 — 조문내용 포함
_JOSUB_OK = {
    "법령명_한글": "건축법",
    "시행일자": "20260227",
    "조문번호": "000003",
    "조문제목": "적용 제외",
    "조문내용": "다음 각 호의 어느 하나에 해당하는 건축물에는 이 법을 적용하지 아니한다.",
}

# eflawjosub 빈 응답 — 조문내용 없음(오늘 날짜로 잘못 호출된 경우)
_JOSUB_EMPTY = {
    "법령명_한글": "건축법",
    "시행일자": "20260227",
    "조문번호": "000003",
    "조문내용": "",
}


# ---------------------------------------------------------------------------
# 정상 케이스: 법령.기본정보.시행일자 경로
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_efyd_extracted_from_basicinfo():
    """법령.기본정보.시행일자 경로에서 efYd 가 올바르게 추출되고 조문내용이 반환된다."""
    repo = LawDetailRepository()

    detail_resp = _make_response(_DETAIL_BASICINFO)
    josub_resp = _make_response(_JOSUB_OK)

    call_params = []

    async def fake_aget(url, params=None, timeout=None):
        call_params.append(dict(params or {}))
        if params and params.get("target") == "eflawjosub":
            return josub_resp
        return detail_resp

    with patch("src.repositories.law_detail.aget", side_effect=fake_aget):
        result = await repo.get_single_article(
            law_id="273437",
            article_number="3",
            arguments={"env": {"LAW_API_KEY": "testkey123"}},
        )

    assert result.get("content") != "조문 내용을 찾을 수 없습니다.", (
        "기본정보.시행일자 경로를 읽지 못해 오늘 날짜로 폴백된 것으로 보임"
    )
    assert "적용 제외" in result.get("content", "") or result.get("content")

    # eflawjosub 호출 시 efYd 가 오늘 날짜가 아닌 20260227 이어야 함
    josub_call = next(p for p in call_params if p.get("target") == "eflawjosub")
    assert josub_call["efYd"] == "20260227", (
        f"efYd 가 20260227 이어야 하는데 {josub_call['efYd']} 로 호출됨"
    )


# ---------------------------------------------------------------------------
# 법령.시행일자 최상위 경로 (하위 호환)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_efyd_from_top_level():
    """detail_data['법령']['시행일자'] (직접 경로)에서도 추출된다."""
    repo = LawDetailRepository()

    detail_body = {
        "법령": {
            "법령명_한글": "건축법",
            "시행일자": "20260227",
        }
    }
    detail_resp = _make_response(detail_body)
    josub_resp = _make_response(_JOSUB_OK)

    call_params = []

    async def fake_aget(url, params=None, timeout=None):
        call_params.append(dict(params or {}))
        return josub_resp if params and params.get("target") == "eflawjosub" else detail_resp

    with patch("src.repositories.law_detail.aget", side_effect=fake_aget):
        result = await repo.get_single_article(
            law_id="273437",
            article_number="3",
            arguments={"env": {"LAW_API_KEY": "testkey123"}},
        )

    josub_call = next(p for p in call_params if p.get("target") == "eflawjosub")
    assert josub_call["efYd"] == "20260227"


# ---------------------------------------------------------------------------
# efYd 를 아무 경로에서도 못 찾으면 오늘 날짜 폴백 — warning 로그 발생
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_efyd_fallback_to_today_logs_warning(caplog):
    """시행일자를 찾지 못하면 오늘 날짜를 사용하고 warning 을 남긴다."""
    import logging
    repo = LawDetailRepository()

    detail_body = {"법령": {"법령명_한글": "건축법"}}  # 시행일자 없음
    detail_resp = _make_response(detail_body)
    josub_resp = _make_response(_JOSUB_EMPTY)

    async def fake_aget(url, params=None, timeout=None):
        return josub_resp if params and params.get("target") == "eflawjosub" else detail_resp

    with caplog.at_level(logging.WARNING, logger="lexguard-mcp"):
        with patch("src.repositories.law_detail.aget", side_effect=fake_aget):
            result = await repo.get_single_article(
                law_id="273437",
                article_number="3",
                arguments={"env": {"LAW_API_KEY": "testkey123"}},
            )

    assert any("시행일자" in r.message for r in caplog.records), (
        "시행일자 폴백 시 warning 로그가 기록되어야 함"
    )


# ---------------------------------------------------------------------------
# API 키 없으면 에러 반환
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_missing_api_key_returns_error():
    repo = LawDetailRepository()
    result = await repo.get_single_article(
        law_id="273437",
        article_number="3",
        arguments={"env": {"LAW_API_KEY": ""}},
    )
    assert "error" in result
    assert result.get("error_code") == "API_ERROR_AUTH"
