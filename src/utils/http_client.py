"""
HTTP Client 유틸리티 - httpx 기반 중앙 HTTP 클라이언트

동기(Sync): 기존 Repository 코드와 drop-in 호환 (requests 대체)
비동기(Async): 신규 코드에서 asyncio 환경에서 사용
"""
import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("lexguard-mcp")

# 공통 타임아웃 설정
_DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)

# 공통 헤더
_DEFAULT_HEADERS = {
    "Accept": "application/json, text/xml, */*",
    "User-Agent": "LexGuardMcp/1.0",
}


# ────────────────────────────────────────────────────────────────
# 동기 클라이언트 (기존 Repository 의 requests.get() 대체용)
# ────────────────────────────────────────────────────────────────

def sync_get(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    timeout: float = 30.0,
    **kwargs,
) -> httpx.Response:
    """
    동기 GET 요청 (requests.get() drop-in 대체).
    
    기존 Repository 코드에서 `requests.get()` → `sync_get()` 으로
    교체만 하면 동일하게 동작합니다.
    """
    with httpx.Client(
        timeout=httpx.Timeout(timeout),
        headers=_DEFAULT_HEADERS,
        follow_redirects=True,
    ) as client:
        response = client.get(url, params=params, **kwargs)
        response.raise_for_status()
        return response


# ────────────────────────────────────────────────────────────────
# 비동기 클라이언트 싱글톤 (신규 async 코드용)
# ────────────────────────────────────────────────────────────────

_async_client: Optional[httpx.AsyncClient] = None


def get_async_client() -> httpx.AsyncClient:
    """
    애플리케이션 공유 AsyncClient 반환 (싱글톤).
    FastAPI lifespan 이벤트에서 초기화/정리를 권장합니다.
    """
    global _async_client
    if _async_client is None or _async_client.is_closed:
        _async_client = httpx.AsyncClient(
            timeout=_DEFAULT_TIMEOUT,
            headers=_DEFAULT_HEADERS,
            follow_redirects=True,
        )
    return _async_client


async def async_get(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    timeout: Optional[float] = None,
    **kwargs,
) -> httpx.Response:
    """
    비동기 GET 요청. async 환경에서 asyncio.to_thread() 없이 직접 사용.
    """
    client = get_async_client()
    req_kwargs: Dict[str, Any] = {"params": params, **kwargs}
    if timeout is not None:
        req_kwargs["timeout"] = timeout
    response = await client.get(url, **req_kwargs)
    response.raise_for_status()
    return response


async def close_async_client() -> None:
    """공유 AsyncClient 닫기 (FastAPI shutdown lifespan 에서 호출)."""
    global _async_client
    if _async_client and not _async_client.is_closed:
        await _async_client.aclose()
        _async_client = None
        logger.debug("AsyncClient closed")
