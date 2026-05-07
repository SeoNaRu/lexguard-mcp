"""smart_search repository call signatures."""

import pytest

from src.services.smart_search_service import SmartSearchService


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("search_type", "repo_attr", "method_name", "query"),
    [
        (
            "precedent",
            "precedent_repo",
            "search_precedent",
            "최근 3년 부당해고 판례 검색",
        ),
        (
            "constitutional",
            "constitutional_repo",
            "search_constitutional_decision",
            "최근 3년 위헌 결정 알려줘",
        ),
        (
            "administrative_appeal",
            "appeal_repo",
            "search_administrative_appeal",
            "최근 3년 행정심판 재결례 알려줘",
        ),
    ],
)
async def test_smart_search_passes_time_condition_to_time_aware_repositories(
    monkeypatch,
    search_type,
    repo_attr,
    method_name,
    query,
):
    service = SmartSearchService()
    captured = []

    async def fake_search(
        self,
        query=None,
        page=1,
        per_page=20,
        *args,
        date_from=None,
        date_to=None,
        arguments=None,
    ):
        if search_type == "precedent":
            if len(args) >= 2 and date_from is None:
                date_from = args[1]
            if len(args) >= 3 and date_to is None:
                date_to = args[2]
        else:
            if len(args) >= 1 and date_from is None:
                date_from = args[0]
            if len(args) >= 2 and date_to is None:
                date_to = args[1]
        captured.append(
            {
                "query": query,
                "page": page,
                "per_page": per_page,
                "date_from": date_from,
                "date_to": date_to,
            }
        )
        if search_type == "precedent":
            return {"precedents": [{"case_number": "stub", "case_name": "stub"}], "total": 1}
        if search_type == "constitutional":
            return {"decisions": [{"case_number": "stub"}], "total": 1}
        return {"appeals": [{"case_number": "stub"}], "total": 1}

    repository = getattr(service, repo_attr)
    monkeypatch.setattr(repository, method_name, fake_search.__get__(repository, type(repository)))

    parsed = service.parse_time_condition(query)

    assert parsed is not None

    await service.smart_search(
        query,
        search_types=[search_type],
        max_results_per_type=3,
        arguments={},
    )

    assert captured == [
        {
            "query": query,
            "page": 1,
            "per_page": 3,
            "date_from": parsed["date_from"],
            "date_to": parsed["date_to"],
        }
    ]
