"""document_issue_analysis MCP 경로와 동일한 키워드 인자로 auto_search가 bool인지 검증."""
import asyncio

import pytest

from src.services.situation_guidance_service import SituationGuidanceService
from src.utils.response_formatter import format_mcp_response


@pytest.mark.asyncio
async def test_document_issue_auto_search_is_bool_in_structured_content():
    svc = SituationGuidanceService()
    result = await svc.document_issue_analysis(
        "제1조 계약기간 1년",
        arguments={},
        auto_search=False,
        max_clauses=1,
        max_results_per_type=1,
    )
    assert isinstance(result.get("auto_search"), bool)

    mcp = format_mcp_response(result, "document_issue_tool")
    sc = mcp["structuredContent"]
    assert isinstance(sc.get("auto_search"), bool)
