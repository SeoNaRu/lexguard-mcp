"""
Special Administrative Appeal Service - 특별행정심판 관련 비즈니스 로직
"""
import asyncio
from typing import Optional
from ..repositories.special_administrative_appeal_repository import SpecialAdministrativeAppealRepository
from ..models import SearchSpecialAdministrativeAppealRequest, GetSpecialAdministrativeAppealRequest


class SpecialAdministrativeAppealService:
    """특별행정심판 관련 비즈니스 로직을 처리하는 Service"""
    
    def __init__(self):
        self.repository = SpecialAdministrativeAppealRepository()
    
    async def search_special_administrative_appeal(
        self,
        req: SearchSpecialAdministrativeAppealRequest,
        arguments: Optional[dict] = None
    ) -> dict:
        """특별행정심판 검색"""
        try:
            if arguments is None:
                arguments = {}
            return await asyncio.to_thread(
                self.repository.search_special_administrative_appeal,
                req.tribunal_type,
                req.query,
                req.page,
                req.per_page,
                arguments
            )
        except Exception as e:
            return {
                "error": f"특별행정심판 검색 중 오류 발생: {str(e)}",
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }
    
    async def get_special_administrative_appeal(
        self,
        req: GetSpecialAdministrativeAppealRequest,
        arguments: Optional[dict] = None
    ) -> dict:
        """특별행정심판 조회"""
        try:
            if arguments is None:
                arguments = {}
            return await asyncio.to_thread(
                self.repository.get_special_administrative_appeal,
                req.tribunal_type,
                req.appeal_id,
                arguments
            )
        except Exception as e:
            return {
                "error": f"특별행정심판 조회 중 오류 발생: {str(e)}",
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }

