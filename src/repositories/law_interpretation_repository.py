"""
Law Interpretation Repository - 법령해석 검색 및 조회 기능
"""
import requests
import json
from typing import Optional
from .base import BaseLawRepository, logger, LAW_API_SEARCH_URL, LAW_API_BASE_URL, search_cache, failure_cache


class LawInterpretationRepository(BaseLawRepository):
    """법령해석 검색 및 조회 관련 기능을 담당하는 Repository"""
    
    def search_law_interpretation(
        self,
        query: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        agency: Optional[str] = None,
        arguments: Optional[dict] = None
    ) -> dict:
        """
        법령해석을 검색합니다.
        
        Args:
            query: 검색어 (법령해석명 또는 키워드)
            page: 페이지 번호 (기본값: 1)
            per_page: 페이지당 결과 수 (기본값: 20, 최대: 100)
            agency: 부처명 (예: '고용노동부', '국세청')
            arguments: 추가 인자 (API 키 등)
            
        Returns:
            검색 결과 딕셔너리 또는 {"error": "error message"}
        """
        logger.debug("search_law_interpretation called | query=%r page=%d per_page=%d agency=%r", 
                    query, page, per_page, agency)
        
        if per_page < 1:
            per_page = 1
        if per_page > 100:
            per_page = 100
        
        cache_key = ("law_interpretation", query or "", page, per_page, agency or "")
        
        if cache_key in search_cache:
            logger.debug("Cache hit for law interpretation search")
            return search_cache[cache_key]
        
        if cache_key in failure_cache:
            logger.debug("Failure cache hit, skipping")
            return failure_cache[cache_key]
        
        api_key = self.get_api_key(arguments)
        
        try:
            params = {
                "target": "expc",
                "type": "JSON",
                "page": page,
                "display": per_page
            }
            
            if query:
                params["query"] = self.normalize_search_query(query)
            
            # 부처명이 있으면 질의기관코드로 변환 (간단한 매핑)
            if agency:
                # 부처명을 기관코드로 변환하는 로직 (필요시 확장)
                agency_code_map = {
                    "고용노동부": "100000",
                    "국세청": "200000",
                    "기획재정부": "300000",
                    # 필요시 더 추가
                }
                if agency in agency_code_map:
                    params["inq"] = agency_code_map[agency]
            
            if api_key:
                params["OC"] = api_key
            
            response = requests.get(LAW_API_SEARCH_URL, params=params, timeout=10)
            response.raise_for_status()
            
            if response.text.strip().startswith('<!DOCTYPE') or '<html' in response.text.lower():
                error_msg = "API가 HTML 에러 페이지를 반환했습니다. API 키가 유효하지 않거나 API 사용 권한이 없을 수 있습니다."
                logger.error("API returned HTML error page")
                return {
                    "error": error_msg,
                    "query": query,
                    "api_url": response.url,
                    "note": "국가법령정보센터 OPEN API 사용을 위해서는 https://open.law.go.kr 에서 회원가입 및 API 활용 신청이 필요합니다."
                }
            
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                error_msg = f"API 응답이 유효한 JSON 형식이 아닙니다: {str(e)}"
                logger.error("Invalid JSON response | error=%s", str(e))
                return {
                    "error": error_msg,
                    "query": query,
                    "api_url": response.url,
                    "raw_response": response.text[:500],
                    "recovery_guide": "API 응답 형식 오류입니다. API 서버 상태를 확인하거나 잠시 후 다시 시도하세요."
                }
            
            result = {
                "query": query,
                "page": page,
                "per_page": per_page,
                "agency": agency,
                "total": 0,
                "interpretations": [],
                "api_url": response.url
            }
            
            # JSON 구조 파싱
            if isinstance(data, dict):
                if "ExpcSearch" in data:
                    expc_search = data["ExpcSearch"]
                    if isinstance(expc_search, dict):
                        result["total"] = expc_search.get("totalCnt", 0)
                        interpretations = expc_search.get("expc", [])
                    else:
                        interpretations = []
                elif "expc" in data:
                    result["total"] = data.get("totalCnt", 0)
                    interpretations = data.get("expc", [])
                else:
                    result["total"] = data.get("totalCnt", 0)
                    interpretations = data.get("expc", [])
                
                if not isinstance(interpretations, list):
                    interpretations = [interpretations] if interpretations else []
                
                result["interpretations"] = interpretations[:per_page]
            
            if result["total"] == 0:
                result["message"] = "검색 결과가 없습니다."
            
            search_cache[cache_key] = result
            logger.debug("API call successful for law interpretation search | total=%d", result["total"])
            
            return result
            
        except requests.exceptions.Timeout:
            error_msg = "API 호출 타임아웃"
            logger.error(error_msg)
            error_result = {
                "error": error_msg,
                "recovery_guide": "네트워크 응답 시간이 초과되었습니다. 잠시 후 다시 시도하거나, 인터넷 연결을 확인하세요."
            }
            failure_cache[cache_key] = error_result
            return error_result
        except requests.exceptions.RequestException as e:
            error_msg = f"API 요청 실패: {str(e)}"
            logger.error(error_msg)
            error_result = {
                "error": error_msg,
                "recovery_guide": "네트워크 오류입니다. 잠시 후 다시 시도하거나, 인터넷 연결을 확인하세요."
            }
            failure_cache[cache_key] = error_result
            return error_result
        except Exception as e:
            error_msg = f"예상치 못한 오류: {str(e)}"
            logger.exception(error_msg)
            return {
                "error": error_msg,
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }
    
    def get_law_interpretation(
        self,
        interpretation_id: str,
        arguments: Optional[dict] = None
    ) -> dict:
        """
        법령해석 상세 정보를 조회합니다.
        
        Args:
            interpretation_id: 법령해석 일련번호
            arguments: 추가 인자 (API 키 등)
            
        Returns:
            법령해석 상세 정보 딕셔너리 또는 {"error": "error message"}
        """
        logger.debug("get_law_interpretation called | interpretation_id=%r", interpretation_id)
        
        cache_key = ("law_interpretation_detail", interpretation_id)
        
        if cache_key in search_cache:
            logger.debug("Cache hit for law interpretation detail")
            return search_cache[cache_key]
        
        if cache_key in failure_cache:
            logger.debug("Failure cache hit, skipping")
            return failure_cache[cache_key]
        
        api_key = self.get_api_key(arguments)
        
        try:
            params = {
                "target": "expc",
                "type": "JSON",
                "ID": interpretation_id
            }
            
            if api_key:
                params["OC"] = api_key
            
            response = requests.get(LAW_API_BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            
            if response.text.strip().startswith('<!DOCTYPE') or '<html' in response.text.lower():
                error_msg = "API가 HTML 에러 페이지를 반환했습니다."
                logger.error("API returned HTML error page")
                return {
                    "error": error_msg,
                    "interpretation_id": interpretation_id,
                    "api_url": response.url
                }
            
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                error_msg = f"API 응답이 유효한 JSON 형식이 아닙니다: {str(e)}"
                logger.error("Invalid JSON response | error=%s", str(e))
                return {
                    "error": error_msg,
                    "interpretation_id": interpretation_id,
                    "api_url": response.url
                }
            
            result = {
                "interpretation_id": interpretation_id,
                "interpretation": data,
                "api_url": response.url
            }
            
            search_cache[cache_key] = result
            logger.debug("API call successful for law interpretation detail")
            
            return result
            
        except requests.exceptions.Timeout:
            error_msg = "API 호출 타임아웃"
            logger.error(error_msg)
            error_result = {
                "error": error_msg,
                "interpretation_id": interpretation_id,
                "recovery_guide": "네트워크 응답 시간이 초과되었습니다. 잠시 후 다시 시도하거나, 인터넷 연결을 확인하세요."
            }
            failure_cache[cache_key] = error_result
            return error_result
        except requests.exceptions.RequestException as e:
            error_msg = f"API 요청 실패: {str(e)}"
            logger.error(error_msg)
            error_result = {"error": error_msg, "interpretation_id": interpretation_id}
            failure_cache[cache_key] = error_result
            return error_result
        except Exception as e:
            error_msg = f"예상치 못한 오류: {str(e)}"
            logger.exception(error_msg)
            return {
                "error": error_msg,
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }

