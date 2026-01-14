#!/usr/bin/env python3
"""
한국 법령 MCP 서버 using FastMCP
국가법령정보센터(law.go.kr) API 연동 MCP 서버
Streamable HTTP 방식 지원

레이어드 아키텍처 적용:
- Routes → Services → Repositories
"""
import sys
import os
from .config.settings import setup_logging, get_api
from .services.law_service import LawService
from .services.health_service import HealthService
from .routes.mcp_routes import register_mcp_routes
from .routes.http_routes import register_http_routes

# 로깅 설정
logger = setup_logging()

# FastAPI 앱 초기화
api = get_api()

# Service 인스턴스 생성
law_service = LawService()
health_service = HealthService()

# Routes 등록
register_mcp_routes(api, law_service, health_service)
register_http_routes(api, law_service, health_service)


if __name__ == "__main__":
    # Streamable HTTP 모드로 실행 (MCP 규칙 준수)
    import uvicorn
    port = int(os.environ.get('PORT', 8099))
    
    print("한국 법령 MCP 서버 시작 중...", file=sys.stderr)
    print("서버: lexguard-mcp-service", file=sys.stderr)
    print("전송 방식: Streamable HTTP", file=sys.stderr)
    print(f"포트: {port}", file=sys.stderr)
    print("사용 가능한 도구: health, search_law_tool, get_law_tool", file=sys.stderr)
    print("MCP 엔드포인트: POST /mcp", file=sys.stderr)
    print(f"로컬 테스트: http://localhost:{port}/mcp", file=sys.stderr)
    
    # 개발 환경에서는 reload=True로 설정 (코드 변경 시 자동 재시작)
    # 프로덕션에서는 환경 변수로 reload=False 설정
    reload = os.environ.get('RELOAD', 'true').lower() == 'true'
    uvicorn.run("src.main:api", host="0.0.0.0", port=port, reload=reload)
