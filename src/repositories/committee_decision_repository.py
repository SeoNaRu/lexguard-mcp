"""
Committee Decision Repository - 위원회 결정문 검색 및 조회 기능
"""
import requests
import json
from typing import Optional
from .base import BaseLawRepository, logger, LAW_API_SEARCH_URL, LAW_API_BASE_URL, search_cache, failure_cache


# 위원회 타입별 target 매핑 (API 문서 기준)
COMMITTEE_TARGET_MAP = {
    "개인정보보호위원회": "ppc",  # API 문서: target=ppc
    "금융위원회": "fsc",  # API 문서: target=fsc
    "노동위원회": "nlrc",  # API 문서: target=nlrc
    "고용보험심사위원회": "eiac",  # API 문서: target=eiac
    "국민권익위원회": "acr",  # API 문서: target=acr
    "방송미디어통신위원회": "kcc",  # API 문서: target=kcc
    "산업재해보상보험재심사위원회": "iaciac",  # API 문서: target=iaciac
    "중앙토지수용위원회": "oclt",  # API 문서: target=oclt
    "중앙환경분쟁조정위원회": "ecc",  # API 문서: target=ecc
    "증권선물위원회": "sfc",  # API 문서: target=sfc
    "국가인권위원회": "nhrck",  # API 문서: target=nhrck
}


class CommitteeDecisionRepository(BaseLawRepository):
    """위원회 결정문 검색 및 조회 관련 기능을 담당하는 Repository"""
    
    def search_committee_decision(
        self,
        committee_type: str,
        query: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        arguments: Optional[dict] = None
    ) -> dict:
        """위원회 결정문을 검색합니다."""
        logger.debug("search_committee_decision called | committee_type=%r query=%r page=%d per_page=%d", 
                    committee_type, query, page, per_page)
        
        if per_page < 1:
            per_page = 1
        if per_page > 100:
            per_page = 100
        
        target = COMMITTEE_TARGET_MAP.get(committee_type)
        if not target:
            return {
                "error": f"지원하지 않는 위원회 종류입니다: {committee_type}",
                "supported_committees": list(COMMITTEE_TARGET_MAP.keys()),
                "recovery_guide": f"지원하는 위원회 종류를 사용해주세요: {', '.join(COMMITTEE_TARGET_MAP.keys())}"
            }
        
        cache_key = ("committee_decision", committee_type, query or "", page, per_page)
        
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
            response.raise_for_status()
            
            # 응답이 비어있는지 확인
            if not response.text or not response.text.strip():
                return {
                    "error": "API가 빈 응답을 반환했습니다. API 키가 필요하거나 권한이 없을 수 있습니다.",
                    "committee_type": committee_type,
                    "query": query,
                    "api_url": response.url,
                    "recovery_guide": "API 키가 필요합니다. 사용자에게 API 키를 요청하거나, API 키를 환경변수(LAW_API_KEY)로 설정하세요.",
                    "note": "국가법령정보센터 OPEN API 사용을 위해서는 https://open.law.go.kr 에서 회원가입 및 API 활용 신청이 필요합니다."
                }
            
            invalid_response = self.validate_drf_response(response)
            if invalid_response:
                return invalid_response
            
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                return {
                    "error": f"API 응답이 유효한 JSON 형식이 아닙니다: {str(e)}",
                    "committee_type": committee_type,
                    "query": query,
                    "api_url": response.url,
                    "raw_response": response.text[:200] if response.text else "Empty response",
                    "recovery_guide": "API 응답 형식 오류입니다. API 서버 상태를 확인하거나 잠시 후 다시 시도하세요."
                }
            
            result = {
                "committee_type": committee_type,
                "query": query,
                "page": page,
                "per_page": per_page,
                "total": 0,
                "decisions": [],
                "api_url": response.url
            }
            
            # JSON 구조 파싱 (위원회별로 다를 수 있음)
            if isinstance(data, dict):
                # 다양한 가능한 키 시도
                for key in ["totalCnt", "total", "count"]:
                    if key in data:
                        result["total"] = data.get(key, 0)
                        break
                
                # 결정문 배열 찾기
                for key in ["dec", "decision", "decisions", "data"]:
                    if key in data:
                        decisions = data.get(key, [])
                        if not isinstance(decisions, list):
                            decisions = [decisions] if decisions else []
                        result["decisions"] = decisions[:per_page]
                        break
            
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
    
    def get_committee_decision(
        self,
        committee_type: str,
        decision_id: str,
        arguments: Optional[dict] = None
    ) -> dict:
        """위원회 결정문 상세 정보를 조회합니다."""
        logger.debug("get_committee_decision called | committee_type=%r decision_id=%r", committee_type, decision_id)
        
        target = COMMITTEE_TARGET_MAP.get(committee_type)
        if not target:
            return {
                "error": f"지원하지 않는 위원회 종류입니다: {committee_type}",
                "supported_committees": list(COMMITTEE_TARGET_MAP.keys()),
                "recovery_guide": f"지원하는 위원회 종류를 사용해주세요: {', '.join(COMMITTEE_TARGET_MAP.keys())}"
            }
        
        cache_key = ("committee_decision_detail", committee_type, decision_id)
        
        if cache_key in search_cache:
            return search_cache[cache_key]
        if cache_key in failure_cache:
            return failure_cache[cache_key]
        
        try:
            params = {
                "target": target,
                "type": "JSON",
                "ID": decision_id
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
                    "committee_type": committee_type,
                    "decision_id": decision_id,
                    "api_url": response.url,
                    "recovery_guide": "API 응답 형식 오류입니다. API 서버 상태를 확인하거나 잠시 후 다시 시도하세요."
                }
            
            result = {
                "committee_type": committee_type,
                "decision_id": decision_id,
                "decision": data,
                "api_url": response.url
            }
            
            search_cache[cache_key] = result
            return result
            
        except requests.exceptions.Timeout:
            error_result = {
                "error": "API 호출 타임아웃",
                "committee_type": committee_type,
                "decision_id": decision_id,
                "recovery_guide": "네트워크 응답 시간이 초과되었습니다. 잠시 후 다시 시도하거나, 인터넷 연결을 확인하세요."
            }
            failure_cache[cache_key] = error_result
            return error_result
        except requests.exceptions.RequestException as e:
            error_result = {
                "error": f"API 요청 실패: {str(e)}",
                "committee_type": committee_type,
                "decision_id": decision_id,
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

