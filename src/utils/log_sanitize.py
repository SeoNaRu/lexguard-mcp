"""
HTTP 헤더 로깅용 마스킹 (전체 시크릿 노출 방지)
"""


def sanitize_http_headers_for_log(headers) -> dict:
    """
    Starlette/FastAPI Headers 또는 (key, value) 매핑을 로그에 넣기 안전한 dict로 변환합니다.
    Authorization, Cookie, 세션·토큰류는 값을 남기지 않습니다.
    """
    sensitive_exact = frozenset(
        {
            "authorization",
            "proxy-authorization",
            "cookie",
            "set-cookie",
            "x-api-key",
            "x-auth-token",
            "x-real-ip",
            "mcp-session-id",
        }
    )
    out: dict = {}
    try:
        items = headers.items() if hasattr(headers, "items") else []
    except Exception:
        return {"_error": "headers not iterable"}
    for k, v in items:
        try:
            lk = k.lower() if isinstance(k, str) else str(k).lower()
        except Exception:
            lk = ""
        if (
            lk in sensitive_exact
            or "token" in lk
            or "secret" in lk
            or lk.endswith("-key")
            or "session-id" in lk
        ):
            out[k] = "<redacted>"
        else:
            out[k] = v
    return out
