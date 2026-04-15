"""
Law Link Repository - 법령-자치법규 연계 정보 검색
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


class LawLinkRepository(BaseLawRepository):
    """법령-자치법규 연계 정보(lnkLs·lnkLsOrdJo·lnkDep·lnkOrd·lnkLsOrd·lnkOrg) 담당 Repository"""

    async def _search_link(
        self,
        target: str,
        list_key: str,
        query: Optional[str],
        page: int,
        per_page: int,
        extra_params: Optional[dict],
        arguments: Optional[dict],
    ) -> dict:
        """연계 API 공통 검색 헬퍼."""
        cache_key = (target, query or "", page, per_page, str(sorted((extra_params or {}).items())))
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
            if extra_params:
                params.update(extra_params)

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
            logger.exception("LawLinkRepository._search_link 오류")
            return {"error": f"예상치 못한 오류: {e}"}

    # ------------------------------------------------------------------ #
    # lnkLs: 법령-자치법규 연계 목록
    # ------------------------------------------------------------------ #

    async def search_law_ordinance_link(
        self,
        query: Optional[str] = None,
        law_id: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        arguments: Optional[dict] = None,
    ) -> dict:
        """법령-자치법규 연계 목록 검색 (target=lnkLs)."""
        extra = {"lsId": law_id} if law_id else None
        return await self._search_link("lnkLs", "lnkLs", query, page, per_page, extra, arguments)

    # ------------------------------------------------------------------ #
    # lnkLsOrdJo: 연계 법령별 조례 조문 목록
    # ------------------------------------------------------------------ #

    async def search_linked_ordinance_articles(
        self,
        query: Optional[str] = None,
        law_id: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        arguments: Optional[dict] = None,
    ) -> dict:
        """연계 법령별 조례 조문 목록 검색 (target=lnkLsOrdJo)."""
        extra = {"lsId": law_id} if law_id else None
        return await self._search_link("lnkLsOrdJo", "lnkLsOrdJo", query, page, per_page, extra, arguments)

    # ------------------------------------------------------------------ #
    # lnkDep: 연계 법령 소관부처별 목록
    # ------------------------------------------------------------------ #

    async def search_link_by_department(
        self,
        query: Optional[str] = None,
        department: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        arguments: Optional[dict] = None,
    ) -> dict:
        """연계 법령 소관부처별 목록 검색 (target=lnkDep)."""
        extra = {"orgCd": department} if department else None
        return await self._search_link("lnkDep", "lnkDep", query, page, per_page, extra, arguments)

    # ------------------------------------------------------------------ #
    # lnkOrd: 연계 조례 목록
    # ------------------------------------------------------------------ #

    async def search_linked_ordinance(
        self,
        query: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        arguments: Optional[dict] = None,
    ) -> dict:
        """연계 조례 목록 검색 (target=lnkOrd)."""
        return await self._search_link("lnkOrd", "lnkOrd", query, page, per_page, None, arguments)

    # ------------------------------------------------------------------ #
    # lnkLsOrd: 연계 법령별 조례 목록
    # ------------------------------------------------------------------ #

    async def search_law_linked_ordinance(
        self,
        query: Optional[str] = None,
        law_id: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        arguments: Optional[dict] = None,
    ) -> dict:
        """연계 법령별 조례 목록 검색 (target=lnkLsOrd)."""
        extra = {"lsId": law_id} if law_id else None
        return await self._search_link("lnkLsOrd", "lnkLsOrd", query, page, per_page, extra, arguments)

    # ------------------------------------------------------------------ #
    # lnkOrg: 연계 조례 지자체별 목록
    # ------------------------------------------------------------------ #

    async def search_link_by_region(
        self,
        query: Optional[str] = None,
        region_code: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        arguments: Optional[dict] = None,
    ) -> dict:
        """연계 조례 지자체별 목록 검색 (target=lnkOrg)."""
        extra = {"orgCd": region_code} if region_code else None
        return await self._search_link("lnkOrg", "lnkOrg", query, page, per_page, extra, arguments)
