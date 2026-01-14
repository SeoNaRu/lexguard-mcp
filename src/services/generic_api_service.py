"""
범용 API 서비스
범용 API 호출을 위한 비즈니스 로직 처리
"""
import asyncio
from typing import Optional, Dict, Any
from ..repositories.generic_api_repository import GenericAPIRepository


class GenericAPIService:
    """범용 API 호출을 처리하는 Service"""
    
    def __init__(self):
        self.repository = GenericAPIRepository()
    
    async def call_api(
        self,
        api_id: int,
        params: Optional[Dict[str, Any]] = None,
        arguments: Optional[Dict] = None
    ) -> Dict:
        """API를 호출합니다"""
        try:
            return await asyncio.to_thread(
                self.repository.call_api,
                api_id,
                params,
                arguments
            )
        except Exception as e:
            return {
                "error": f"API 호출 중 오류 발생: {str(e)}",
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }
    
    async def get_api_info(self, api_id: int) -> Optional[Dict]:
        """API 정보를 조회합니다"""
        try:
            return await asyncio.to_thread(
                self.repository.get_api_info,
                api_id
            )
        except Exception as e:
            return None
    
    async def list_available_apis(self, category: Optional[str] = None) -> list:
        """사용 가능한 API 목록을 조회합니다"""
        try:
            return await asyncio.to_thread(
                self.repository.list_available_apis,
                category
            )
        except Exception as e:
            return []

