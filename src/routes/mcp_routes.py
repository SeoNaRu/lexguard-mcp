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
    GENERIC_DOCUMENT_REVIEW_INSTRUCTION,
    LABOR_CONTRACT_REVIEW_INSTRUCTION,
)
from .tool_schemas import TOOLS_LIST
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
                    tools_list = TOOLS_LIST
                    # ↑ 스키마 정의는 src/routes/tool_schemas.py 에서 관리

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

                    _services = {
                        "health": health_service,
                        "smart_search": smart_search_service,
                        "situation_guidance": situation_guidance_service,
                        "law_comparison": law_comparison_service,
                        "law_detail_repo": _law_detail_repo,
                    }

                    result = None
                    try:
                        from .tool_handlers import dispatch
                        result = await dispatch(tool_name, arguments, _services)

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

