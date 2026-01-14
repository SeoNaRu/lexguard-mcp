"""
HTTP Routes - 일반 HTTP 엔드포인트
Controller 패턴: 요청을 받아 Service를 호출
"""
from fastapi import FastAPI
from ..services.law_service import LawService
from ..services.health_service import HealthService
from ..models import SearchLawRequest, ListLawNamesRequest, GetLawDetailRequest
from contextlib import contextmanager
import os
import logging

logger = logging.getLogger("lexguard-mcp")


@contextmanager
def temporary_env(overrides: dict):
    """임시 환경 변수 설정 컨텍스트 매니저"""
    saved_values = {}
    try:
        for key, value in (overrides or {}).items():
            saved_values[key] = os.environ.get(key)
            if value is not None:
                os.environ[key] = str(value)
        yield
    finally:
        for key, original in saved_values.items():
            if original is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original


def register_http_routes(api: FastAPI, law_service: LawService, health_service: HealthService):
    """HTTP 엔드포인트 등록"""
    
    @api.get("/")
    @api.head("/")
    async def root():
        """루트 경로 - Render 포트 감지 및 서버 정보"""
        return {
            "service": "LexGuard MCP",
            "status": "running",
            "endpoints": {
                "health": "/health",
                "mcp": "/mcp",
                "tools": "/tools"
            },
            "message": "한국 법령 MCP 서버가 정상적으로 실행 중입니다."
        }
    
    @api.get("/health")
    async def health_check_get():
        """HTTP GET endpoint: Health check"""
        return await health_service.check_health()
    
    @api.post("/health")
    async def health_check_post():
        """HTTP POST endpoint: Health check"""
        return await health_service.check_health()
    
    @api.get("/tools")
    async def get_tools_http():
        """HTTP endpoint: Get list of available tools"""
        try:
            tools_list = [
                {
                    "name": "health",
                    "description": "서비스 상태 확인 (API 키 설정 등)",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                },
                {
                    "name": "search_law_tool",
                    "description": "법령을 검색합니다 (법령명 또는 키워드로 검색)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "법령 검색어"},
                            "page": {"type": "integer", "description": "페이지 번호 (기본값: 1)"},
                            "per_page": {"type": "integer", "description": "페이지당 결과 수 (기본값: 10, 최대: 50)"}
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "list_law_names_tool",
                    "description": "법령명 목록을 조회합니다 (전체 법령명 목록 또는 검색어로 필터링)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "page": {"type": "integer", "description": "페이지 번호 (기본값: 1)"},
                            "per_page": {"type": "integer", "description": "페이지당 결과 수 (기본값: 50, 최대: 100)"},
                            "query": {"type": "string", "description": "검색어 (법령명으로 필터링, 선택사항)"}
                        },
                        "required": []
                    }
                },
                {
                    "name": "get_law_detail_tool",
                    "description": "법령 상세 정보를 조회합니다 (법령명으로 검색하여 상세 정보 조회)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "law_name": {"type": "string", "description": "법령명 (예: '119구조·구급에 관한 법률 시행령')"}
                        },
                        "required": ["law_name"]
                    }
                }
            ]
            
            return tools_list
        except Exception as e:
            logger.exception("Error getting tools list: %s", str(e))
            return []
    
    @api.post("/tools/{tool_name}")
    async def call_tool_http(tool_name: str, request_data: dict):
        """HTTP endpoint: Call tool"""
        logger.debug("HTTP call_tool | tool=%s request=%s", tool_name, request_data)
        env = request_data.get("env", {}) if isinstance(request_data, dict) else {}
        
        def convert_float_to_int(data: dict, keys: list):
            """Convert float values to int for specified keys"""
            for key in keys:
                if key in data and isinstance(data[key], float):
                    data[key] = int(data[key])
        
        try:
            creds = {}
            law_keys = ["LAW_API_KEY"]
            if isinstance(env, dict):
                for key in law_keys:
                    if key in env:
                        creds[key] = env[key]
            
            if creds:
                masked = dict(creds)
                for key in masked:
                    if masked[key]:
                        masked[key] = masked[key][:6] + "***"
                logger.debug("Applying temp env | %s", masked)
            
            async def run_with_env(coro_func):
                with temporary_env(creds):
                    return await coro_func
            
            if tool_name == "health":
                return await health_service.check_health()
            
            if tool_name == "search_law_tool":
                query = request_data.get("query")
                if not query:
                    return {
                        "error": "필수 파라미터 누락: query",
                        "recovery_guide": "검색어(query)를 입력해주세요."
                    }
                page = request_data.get("page", 1)
                per_page = request_data.get("per_page", 10)
                convert_float_to_int(request_data, ["page", "per_page"])
                req = SearchLawRequest(query=query, page=page, per_page=per_page)
                return await run_with_env(
                    law_service.search_law(req, arguments=request_data)
                )
            
            if tool_name == "list_law_names_tool":
                page = request_data.get("page", 1)
                per_page = request_data.get("per_page", 50)
                query = request_data.get("query")
                convert_float_to_int(request_data, ["page", "per_page"])
                req = ListLawNamesRequest(page=page, per_page=per_page, query=query)
                return await run_with_env(
                    law_service.list_law_names(req, arguments=request_data)
                )
            
            if tool_name == "get_law_detail_tool":
                law_name = request_data.get("law_name")
                if not law_name:
                    return {
                        "error": "필수 파라미터 누락: law_name",
                        "recovery_guide": "법령명(law_name)을 입력해주세요. 예: '형법', '민법', '개인정보보호법'"
                    }
                req = GetLawDetailRequest(law_name=law_name)
                return await run_with_env(
                    law_service.get_law_detail(req, arguments=request_data)
                )
            
            return {
                "error": "도구를 찾을 수 없습니다",
                "recovery_guide": "요청한 도구가 존재하지 않습니다. 사용 가능한 도구 목록을 확인하세요."
            }
        except Exception as e:
            logger.exception("Error in call_tool_http: %s", str(e))
            return {
                "error": f"도구 호출 중 오류 발생: {str(e)}",
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }

