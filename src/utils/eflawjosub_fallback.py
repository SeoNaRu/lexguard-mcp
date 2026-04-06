"""
eflawjosub(JSON) 빈 조문 응답 시 보조 조회.

- html: 동일 파라미터로 type=HTML 요청 후 본문 텍스트 추출 (공유 AsyncClient).
- playwright: HTML이 부족할 때 headless Chromium으로 동일 URL 로드 (선택 의존성).

운영 시 메모리·브라우저 바이너리·국가법령정보센터 이용약관을 검토한 뒤 활성화할 것.
"""
from __future__ import annotations

import html as html_module
import logging
import os
import re
from typing import Any, Optional

from .http_client import aget

logger = logging.getLogger("lexguard-mcp")

_TAG_RE = re.compile(r"<[^>]+>", re.DOTALL)
_WS_RE = re.compile(r"\s+")


def _fallback_mode() -> str:
    """LEXGUARD_EFLAWJOSUB_FALLBACK: ''(끔), 'html', 'playwright'(html 후 브라우저)."""
    return (os.environ.get("LEXGUARD_EFLAWJOSUB_FALLBACK") or "").strip().lower()


def _strip_html_to_text(raw: str) -> str:
    if not raw:
        return ""
    text = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", raw)
    text = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", text)
    text = _TAG_RE.sub(" ", text)
    text = html_module.unescape(text)
    text = _WS_RE.sub(" ", text).strip()
    return text


def _html_response_usable(text: str) -> bool:
    if len(text) < 80:
        return False
    lower = text.lower()
    if "error" in lower and len(text) < 400:
        return False
    return True


async def afetch_eflawjosub_as_html(
    law_api_base_url: str,
    params_template: dict[str, Any],
    timeout: float = 15.0,
) -> tuple[Optional[str], Optional[str]]:
    """eflawjosub 동일 파라미터로 type=HTML GET (비동기)."""
    params = {**params_template, "type": "HTML"}
    try:
        resp = await aget(law_api_base_url, params=params, timeout=timeout)
        if resp.status_code >= 400:
            logger.debug("eflawjosub HTML fallback | status=%s", resp.status_code)
            return None, str(resp.url)
        raw = resp.text or ""
        plain = _strip_html_to_text(raw)
        if not _html_response_usable(plain):
            return None, str(resp.url)
        return plain, str(resp.url)
    except Exception as e:
        logger.info("eflawjosub HTML fallback failed | error=%s", e)
        return None, None


def fetch_via_playwright(url: str, timeout_ms: int = 45_000) -> Optional[str]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.warning("Playwright 미설치: pip install playwright 후 playwright install chromium")
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                page.wait_for_timeout(800)
                body = page.inner_text("body")
            finally:
                browser.close()
        plain = _strip_html_to_text(body or "")
        return plain if _html_response_usable(plain) else None
    except Exception as e:
        logger.info("eflawjosub Playwright fallback failed | error=%s", e)
        return None


async def atry_recover_article_text(
    law_api_base_url: str,
    json_params: dict[str, Any],
) -> tuple[Optional[str], Optional[str], str]:
    """
    JSON 조문 본문이 비었을 때 복구 시도.

    Returns:
        (text, source_url, mode_used)
        mode_used: 'none' | 'html' | 'playwright'
    """
    mode = _fallback_mode()
    if mode not in ("html", "playwright"):
        return None, None, "none"

    plain, html_url = await afetch_eflawjosub_as_html(law_api_base_url, json_params)
    if plain:
        return plain, html_url, "html"

    if mode == "playwright" and html_url:
        pw_text = fetch_via_playwright(html_url)
        if pw_text:
            return pw_text, html_url, "playwright"

    return None, html_url, mode
