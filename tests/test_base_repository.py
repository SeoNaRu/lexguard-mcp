"""
BaseLawRepository 유틸리티 메서드 단위 테스트

API 호출 없이 순수 유틸리티 로직을 검증.
"""

import importlib

import pytest
from src.repositories import base as base_module
from src.repositories.base import BaseLawRepository


@pytest.fixture
def repo():
    return BaseLawRepository()


# ---------------------------------------------------------------------------
# is_placeholder_key
# ---------------------------------------------------------------------------


class TestIsPlaceholderKey:
    def test_none_is_placeholder(self, repo):
        assert repo.is_placeholder_key(None) is True

    def test_empty_string_is_placeholder(self, repo):
        assert repo.is_placeholder_key("") is True

    def test_whitespace_is_placeholder(self, repo):
        assert repo.is_placeholder_key("   ") is True

    def test_your_api_key_is_placeholder(self, repo):
        assert repo.is_placeholder_key("your_api_key") is True

    def test_test_is_placeholder(self, repo):
        assert repo.is_placeholder_key("test") is True

    def test_dummy_is_placeholder(self, repo):
        assert repo.is_placeholder_key("dummy") is True

    def test_starts_with_your_is_placeholder(self, repo):
        assert repo.is_placeholder_key("your_anything_here") is True

    def test_real_key_is_not_placeholder(self, repo):
        assert repo.is_placeholder_key("actualrealkey123") is False

    def test_short_real_key_is_not_placeholder(self, repo):
        assert repo.is_placeholder_key("abc123") is False


# ---------------------------------------------------------------------------
# mask_api_key
# ---------------------------------------------------------------------------


class TestMaskApiKey:
    def test_none_returns_empty(self, repo):
        assert repo.mask_api_key(None) == ""

    def test_empty_returns_empty(self, repo):
        assert repo.mask_api_key("") == ""

    def test_long_key_masked(self, repo):
        result = repo.mask_api_key("abcdefgh12345678")
        assert "****" in result
        assert result.startswith("abcd")
        assert result.endswith("5678")

    def test_short_key_masked(self, repo):
        result = repo.mask_api_key("abcd")
        assert "****" in result

    def test_mask_hides_middle(self, repo):
        key = "ABCDEF123456"
        result = repo.mask_api_key(key)
        assert key not in result


# ---------------------------------------------------------------------------
# parse_article_number
# ---------------------------------------------------------------------------


class TestParseArticleNumber:
    def test_simple_article(self, repo):
        result = repo.parse_article_number("제1조")
        assert result == "000001"

    def test_two_digit_article(self, repo):
        result = repo.parse_article_number("제23조")
        assert result == "000023"

    def test_article_with_sub(self, repo):
        result = repo.parse_article_number("제10조의2")
        assert result == "001002"

    def test_empty_returns_zeroes(self, repo):
        result = repo.parse_article_number("")
        assert result == "000000"

    def test_none_like_no_number(self, repo):
        result = repo.parse_article_number("제조")
        assert result == "000000"

    def test_int_article_number(self, repo):
        """MCP JSON에서 article_number가 숫자 타입으로 올 때"""
        assert repo.parse_article_number(50) == "000050"
        assert repo.parse_article_number(1) == "000001"

    def test_none_returns_zeroes(self, repo):
        assert repo.parse_article_number(None) == "000000"


# ---------------------------------------------------------------------------
# normalize_search_query
# ---------------------------------------------------------------------------


class TestNormalizeSearchQuery:
    def test_strips_whitespace(self, repo):
        result = repo.normalize_search_query("  근로기준법  ")
        assert result == "근로기준법"

    def test_collapses_internal_spaces(self, repo):
        result = repo.normalize_search_query("근로  기준  법")
        assert result == "근로 기준 법"

    def test_empty_string(self, repo):
        result = repo.normalize_search_query("")
        assert result == ""

    def test_already_clean(self, repo):
        result = repo.normalize_search_query("개인정보보호법")
        assert result == "개인정보보호법"


# ---------------------------------------------------------------------------
# _has_html_body
# ---------------------------------------------------------------------------


class TestHasHtmlBody:
    def test_html_doctype_detected(self, repo):
        body = "<!DOCTYPE html><html><body>에러</body></html>"
        assert repo._has_html_body(body) is True

    def test_html_tag_detected(self, repo):
        body = "<html><head></head><body>오류 페이지</body></html>"
        assert repo._has_html_body(body) is True

    def test_xml_not_html(self, repo):
        body = '<?xml version="1.0"?><response><item>내용</item></response>'
        assert repo._has_html_body(body) is False

    def test_json_not_html(self, repo):
        body = '{"result": "ok", "data": []}'
        assert repo._has_html_body(body) is False

    def test_empty_not_html(self, repo):
        assert repo._has_html_body("") is False

    def test_none_not_html(self, repo):
        assert repo._has_html_body(None) is False


# ---------------------------------------------------------------------------
# _sanitize_url
# ---------------------------------------------------------------------------


class TestSanitizeUrl:
    def test_masks_oc_param(self, repo):
        url = "https://www.law.go.kr/DRF/lawService.do?OC=myrealapikey&target=law"
        result = repo._sanitize_url(url)
        assert "myrealapikey" not in result
        # URL 인코딩 후에도 마스킹 확인 (* → %2A)
        assert "****" in result or "%2A%2A%2A%2A" in result

    def test_preserves_other_params(self, repo):
        url = "https://www.law.go.kr/DRF/lawService.do?OC=mykey&target=law&type=JSON"
        result = repo._sanitize_url(url)
        assert "target=law" in result
        assert "type=JSON" in result

    def test_url_without_oc_unchanged(self, repo):
        url = "https://www.law.go.kr/DRF/lawService.do?target=law&type=JSON"
        result = repo._sanitize_url(url)
        assert result == url

    def test_empty_url_returns_empty(self, repo):
        assert repo._sanitize_url("") == ""


# ---------------------------------------------------------------------------
# DRF URL generation
# ---------------------------------------------------------------------------


class TestDrfUrlGeneration:
    def test_default_scheme_is_https(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("LAW_GO_KR_DRF_SCHEME", raising=False)
        reloaded = importlib.reload(base_module)

        assert reloaded.LAW_API_BASE_URL == "https://www.law.go.kr/DRF/lawService.do"
        assert reloaded.LAW_API_SEARCH_URL == "https://www.law.go.kr/DRF/lawSearch.do"

    def test_http_scheme_supported(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("LAW_GO_KR_DRF_SCHEME", "http")
        reloaded = importlib.reload(base_module)

        assert reloaded.LAW_API_BASE_URL == "http://www.law.go.kr/DRF/lawService.do"
        assert reloaded.LAW_API_SEARCH_URL == "http://www.law.go.kr/DRF/lawSearch.do"

    def test_https_scheme_supported(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("LAW_GO_KR_DRF_SCHEME", "https")
        reloaded = importlib.reload(base_module)

        assert reloaded.LAW_API_BASE_URL == "https://www.law.go.kr/DRF/lawService.do"
        assert reloaded.LAW_API_SEARCH_URL == "https://www.law.go.kr/DRF/lawSearch.do"

    def test_invalid_scheme_falls_back_to_https(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("LAW_GO_KR_DRF_SCHEME", "ftp")
        reloaded = importlib.reload(base_module)

        assert reloaded.LAW_API_BASE_URL == "https://www.law.go.kr/DRF/lawService.do"
        assert reloaded.LAW_API_SEARCH_URL == "https://www.law.go.kr/DRF/lawSearch.do"
