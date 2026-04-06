"""
HTTP Client 유틸리티 - httpx 기반 중앙 HTTP 클라이언트

동기(Sync): Repository 의 requests.get() 대체 (기본은 status 무시, requests 와 동일)
비동기(Async): asyncio 환경에서 async_get 사용
"""
import threading
import httpx
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("lexguard-mcp")

_DEFAULT_TIMEOUT = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)

_DEFAULT_HEADERS = {
    "Accept": "application/json, text/xml, */*",
    "User-Agent": "LexGuardMcp/1.0",
}

_sync_client: Optional[httpx.Client] = None
_sync_lock = threading.Lock()


def _get_sync_client() -> httpx.Client:
    """프로세스당 공유 Sync 클라이언트 (연결 재사용)."""
    global _sync_client
    with _sync_lock:
        if _sync_client is None or _sync_client.is_closed:
            _sync_client = httpx.Client(
                timeout=_DEFAULT_TIMEOUT,
                headers=_DEFAULT_HEADERS,
                follow_redirects=True,
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
            )
        return _sync_client


def close_sync_client() -> None:
    """공유 Sync 클라이언트 종료 (테스트·앱 shutdown)."""
    global _sync_client
    with _sync_lock:
        if _sync_client is not None and not _sync_client.is_closed:
            _sync_client.close()
        _sync_client = None
        logger.debug("Sync httpx Client closed")


def sync_get(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    timeout: Optional[float] = None,
    raise_for_status: bool = False,
    **kwargs: Any,
) -> httpx.Response:
    """
    동기 GET. requests.get() 과 같이 기본적으로 HTTP 에러 시 예외를 내지 않음.
    validate_drf_response 이후에 response.raise_for_status() 호출하는 기존 흐름 유지.
    """
    client = _get_sync_client()
    req_timeout: Any = timeout if timeout is not None else _DEFAULT_TIMEOUT
    response = client.get(url, params=params, timeout=req_timeout, **kwargs)
    if raise_for_status:
        response.raise_for_status()
    return response


_async_client: Optional[httpx.AsyncClient] = None


def get_async_client() -> httpx.AsyncClient:
    global _async_client
    if _async_client is None or _async_client.is_closed:
        _async_client = httpx.AsyncClient(
            timeout=_DEFAULT_TIMEOUT,
            headers=_DEFAULT_HEADERS,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
        )
    return _async_client


async def aget(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    timeout: Optional[float] = None,
    raise_for_status: bool = False,
    **kwargs: Any,
) -> httpx.Response:
    """
    비동기 GET. sync_get 과 같이 기본적으로 HTTP 에러 시 예외를 내지 않음.
    Repository 전면 async 전환 시 공유 AsyncClient 로 연결 재사용.
    """
    client = get_async_client()
    req_timeout: Any = timeout if timeout is not None else _DEFAULT_TIMEOUT
    response = await client.get(url, params=params, timeout=req_timeout, **kwargs)
    if raise_for_status:
        response.raise_for_status()
    return response


async def async_get(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    timeout: Optional[float] = None,
    **kwargs: Any,
) -> httpx.Response:
    client = get_async_client()
    req_kwargs: Dict[str, Any] = {"params": params, **kwargs}
    if timeout is not None:
        req_kwargs["timeout"] = timeout
    response = await client.get(url, **req_kwargs)
    response.raise_for_status()
    return response


async def close_async_client() -> None:
    global _async_client
    if _async_client and not _async_client.is_closed:
        await _async_client.aclose()
        _async_client = None
        logger.debug("AsyncClient closed")
