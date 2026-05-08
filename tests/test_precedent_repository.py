import pytest

from src.repositories import precedent_repository as precedent_module
from src.repositories.precedent_repository import PrecedentRepository


@pytest.mark.asyncio
async def test_search_precedent_with_fallback_preserves_attempt_api_urls(monkeypatch):
    repo = PrecedentRepository()

    async def fake_search(query, page, per_page, court, date_from, date_to, arguments):
        label = f"{query}|{date_from}|{date_to}"
        return {
            "query": query,
            "page": page,
            "per_page": per_page,
            "total": 0,
            "precedents": [],
            "api_url": label,
        }

    monkeypatch.setattr(repo, "_search_precedent_internal", fake_search)
    monkeypatch.setattr(
        precedent_module,
        "build_query_set",
        lambda query, issue_type=None, must_include=None: [],
    )
    monkeypatch.setattr(
        precedent_module,
        "expand_date_range_stepwise",
        lambda date_from, date_to, step: (
            ("20160101", "20260101") if step == 1 else (None, None)
        ),
    )
    monkeypatch.setattr(
        precedent_module,
        "extract_keywords",
        lambda query: ["부당해고", "판례", "최근"],
    )

    result = await repo.search_precedent_with_fallback(
        query="최근 3년 부당해고 판례",
        page=1,
        per_page=3,
        date_from="20230509",
        date_to="20260508",
        arguments={"OC": "15248"},
    )

    assert result["api_url"] == "부당해고 판례 최근|None|None"
    assert result["attempts"][0]["api_url"] == "최근 3년 부당해고 판례|20230509|20260508"
    assert result["attempts"][-1]["api_url"] == "부당해고 판례 최근|None|None"
