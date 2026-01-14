"""
Administrative Rule Service - 행정규칙 관련 비즈니스 로직
"""
import asyncio
from typing import Optional
from ..repositories.administrative_rule_repository import AdministrativeRuleRepository
from ..models import SearchAdministrativeRuleRequest


class AdministrativeRuleService:
    """행정규칙 관련 비즈니스 로직을 처리하는 Service"""
    
    def __init__(self):
        self.repository = AdministrativeRuleRepository()
    
    async def search_administrative_rule(
        self,
        req: SearchAdministrativeRuleRequest,
        arguments: Optional[dict] = None
    ) -> dict:
        """행정규칙 검색"""
        try:
            if arguments is None:
                arguments = {}
            return await asyncio.to_thread(
                self.repository.search_administrative_rule,
                req.query,
                req.agency,
                req.page,
                req.per_page,
                arguments
            )
        except Exception as e:
            return {
                "error": f"행정규칙 검색 중 오류 발생: {str(e)}",
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }

