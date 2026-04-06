"""eflawjosub 폴백 유틸 순수 로직 테스트 (네트워크 없음)."""

from unittest.mock import AsyncMock, patch

import pytest

from src.utils.eflawjosub_fallback import (
    _fallback_mode,
    _strip_html_to_text,
    afetch_eflawjosub_as_html,
)


def test_strip_html_to_text_basic():
    raw = "<html><body><p>근로자는 <b>휴게</b>를 가진다.</p></body></html>"
    t = _strip_html_to_text(raw)
    assert "근로자" in t
    assert "<" not in t


def test_fallback_mode_reads_env(monkeypatch):
    monkeypatch.delenv("LEXGUARD_EFLAWJOSUB_FALLBACK", raising=False)
    assert _fallback_mode() == ""
    monkeypatch.setenv("LEXGUARD_EFLAWJOSUB_FALLBACK", "HTML")
    assert _fallback_mode() == "html"
    monkeypatch.setenv("LEXGUARD_EFLAWJOSUB_FALLBACK", "Playwright")
    assert _fallback_mode() == "playwright"


@pytest.mark.asyncio
async def test_afetch_eflawjosub_as_html_404():
    class _Resp:
        status_code = 404
        url = "https://example.invalid/law"
        text = ""

    with patch(
        "src.utils.eflawjosub_fallback.aget",
        new_callable=AsyncMock,
        return_value=_Resp(),
    ):
        plain, url = await afetch_eflawjosub_as_html(
            "https://example.invalid", {"target": "eflawjosub"}
        )
        assert plain is None
        assert "example" in (url or "")
