"""
Constitutional Decision Repository - 헌재결정 검색 및 조회 기능
"""
import requests
import json
from typing import Optional
from .base import BaseLawRepository, logger, LAW_API_SEARCH_URL, LAW_API_BASE_URL, search_cache, failure_cache


class ConstitutionalDecisionRepository(BaseLawRepository):
    """헌재결정 검색 및 조회 관련 기능을 담당하는 Repository"""
    
    def search_constitutional_decision(
        self,
        query: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        arguments: Optional[dict] = None
    ) -> dict:
        """헌재결정을 검색합니다."""
        logger.debug("search_constitutional_decision called | query=%r page=%d per_page=%d", query, page, per_page)
        
        if per_page < 1:
            per_page = 1
        if per_page > 100:
            per_page = 100
        
        cache_key = ("constitutional_decision", query or "", page, per_page, date_from or "", date_to or "")
        
        if cache_key in search_cache:
            return search_cache[cache_key]
        if cache_key in failure_cache:
            return failure_cache[cache_key]
        
        api_key = self.get_api_key(arguments)
        
        try:
            params = {
                "target": "detc",
                "type": "JSON",
                "page": page,
                "display": per_page
            }
            
            if query:
                params["query"] = self.normalize_search_query(query)
            
            if date_from and date_to:
                params["detcYd"] = f"{date_from}~{date_to}"
            elif date_from:
                params["detcYd"] = f"{date_from}~{date_from}"
            elif date_to:
                params["detcYd"] = f"{date_to}~{date_to}"
            
            if api_key:
                params["OC"] = api_key
            
            response = requests.get(LAW_API_SEARCH_URL, params=params, timeout=10)
            response.raise_for_status()
            
            if response.text.strip().startswith('<!DOCTYPE') or '<html' in response.text.lower():
                return {
                    "error": "API가 HTML 에러 페이지를 반환했습니다.",
                    "query": query,
                    "api_url": response.url,
                    "recovery_guide": "API 키가 필요합니다. 사용자에게 API 키를 요청하거나, API 키를 환경변수(LAW_API_KEY)로 설정하세요."
                }
            
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
                "decisions": [],
                "api_url": response.url
            }
            
            if isinstance(data, dict):
                if "DetcSearch" in data:
                    detc_search = data["DetcSearch"]
                    if isinstance(detc_search, dict):
                        result["total"] = detc_search.get("totalCnt", 0)
                        decisions = detc_search.get("detc", [])
                    else:
                        decisions = []
                elif "detc" in data:
                    result["total"] = data.get("totalCnt", 0)
                    decisions = data.get("detc", [])
                else:
                    result["total"] = data.get("totalCnt", 0)
                    decisions = data.get("detc", [])
                
                if not isinstance(decisions, list):
                    decisions = [decisions] if decisions else []
                
                result["decisions"] = decisions[:per_page]
            
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
    
    def get_constitutional_decision(
        self,
        decision_id: str,
        arguments: Optional[dict] = None
    ) -> dict:
        """헌재결정 상세 정보를 조회합니다."""
        logger.debug("get_constitutional_decision called | decision_id=%r", decision_id)
        
        cache_key = ("constitutional_decision_detail", decision_id)
        
        if cache_key in search_cache:
            return search_cache[cache_key]
        if cache_key in failure_cache:
            return failure_cache[cache_key]
        
        api_key = self.get_api_key(arguments)
        
        try:
            params = {
                "target": "detc",
                "type": "JSON",
                "ID": decision_id
            }
            
            if api_key:
                params["OC"] = api_key
            
            response = requests.get(LAW_API_BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            
            if response.text.strip().startswith('<!DOCTYPE') or '<html' in response.text.lower():
                return {
                    "error": "API가 HTML 에러 페이지를 반환했습니다.",
                    "decision_id": decision_id,
                    "api_url": response.url,
                    "recovery_guide": "API 키가 필요합니다. 사용자에게 API 키를 요청하거나, API 키를 환경변수(LAW_API_KEY)로 설정하세요."
                }
            
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                return {
                    "error": f"API 응답이 유효한 JSON 형식이 아닙니다: {str(e)}",
                    "decision_id": decision_id,
                    "api_url": response.url,
                    "recovery_guide": "API 응답 형식 오류입니다. API 서버 상태를 확인하거나 잠시 후 다시 시도하세요."
                }
            
            result = {
                "decision_id": decision_id,
                "decision": data,
                "api_url": response.url
            }
            
            search_cache[cache_key] = result
            return result
            
        except requests.exceptions.Timeout:
            error_result = {
                "error": "API 호출 타임아웃",
                "decision_id": decision_id,
                "recovery_guide": "네트워크 응답 시간이 초과되었습니다. 잠시 후 다시 시도하거나, 인터넷 연결을 확인하세요."
            }
            failure_cache[cache_key] = error_result
            return error_result
        except requests.exceptions.RequestException as e:
            error_result = {"error": f"API 요청 실패: {str(e)}", "decision_id": decision_id}
            failure_cache[cache_key] = error_result
            return error_result
        except Exception as e:
            logger.exception("예상치 못한 오류")
            return {
                "error": f"예상치 못한 오류: {str(e)}",
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }

