"""
Local Ordinance Repository - 자치법규 검색 기능
"""
import requests
import json
from typing import Optional
from .base import BaseLawRepository, logger, LAW_API_SEARCH_URL, search_cache, failure_cache


class LocalOrdinanceRepository(BaseLawRepository):
    """자치법규 검색 관련 기능을 담당하는 Repository"""
    
    def search_local_ordinance(
        self,
        query: Optional[str] = None,
        local_government: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        arguments: Optional[dict] = None
    ) -> dict:
        """자치법규를 검색합니다."""
        logger.debug("search_local_ordinance called | query=%r local_government=%r page=%d per_page=%d", 
                    query, local_government, page, per_page)
        
        if per_page < 1:
            per_page = 1
        if per_page > 100:
            per_page = 100
        
        cache_key = ("local_ordinance", query or "", local_government or "", page, per_page)
        
        if cache_key in search_cache:
            return search_cache[cache_key]
        if cache_key in failure_cache:
            return failure_cache[cache_key]
        
        try:
            params = {
                "target": "ordin",  # API 문서: target=ordin
                "type": "JSON",
                "page": page,
                "display": per_page
            }
            
            if query:
                params["query"] = self.normalize_search_query(query)
            
            if local_government:
                params["orgNm"] = local_government
            
            _, api_key_error = self.attach_api_key(params, arguments, LAW_API_SEARCH_URL)
            if api_key_error:
                return api_key_error
            
            response = requests.get(LAW_API_SEARCH_URL, params=params, timeout=10)
            
            if not response.text or not response.text.strip():
                return {
                    "error": "API가 빈 응답을 반환했습니다. API 키가 필요하거나 권한이 없을 수 있습니다.",
                    "query": query,
                    "local_government": local_government,
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
                    "query": query,
                    "local_government": local_government,
                    "api_url": response.url,
                    "recovery_guide": "API 응답 형식 오류입니다. API 서버 상태를 확인하거나 잠시 후 다시 시도하세요.",
                    "raw_response": response.text[:200] if response.text else "Empty response"
                }
            
            result = {
                "query": query,
                "local_government": local_government,
                "page": page,
                "per_page": per_page,
                "total": 0,
                "ordinances": [],
                "api_url": response.url
            }
            
            if isinstance(data, dict):
                # 자치법규는 OrdinSearch 래퍼 사용
                if "OrdinSearch" in data:
                    ordin_search = data["OrdinSearch"]
                    if isinstance(ordin_search, dict):
                        total_raw = ordin_search.get("totalCnt", 0)
                        try:
                            result["total"] = int(total_raw)
                        except (TypeError, ValueError):
                            result["total"] = 0
                        ordinances = ordin_search.get("ordin", [])
                    else:
                        ordinances = []
                elif "ordin" in data:
                    total_raw = data.get("totalCnt", 0)
                    try:
                        result["total"] = int(total_raw)
                    except (TypeError, ValueError):
                        result["total"] = 0
                    ordinances = data.get("ordin", [])
                else:
                    total_raw = data.get("totalCnt", 0)
                    try:
                        result["total"] = int(total_raw)
                    except (TypeError, ValueError):
                        result["total"] = 0
                    ordinances = data.get("ordin", [])
                
                if not isinstance(ordinances, list):
                    ordinances = [ordinances] if ordinances else []
                
                result["ordinances"] = ordinances[:per_page]
            
            # total은 있는데 목록이 비어 있는 경우 메타 정보 추가
            if result["total"] and not result["ordinances"]:
                result["note"] = "API 응답에서 totalCnt는 있으나 자치법규 목록(ordin)이 비어 있습니다. 국가법령정보센터 응답 구조를 확인하세요."
            
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

