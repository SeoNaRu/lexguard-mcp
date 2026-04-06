"""sanitize_http_headers_for_log 단위 테스트"""
from starlette.datastructures import Headers

from src.utils.log_sanitize import sanitize_http_headers_for_log


def test_masks_authorization_and_cookie():
    h = Headers(
        {
            "Authorization": "Bearer secret-token",
            "Cookie": "session=abc",
            "Content-Type": "application/json",
        }
    )
    out = sanitize_http_headers_for_log(h)
    assert out["authorization"] == "<redacted>"
    assert out["cookie"] == "<redacted>"
    assert out["content-type"] == "application/json"


def test_masks_mcp_session_id():
    h = Headers({"Mcp-Session-Id": "sess-value-123"})
    out = sanitize_http_headers_for_log(h)
    assert out.get("mcp-session-id") == "<redacted>"
