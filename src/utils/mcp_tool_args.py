"""
MCP tools/call 공통 인자 검증 (라우트와 테스트에서 동일 로직 사용)
"""
import re
from typing import Optional, Tuple

from ..models import CompareLawsRequest


def _normalize_compare_type(raw: object) -> Optional[str]:
    """비교 유형 표현 변형을 표준 compare_type으로 정규화한다."""
    if not isinstance(raw, str):
        return None

    text = raw.strip()
    if not text:
        return None

    compact = re.sub(r"\s+", "", text)
    compact = compact.replace("·", "")

    if "연혁" in compact:
        return "연혁"
    if re.search(r"(?:3|삼|세)단(?:계)?비교", compact):
        return "3단비교"
    if "신구법" in compact or "신구비교" in compact:
        return "신구법"
    return None


def _normalize_law_name(raw: object) -> str:
    """툴 호출 인자에 자연어가 섞여 와도 법령명만 최대한 추출한다."""
    if not isinstance(raw, str):
        return ""

    text = raw.strip()
    if not text:
        return ""

    candidates = re.findall(r"[가-힣A-Za-z0-9·ㆍ]+법", text)
    for candidate in candidates:
        if candidate != "신구법":
            return candidate

    cleaned = re.sub(r"(신구법|연혁|(?:3|삼|세)단(?:계)?\s*비교)", " ", text)
    cleaned = re.sub(r"(조회|비교|보여줘|알려줘|확인해줘|찾아줘)", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def resolve_law_comparison_tool(
    arguments: dict,
) -> Tuple[Optional[CompareLawsRequest], Optional[dict]]:
    """
    law_comparison_tool 인자 검증.
    성공 시 (CompareLawsRequest, None), 실패 시 (None, error_dict).
    """
    raw_ln = arguments.get("law_name")
    law_name = _normalize_law_name(raw_ln)
    if not law_name:
        return None, {
            "error_code": "INVALID_INPUT",
            "error": "law_name이 필요합니다.",
            "recovery_guide": "비교할 법령명을 입력하세요.",
        }

    ct_raw = arguments.get("compare_type")
    compare_type = _normalize_compare_type(ct_raw)
    if isinstance(ct_raw, str) and ct_raw.strip() and compare_type is None:
        return None, {
            "error_code": "INVALID_INPUT",
            "error": "compare_type이 올바르지 않습니다.",
            "recovery_guide": "compare_type은 신구법, 연혁, 3단비교 중 하나여야 합니다.",
        }
    compare_type = compare_type or _normalize_compare_type(raw_ln) or "신구법"
    return CompareLawsRequest(law_name=law_name, compare_type=compare_type), None
