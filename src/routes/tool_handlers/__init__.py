"""MCP 도구 핸들러 디스패처.

services dict 키:
    "health"              - HealthService 인스턴스
    "smart_search"        - SmartSearchService 인스턴스
    "situation_guidance"  - SituationGuidanceService 인스턴스
    "law_comparison"      - LawComparisonService 인스턴스
    "law_detail_repo"     - LawDetailRepository 인스턴스
"""
from .legal_qa import handle_health, handle_legal_qa
from .document_issue import handle_document_issue
from .lookup_tools import (
    handle_law_article,
    handle_law_comparison,
    handle_precedent_lookup,
    handle_interpretation,
    handle_administrative_appeal,
    handle_constitutional_decision,
    handle_committee_decision,
    handle_special_administrative_appeal,
    handle_local_ordinance,
    handle_administrative_rule,
    handle_ministry_interpretation,
    handle_law_history,
    handle_law_info,
    handle_law_form,
    handle_law_link,
)

_DISPATCH_TABLE = {
    "health": handle_health,
    "legal_qa_tool": handle_legal_qa,
    "document_issue_tool": handle_document_issue,
    "law_article_tool": handle_law_article,
    "law_comparison_tool": handle_law_comparison,
    "precedent_lookup_tool": handle_precedent_lookup,
    "interpretation_tool": handle_interpretation,
    "administrative_appeal_tool": handle_administrative_appeal,
    "constitutional_decision_tool": handle_constitutional_decision,
    "committee_decision_tool": handle_committee_decision,
    "special_administrative_appeal_tool": handle_special_administrative_appeal,
    "local_ordinance_tool": handle_local_ordinance,
    "administrative_rule_tool": handle_administrative_rule,
    "ministry_interpretation_tool": handle_ministry_interpretation,
    "law_history_tool": handle_law_history,
    "law_info_tool": handle_law_info,
    "law_form_tool": handle_law_form,
    "law_link_tool": handle_law_link,
}


async def dispatch(tool_name: str, arguments: dict, services: dict) -> dict:
    """tool_name에 맞는 핸들러를 찾아 실행한다.

    미등록 도구면 {"error": "Unknown tool: <name>"} 반환.
    """
    handler = _DISPATCH_TABLE.get(tool_name)
    if handler is None:
        return {"error": f"Unknown tool: {tool_name}"}

    # health는 arguments를 받지 않음
    if tool_name == "health":
        return await handler(services)
    return await handler(arguments, services)
