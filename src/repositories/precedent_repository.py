"""
Precedent Repository - 판례 검색 및 조회 기능
"""
import requests
import json
from typing import Optional
from .base import BaseLawRepository, logger, LAW_API_SEARCH_URL, LAW_API_BASE_URL, search_cache, failure_cache


class PrecedentRepository(BaseLawRepository):
    """판례 검색 및 조회 관련 기능을 담당하는 Repository"""
    
    def search_precedent(
        self,
        query: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        court: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        arguments: Optional[dict] = None
    ) -> dict:
        """
        판례를 검색합니다.
        
        Args:
            query: 검색어 (판례명 또는 키워드)
            page: 페이지 번호 (기본값: 1)
            per_page: 페이지당 결과 수 (기본값: 20, 최대: 100)
            court: 법원 종류 (대법원:400201, 하위법원:400202)
            date_from: 시작일자 (YYYYMMDD)
            date_to: 종료일자 (YYYYMMDD)
            arguments: 추가 인자 (API 키 등)
            
        Returns:
            검색 결과 딕셔너리 또는 {"error": "error message"}
        """
        logger.debug("search_precedent called | query=%r page=%d per_page=%d", query, page, per_page)
        
        if per_page < 1:
            per_page = 1
        if per_page > 100:
            per_page = 100
        
        cache_key = ("precedent", query or "", page, per_page, court or "", date_from or "", date_to or "")
        
        if cache_key in search_cache:
            logger.debug("Cache hit for precedent search")
            return search_cache[cache_key]
        
        if cache_key in failure_cache:
            logger.debug("Failure cache hit, skipping")
            return failure_cache[cache_key]
        
        api_key = self.get_api_key(arguments)
        
        try:
            params = {
                "target": "prec",
                "type": "JSON",
                "page": page,
                "display": per_page
            }
            
            if query:
                params["query"] = self.normalize_search_query(query)
            
            if court:
                params["org"] = court
            
            if date_from and date_to:
                params["prncYd"] = f"{date_from}~{date_to}"
            elif date_from:
                params["prncYd"] = f"{date_from}~{date_from}"
            elif date_to:
                params["prncYd"] = f"{date_to}~{date_to}"
            
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
                    "note": "국가법령정보센터 OPEN API 사용을 위해서는 https://open.law.go.kr 에서 회원가입 및 API 활용 신청이 필요합니다.",
                    "recovery_guide": "API 키가 필요합니다. 사용자에게 API 키를 요청하거나, API 키를 환경변수(LAW_API_KEY)로 설정하세요."
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
                    "raw_response": response.text[:500]
                }
            
            result = {
                "query": query,
                "page": page,
                "per_page": per_page,
                "total": 0,
                "precedents": [],
                "api_url": response.url
            }
            
            # JSON 구조 파싱
            if isinstance(data, dict):
                if "PrecSearch" in data:
                    prec_search = data["PrecSearch"]
                    if isinstance(prec_search, dict):
                        result["total"] = prec_search.get("totalCnt", 0)
                        precedents = prec_search.get("prec", [])
                    else:
                        precedents = []
                elif "prec" in data:
                    result["total"] = data.get("totalCnt", 0)
                    precedents = data.get("prec", [])
                else:
                    result["total"] = data.get("totalCnt", 0)
                    precedents = data.get("prec", [])
                
                if not isinstance(precedents, list):
                    precedents = [precedents] if precedents else []
                
                result["precedents"] = precedents[:per_page]
            
            if result["total"] == 0:
                result["message"] = "검색 결과가 없습니다."
            
            search_cache[cache_key] = result
            logger.debug("API call successful for precedent search | total=%d", result["total"])
            
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
    
    def get_precedent(
        self,
        precedent_id: Optional[str] = None,
        case_number: Optional[str] = None,
        arguments: Optional[dict] = None
    ) -> dict:
        """
        판례 상세 정보를 조회합니다.
        
        Args:
            precedent_id: 판례 일련번호
            case_number: 사건번호 (precedent_id와 둘 중 하나는 필수)
            arguments: 추가 인자 (API 키 등)
            
        Returns:
            판례 상세 정보 딕셔너리 또는 {"error": "error message"}
        """
        logger.debug("get_precedent called | precedent_id=%r case_number=%r", precedent_id, case_number)
        
        if not precedent_id and not case_number:
            return {
                "error": "precedent_id 또는 case_number 중 하나는 필수입니다.",
                "recovery_guide": "판례 일련번호(precedent_id) 또는 사건번호(case_number) 중 하나를 입력해주세요."
            }
        
        # case_number로 검색해서 precedent_id 찾기
        if case_number and not precedent_id:
            search_result = self.search_precedent(query=case_number, per_page=1, arguments=arguments)
            if "error" in search_result:
                return search_result
            
            precedents = search_result.get("precedents", [])
            if precedents and isinstance(precedents[0], dict):
                # 사건번호로 매칭
                for prec in precedents:
                    if prec.get("사건번호") == case_number or prec.get("사건번호", "").endswith(case_number):
                        precedent_id = (prec.get("판례정보일련번호") or 
                                       prec.get("일련번호") or
                                       prec.get("id"))
                        break
                
                if not precedent_id and precedents:
                    # 첫 번째 결과 사용
                    precedent_id = (precedents[0].get("판례정보일련번호") or 
                                   precedents[0].get("일련번호") or
                                   precedents[0].get("id"))
            
            if not precedent_id:
                return {
                    "error": "판례 ID를 찾을 수 없습니다.",
                    "case_number": case_number
                }
        
        cache_key = ("precedent_detail", precedent_id)
        
        if cache_key in search_cache:
            logger.debug("Cache hit for precedent detail")
            return search_cache[cache_key]
        
        if cache_key in failure_cache:
            logger.debug("Failure cache hit, skipping")
            return failure_cache[cache_key]
        
        api_key = self.get_api_key(arguments)
        
        try:
            params = {
                "target": "prec",
                "type": "JSON",
                "ID": precedent_id
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
                    "precedent_id": precedent_id,
                    "api_url": response.url
                }
            
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                error_msg = f"API 응답이 유효한 JSON 형식이 아닙니다: {str(e)}"
                logger.error("Invalid JSON response | error=%s", str(e))
                return {
                    "error": error_msg,
                    "precedent_id": precedent_id,
                    "api_url": response.url
                }
            
            result = {
                "precedent_id": precedent_id,
                "precedent": data,
                "api_url": response.url
            }
            
            search_cache[cache_key] = result
            logger.debug("API call successful for precedent detail")
            
            return result
            
        except requests.exceptions.Timeout:
            error_msg = "API 호출 타임아웃"
            logger.error(error_msg)
            error_result = {
                "error": error_msg,
                "precedent_id": precedent_id,
                "recovery_guide": "네트워크 응답 시간이 초과되었습니다. 잠시 후 다시 시도하거나, 인터넷 연결을 확인하세요."
            }
            failure_cache[cache_key] = error_result
            return error_result
        except requests.exceptions.RequestException as e:
            error_msg = f"API 요청 실패: {str(e)}"
            logger.error(error_msg)
            error_result = {"error": error_msg, "precedent_id": precedent_id}
            failure_cache[cache_key] = error_result
            return error_result
        except Exception as e:
            error_msg = f"예상치 못한 오류: {str(e)}"
            logger.exception(error_msg)
            return {
                "error": error_msg,
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }

