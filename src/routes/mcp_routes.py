"""
MCP Routes - MCP Streamable HTTP 엔드포인트
Controller 패턴: 요청을 받아 Service를 호출
"""
import json
import asyncio
import copy
import os
from importlib.metadata import version as _pkg_version, PackageNotFoundError
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from starlette.requests import ClientDisconnect
from ..services.law_service import LawService
from ..services.health_service import HealthService
from ..services.law_comparison_service import LawComparisonService
from ..services.smart_search_service import SmartSearchService
from ..services.situation_guidance_service import SituationGuidanceService
from ..utils.mcp_tool_args import resolve_law_comparison_tool
from ..utils.document_issue_prompts import (
    DOCUMENT_ISSUE_TOOL_DESCRIPTION_TEXT,
    GENERIC_DOCUMENT_REVIEW_INSTRUCTION,
    LABOR_CONTRACT_REVIEW_INSTRUCTION,
)
from ..utils.response_truncator import shrink_response_bytes
from ..utils.log_sanitize import sanitize_http_headers_for_log
from .resource_handlers import build_resources_list, read_resource
from ..config.settings import get_limiter
import logging

logger = logging.getLogger("lexguard-mcp")

# Cursor MCP는 initialize / tools/list / 세션 등으로 분당 요청이 많다. 기본 60/min은 429 유발.
_MCP_RATE_LIMIT = (os.environ.get("LEXGUARD_MCP_RATE_LIMIT") or "600/minute").strip() or "600/minute"

try:
    _SERVER_VERSION = _pkg_version("lexguard-mcp")
except PackageNotFoundError:
    _SERVER_VERSION = "1.0.0"


def register_mcp_routes(api: FastAPI, law_service: LawService, health_service: HealthService):
    """MCP Streamable HTTP 엔드포인트 등록"""
    smart_search_service = SmartSearchService()
    situation_guidance_service = SituationGuidanceService()
    law_comparison_service = LawComparisonService()

    # resources/read 에서 사용할 repo 인스턴스 (lazy import 방지)
    from ..repositories.law_detail import LawDetailRepository
    from ..repositories.precedent_repository import PrecedentRepository
    from ..repositories.law_interpretation_repository import LawInterpretationRepository
    from ..repositories.administrative_appeal_repository import AdministrativeAppealRepository
    _law_detail_repo = LawDetailRepository()
    _precedent_repo = PrecedentRepository()
    _interpretation_repo = LawInterpretationRepository()
    _appeal_repo = AdministrativeAppealRepository()

    # 모든 요청 로깅 미들웨어 (디버깅용) - Health Check 요청 제외
    @api.middleware("http")
    async def log_all_requests(request: Request, call_next):
        is_health_check = (
            request.url.path == "/health" or
            request.headers.get("render-health-check") == "1"
        )

        if not is_health_check:
            logger.info("=" * 80)
            logger.info(f"ALL REQUEST: {request.method} {request.url}")
            logger.info(f"Client: {request.client}")
            logger.info(f"Path: {request.url.path}")
            logger.info("Headers: %s", sanitize_http_headers_for_log(request.headers))

        try:
            response = await call_next(request)

            if not is_health_check:
                logger.info(f"Response Status: {response.status_code}")
                logger.info("=" * 80)

            return response
        except Exception as e:
            logger.exception(f"Request error: {e}")
            if not is_health_check:
                logger.info("=" * 80)
            raise

    @api.options("/mcp")
    async def mcp_options(request: Request):
        """CORS preflight 요청 처리"""
        logger.info("MCP OPTIONS request received")
        from fastapi.responses import Response
        return Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Accept, Mcp-Session-Id",
                "Access-Control-Max-Age": "86400"
            }
        )

    @api.get("/mcp")
    async def mcp_get_sse_stream(request: Request):
        """MCP Streamable HTTP GET 엔드포인트"""
        accept_header = request.headers.get("Accept", "")
        logger.debug("MCP GET | accept=%s client=%s", accept_header, request.client)

        if accept_header and "text/event-stream" not in accept_header and "*/*" not in accept_header:
            from fastapi import HTTPException
            logger.warning("MCP GET: Unsupported Accept header: %s", accept_header)
            raise HTTPException(status_code=405, detail="Method Not Allowed: SSE stream not supported")

        async def server_to_client_stream():
            yield f"data: {json.dumps({'type': 'stream_opened'})}\n\n"
            try:
                while True:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                logger.debug("SSE stream closed by client")

        return StreamingResponse(
            server_to_client_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    @api.post("/mcp")
    @get_limiter().limit(_MCP_RATE_LIMIT)
    async def mcp_streamable_http(request: Request):
        """
        MCP Streamable HTTP 엔드포인트 (통합·전용 툴)
        JSON-RPC 2.0 메시지를 받아서 SSE로 스트리밍 응답
        Rate limit: LEXGUARD_MCP_RATE_LIMIT (기본 600/min, IP당)
        """
        request.headers.get("Accept", "")
        request.headers.get("Content-Type", "")
        session_id_header = request.headers.get("Mcp-Session-Id", "")
        origin_header = request.headers.get("Origin", "")
        # 요청 본문을 먼저 읽어서 캐시 (한 번만 읽을 수 있으므로)
        try:
            cached_body = await request.body()
            cached_body_text = cached_body.decode("utf-8")
        except ClientDisconnect:
            logger.info("⚠️ Client disconnected before POST handler could read body")
            cached_body = b""
            cached_body_text = ""
        except Exception as e:
            logger.error("❌ Failed to read request body in POST handler: %s", e)
            cached_body = b""
            cached_body_text = ""

        logger.debug(
            "MCP POST | body=%d bytes session=%s origin=%s",
            len(cached_body), session_id_header or "-", origin_header or "-",
        )

        async def generate():
            logger.debug("SSE generate started")

            body_bytes = cached_body
            body_text = cached_body_text

            if not body_bytes:
                logger.warning("⚠️ Empty request body")
                return

            try:
                logger.info("📝 Processing MCP request: %s", body_text[:200] if body_text else "empty")

                data = json.loads(body_text)
                request_id = data.get("id")
                method = data.get("method")
                params = data.get("params", {})

                # initialize 처리
                if method == "initialize":
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "protocolVersion": "2025-06-18",
                            "capabilities": {
                                "tools": {},
                                "prompts": {},
                                "resources": {}
                            },
                            "serverInfo": {
                                "name": "lexguard-mcp",
                                "version": _SERVER_VERSION
                            }
                        }
                    }
                    response_json = json.dumps(response, ensure_ascii=False)
                    logger.info("MCP: initialize | version=%s", _SERVER_VERSION)
                    yield f"data: {response_json}\n\n"

                # notifications/initialized 처리
                elif method == "notifications/initialized":
                    logger.debug("MCP: notifications/initialized")
                    return

                # tools/list 처리
                elif method == "tools/list":
                    tools_list = [
                        {
                            "name": "legal_qa_tool",
                            "priority": 1,
                            "category": "integrated",
                            "description": """법률 질문에 대한 법적 근거의 실마리를 제공합니다. 법령, 판례, 행정해석, 위원회 결정례 등을 통합 검색합니다.
통합 법률 검색·근거 실마리의 기본 진입점입니다. 출처가 한정된 검색(판례만, 해석만, 심판만 등)은 해당 전용 툴을 우선 검토하세요.

답변 형식 (A 타입, 반드시 준수):
1) 한 줄 방향 제시 (예: 문제가 될 가능성이 있는 사안입니다)
2) 체크리스트 3개 이하 (판단 포인트)
3) 관련 법령/판례 방향만 언급 (조문 전체 인용 금지)
4) 판단 유보 문장 (본 답변은 법적 판단을 대신하지 않으며...)
5) 추가 정보 요청

금지: 이모지, 타이틀(법률 상담 결과 등), 조문 전체 인용, 단정적 결론, API 링크 노출""",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "사용자의 법률 질문 (예: '프리랜서 근로자성 판례', '최근 5년 부당해고 판례', '개인정보보호법 해석')"
                                    },
                                    "max_results_per_type": {
                                        "type": "integer",
                                        "description": "타입당 최대 결과 수",
                                        "default": 3,
                                        "minimum": 1,
                                        "maximum": 10
                                    }
                                },
                                "required": ["query"]
                            },
                            "outputSchema": {
                                "type": "object",
                                "properties": {
                                    "success": {"type": "boolean"},
                                    "success_transport": {"type": "boolean"},
                                    "success_search": {"type": "boolean"},
                                    "has_legal_basis": {"type": "boolean"},
                                    "query": {"type": "string"},
                                    "domain": {"type": "string"},
                                    "detected_intent": {"type": "string"},
                                    "results": {"type": "object"},
                                    "sources_count": {"type": "object"},
                                    "total_sources": {"type": "integer"},
                                    "missing_reason": {"type": ["string", "null"]},
                                    "elapsed_seconds": {"type": "number"},
                                    "pipeline_version": {"type": "string"}
                                }
                            }
                        },
                        {
                            "name": "document_issue_tool",
                            "priority": 1,
                            "category": "document",
                            "description": DOCUMENT_ISSUE_TOOL_DESCRIPTION_TEXT,
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "document_text": {
                                        "type": "string",
                                        "description": "계약서/약관 등 문서 텍스트"
                                    },
                                    "auto_search": {
                                        "type": "boolean",
                                        "description": "조항별 추천 검색어로 자동 검색 수행 여부",
                                        "default": True
                                    },
                                    "max_clauses": {
                                        "type": "integer",
                                        "description": "자동 검색할 조항 수 제한",
                                        "default": 3,
                                        "minimum": 1,
                                        "maximum": 10
                                    },
                                    "max_results_per_type": {
                                        "type": "integer",
                                        "description": "타입당 최대 결과 수",
                                        "default": 3,
                                        "minimum": 1,
                                        "maximum": 10
                                    }
                                },
                                "required": ["document_text"]
                            },
                            "outputSchema": {
                                "type": "object",
                                "properties": {
                                    "success": {"type": "boolean"},
                                    "success_transport": {"type": "boolean"},
                                    "success_search": {"type": "boolean"},
                                    "auto_search": {"type": "boolean"},
                                    "analysis_success": {"type": "boolean"},
                                    "has_legal_basis": {"type": "boolean"},
                                    "document_analysis": {"type": "object"},
                                    "evidence_results": {"type": "array"},
                                    "missing_reason": {"type": ["string", "null"]},
                                    "legal_basis_block": {"type": "object"}
                                }
                            }
                        },
                        {
                            "name": "law_article_tool",
                            "priority": 1,
                            "category": "law",
                            "description": """특정 법령의 조문을 직접 정밀 조회합니다. 법령명과 조문번호를 알고 있을 때 사용하세요.
법령 신구·연혁·3단 비교가 필요하면 law_comparison_tool을 사용하세요.

답변 형식 (A 타입, 반드시 준수):
1) 조문 내용 요약 (인용 최소화)
2) 실무적 의미 한 줄 설명
3) 판단 유보 문장 (본 답변은 법적 판단을 대신하지 않으며...)

금지: 이모지, 조문 전체 인용, 단정적 결론""",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "law_name": {
                                        "type": "string",
                                        "description": "법령명 (예: 근로기준법, 민법, 형법, 개인정보보호법)"
                                    },
                                    "article_number": {
                                        "type": "string",
                                        "description": "조문 번호 (예: '50', '2', '110'). 생략 시 법령 전체 개요 반환"
                                    },
                                    "hang": {
                                        "type": "string",
                                        "description": "항 번호 (예: '1', '2')"
                                    },
                                    "ho": {
                                        "type": "string",
                                        "description": "호 번호 (예: '1', '2')"
                                    },
                                    "mok": {
                                        "type": "string",
                                        "description": "목 번호 (예: '가', '나')"
                                    }
                                },
                                "required": ["law_name"]
                            },
                            "outputSchema": {
                                "type": "object",
                                "properties": {
                                    "success": {"type": "boolean"},
                                    "law_name": {"type": "string"},
                                    "article_number": {"type": ["string", "null"]},
                                    "law_id": {"type": ["string", "null"]},
                                    "detail": {"type": ["object", "null"]},
                                    "error": {"type": ["string", "null"]}
                                }
                            }
                        },
                        {
                            "name": "law_comparison_tool",
                            "priority": 1,
                            "category": "law",
                            "description": """국가법령정보센터 API 기준으로 법령 신구·연혁·3단 비교 결과를 조회합니다. 비교·연혁 조회가 목적일 때 사용하세요. 일반 법률 질문·판례 검색은 legal_qa_tool 또는 전용 툴을 쓰세요.

판단 유보: 본 도구는 조회 결과만 제공하며 법적 판단을 대신하지 않습니다.

금지: 이모지, 단정적 결론, API 링크 노출""",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "law_name": {
                                        "type": "string",
                                        "description": "비교할 법령명 (예: 형법, 민법, 근로기준법)",
                                    },
                                    "compare_type": {
                                        "type": "string",
                                        "description": "비교 유형: 신구법(신·구법 대비), 연혁(법령 연혁), 3단비교",
                                        "enum": ["신구법", "연혁", "3단비교"],
                                        "default": "신구법",
                                    },
                                },
                                "required": ["law_name"],
                            },
                            "outputSchema": {
                                "type": "object",
                                "properties": {
                                    "law_name": {"type": "string"},
                                    "law_id": {"type": ["string", "null"]},
                                    "compare_type": {"type": "string"},
                                    "comparison": {"type": "object"},
                                    "error": {"type": ["string", "null"]},
                                    "error_code": {"type": ["string", "null"]},
                                    "recovery_guide": {"type": ["string", "null"]},
                                },
                            },
                        },
                        {
                            "name": "precedent_lookup_tool",
                            "priority": 1,
                            "category": "precedent",
                            "description": """판례만 검색합니다. 사건번호가 있으면 case_number, 없으면 keyword로 검색하세요. 통합 legal_qa_tool보다 판례에 집중할 때 사용합니다.

판단 유보: 본 도구는 검색 결과만 제공하며 법적 판단을 대신하지 않습니다. 추가 사실관계 확인을 요청하세요.

금지: 이모지, 조문 전체 인용, 단정적 결론, API 링크 노출""",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "keyword": {
                                        "type": "string",
                                        "description": "판례 검색 키워드 (사건번호가 없을 때)"
                                    },
                                    "case_number": {
                                        "type": "string",
                                        "description": "사건번호 (예: 2023다12345, 2021도4321). 있으면 우선 사용"
                                    },
                                    "page": {"type": "integer", "default": 1, "minimum": 1},
                                    "per_page": {
                                        "type": "integer",
                                        "default": 10,
                                        "minimum": 1,
                                        "maximum": 50,
                                        "description": "페이지당 건수"
                                    },
                                    "court": {
                                        "type": "string",
                                        "description": "법원 필터(코드). 생략 시 전체"
                                    },
                                    "date_from": {"type": "string", "description": "선고일 시작 YYYYMMDD"},
                                    "date_to": {"type": "string", "description": "선고일 종료 YYYYMMDD"}
                                },
                                "allOf": [
                                    {
                                        "anyOf": [
                                            {"required": ["keyword"]},
                                            {"required": ["case_number"]}
                                        ]
                                    }
                                ]
                            },
                            "outputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string"},
                                    "total": {"type": "integer"},
                                    "precedents": {"type": "array"},
                                    "error": {"type": "string"},
                                    "error_code": {"type": "string"}
                                }
                            }
                        },
                        {
                            "name": "interpretation_tool",
                            "priority": 1,
                            "category": "interpretation",
                            "description": """법령해석(행정기관 해석례 등)만 검색합니다. 해석·유권해석 실마리가 필요할 때 legal_qa_tool 대신 사용합니다.

판단 유보: 본 도구는 검색 결과만 제공하며 법적 판단을 대신하지 않습니다.

금지: 이모지, 단정적 결론, API 링크 노출""",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "법령해석 검색어"
                                    },
                                    "page": {"type": "integer", "default": 1, "minimum": 1},
                                    "per_page": {
                                        "type": "integer",
                                        "default": 10,
                                        "minimum": 1,
                                        "maximum": 50
                                    },
                                    "agency": {
                                        "type": "string",
                                        "description": "부처명 필터 (예: 고용노동부, 국세청). 지원되는 명칭만 적용"
                                    }
                                },
                                "required": ["query"]
                            },
                            "outputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string"},
                                    "total": {"type": "integer"},
                                    "interpretations": {"type": "array"},
                                    "error": {"type": "string"},
                                    "error_code": {"type": "string"}
                                }
                            }
                        },
                        {
                            "name": "administrative_appeal_tool",
                            "priority": 1,
                            "category": "administrative_appeal",
                            "description": """행정심판 재결만 검색합니다. 행정심판·재결례 실마리가 필요할 때 legal_qa_tool 대신 사용합니다.

판단 유보: 본 도구는 검색 결과만 제공하며 법적 판단을 대신하지 않습니다.

금지: 이모지, 단정적 결론, API 링크 노출""",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "행정심판 재결 검색어"
                                    },
                                    "page": {"type": "integer", "default": 1, "minimum": 1},
                                    "per_page": {
                                        "type": "integer",
                                        "default": 10,
                                        "minimum": 1,
                                        "maximum": 50
                                    },
                                    "date_from": {"type": "string", "description": "재결일 시작 YYYYMMDD"},
                                    "date_to": {"type": "string", "description": "재결일 종료 YYYYMMDD"}
                                },
                                "required": ["query"]
                            },
                            "outputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string"},
                                    "total": {"type": "integer"},
                                    "appeals": {"type": "array"},
                                    "error": {"type": "string"},
                                    "error_code": {"type": "string"}
                                }
                            }
                        },
                        {
                            "name": "constitutional_decision_tool",
                            "priority": 1,
                            "category": "constitutional",
                            "description": """헌법재판소 결정만 검색합니다. 위헌·헌법소원 등 헌재 실마리가 필요할 때 legal_qa_tool 대신 사용합니다.

판단 유보: 본 도구는 검색 결과만 제공하며 법적 판단을 대신하지 않습니다.

금지: 이모지, 단정적 결론, API 링크 노출""",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string", "description": "헌재결정 검색어"},
                                    "page": {"type": "integer", "default": 1, "minimum": 1},
                                    "per_page": {
                                        "type": "integer",
                                        "default": 10,
                                        "minimum": 1,
                                        "maximum": 50,
                                    },
                                    "date_from": {"type": "string", "description": "YYYYMMDD"},
                                    "date_to": {"type": "string", "description": "YYYYMMDD"},
                                },
                                "required": ["query"],
                            },
                            "outputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string"},
                                    "total": {"type": "integer"},
                                    "decisions": {"type": "array"},
                                    "error": {"type": "string"},
                                    "error_code": {"type": "string"},
                                },
                            },
                        },
                        {
                            "name": "committee_decision_tool",
                            "priority": 1,
                            "category": "committee",
                            "description": """독립위원회 등 결정문만 검색합니다. committee_type은 API가 지원하는 정확한 명칭이어야 합니다 (예: 개인정보보호위원회, 금융위원회, 노동위원회 등).

판단 유보: 본 도구는 검색 결과만 제공하며 법적 판단을 대신하지 않습니다.

금지: 이모지, 단정적 결론, API 링크 노출""",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "committee_type": {
                                        "type": "string",
                                        "description": "위원회 명칭 (저장소 COMMITTEE_TARGET_MAP 키와 일치)",
                                    },
                                    "query": {"type": "string", "description": "결정문 검색어"},
                                    "page": {"type": "integer", "default": 1, "minimum": 1},
                                    "per_page": {
                                        "type": "integer",
                                        "default": 10,
                                        "minimum": 1,
                                        "maximum": 50,
                                    },
                                },
                                "required": ["committee_type", "query"],
                            },
                            "outputSchema": {
                                "type": "object",
                                "properties": {
                                    "total": {"type": "integer"},
                                    "decisions": {"type": "array"},
                                    "error": {"type": "string"},
                                    "error_code": {"type": "string"},
                                },
                            },
                        },
                        {
                            "name": "special_administrative_appeal_tool",
                            "priority": 1,
                            "category": "special_appeal",
                            "description": """특별행정심판원 재결만 검색합니다. tribunal_type은 조세심판원·해양안전심판원 등 저장소가 지원하는 정확한 명칭이어야 합니다.

판단 유보: 본 도구는 검색 결과만 제공하며 법적 판단을 대신하지 않습니다.

금지: 이모지, 단정적 결론, API 링크 노출""",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "tribunal_type": {
                                        "type": "string",
                                        "description": "심판원 명칭 (TRIBUNAL_TARGET_MAP 키와 일치)",
                                    },
                                    "query": {"type": "string", "description": "재결 검색어"},
                                    "page": {"type": "integer", "default": 1, "minimum": 1},
                                    "per_page": {
                                        "type": "integer",
                                        "default": 10,
                                        "minimum": 1,
                                        "maximum": 50,
                                    },
                                },
                                "required": ["tribunal_type", "query"],
                            },
                            "outputSchema": {
                                "type": "object",
                                "properties": {
                                    "total": {"type": "integer"},
                                    "appeals": {"type": "array"},
                                    "error": {"type": "string"},
                                    "error_code": {"type": "string"},
                                },
                            },
                        },
                        {
                            "name": "local_ordinance_tool",
                            "priority": 1,
                            "category": "ordinance",
                            "description": """자치법규(조례 등)만 검색합니다. 지역 조례·규칙 실마리가 필요할 때 legal_qa_tool 대신 사용할 수 있습니다. query와 local_government 중 하나 이상을 넣으세요.

판단 유보: 본 도구는 검색 결과만 제공하며 법적 판단을 대신하지 않습니다.

금지: 이모지, 단정적 결론, API 링크 노출""",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "조례명 또는 검색 키워드",
                                    },
                                    "local_government": {
                                        "type": "string",
                                        "description": "지방자치단체 명칭 필터 (예: 서울시, 부산시)",
                                    },
                                    "page": {"type": "integer", "default": 1, "minimum": 1},
                                    "per_page": {
                                        "type": "integer",
                                        "default": 20,
                                        "minimum": 1,
                                        "maximum": 50,
                                    },
                                },
                                "allOf": [
                                    {
                                        "anyOf": [
                                            {"required": ["query"]},
                                            {"required": ["local_government"]},
                                        ]
                                    }
                                ],
                            },
                            "outputSchema": {
                                "type": "object",
                                "properties": {
                                    "total": {"type": "integer"},
                                    "ordinances": {"type": "array"},
                                    "error": {"type": ["string", "null"]},
                                    "error_code": {"type": ["string", "null"]},
                                },
                            },
                        },
                        {
                            "name": "administrative_rule_tool",
                            "priority": 1,
                            "category": "admin_rule",
                            "description": """행정규칙만 검색합니다. 부처 훈령·예규 등 실마리가 필요할 때 legal_qa_tool 대신 사용할 수 있습니다. query와 agency 중 하나 이상을 넣으세요.

판단 유보: 본 도구는 검색 결과만 제공하며 법적 판단을 대신하지 않습니다.

금지: 이모지, 단정적 결론, API 링크 노출""",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "행정규칙명 또는 검색 키워드",
                                    },
                                    "agency": {
                                        "type": "string",
                                        "description": "부처명 (예: 고용노동부, 교육부). 저장소 매핑에 있는 명칭만 기관 필터로 적용될 수 있습니다.",
                                    },
                                    "page": {"type": "integer", "default": 1, "minimum": 1},
                                    "per_page": {
                                        "type": "integer",
                                        "default": 20,
                                        "minimum": 1,
                                        "maximum": 50,
                                    },
                                },
                                "allOf": [
                                    {
                                        "anyOf": [
                                            {"required": ["query"]},
                                            {"required": ["agency"]},
                                        ]
                                    }
                                ],
                            },
                            "outputSchema": {
                                "type": "object",
                                "properties": {
                                    "total": {"type": "integer"},
                                    "rules": {"type": "array"},
                                    "error": {"type": ["string", "null"]},
                                    "error_code": {"type": ["string", "null"]},
                                },
                            },
                        },
                        {
                            "name": "health",
                            "priority": 2,
                            "category": "utility",
                            "description": "서비스 상태를 확인합니다. API 키 설정 상태, 환경 변수, 서버 상태 등을 확인할 때 사용합니다. 예: '서버 상태 확인', 'API 키 설정 확인'.",
                            "inputSchema": {
                                "type": "object",
                                "additionalProperties": False
                            },
                            "outputSchema": {
                                "type": "object",
                                "properties": {
                                    "success": {"type": "boolean"},
                                    "status": {"type": "string"},
                                    "environment": {"type": "object"},
                                    "message": {"type": "string"},
                                    "server": {"type": "string"},
                                    "api_ready": {"type": "boolean"},
                                    "api_status": {"type": "string"}
                                }
                            }
                        }
                    ]

                    # MCP 표준 필드만 노출
                    mcp_tools = []
                    for tool in tools_list:
                        annotations = {}
                        if "priority" in tool:
                            annotations["priority"] = tool.get("priority")
                        if "category" in tool:
                            annotations["category"] = tool.get("category")
                        filtered = {
                            "name": tool.get("name"),
                            "description": tool.get("description"),
                            "inputSchema": tool.get("inputSchema"),
                            "outputSchema": tool.get("outputSchema")
                        }
                        filtered = {k: v for k, v in filtered.items() if v is not None}
                        if annotations:
                            filtered["annotations"] = annotations
                        mcp_tools.append(filtered)

                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "tools": mcp_tools
                        }
                    }
                    response_json = json.dumps(response, ensure_ascii=False)
                    logger.info("MCP: tools/list response | length=%d tools_count=%d",
                               len(response_json),
                               len(mcp_tools))
                    yield f"data: {response_json}\n\n"

                # resources/list 처리
                elif method == "resources/list":
                    resources_data = build_resources_list()
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": resources_data,
                    }
                    response_json = json.dumps(response, ensure_ascii=False)
                    logger.info(
                        "MCP: resources/list | resources=%d templates=%d",
                        len(resources_data.get("resources", [])),
                        len(resources_data.get("resourceTemplates", [])),
                    )
                    yield f"data: {response_json}\n\n"

                # resources/read 처리
                elif method == "resources/read":
                    uri = params.get("uri", "")
                    logger.info("MCP: resources/read | uri=%s", uri)
                    try:
                        resource_result = await read_resource(
                            uri,
                            _law_detail_repo,
                            _precedent_repo,
                            _interpretation_repo,
                        )
                        if resource_result.get("error"):
                            error_response = {
                                "jsonrpc": "2.0",
                                "id": request_id,
                                "error": {
                                    "code": -32602,
                                    "message": resource_result["error"],
                                },
                            }
                            yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"
                        else:
                            response = {
                                "jsonrpc": "2.0",
                                "id": request_id,
                                "result": resource_result,
                            }
                            yield f"data: {json.dumps(response, ensure_ascii=False)}\n\n"
                    except Exception as e:
                        logger.error("resources/read error | uri=%s error=%s", uri, e, exc_info=True)
                        error_response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {"code": -32603, "message": f"리소스 조회 오류: {e}"},
                        }
                        yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"

                # prompts/list 처리
                elif method == "prompts/list":
                    prompts_list = _build_prompts_list()
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "prompts": prompts_list
                        }
                    }
                    response_json = json.dumps(response, ensure_ascii=False)
                    logger.info("MCP: prompts/list response | count=%d", len(prompts_list))
                    yield f"data: {response_json}\n\n"

                # prompts/get 처리
                elif method == "prompts/get":
                    prompt_name = params.get("name")
                    arguments_in = params.get("arguments", {})
                    prompt_result = _get_prompt(prompt_name, arguments_in)
                    if prompt_result is None:
                        error_response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": -32602,
                                "message": f"Prompt not found: {prompt_name}"
                            }
                        }
                        yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"
                    else:
                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": prompt_result
                        }
                        response_json = json.dumps(response, ensure_ascii=False)
                        logger.info("MCP: prompts/get response | name=%s", prompt_name)
                        yield f"data: {response_json}\n\n"

                # tools/call 처리
                elif method == "tools/call":
                    tool_name = params.get("name")
                    arguments = params.get("arguments", {})

                    logger.info("MCP tool call | tool=%s arguments=%s", tool_name, arguments)

                    result = None
                    try:
                        if tool_name == "health":
                            result = await health_service.check_health()

                        elif tool_name == "legal_qa_tool":
                            query = arguments.get("query")
                            max_results = arguments.get("max_results_per_type", 3)
                            logger.debug("Calling comprehensive_search_v2 | query=%s max_results=%d",
                                       query, max_results)
                            result = await smart_search_service.comprehensive_search_v2(
                                query,
                                max_results
                            )

                        elif tool_name == "document_issue_tool":
                            document_text = arguments.get("document_text")
                            _raw_auto = arguments.get("auto_search", True)
                            if _raw_auto is True or _raw_auto is False:
                                auto_search = _raw_auto
                            elif isinstance(_raw_auto, str):
                                auto_search = _raw_auto.strip().lower() in (
                                    "true", "1", "yes",
                                )
                            else:
                                auto_search = bool(_raw_auto)
                            max_clauses = int(arguments.get("max_clauses", 3))
                            max_results = int(arguments.get("max_results_per_type", 3))
                            logger.debug("Calling document_issue_tool | doc_len=%d auto_search=%s max_clauses=%d max_results=%d",
                                       len(document_text) if document_text else 0,
                                       auto_search, max_clauses, max_results)
                            result = await situation_guidance_service.document_issue_analysis(
                                document_text,
                                arguments=arguments,
                                auto_search=auto_search,
                                max_clauses=max_clauses,
                                max_results_per_type=max_results,
                            )

                        elif tool_name == "law_article_tool":
                            law_name = arguments.get("law_name")
                            article_number = arguments.get("article_number")
                            hang = arguments.get("hang")
                            ho = arguments.get("ho")
                            mok = arguments.get("mok")
                            mode = "single" if article_number else "detail"
                            logger.debug(
                                "Calling law_article_tool | law=%s article=%s hang=%s ho=%s mok=%s",
                                law_name, article_number, hang, ho, mok,
                            )
                            result = await _law_detail_repo.get_law(
                                None,
                                law_name,
                                mode,
                                article_number,
                                hang,
                                ho,
                                mok,
                                arguments,
                            )

                        elif tool_name == "law_comparison_tool":
                            req_cmp, err_cmp = resolve_law_comparison_tool(arguments)
                            if err_cmp:
                                result = err_cmp
                            else:
                                result = await law_comparison_service.compare_laws(req_cmp, arguments)

                        elif tool_name == "precedent_lookup_tool":
                            result = await smart_search_service.precedent_lookup(
                                keyword=arguments.get("keyword"),
                                case_number=arguments.get("case_number"),
                                page=int(arguments.get("page", 1)),
                                per_page=int(arguments.get("per_page", 10)),
                                court=arguments.get("court"),
                                date_from=arguments.get("date_from"),
                                date_to=arguments.get("date_to"),
                                arguments=arguments,
                            )

                        elif tool_name == "interpretation_tool":
                            result = await smart_search_service.interpretation_lookup(
                                query=arguments.get("query", ""),
                                page=int(arguments.get("page", 1)),
                                per_page=int(arguments.get("per_page", 10)),
                                agency=arguments.get("agency"),
                                arguments=arguments,
                            )

                        elif tool_name == "administrative_appeal_tool":
                            result = await smart_search_service.administrative_appeal_lookup(
                                query=arguments.get("query", ""),
                                page=int(arguments.get("page", 1)),
                                per_page=int(arguments.get("per_page", 10)),
                                date_from=arguments.get("date_from"),
                                date_to=arguments.get("date_to"),
                                arguments=arguments,
                            )

                        elif tool_name == "constitutional_decision_tool":
                            result = await smart_search_service.constitutional_decision_lookup(
                                query=arguments.get("query", ""),
                                page=int(arguments.get("page", 1)),
                                per_page=int(arguments.get("per_page", 10)),
                                date_from=arguments.get("date_from"),
                                date_to=arguments.get("date_to"),
                                arguments=arguments,
                            )

                        elif tool_name == "committee_decision_tool":
                            result = await smart_search_service.committee_decision_lookup(
                                committee_type=arguments.get("committee_type", ""),
                                query=arguments.get("query", ""),
                                page=int(arguments.get("page", 1)),
                                per_page=int(arguments.get("per_page", 10)),
                                arguments=arguments,
                            )

                        elif tool_name == "special_administrative_appeal_tool":
                            result = await smart_search_service.special_administrative_appeal_lookup(
                                tribunal_type=arguments.get("tribunal_type", ""),
                                query=arguments.get("query", ""),
                                page=int(arguments.get("page", 1)),
                                per_page=int(arguments.get("per_page", 10)),
                                arguments=arguments,
                            )

                        elif tool_name == "local_ordinance_tool":
                            _pp_lo = int(arguments.get("per_page", 20))
                            _pp_lo = max(1, min(50, _pp_lo))
                            result = await smart_search_service.local_ordinance_lookup(
                                query=arguments.get("query"),
                                local_government=arguments.get("local_government"),
                                page=int(arguments.get("page", 1)),
                                per_page=_pp_lo,
                                arguments=arguments,
                            )

                        elif tool_name == "administrative_rule_tool":
                            _pp_ar = int(arguments.get("per_page", 20))
                            _pp_ar = max(1, min(50, _pp_ar))
                            result = await smart_search_service.administrative_rule_lookup(
                                query=arguments.get("query"),
                                agency=arguments.get("agency"),
                                page=int(arguments.get("page", 1)),
                                per_page=_pp_ar,
                                arguments=arguments,
                            )

                        else:
                            result = {"error": f"Unknown tool: {tool_name}"}

                    except Exception as e:
                        logger.error("Tool call error | tool=%s error=%s", tool_name, str(e), exc_info=True)
                        result = {"error": str(e)}

                    # Response 생성 및 전송
                    if result:
                        # JSON 직렬화를 위해 데이터 정리
                        def clean_for_json(obj):
                            if isinstance(obj, dict):
                                return {k: clean_for_json(v) for k, v in obj.items()}
                            elif isinstance(obj, list):
                                return [clean_for_json(item) for item in obj]
                            elif isinstance(obj, str):
                                return "".join(ch for ch in obj if ord(ch) not in range(0x00, 0x09) and ord(ch) not in range(0x0B, 0x0D) and ord(ch) not in range(0x0E, 0x20))
                            else:
                                return obj

                        cleaned_result = clean_for_json(result)
                        from ..utils.response_formatter import format_mcp_response, sanitize_for_mcp_json

                        cleaned_result = sanitize_for_mcp_json(cleaned_result)
                        final_result = copy.deepcopy(cleaned_result)
                        final_result = shrink_response_bytes(final_result)

                        # MCP 표준 형식으로 변환
                        mcp_formatted = format_mcp_response(final_result, tool_name)

                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": mcp_formatted
                        }
                        response_json = json.dumps(response, ensure_ascii=False)
                        logger.info("MCP: Sending final response | tool=%s has_error=%s result_size=%d",
                                   tool_name, "error" in final_result, len(json.dumps(final_result, ensure_ascii=False)))
                        logger.info("MCP: Response JSON length=%d (first 300 chars): %s",
                                   len(response_json), response_json[:300])
                        logger.info("MCP: Yielding SSE event | length=%d", len(response_json))
                        yield f"data: {response_json}\n\n"
                    else:
                        error_response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": -32603,
                                "message": "Tool returned no result"
                            }
                        }
                        yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"

                else:
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Unknown method: {method}"
                        }
                    }
                    yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"

            except json.JSONDecodeError as e:
                logger.error("Invalid JSON in request body: %s", e, exc_info=True)
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": "Parse error: Invalid JSON"
                    }
                }
                yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"
            except Exception as e:
                logger.error("MCP request processing error: %s", e, exc_info=True)
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request_id if 'request_id' in locals() else None,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }
                yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"

        logger.info("MCP POST RESPONSE (SSE)")
        logger.info("  Status: 200")
        logger.info("  Content-Type: text/event-stream")
        logger.info("=" * 80)

        return StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )


# ---------------------------------------------------------------------------
# MCP Prompts 데이터 정의
# ---------------------------------------------------------------------------

_PROMPTS = [
    {
        "name": "legal_basis_answer",
        "description": "법률 질문에 대해 관련 법령 조문 번호와 판례 요지를 반드시 포함한 답변을 생성합니다.",
        "arguments": [
            {
                "name": "question",
                "description": "법률 질문 (예: 프리랜서 근로자성 인정 요건은?)",
                "required": True
            }
        ]
    },
    {
        "name": "precedent_summary",
        "description": "관련 판례를 사실관계 / 쟁점 / 판단요지 3단계로 나눠 요약합니다.",
        "arguments": [
            {
                "name": "topic",
                "description": "판례 주제 (예: 부당해고, 손해배상, 개인정보유출)",
                "required": True
            },
            {
                "name": "court",
                "description": "법원 (예: 대법원, 헌법재판소). 생략 시 전체 검색",
                "required": False
            }
        ]
    },
    {
        "name": "contract_risk_check",
        "description": "계약서나 약관 텍스트에서 법적으로 문제될 수 있는 조항을 항목별로 정리합니다.",
        "arguments": [
            {
                "name": "contract_text",
                "description": "분석할 계약서 또는 약관 전문",
                "required": True
            },
            {
                "name": "contract_type",
                "description": "계약서 유형 (예: 프리랜서 계약서, 임대차 계약서, 이용약관). 생략 시 자동 감지",
                "required": False
            }
        ]
    },
    {
        "name": "labor_contract_review",
        "description": "근로계약서·용역 계약서를 조항별로 조문·위험도·수정방향까지 포함해 검토합니다(document_issue_tool B 타입과 동일 구조).",
        "arguments": [
            {
                "name": "contract_text",
                "description": "근로·용역 계약서 전문",
                "required": True
            }
        ]
    },
    {
        "name": "legal_qa",
        "description": "일상적인 법률 상황을 설명하면 관련 법령·판례·행정해석을 찾아 실마리를 제공합니다.",
        "arguments": [
            {
                "name": "situation",
                "description": "법률적 도움이 필요한 상황 설명 (예: 퇴직 후 퇴직금을 받지 못했습니다)",
                "required": True
            },
            {
                "name": "domain",
                "description": "법률 도메인 (노동/부동산/개인정보/소비자/세금/금융/의료/환경). 생략 시 자동 감지",
                "required": False
            }
        ]
    }
]

_PROMPT_MESSAGES = {
    "legal_basis_answer": lambda args: {
        "description": "법령 근거 포함 답변 프롬프트",
        "messages": [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": (
                        f"다음 질문에 대해 반드시 관련 법령 조문 번호와 판례 요지를 함께 알려주세요.\n\n"
                        f"질문: {args.get('question', '')}\n\n"
                        "답변 형식:\n"
                        "1) 핵심 방향 한 줄\n"
                        "2) 관련 법령 조문 번호 (예: 근로기준법 제23조 제1항)\n"
                        "3) 관련 판례 요지 (사건번호 + 핵심 판시 내용)\n"
                        "4) 판단 유보 문장\n\n"
                        "본 답변은 법적 판단을 대신하지 않습니다."
                    )
                }
            }
        ]
    },
    "precedent_summary": lambda args: {
        "description": "판례 요약형 프롬프트",
        "messages": [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": (
                        f"'{args.get('topic', '')}' 관련 판례를 아래 형식으로 요약해주세요.\n"
                        + (f"(대상 법원: {args['court']})\n" if args.get("court") else "")
                        + "\n"
                        "## 사실관계\n[당사자 관계와 핵심 사실]\n\n"
                        "## 쟁점\n[법적 판단이 필요한 핵심 쟁점]\n\n"
                        "## 판단요지\n[법원의 핵심 판시 내용]\n\n"
                        "본 요약은 법적 자문을 대신하지 않습니다."
                    )
                }
            }
        ]
    },
    "contract_risk_check": lambda args: {
        "description": "범용 계약서 위험조항 점검 프롬프트 (임대차·약관·일반 계약 등; 노동 전용 규칙 없음)",
        "messages": [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": (
                        (f"계약서 유형(참고): {args['contract_type']}\n\n" if args.get("contract_type") else "")
                        + "근로계약·용역·노동 문서 전용 검토는 labor_contract_review 또는 document_issue_tool(근로 분류)을 사용하세요.\n\n"
                        + GENERIC_DOCUMENT_REVIEW_INSTRUCTION
                        + "\n\n--- 계약서 전문 ---\n"
                        + f"{args.get('contract_text', '(계약서 텍스트를 붙여넣어 주세요)')}\n"
                        + "---\n"
                    )
                }
            }
        ]
    },
    "labor_contract_review": lambda args: {
        "description": "근로계약서 고밀도 검토 프롬프트(document_issue_tool B 타입과 정합)",
        "messages": [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": (
                        LABOR_CONTRACT_REVIEW_INSTRUCTION
                        + "\n\n--- 계약서 전문 ---\n"
                        + f"{args.get('contract_text', '')}\n"
                        + "---\n"
                    )
                }
            }
        ]
    },
    "legal_qa": lambda args: {
        "description": "범용 법률 QA 프롬프트",
        "messages": [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": (
                        "다음 상황에 대한 법률적 실마리를 제공해주세요.\n\n"
                        f"상황: {args.get('situation', '')}\n"
                        + (f"법률 도메인: {args['domain']}\n" if args.get("domain") else "")
                        + "\n"
                        "요청 사항:\n"
                        "1) 관련 법령과 조문 방향\n"
                        "2) 유사 판례나 행정해석 방향\n"
                        "3) 실질적으로 확인해야 할 체크포인트 3개 이하\n"
                        "4) 추가로 필요한 정보 요청\n\n"
                        "본 답변은 법적 자문을 대신하지 않으며, 구체적인 사실관계에 따라 결론이 달라질 수 있습니다."
                    )
                }
            }
        ]
    }
}


def _build_prompts_list() -> list:
    """MCP prompts/list 응답용 프롬프트 목록 반환"""
    return [
        {
            "name": p["name"],
            "description": p["description"],
            "arguments": p.get("arguments", [])
        }
        for p in _PROMPTS
    ]


def _get_prompt(name: str, arguments: dict) -> dict | None:
    """MCP prompts/get 응답 반환. 존재하지 않으면 None"""
    if name not in _PROMPT_MESSAGES:
        return None
    builder = _PROMPT_MESSAGES[name]
    return builder(arguments or {})

