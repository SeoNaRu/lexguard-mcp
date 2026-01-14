"""
Law Comparison Repository - 법령 비교 및 연혁 조회 기능
"""
import requests
import json
from typing import Optional
from .base import BaseLawRepository, logger, LAW_API_SEARCH_URL, LAW_API_BASE_URL, search_cache, failure_cache


class LawComparisonRepository(BaseLawRepository):
    """법령 비교 및 연혁 조회 관련 기능을 담당하는 Repository"""
    
    def compare_laws(
        self,
        law_name: str,
        compare_type: str = "신구법",
        arguments: Optional[dict] = None
    ) -> dict:
        """법령을 비교합니다 (신구법 비교, 연혁, 3단 비교)."""
        logger.debug("compare_laws called | law_name=%r compare_type=%r", law_name, compare_type)
        
        cache_key = ("law_comparison", law_name, compare_type)
        
        if cache_key in search_cache:
            return search_cache[cache_key]
        if cache_key in failure_cache:
            return failure_cache[cache_key]
        
        api_key = self.get_api_key(arguments)
        
        try:
            # 먼저 법령명으로 법령 ID 찾기
            search_params = {
                "target": "law",
                "type": "JSON",
                "query": self.normalize_search_query(law_name),
                "page": 1,
                "display": 10  # 더 많은 결과에서 정확한 매칭을 위해
            }
            
            if api_key:
                search_params["OC"] = api_key
            
            search_response = requests.get(LAW_API_SEARCH_URL, params=search_params, timeout=10)
            search_response.raise_for_status()
            
            if search_response.text.strip().startswith('<!DOCTYPE') or '<html' in search_response.text.lower():
                return {
                    "error": "법령 검색 API가 HTML 에러 페이지를 반환했습니다.",
                    "law_name": law_name,
                    "recovery_guide": "API 키가 필요합니다. 사용자에게 API 키를 요청하거나, API 키를 환경변수(LAW_API_KEY)로 설정하세요."
                }
            
            law_id = None
            normalized_query = self.normalize_search_query(law_name)
            
            try:
                search_data = search_response.json()
                if isinstance(search_data, dict):
                    laws = search_data.get("LawSearch", {}).get("law", []) or search_data.get("law", [])
                    if not isinstance(laws, list):
                        laws = [laws] if laws else []
                    
                    # 정확히 일치하는 법령명 찾기
                    for law_item in laws:
                        if isinstance(law_item, dict):
                            item_name = (law_item.get("법령명한글") or 
                                       law_item.get("lawNm") or 
                                       law_item.get("법령명") or "")
                            if normalized_query == self.normalize_search_query(item_name):
                                law_id = (law_item.get("법령일련번호") or 
                                         law_item.get("일련번호") or
                                         law_item.get("lawSeq") or
                                         law_item.get("id"))
                                break
                    
                    # 정확히 일치하지 않으면 첫 번째 결과 사용
                    if not law_id and laws and isinstance(laws[0], dict):
                        law_id = (laws[0].get("법령일련번호") or 
                                 laws[0].get("일련번호") or
                                 laws[0].get("lawSeq") or
                                 laws[0].get("id"))
            except json.JSONDecodeError:
                pass
            
            if not law_id:
                return {
                    "error": "법령 ID를 찾을 수 없습니다.",
                    "law_name": law_name,
                    "recovery_guide": "법령명을 정확히 입력해주세요. 예: '형법', '민법', '개인정보보호법'. 법령명이 정확한지 확인하세요."
                }
            
            # 비교 타입에 따라 다른 API 호출 (API 문서 기준)
            if compare_type == "신구법":
                target = "oldAndNew"  # API 문서: target=oldAndNew
            elif compare_type == "연혁":
                target = "lsHistory"  # API 문서: target=lsHistory
            elif compare_type == "3단비교":
                target = "thdCmp"  # API 문서: target=thdCmp
            else:
                return {
                    "error": f"지원하지 않는 비교 유형입니다: {compare_type}",
                    "supported_types": ["신구법", "연혁", "3단비교"],
                    "recovery_guide": "비교 유형을 '신구법', '연혁', '3단비교' 중 하나로 선택해주세요."
                }
            
            params = {
                "target": target,
                "type": "JSON",
                "MST": law_id
            }
            
            if api_key:
                params["OC"] = api_key
            
            response = requests.get(LAW_API_BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            
            if response.text.strip().startswith('<!DOCTYPE') or '<html' in response.text.lower():
                return {
                    "error": "API가 HTML 에러 페이지를 반환했습니다.",
                    "law_name": law_name,
                    "compare_type": compare_type,
                    "api_url": response.url,
                    "recovery_guide": "API 키가 필요합니다. 사용자에게 API 키를 요청하거나, API 키를 환경변수(LAW_API_KEY)로 설정하세요."
                }
            
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                return {
                    "error": f"API 응답이 유효한 JSON 형식이 아닙니다: {str(e)}",
                    "law_name": law_name,
                    "compare_type": compare_type,
                    "api_url": response.url,
                    "recovery_guide": "API 응답 형식 오류입니다. API 서버 상태를 확인하거나 잠시 후 다시 시도하세요."
                }
            
            result = {
                "law_name": law_name,
                "law_id": law_id,
                "compare_type": compare_type,
                "comparison": data,
                "api_url": response.url
            }
            
            search_cache[cache_key] = result
            return result
            
        except requests.exceptions.Timeout:
            error_result = {
                "error": "API 호출 타임아웃",
                "law_name": law_name,
                "compare_type": compare_type,
                "recovery_guide": "네트워크 응답 시간이 초과되었습니다. 잠시 후 다시 시도하거나, 인터넷 연결을 확인하세요."
            }
            failure_cache[cache_key] = error_result
            return error_result
        except requests.exceptions.RequestException as e:
            error_result = {
                "error": f"API 요청 실패: {str(e)}",
                "law_name": law_name,
                "compare_type": compare_type,
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

