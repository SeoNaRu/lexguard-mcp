"""
Administrative Rule Repository - 행정규칙 검색 기능
"""
import requests
import json
from typing import Optional
from .base import BaseLawRepository, logger, LAW_API_SEARCH_URL, search_cache, failure_cache


class AdministrativeRuleRepository(BaseLawRepository):
    """행정규칙 검색 관련 기능을 담당하는 Repository"""
    
    def search_administrative_rule(
        self,
        query: Optional[str] = None,
        agency: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        arguments: Optional[dict] = None
    ) -> dict:
        """행정규칙을 검색합니다."""
        logger.debug("search_administrative_rule called | query=%r agency=%r page=%d per_page=%d", 
                    query, agency, page, per_page)
        
        if per_page < 1:
            per_page = 1
        if per_page > 100:
            per_page = 100
        
        cache_key = ("administrative_rule", query or "", agency or "", page, per_page)
        
        if cache_key in search_cache:
            return search_cache[cache_key]
        if cache_key in failure_cache:
            return failure_cache[cache_key]
        
        api_key = self.get_api_key(arguments)
        
        try:
            params = {
                "target": "admrul",
                "type": "JSON",
                "page": page,
                "display": per_page
            }
            
            if query:
                params["query"] = self.normalize_search_query(query)
            
            if agency:
                # 부처명을 기관코드로 변환 (간단한 매핑)
                agency_code_map = {
                    "고용노동부": "100000",
                    "교육부": "200000",
                    "기획재정부": "300000",
                    # 필요시 더 추가
                }
                if agency in agency_code_map:
                    params["orgCd"] = agency_code_map[agency]
            
            if api_key:
                params["OC"] = api_key
            
            response = requests.get(LAW_API_SEARCH_URL, params=params, timeout=10)
            response.raise_for_status()
            
            if response.text.strip().startswith('<!DOCTYPE') or '<html' in response.text.lower():
                return {
                    "error": "API가 HTML 에러 페이지를 반환했습니다.",
                    "query": query,
                    "agency": agency,
                    "api_url": response.url
                }
            
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                return {
                    "error": f"API 응답이 유효한 JSON 형식이 아닙니다: {str(e)}",
                    "query": query,
                    "agency": agency,
                    "api_url": response.url,
                    "recovery_guide": "API 응답 형식 오류입니다. API 서버 상태를 확인하거나 잠시 후 다시 시도하세요."
                }
            
            result = {
                "query": query,
                "agency": agency,
                "page": page,
                "per_page": per_page,
                "total": 0,
                "rules": [],
                "api_url": response.url
            }
            
            if isinstance(data, dict):
                if "AdmrulSearch" in data:
                    admrul_search = data["AdmrulSearch"]
                    if isinstance(admrul_search, dict):
                        result["total"] = admrul_search.get("totalCnt", 0)
                        rules = admrul_search.get("admrul", [])
                    else:
                        rules = []
                elif "admrul" in data:
                    result["total"] = data.get("totalCnt", 0)
                    rules = data.get("admrul", [])
                else:
                    result["total"] = data.get("totalCnt", 0)
                    rules = data.get("admrul", [])
                
                if not isinstance(rules, list):
                    rules = [rules] if rules else []
                
                result["rules"] = rules[:per_page]
            
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

