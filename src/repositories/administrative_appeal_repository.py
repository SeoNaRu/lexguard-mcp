"""
Administrative Appeal Repository - 행정심판 검색 및 조회 기능
"""
import requests
import json
from typing import Optional
from .base import BaseLawRepository, logger, LAW_API_SEARCH_URL, LAW_API_BASE_URL, search_cache, failure_cache


class AdministrativeAppealRepository(BaseLawRepository):
    """행정심판 검색 및 조회 관련 기능을 담당하는 Repository"""
    
    def search_administrative_appeal(
        self,
        query: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        arguments: Optional[dict] = None
    ) -> dict:
        """행정심판을 검색합니다."""
        logger.debug("search_administrative_appeal called | query=%r page=%d per_page=%d", query, page, per_page)
        
        if per_page < 1:
            per_page = 1
        if per_page > 100:
            per_page = 100
        
        cache_key = ("administrative_appeal", query or "", page, per_page, date_from or "", date_to or "")
        
        if cache_key in search_cache:
            return search_cache[cache_key]
        if cache_key in failure_cache:
            return failure_cache[cache_key]
        
        try:
            params = {
                "target": "decc",
                "type": "JSON",
                "page": page,
                "display": per_page
            }
            
            if query:
                params["query"] = self.normalize_search_query(query)
            
            if date_from and date_to:
                params["deccYd"] = f"{date_from}~{date_to}"
            elif date_from:
                params["deccYd"] = f"{date_from}~{date_from}"
            elif date_to:
                params["deccYd"] = f"{date_to}~{date_to}"
            
            _, api_key_error = self.attach_api_key(params, arguments, LAW_API_SEARCH_URL)
            if api_key_error:
                return api_key_error
            
            response = requests.get(LAW_API_SEARCH_URL, params=params, timeout=10)
            response.raise_for_status()
            
            invalid_response = self.validate_drf_response(response)
            if invalid_response:
                return invalid_response
            
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                return {
                    "error": f"API 응답이 유효한 JSON 형식이 아닙니다: {str(e)}",
                    "query": query,
                    "api_url": response.url,
                    "recovery_guide": "API 응답 형식 오류입니다. API 서버 상태를 확인하거나 잠시 후 다시 시도하세요."
                }
            
            result = {
                "query": query,
                "page": page,
                "per_page": per_page,
                "total": 0,
                "appeals": [],
                "api_url": response.url
            }
            
            if isinstance(data, dict):
                if "DeccSearch" in data:
                    decc_search = data["DeccSearch"]
                    if isinstance(decc_search, dict):
                        result["total"] = decc_search.get("totalCnt", 0)
                        appeals = decc_search.get("decc", [])
                    else:
                        appeals = []
                elif "decc" in data:
                    result["total"] = data.get("totalCnt", 0)
                    appeals = data.get("decc", [])
                else:
                    result["total"] = data.get("totalCnt", 0)
                    appeals = data.get("decc", [])
                
                if not isinstance(appeals, list):
                    appeals = [appeals] if appeals else []
                
                result["appeals"] = appeals[:per_page]
            
            search_cache[cache_key] = result
            return result
            
        except requests.exceptions.Timeout:
            error_result = {
                "error": "API 호출 타임아웃",
                "recovery_guide": "네트워크 응답 시간이 초과되었습니다. 잠시 후 다시 시도하거나, 인터넷 연결을 확인하세요."
            }
            failure_cache[cache_key] = error_result
            return error_result
        except requests.exceptions.RequestException as e:
            error_result = {
                "error": f"API 요청 실패: {str(e)}",
                "recovery_guide": "네트워크 오류입니다. 잠시 후 다시 시도하거나, 인터넷 연결을 확인하세요."
            }
            failure_cache[cache_key] = error_result
            return error_result
        except Exception as e:
            logger.exception("예상치 못한 오류")
            return {
                "error": f"예상치 못한 오류: {str(e)}",
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }
    
    def get_administrative_appeal(
        self,
        appeal_id: str,
        arguments: Optional[dict] = None
    ) -> dict:
        """행정심판 상세 정보를 조회합니다."""
        logger.debug("get_administrative_appeal called | appeal_id=%r", appeal_id)
        
        cache_key = ("administrative_appeal_detail", appeal_id)
        
        if cache_key in search_cache:
            return search_cache[cache_key]
        if cache_key in failure_cache:
            return failure_cache[cache_key]
        
        try:
            params = {
                "target": "decc",
                "type": "JSON",
                "ID": appeal_id
            }
            
            _, api_key_error = self.attach_api_key(params, arguments, LAW_API_BASE_URL)
            if api_key_error:
                return api_key_error
            
            response = requests.get(LAW_API_BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            
            invalid_response = self.validate_drf_response(response)
            if invalid_response:
                return invalid_response
            
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                return {
                    "error": f"API 응답이 유효한 JSON 형식이 아닙니다: {str(e)}",
                    "appeal_id": appeal_id,
                    "api_url": response.url
                }
            
            result = {
                "appeal_id": appeal_id,
                "appeal": data,
                "api_url": response.url
            }
            
            search_cache[cache_key] = result
            return result
            
        except requests.exceptions.Timeout:
            error_result = {
                "error": "API 호출 타임아웃",
                "appeal_id": appeal_id,
                "recovery_guide": "네트워크 응답 시간이 초과되었습니다. 잠시 후 다시 시도하거나, 인터넷 연결을 확인하세요."
            }
            failure_cache[cache_key] = error_result
            return error_result
        except requests.exceptions.RequestException as e:
            error_result = {"error": f"API 요청 실패: {str(e)}", "appeal_id": appeal_id}
            failure_cache[cache_key] = error_result
            return error_result
        except Exception as e:
            logger.exception("예상치 못한 오류")
            return {
                "error": f"예상치 못한 오류: {str(e)}",
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }

