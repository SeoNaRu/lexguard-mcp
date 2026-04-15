"""document_issue_tool 핸들러."""
import logging

logger = logging.getLogger("lexguard-mcp")


async def handle_document_issue(arguments: dict, services: dict) -> dict:
    document_text = arguments.get("document_text")

    _raw_auto = arguments.get("auto_search", True)
    if _raw_auto is True or _raw_auto is False:
        auto_search = _raw_auto
    elif isinstance(_raw_auto, str):
        auto_search = _raw_auto.strip().lower() in ("true", "1", "yes")
    else:
        auto_search = bool(_raw_auto)

    max_clauses = int(arguments.get("max_clauses", 3))
    max_results = int(arguments.get("max_results_per_type", 3))

    logger.debug(
        "Calling document_issue_tool | doc_len=%d auto_search=%s max_clauses=%d max_results=%d",
        len(document_text) if document_text else 0,
        auto_search, max_clauses, max_results,
    )
    return await services["situation_guidance"].document_issue_analysis(
        document_text,
        arguments=arguments,
        auto_search=auto_search,
        max_clauses=max_clauses,
        max_results_per_type=max_results,
    )
