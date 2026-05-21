"""mcp_tool_args — law_comparison 검증"""
from src.utils.mcp_tool_args import resolve_law_comparison_tool


def test_resolve_law_comparison_ok():
    req, err = resolve_law_comparison_tool({"law_name": " 민법 ", "compare_type": "연혁"})
    assert err is None
    assert req is not None
    assert req.law_name == "민법"
    assert req.compare_type == "연혁"


def test_resolve_law_comparison_infers_history_from_law_name_phrase():
    req, err = resolve_law_comparison_tool({"law_name": "민법 연혁 조회"})
    assert err is None
    assert req is not None
    assert req.law_name == "민법"
    assert req.compare_type == "연혁"


def test_resolve_law_comparison_infers_three_way_from_law_name_phrase():
    req, err = resolve_law_comparison_tool({"law_name": "형법 3단 비교 보여줘"})
    assert err is None
    assert req is not None
    assert req.law_name == "형법"
    assert req.compare_type == "3단비교"


def test_resolve_law_comparison_infers_default_compare_type_from_phrase():
    req, err = resolve_law_comparison_tool({"law_name": "근로기준법 신구법 비교 보여줘"})
    assert err is None
    assert req is not None
    assert req.law_name == "근로기준법"
    assert req.compare_type == "신구법"


def test_resolve_law_comparison_normalizes_compare_type_phrase():
    req, err = resolve_law_comparison_tool({"law_name": "민법", "compare_type": "연혁 조회"})
    assert err is None
    assert req is not None
    assert req.compare_type == "연혁"


def test_resolve_law_comparison_normalizes_three_way_compare_type_phrase():
    req, err = resolve_law_comparison_tool({"law_name": "형법", "compare_type": "3단 비교"})
    assert err is None
    assert req is not None
    assert req.compare_type == "3단비교"


def test_resolve_law_comparison_empty_law_name():
    req, err = resolve_law_comparison_tool({"law_name": ""})
    assert req is None
    assert err is not None
    assert err.get("error_code") == "INVALID_INPUT"


def test_resolve_law_comparison_bad_compare_type():
    req, err = resolve_law_comparison_tool({"law_name": "형법", "compare_type": "wrong"})
    assert req is None
    assert err is not None
    assert err.get("error_code") == "INVALID_INPUT"


# ---------------------------------------------------------------------------
# _normalize_law_name 강화 — 사전 매칭 우선 + 비법령 토큰 블랙리스트
# ---------------------------------------------------------------------------


def test_law_name_dictionary_match_skips_non_law_token():
    """'방법' 같은 비법령 토큰이 앞에 있어도 사전의 진짜 법령명을 선택."""
    req, err = resolve_law_comparison_tool({"law_name": "방법론에 관한 민법 조항 연혁"})
    assert err is None
    assert req.law_name == "민법"
    assert req.compare_type == "연혁"


def test_law_name_dictionary_longest_match_wins():
    """'상가건물임대차보호법'이 '주택임대차보호법' 길이로 우선 매칭 가능. 가장 긴 사전 매칭 채택."""
    req, err = resolve_law_comparison_tool({"law_name": "상가건물임대차보호법 연혁"})
    assert err is None
    assert req.law_name == "상가건물임대차보호법"


def test_law_name_whitespace_variations():
    """공백이 섞여도 사전 매칭 작동: '주택 임대차 보호법' → '주택임대차보호법'."""
    req, err = resolve_law_comparison_tool({"law_name": "주택 임대차 보호법 신구법 비교"})
    assert err is None
    assert req.law_name == "주택임대차보호법"
    assert req.compare_type == "신구법"


def test_law_name_skips_blacklisted_law_suffix_tokens():
    """사전에 없는 입력에서, '위법'·'준법' 같은 비법령 토큰은 건너뛰고 다음 후보 선택."""
    req, err = resolve_law_comparison_tool({"law_name": "위법한 행위와 관련된 주민등록법 연혁"})
    assert err is None
    assert req.law_name == "주민등록법"


def test_law_name_falls_back_to_first_when_not_in_dictionary():
    """사전에 없는 법령명도 정규식 후보로 추출. 첫 비-블랙리스트 후보 선택."""
    req, err = resolve_law_comparison_tool({"law_name": "전기사업법 신구법 비교 보여줘"})
    assert err is None
    assert req.law_name == "전기사업법"
    assert req.compare_type == "신구법"


def test_law_name_ignores_sinkubeop_token_alone():
    """'신구법' 토큰만 들어오고 다른 법령명 없는 경우, 추가 cleanup이 빈 결과여도 비-신구법 정상 처리."""
    req, err = resolve_law_comparison_tool({"law_name": "민법 신구법", "compare_type": "신구법"})
    assert err is None
    assert req.law_name == "민법"
    assert req.compare_type == "신구법"


def test_law_name_dictionary_picks_correct_target_over_method():
    """'방법'이 앞에 와도 사전의 형법 인식. 정규식 fallback이라면 '방법'을 잡아 오류였을 케이스."""
    req, err = resolve_law_comparison_tool({"law_name": "수사방법을 정한 형법 조항 연혁"})
    assert err is None
    assert req.law_name == "형법"
