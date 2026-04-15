"""situation_guidance_service 내부 헬퍼 함수 모음.

comprehensive_search 와 document_issue_analysis 에서 반복 사용되는
데이터 조회·집계 함수를 모듈 레벨로 추출합니다.
"""
from typing import Optional, List, Dict


# ------------------------------------------------------------------ #
# comprehensive_search 헬퍼
# ------------------------------------------------------------------ #

def has_law_data(payload: dict) -> bool:
    """에러 없이 법령 데이터가 있으면 True."""
    if not isinstance(payload, dict):
        return False
    if "error" in payload:
        return False
    return bool(payload.get("laws") or payload.get("law_name"))


def has_precedent_data(payload: dict) -> bool:
    """에러 없이 판례 데이터가 있으면 True."""
    if not isinstance(payload, dict):
        return False
    if "error" in payload:
        return False
    return bool(payload.get("precedents"))


def has_interpretation_data(payload: dict) -> bool:
    """에러 없이 법령해석 데이터가 있으면 True."""
    if not isinstance(payload, dict):
        return False
    if "error" in payload:
        return False
    return bool(payload.get("interpretations"))


def has_appeal_data(payload: dict) -> bool:
    """에러 없이 행정심판 데이터가 있으면 True."""
    if not isinstance(payload, dict):
        return False
    if "error" in payload:
        return False
    return bool(payload.get("appeals"))


def collect_error(payload: dict) -> Optional[dict]:
    """에러 응답(error/api_error/HTML 반환)을 그대로 반환, 정상이면 None."""
    if not isinstance(payload, dict):
        return None
    content_type = payload.get("content_type") or payload.get("api_error", {}).get("content_type")
    if "error" in payload or "api_error" in payload:
        return payload
    if isinstance(content_type, str) and content_type.lower().startswith("text/html"):
        return payload
    return None


# ------------------------------------------------------------------ #
# document_issue_analysis 헬퍼
# ------------------------------------------------------------------ #

def count_sources(payload: Optional[dict]) -> int:
    """smart_search 결과에서 법적 근거 수를 집계합니다."""
    if not isinstance(payload, dict):
        return 0
    sources_count = payload.get("sources_count")
    if isinstance(sources_count, dict):
        return sum(int(v or 0) for v in sources_count.values())
    results = payload.get("results", {}) if isinstance(payload.get("results"), dict) else {}
    law_count = len(results.get("law", {}).get("laws", [])) if isinstance(results.get("law"), dict) else 0
    precedent_count = len(results.get("precedent", {}).get("precedents", [])) if isinstance(results.get("precedent"), dict) else 0
    interpretation_count = len(results.get("interpretation", {}).get("interpretations", [])) if isinstance(results.get("interpretation"), dict) else 0
    if not (law_count or precedent_count or interpretation_count):
        citations = payload.get("citations")
        if isinstance(citations, list) and citations:
            return len(citations)
    return law_count + precedent_count + interpretation_count


def collect_precedents(payload: Optional[dict]) -> List[str]:
    """smart_search 결과에서 판례 사건명 목록(최대 5건)을 반환합니다."""
    if not isinstance(payload, dict):
        return []
    results = payload.get("results", {}) if isinstance(payload.get("results"), dict) else {}
    precedents = (
        results.get("precedent", {}).get("precedents", [])
        if isinstance(results.get("precedent", {}), dict)
        else []
    )
    names = []
    for item in precedents:
        if isinstance(item, dict):
            name = item.get("case_name") or item.get("caseNumber") or item.get("case_number")
            if name:
                names.append(name)
    return names[:5]


def collect_citations(payload: Optional[dict]) -> List[dict]:
    """smart_search 결과에서 citations 목록(최대 5건)을 반환합니다."""
    if not isinstance(payload, dict):
        return []
    citations = payload.get("citations", [])
    return citations[:5] if isinstance(citations, list) else []
