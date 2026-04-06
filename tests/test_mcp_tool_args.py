"""mcp_tool_args — law_comparison 검증"""
from src.utils.mcp_tool_args import resolve_law_comparison_tool


def test_resolve_law_comparison_ok():
    req, err = resolve_law_comparison_tool({"law_name": " 민법 ", "compare_type": "연혁"})
    assert err is None
    assert req is not None
    assert req.law_name == "민법"
    assert req.compare_type == "연혁"


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
