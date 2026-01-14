"""
MCP Routes - MCP Streamable HTTP 엔드포인트
Controller 패턴: 요청을 받아 Service를 호출
"""
import json
import asyncio
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
from ..utils.response_truncator import truncate_response, get_response_size
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
            logger.info("MCP request body: %s", body)
            
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
                                    "tools": {}
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
                        # 기본 툴 목록
                        tools_list = [
                            {
                                "name": "health",
                                "priority": 2,
                                "category": "utility",
                                "description": "서비스 상태를 확인합니다. API 키 설정 상태, 환경 변수, 서버 상태 등을 확인할 때 사용합니다. 예: '서버 상태 확인', 'API 키 설정 확인'.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {},
                                    "required": []
                                }
                            },
                            {
                                "name": "smart_search_tool",
                                "priority": 1,
                                "category": "integrated",
                                "description": "**통합 검색 툴 (우선 사용 권장)**: 사용자 질문을 분석하여 적절한 법적 정보를 자동으로 검색합니다. 법령, 판례, 법령해석, 행정심판, 헌재결정 등을 자동으로 찾아줍니다. LLM이 사용자 질문만 받으면 이 툴을 사용하여 모든 법적 정보를 통합 검색할 수 있습니다.\n\n**응답 구조**:\n```json\n{\n  \"success\": true,\n  \"query\": \"형법 제329조\",\n  \"detected_intents\": [\"law\"],\n  \"results\": {\n    \"law\": {\n      \"law_name\": \"형법\",\n      \"article\": {\n        \"article_number\": \"제329조\",\n        \"content\": \"...\"\n      }\n    }\n  },\n  \"total_types\": 1\n}\n```",
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
                                }
                            },
                            {
                                "name": "situation_guidance_tool",
                                "priority": 1,
                                "category": "integrated",
                                "description": "**통합 상황 가이드 툴 (우선 사용 권장)**: 사용자의 법적 상황을 종합적으로 분석하여 관련 법령, 판례, 해석, 심판례를 모두 찾아주고 단계별 가이드를 제공합니다. 여러 법과 여러 기관의 정보를 통합하여 사용자의 법적 스트레스를 덜어주는 것이 목적입니다.\n\n**응답 구조**:\n```json\n{\n  \"success\": true,\n  \"situation\": \"회사에서 해고당했는데 퇴직금을 받지 못했어요\",\n  \"detected_domains\": [\"노동\"],\n  \"laws\": {...},\n  \"precedents\": {...},\n  \"interpretations\": {...},\n  \"guidance\": [\n    \"1. 근로기준법 제34조 확인\",\n    \"2. 퇴직금 지급 의무 확인\"\n  ]\n}\n```",
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
                                }
                            },
                            {
                                "name": "search_precedent_tool",
                                "priority": 2,
                                "category": "precedent",
                                "description": "판례를 검색합니다. 유사한 사건의 판례를 찾을 때 사용합니다. 예: '손해배상 판례 검색', '계약해지 관련 판례 찾기', '대법원 2020년 판례'.\n\n**응답 구조**:\n```json\n{\n  \"success\": true,\n  \"query\": \"손해배상\",\n  \"page\": 1,\n  \"per_page\": 20,\n  \"total\": 150,\n  \"precedents\": [\n    {\n      \"precedent_id\": \"123456\",\n      \"case_name\": \"...\",\n      \"case_number\": \"...\"\n    }\n  ]\n}\n```",
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
                                        }
                                    },
                                    "required": []
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
                                }
                            },
                            {
                                "name": "get_law_interpretation_tool",
                                "priority": 2,
                                "category": "interpretation",
                                "description": "법령해석 상세 정보를 조회합니다. 법령해석 검색 결과에서 특정 해석의 상세 내용을 확인할 때 사용합니다. 예: '법령해석 ID 123456 상세 내용 확인', '고용노동부 법령해석 상세 조회'.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "interpretation_id": {
                                            "type": "string",
                                            "description": "법령해석 일련번호 (필수)"
                                        }
                                    },
                                    "required": ["interpretation_id"]
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
                                }
                            },
                            {
                                "name": "get_administrative_appeal_tool",
                                "priority": 2,
                                "category": "administrative",
                                "description": "행정심판 상세 정보를 조회합니다. 행정심판 검색 결과에서 특정 심판의 상세 내용과 재결 내용을 확인할 때 사용합니다. 예: '행정심판 ID 123456 상세 내용', '재결례 일련번호로 상세 조회'.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "appeal_id": {
                                            "type": "string",
                                            "description": "행정심판 일련번호 (필수)"
                                        }
                                    },
                                    "required": ["appeal_id"]
                                }
                            },
                            {
                                "name": "search_committee_decision_tool",
                                "priority": 2,
                                "category": "administrative",
                                "description": "위원회 결정문을 검색합니다. 개인정보보호위원회, 금융위원회, 노동위원회 등 각종 위원회의 결정문을 검색할 수 있습니다. 예: '개인정보보호위원회 결정문 찾아줘', '금융위원회 결정 확인'.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "committee_type": {
                                            "type": "string",
                                            "description": "위원회 종류 (예: '개인정보보호위원회', '금융위원회', '노동위원회', '고용보험심사위원회', '국민권익위원회')",
                                            "enum": ["개인정보보호위원회", "금융위원회", "노동위원회", "고용보험심사위원회", "국민권익위원회", "방송미디어통신위원회", "산업재해보상보험재심사위원회", "중앙토지수용위원회", "중앙환경분쟁조정위원회", "증권선물위원회", "국가인권위원회"]
                                        },
                                        "query": {
                                            "type": "string",
                                            "description": "검색어 (결정문 사건명 또는 키워드)"
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
                                        }
                                    },
                                    "required": ["committee_type"]
                                }
                            },
                            {
                                "name": "get_committee_decision_tool",
                                "priority": 2,
                                "category": "administrative",
                                "description": "위원회 결정문 상세 정보를 조회합니다. 위원회 결정문 검색 결과에서 특정 결정문의 상세 내용을 확인할 때 사용합니다. 예: '개인정보보호위원회 결정문 ID 123456 상세 내용', '금융위원회 결정문 상세 조회'.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "committee_type": {
                                            "type": "string",
                                            "description": "위원회 종류 (예: '개인정보보호위원회', '금융위원회')",
                                            "enum": ["개인정보보호위원회", "금융위원회", "노동위원회", "고용보험심사위원회", "국민권익위원회", "방송미디어통신위원회", "산업재해보상보험재심사위원회", "중앙토지수용위원회", "중앙환경분쟁조정위원회", "증권선물위원회", "국가인권위원회"]
                                        },
                                        "decision_id": {
                                            "type": "string",
                                            "description": "결정문 일련번호 (필수)"
                                        }
                                    },
                                    "required": ["committee_type", "decision_id"]
                                }
                            },
                            {
                                "name": "search_constitutional_decision_tool",
                                "priority": 2,
                                "category": "constitutional",
                                "description": "헌법재판소 결정례를 검색합니다. 법률이나 행정처분의 위헌 여부를 확인하거나 헌법재판소의 결정례를 참고할 때 사용합니다. 예: '헌재결정례 검색', '위헌 결정례 찾기', '2020년 헌재결정 확인', '개인정보보호법 위헌 결정'.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "query": {
                                            "type": "string",
                                            "description": "검색어 (헌재결정 사건명 또는 키워드)"
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
                                }
                            },
                            {
                                "name": "get_constitutional_decision_tool",
                                "priority": 2,
                                "category": "constitutional",
                                "description": "헌법재판소 결정 상세 정보를 조회합니다. 헌재결정 검색 결과에서 특정 결정의 상세 내용과 결정 이유를 확인할 때 사용합니다. 예: '헌재결정 ID 123456 상세 내용', '헌재결정례 일련번호로 상세 조회'.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "decision_id": {
                                            "type": "string",
                                            "description": "헌재결정 일련번호 (필수)"
                                        }
                                    },
                                    "required": ["decision_id"]
                                }
                            },
                            {
                                "name": "search_special_administrative_appeal_tool",
                                "priority": 2,
                                "category": "administrative",
                                "description": "특별행정심판을 검색합니다. 조세심판원, 해양안전심판원 등 특별행정심판원의 재결례를 검색할 수 있습니다. 세금 관련 분쟁이나 해양사고 관련 심판 사례를 찾을 때 사용합니다. 예: '조세심판원 재결례 검색', '해양안전심판원 특별행정심판 찾기', '소득세 관련 조세심판 사례'.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "tribunal_type": {
                                            "type": "string",
                                            "description": "심판원 종류 (예: '조세심판원', '해양안전심판원', '인사혁신처 소청심사위원회', '국민권익위원회')",
                                            "enum": ["조세심판원", "해양안전심판원", "국민권익위원회", "인사혁신처 소청심사위원회"]
                                        },
                                        "query": {
                                            "type": "string",
                                            "description": "검색어 (재결례 사건명 또는 키워드)"
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
                                        }
                                    },
                                    "required": ["tribunal_type"]
                                }
                            },
                            {
                                "name": "get_special_administrative_appeal_tool",
                                "priority": 2,
                                "category": "administrative",
                                "description": "특별행정심판 상세 정보를 조회합니다. 특별행정심판 검색 결과에서 특정 심판의 상세 내용과 재결 내용을 확인할 때 사용합니다. 예: '조세심판원 재결례 ID 123456 상세 내용', '특별행정심판 상세 조회'.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "tribunal_type": {
                                            "type": "string",
                                            "description": "심판원 종류 (예: '조세심판원', '해양안전심판원')",
                                            "enum": ["조세심판원", "해양안전심판원", "국민권익위원회", "인사혁신처 소청심사위원회"]
                                        },
                                        "appeal_id": {
                                            "type": "string",
                                            "description": "재결례 일련번호 (필수)"
                                        }
                                    },
                                    "required": ["tribunal_type", "appeal_id"]
                                }
                            },
                            {
                                "name": "compare_laws_tool",
                                "priority": 2,
                                "category": "utility",
                                "description": "법령을 비교합니다. 신구법 비교, 법령 연혁, 3단 비교를 지원합니다. 예: '형법의 변경사항을 알려줘', '개인정보보호법 신구법 비교', '민법 연혁 확인'.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "law_name": {
                                            "type": "string",
                                            "description": "법령명 (예: '형법', '민법', '개인정보보호법')"
                                        },
                                        "compare_type": {
                                            "type": "string",
                                            "description": "비교 유형",
                                            "enum": ["신구법", "연혁", "3단비교"],
                                            "default": "신구법"
                                        }
                                    },
                                    "required": ["law_name"]
                                }
                            },
                            {
                                "name": "search_local_ordinance_tool",
                                "priority": 2,
                                "category": "local",
                                "description": "지방자치단체의 조례, 규칙을 검색합니다. 예: '서울시 조례 검색', '부산시 규칙 찾기'.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "query": {
                                            "type": "string",
                                            "description": "검색어 (조례명 또는 키워드)"
                                        },
                                        "local_government": {
                                            "type": "string",
                                            "enum": [
                                                "서울특별시", "부산광역시", "대구광역시", "인천광역시", 
                                                "광주광역시", "대전광역시", "울산광역시", "세종특별자치시",
                                                "경기도", "강원특별자치도", "충청북도", "충청남도", 
                                                "전북특별자치도", "전라남도", "경상북도", "경상남도", 
                                                "제주특별자치도",
                                                "수원시", "성남시", "고양시", "용인시", "부천시", 
                                                "안산시", "안양시", "남양주시", "화성시", "평택시",
                                                "의정부시", "시흥시", "김포시", "광명시", "광주시",
                                                "군포시", "하남시", "오산시", "이천시", "안성시",
                                                "포천시", "의왕시", "양주시", "구리시", "여주시",
                                                "양평군", "동두천시", "과천시", "가평군", "연천군",
                                                "춘천시", "원주시", "강릉시", "동해시", "태백시",
                                                "속초시", "삼척시", "홍천군", "횡성군", "영월군",
                                                "평창군", "정선군", "철원군", "화천군", "양구군",
                                                "인제군", "고성군", "양양군", "청주시", "충주시",
                                                "제천시", "보은군", "옥천군", "영동군", "증평군",
                                                "진천군", "괴산군", "음성군", "단양군", "천안시",
                                                "공주시", "보령시", "아산시", "서산시", "논산시",
                                                "계룡시", "당진시", "금산군", "부여군", "서천군",
                                                "청양군", "홍성군", "예산군", "태안군", "전주시",
                                                "군산시", "익산시", "정읍시", "남원시", "김제시",
                                                "완주군", "진안군", "무주군", "장수군", "임실군",
                                                "순창군", "고창군", "부안군", "목포시", "여수시",
                                                "순천시", "나주시", "광양시", "담양군", "곡성군",
                                                "구례군", "고흥군", "보성군", "화순군", "장흥군",
                                                "강진군", "해남군", "영암군", "무안군", "함평군",
                                                "영광군", "장성군", "완도군", "진도군", "신안군",
                                                "포항시", "경주시", "김천시", "안동시", "구미시",
                                                "영주시", "영천시", "상주시", "문경시", "경산시",
                                                "의성군", "청송군", "영양군", "영덕군", "청도군",
                                                "고령군", "성주군", "칠곡군", "예천군", "봉화군",
                                                "울진군", "울릉군", "창원시", "진주시", "통영시",
                                                "사천시", "김해시", "밀양시", "거제시", "양산시",
                                                "의령군", "함안군", "창녕군", "고성군", "남해군",
                                                "하동군", "산청군", "함양군", "거창군", "합천군",
                                                "제주시", "서귀포시"
                                            ],
                                            "description": "지방자치단체명. 특별시/광역시: '서울특별시', '부산광역시', '대구광역시', '인천광역시', '광주광역시', '대전광역시', '울산광역시', '세종특별자치시'. 도: '경기도', '강원특별자치도', '충청북도', '충청남도', '전북특별자치도', '전라남도', '경상북도', '경상남도', '제주특별자치도'. 주요 시/군도 포함. 생략 가능."
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
                                        }
                                    },
                                    "required": []
                                }
                            },
                            {
                                "name": "search_administrative_rule_tool",
                                "priority": 2,
                                "category": "administrative",
                                "description": "행정규칙을 검색합니다. 정부 부처의 행정규칙, 훈령, 예규, 고시를 검색할 수 있습니다. 예: '고용노동부 행정규칙', '국세청 훈령 검색'.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "query": {
                                            "type": "string",
                                            "description": "검색어 (행정규칙명 또는 키워드)"
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
                                        }
                                    },
                                    "required": []
                                }
                            }
                        ]
                        
                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": {
                                "tools": tools_list
                            }
                        }
                        response_json = json.dumps(response, ensure_ascii=False)
                        logger.info("MCP: tools/list response | length=%d tools_count=%d", 
                                   len(response_json), 
                                   len(tools_list))
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
                                req = SearchPrecedentRequest(
                                    query=query,
                                    page=page,
                                    per_page=per_page,
                                    court=court,
                                    date_from=date_from,
                                    date_to=date_to
                                )
                                logger.debug("Calling search_precedent | query=%s page=%d per_page=%d", query, page, per_page)
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
                            elif tool_name == "get_law_interpretation_tool":
                                interpretation_id = arguments.get("interpretation_id")
                                req = GetLawInterpretationRequest(interpretation_id=interpretation_id)
                                logger.debug("Calling get_law_interpretation | interpretation_id=%s", interpretation_id)
                                result = await law_interpretation_service.get_law_interpretation(req, None)
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
                                logger.debug("Calling get_committee_decision | committee_type=%s decision_id=%s", committee_type, decision_id)
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
                                logger.debug("Calling get_special_administrative_appeal | tribunal_type=%s appeal_id=%s", tribunal_type, appeal_id)
                                result = await special_administrative_appeal_service.get_special_administrative_appeal(req, None)
                            elif tool_name == "compare_laws_tool":
                                law_name = arguments.get("law_name")
                                compare_type = arguments.get("compare_type", "신구법")
                                req = CompareLawsRequest(
                                    law_name=law_name,
                                    compare_type=compare_type
                                )
                                logger.debug("Calling compare_laws | law_name=%s compare_type=%s", law_name, compare_type)
                                result = await law_comparison_service.compare_laws(req, None)
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
                        def clean_for_json(obj):
                            """JSON 직렬화를 위해 데이터 정리"""
                            if isinstance(obj, dict):
                                return {k: clean_for_json(v) for k, v in obj.items()}
                            elif isinstance(obj, list):
                                return [clean_for_json(item) for item in obj]
                            elif isinstance(obj, str):
                                # 제어 문자 제거 (줄바꿈, 탭 등은 공백으로 변환)
                                cleaned = obj.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
                                # 연속된 공백을 하나로
                                cleaned = ' '.join(cleaned.split())
                                return cleaned
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

