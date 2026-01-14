"""
Committee Decision Service - 위원회 결정문 관련 비즈니스 로직
"""
import asyncio
from typing import Optional
from ..repositories.committee_decision_repository import CommitteeDecisionRepository
from ..models import SearchCommitteeDecisionRequest, GetCommitteeDecisionRequest


class CommitteeDecisionService:
    """위원회 결정문 관련 비즈니스 로직을 처리하는 Service"""
    
    def __init__(self):
        self.repository = CommitteeDecisionRepository()
    
    async def search_committee_decision(
        self,
        req: SearchCommitteeDecisionRequest,
        arguments: Optional[dict] = None
    ) -> dict:
        """위원회 결정문 검색"""
        try:
            if arguments is None:
                arguments = {}
            return await asyncio.to_thread(
                self.repository.search_committee_decision,
                req.committee_type,
                req.query,
                req.page,
                req.per_page,
                arguments
            )
        except Exception as e:
            return {
                "error": f"위원회 결정문 검색 중 오류 발생: {str(e)}",
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }
    
    async def get_committee_decision(
        self,
        req: GetCommitteeDecisionRequest,
        arguments: Optional[dict] = None
    ) -> dict:
        """위원회 결정문 조회"""
        try:
            if arguments is None:
                arguments = {}
            return await asyncio.to_thread(
                self.repository.get_committee_decision,
                req.committee_type,
                req.decision_id,
                arguments
            )
        except Exception as e:
            return {
                "error": f"위원회 결정문 조회 중 오류 발생: {str(e)}",
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }

