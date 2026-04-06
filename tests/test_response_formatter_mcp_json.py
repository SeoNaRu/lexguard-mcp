"""format_mcp_response JSON 직렬화 (httpx.URL 등)."""

import json

import httpx

from src.utils.response_formatter import format_mcp_response, sanitize_for_mcp_json


def test_sanitize_for_mcp_json_nested_httpx_url():
    u = httpx.URL("https://www.law.go.kr/DRF/lawSearch.do?query=test")
    raw = {"outer": {"api_url": u}, "list": [u]}
    out = sanitize_for_mcp_json(raw)
    assert out["outer"]["api_url"] == str(u)
    assert out["list"][0] == str(u)


def test_format_mcp_response_with_httpx_url_in_api_url():
    u = httpx.URL("https://www.law.go.kr/DRF/lawSearch.do")
    result = format_mcp_response(
        {"query": "근로기준법", "laws": [], "total": 0, "api_url": u},
        "search_law_tool",
    )
    payload = json.loads(result["content"][-1]["text"])
    assert payload["api_url"] == str(u)
    assert result["structuredContent"]["api_url"] == str(u)
