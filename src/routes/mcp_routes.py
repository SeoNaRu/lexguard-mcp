"""
MCP Routes - MCP Streamable HTTP 엔드포인트
Controller 패턴: 요청을 받아 Service를 호출
"""
import json
import asyncio
import re
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from ..services.law_service import LawService
from ..services.health_service import HealthService
from ..services.generic_api_service import GenericAPIService
from ..services.precedent_service import PrecedentService
from ..services.law_interpretation_service import LawInterpretationService
from ..services.administrative_appeal_service import AdministrativeAppealService
from ..services.committee_decision_service import CommitteeDecisionService
from ..services.constitutional_decision_service import ConstitutionalDecisionService
from ..services.special_administrative_appeal_service import SpecialAdministrativeAppealService
from ..services.law_comparison_service import LawComparisonService
from ..services.local_ordinance_service import LocalOrdinanceService
from ..services.administrative_rule_service import AdministrativeRuleService
from ..services.smart_search_service import SmartSearchService
from ..services.situation_guidance_service import SituationGuidanceService
from ..tools.dynamic_tool_generator import get_tool_generator
from ..utils.response_truncator import truncate_response, get_response_size, shrink_response_bytes
from ..utils.response_formatter import format_mcp_response
from ..models import (
    SearchLawRequest, GetLawRequest, ListLawNamesRequest, GetLawDetailRequest, GetLawArticlesRequest, GetSingleArticleRequest,
    SearchPrecedentRequest, GetPrecedentRequest,
    SearchLawInterpretationRequest, GetLawInterpretationRequest,
    SearchAdministrativeAppealRequest, GetAdministrativeAppealRequest,
    SearchCommitteeDecisionRequest, GetCommitteeDecisionRequest,
    SearchConstitutionalDecisionRequest, GetConstitutionalDecisionRequest,
    SearchSpecialAdministrativeAppealRequest, GetSpecialAdministrativeAppealRequest,
    CompareLawsRequest,
    SearchLocalOrdinanceRequest,
    SearchAdministrativeRuleRequest,
)
import logging

logger = logging.getLogger("lexguard-mcp")


def register_mcp_routes(api: FastAPI, law_service: LawService, health_service: HealthService):
    """MCP Streamable HTTP 엔드포인트 등록"""
    # 범용 API 서비스 및 툴 생성기 초기화
    generic_api_service = GenericAPIService()
    tool_generator = get_tool_generator()
    precedent_service = PrecedentService()
    law_interpretation_service = LawInterpretationService()
    administrative_appeal_service = AdministrativeAppealService()
    committee_decision_service = CommitteeDecisionService()
    constitutional_decision_service = ConstitutionalDecisionService()
    special_administrative_appeal_service = SpecialAdministrativeAppealService()
    law_comparison_service = LawComparisonService()
    local_ordinance_service = LocalOrdinanceService()
    administrative_rule_service = AdministrativeRuleService()
    smart_search_service = SmartSearchService()
    situation_guidance_service = SituationGuidanceService()
    
    # 모든 요청 로깅 미들웨어 (디버깅용) - Health Check 요청 제외
    @api.middleware("http")
    async def log_all_requests(request: Request, call_next):
        # Render Health Check 요청은 로깅하지 않음
        is_health_check = (
            request.url.path == "/health" or 
            request.headers.get("render-health-check") == "1"
        )
        
        if not is_health_check:
            # 모든 요청 로깅 (Cursor가 다른 경로로 요청하는지 확인)
            logger.info("=" * 80)
            logger.info(f"ALL REQUEST: {request.method} {request.url}")
            logger.info(f"Client: {request.client}")
            logger.info(f"Path: {request.url.path}")
            logger.info(f"Headers: {dict(request.headers)}")
        
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
        """
        MCP Streamable HTTP GET 엔드포인트
        클라이언트가 SSE 스트림을 열어서 서버에서 클라이언트로 메시지를 받을 수 있음
        """
        accept_header = request.headers.get("Accept", "")
        logger.info("=" * 80)
        logger.info("MCP GET request received")
        logger.info(f"Accept: {accept_header}")
        logger.info(f"Client: {request.client}")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info("=" * 80)
        
        # Accept 헤더가 없거나 비어있으면 기본적으로 SSE 허용 (mcp-inspector 호환성)
        # Accept 헤더에 text/event-stream이 명시적으로 없고, 다른 미디어 타입이 요청되면 405 반환
        if accept_header and "text/event-stream" not in accept_header and "*/*" not in accept_header:
            from fastapi import HTTPException
            logger.warning("MCP GET: Unsupported Accept header: %s", accept_header)
            raise HTTPException(status_code=405, detail="Method Not Allowed: SSE stream not supported")
        
        # SSE 스트림 생성 (서버에서 클라이언트로 메시지 전송용)
        async def server_to_client_stream():
            # Stateless 서버이므로 빈 스트림 반환
            # 필요시 서버에서 클라이언트로 notification을 보낼 수 있음
            yield f"data: {json.dumps({'type': 'stream_opened'})}\n\n"
            # 스트림 유지 (클라이언트가 닫을 때까지)
            try:
                while True:
                    await asyncio.sleep(1)
                    # 주기적으로 heartbeat 전송 (선택사항)
                    # yield f": heartbeat\n\n"
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
    async def mcp_streamable_http(request: Request):
        """
        MCP Streamable HTTP 엔드포인트
        JSON-RPC 2.0 메시지를 받아서 SSE로 스트리밍 응답
        """
        # 요청 헤더 상세 로깅 (Cursor 디버깅용)
        accept_header = request.headers.get("Accept", "")
        content_type_header = request.headers.get("Content-Type", "")
        session_id_header = request.headers.get("Mcp-Session-Id", "")
        origin_header = request.headers.get("Origin", "")
        logger.info("=" * 80)
        logger.info("MCP POST REQUEST RECEIVED")
        logger.info("  Method: POST")
        logger.info("  Path: /mcp")
        logger.info("  Headers:")
        logger.info("    Accept: %s", accept_header)
        logger.info("    Content-Type: %s", content_type_header)
        logger.info("    Mcp-Session-Id: %s", session_id_header or "(없음)")
        logger.info("    Origin: %s", origin_header or "(없음)")
        logger.info("=" * 80)
        
        # Accept 헤더 확인 (MCP 스펙: application/json, text/event-stream 둘 다 지원해야 함)
        if accept_header:
            has_json = "application/json" in accept_header
            has_sse = "text/event-stream" in accept_header
            if not (has_json or has_sse):
                logger.warning("MCP: Unsupported Accept header: %s", accept_header)
                # 406 Not Acceptable 반환하지 않고 계속 진행 (호환성)
        
        try:
            body = await request.json()
            def _sanitize_body(payload):
                if not isinstance(payload, dict):
                    return payload
                sanitized = json.loads(json.dumps(payload))  # shallow copy
                params = sanitized.get("params") if isinstance(sanitized, dict) else None
                if isinstance(params, dict):
                    arguments = params.get("arguments")
                    if isinstance(arguments, dict) and "document_text" in arguments:
                        text = arguments.get("document_text") or ""
                        arguments["document_text"] = f"[document_text length={len(text)}]"
                    for k, v in list(arguments.items()) if isinstance(arguments, dict) else []:
                        if isinstance(v, str) and len(v) > 200:
                            arguments[k] = v[:200] + "...[truncated]"
                return sanitized
            logger.info("MCP request body: %s", _sanitize_body(body))
            
            jsonrpc = body.get("jsonrpc", "2.0")
            method = body.get("method")
            params = body.get("params", {})
            request_id = body.get("id")
            
            if jsonrpc != "2.0":
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32600,
                        "message": "Invalid Request"
                    }
                }
                async def error_stream():
                    yield f"data: {json.dumps(error_response)}\n\n"
                return StreamingResponse(error_stream(), media_type="text/event-stream")
            
            async def process_mcp_message():
                try:
                    if method == "initialize":
                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": {
                                "protocolVersion": "2025-03-26",
                                "capabilities": {
                                    "tools": {
                                        "listChanged": False
                                    }
                                },
                                "serverInfo": {
                                    "name": "lexguard-mcp",
                                    "version": "1.0.0"
                                }
                            }
                        }
                        response_json = json.dumps(response, ensure_ascii=False)
                        logger.info("MCP: initialize response | length=%d", len(response_json))
                        logger.debug("MCP: initialize response body: %s", response_json[:500])
                        # 즉시 응답 전송 (버퍼링 방지)
                        yield f"data: {response_json}\n\n"
                        
                    elif method == "notifications/initialized":
                        # Notification은 응답이 필요 없음 (MCP 스펙)
                        # 하지만 SSE 스트림을 열었으므로 빈 이벤트를 보내고 종료
                        logger.debug("MCP: notifications/initialized received, no response needed")
                        # 빈 이벤트를 보내고 스트림 종료
                        yield f": notification received\n\n"
                        # async generator는 자동으로 종료됨
                        
                    elif method == "tools/list":
                        # 핵심 툴 목록 (페이지네이션 지원)
                        cursor_value = params.get("cursor")
                        page_size = 12
                        start_index = 0
                        if isinstance(cursor_value, str) and cursor_value.isdigit():
                            start_index = int(cursor_value)
                        tools_list = [
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
                            },
                            {
                                "name": "smart_search_tool",
                                "priority": 1,
                                "category": "integrated",
                                "description": "**통합 검색 툴 (메인 진입점, 우선 사용 권장)**: 사용자 질문을 분석하여 적절한 법적 정보를 자동으로 검색합니다. 법령, 판례, 법령해석, 행정심판, 헌재결정 등을 자동으로 찾아줍니다. LLM이 사용자 질문만 받으면 이 툴을 사용하여 모든 법적 정보를 통합 검색할 수 있습니다.\n\n**응답 구조**:\n```json\n{\n  \"success\": true,\n  \"has_legal_basis\": true,\n  \"query\": \"형법 제329조\",\n  \"detected_intents\": [\"law\"],\n  \"results\": {\n    \"law\": {\n      \"law_name\": \"형법\",\n      \"article\": {\n        \"article_number\": \"제329조\",\n        \"content\": \"...\"\n      }\n    }\n  },\n  \"sources_count\": {\"law\": 1, \"precedent\": 0},\n  \"citations\": [...],\n  \"one_line_answer\": \"형법 제329조는...\",\n  \"next_questions\": [...]\n}\n```",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "query": {
                                            "type": "string",
                                            "description": "사용자 질문 (예: '형법 제250조가 뭐야?', '손해배상 판례 찾아줘', '개인정보보호법 해석 확인')"
                                        },
                                        "search_types": {
                                            "type": "array",
                                            "items": {
                                                "type": "string",
                                                "enum": ["law", "precedent", "interpretation", "administrative_appeal", "constitutional", "committee", "special_appeal", "ordinance", "rule"]
                                            },
                                            "description": "강제로 검색할 타입 목록 (생략하면 자동 분석)"
                                        },
                                        "max_results_per_type": {
                                            "type": "integer",
                                            "description": "타입당 최대 결과 수",
                                            "default": 5,
                                            "minimum": 1,
                                            "maximum": 20
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
                                        "detected_intents": {"type": "array"},
                                        "results": {"type": "object"},
                                        "sources_count": {"type": "object"},
                                        "missing_reason": {"type": ["string", "null"]},
                                        "citations": {"type": "array"},
                                        "one_line_answer": {"type": ["string", "null"]},
                                        "next_questions": {"type": "array"},
                                        "legal_basis_block_text": {"type": ["string", "null"]},
                                        "legal_basis_block": {"type": "object"},
                                        "response_policy": {"type": "object"}
                                    }
                                }
                            },
                            {
                                "name": "situation_guidance_tool",
                                "priority": 1,
                                "category": "integrated",
                                "description": "**상황별 근거형 가이드 툴**: 사용자의 법적 상황을 분석하여 관련 법령, 판례, 해석을 찾아주고 단계별 가이드를 제공합니다. 내부적으로 smart_search_tool을 호출하여 실제 법적 근거를 포함합니다.\n\n**응답 구조**:\n```json\n{\n  \"success\": true,\n  \"has_legal_basis\": true,\n  \"situation\": \"회사에서 해고당했는데 퇴직금을 받지 못했어요\",\n  \"detected_domains\": [\"노동\"],\n  \"laws\": {...},\n  \"precedents\": {...},\n  \"interpretations\": {...},\n  \"sources_count\": {\"law\": 2, \"precedent\": 3},\n  \"guidance\": [\n    \"1. 근로기준법 제34조 확인\",\n    \"2. 퇴직금 지급 의무 확인\"\n  ],\n  \"missing_reason\": null\n}\n```",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "situation": {
                                            "type": "string",
                                            "description": "사용자의 법적 상황 설명 (예: '회사에서 해고당했는데 퇴직금을 받지 못했어요', '개인정보가 유출되었는데 어떻게 해야 하나요', '세금 부과가 부당하다고 생각합니다')"
                                        },
                                        "max_results_per_type": {
                                            "type": "integer",
                                            "description": "타입당 최대 결과 수",
                                            "default": 5,
                                            "minimum": 1,
                                            "maximum": 10
                                        }
                                    },
                                    "required": ["situation"]
                                },
                                "outputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "success": {"type": "boolean"},
                                        "success_transport": {"type": "boolean"},
                                        "success_search": {"type": "boolean"},
                                        "has_legal_basis": {"type": "boolean"},
                                        "situation": {"type": "string"},
                                        "detected_domains": {"type": "array"},
                                        "laws": {"type": "object"},
                                        "precedents": {"type": "object"},
                                        "interpretations": {"type": "object"},
                                        "sources_count": {"type": "object"},
                                        "missing_reason": {"type": ["string", "null"]},
                                        "legal_basis_block_text": {"type": ["string", "null"]},
                                        "legal_basis_block": {"type": "object"},
                                        "guidance": {"type": ["object", "array"]},
                                        "document_analysis": {"type": ["object", "null"]},
                                        "answer": {"type": ["object", "null"]}
                                    }
                                }
                            },
                            {
                                "name": "document_issue_tool",
                                "priority": 1,
                                "category": "document",
                                "description": "**문서/계약서 조항 분석 툴**: 계약서·약관 텍스트를 입력받아 조항별 이슈와 근거 조회 힌트를 생성합니다. 옵션으로 조항별 자동 검색까지 수행할 수 있습니다.\n\n**응답 구조**:\n```json\n{\n  \"success\": true,\n  \"document_analysis\": {\n    \"clauses\": [\"제1조 ...\"],\n    \"clause_issues\": [...],\n    \"clause_basis_hints\": [...]\n  },\n  \"evidence_results\": [...],\n  \"legal_basis_block\": {...}\n}\n```",
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
                                            "description": "자동 검색 시 타입당 최대 결과 수",
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
                                        "has_legal_basis": {"type": "boolean"},
                                        "missing_reason": {"type": ["string", "null"]},
                                        "document_analysis": {"type": ["object", "null"]},
                                        "answer": {"type": ["object", "null"]},
                                        "citations": {"type": "array"},
                                        "legal_basis_block_text": {"type": ["string", "null"]},
                                        "retry_plan": {"type": ["object", "null"]}
                                    }
                                }
                            },
                            {
                                "name": "search_law_tool",
                                "priority": 2,
                                "category": "law",
                                "description": "법령을 검색합니다. 법령명 또는 키워드로 검색할 수 있습니다. 예: '형법', '개인정보보호법', '노동법'. query를 생략하면 전체 법령 목록을 반환합니다.\n\n**언제 사용하나요?**\n- `smart_search_tool`이 법령 검색을 자동으로 처리하지만, 직접 법령 목록을 보고 싶을 때\n- 특정 법령명으로 정확히 검색하고 싶을 때\n\n**응답 구조**:\n```json\n{\n  \"success\": true,\n  \"query\": \"형법\",\n  \"page\": 1,\n  \"per_page\": 10,\n  \"total\": 150,\n  \"laws\": [\n    {\n      \"law_id\": \"123456\",\n      \"law_name\": \"형법\",\n      \"...\": \"...\"\n    }\n  ]\n}\n```",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "query": {
                                            "type": "string",
                                            "description": "법령 검색어 (예: '형법', '개인정보보호법'). 생략하면 전체 목록 반환"
                                        },
                                        "page": {
                                            "type": "integer",
                                            "description": "페이지 번호",
                                            "default": 1,
                                            "minimum": 1
                                        },
                                        "per_page": {
                                            "type": "integer",
                                            "description": "페이지당 결과 수",
                                            "default": 10,
                                            "minimum": 1,
                                            "maximum": 100
                                        }
                                    },
                                    "required": []
                                },
                                "outputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "success": {"type": "boolean"},
                                        "query": {"type": ["string", "null"]},
                                        "page": {"type": "integer"},
                                        "per_page": {"type": "integer"},
                                        "total": {"type": "integer"},
                                        "laws": {"type": "array"}
                                    }
                                }
                            },
                            {
                                "name": "get_law_tool",
                                "priority": 2,
                                "category": "law",
                                "description": "법령을 조회합니다. mode에 따라 상세정보(detail), 전체 조문(articles), 단일 조문(single)을 조회할 수 있습니다. 예: '형법 제1조 확인', '민법 전체 조문 보기', '개인정보보호법 제15조 제1항 확인'.\n\n**파라미터 형식**:\n- `article_number`: '제1조', '1조', '1' 모두 지원 (자동 정규화)\n- `hang`: '제1항', '1항', '1' 모두 지원\n- `ho`: '제2호', '2호', '2' 모두 지원\n- `mok`: '가', '가목' 모두 지원\n\n**응답 구조**:\n```json\n{\n  \"success\": true,\n  \"law_name\": \"형법\",\n  \"law_id\": \"123456\",\n  \"mode\": \"single\",\n  \"article\": {\n    \"article_number\": \"제1조\",\n    \"content\": \"...\"\n  }\n}\n```",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "law_id": {
                                            "type": "string",
                                            "description": "법령 ID (law_name과 둘 중 하나는 필수)"
                                        },
                                        "law_name": {
                                            "type": "string",
                                            "description": "법령명 (예: '형법', '민법', '개인정보보호법'). law_id와 둘 중 하나는 필수"
                                        },
                                        "mode": {
                                            "type": "string",
                                            "description": "조회 모드: 'detail'(상세정보), 'articles'(전체 조문), 'single'(단일 조문)",
                                            "enum": ["detail", "articles", "single"],
                                            "default": "detail"
                                        },
                                        "article_number": {
                                            "type": "string",
                                            "description": "조 번호 (mode='single'일 때 필수, 예: '제1조', '제10조의2')"
                                        },
                                        "hang": {
                                            "type": "string",
                                            "description": "항 번호 (mode='single'일 때 선택사항, 예: '제1항', '제2항')"
                                        },
                                        "ho": {
                                            "type": "string",
                                            "description": "호 번호 (mode='single'일 때 선택사항, 예: '제2호', '제10호의2')"
                                        },
                                        "mok": {
                                            "type": "string",
                                            "description": "목 (mode='single'일 때 선택사항, 예: '가', '나', '다')"
                                        }
                                    },
                                    "required": []
                                },
                                "outputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "success": {"type": "boolean"},
                                        "law_name": {"type": ["string", "null"]},
                                        "law_id": {"type": ["string", "null"]},
                                        "mode": {"type": "string"},
                                        "article": {"type": ["object", "null"]},
                                        "articles": {"type": ["array", "null"]},
                                        "detail": {"type": ["object", "null"]}
                                    }
                                }
                            },
                            {
                                "name": "search_precedent_tool",
                                "priority": 2,
                                "category": "precedent",
                                "description": "판례를 검색합니다. 유사한 사건의 판례를 찾을 때 사용합니다. 예: '손해배상 판례 검색', '계약해지 관련 판례 찾기', '대법원 2020년 판례'.\n\n**다단계 검색 전략 (use_fallback=true)**: 검색 결과가 0일 때 자동으로 동의어 확장, 날짜 범위 확장, 키워드 추출 등을 시도합니다.\n\n**응답 구조**:\n```json\n{\n  \"success\": true,\n  \"query\": \"손해배상\",\n  \"page\": 1,\n  \"per_page\": 20,\n  \"total\": 150,\n  \"precedents\": [...],\n  \"query_plan\": [...],\n  \"attempts\": [...],\n  \"fallback_used\": false\n}\n```",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "query": {
                                            "type": "string",
                                            "description": "검색어 (판례명 또는 키워드, 예: '손해배상', '계약해지')"
                                        },
                                        "page": {
                                            "type": "integer",
                                            "description": "페이지 번호",
                                            "default": 1,
                                            "minimum": 1
                                        },
                                        "per_page": {
                                            "type": "integer",
                                            "description": "페이지당 결과 수",
                                            "default": 20,
                                            "minimum": 1,
                                            "maximum": 100
                                        },
                                        "court": {
                                            "type": "string",
                                            "enum": ["400201", "400202"],
                                            "description": "법원 종류: '400201' (대법원), '400202' (하위법원). 생략 가능."
                                        },
                                        "date_from": {
                                            "type": "string",
                                            "description": "시작일자 (YYYYMMDD, 예: '20200101')"
                                        },
                                        "date_to": {
                                            "type": "string",
                                            "description": "종료일자 (YYYYMMDD, 예: '20201231')"
                                        },
                                        "use_fallback": {
                                            "type": "boolean",
                                            "description": "다단계 fallback 전략 사용 여부 (검색 결과가 0일 때 자동으로 동의어 확장, 날짜 범위 확장 등을 시도)",
                                            "default": False
                                        },
                                        "issue_type": {
                                            "type": "string",
                                            "description": "쟁점 유형 (예: '근로자성', '재산분할', '부당해고', '손해배상'). 검색 쿼리 최적화에 사용됩니다."
                                        },
                                        "must_include": {
                                            "type": "array",
                                            "items": {
                                                "type": "string"
                                            },
                                            "description": "반드시 포함할 키워드 리스트 (예: ['근로기준법', '근로자']). 검색 정확도를 높이기 위해 사용됩니다."
                                        }
                                    },
                                    "required": []
                                },
                                "outputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "success": {"type": "boolean"},
                                        "query": {"type": ["string", "null"]},
                                        "page": {"type": "integer"},
                                        "per_page": {"type": "integer"},
                                        "total": {"type": "integer"},
                                        "precedents": {"type": "array"},
                                        "query_plan": {"type": ["array", "null"]},
                                        "attempts": {"type": ["array", "null"]},
                                        "fallback_used": {"type": ["boolean", "null"]}
                                    }
                                }
                            },
                            {
                                "name": "get_precedent_tool",
                                "priority": 2,
                                "category": "precedent",
                                "description": "판례 상세 정보를 조회합니다. 판례 ID 또는 사건번호로 조회할 수 있습니다. 유사한 사건의 판례를 찾은 후 상세 내용을 확인할 때 사용합니다. 예: '판례 ID 123456 상세 내용 확인', '사건번호 2020다12345 판례 조회'.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "precedent_id": {
                                            "type": "string",
                                            "description": "판례 일련번호 (precedent_id 또는 case_number 중 하나는 필수)"
                                        },
                                        "case_number": {
                                            "type": "string",
                                            "description": "사건번호 (예: '2020다12345', precedent_id 또는 case_number 중 하나는 필수)"
                                        }
                                    },
                                    "required": []
                                },
                                "outputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "success": {"type": "boolean"},
                                        "precedent_id": {"type": ["string", "null"]},
                                        "case_number": {"type": ["string", "null"]},
                                        "precedent": {"type": ["object", "null"]}
                                    }
                                }
                            },
                            {
                                "name": "search_law_interpretation_tool",
                                "priority": 2,
                                "category": "interpretation",
                                "description": "법령해석을 검색합니다. 정부 기관의 공식 법령 해석을 확인할 때 사용합니다. 특정 법령에 대한 정부의 공식 해석이나 의견을 찾을 때 사용합니다. 예: '개인정보보호법 해석 검색', '소득세 관련 법령해석 찾기', '고용노동부 법령해석 확인'.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "query": {
                                            "type": "string",
                                            "description": "검색어 (법령해석명 또는 키워드, 예: '개인정보보호법', '소득세')"
                                        },
                                        "page": {
                                            "type": "integer",
                                            "description": "페이지 번호",
                                            "default": 1,
                                            "minimum": 1
                                        },
                                        "per_page": {
                                            "type": "integer",
                                            "description": "페이지당 결과 수",
                                            "default": 20,
                                            "minimum": 1,
                                            "maximum": 100
                                        },
                                        "agency": {
                                            "type": "string",
                                            "enum": [
                                                "기획재정부", "국세청", "관세청", "고용노동부", "교육부", 
                                                "보건복지부", "질병관리청", "식품의약품안전처", "법무부", 
                                                "외교부", "국방부", "방위사업청", "병무청", "행정안전부", 
                                                "경찰청", "소방청", "해양경찰청", "문화체육관광부", 
                                                "농림축산식품부", "농촌진흥청", "산림청", "산업통상부", 
                                                "중소벤처기업부", "과학기술정보통신부", "국가데이터처", 
                                                "지식재산처", "기상청", "해양수산부", "국토교통부", 
                                                "행정중심복합도시건설청", "기후에너지환경부", "통일부", 
                                                "국가보훈부", "성평등가족부", "재외동포청", "인사혁신처", 
                                                "법제처", "조달청", "국가유산청"
                                            ],
                                            "description": "부처명. 주요 부처: '기획재정부', '국세청', '고용노동부', '교육부', '보건복지부', '법무부', '외교부', '국방부', '행정안전부', '문화체육관광부', '농림축산식품부', '산업통상부', '중소벤처기업부', '과학기술정보통신부', '해양수산부', '국토교통부', '기후에너지환경부', '통일부', '국가보훈부', '성평등가족부' 등. 생략 가능."
                                        }
                                    },
                                    "required": []
                                },
                                "outputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "success": {"type": "boolean"},
                                        "query": {"type": ["string", "null"]},
                                        "page": {"type": "integer"},
                                        "per_page": {"type": "integer"},
                                        "total": {"type": "integer"},
                                        "interpretations": {"type": "array"}
                                    }
                                }
                            },
                            {
                                "name": "search_administrative_appeal_tool",
                                "priority": 2,
                                "category": "administrative",
                                "description": "행정심판 사례를 검색합니다. 행정기관의 처분이나 부작위에 대한 심판 사례를 찾을 때 사용합니다. 유사한 행정심판 사례를 참고하거나 선례를 확인할 때 사용합니다. 예: '행정심판 사례 검색', '2020년 행정심판 재결례 찾기', '세금 관련 행정심판 사례'.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "query": {
                                            "type": "string",
                                            "description": "검색어 (행정심판 사건명 또는 키워드)"
                                        },
                                        "page": {
                                            "type": "integer",
                                            "description": "페이지 번호",
                                            "default": 1,
                                            "minimum": 1
                                        },
                                        "per_page": {
                                            "type": "integer",
                                            "description": "페이지당 결과 수",
                                            "default": 20,
                                            "minimum": 1,
                                            "maximum": 100
                                        },
                                        "date_from": {
                                            "type": "string",
                                            "description": "시작일자 (YYYYMMDD)"
                                        },
                                        "date_to": {
                                            "type": "string",
                                            "description": "종료일자 (YYYYMMDD)"
                                        }
                                    },
                                    "required": []
                                },
                                "outputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "success": {"type": "boolean"},
                                        "query": {"type": ["string", "null"]},
                                        "page": {"type": "integer"},
                                        "per_page": {"type": "integer"},
                                        "total": {"type": "integer"},
                                        "appeals": {"type": "array"}
                                    }
                                }
                            },
                        ]
                        
                        # 표준 권장: 무파라미터 툴 스키마 보강 + outputSchema 기본 제공
                        for tool in tools_list:
                            input_schema = tool.get("inputSchema")
                            if isinstance(input_schema, dict):
                                props = input_schema.get("properties")
                                required = input_schema.get("required")
                                if (not props) and (not required) and "additionalProperties" not in input_schema:
                                    tool["inputSchema"] = {
                                        "type": "object",
                                        "additionalProperties": False
                                    }
                            if "outputSchema" not in tool:
                                tool["outputSchema"] = {
                                    "type": "object"
                                }
                        
                        # MCP 표준 필드만 노출 (추가 필드는 annotations로 이동)
                        mcp_tools = []
                        for tool in tools_list:
                            annotations = {}
                            if "priority" in tool:
                                annotations["priority"] = tool.get("priority")
                            if "category" in tool:
                                annotations["category"] = tool.get("category")
                            filtered = {
                                "name": tool.get("name"),
                                "title": tool.get("title"),
                                "description": tool.get("description"),
                                "inputSchema": tool.get("inputSchema"),
                                "outputSchema": tool.get("outputSchema")
                            }
                            # None 값 제거 (PlayMCP 엄격 파서 대응)
                            filtered = {k: v for k, v in filtered.items() if v is not None}
                            if annotations:
                                filtered["annotations"] = annotations
                            if tool.get("icons"):
                                filtered["icons"] = tool.get("icons")
                            mcp_tools.append(filtered)
                        
                        paged_tools = mcp_tools[start_index:start_index + page_size]
                        next_cursor = None
                        if start_index + page_size < len(mcp_tools):
                            next_cursor = str(start_index + page_size)
                        
                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": {
                                "tools": paged_tools
                            }
                        }
                        if next_cursor is not None:
                            response["result"]["nextCursor"] = next_cursor
                        response_json = json.dumps(response, ensure_ascii=False)
                        logger.info("MCP: tools/list response | length=%d tools_count=%d", 
                                   len(response_json), 
                                   len(mcp_tools))
                        yield f"data: {response_json}\n\n"
                        
                    elif method == "tools/call":
                        tool_name = params.get("name")
                        arguments = params.get("arguments", {})
                        
                        logger.info("MCP tool call | tool=%s arguments=%s", tool_name, arguments)
                        
                        result = None
                        try:
                            if tool_name == "health":
                                result = await health_service.check_health()
                            elif tool_name == "smart_search_tool":
                                query = arguments.get("query")
                                search_types = arguments.get("search_types")
                                max_results = arguments.get("max_results_per_type", 5)
                                logger.debug("Calling smart_search | query=%s search_types=%s max_results=%d", 
                                           query, search_types, max_results)
                                result = await smart_search_service.smart_search(
                                    query,
                                    search_types,
                                    max_results,
                                    None
                                )
                            elif tool_name == "situation_guidance_tool":
                                situation = arguments.get("situation")
                                max_results = arguments.get("max_results_per_type", 5)
                                logger.debug("Calling situation_guidance | situation=%s max_results=%d", 
                                           situation[:100] if situation else None, max_results)
                                result = await situation_guidance_service.comprehensive_search(
                                    situation,
                                    max_results,
                                    None
                                )
                            elif tool_name == "document_issue_tool":
                                document_text = arguments.get("document_text")
                                auto_search = arguments.get("auto_search", True)
                                max_clauses = arguments.get("max_clauses", 3)
                                max_results = arguments.get("max_results_per_type", 3)
                                logger.debug("Calling document_issue | length=%s", len(document_text) if document_text else 0)
                                result = await situation_guidance_service.document_issue_analysis(
                                    document_text,
                                    None,
                                    auto_search=auto_search,
                                    max_clauses=max_clauses,
                                    max_results_per_type=max_results
                                )
                            elif tool_name == "search_law_tool":
                                query = arguments.get("query")
                                page = arguments.get("page", 1)
                                per_page = arguments.get("per_page", 10)
                                req = SearchLawRequest(query=query, page=page, per_page=per_page)
                                logger.debug("Calling search_law | query=%s page=%d per_page=%d", query, page, per_page)
                                result = await law_service.search_law(req, None)
                            elif tool_name == "get_law_tool":
                                law_id = arguments.get("law_id")
                                law_name = arguments.get("law_name")
                                mode = arguments.get("mode", "detail")
                                article_number = arguments.get("article_number")
                                hang = arguments.get("hang")
                                ho = arguments.get("ho")
                                mok = arguments.get("mok")
                                req = GetLawRequest(
                                        law_id=law_id,
                                    law_name=law_name,
                                    mode=mode,
                                        article_number=article_number,
                                        hang=hang,
                                        ho=ho,
                                        mok=mok
                                    )
                                logger.debug("Calling get_law | law_id=%s law_name=%s mode=%s article_number=%s", 
                                           law_id, law_name, mode, article_number)
                                result = await law_service.get_law(req, None)
                            elif tool_name == "search_precedent_tool":
                                query = arguments.get("query")
                                page = arguments.get("page", 1)
                                per_page = arguments.get("per_page", 20)
                                court = arguments.get("court")
                                date_from = arguments.get("date_from")
                                date_to = arguments.get("date_to")
                                use_fallback = arguments.get("use_fallback", False)
                                issue_type = arguments.get("issue_type")
                                must_include = arguments.get("must_include")
                                req = SearchPrecedentRequest(
                                    query=query,
                                    page=page,
                                    per_page=per_page,
                                    court=court,
                                    date_from=date_from,
                                    date_to=date_to,
                                    use_fallback=use_fallback,
                                    issue_type=issue_type,
                                    must_include=must_include
                                )
                                logger.debug("Calling search_precedent | query=%s page=%d per_page=%d use_fallback=%s", 
                                           query, page, per_page, use_fallback)
                                result = await precedent_service.search_precedent(req, None)
                            elif tool_name == "get_precedent_tool":
                                precedent_id = arguments.get("precedent_id")
                                case_number = arguments.get("case_number")
                                req = GetPrecedentRequest(
                                    precedent_id=precedent_id,
                                    case_number=case_number
                                )
                                logger.debug("Calling get_precedent | precedent_id=%s case_number=%s", precedent_id, case_number)
                                result = await precedent_service.get_precedent(req, None)
                            elif tool_name == "search_law_interpretation_tool":
                                query = arguments.get("query")
                                page = arguments.get("page", 1)
                                per_page = arguments.get("per_page", 20)
                                agency = arguments.get("agency")
                                req = SearchLawInterpretationRequest(
                                    query=query,
                                    page=page,
                                    per_page=per_page,
                                    agency=agency
                                )
                                logger.debug("Calling search_law_interpretation | query=%s page=%d per_page=%d agency=%s", 
                                           query, page, per_page, agency)
                                result = await law_interpretation_service.search_law_interpretation(req, None)
                            elif tool_name == "search_administrative_appeal_tool":
                                query = arguments.get("query")
                                page = arguments.get("page", 1)
                                per_page = arguments.get("per_page", 20)
                                date_from = arguments.get("date_from")
                                date_to = arguments.get("date_to")
                                req = SearchAdministrativeAppealRequest(
                                    query=query,
                                    page=page,
                                    per_page=per_page,
                                    date_from=date_from,
                                    date_to=date_to
                                )
                                logger.debug("Calling search_administrative_appeal | query=%s page=%d per_page=%d", query, page, per_page)
                                result = await administrative_appeal_service.search_administrative_appeal(req, None)
                            elif tool_name == "get_administrative_appeal_tool":
                                appeal_id = arguments.get("appeal_id")
                                req = GetAdministrativeAppealRequest(appeal_id=appeal_id)
                                logger.debug("Calling get_administrative_appeal | appeal_id=%s", appeal_id)
                                result = await administrative_appeal_service.get_administrative_appeal(req, None)
                            elif tool_name == "search_committee_decision_tool":
                                committee_type = arguments.get("committee_type")
                                query = arguments.get("query")
                                page = arguments.get("page", 1)
                                per_page = arguments.get("per_page", 20)
                                req = SearchCommitteeDecisionRequest(
                                    committee_type=committee_type,
                                    query=query,
                                    page=page,
                                    per_page=per_page
                                )
                                logger.debug("Calling search_committee_decision | committee_type=%s query=%s page=%d per_page=%d",
                                           committee_type, query, page, per_page)
                                result = await committee_decision_service.search_committee_decision(req, None)
                            elif tool_name == "get_committee_decision_tool":
                                committee_type = arguments.get("committee_type")
                                decision_id = arguments.get("decision_id")
                                req = GetCommitteeDecisionRequest(
                                    committee_type=committee_type,
                                    decision_id=decision_id
                                )
                                logger.debug("Calling get_committee_decision | committee_type=%s decision_id=%s",
                                           committee_type, decision_id)
                                result = await committee_decision_service.get_committee_decision(req, None)
                            elif tool_name == "search_constitutional_decision_tool":
                                query = arguments.get("query")
                                page = arguments.get("page", 1)
                                per_page = arguments.get("per_page", 20)
                                date_from = arguments.get("date_from")
                                date_to = arguments.get("date_to")
                                req = SearchConstitutionalDecisionRequest(
                                    query=query,
                                    page=page,
                                    per_page=per_page,
                                    date_from=date_from,
                                    date_to=date_to
                                )
                                logger.debug("Calling search_constitutional_decision | query=%s page=%d per_page=%d", query, page, per_page)
                                result = await constitutional_decision_service.search_constitutional_decision(req, None)
                            elif tool_name == "get_constitutional_decision_tool":
                                decision_id = arguments.get("decision_id")
                                req = GetConstitutionalDecisionRequest(decision_id=decision_id)
                                logger.debug("Calling get_constitutional_decision | decision_id=%s", decision_id)
                                result = await constitutional_decision_service.get_constitutional_decision(req, None)
                            elif tool_name == "search_special_administrative_appeal_tool":
                                tribunal_type = arguments.get("tribunal_type")
                                query = arguments.get("query")
                                page = arguments.get("page", 1)
                                per_page = arguments.get("per_page", 20)
                                req = SearchSpecialAdministrativeAppealRequest(
                                    tribunal_type=tribunal_type,
                                    query=query,
                                    page=page,
                                    per_page=per_page
                                )
                                logger.debug("Calling search_special_administrative_appeal | tribunal_type=%s query=%s page=%d per_page=%d",
                                           tribunal_type, query, page, per_page)
                                result = await special_administrative_appeal_service.search_special_administrative_appeal(req, None)
                            elif tool_name == "get_special_administrative_appeal_tool":
                                tribunal_type = arguments.get("tribunal_type")
                                appeal_id = arguments.get("appeal_id")
                                req = GetSpecialAdministrativeAppealRequest(
                                    tribunal_type=tribunal_type,
                                    appeal_id=appeal_id
                                )
                                logger.debug("Calling get_special_administrative_appeal | tribunal_type=%s appeal_id=%s",
                                           tribunal_type, appeal_id)
                                result = await special_administrative_appeal_service.get_special_administrative_appeal(req, None)
                            elif tool_name == "search_local_ordinance_tool":
                                query = arguments.get("query")
                                local_government = arguments.get("local_government")
                                page = arguments.get("page", 1)
                                per_page = arguments.get("per_page", 20)
                                req = SearchLocalOrdinanceRequest(
                                    query=query,
                                    local_government=local_government,
                                    page=page,
                                    per_page=per_page
                                )
                                logger.debug("Calling search_local_ordinance | query=%s local_government=%s page=%d per_page=%d",
                                           query, local_government, page, per_page)
                                result = await local_ordinance_service.search_local_ordinance(req, None)
                            elif tool_name == "search_administrative_rule_tool":
                                query = arguments.get("query")
                                agency = arguments.get("agency")
                                page = arguments.get("page", 1)
                                per_page = arguments.get("per_page", 20)
                                req = SearchAdministrativeRuleRequest(
                                    query=query,
                                    agency=agency,
                                    page=page,
                                    per_page=per_page
                                )
                                logger.debug("Calling search_administrative_rule | query=%s agency=%s page=%d per_page=%d",
                                           query, agency, page, per_page)
                                result = await administrative_rule_service.search_administrative_rule(req, None)
                            elif tool_name == "compare_laws_tool":
                                law_name = arguments.get("law_name")
                                compare_type = arguments.get("compare_type", "신구법")
                                req = CompareLawsRequest(
                                    law_name=law_name,
                                    compare_type=compare_type
                                )
                                logger.debug("Calling compare_laws | law_name=%s compare_type=%s", law_name, compare_type)
                                result = await law_comparison_service.compare_laws(req, None)
                            elif tool_name.startswith("call_api_"):
                                # 동적 API 호출 툴
                                api_id = arguments.get("_api_id")
                                if not api_id:
                                    # 툴 이름에서 API ID 추출
                                    try:
                                        api_id = int(tool_name.replace("call_api_", ""))
                                    except ValueError:
                                        result = {"error": f"유효하지 않은 API ID: {tool_name}"}
                                        api_id = None
                                
                                if api_id:
                                    # _api_id 제외한 나머지 파라미터
                                    api_params = {k: v for k, v in arguments.items() if k != "_api_id"}
                                    logger.info(f"Calling dynamic API | api_id={api_id} params={list(api_params.keys())}")
                                    result = await generic_api_service.call_api(api_id, api_params, None)
                            else:
                                result = {"error": f"Unknown tool: {tool_name}"}
                        except asyncio.TimeoutError as e:
                            logger.error("MCP: Tool %s timeout: %s", tool_name, str(e))
                            result = {
                                "error": f"Tool 실행 타임아웃: {str(e)}",
                                "recovery_guide": "도구 실행 시간이 초과되었습니다. 잠시 후 다시 시도하거나, 더 간단한 요청으로 시도해보세요."
                            }
                        except Exception as e:
                            logger.exception("MCP: Error calling tool %s: %s", tool_name, str(e))
                            result = {
                                "error": f"Tool 실행 중 오류 발생: {str(e)}",
                                "error_type": type(e).__name__,
                                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
                            }
                        
                        # JSON 직렬화 전에 데이터 정리 (특수문자, 제어문자 제거)
                        _CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
                        def clean_for_json(obj):
                            """JSON 직렬화를 위해 데이터 정리 (개행 유지)"""
                            if isinstance(obj, dict):
                                return {k: clean_for_json(v) for k, v in obj.items()}
                            elif isinstance(obj, list):
                                return [clean_for_json(item) for item in obj]
                            elif isinstance(obj, str):
                                # 제어 문자 제거 (개행/탭은 유지)
                                return _CONTROL_CHARS_RE.sub("", obj)
                            else:
                                return obj
                        
                        # 데이터 정리
                        cleaned_result = clean_for_json(result) if isinstance(result, (dict, list, str)) else result
                        
                        # Cursor가 기대하는 MCP tool result 포맷으로 변환
                        # 필수: result.content: [{ "type": "text", "text": "..." }]
                        # 권장: isError: false/true
                        
                        # 에러 여부 확인
                        is_error = False
                        if isinstance(cleaned_result, dict) and "error" in cleaned_result:
                            is_error = True
                        
                        # content 배열 생성 (구조화된 응답 사용)
                        if isinstance(cleaned_result, dict) and "content" in cleaned_result:
                            # 이미 content가 있으면 그대로 사용 (하지만 isError는 추가)
                            mcp_result = cleaned_result.copy()
                            mcp_result["isError"] = is_error
                        else:
                            # 구조화된 응답으로 변환
                            mcp_result = format_mcp_response(cleaned_result, tool_name)
                        
                        # 24KB 응답 크기 제한 적용 (MCP 규격 준수)
                        mcp_result = truncate_response(mcp_result)
                        response_size = get_response_size(mcp_result)
                        logger.info("MCP: Response size after truncation: %d bytes (max: 24KB)", response_size)
                        
                        final_response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": mcp_result
                        }
                        # 최종 JSON 크기 하드 제한 적용 (24KB)
                        final_response = shrink_response_bytes(final_response)
                        final_response_size = get_response_size(final_response)
                        logger.info("MCP: Final JSONRPC size=%d bytes (max: 24076)", final_response_size)
                        logger.info("MCP: Sending final response | tool=%s has_error=%s result_size=%d", 
                                   tool_name, 
                                   "error" in result if isinstance(result, dict) else False,
                                   len(str(result)))
                        # JSON 직렬화 (한글 처리)
                        try:
                            response_json = json.dumps(final_response, ensure_ascii=False)
                            logger.info("MCP: Response JSON length=%d (first 300 chars): %s", len(response_json), response_json[:300])
                        except (TypeError, ValueError) as e:
                            logger.error("JSON serialization failed: %s", str(e))
                            # 폴백: ASCII로 직렬화
                            try:
                                response_json = json.dumps(final_response, ensure_ascii=True)
                            except Exception as e2:
                                logger.error("ASCII serialization also failed: %s", str(e2))
                                # 최종 폴백: 에러 메시지 반환
                                error_response = {
                                    "jsonrpc": "2.0",
                                    "id": request_id,
                                    "error": {
                                        "code": -32603,
                                        "message": f"Response serialization failed: {str(e2)}"
                                    }
                                }
                                response_json = json.dumps(error_response, ensure_ascii=True)
                        
                        # SSE 이벤트 전송 (즉시 flush되도록)
                        event_data = f"data: {response_json}\n\n"
                        logger.info("MCP: Yielding SSE event | length=%d", len(event_data))
                        yield event_data
                        logger.debug("MCP: SSE event sent, stream will close")
                        
                    else:
                        error_response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": -32601,
                                "message": f"Method not found: {method}"
                            }
                        }
                        yield f"data: {json.dumps(error_response)}\n\n"
                    
                except Exception as e:
                    logger.exception("Error processing MCP message: %s", str(e))
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32603,
                            "message": f"Internal error: {str(e)}"
                        }
                    }
                    yield f"data: {json.dumps(error_response)}\n\n"
            
            # SSE 응답 (MCP Streamable HTTP는 항상 SSE 사용)
            response_headers = {
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Accept, Mcp-Session-Id",
                "Content-Type": "text/event-stream"
            }
            
            # 세션 ID가 있으면 응답에도 포함
            if session_id_header:
                response_headers["Mcp-Session-Id"] = session_id_header
            
            logger.info("MCP POST RESPONSE (SSE)")
            logger.info("  Status: 200")
            logger.info("  Content-Type: text/event-stream")
            if session_id_header:
                logger.info("  Mcp-Session-Id: %s", session_id_header)
            logger.info("=" * 80)
            
            return StreamingResponse(
                process_mcp_message(),
                media_type="text/event-stream",
                headers=response_headers
            )
            
        except Exception as e:
            logger.exception("Error in MCP endpoint: %s", str(e))
            async def error_stream():
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {str(e)}"
                    }
                }
                yield f"data: {json.dumps(error_response)}\n\n"
            return StreamingResponse(error_stream(), media_type="text/event-stream")

