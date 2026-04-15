"""전용 조회 도구 핸들러 (law_article, law_comparison, 각종 lookup)."""
import logging
from ...utils.mcp_tool_args import resolve_law_comparison_tool

logger = logging.getLogger("lexguard-mcp")


async def handle_law_article(arguments: dict, services: dict) -> dict:
    law_name = arguments.get("law_name")
    article_number = arguments.get("article_number")
    hang = arguments.get("hang")
    ho = arguments.get("ho")
    mok = arguments.get("mok")
    mode = "single" if article_number else "detail"
    logger.debug(
        "Calling law_article_tool | law=%s article=%s hang=%s ho=%s mok=%s",
        law_name, article_number, hang, ho, mok,
    )
    return await services["law_detail_repo"].get_law(
        None, law_name, mode, article_number, hang, ho, mok, arguments,
    )


async def handle_law_comparison(arguments: dict, services: dict) -> dict:
    req_cmp, err_cmp = resolve_law_comparison_tool(arguments)
    if err_cmp:
        return err_cmp
    return await services["law_comparison"].compare_laws(req_cmp, arguments)


async def handle_precedent_lookup(arguments: dict, services: dict) -> dict:
    return await services["smart_search"].precedent_lookup(
        keyword=arguments.get("keyword"),
        case_number=arguments.get("case_number"),
        page=int(arguments.get("page", 1)),
        per_page=int(arguments.get("per_page", 10)),
        court=arguments.get("court"),
        date_from=arguments.get("date_from"),
        date_to=arguments.get("date_to"),
        arguments=arguments,
    )


async def handle_interpretation(arguments: dict, services: dict) -> dict:
    return await services["smart_search"].interpretation_lookup(
        query=arguments.get("query", ""),
        page=int(arguments.get("page", 1)),
        per_page=int(arguments.get("per_page", 10)),
        agency=arguments.get("agency"),
        arguments=arguments,
    )


async def handle_administrative_appeal(arguments: dict, services: dict) -> dict:
    return await services["smart_search"].administrative_appeal_lookup(
        query=arguments.get("query", ""),
        page=int(arguments.get("page", 1)),
        per_page=int(arguments.get("per_page", 10)),
        date_from=arguments.get("date_from"),
        date_to=arguments.get("date_to"),
        arguments=arguments,
    )


async def handle_constitutional_decision(arguments: dict, services: dict) -> dict:
    return await services["smart_search"].constitutional_decision_lookup(
        query=arguments.get("query", ""),
        page=int(arguments.get("page", 1)),
        per_page=int(arguments.get("per_page", 10)),
        date_from=arguments.get("date_from"),
        date_to=arguments.get("date_to"),
        arguments=arguments,
    )


async def handle_committee_decision(arguments: dict, services: dict) -> dict:
    return await services["smart_search"].committee_decision_lookup(
        committee_type=arguments.get("committee_type", ""),
        query=arguments.get("query", ""),
        page=int(arguments.get("page", 1)),
        per_page=int(arguments.get("per_page", 10)),
        arguments=arguments,
    )


async def handle_special_administrative_appeal(arguments: dict, services: dict) -> dict:
    return await services["smart_search"].special_administrative_appeal_lookup(
        tribunal_type=arguments.get("tribunal_type", ""),
        query=arguments.get("query", ""),
        page=int(arguments.get("page", 1)),
        per_page=int(arguments.get("per_page", 10)),
        arguments=arguments,
    )


async def handle_local_ordinance(arguments: dict, services: dict) -> dict:
    per_page = max(1, min(50, int(arguments.get("per_page", 20))))
    return await services["smart_search"].local_ordinance_lookup(
        query=arguments.get("query"),
        local_government=arguments.get("local_government"),
        page=int(arguments.get("page", 1)),
        per_page=per_page,
        arguments=arguments,
    )


async def handle_administrative_rule(arguments: dict, services: dict) -> dict:
    per_page = max(1, min(50, int(arguments.get("per_page", 20))))
    return await services["smart_search"].administrative_rule_lookup(
        query=arguments.get("query"),
        agency=arguments.get("agency"),
        page=int(arguments.get("page", 1)),
        per_page=per_page,
        arguments=arguments,
    )


async def handle_ministry_interpretation(arguments: dict, services: dict) -> dict:
    per_page = max(1, min(50, int(arguments.get("per_page", 20))))
    return await services["smart_search"].ministry_interpretation_lookup(
        query=arguments.get("query"),
        agency=arguments.get("agency"),
        page=int(arguments.get("page", 1)),
        per_page=per_page,
        arguments=arguments,
    )


async def handle_law_history(arguments: dict, services: dict) -> dict:
    per_page = max(1, min(50, int(arguments.get("per_page", 20))))
    return await services["smart_search"].law_history_lookup(
        search_type=arguments.get("search_type", "law_change"),
        query=arguments.get("query"),
        law_id=arguments.get("law_id"),
        article_number=arguments.get("article_number"),
        date=arguments.get("date"),
        page=int(arguments.get("page", 1)),
        per_page=per_page,
        arguments=arguments,
    )


async def handle_law_info(arguments: dict, services: dict) -> dict:
    per_page = max(1, min(50, int(arguments.get("per_page", 20))))
    return await services["smart_search"].law_info_lookup(
        info_type=arguments.get("info_type", "english_law"),
        query=arguments.get("query"),
        item_id=arguments.get("item_id"),
        page=int(arguments.get("page", 1)),
        per_page=per_page,
        arguments=arguments,
    )


async def handle_law_form(arguments: dict, services: dict) -> dict:
    per_page = max(1, min(50, int(arguments.get("per_page", 20))))
    return await services["smart_search"].law_form_lookup(
        form_type=arguments.get("form_type", "law"),
        query=arguments.get("query"),
        page=int(arguments.get("page", 1)),
        per_page=per_page,
        arguments=arguments,
    )


async def handle_law_link(arguments: dict, services: dict) -> dict:
    per_page = max(1, min(50, int(arguments.get("per_page", 20))))
    return await services["smart_search"].law_link_lookup(
        link_type=arguments.get("link_type", "law_to_ordinance"),
        query=arguments.get("query"),
        law_id=arguments.get("law_id"),
        department=arguments.get("department"),
        region_code=arguments.get("region_code"),
        page=int(arguments.get("page", 1)),
        per_page=per_page,
        arguments=arguments,
    )
