"""MCP resource_handlers URI·정적 리소스 테스트."""

import pytest

from src.routes.resource_handlers import (
    _parse_law_uri_segments,
    _read_lexguard_static,
    parse_resource_uri,
    read_resource,
)


def test_parse_resource_uri_law_with_article():
    assert parse_resource_uri("law://근로기준법/50") == ("law", "근로기준법/50")


def test_parse_law_uri_segments_full():
    law, a, h, ho, m = _parse_law_uri_segments("민법/103/2/1/가")
    assert law == "민법"
    assert a == "103"
    assert h == "2"
    assert ho == "1"
    assert m == "가"


def test_parse_law_uri_segments_article_only():
    law, a, h, ho, m = _parse_law_uri_segments("근로기준법/50")
    assert law == "근로기준법"
    assert a == "50"
    assert h is None


def test_parse_resource_uri_lexguard():
    assert parse_resource_uri("lexguard://integration-handbook") == (
        "lexguard",
        "integration-handbook",
    )


def test_read_lexguard_handbook_ok():
    r = _read_lexguard_static("lexguard://integration-handbook", "integration-handbook")
    assert "error" not in r
    assert r["contents"][0]["mimeType"] == "text/markdown"
    assert "law://" in r["contents"][0]["text"]


def test_read_lexguard_unknown():
    r = _read_lexguard_static("lexguard://nope", "nope")
    assert r.get("error")


@pytest.mark.asyncio
async def test_read_resource_lexguard_async():
    r = await read_resource(
        "lexguard://integration-handbook",
        None,
        None,
        None,
        None,
    )
    assert "law://" in r["contents"][0]["text"]
    assert "캐시" in r["contents"][0]["text"] or "URI" in r["contents"][0]["text"]
