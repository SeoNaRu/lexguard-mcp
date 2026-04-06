"""
MCP Resources 핸들러
law://, case://, interpret://, appeal://, lexguard:// URI 스킴 지원

resources/list  → 대표 법령 목록 + URI 템플릿 반환
resources/read  → URI 파싱 후 실제 법령/판례/해석 데이터 반환
"""
import json
import logging
from typing import Optional

logger = logging.getLogger("lexguard-mcp")

# ---------------------------------------------------------------------------
# 클라이언트용 통합 안내 (resources/read: lexguard://integration-handbook)
# ---------------------------------------------------------------------------
_INTEGRATION_HANDBOOK_MD = """# LexGuard MCP — URI·캐시·폴백 안내

본 문서는 LobeHub 등 MCP 클라이언트에서 resources/read로 열람할 수 있습니다. 법적 판단을 제공하지 않습니다.

## 지원 URI 스킴

| URI | 의미 |
|-----|------|
| `law://법령명` | 법령 상세·조문 목록 요약 |
| `law://법령명/조` | 단일 조문 (예: `law://근로기준법/50`) |
| `law://법령명/조/항/호/목` | 조 이후 항·호·목을 순서대로 지정 (앞쪽만 쓰면 조+항 등) |
| `case://검색어` | 판례 검색 상위 5건 요약 |
| `interpret://검색어` | 법령해석 검색 상위 5건 요약 |
| `appeal://검색어` | 행정심판 재결 검색 상위 5건 요약 |

항·호·목이 복잡하면 MCP 툴 `law_article_tool`을 병행하세요.

## HTTP 클라이언트 (비동기)

Repository 메서드는 공유 `httpx.AsyncClient`(`aget`)로 DRF를 호출합니다. 앱 종료 시 lifespan에서 `close_async_client`로 연결을 닫습니다.

## Repository 검색 캐시 키 (서버 내부)

성공 응답은 약 30분, 실패는 약 5분 캐시됩니다. 키는 튜플로 구성되는 경우가 많습니다.

- 판례: `("precedent", query, page, per_page, court, date_from, date_to)`
- 법령해석: `("law_interpretation", query, page, per_page, agency)`
- 행정심판: `("administrative_appeal", query, page, per_page, date_from, date_to)`
- 기타 저장소별로 `search_cache` / `failure_cache`에 동일 패턴 적용

클라이언트는 캐시 키를 직접 넣을 필요는 없고, 동일 질의에 대한 서버 측 중복 호출 완화용으로 이해하면 됩니다.

## eflawjosub 빈 JSON 시 웹 폴백 (선택)

환경변수 `LEXGUARD_EFLAWJOSUB_FALLBACK`:

- 비우거나 미설정: 폴백 없음
- `html`: 동일 요청을 `type=HTML`로 재시도 후 본문 추출
- `playwright`: HTML이 부족하면 headless Chromium으로 동일 URL 로드 (메모리·크롬 바이너리 필요)

Playwright 사용 시: `pip install playwright` 후 `playwright install chromium`. 국가법령정보센터 이용약관·운영 정책을 확인한 뒤 켜세요.
"""

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
            "uriTemplate": "law://{법령명}/{조문번호}",
            "name": "법령 단일 조문",
            "description": (
                "법령명과 조문번호로 해당 조만 조회합니다. "
                "예: law://근로기준법/50. 항·호·목은 law://법/조/항/호/목 템플릿 참고."
            ),
            "mimeType": "text/plain",
        },
        {
            "uriTemplate": "law://{법령명}/{조}/{항}/{호}/{목}",
            "name": "법령 조·항·호·목",
            "description": (
                "경로 최대 5단. 생략 시 뒤 세그먼트만 사용. "
                "예: law://근로기준법/50/1 (조+항)"
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
        {
            "uriTemplate": "appeal://{검색어}",
            "name": "행정심판 재결",
            "description": (
                "키워드로 행정심판 재결 검색 요약을 조회합니다. "
                "예: appeal://취소소송  또는  appeal://과징금"
            ),
            "mimeType": "text/plain",
        },
    ]

    resources.append(
        {
            "uri": "lexguard://integration-handbook",
            "name": "LexGuard URI·캐시 안내",
            "description": (
                "클라이언트용: 지원 URI 스킴, Repository 검색 캐시 키 패턴, "
                "eflawjosub 웹 폴백 환경변수 요약"
            ),
            "mimeType": "text/markdown",
        }
    )

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
    appeal_repo,
) -> dict:
    """
    URI에 해당하는 리소스를 조회하고 MCP content 배열 형태로 반환.

    Supported URI schemes:
        law://{법령명}              → 법령 상세 (법령명으로 조회)
        law://{법령명}/{조문번호}    → 단일 조문
        case://{검색어}             → 판례 검색 (상위 5건)
        interpret://{검색어}        → 법령해석 검색 (상위 5건)
        appeal://{검색어}           → 행정심판 재결 검색 (상위 5건)
        lexguard://integration-handbook → URI·캐시·폴백 문서

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

    elif scheme == "appeal":
        return await _read_appeal(uri, identifier, appeal_repo)

    elif scheme == "lexguard":
        return _read_lexguard_static(uri, identifier)

    else:
        msg = (
            f"지원하지 않는 URI 스킴입니다: '{scheme}://'. "
            "사용 가능: law://, case://, interpret://, appeal://, lexguard://"
        )
        logger.warning("resources/read unsupported scheme | scheme=%s", scheme)
        return _error_content(uri, msg)


# ---------------------------------------------------------------------------
# 내부 조회 함수
# ---------------------------------------------------------------------------

def _parse_law_uri_segments(identifier: str) -> tuple[str, Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    law:// 경로 분할: 법령명[/조][/항][/호][/목] (최대 5세그먼트).
    """
    parts = [p.strip() for p in identifier.split("/") if p.strip()]
    if not parts:
        raise ValueError("empty")
    if len(parts) > 5:
        raise ValueError("too_many")
    law_name = parts[0]
    if len(parts) == 1:
        return (law_name, None, None, None, None)
    article_number = parts[1]
    hang = parts[2] if len(parts) > 2 else None
    ho = parts[3] if len(parts) > 3 else None
    mok = parts[4] if len(parts) > 4 else None
    return (law_name, article_number, hang, ho, mok)


async def _read_law(uri: str, identifier: str, law_detail_repo) -> dict:
    """law://법령명 또는 law://법령명/조/항/호/목 (뒤 세그먼트는 선택)"""
    try:
        law_name, article_number, hang, ho, mok = _parse_law_uri_segments(identifier)
    except ValueError as e:
        if str(e) == "too_many":
            return _error_content(uri, "law:// 경로는 법령명/조/항/호/목 까지 최대 5단입니다.")
        return _error_content(uri, "law:// 식별자가 비어 있습니다.")

    if not law_name:
        return _error_content(uri, "법령명이 비어 있습니다.")

    mode = "single" if article_number else "detail"
    try:
        result = await law_detail_repo.get_law(
            None,
            law_name,
            mode,
            article_number,
            hang,
            ho,
            mok,
            None,
        )
    except Exception as e:
        logger.error("resources/read law error | id=%s error=%s", identifier, e)
        return _error_content(uri, f"법령 조회 중 오류 발생: {e}")

    if not result or result.get("error"):
        reason = (result or {}).get("error", "조회 결과 없음")
        return _error_content(uri, f"'{identifier}' 법령을 찾을 수 없습니다. ({reason})")

    if mode == "single":
        text = _single_article_to_text(law_name, article_number or "", result)
    else:
        text = _law_result_to_text(law_name, result)
    return _ok_content(uri, text)


async def _read_case(uri: str, keyword: str, precedent_repo) -> dict:
    """case://{검색어} → 판례 검색 (상위 5건 요약)"""
    try:
        result = await precedent_repo.search_precedent(
            keyword,
            1,
            5,
            None,
            None,
            None,
            None,
        )
    except Exception as e:
        logger.error("resources/read case error | keyword=%s error=%s", keyword, e)
        return _error_content(uri, f"판례 검색 중 오류 발생: {e}")

    if not result or result.get("error"):
        reason = (result or {}).get("error", "조회 결과 없음")
        return _error_content(uri, f"'{keyword}' 판례를 찾을 수 없습니다. ({reason})")

    text = _precedent_result_to_text(keyword, result)
    return _ok_content(uri, text)


async def _read_appeal(uri: str, keyword: str, appeal_repo) -> dict:
    """appeal://{검색어} → 행정심판 재결 검색 (상위 5건 요약)"""
    try:
        result = await appeal_repo.search_administrative_appeal(
            keyword,
            1,
            5,
            None,
            None,
            None,
        )
    except Exception as e:
        logger.error("resources/read appeal error | keyword=%s error=%s", keyword, e)
        return _error_content(uri, f"행정심판 검색 중 오류 발생: {e}")

    if not result or result.get("error"):
        reason = (result or {}).get("error", "조회 결과 없음")
        return _error_content(uri, f"'{keyword}' 행정심판 재결을 찾을 수 없습니다. ({reason})")

    text = _appeal_result_to_text(keyword, result)
    return _ok_content(uri, text)


async def _read_interpret(uri: str, keyword: str, interpretation_repo) -> dict:
    """interpret://{검색어} → 법령해석 검색 (상위 5건 요약)"""
    try:
        result = await interpretation_repo.search_law_interpretation(
            keyword,
            1,
            5,
            None,
            None,
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

def _read_lexguard_static(uri: str, identifier: str) -> dict:
    if identifier != "integration-handbook":
        return _error_content(uri, f"알 수 없는 lexguard 리소스: {identifier}")
    return {
        "contents": [
            {
                "uri": uri,
                "mimeType": "text/markdown",
                "text": _INTEGRATION_HANDBOOK_MD,
            }
        ]
    }


def _single_article_to_text(law_name: str, article_number: str, result: dict) -> str:
    sub = []
    if result.get("hang"):
        sub.append(f"항 {result.get('hang')}")
    if result.get("ho"):
        sub.append(f"호 {result.get('ho')}")
    if result.get("mok"):
        sub.append(f"목 {result.get('mok')}")
    sub_s = (" " + ", ".join(sub)) if sub else ""
    lines = [f"[조문] {law_name} 제{article_number}조{sub_s} (표기는 원문과 다를 수 있음)"]
    title = result.get("title") or result.get("조문제목")
    content = result.get("content") or result.get("조문내용")
    if title:
        lines.append(str(title))
    if content:
        lines.append(str(content)[:4000])
    if result.get("fallback"):
        lines.append(f"\n[폴백] {result.get('fallback')}")
    return "\n".join(lines)


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


def _appeal_result_to_text(keyword: str, result: dict) -> str:
    lines = [f"[행정심판] '{keyword}'", f"총 {result.get('total', 0)}건"]
    appeals = result.get("appeals") or []
    for i, ap in enumerate(appeals, 1):
        if not isinstance(ap, dict):
            continue
        title = ap.get("title") or ap.get("사건명") or ap.get("재결제목", "-")
        num = ap.get("case_number") or ap.get("사건번호", "")
        date = ap.get("decision_date") or ap.get("재결일자", "")
        summary = ap.get("summary") or ap.get("재결요지", "")
        lines.append(f"\n{i}. {title}")
        if num:
            lines.append(f"   사건번호: {num}")
        if date:
            lines.append(f"   재결일: {date}")
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
