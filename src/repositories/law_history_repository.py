"""
Law History Repository - 법령 변경이력·조문 개정이력 검색
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


class LawHistoryRepository(BaseLawRepository):
    """법령 변경이력(lsHstInf) 및 조문 개정이력(lsJoHstInf) 담당 Repository"""

    # ------------------------------------------------------------------ #
    # 법령 변경이력 (target=lsHstInf) — lawSearch.do
    # ------------------------------------------------------------------ #

    async def search_law_change_history(
        self,
        query: Optional[str] = None,
        law_id: Optional[str] = None,
        reg_dt: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        arguments: Optional[dict] = None,
    ) -> dict:
        """법령 변경이력 목록 검색 (target=lsHstInf).

        Args:
            query: 법령명 검색어
            law_id: 법령 ID (lsId)
            reg_dt: 기준 일자 (YYYYMMDD, 해당 일자 기준 변경이력)
            page: 페이지 번호
            per_page: 페이지당 결과 수
            arguments: API 키 등 추가 인자
        """
        cache_key = ("lsHstInf", query or "", law_id or "", reg_dt or "", page, per_page)
        if cache_key in search_cache:
            return search_cache[cache_key]
        if cache_key in failure_cache:
            return failure_cache[cache_key]

        try:
            params: dict = {
                "target": "lsHstInf",
                "type": "JSON",
                "page": page,
                "display": per_page,
            }
            if query:
                params["query"] = self.normalize_search_query(query)
            if law_id:
                params["lsId"] = law_id
            if reg_dt:
                params["regDt"] = reg_dt

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
                    if isinstance(v, dict) and "lsHstInf" in v:
                        try:
                            total = int(v.get("totalCnt", 0))
                        except (TypeError, ValueError):
                            total = 0
                        items = v.get("lsHstInf", [])
                        break
                else:
                    try:
                        total = int(data.get("totalCnt", 0))
                    except (TypeError, ValueError):
                        total = 0
                    items = data.get("lsHstInf", [])
                if not isinstance(items, list):
                    items = [items] if items else []

            result = {
                "query": query,
                "law_id": law_id,
                "reg_dt": reg_dt,
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
            logger.exception("search_law_change_history 오류")
            return {"error": f"예상치 못한 오류: {e}"}

    # ------------------------------------------------------------------ #
    # 일자별 조문 개정이력 (target=lsJoHstInf) — lawSearch.do
    # ------------------------------------------------------------------ #

    async def search_article_change_history(
        self,
        query: Optional[str] = None,
        law_id: Optional[str] = None,
        reg_dt: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        arguments: Optional[dict] = None,
    ) -> dict:
        """일자별 조문 개정이력 목록 검색 (target=lsJoHstInf, lawSearch.do)."""
        cache_key = ("lsJoHstInf_search", query or "", law_id or "", reg_dt or "", page, per_page)
        if cache_key in search_cache:
            return search_cache[cache_key]
        if cache_key in failure_cache:
            return failure_cache[cache_key]

        try:
            params: dict = {
                "target": "lsJoHstInf",
                "type": "JSON",
                "page": page,
                "display": per_page,
            }
            if query:
                params["query"] = self.normalize_search_query(query)
            if law_id:
                params["lsId"] = law_id
            if reg_dt:
                params["regDt"] = reg_dt

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
                    if isinstance(v, dict) and "lsJoHstInf" in v:
                        try:
                            total = int(v.get("totalCnt", 0))
                        except (TypeError, ValueError):
                            total = 0
                        items = v.get("lsJoHstInf", [])
                        break
                else:
                    try:
                        total = int(data.get("totalCnt", 0))
                    except (TypeError, ValueError):
                        total = 0
                    items = data.get("lsJoHstInf", [])
                if not isinstance(items, list):
                    items = [items] if items else []

            result = {
                "query": query,
                "law_id": law_id,
                "reg_dt": reg_dt,
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
            logger.exception("search_article_change_history 오류")
            return {"error": f"예상치 못한 오류: {e}"}

    # ------------------------------------------------------------------ #
    # 조문별 변경이력 (target=lsJoHstInf) — lawService.do
    # ------------------------------------------------------------------ #

    async def get_article_change_history(
        self,
        law_id: str,
        jo_no: Optional[str] = None,
        arguments: Optional[dict] = None,
    ) -> dict:
        """조문별 변경이력 조회 (target=lsJoHstInf, lawService.do).

        Args:
            law_id: 법령 ID (lsId)
            jo_no: 조문 번호 (joNo, 예: '000100')
            arguments: API 키 등 추가 인자
        """
        cache_key = ("lsJoHstInf_detail", law_id, jo_no or "")
        if cache_key in search_cache:
            return search_cache[cache_key]
        if cache_key in failure_cache:
            return failure_cache[cache_key]

        try:
            params: dict = {
                "target": "lsJoHstInf",
                "type": "JSON",
                "lsId": law_id,
            }
            if jo_no:
                params["joNo"] = jo_no

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

            result = {
                "law_id": law_id,
                "jo_no": jo_no,
                "data": data,
                "api_url": str(response.url),
            }
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
            logger.exception("get_article_change_history 오류")
            return {"error": f"예상치 못한 오류: {e}"}
