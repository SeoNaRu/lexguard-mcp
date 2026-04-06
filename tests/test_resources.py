"""
MCP Resources 엔드포인트 테스트

resource_handlers.py의 build_resources_list / parse_resource_uri / 텍스트 포맷 함수를 검증.
read_resource 는 실제 API 호출이 필요해서 URI 파싱 + 에러 응답만 단위 테스트.
"""
from src.routes.resource_handlers import (
    build_resources_list,
    parse_resource_uri,
    _law_result_to_text,
    _precedent_result_to_text,
    _interpretation_result_to_text,
    _ok_content,
    _error_content,
)


# ---------------------------------------------------------------------------
# build_resources_list
# ---------------------------------------------------------------------------

class TestBuildResourcesList:
    def test_returns_dict(self):
        result = build_resources_list()
        assert isinstance(result, dict)

    def test_has_resources_key(self):
        result = build_resources_list()
        assert "resources" in result

    def test_has_resource_templates_key(self):
        result = build_resources_list()
        assert "resourceTemplates" in result

    def test_resources_is_list(self):
        result = build_resources_list()
        assert isinstance(result["resources"], list)

    def test_resource_templates_is_list(self):
        result = build_resources_list()
        assert isinstance(result["resourceTemplates"], list)

    def test_featured_laws_count(self):
        result = build_resources_list()
        assert len(result["resources"]) >= 5

    def test_each_resource_has_uri(self):
        result = build_resources_list()
        for r in result["resources"]:
            assert "uri" in r
            assert r["uri"].startswith("law://") or r["uri"].startswith("lexguard://")

    def test_each_resource_has_name_and_description(self):
        result = build_resources_list()
        for r in result["resources"]:
            assert "name" in r
            assert "description" in r
            assert r["name"].strip()

    def test_each_resource_has_mime_type(self):
        result = build_resources_list()
        for r in result["resources"]:
            assert r.get("mimeType") in ("text/plain", "text/markdown")

    def test_templates_cover_all_schemes(self):
        result = build_resources_list()
        templates = result["resourceTemplates"]
        uri_templates = [t["uriTemplate"] for t in templates]
        assert sum(1 for u in uri_templates if u.startswith("law://")) >= 3
        assert any("case://" in u for u in uri_templates)
        assert any("interpret://" in u for u in uri_templates)
        assert any("appeal://" in u for u in uri_templates)

    def test_templates_have_required_fields(self):
        result = build_resources_list()
        for tmpl in result["resourceTemplates"]:
            assert "uriTemplate" in tmpl
            assert "name" in tmpl
            assert "description" in tmpl

    def test_geunro_gibunjunbeob_present(self):
        """근로기준법이 대표 법령에 포함되어 있어야 함"""
        result = build_resources_list()
        uris = [r["uri"] for r in result["resources"]]
        assert "law://근로기준법" in uris

    def test_integration_handbook_present(self):
        result = build_resources_list()
        uris = [r["uri"] for r in result["resources"]]
        assert "lexguard://integration-handbook" in uris


# ---------------------------------------------------------------------------
# parse_resource_uri
# ---------------------------------------------------------------------------

class TestParseResourceUri:
    def test_law_uri(self):
        result = parse_resource_uri("law://근로기준법")
        assert result is not None
        scheme, identifier = result
        assert scheme == "law"
        assert identifier == "근로기준법"

    def test_case_uri(self):
        scheme, identifier = parse_resource_uri("case://부당해고")
        assert scheme == "case"
        assert identifier == "부당해고"

    def test_interpret_uri(self):
        scheme, identifier = parse_resource_uri("interpret://근로시간")
        assert scheme == "interpret"
        assert identifier == "근로시간"

    def test_uri_with_trailing_slash(self):
        result = parse_resource_uri("law://근로기준법/")
        assert result is not None
        _, identifier = result
        assert identifier == "근로기준법"

    def test_empty_uri_returns_none(self):
        assert parse_resource_uri("") is None

    def test_no_scheme_returns_none(self):
        assert parse_resource_uri("근로기준법") is None

    def test_empty_identifier_returns_none(self):
        assert parse_resource_uri("law://") is None

    def test_unknown_scheme_parsed(self):
        """알 수 없는 스킴도 파싱은 성공 (read_resource에서 에러 처리)"""
        result = parse_resource_uri("foo://bar")
        assert result is not None
        scheme, _ = result
        assert scheme == "foo"

    def test_scheme_lowercased(self):
        result = parse_resource_uri("LAW://근로기준법")
        assert result is not None
        scheme, _ = result
        assert scheme == "law"

    def test_complex_identifier(self):
        scheme, identifier = parse_resource_uri("case://대법원-2019다12345")
        assert scheme == "case"
        assert identifier == "대법원-2019다12345"


# ---------------------------------------------------------------------------
# _ok_content / _error_content
# ---------------------------------------------------------------------------

class TestContentHelpers:
    def test_ok_content_structure(self):
        result = _ok_content("law://근로기준법", "법령 내용")
        assert "contents" in result
        assert len(result["contents"]) == 1
        content = result["contents"][0]
        assert content["uri"] == "law://근로기준법"
        assert content["mimeType"] == "text/plain"
        assert content["text"] == "법령 내용"

    def test_error_content_has_error_key(self):
        result = _error_content("law://없는법령", "법령을 찾을 수 없습니다")
        assert "error" in result
        assert "없는법령" in result["error"] or "찾을" in result["error"]

    def test_error_content_has_contents(self):
        result = _error_content("case://없음", "오류 메시지")
        assert "contents" in result
        assert len(result["contents"]) == 1

    def test_error_content_text_contains_error(self):
        result = _error_content("case://없음", "오류 메시지")
        text = result["contents"][0]["text"]
        assert "오류" in text or "오류 메시지" in text


# ---------------------------------------------------------------------------
# 텍스트 포맷 함수
# ---------------------------------------------------------------------------

class TestLawResultToText:
    def test_includes_law_name(self):
        result = _law_result_to_text("근로기준법", {"law_id": "123", "articles": []})
        assert "근로기준법" in result

    def test_includes_law_id(self):
        result = _law_result_to_text("형법", {"law_id": "ABC-001", "articles": []})
        assert "ABC-001" in result

    def test_articles_listed(self):
        articles = [
            {"article_number": "제1조", "article_title": "목적", "content": "이 법은..."},
            {"article_number": "제2조", "article_title": "정의", "content": "이 법에서..."},
        ]
        result = _law_result_to_text("근로기준법", {"law_id": "1", "articles": articles})
        assert "제1조" in result
        assert "목적" in result

    def test_articles_truncated_at_20(self):
        articles = [{"article_number": f"제{i}조", "article_title": "", "content": ""} for i in range(30)]
        result = _law_result_to_text("형법", {"law_id": "2", "articles": articles})
        assert "외" in result or "30" in result or "20" in result

    def test_empty_articles_shows_raw_data(self):
        result = _law_result_to_text("민법", {"law_id": "3", "articles": [], "detail": {"공포일자": "20230101"}})
        assert "민법" in result


class TestPrecedentResultToText:
    def test_includes_keyword(self):
        result = _precedent_result_to_text("부당해고", {"total": 0, "precedents": []})
        assert "부당해고" in result

    def test_includes_total(self):
        result = _precedent_result_to_text("손해배상", {"total": 42, "precedents": []})
        assert "42" in result

    def test_formats_case_number(self):
        prec = {
            "case_number": "2023다12345",
            "case_name": "부당해고 사건",
            "court_name": "대법원",
            "judgment_date": "20231015",
            "summary": "근로자성이 인정된다.",
        }
        result = _precedent_result_to_text("부당해고", {"total": 1, "precedents": [prec]})
        assert "2023다12345" in result
        assert "대법원" in result
        assert "근로자성" in result

    def test_summary_truncated(self):
        long_summary = "가" * 500
        prec = {"case_number": "2023다1", "summary": long_summary}
        result = _precedent_result_to_text("테스트", {"total": 1, "precedents": [prec]})
        assert len(result) < 2000


class TestInterpretationResultToText:
    def test_includes_keyword(self):
        result = _interpretation_result_to_text("근로시간", {"total": 0, "interpretations": []})
        assert "근로시간" in result

    def test_formats_interpretation(self):
        interp = {
            "title": "근로시간 산정 방법",
            "agency_name": "고용노동부",
            "issue_date": "20230301",
            "summary": "근로시간은...",
        }
        result = _interpretation_result_to_text("근로시간", {"total": 1, "interpretations": [interp]})
        assert "근로시간 산정 방법" in result
        assert "고용노동부" in result
