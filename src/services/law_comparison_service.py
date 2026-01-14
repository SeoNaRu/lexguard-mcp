"""
Law Comparison Service - 법령 비교 관련 비즈니스 로직
"""
import asyncio
from typing import Optional
from ..repositories.law_comparison_repository import LawComparisonRepository
from ..models import CompareLawsRequest


class LawComparisonService:
    """법령 비교 관련 비즈니스 로직을 처리하는 Service"""
    
    def __init__(self):
        self.repository = LawComparisonRepository()
    
    async def compare_laws(
        self,
        req: CompareLawsRequest,
        arguments: Optional[dict] = None
    ) -> dict:
        """법령 비교"""
        try:
            if arguments is None:
                arguments = {}
            return await asyncio.to_thread(
                self.repository.compare_laws,
                req.law_name,
                req.compare_type,
                arguments
            )
        except Exception as e:
            return {
                "error": f"법령 비교 중 오류 발생: {str(e)}",
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }

