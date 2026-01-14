"""
범용 API 호출 리포지토리
api_crawler의 메타데이터를 기반으로 모든 API를 호출할 수 있는 공통 리포지토리
"""
import requests
import json
import logging
from typing import Dict, Optional, Any, List
from ..tools.api_metadata_loader import get_metadata_loader
from .base import BaseLawRepository

logger = logging.getLogger("lexguard-mcp")


class GenericAPIRepository(BaseLawRepository):
    """범용 API 호출을 담당하는 Repository"""
    
    def __init__(self):
        self.metadata_loader = get_metadata_loader()
    
    def call_api(
        self,
        api_id: int,
        params: Optional[Dict[str, Any]] = None,
        arguments: Optional[Dict] = None
    ) -> Dict:
        """
        API를 호출합니다.
        
        Args:
            api_id: API ID (api_index.json의 id)
            params: API 파라미터 딕셔너리
            arguments: 추가 인자 (API 키 등)
            
        Returns:
            API 응답 딕셔너리 또는 {"error": "error message"}
        """
        if params is None:
            params = {}
        
        # API 메타데이터 로드
        api_detail = self.metadata_loader.load_api_detail(api_id)
        if not api_detail:
            return {
                "error": f"API를 찾을 수 없습니다: id={api_id}",
                "api_id": api_id,
                "recovery_guide": "API ID가 올바른지 확인하세요. api_index.json에서 사용 가능한 API 목록을 확인하세요."
            }
        
        api_name = api_detail.get("api_name", "Unknown")
        request_url = api_detail.get("request_url", "")
        request_parameters = api_detail.get("request_parameters", [])
        
        if not request_url:
            return {
                "error": f"API URL이 없습니다: {api_name}",
                "api_name": api_name,
                "api_id": api_id,
                "recovery_guide": "API 메타데이터에 URL이 설정되지 않았습니다. API 설정을 확인하거나 관리자에게 문의하세요."
            }
        
        logger.info(f"Calling API | id={api_id} name={api_name}")
        
        # API 키 추가
        api_key = self.get_api_key(arguments)
        if api_key:
            params["OC"] = api_key
        
        # 필수 파라미터 확인
        required_params = [p["name"] for p in request_parameters if p.get("required", False)]
        missing_params = [p for p in required_params if p not in params]
        
        if missing_params:
            return {
                "error": f"필수 파라미터가 누락되었습니다: {', '.join(missing_params)}",
                "required_params": required_params,
                "provided_params": list(params.keys()),
                "api_name": api_name,
                "api_id": api_id,
                "recovery_guide": f"필수 파라미터를 모두 입력해주세요: {', '.join(missing_params)}. API 문서를 확인하여 필요한 파라미터를 확인하세요."
            }
        
        # target 파라미터는 URL에서 추출하거나 params에 추가
        if "target" not in params and "target=" in request_url:
            # URL에서 target 추출
            import urllib.parse
            parsed_url = urllib.parse.urlparse(request_url)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            if "target" in query_params:
                params["target"] = query_params["target"][0]
        
        # type 파라미터 기본값 설정
        if "type" not in params:
            params["type"] = "JSON"
        
        try:
            # API 호출
            response = requests.get(request_url, params=params, timeout=30)
            response.raise_for_status()
            
            # HTML 에러 페이지인지 확인
            if response.text.strip().startswith('<!DOCTYPE') or '<html' in response.text.lower():
                text = response.text or ""
                try:
                    import re as _re
                    title_match = _re.search(r"<title[^>]*>(.*?)</title>", text, _re.IGNORECASE | _re.DOTALL)
                    title_text = title_match.group(1).strip() if title_match else None
                except Exception:
                    title_text = None
                
                head_snippet = text[:300]
                status_code = response.status_code
                content_type = response.headers.get("content-type")
                
                logger.error(
                    "API returned HTML error page | url=%s status=%s ct=%s title=%r head=%r",
                    response.url,
                    status_code,
                    content_type,
                    title_text,
                    head_snippet,
                )
                
                error_msg = "API가 HTML 에러 페이지를 반환했습니다. API 키가 유효하지 않거나 API 사용 권한이 없을 수 있습니다."
                return {
                    "error": error_msg,
                    "api_name": api_name,
                    "api_id": api_id,
                    "api_url": response.url,
                    "api_error": {
                        "status": status_code,
                        "content_type": content_type,
                        "title": title_text,
                        "head": head_snippet,
                    },
                    "recovery_guide": "API 키가 필요하거나, 요청 형식이 잘못되었을 수 있습니다. 서버 로그의 api_error 정보를 확인하고 검색어를 단순한 키워드로 줄여서 다시 시도하세요.",
                    "note": "국가법령정보센터 OPEN API 사용을 위해서는 https://open.law.go.kr 에서 회원가입 및 API 활용 신청이 필요합니다."
                }
            
            # 응답 파싱
            content_type = response.headers.get("Content-Type", "").lower()
            
            if "json" in content_type or params.get("type") == "JSON":
                try:
                    data = response.json()
                    return {
                        "api_name": api_name,
                        "api_id": api_id,
                        "data": data
                    }
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON response | url={response.url} | error={str(e)}")
                    return {
                        "error": f"API 응답이 유효한 JSON 형식이 아닙니다: {str(e)}",
                        "api_name": api_name,
                        "api_id": api_id,
                        "api_url": response.url,
                        "raw_response": response.text[:500],
                        "recovery_guide": "API 응답 형식 오류입니다. API 서버 상태를 확인하거나 잠시 후 다시 시도하세요."
                    }
            elif "xml" in content_type or params.get("type") == "XML":
                # XML 응답은 텍스트로 반환
                return {
                    "api_name": api_name,
                    "api_id": api_id,
                    "data": response.text
                }
            else:
                # HTML 또는 기타 형식
                return {
                    "api_name": api_name,
                    "api_id": api_id,
                    "data": response.text
                }
                
        except requests.exceptions.Timeout:
            error_msg = f"API 호출 타임아웃: {api_name}"
            logger.error(error_msg)
            return {
                "error": error_msg,
                "api_name": api_name,
                "api_id": api_id,
                "recovery_guide": "네트워크 오류입니다. 잠시 후 다시 시도하거나, 인터넷 연결을 확인하세요."
            }
        
        except requests.exceptions.RequestException as e:
            error_msg = f"API 호출 중 오류 발생: {str(e)}"
            logger.error(f"{error_msg} | url={request_url}")
            return {
                "error": error_msg,
                "api_name": api_name,
                "api_id": api_id,
                "api_url": request_url,
                "recovery_guide": "네트워크 오류입니다. 잠시 후 다시 시도하거나, 인터넷 연결을 확인하세요."
            }
        
        except Exception as e:
            error_msg = f"예상치 못한 오류 발생: {str(e)}"
            logger.exception(f"{error_msg} | api_id={api_id}")
            return {
                "error": error_msg,
                "api_name": api_name,
                "api_id": api_id,
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }
    
    def get_api_info(self, api_id: int) -> Optional[Dict]:
        """API 정보를 반환합니다 (메타데이터만)"""
        return self.metadata_loader.load_api_detail(api_id)
    
    def list_available_apis(self, category: Optional[str] = None) -> List[Dict]:
        """사용 가능한 API 목록을 반환합니다"""
        if category:
            return self.metadata_loader.get_apis_by_category(category)
        return self.metadata_loader.get_all_apis()

