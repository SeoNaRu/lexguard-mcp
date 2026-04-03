"""
MCP Resources 핸들러
law://, case://, interpret:// URI 스킴 지원

resources/list  → 대표 법령 목록 + URI 템플릿 반환
resources/read  → URI 파싱 후 실제 법령/판례/해석 데이터 반환
"""
import asyncio
import json
import logging
from typing import Optional

logger = logging.getLogger("lexguard-mcp")

# ---------------------------------------------------------------------------
# 정적 대표 법령 목록 (도메인별 핵심 법령)
# ---------------------------------------------------------------------------
_FEATURED_LAWS = [
    {"name": "근로기준법",        "domain": "노동"},
    {"name": "개인정보보호법",    "domain": "개인정보"},
    {"name": "주택임대차보호법",  "domain": "부동산"},
    {"name": "소비자기본법",      "domain": "소비자"},
    {"name": "소득세법",          "domain": "세금"},
    {"name": "민법",              "domain": "일반"},
    {"name": "형법",              "domain": "일반"},
    {"name": "국민건강보험법",    "domain": "의료"},
]

# ---------------------------------------------------------------------------
# resources/list
# ---------------------------------------------------------------------------

def build_resources_list() -> dict:
    """
    resources/list 응답용 딕셔너리 반환.

    Returns:
        {"resources": [...], "resourceTemplates": [...]}
    """
    resources = [
        {
            "uri": f"law://{law['name']}",
            "name": law["name"],
            "description": f"{law['name']} 전문 조회 ({law['domain']} 도메인)",
            "mimeType": "text/plain",
        }
        for law in _FEATURED_LAWS
    ]

    resource_templates = [
        {
            "uriTemplate": "law://{법령명}",
            "name": "법령 본문",
            "description": (
                "법령명으로 법령 본문과 조문 목록을 조회합니다. "
                "예: law://근로기준법  또는  law://개인정보보호법"
            ),
            "mimeType": "text/plain",
        },
        {
            "uriTemplate": "case://{검색어}",
            "name": "판례 검색",
            "description": (
                "키워드로 관련 판례를 검색합니다. "
                "예: case://부당해고  또는  case://개인정보유출손해배상"
            ),
            "mimeType": "text/plain",
        },
        {
            "uriTemplate": "interpret://{검색어}",
            "name": "법령해석",
            "description": (
                "키워드로 법령해석 목록을 조회합니다. "
                "예: interpret://근로시간  또는  interpret://개인정보처리"
            ),
            "mimeType": "text/plain",
        },
    ]

    return {"resources": resources, "resourceTemplates": resource_templates}


# ---------------------------------------------------------------------------
# resources/read
# ---------------------------------------------------------------------------

def parse_resource_uri(uri: str) -> Optional[tuple]:
    """
    URI를 (scheme, identifier) 형태로 파싱.

    Returns:
        (scheme, identifier) 또는 None (파싱 실패 시)
    """
    if not uri or "://" not in uri:
        return None
    scheme, identifier = uri.split("://", 1)
    identifier = identifier.strip().rstrip("/")
    if not identifier:
        return None
    return scheme.lower(), identifier


async def read_resource(
    uri: str,
    law_detail_repo,
    precedent_repo,
    interpretation_repo,
) -> dict:
    """
    URI에 해당하는 리소스를 조회하고 MCP content 배열 형태로 반환.

    Supported URI schemes:
        law://{법령명}          → 법령 상세 (법령명으로 조회)
        case://{검색어}         → 판례 검색 (상위 5건)
        interpret://{검색어}    → 법령해석 검색 (상위 5건)

    Returns:
        {"contents": [{"uri": ..., "mimeType": "text/plain", "text": ...}]}
        또는 {"error": "...", "contents": [...]}
    """
    parsed = parse_resource_uri(uri)
    if parsed is None:
        msg = f"지원하지 않는 URI 형식입니다: '{uri}'"
        logger.warning("resources/read invalid URI | uri=%s", uri)
        return _error_content(uri, msg)

    scheme, identifier = parsed
    logger.info("resources/read | scheme=%s identifier=%s", scheme, identifier)

    if scheme == "law":
        return await _read_law(uri, identifier, law_detail_repo)

    elif scheme == "case":
        return await _read_case(uri, identifier, precedent_repo)

    elif scheme == "interpret":
        return await _read_interpret(uri, identifier, interpretation_repo)

    else:
        msg = f"지원하지 않는 URI 스킴입니다: '{scheme}://'. 사용 가능: law://, case://, interpret://"
        logger.warning("resources/read unsupported scheme | scheme=%s", scheme)
        return _error_content(uri, msg)


# ---------------------------------------------------------------------------
# 내부 조회 함수
# ---------------------------------------------------------------------------

async def _read_law(uri: str, law_name: str, law_detail_repo) -> dict:
    """law://{법령명} → 법령 상세 조회"""
    try:
        result = await asyncio.to_thread(
            law_detail_repo.get_law,
            None,       # law_id
            law_name,   # law_name
            "detail",   # mode
            None,       # article_number
            None,       # hang
            None,       # ho
            None,       # mok
            None,       # arguments (API 키는 서버 환경변수에서 자동 로드)
        )
    except Exception as e:
        logger.error("resources/read law error | law=%s error=%s", law_name, e)
        return _error_content(uri, f"법령 조회 중 오류 발생: {e}")

    if not result or result.get("error"):
        reason = (result or {}).get("error", "조회 결과 없음")
        return _error_content(uri, f"'{law_name}' 법령을 찾을 수 없습니다. ({reason})")

    # 사람이 읽기 좋은 텍스트 형태로 변환
    text = _law_result_to_text(law_name, result)
    return _ok_content(uri, text)


async def _read_case(uri: str, keyword: str, precedent_repo) -> dict:
    """case://{검색어} → 판례 검색 (상위 5건 요약)"""
    try:
        result = await asyncio.to_thread(
            precedent_repo.search_precedent,
            keyword,    # query
            1,          # page
            5,          # per_page
            None,       # court
            None,       # date_from
            None,       # date_to
            None,       # arguments
        )
    except Exception as e:
        logger.error("resources/read case error | keyword=%s error=%s", keyword, e)
        return _error_content(uri, f"판례 검색 중 오류 발생: {e}")

    if not result or result.get("error"):
        reason = (result or {}).get("error", "조회 결과 없음")
        return _error_content(uri, f"'{keyword}' 판례를 찾을 수 없습니다. ({reason})")

    text = _precedent_result_to_text(keyword, result)
    return _ok_content(uri, text)


async def _read_interpret(uri: str, keyword: str, interpretation_repo) -> dict:
    """interpret://{검색어} → 법령해석 검색 (상위 5건 요약)"""
    try:
        result = await asyncio.to_thread(
            interpretation_repo.search_law_interpretation,
            keyword,    # query
            1,          # page
            5,          # per_page
            None,       # agency
            None,       # arguments
        )
    except Exception as e:
        logger.error("resources/read interpret error | keyword=%s error=%s", keyword, e)
        return _error_content(uri, f"법령해석 검색 중 오류 발생: {e}")

    if not result or result.get("error"):
        reason = (result or {}).get("error", "조회 결과 없음")
        return _error_content(uri, f"'{keyword}' 법령해석을 찾을 수 없습니다. ({reason})")

    text = _interpretation_result_to_text(keyword, result)
    return _ok_content(uri, text)


# ---------------------------------------------------------------------------
# 텍스트 포맷 변환
# ---------------------------------------------------------------------------

def _law_result_to_text(law_name: str, result: dict) -> str:
    lines = [f"[법령] {law_name}"]

    detail = result.get("detail") or {}
    if isinstance(detail, dict):
        lines.append(f"법령 ID: {result.get('law_id', '-')}")
        promulgation = detail.get("promulgation_date") or detail.get("공포일자", "")
        if promulgation:
            lines.append(f"공포일: {promulgation}")
        enforcement = detail.get("enforcement_date") or detail.get("시행일자", "")
        if enforcement:
            lines.append(f"시행일: {enforcement}")

    articles = result.get("articles") or []
    if articles:
        lines.append(f"\n조문 목록 (총 {len(articles)}개):")
        for art in articles[:20]:
            if isinstance(art, dict):
                num = art.get("article_number") or art.get("조문번호", "")
                title = art.get("article_title") or art.get("조문제목", "")
                content = art.get("content") or art.get("조문내용", "")
                lines.append(f"  {num} {title}")
                if content:
                    lines.append(f"    {str(content)[:200]}")
        if len(articles) > 20:
            lines.append(f"  ... 외 {len(articles) - 20}개 조문")
    else:
        # detail에 raw 데이터가 있으면 JSON으로 출력
        if result:
            lines.append("\n[원본 데이터]")
            lines.append(json.dumps(result, ensure_ascii=False, indent=2)[:2000])

    return "\n".join(lines)


def _precedent_result_to_text(keyword: str, result: dict) -> str:
    lines = [f"[판례 검색] '{keyword}'", f"총 {result.get('total', 0)}건"]
    precedents = result.get("precedents") or []
    for i, prec in enumerate(precedents, 1):
        if not isinstance(prec, dict):
            continue
        case_num = prec.get("case_number") or prec.get("사건번호", "-")
        case_name = prec.get("case_name") or prec.get("사건명", "")
        court = prec.get("court_name") or prec.get("법원명", "")
        date = prec.get("judgment_date") or prec.get("선고일자", "")
        summary = prec.get("summary") or prec.get("판시사항", "")
        lines.append(f"\n{i}. {case_num}")
        if case_name:
            lines.append(f"   사건명: {case_name}")
        if court:
            lines.append(f"   법원: {court}")
        if date:
            lines.append(f"   선고일: {date}")
        if summary:
            lines.append(f"   요지: {str(summary)[:300]}")
    return "\n".join(lines)


def _interpretation_result_to_text(keyword: str, result: dict) -> str:
    lines = [f"[법령해석] '{keyword}'", f"총 {result.get('total', 0)}건"]
    interpretations = result.get("interpretations") or []
    for i, interp in enumerate(interpretations, 1):
        if not isinstance(interp, dict):
            continue
        title = interp.get("title") or interp.get("제목", "-")
        agency = interp.get("agency_name") or interp.get("기관명", "")
        date = interp.get("issue_date") or interp.get("발행일", "")
        summary = interp.get("summary") or interp.get("요지", "")
        lines.append(f"\n{i}. {title}")
        if agency:
            lines.append(f"   기관: {agency}")
        if date:
            lines.append(f"   일자: {date}")
        if summary:
            lines.append(f"   요지: {str(summary)[:300]}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

def _ok_content(uri: str, text: str) -> dict:
    return {"contents": [{"uri": uri, "mimeType": "text/plain", "text": text}]}


def _error_content(uri: str, message: str) -> dict:
    return {
        "error": message,
        "contents": [{"uri": uri, "mimeType": "text/plain", "text": f"[오류] {message}"}],
    }
