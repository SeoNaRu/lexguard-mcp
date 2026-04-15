"""
Law Misc Repository - 영문법령·조약·체계도·한눈보기·약칭·삭제이력·위임법령 검색
"""
import httpx
from ..utils.http_client import aget
import json
from typing import Optional
from .base import (
    BaseLawRepository,
    logger,
    LAW_API_SEARCH_URL,
    LAW_API_BASE_URL,
    search_cache,
    failure_cache,
    DRF_REQUEST_TIMEOUT_SEC,
)


def _parse_search_result(data: dict, list_key: str) -> tuple:
    """공통 목록 응답 파싱. (total, items) 반환."""
    total = 0
    items = []
    if not isinstance(data, dict):
        return total, items

    # 상위 wrapper key 탐색 (예: ElawSearch, TrtySearch 등)
    for v in data.values():
        if isinstance(v, dict) and list_key in v:
            try:
                total = int(v.get("totalCnt", 0))
            except (TypeError, ValueError):
                total = 0
            items = v.get(list_key, [])
            break
    else:
        # flat 구조
        try:
            total = int(data.get("totalCnt", 0))
        except (TypeError, ValueError):
            total = 0
        items = data.get(list_key, [])

    if not isinstance(items, list):
        items = [items] if items else []
    return total, items


class LawMiscRepository(BaseLawRepository):
    """영문법령·조약·체계도·한눈보기·약칭·삭제이력·위임법령 담당 Repository"""

    # ------------------------------------------------------------------ #
    # 내부 공통 헬퍼
    # ------------------------------------------------------------------ #

    async def _search(
        self,
        target: str,
        list_key: str,
        query: Optional[str],
        page: int,
        per_page: int,
        extra_params: Optional[dict],
        arguments: Optional[dict],
    ) -> dict:
        """목록 검색 공통 로직."""
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
                return {"error": f"JSON 파싱 오류: {e}", "recovery_guide": "API 서버 상태를 확인하세요."}

            total, items = _parse_search_result(data, list_key)
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
            return {"error": f"API 요청 실패: {e}", "recovery_guide": "네트워크 연결을 확인하세요."}
        except Exception as e:
            logger.exception("LawMiscRepository._search 오류")
            return {"error": f"예상치 못한 오류: {e}"}

    async def _get_detail(
        self,
        target: str,
        item_id: str,
        extra_params: Optional[dict],
        arguments: Optional[dict],
    ) -> dict:
        """본문 조회 공통 로직."""
        cache_key = (target + "_detail", item_id, str(sorted((extra_params or {}).items())))
        if cache_key in search_cache:
            return search_cache[cache_key]
        if cache_key in failure_cache:
            return failure_cache[cache_key]

        try:
            params: dict = {"target": target, "type": "JSON", "ID": item_id}
            if extra_params:
                params.update(extra_params)

            _, err = self.attach_api_key(params, arguments, LAW_API_BASE_URL)
            if err:
                return err

            response = await aget(LAW_API_BASE_URL, params=params, timeout=DRF_REQUEST_TIMEOUT_SEC)
            invalid = self.validate_drf_response(response)
            if invalid:
                failure_cache[cache_key] = invalid
                return invalid
            response.raise_for_status()

            try:
                data = response.json()
            except json.JSONDecodeError as e:
                return {"error": f"JSON 파싱 오류: {e}"}

            result = {"target": target, "id": item_id, "data": data, "api_url": str(response.url)}
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
            logger.exception("LawMiscRepository._get_detail 오류")
            return {"error": f"예상치 못한 오류: {e}"}

    # ------------------------------------------------------------------ #
    # 영문법령 (target=elaw)
    # ------------------------------------------------------------------ #

    async def search_english_law(
        self,
        query: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        arguments: Optional[dict] = None,
    ) -> dict:
        """영문법령 목록 검색 (target=elaw)."""
        return await self._search("elaw", "elaw", query, page, per_page, None, arguments)

    async def get_english_law(
        self,
        law_id: str,
        arguments: Optional[dict] = None,
    ) -> dict:
        """영문법령 본문 조회 (target=elaw)."""
        return await self._get_detail("elaw", law_id, None, arguments)

    # ------------------------------------------------------------------ #
    # 조약 (target=trty)
    # ------------------------------------------------------------------ #

    async def search_treaty(
        self,
        query: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        arguments: Optional[dict] = None,
    ) -> dict:
        """조약 목록 검색 (target=trty)."""
        return await self._search("trty", "trty", query, page, per_page, None, arguments)

    async def get_treaty(
        self,
        treaty_id: str,
        arguments: Optional[dict] = None,
    ) -> dict:
        """조약 본문 조회 (target=trty)."""
        return await self._get_detail("trty", treaty_id, None, arguments)

    # ------------------------------------------------------------------ #
    # 법령 체계도 (target=lsStmd)
    # ------------------------------------------------------------------ #

    async def search_law_structure(
        self,
        query: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        arguments: Optional[dict] = None,
    ) -> dict:
        """법령 체계도 목록 검색 (target=lsStmd)."""
        return await self._search("lsStmd", "lsStmd", query, page, per_page, None, arguments)

    async def get_law_structure(
        self,
        law_id: str,
        arguments: Optional[dict] = None,
    ) -> dict:
        """법령 체계도 본문 조회 (target=lsStmd)."""
        return await self._get_detail("lsStmd", law_id, None, arguments)

    # ------------------------------------------------------------------ #
    # 한눈보기 (target=oneview)
    # ------------------------------------------------------------------ #

    async def search_oneview(
        self,
        query: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        arguments: Optional[dict] = None,
    ) -> dict:
        """한눈보기 목록 검색 (target=oneview)."""
        return await self._search("oneview", "oneview", query, page, per_page, None, arguments)

    async def get_oneview(
        self,
        law_id: str,
        arguments: Optional[dict] = None,
    ) -> dict:
        """한눈보기 본문 조회 (target=oneview)."""
        return await self._get_detail("oneview", law_id, None, arguments)

    # ------------------------------------------------------------------ #
    # 법령명 약칭 (target=lsAbrv)
    # ------------------------------------------------------------------ #

    async def search_law_abbreviation(
        self,
        query: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        arguments: Optional[dict] = None,
    ) -> dict:
        """법령명 약칭 목록 검색 (target=lsAbrv)."""
        return await self._search("lsAbrv", "lsAbrv", query, page, per_page, None, arguments)

    # ------------------------------------------------------------------ #
    # 삭제 데이터 목록 (target=delHst)
    # ------------------------------------------------------------------ #

    async def search_deleted_history(
        self,
        query: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        arguments: Optional[dict] = None,
    ) -> dict:
        """삭제 데이터 목록 검색 (target=delHst)."""
        return await self._search("delHst", "delHst", query, page, per_page, None, arguments)

    # ------------------------------------------------------------------ #
    # 위임 법령 (target=lsDelegated) — lawService.do 사용
    # ------------------------------------------------------------------ #

    async def get_delegated_law(
        self,
        law_id: str,
        arguments: Optional[dict] = None,
    ) -> dict:
        """위임 법령 조회 (target=lsDelegated)."""
        return await self._get_detail("lsDelegated", law_id, None, arguments)
