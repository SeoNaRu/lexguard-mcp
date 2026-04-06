"""
설정 관리
로깅, FastAPI, FastMCP 앱 초기화
"""
from typing import Any

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import FastMCP
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# Load .env file
load_dotenv()

# Rate Limiter 싱글톤 (지연 초기화 - import 타임 .env 충돌 방지)
_limiter: "Limiter | None" = None


def get_limiter() -> Limiter:
    """Rate Limiter 싱글톤 반환 (처음 호출 시 초기화)."""
    global _limiter
    if _limiter is None:
        _limiter = Limiter(
            key_func=get_remote_address,
            default_limits=["60/minute"],
            # starlette Config가 .env 파일을 다시 읽지 않도록 storage_uri 명시
            storage_uri="memory://",
        )
    return _limiter


def setup_logging() -> logging.Logger:
    """로깅 설정"""
    logger = logging.getLogger("lexguard-mcp")
    level = getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
        logger.addHandler(handler)
    logger.propagate = True
    return logger


def get_api() -> FastAPI:
    """FastAPI 앱 인스턴스 반환"""
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """서버 시작/종료 시 실행되는 lifespan 이벤트"""
        logger = logging.getLogger("lexguard-mcp")
        logger.info("LexGuard MCP 서버 시작")
        yield
        # 비동기 HTTP 클라이언트 정리
        from ..utils.http_client import close_async_client
        await close_async_client()
        logger.info("LexGuard MCP 서버 종료")

    api = FastAPI(lifespan=lifespan)

    # Rate Limiter 등록
    _lim = get_limiter()
    api.state.limiter = _lim
    api.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    api.add_middleware(SlowAPIMiddleware)

    # CORS 설정 추가 (Cursor 등 클라이언트에서 접근 가능하도록)
    api.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 개발 환경에서는 모든 origin 허용
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return api


def get_mcp() -> FastMCP:
    """FastMCP 인스턴스 반환"""
    return FastMCP[Any]()

