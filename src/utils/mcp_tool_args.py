"""
MCP tools/call 공통 인자 검증 (라우트와 테스트에서 동일 로직 사용)
"""
from typing import Optional, Tuple

from ..models import CompareLawsRequest


def resolve_law_comparison_tool(
    arguments: dict,
) -> Tuple[Optional[CompareLawsRequest], Optional[dict]]:
    """
    law_comparison_tool 인자 검증.
    성공 시 (CompareLawsRequest, None), 실패 시 (None, error_dict).
    """
    raw_ln = arguments.get("law_name")
    law_name = (raw_ln or "").strip() if isinstance(raw_ln, str) else ""
    if not law_name:
        return None, {
            "error_code": "INVALID_INPUT",
            "error": "law_name이 필요합니다.",
            "recovery_guide": "비교할 법령명을 입력하세요.",
        }
    ct_raw = arguments.get("compare_type") or "신구법"
    if ct_raw not in ("신구법", "연혁", "3단비교"):
        return None, {
            "error_code": "INVALID_INPUT",
            "error": "compare_type이 올바르지 않습니다.",
            "recovery_guide": "compare_type은 신구법, 연혁, 3단비교 중 하나여야 합니다.",
        }
    return CompareLawsRequest(law_name=law_name, compare_type=ct_raw), None
