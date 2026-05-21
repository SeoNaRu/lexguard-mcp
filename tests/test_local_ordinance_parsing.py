"""
LocalOrdinanceRepository.search_local_ordinance — 응답 파싱 회귀 테스트.

라이브 검증에서 발견된 이슈: law.go.kr 자치법규 검색 API가 OrdinSearch.law 키에
배열을 담아 반환하는데 (다른 검색 API 패턴과 달리), 기존 파싱이 'ordin' 키만
탐색해서 totalCnt > 0인데 ordinances=[] 로 나오던 버그.

응답 키 변형 모두 처리되는지 fixture로 검증.
"""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.repositories.local_ordinance_repository import LocalOrdinanceRepository


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "api_responses"


def load_fixture(name: str) -> dict:
    with (FIXTURES_DIR / name).open(encoding="utf-8") as f:
        return json.load(f)


def make_mock_response(body: dict) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"Content-Type": "application/json"}
    mock_resp.text = json.dumps(body, ensure_ascii=False)
    mock_resp.json = MagicMock(return_value=body)
    mock_resp.url = "https://www.law.go.kr/DRF/lawSearch.do"
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


@pytest.mark.asyncio
async def test_parses_ordinances_from_law_key():
    """실제 law.go.kr 응답 구조(OrdinSearch.law)에서 자치법규 배열 추출."""
    fixture = load_fixture("ordin_search_law_key.json")
    repo = LocalOrdinanceRepository()

    async def fake_aget(url, params=None, timeout=None):
        return make_mock_response(fixture)

    with patch("src.repositories.local_ordinance_repository.aget", side_effect=fake_aget):
        result = await repo.search_local_ordinance(
            query="청소년",
            local_government="서울",
            arguments={"env": {"LAW_API_KEY": "testkey123"}},
        )

    assert result["total"] == 410
    assert len(result["ordinances"]) == 2
    assert result["ordinances"][0]["자치법규명"] == "서울특별시 청소년 보호 조례"
    assert "note" not in result, f"빈 결과 안내가 잘못 나옴: {result.get('note')}"


@pytest.mark.asyncio
async def test_parses_ordinances_from_ordin_key_legacy():
    """레거시 OrdinSearch.ordin 키도 fallback으로 처리."""
    fixture = load_fixture("ordin_search_ordin_key.json")
    repo = LocalOrdinanceRepository()

    async def fake_aget(url, params=None, timeout=None):
        return make_mock_response(fixture)

    with patch("src.repositories.local_ordinance_repository.aget", side_effect=fake_aget):
        result = await repo.search_local_ordinance(
            query="환경",
            local_government="부산",
            arguments={"env": {"LAW_API_KEY": "testkey123"}},
        )

    assert result["total"] == 3
    assert len(result["ordinances"]) == 2
    assert result["ordinances"][0]["지자체기관명"] == "부산광역시"


@pytest.mark.asyncio
async def test_empty_response_handled_gracefully():
    """totalCnt=0, law/ordin 키 모두 없는 경우 빈 결과 반환."""
    fixture = load_fixture("ordin_search_empty.json")
    repo = LocalOrdinanceRepository()

    async def fake_aget(url, params=None, timeout=None):
        return make_mock_response(fixture)

    with patch("src.repositories.local_ordinance_repository.aget", side_effect=fake_aget):
        result = await repo.search_local_ordinance(
            query="없는검색어",
            local_government="서울",
            arguments={"env": {"LAW_API_KEY": "testkey123"}},
        )

    assert result["total"] == 0
    assert result["ordinances"] == []
    assert "note" not in result


@pytest.mark.asyncio
async def test_per_page_limit_applied_to_ordinances():
    """per_page보다 응답 항목이 많으면 잘라서 반환."""
    fixture = load_fixture("ordin_search_law_key.json")  # 2건
    repo = LocalOrdinanceRepository()

    async def fake_aget(url, params=None, timeout=None):
        return make_mock_response(fixture)

    with patch("src.repositories.local_ordinance_repository.aget", side_effect=fake_aget):
        result = await repo.search_local_ordinance(
            query="청소년",
            local_government="서울",
            per_page=1,
            arguments={"env": {"LAW_API_KEY": "testkey123"}},
        )

    assert len(result["ordinances"]) == 1


@pytest.mark.asyncio
async def test_single_dict_response_wrapped_to_list():
    """API가 단일 항목을 list 대신 dict로 줄 때도 list로 정규화."""
    body = {
        "OrdinSearch": {
            "totalCnt": "1",
            "law": {
                "자치법규ID": "8888",
                "자치법규명": "단독 항목 조례",
                "지자체기관명": "대전광역시",
            },
        }
    }
    repo = LocalOrdinanceRepository()

    async def fake_aget(url, params=None, timeout=None):
        return make_mock_response(body)

    with patch("src.repositories.local_ordinance_repository.aget", side_effect=fake_aget):
        result = await repo.search_local_ordinance(
            query="조례",
            local_government="대전",
            arguments={"env": {"LAW_API_KEY": "testkey123"}},
        )

    assert result["total"] == 1
    assert isinstance(result["ordinances"], list)
    assert len(result["ordinances"]) == 1
    assert result["ordinances"][0]["자치법규명"] == "단독 항목 조례"


@pytest.mark.asyncio
async def test_total_with_no_items_emits_note():
    """totalCnt > 0인데 law/ordin 모두 비어 있으면 note 메시지 추가 (회귀 방지용)."""
    body = {
        "OrdinSearch": {
            "totalCnt": "100",
        }
    }
    repo = LocalOrdinanceRepository()

    async def fake_aget(url, params=None, timeout=None):
        return make_mock_response(body)

    with patch("src.repositories.local_ordinance_repository.aget", side_effect=fake_aget):
        result = await repo.search_local_ordinance(
            query="조례",
            local_government="서울",
            arguments={"env": {"LAW_API_KEY": "testkey123"}},
        )

    assert result["total"] == 100
    assert result["ordinances"] == []
    assert "note" in result and "totalCnt" in result["note"]


@pytest.mark.asyncio
async def test_root_level_law_key_without_ordin_search_wrapper():
    """OrdinSearch 래퍼 없이 root에 law 키만 있는 응답 변형도 처리."""
    body = {
        "totalCnt": "1",
        "law": [
            {"자치법규ID": "111", "자치법규명": "루트레벨 응답", "지자체기관명": "광주광역시"},
        ],
    }
    repo = LocalOrdinanceRepository()

    async def fake_aget(url, params=None, timeout=None):
        return make_mock_response(body)

    with patch("src.repositories.local_ordinance_repository.aget", side_effect=fake_aget):
        result = await repo.search_local_ordinance(
            query="조례",
            local_government="광주",
            arguments={"env": {"LAW_API_KEY": "testkey123"}},
        )

    assert result["total"] == 1
    assert len(result["ordinances"]) == 1
    assert result["ordinances"][0]["자치법규명"] == "루트레벨 응답"
