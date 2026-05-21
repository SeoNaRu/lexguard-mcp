"""
response_formatter.add_metadata — _meta.fields/response_type/parsing_hint 정확도 검증.

라이브 검증 중 발견된 이슈:
1) response_type_map의 키가 옛 tool 이름들만 등록되어 있어 실제 MCP 이름
   (precedent_lookup_tool, legal_qa_tool, local_ordinance_tool 등)이 모두
   response_type="unknown"으로 떨어지던 문제.
2) success 필드가 명시되지 않은 응답(레거시 raw return 패턴)이 falsy 평가되어
   error 분기로 가서 fields=["error","recovery_guide"]로 잘못 표시되던 문제.
"""
from src.utils.response_formatter import add_metadata, format_mcp_response


# ---------------------------------------------------------------------------
# response_type_map — 현재 MCP tool 이름 등록
# ---------------------------------------------------------------------------


def test_precedent_lookup_tool_maps_to_precedent_list():
    formatted = {"success": True, "query": "부당해고", "total": 28, "precedents": []}
    add_metadata(formatted, "precedent_lookup_tool")
    assert formatted["_meta"]["response_type"] == "precedent_list"
    assert "results.precedents" in formatted["_meta"]["parsing_hint"]


def test_legal_qa_tool_maps_to_integrated_search():
    formatted = {"success": True, "query": "부당해고", "results": {}}
    add_metadata(formatted, "legal_qa_tool")
    assert formatted["_meta"]["response_type"] == "integrated_search"


def test_local_ordinance_tool_maps_to_ordinance_list():
    formatted = {"success": True, "query": "청소년", "total": 410, "ordinances": []}
    add_metadata(formatted, "local_ordinance_tool")
    assert formatted["_meta"]["response_type"] == "ordinance_list"


def test_law_comparison_tool_maps_to_law_comparison():
    formatted = {"success": True, "law_name": "민법", "comparison": {}}
    add_metadata(formatted, "law_comparison_tool")
    assert formatted["_meta"]["response_type"] == "law_comparison"


def test_interpretation_tool_maps_to_interpretation_list():
    formatted = {"success": True, "query": "근로기준법", "interpretations": []}
    add_metadata(formatted, "interpretation_tool")
    assert formatted["_meta"]["response_type"] == "interpretation_list"


def test_law_history_tool_has_parsing_hint():
    formatted = {"success": True, "law_name": "민법", "history": []}
    add_metadata(formatted, "law_history_tool")
    assert formatted["_meta"]["response_type"] == "law_history"
    assert formatted["_meta"]["parsing_hint"] != "응답 구조를 확인하세요."


# ---------------------------------------------------------------------------
# fields 추출 — success 명시되지 않은 응답도 success로 간주
# ---------------------------------------------------------------------------


def test_fields_extracted_when_success_field_absent():
    """success 필드 없어도 error/error_code 없으면 정상 응답으로 처리."""
    formatted = {
        "query": "부당해고",
        "total": 28,
        "precedents": [{"사건번호": "x"}],
        "api_url": "https://x.com",
    }
    add_metadata(formatted, "precedent_lookup_tool")
    assert formatted["_meta"]["fields"] != ["error", "recovery_guide"]
    assert "query" in formatted["_meta"]["fields"]
    assert "precedents" in formatted["_meta"]["fields"]
    assert "api_url" not in formatted["_meta"]["fields"]  # api_url은 메타에서 제외


def test_fields_error_when_explicit_success_false():
    formatted = {"success": False, "error": "API 키 없음", "recovery_guide": "..."}
    add_metadata(formatted, "law_article_tool")
    assert formatted["_meta"]["fields"] == ["error", "recovery_guide"]


def test_fields_error_when_error_key_present_without_success_false():
    formatted = {"error": "타임아웃", "recovery_guide": "재시도하세요"}
    add_metadata(formatted, "law_article_tool")
    assert formatted["_meta"]["fields"] == ["error", "recovery_guide"]


def test_fields_error_when_error_code_present():
    """error_code만 있어도 에러로 판단."""
    formatted = {"error_code": "INVALID_INPUT", "missing_reason": "..."}
    add_metadata(formatted, "law_comparison_tool")
    assert formatted["_meta"]["fields"] == ["error", "recovery_guide"]


def test_success_true_with_normal_fields():
    """전형적인 성공 응답: success=True 명시 + 정상 필드들."""
    formatted = {
        "success": True,
        "law_id": "001872",
        "title": "근로시간",
        "content": "1주 간의 근로시간은...",
        "api_url": "https://x.com",
    }
    add_metadata(formatted, "law_article_tool")
    assert "law_id" in formatted["_meta"]["fields"]
    assert "title" in formatted["_meta"]["fields"]
    assert "content" in formatted["_meta"]["fields"]


def test_unknown_tool_name_falls_back_to_unknown_type():
    """등록되지 않은 tool 이름은 'unknown' + 기본 parsing_hint."""
    formatted = {"success": True, "data": "..."}
    add_metadata(formatted, "totally_unknown_tool")
    assert formatted["_meta"]["response_type"] == "unknown"
    assert formatted["_meta"]["parsing_hint"] == "응답 구조를 확인하세요."


def test_legal_basis_block_pinned_to_top_of_fields():
    """legal_basis_block은 fields 첫 자리로 고정."""
    formatted = {
        "success": True,
        "query": "x",
        "results": {},
        "legal_basis_block": {"summary": None},
    }
    add_metadata(formatted, "legal_qa_tool")
    assert formatted["_meta"]["fields"][0] == "legal_basis_block"


def test_format_mcp_response_preserves_error_code_for_local_ordinance():
    """repository의 INVALID_INPUT이 MCP structuredContent까지 보존되어야 한다."""
    result = {
        "error_code": "INVALID_INPUT",
        "error": "지원하지 않는 지자체 명칭입니다: '없는지역'",
        "recovery_guide": "광역자치단체 명칭을 사용하세요.",
    }

    response = format_mcp_response(result, "local_ordinance_tool")

    assert response["isError"] is True
    assert response["structuredContent"]["success"] is False
    assert response["structuredContent"]["error_code"] == "INVALID_INPUT"
    assert response["structuredContent"]["_meta"]["response_type"] == "ordinance_list"
    assert response["structuredContent"]["_meta"]["fields"] == ["error", "recovery_guide"]


def test_format_mcp_response_preserves_error_code_for_law_article():
    """law_article_tool 전용 에러 포맷도 error_code를 버리지 않는다."""
    result = {
        "error_code": "NOT_FOUND",
        "error": "법령을 찾을 수 없습니다.",
        "recovery_guide": "법령명을 확인하세요.",
    }

    response = format_mcp_response(result, "law_article_tool")

    assert response["isError"] is True
    assert response["structuredContent"]["error_code"] == "NOT_FOUND"
    assert response["structuredContent"]["_meta"]["response_type"] == "law_article"
