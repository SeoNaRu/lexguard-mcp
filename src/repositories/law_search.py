"""
Law Search Repository - 법령 검색 기능
"""
import requests
import json
import xml.etree.ElementTree as ET
import re
from typing import Optional
from .base import BaseLawRepository, logger, LAW_API_BASE_URL, LAW_API_SEARCH_URL, search_cache, failure_cache


class LawSearchRepository(BaseLawRepository):
    """법령 검색 관련 기능을 담당하는 Repository"""
    
    def search_law(self, query: Optional[str] = None, page: int = 1, per_page: int = 10, arguments: Optional[dict] = None) -> dict:
        """
        법령을 검색합니다 (통합: 검색 + 목록 조회).
        
        Args:
            query: 검색어 (법령명 또는 키워드, None이면 전체 목록 반환)
            page: 페이지 번호 (기본값: 1)
            per_page: 페이지당 결과 수 (기본값: 10, 최대: 100)
            arguments: 추가 인자 (API 키 등)
            
        Returns:
            검색 결과 딕셔너리 또는 {"error": "error message"}
        """
        logger.debug("search_law called | query=%r page=%d per_page=%d", query, page, per_page)
        
        if per_page < 1:
            per_page = 1
        if per_page > 100:
            per_page = 100
        
        # query가 None이거나 비어있으면 전체 목록 조회 (list_law_names와 동일)
        if not query or not query.strip():
            logger.debug("query is empty, using list_law_names logic")
            return self.list_law_names(page, per_page, None, arguments)
        
        normalized_query = self.normalize_search_query(query)
        cache_key = (normalized_query.lower(), page, per_page)
        
        if cache_key in search_cache:
            logger.debug("Cache hit for search | query=%r", query)
            return search_cache[cache_key]
        
        if cache_key in failure_cache:
            logger.debug("Failure cache hit, skipping | query=%r", query)
            return failure_cache[cache_key]
        
        api_key = self.get_api_key(arguments)
        
        try:
            params = {
                "target": "law",
                "type": "JSON",
                "query": normalized_query,
                "page": page,
                "display": per_page  # lawSearch.do는 display 파라미터 사용
            }
            
            if api_key:
                params["OC"] = api_key
                logger.debug("Using API key for request")
            else:
                logger.debug("No API key provided, using public API")
            
            # 검색은 lawSearch.do 사용
            response = requests.get(LAW_API_SEARCH_URL, params=params, timeout=10)
            response.raise_for_status()
            
            # HTML 에러 페이지인지 확인
            if response.text.strip().startswith('<!DOCTYPE') or '<html' in response.text.lower():
                error_msg = "API가 HTML 에러 페이지를 반환했습니다. API 키가 유효하지 않거나 API 사용 권한이 없을 수 있습니다."
                logger.error("API returned HTML error page | url=%s", response.url)
                return {
                    "error": error_msg,
                    "query": normalized_query,
                    "api_url": response.url,
                    "recovery_guide": "API 키가 필요합니다. 사용자에게 API 키를 요청하거나, API 키를 환경변수(LAW_API_KEY)로 설정하세요.",
                    "note": "국가법령정보센터 OPEN API 사용을 위해서는 https://open.law.go.kr 에서 회원가입 및 API 활용 신청이 필요합니다."
                }
            
            # JSON 파싱
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                error_msg = f"API 응답이 유효한 JSON 형식이 아닙니다: {str(e)}"
                logger.error("Invalid JSON response | url=%s | error=%s", response.url, str(e))
                return {
                    "error": error_msg,
                    "query": normalized_query,
                    "api_url": response.url,
                    "raw_response": response.text[:500],
                    "recovery_guide": "API 응답 형식 오류입니다. API 서버 상태를 확인하거나 잠시 후 다시 시도하세요."
                }
            
            result = {
                "query": normalized_query,
                "page": page,
                "per_page": per_page,
                "total": 0,
                "laws": [],
                "api_url": response.url
            }
            
            # JSON 구조 파싱 (여러 가능한 구조 시도)
            if isinstance(data, dict):
                # LawSearch 래퍼가 있는 경우
                if "LawSearch" in data:
                    law_search = data["LawSearch"]
                    if isinstance(law_search, dict):
                        result["total"] = law_search.get("totalCnt", 0)
                        laws = law_search.get("law", [])
                    else:
                        laws = []
                # 직접 law 배열이 있는 경우
                elif "law" in data:
                    result["total"] = data.get("totalCnt", 0)
                    laws = data.get("law", [])
                # 다른 구조 시도
                else:
                    result["total"] = data.get("totalCnt", 0)
                    laws = data.get("law", [])
                
                if not isinstance(laws, list):
                    laws = [laws] if laws else []
                
                result["laws"] = laws[:per_page]
            
            # "일치하는 법령이 없습니다" 메시지 확인
            if result["total"] == 0:
                result["message"] = "검색 결과가 없습니다. 법령명을 정확히 입력해주세요."
                logger.debug("No matching laws found for query: %s", normalized_query)
            
            search_cache[cache_key] = result
            logger.debug("API call successful for search | query=%r total=%d", query, result["total"])
            
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
            error_result = {"error": error_msg}
            failure_cache[cache_key] = error_result
            return error_result
        except Exception as e:
            error_msg = f"예상치 못한 오류: {str(e)}"
            logger.exception(error_msg)
            return {
                "error": error_msg,
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }
    
    def list_law_names(self, page: int = 1, per_page: int = 50, query: Optional[str] = None, arguments: Optional[dict] = None) -> dict:
        """
        법령명 목록을 조회합니다.
        
        Args:
            page: 페이지 번호 (기본값: 1)
            per_page: 페이지당 결과 수 (기본값: 50, 최대: 100)
            query: 검색어 (선택사항, 법령명으로 필터링)
            arguments: 추가 인자 (API 키 등)
            
        Returns:
            법령명 목록 딕셔너리 또는 {"error": "error message"}
        """
        logger.debug("list_law_names called | page=%d per_page=%d query=%r", page, per_page, query)
        
        if per_page < 1:
            per_page = 1
        if per_page > 100:
            per_page = 100
        
        cache_key = ("law_names", page, per_page, query or "")
        
        if cache_key in search_cache:
            logger.debug("Cache hit for law names list")
            return search_cache[cache_key]
        
        if cache_key in failure_cache:
            logger.debug("Failure cache hit, skipping")
            return failure_cache[cache_key]
        
        api_key = self.get_api_key(arguments)
        
        try:
            # lawSearch.do는 JSON을 지원하지 않으므로 XML 사용
            params = {
                "target": "law",
                "type": "XML",
                "search": "1",
                "display": per_page,
                "page": page,
                "sort": "lasc"
            }
            
            if query:
                params["query"] = self.normalize_search_query(query)
            else:
                params["query"] = "*"
            
            if api_key:
                params["OC"] = api_key
                logger.debug("Using API key for request")
            else:
                logger.debug("No API key provided, using public API")
            
            response = requests.get(LAW_API_SEARCH_URL, params=params, timeout=30)
            response.raise_for_status()
            
            if response.text.strip().startswith('<!DOCTYPE') or '<html' in response.text.lower():
                error_msg = "API가 HTML 에러 페이지를 반환했습니다. API 키가 유효하지 않거나 API 사용 권한이 없을 수 있습니다."
                logger.error("API returned HTML error page | url=%s", response.url)
                return {
                    "error": error_msg,
                    "api_url": response.url,
                    "note": "국가법령정보센터 OPEN API 사용을 위해서는 https://open.law.go.kr 에서 회원가입 및 API 활용 신청이 필요합니다."
                }
            
            # XML 파싱
            result = {
                "page": page,
                "per_page": per_page,
                "query": query,
                "total": 0,
                "law_names": [],
                "api_url": response.url
            }
            
            # XML 응답에 에러 메시지가 있는지 확인
            error_keywords = ["잘못되었습니다", "오류", "error", "에러"]
            if any(keyword in response.text for keyword in error_keywords):
                # 에러 메시지 추출 시도
                error_match = re.search(r'<error[^>]*>(.*?)</error>', response.text, re.IGNORECASE | re.DOTALL)
                if not error_match:
                    error_match = re.search(r'<message[^>]*>(.*?)</message>', response.text, re.IGNORECASE | re.DOTALL)
                if error_match:
                    error_msg = error_match.group(1).strip()
                    logger.error("API returned error in XML | error=%s", error_msg)
                    return {
                        "error": f"API 오류: {error_msg}",
                        "page": page,
                        "per_page": per_page,
                        "query": query,
                        "api_url": response.url,
                        "recovery_guide": "API 서버에서 오류가 발생했습니다. 검색어를 확인하거나 잠시 후 다시 시도하세요."
                    }
            
            try:
                root = ET.fromstring(response.text)
                
                # totalCnt 추출 (여러 위치 확인)
                total_elem = root.find('.//totalCnt')
                if total_elem is not None and total_elem.text:
                    result["total"] = int(total_elem.text)
                else:
                    # totalCnt가 없으면 법령 개수를 직접 세기
                    law_count = len(root.findall('.//법령')) or len(root.findall('.//law'))
                    if law_count > 0:
                        result["total"] = law_count
                
                # 법령명 추출 (실제 XML 구조에 맞게 수정, 최적화)
                # 1. <법령> 태그 찾기 (한글 태그) - 필요한 개수만큼만 처리
                law_elems = root.findall('.//법령')
                if not law_elems:
                    law_elems = root.findall('.//law')
                
                # 필요한 개수만큼만 처리 (성능 최적화)
                for law_elem in law_elems[:per_page]:
                    law_name = None
                    # 법령명 태그 찾기 (CDATA 섹션 포함)
                    name_elem = law_elem.find('법령명')
                    if name_elem is not None:
                        # CDATA 섹션이 있으면 text로 바로 접근 가능
                        law_name = name_elem.text
                        if law_name:
                            law_name = law_name.strip()
                    
                    # 법령명을 찾지 못한 경우 다른 태그 시도
                    if not law_name:
                        for tag_name in ['법령명한글', 'lawNm']:
                            name_elem = law_elem.find(tag_name)
                            if name_elem is not None and name_elem.text:
                                law_name = name_elem.text.strip()
                                break
                    
                    if law_name:
                        result["law_names"].append(law_name)
                        # 필요한 개수만큼만 수집
                        if len(result["law_names"]) >= per_page:
                            break
                
            except ET.ParseError as e:
                logger.warning("XML 파싱 실패, 정규식으로 재시도: %s", str(e))
                # XML 파싱 실패 시 정규식으로 재시도
                total_match = re.search(r'<totalCnt>(\d+)</totalCnt>', response.text)
                if total_match:
                    result["total"] = int(total_match.group(1))
                else:
                    # 법령 개수 세기
                    law_count = len(re.findall(r'<법령>', response.text)) or len(re.findall(r'<law>', response.text))
                    if law_count > 0:
                        result["total"] = law_count
                
                # 법령명 정규식으로 추출 (실제 구조에 맞게)
                # CDATA 섹션 포함 법령명 추출
                law_names = re.findall(r'<법령명><!\[CDATA\[(.*?)\]\]></법령명>', response.text)
                if not law_names:
                    law_names = re.findall(r'<법령명>(.*?)</법령명>', response.text)
                if not law_names:
                    law_names = re.findall(r'<법령명한글><!\[CDATA\[(.*?)\]\]></법령명한글>', response.text)
                if not law_names:
                    law_names = re.findall(r'<법령명한글>(.*?)</법령명한글>', response.text)
                if not law_names:
                    law_names = re.findall(r'<lawNm>(.*?)</lawNm>', response.text)
                
                result["law_names"] = law_names[:per_page] if law_names else []
            
            result["law_names"] = result["law_names"][:per_page]
            
            search_cache[cache_key] = result
            logger.debug("API call successful for law names list | total=%d", result["total"])
            
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
            error_result = {"error": error_msg}
            failure_cache[cache_key] = error_result
            return error_result
        except Exception as e:
            error_msg = f"예상치 못한 오류: {str(e)}"
            logger.exception(error_msg)
            return {
                "error": error_msg,
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }

