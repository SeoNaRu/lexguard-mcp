"""
Administrative Appeal Service - 행정심판 관련 비즈니스 로직
"""
import asyncio
from typing import Optional
from ..repositories.administrative_appeal_repository import AdministrativeAppealRepository
from ..models import SearchAdministrativeAppealRequest, GetAdministrativeAppealRequest


class AdministrativeAppealService:
    """행정심판 관련 비즈니스 로직을 처리하는 Service"""
    
    def __init__(self):
        self.repository = AdministrativeAppealRepository()
    
    async def search_administrative_appeal(
        self,
        req: SearchAdministrativeAppealRequest,
        arguments: Optional[dict] = None
    ) -> dict:
        """행정심판 검색"""
        try:
            if arguments is None:
                arguments = {}
            return await asyncio.to_thread(
                self.repository.search_administrative_appeal,
                req.query,
                req.page,
                req.per_page,
                req.date_from,
                req.date_to,
                arguments
            )
        except Exception as e:
            return {
                "error": f"행정심판 검색 중 오류 발생: {str(e)}",
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }
    
    async def get_administrative_appeal(
        self,
        req: GetAdministrativeAppealRequest,
        arguments: Optional[dict] = None
    ) -> dict:
        """행정심판 조회"""
        try:
            if arguments is None:
                arguments = {}
            return await asyncio.to_thread(
                self.repository.get_administrative_appeal,
                req.appeal_id,
                arguments
            )
        except Exception as e:
            return {
                "error": f"행정심판 조회 중 오류 발생: {str(e)}",
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }

