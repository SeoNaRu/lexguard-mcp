"""
response_formatter — OC API 키 마스킹 + law_comparison 빈 응답 명시화 검증.
"""
import pytest

from src.utils.response_formatter import (
    mask_oc_in_url,
    sanitize_for_mcp_json,
    format_search_response,
)


# ---------------------------------------------------------------------------
# mask_oc_in_url 단위
# ---------------------------------------------------------------------------


def test_mask_oc_in_url_masks_long_key():
    url = "https://www.law.go.kr/DRF/lawSearch.do?target=prec&OC=LexGuardKey"
    masked = mask_oc_in_url(url)
    assert "OC=LexGuardKey" not in masked
    assert "OC=Lex" in masked and "Key" in masked
    assert "****" in masked


def test_mask_oc_in_url_short_key_uses_short_mask():
    url = "https://www.law.go.kr/DRF/lawSearch.do?target=prec&OC=abc123"
    masked = mask_oc_in_url(url)
    assert "OC=abc123" not in masked
    assert "****" in masked


def test_mask_oc_in_url_returns_unchanged_without_oc():
    url = "https://www.law.go.kr/DRF/lawSearch.do?target=prec&type=JSON"
    assert mask_oc_in_url(url) == url


def test_mask_oc_in_url_non_string_pass_through():
    assert mask_oc_in_url(None) is None
    assert mask_oc_in_url(123) == 123


def test_mask_oc_in_url_preserves_other_params():
    url = "https://x.com/?target=prec&page=1&OC=LongApiKey123&display=10"
    masked = mask_oc_in_url(url)
    assert "target=prec" in masked
    assert "page=1" in masked
    assert "display=10" in masked
    assert "OC=LongApiKey123" not in masked


# ---------------------------------------------------------------------------
# sanitize_for_mcp_json — dict tree에서 api_url 마스킹
# ---------------------------------------------------------------------------


def test_sanitize_masks_api_url_in_nested_dict():
    payload = {
        "success": True,
        "api_url": "https://x.com/?OC=LexGuardKey",
        "result": {
            "api_url": "https://x.com/?OC=AnotherKey",
            "items": [{"api_url": "https://x.com/?OC=NestedKeyValue"}],
        },
    }
    sanitized = sanitize_for_mcp_json(payload)
    assert "LexGuardKey" not in sanitized["api_url"]
    assert "AnotherKey" not in sanitized["result"]["api_url"]
    assert "NestedKeyValue" not in sanitized["result"]["items"][0]["api_url"]


def test_sanitize_leaves_non_api_url_strings_alone():
    """api_url 외 다른 키에 동일 URL이 들어가도 마스킹 대상 아님 (키 기반 매칭)."""
    payload = {
        "url": "https://x.com/?OC=LexGuardKey",
        "api_url": "https://x.com/?OC=LexGuardKey",
    }
    sanitized = sanitize_for_mcp_json(payload)
    assert sanitized["url"] == "https://x.com/?OC=LexGuardKey"
    assert "LexGuardKey" not in sanitized["api_url"]


# ---------------------------------------------------------------------------
# law_comparison_tool — 빈 응답 명시화
# ---------------------------------------------------------------------------


def test_law_comparison_empty_comparison_marks_missing_reason():
    result = {
        "law_name": "형법",
        "compare_type": "3단비교",
        "comparison": {},
        "api_url": "https://x.com/?OC=LexGuardKey",
    }
    formatted = format_search_response(result, "law_comparison_tool")
    assert formatted["success"] is False
    assert formatted["missing_reason"] == "EMPTY_COMPARISON"
    assert "recovery_guide" in formatted


def test_law_comparison_nonempty_comparison_marks_success():
    result = {
        "law_name": "근로기준법",
        "compare_type": "신구법",
        "comparison": {"OldAndNewService": {"신조문목록": {"조문": [{"content": "..."}]}}},
        "api_url": "https://x.com/?OC=LexGuardKey",
    }
    formatted = format_search_response(result, "law_comparison_tool")
    assert formatted["success"] is True
    assert "missing_reason" not in formatted
    assert formatted["law_name"] == "근로기준법"


def test_law_comparison_none_comparison_marks_missing_reason():
    result = {
        "law_name": "민법",
        "compare_type": "연혁",
        "comparison": None,
        "api_url": "https://x.com/?OC=LexGuardKey",
    }
    formatted = format_search_response(result, "law_comparison_tool")
    assert formatted["success"] is False
    assert formatted["missing_reason"] == "EMPTY_COMPARISON"


def test_legacy_compare_laws_tool_name_still_works():
    """이전 도구 이름 키 호환성 유지."""
    result = {"law_name": "민법", "compare_type": "신구법", "comparison": {"x": 1}}
    formatted = format_search_response(result, "compare_laws_tool")
    assert formatted["success"] is True
