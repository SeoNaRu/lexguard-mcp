"""
MCP tools/call 공통 인자 검증 (라우트와 테스트에서 동일 로직 사용)
"""
import re
from typing import Optional, Tuple

from ..models import CompareLawsRequest


_COMMON_LAW_NAMES: Tuple[str, ...] = (
    "민법", "형법", "상법", "헌법",
    "근로기준법", "노동조합법", "산업재해보상보험법", "고용보험법",
    "국민연금법", "국민건강보험법",
    "개인정보보호법", "정보통신망법", "통신비밀보호법",
    "주택임대차보호법", "상가건물임대차보호법", "부동산등기법",
    "공인중개사법", "주택법", "건축법",
    "국가공무원법", "지방공무원법", "공무원연금법",
    "도로교통법", "교통사고처리특례법", "자동차관리법",
    "형사소송법", "민사소송법", "민사집행법", "행정소송법", "행정심판법",
    "국세기본법", "부가가치세법", "소득세법", "법인세법",
    "공정거래법", "약관규제법", "표시광고법",
    "소비자기본법", "전자상거래법",
    "저작권법", "특허법", "상표법", "디자인보호법", "부정경쟁방지법",
    "의료법", "약사법",
    "가사소송법", "가족관계등록법",
    "청소년보호법", "아동복지법", "노인복지법", "장애인복지법",
    "채무자회생법",
    "변호사법",
    "교육기본법", "초중등교육법", "고등교육법",
    "주민등록법", "출입국관리법", "병역법",
)

_NON_LAW_WORDS: frozenset = frozenset({
    "방법", "기법", "비법", "수법", "용법", "타법", "당법", "차법", "활법", "어법",
    "묘법", "예법", "별법", "위법", "준법", "범법", "탈법", "악법",
    "신법", "구법", "신구법",
})


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
    """툴 호출 인자에 자연어가 섞여 와도 법령명만 최대한 추출한다.

    우선순위:
      1) 자주 쓰이는 법령명 사전에 일치하는 가장 긴 부분 문자열
      2) `...법`으로 끝나는 정규식 매칭 중 비법령 토큰("방법", "기법" 등) 제외 첫 후보
      3) 명령 표현/비교 표현을 제거한 잔여 텍스트
    """
    if not isinstance(raw, str):
        return ""

    text = raw.strip()
    if not text:
        return ""

    compact = re.sub(r"\s+", "", text)
    dictionary_hits = [name for name in _COMMON_LAW_NAMES if name in compact]
    if dictionary_hits:
        dictionary_hits.sort(key=len, reverse=True)
        return dictionary_hits[0]

    candidates = re.findall(r"[가-힣A-Za-z0-9·ㆍ]+법", text)
    for candidate in candidates:
        if candidate in _NON_LAW_WORDS:
            continue
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
