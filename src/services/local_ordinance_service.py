"""
Local Ordinance Service - 자치법규 관련 비즈니스 로직
"""
import asyncio
from typing import Optional
from ..repositories.local_ordinance_repository import LocalOrdinanceRepository
from ..models import SearchLocalOrdinanceRequest


class LocalOrdinanceService:
    """자치법규 관련 비즈니스 로직을 처리하는 Service"""
    
    def __init__(self):
        self.repository = LocalOrdinanceRepository()
    
    async def search_local_ordinance(
        self,
        req: SearchLocalOrdinanceRequest,
        arguments: Optional[dict] = None
    ) -> dict:
        """자치법규 검색"""
        try:
            if arguments is None:
                arguments = {}
            return await asyncio.to_thread(
                self.repository.search_local_ordinance,
                req.query,
                req.local_government,
                req.page,
                req.per_page,
                arguments
            )
        except Exception as e:
            return {
                "error": f"자치법규 검색 중 오류 발생: {str(e)}",
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }

