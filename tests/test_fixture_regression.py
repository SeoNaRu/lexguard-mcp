"""
응답 형태 회귀 테스트 인프라.

`tests/fixtures/api_responses/` 의 실제 API 응답 JSON을 로드해서 repository →
tool 출력 변환이 일관되게 동작하는지 검증한다. API 응답 모양이 미묘하게 바뀌었을
때 (필드 추가/제거, 배열↔dict 토글 등) 회귀를 즉시 잡는 것이 목적.
"""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.repositories.law_detail import LawDetailRepository


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "api_responses"


def load_fixture(name: str) -> dict:
    """fixtures/api_responses/{name} 을 JSON으로 로드."""
    path = FIXTURES_DIR / name
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def make_mock_response(body: dict, status_code: int = 200) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.headers = {"Content-Type": "application/json"}
    mock_resp.text = json.dumps(body, ensure_ascii=False)
    mock_resp.json = MagicMock(return_value=body)
    mock_resp.url = "https://www.law.go.kr/DRF/lawService.do"
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


# ---------------------------------------------------------------------------
# 인프라 단위 — fixture 로드 자체 검증
# ---------------------------------------------------------------------------


def test_fixtures_directory_exists():
    assert FIXTURES_DIR.is_dir(), f"fixtures dir missing: {FIXTURES_DIR}"


def test_all_fixture_files_load_as_valid_json():
    """fixtures/api_responses/ 안의 모든 .json은 파싱 가능해야 한다."""
    files = list(FIXTURES_DIR.glob("*.json"))
    assert len(files) >= 5, f"최소 5개 fixture 필요, 현재 {len(files)}개"
    for f in files:
        with f.open(encoding="utf-8") as fh:
            data = json.load(fh)
        assert isinstance(data, dict), f"{f.name}: top-level은 dict여야 함"


# ---------------------------------------------------------------------------
# eflawjosub 응답 변형 — _select_article_unit + 본문 추출 회귀
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fixture_eflawjosub_53_single_article_returns_body():
    """53조 형태: 조문단위가 단일 원소 배열 → 항 본문 합쳐서 반환."""
    fixture = load_fixture("eflawjosub_53_single_article.json")
    repo = LawDetailRepository()

    async def fake_aget(url, params=None, timeout=None):
        return make_mock_response(fixture)

    with patch("src.repositories.law_detail.aget", side_effect=fake_aget):
        result = await repo.get_single_article(
            law_id="001872",
            article_number="53",
            arguments={"env": {"LAW_API_KEY": "testkey123"}},
        )

    content = result.get("content") or ""
    assert "연장 근로의 제한" in content or "12시간" in content
    assert "조문 내용을 찾을 수 없습니다" not in content


@pytest.mark.asyncio
async def test_fixture_eflawjosub_50_chapter_then_body_picks_body():
    """50조 형태: [장 헤더, 본문] → 장 헤더가 아니라 본문 항 내용 반환."""
    fixture = load_fixture("eflawjosub_50_chapter_then_body.json")
    repo = LawDetailRepository()

    async def fake_aget(url, params=None, timeout=None):
        return make_mock_response(fixture)

    with patch("src.repositories.law_detail.aget", side_effect=fake_aget):
        result = await repo.get_single_article(
            law_id="001872",
            article_number="50",
            arguments={"env": {"LAW_API_KEY": "testkey123"}},
        )

    content = result.get("content") or ""
    assert "제4장 근로시간과 휴식" not in content, "장 헤더가 본문으로 새어 들어옴"
    assert "40시간" in content, f"본문 항이 누락됨: {content!r}"


@pytest.mark.asyncio
async def test_fixture_eflawjosub_with_jomun_content_returns_content():
    """조문단위가 dict인 옛 형태 + 조문내용 필드 → 그대로 반환."""
    fixture = load_fixture("eflawjosub_with_jomun_content.json")
    repo = LawDetailRepository()

    async def fake_aget(url, params=None, timeout=None):
        return make_mock_response(fixture)

    with patch("src.repositories.law_detail.aget", side_effect=fake_aget):
        result = await repo.get_single_article(
            law_id="001003",
            article_number="103",
            arguments={"env": {"LAW_API_KEY": "testkey123"}},
        )

    content = result.get("content") or ""
    assert "선량한 풍속" in content


@pytest.mark.asyncio
async def test_fixture_eflawjosub_chapter_only_returns_fallback_header():
    """본문이 없고 장 헤더만 있는 경우(이상한 응답) → 최후 fallback으로 헤더라도 반환되도록."""
    fixture = load_fixture("eflawjosub_chapter_only.json")
    repo = LawDetailRepository()

    async def fake_aget(url, params=None, timeout=None):
        return make_mock_response(fixture)

    with patch("src.repositories.law_detail.aget", side_effect=fake_aget):
        result = await repo.get_single_article(
            law_id="001872",
            article_number="50",
            arguments={"env": {"LAW_API_KEY": "testkey123"}},
        )

    content = result.get("content") or ""
    assert "제4장 근로시간과 휴식" in content or "조문 내용을 찾을 수 없습니다" in content


@pytest.mark.asyncio
async def test_fixture_eflawjosub_real_53_prefers_hang_over_jomun_content_when_hang_present():
    """조문내용 필드가 '제53조(...)' 제목 형태이고 항이 진짜 본문인 경우 → 항 합치기 우선.

    회귀 방지: 라이브 응답에서 조문내용에는 제목 정도만 담기고 본문은 항 배열에
    있는 패턴이 관찰됨. 그 경우 조문내용을 본문으로 채택해서는 안 됨.
    """
    fixture = load_fixture("eflawjosub_real_53_jomun_alias.json")
    repo = LawDetailRepository()

    async def fake_aget(url, params=None, timeout=None):
        return make_mock_response(fixture)

    with patch("src.repositories.law_detail.aget", side_effect=fake_aget):
        result = await repo.get_single_article(
            law_id="001872",
            article_number="53",
            arguments={"env": {"LAW_API_KEY": "testkey123"}},
        )

    content = result.get("content") or ""
    assert "당사자 간에 합의하면" in content, f"항 본문이 누락됨: {content!r}"
    assert "12시간" in content


@pytest.mark.asyncio
async def test_fixture_eflawjosub_real_50_uses_jomun_alias_key():
    """실제 law.go.kr 응답 구조: 법령.조문.조문단위 (조문정보 아님). 같은 흐름으로 본문 추출."""
    fixture = load_fixture("eflawjosub_real_50_chapter_then_body.json")
    repo = LawDetailRepository()

    async def fake_aget(url, params=None, timeout=None):
        return make_mock_response(fixture)

    with patch("src.repositories.law_detail.aget", side_effect=fake_aget):
        result = await repo.get_single_article(
            law_id="001872",
            article_number="50",
            arguments={"env": {"LAW_API_KEY": "testkey123"}},
        )

    content = result.get("content") or ""
    assert "제4장 근로시간과 휴식" not in content, "조문 alias 경로에서도 장 헤더가 새어 들어오면 안 됨"
    assert "40시간" in content, f"본문 누락 (실제 구조 키): {content!r}"


@pytest.mark.asyncio
async def test_fixture_eflawjosub_empty_response_handled_gracefully():
    """조문단위가 빈 배열 → 에러 없이 'not found' 메시지로 fallback."""
    fixture = load_fixture("eflawjosub_empty_response.json")
    repo = LawDetailRepository()

    async def fake_aget(url, params=None, timeout=None):
        return make_mock_response(fixture)

    with patch("src.repositories.law_detail.aget", side_effect=fake_aget):
        result = await repo.get_single_article(
            law_id="001872",
            article_number="999",
            arguments={"env": {"LAW_API_KEY": "testkey123"}},
        )

    assert isinstance(result, dict)
    assert "law_id" in result
    content = result.get("content") or ""
    assert content == "조문 내용을 찾을 수 없습니다." or content == ""


# ---------------------------------------------------------------------------
# response_formatter — fixture 기반 변환 회귀
# ---------------------------------------------------------------------------


def test_fixture_law_comparison_empty_passes_through_format_search_response():
    """빈 비교 응답 → format_search_response가 missing_reason을 부여하는지 fixture로 검증."""
    from src.utils.response_formatter import format_search_response

    raw = {
        "law_name": "형법",
        "compare_type": "3단비교",
        "comparison": {},
        "api_url": "https://x.com/?OC=LongApiKey1234",
    }
    formatted = format_search_response(raw, "law_comparison_tool")
    assert formatted["success"] is False
    assert formatted["missing_reason"] == "EMPTY_COMPARISON"


def test_fixture_law_comparison_nonempty_marks_success():
    from src.utils.response_formatter import format_search_response

    raw = {
        "law_name": "근로기준법",
        "compare_type": "신구법",
        "comparison": {"OldAndNewService": {"신조문목록": {"조문": [{"content": "..."}]}}},
        "api_url": "https://x.com/?OC=LongApiKey1234",
    }
    formatted = format_search_response(raw, "law_comparison_tool")
    assert formatted["success"] is True
    assert "missing_reason" not in formatted
