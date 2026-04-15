"""legal_qa_tool 및 health 핸들러."""
import logging

logger = logging.getLogger("lexguard-mcp")


async def handle_health(services: dict) -> dict:
    return await services["health"].check_health()


async def handle_legal_qa(arguments: dict, services: dict) -> dict:
    query = arguments.get("query")
    max_results = arguments.get("max_results_per_type", 3)
    logger.debug("Calling smart_search | query=%s max_results=%d", query, max_results)
    return await services["smart_search"].smart_search(
        query,
        search_types=None,
        max_results_per_type=max_results,
        arguments=arguments,
    )
