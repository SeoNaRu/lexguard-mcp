"""
Law Form Repository - 별표서식 검색 (법령·행정규칙·자치법규)
"""
import httpx
from ..utils.http_client import aget
import json
from typing import Optional
from .base import (
    BaseLawRepository,
    logger,
    LAW_API_SEARCH_URL,
    search_cache,
    failure_cache,
    DRF_REQUEST_TIMEOUT_SEC,
)


class LawFormRepository(BaseLawRepository):
    """별표서식(licbyl·admbyl·ordinbyl) 담당 Repository"""

    async def _search_form(
        self,
        target: str,
        list_key: str,
        query: Optional[str],
        page: int,
        per_page: int,
        arguments: Optional[dict],
    ) -> dict:
        """별표서식 공통 검색 헬퍼."""
        cache_key = (target, query or "", page, per_page)
        if cache_key in search_cache:
            return search_cache[cache_key]
        if cache_key in failure_cache:
            return failure_cache[cache_key]

        try:
            params: dict = {
                "target": target,
                "type": "JSON",
                "page": page,
                "display": per_page,
            }
            if query:
                params["query"] = self.normalize_search_query(query)

            _, err = self.attach_api_key(params, arguments, LAW_API_SEARCH_URL)
            if err:
                return err

            response = await aget(LAW_API_SEARCH_URL, params=params, timeout=DRF_REQUEST_TIMEOUT_SEC)
            invalid = self.validate_drf_response(response)
            if invalid:
                failure_cache[cache_key] = invalid
                return invalid
            response.raise_for_status()

            try:
                data = response.json()
            except json.JSONDecodeError as e:
                return {"error": f"JSON 파싱 오류: {e}"}

            total, items = 0, []
            if isinstance(data, dict):
                for v in data.values():
                    if isinstance(v, dict) and list_key in v:
                        try:
                            total = int(v.get("totalCnt", 0))
                        except (TypeError, ValueError):
                            total = 0
                        items = v.get(list_key, [])
                        break
                else:
                    try:
                        total = int(data.get("totalCnt", 0))
                    except (TypeError, ValueError):
                        total = 0
                    items = data.get(list_key, [])
                if not isinstance(items, list):
                    items = [items] if items else []

            result = {
                "target": target,
                "query": query,
                "page": page,
                "per_page": per_page,
                "total": total,
                "items": items[:per_page],
                "api_url": str(response.url),
            }
            if not items:
                result["message"] = "검색 결과가 없습니다."
            search_cache[cache_key] = result
            return result

        except httpx.TimeoutException:
            err = {
                "error_code": "API_ERROR_TIMEOUT",
                "missing_reason": "API_ERROR_TIMEOUT",
                "error": "API 호출 타임아웃",
                "recovery_guide": "잠시 후 다시 시도하세요.",
            }
            failure_cache[cache_key] = err
            return err
        except httpx.RequestError as e:
            return {"error": f"API 요청 실패: {e}"}
        except Exception as e:
            logger.exception("LawFormRepository._search_form 오류")
            return {"error": f"예상치 못한 오류: {e}"}

    async def search_law_forms(
        self,
        query: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        arguments: Optional[dict] = None,
    ) -> dict:
        """법령 별표서식 목록 검색 (target=licbyl)."""
        return await self._search_form("licbyl", "licbyl", query, page, per_page, arguments)

    async def search_admin_rule_forms(
        self,
        query: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        arguments: Optional[dict] = None,
    ) -> dict:
        """행정규칙 별표서식 목록 검색 (target=admbyl)."""
        return await self._search_form("admbyl", "admbyl", query, page, per_page, arguments)

    async def search_ordinance_forms(
        self,
        query: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        arguments: Optional[dict] = None,
    ) -> dict:
        """자치법규 별표서식 목록 검색 (target=ordinbyl)."""
        return await self._search_form("ordinbyl", "ordinbyl", query, page, per_page, arguments)
