"""
로컬/스테이징 스모크: eflawjosub HTML 폴백 URL·응답 확인.

  set LAW_API_KEY
  set LEXGUARD_EFLAWJOSUB_FALLBACK=html   (선택, 본 스크립트는 afetch만 호출)
  python scripts/smoke_eflawjosub_fallback.py

LEXGUARD_SMOKE_MST / LEXGUARD_SMOKE_JO / LEXGUARD_SMOKE_EF_YD 로 파라미터 오버라이드 가능.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.repositories.base import LAW_API_BASE_URL  # noqa: E402
from src.repositories.law_detail import LawDetailRepository  # noqa: E402
from src.utils.eflawjosub_fallback import afetch_eflawjosub_as_html  # noqa: E402


async def main() -> int:
    key = os.environ.get("LAW_API_KEY") or os.environ.get("LAWGOKR_OC")
    if not key or not str(key).strip():
        print("LAW_API_KEY 또는 LAWGOKR_OC 필요", file=sys.stderr)
        return 2

    mst = os.environ.get("LEXGUARD_SMOKE_MST")
    jo = os.environ.get("LEXGUARD_SMOKE_JO", "000050")
    ef_yd = os.environ.get("LEXGUARD_SMOKE_EF_YD", "20240101")

    repo = LawDetailRepository()
    if not mst:
        d = await repo.get_law_detail("근로기준법", None)
        if d.get("error"):
            print("get_law_detail 실패:", d.get("error"), file=sys.stderr)
            return 1
        mst = str(d.get("law_id") or d.get("법령일련번호") or d.get("일련번호") or "")
    if not mst:
        print("MST 없음", file=sys.stderr)
        return 1

    params = {
        "target": "eflawjosub",
        "type": "JSON",
        "MST": mst,
        "efYd": ef_yd,
        "JO": jo,
    }
    _, err = repo.attach_api_key(params, None, LAW_API_BASE_URL)
    if err:
        print("attach_api_key:", err, file=sys.stderr)
        return 1

    plain, url = await afetch_eflawjosub_as_html(LAW_API_BASE_URL, params)
    print("url:", url)
    print("plain_len:", len(plain) if plain else 0)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
