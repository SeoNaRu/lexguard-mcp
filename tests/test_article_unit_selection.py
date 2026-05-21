"""
LawDetailRepository._select_article_unit — 조문단위 배열에서 실제 조 본문 선택 검증.

배경: 장의 첫 조항(예: 근로기준법 50조, 민법 750조)을 조회하면 law.go.kr API가
조문단위를 [장 헤더(조문여부="전문", 항 없음), 조 본문(항 포함)] 형태의 배열로 반환한다.
이전 구현은 무조건 배열의 첫 원소를 사용하여 장 헤더만 잡혔다.
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.repositories.law_detail import LawDetailRepository


# ---------------------------------------------------------------------------
# _select_article_unit 단위 테스트
# ---------------------------------------------------------------------------

def test_select_article_unit_returns_dict_unchanged():
    """dict이 직접 들어오면 그대로 반환 (배열로 감싸지 않은 응답 호환)."""
    unit = {"조문번호": "53", "항": [{"항번호": "①"}]}
    assert LawDetailRepository._select_article_unit(unit) is unit


def test_select_article_unit_returns_none_for_none():
    """None 입력은 None."""
    assert LawDetailRepository._select_article_unit(None) is None


def test_select_article_unit_returns_none_for_empty_list():
    """빈 리스트는 None."""
    assert LawDetailRepository._select_article_unit([]) is None


def test_select_article_unit_single_element_list():
    """원소 하나짜리 리스트는 그 원소를 반환 (53조 같은 일반 케이스)."""
    unit = {"조문번호": "53", "항": [{"항번호": "①", "항내용": "..."}]}
    assert LawDetailRepository._select_article_unit([unit]) is unit


def test_select_article_unit_skips_chapter_header_with_hang():
    """[장헤더, 조본문(항 포함)] → 항을 가진 두 번째 원소 선택. 50조 시나리오."""
    chapter_header = {
        "조문번호": "50",
        "조문여부": "전문",
        "조문키": "0050000",
        "조문내용": "제4장 근로시간과 휴식",
    }
    article_body = {
        "조문번호": "50",
        "조문키": "0050001",
        "항": [{"항번호": "① ", "항내용": "1주 간의 근로시간은 휴게시간을 제외하고 40시간을 초과할 수 없다."}],
    }
    selected = LawDetailRepository._select_article_unit([chapter_header, article_body])
    assert selected is article_body


def test_select_article_unit_skips_chapter_header_with_content_only():
    """항이 없어도, 장 헤더(조문여부=전문)는 스킵하고 내용 있는 원소 선택."""
    chapter_header = {
        "조문여부": "전문",
        "조문내용": "제5장 불법행위",
    }
    article_body = {
        "조문번호": "750",
        "조문내용": "고의 또는 과실로 인한 위법행위로 타인에게 손해를 가한 자는 그 손해를 배상할 책임이 있다.",
    }
    selected = LawDetailRepository._select_article_unit([chapter_header, article_body])
    assert selected is article_body


def test_select_article_unit_falls_back_to_first_when_all_chapter_headers():
    """모두 장 헤더처럼 보이고 항도 없으면 최후에 첫 원소 fallback (회귀 안전)."""
    a = {"조문여부": "전문", "조문내용": "제1장"}
    b = {"조문여부": "전문", "조문내용": "제2장"}
    selected = LawDetailRepository._select_article_unit([a, b])
    assert selected is a


def test_select_article_unit_ignores_non_dict_elements():
    """문자열·None 같은 비-dict 원소는 무시된다."""
    article = {"조문번호": "53", "항": [{"항번호": "①"}]}
    selected = LawDetailRepository._select_article_unit([None, "garbage", article])
    assert selected is article


# ---------------------------------------------------------------------------
# get_single_article 통합 — 50조 (장 첫 조항) 시뮬레이션
# ---------------------------------------------------------------------------

def _make_response(json_body: dict, status_code: int = 200):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.headers = {"Content-Type": "application/json"}
    mock_resp.text = json.dumps(json_body, ensure_ascii=False)
    mock_resp.json = MagicMock(return_value=json_body)
    mock_resp.url = "https://www.law.go.kr/DRF/lawService.do"
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


_DETAIL_BODY = {
    "법령": {
        "기본정보": {
            "법령명_한글": "근로기준법",
            "시행일자": "20251023",
            "법령ID": "001872",
        },
    }
}

_JOSUB_CHAPTER_THEN_BODY = {
    "법령": {
        "조문정보": {
            "조문단위": [
                {
                    "조문번호": "50",
                    "조문여부": "전문",
                    "조문키": "0050000",
                    "조문내용": "제4장 근로시간과 휴식",
                },
                {
                    "조문번호": "50",
                    "조문키": "0050001",
                    "조문제목": "근로시간",
                    "항": [
                        {
                            "항번호": "① ",
                            "항내용": "1주 간의 근로시간은 휴게시간을 제외하고 40시간을 초과할 수 없다.",
                        },
                        {
                            "항번호": "② ",
                            "항내용": "1일의 근로시간은 휴게시간을 제외하고 8시간을 초과할 수 없다.",
                        },
                    ],
                },
            ]
        }
    }
}


@pytest.mark.asyncio
async def test_get_single_article_picks_body_over_chapter_header():
    """50조 시뮬레이션: 조문단위 배열에 장 헤더가 먼저 와도 본문이 반환되어야 한다."""
    repo = LawDetailRepository()
    detail_resp = _make_response(_DETAIL_BODY)
    josub_resp = _make_response(_JOSUB_CHAPTER_THEN_BODY)

    async def fake_aget(url, params=None, timeout=None):
        if params and params.get("target") == "eflawjosub":
            return josub_resp
        return detail_resp

    with patch("src.repositories.law_detail.aget", side_effect=fake_aget):
        result = await repo.get_single_article(
            law_id="265959",
            article_number="50",
            arguments={"env": {"LAW_API_KEY": "testkey123"}},
        )

    content = result.get("content") or ""
    assert "제4장" not in content, f"장 헤더가 본문 자리에 들어옴: {content!r}"
    assert "40시간" in content, f"50조 본문이 누락됨: {content!r}"
