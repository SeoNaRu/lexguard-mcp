"""
Special Administrative Appeal Repository - 특별행정심판 검색 및 조회 기능
"""
import requests
import json
from typing import Optional
from .base import BaseLawRepository, logger, LAW_API_SEARCH_URL, LAW_API_BASE_URL, search_cache, failure_cache


# 특별행정심판원 타입별 target 매핑 (API 문서 기준)
TRIBUNAL_TARGET_MAP = {
    "조세심판원": "ttSpecialDecc",  # API 문서: target=ttSpecialDecc
    "해양안전심판원": "kmstSpecialDecc",  # API 문서: target=kmstSpecialDecc
    "국민권익위원회": "acrSpecialDecc",  # API 문서: target=acrSpecialDecc
    "인사혁신처 소청심사위원회": "adapSpecialDecc",  # API 문서: target=adapSpecialDecc
}


class SpecialAdministrativeAppealRepository(BaseLawRepository):
    """특별행정심판 검색 및 조회 관련 기능을 담당하는 Repository"""
    
    def search_special_administrative_appeal(
        self,
        tribunal_type: str,
        query: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        arguments: Optional[dict] = None
    ) -> dict:
        """특별행정심판을 검색합니다."""
        logger.debug("search_special_administrative_appeal called | tribunal_type=%r query=%r page=%d per_page=%d", 
                    tribunal_type, query, page, per_page)
        
        if per_page < 1:
            per_page = 1
        if per_page > 100:
            per_page = 100
        
        target = TRIBUNAL_TARGET_MAP.get(tribunal_type)
        if not target:
            return {
                "error": f"지원하지 않는 심판원 종류입니다: {tribunal_type}",
                "supported_tribunals": list(TRIBUNAL_TARGET_MAP.keys())
            }
        
        cache_key = ("special_administrative_appeal", tribunal_type, query or "", page, per_page)
        
        if cache_key in search_cache:
            return search_cache[cache_key]
        if cache_key in failure_cache:
            return failure_cache[cache_key]
        
        try:
            params = {
                "target": target,
                "type": "JSON",
                "page": page,
                "display": per_page
            }
            
            if query:
                params["query"] = self.normalize_search_query(query)
            
            _, api_key_error = self.attach_api_key(params, arguments, LAW_API_SEARCH_URL)
            if api_key_error:
                return api_key_error
            
            response = requests.get(LAW_API_SEARCH_URL, params=params, timeout=10)
            
            if not response.text or not response.text.strip():
                return {
                    "error": "API가 빈 응답을 반환했습니다. API 키가 필요하거나 권한이 없을 수 있습니다.",
                    "tribunal_type": tribunal_type,
                    "query": query,
                    "api_url": response.url,
                    "note": "국가법령정보센터 OPEN API 사용을 위해서는 https://open.law.go.kr 에서 회원가입 및 API 활용 신청이 필요합니다."
                }
            
            invalid_response = self.validate_drf_response(response)
            if invalid_response:
                return invalid_response
            response.raise_for_status()
            
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                return {
                    "error": f"API 응답이 유효한 JSON 형식이 아닙니다: {str(e)}",
                    "tribunal_type": tribunal_type,
                    "query": query,
                    "api_url": response.url,
                    "recovery_guide": "API 응답 형식 오류입니다. API 서버 상태를 확인하거나 잠시 후 다시 시도하세요.",
                    "raw_response": response.text[:200] if response.text else "Empty response"
                }
            
            result = {
                "tribunal_type": tribunal_type,
                "query": query,
                "page": page,
                "per_page": per_page,
                "total": 0,
                "appeals": [],
                "api_url": response.url
            }
            
            if isinstance(data, dict):
                # 특별행정심판별로 다른 래퍼 구조 확인
                if "TtSpecialDeccSearch" in data:
                    search_wrapper = data["TtSpecialDeccSearch"]
                    if isinstance(search_wrapper, dict):
                        result["total"] = search_wrapper.get("totalCnt", 0)
                        appeals = search_wrapper.get("ttSpecialDecc", [])
                    else:
                        appeals = []
                elif "ttSpecialDecc" in data:
                    result["total"] = data.get("totalCnt", 0)
                    appeals = data.get("ttSpecialDecc", [])
                elif "KmstSpecialDeccSearch" in data:
                    search_wrapper = data["KmstSpecialDeccSearch"]
                    if isinstance(search_wrapper, dict):
                        result["total"] = search_wrapper.get("totalCnt", 0)
                        appeals = search_wrapper.get("kmstSpecialDecc", [])
                    else:
                        appeals = []
                elif "kmstSpecialDecc" in data:
                    result["total"] = data.get("totalCnt", 0)
                    appeals = data.get("kmstSpecialDecc", [])
                elif "AdapSpecialDeccSearch" in data:
                    search_wrapper = data["AdapSpecialDeccSearch"]
                    if isinstance(search_wrapper, dict):
                        result["total"] = search_wrapper.get("totalCnt", 0)
                        appeals = search_wrapper.get("adapSpecialDecc", [])
                    else:
                        appeals = []
                elif "adapSpecialDecc" in data:
                    result["total"] = data.get("totalCnt", 0)
                    appeals = data.get("adapSpecialDecc", [])
                else:
                    result["total"] = data.get("totalCnt", 0)
                    # 다양한 키 시도
                    appeals = (data.get("decc", []) or 
                              data.get("dec", []) or 
                              data.get("ttSpecialDecc", []) or
                              data.get("kmstSpecialDecc", []) or
                              data.get("adapSpecialDecc", []) or
                              data.get("data", []))
                
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
    
    def get_special_administrative_appeal(
        self,
        tribunal_type: str,
        appeal_id: str,
        arguments: Optional[dict] = None
    ) -> dict:
        """특별행정심판 상세 정보를 조회합니다."""
        logger.debug("get_special_administrative_appeal called | tribunal_type=%r appeal_id=%r", tribunal_type, appeal_id)
        
        target = TRIBUNAL_TARGET_MAP.get(tribunal_type)
        if not target:
            return {
                "error": f"지원하지 않는 심판원 종류입니다: {tribunal_type}",
                "supported_tribunals": list(TRIBUNAL_TARGET_MAP.keys())
            }
        
        cache_key = ("special_administrative_appeal_detail", tribunal_type, appeal_id)
        
        if cache_key in search_cache:
            return search_cache[cache_key]
        if cache_key in failure_cache:
            return failure_cache[cache_key]
        
        try:
            params = {
                "target": target,
                "type": "JSON",
                "ID": appeal_id
            }
            
            _, api_key_error = self.attach_api_key(params, arguments, LAW_API_BASE_URL)
            if api_key_error:
                return api_key_error
            
            response = requests.get(LAW_API_BASE_URL, params=params, timeout=10)
            
            invalid_response = self.validate_drf_response(response)
            if invalid_response:
                return invalid_response
            response.raise_for_status()
            
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                return {
                    "error": f"API 응답이 유효한 JSON 형식이 아닙니다: {str(e)}",
                    "tribunal_type": tribunal_type,
                    "appeal_id": appeal_id,
                    "api_url": response.url
                }
            
            result = {
                "tribunal_type": tribunal_type,
                "appeal_id": appeal_id,
                "appeal": data,
                "api_url": response.url
            }
            
            search_cache[cache_key] = result
            return result
            
        except requests.exceptions.Timeout:
            error_result = {
                "error": "API 호출 타임아웃",
                "tribunal_type": tribunal_type,
                "appeal_id": appeal_id,
                "recovery_guide": "네트워크 응답 시간이 초과되었습니다. 잠시 후 다시 시도하거나, 인터넷 연결을 확인하세요."
            }
            failure_cache[cache_key] = error_result
            return error_result
        except requests.exceptions.RequestException as e:
            error_result = {"error": f"API 요청 실패: {str(e)}", "tribunal_type": tribunal_type, "appeal_id": appeal_id}
            failure_cache[cache_key] = error_result
            return error_result
        except Exception as e:
            logger.exception("예상치 못한 오류")
            return {
                "error": f"예상치 못한 오류: {str(e)}",
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }

