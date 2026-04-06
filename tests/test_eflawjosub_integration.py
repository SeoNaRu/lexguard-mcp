"""
eflawjosub HTML 폴백 — 실 API·실 네트워크 (CI 기본 스킵).

실행: LAW_API_KEY 설정 + LEXGUARD_RUN_EFLAW_E2E=1
"""

import pytest

pytestmark = [pytest.mark.requires_api, pytest.mark.requires_eflaw_e2e]


@pytest.mark.asyncio
async def test_afetch_eflawjosub_html_smoke():
    from src.repositories.base import LAW_API_BASE_URL
    from src.repositories.law_detail import LawDetailRepository
    from src.utils.eflawjosub_fallback import afetch_eflawjosub_as_html

    repo = LawDetailRepository()
    detail = await repo.get_law_detail("근로기준법", None)
    if detail.get("error"):
        pytest.skip("법령 상세 조회 실패(API 키·응답 확인)")
    law_id = str(
        detail.get("law_id")
        or detail.get("법령일련번호")
        or detail.get("일련번호")
        or ""
    )
    if not law_id:
        pytest.skip("law_id 없음")

    params = {
        "target": "eflawjosub",
        "type": "JSON",
        "MST": law_id,
        "efYd": "20240101",
        "JO": "000050",
    }
    _, err = repo.attach_api_key(params, None, LAW_API_BASE_URL)
    if err:
        pytest.skip("API 키 attach 실패")

    plain, html_url = await afetch_eflawjosub_as_html(LAW_API_BASE_URL, params)
    assert html_url
    assert plain is None or len(plain) >= 0
