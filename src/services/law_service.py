"""
Law Service - 법령 관련 비즈니스 로직
Service 패턴: 비즈니스 로직을 처리하고 Repository를 호출
"""
import asyncio
from typing import Optional
from ..repositories.law_repository import LawRepository
from ..models import SearchLawRequest, GetLawRequest, ListLawNamesRequest, GetLawDetailRequest, GetLawArticlesRequest, GetSingleArticleRequest
from ..utils.parameter_normalizer import normalize_article_number, normalize_hang, normalize_ho, normalize_mok


class LawService:
    """법령 관련 비즈니스 로직을 처리하는 Service"""
    
    def __init__(self):
        self.repository = LawRepository()
    
    async def search_law(self, req: SearchLawRequest, arguments: Optional[dict] = None) -> dict:
        """법령 검색 (통합: 검색 + 목록 조회)"""
        try:
            if arguments is None:
                arguments = {}
            return await asyncio.to_thread(
                self.repository.search_law,
                req.query,
                req.page,
                req.per_page,
                arguments
            )
        except Exception as e:
            return {
                "error": f"법령 검색 중 오류 발생: {str(e)}",
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }
    
    async def get_law(self, req: GetLawRequest, arguments: Optional[dict] = None) -> dict:
        """법령 조회 (통합: 상세 + 조문 + 단일 조문)"""
        try:
            if arguments is None:
                arguments = {}
            # law_id와 law_name 둘 중 하나는 필수
            if not req.law_id and not req.law_name:
                return {
                    "error": "law_id 또는 law_name 중 하나는 필수입니다.",
                    "recovery_guide": "법령 ID 또는 법령명 중 하나를 입력해주세요. 예: law_name='형법' 또는 law_id='123456'"
                }
            # mode="single"일 때 article_number 필수
            if req.mode == "single" and not req.article_number:
                return {
                    "error": "mode='single'일 때 article_number는 필수입니다.",
                    "recovery_guide": "단일 조문 조회 시 조 번호를 입력해주세요. 예: article_number='제1조' 또는 '1'"
                }
            
            # 파라미터 정규화 (다양한 형식 지원)
            normalized_article_number = normalize_article_number(req.article_number) if req.article_number else None
            normalized_hang = normalize_hang(req.hang) if req.hang else None
            normalized_ho = normalize_ho(req.ho) if req.ho else None
            normalized_mok = normalize_mok(req.mok) if req.mok else None
            
            # Repository에서 원본 결과 조회
            raw_result = await asyncio.to_thread(
                self.repository.get_law,
                req.law_id,
                req.law_name,
                req.mode,
                normalized_article_number,
                normalized_hang,
                normalized_ho,
                normalized_mok,
                arguments
            )
            
            # 에러면 그대로 반환
            if isinstance(raw_result, dict) and "error" in raw_result:
                return raw_result
            
            # MCP 툴 스키마(get_law_tool)에 맞게 응답 형태를 정규화
            mode = req.mode or "detail"
            
            # 상세 조회: detail 필드에 전체 상세 정보 배치
            if mode == "detail":
                return {
                    "law_name": raw_result.get("law_name") or req.law_name,
                    "law_id": raw_result.get("law_id") or req.law_id,
                    "mode": "detail",
                    "detail": raw_result,
                    "articles": None,
                    "article": None,
                    "api_url": raw_result.get("api_url")
                }
            
            # 전체 조문 조회: articles 배열에 조문 목록 배치
            if mode == "articles":
                return {
                    "law_name": raw_result.get("law_name") or req.law_name,
                    "law_id": raw_result.get("law_id") or req.law_id,
                    "mode": "articles",
                    "detail": None,
                    "articles": raw_result.get("articles", []),
                    "article": None,
                    "api_url": raw_result.get("api_url")
                }
            
            # 단일 조문 조회: article 객체로 래핑
            if mode == "single":
                # repository.get_law(mode='single')는 get_single_article의 결과를 그대로 반환하므로,
                # 이를 article 필드 안으로 넣어준다.
                article_obj = {
                    "law_id": raw_result.get("law_id") or req.law_id,
                    "article_number": raw_result.get("article_number") or normalized_article_number,
                    "hang": raw_result.get("hang") or normalized_hang,
                    "ho": raw_result.get("ho") or normalized_ho,
                    "mok": raw_result.get("mok") or normalized_mok,
                    "title": raw_result.get("title"),
                    "content": raw_result.get("content"),
                    "api_url": raw_result.get("api_url"),
                    "note": raw_result.get("note"),
                    "raw_data": raw_result.get("raw_data")
                }
                
                return {
                    "law_name": req.law_name,
                    "law_id": article_obj["law_id"],
                    "mode": "single",
                    "detail": None,
                    "articles": None,
                    "article": article_obj,
                    "api_url": raw_result.get("api_url")
                }
            
            # 알 수 없는 mode는 Repository의 원본 결과를 그대로 반환 (하위 호환)
            return raw_result
        except Exception as e:
            return {
                "error": f"법령 조회 중 오류 발생: {str(e)}",
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }
    
    async def list_law_names(self, req: ListLawNamesRequest, arguments: Optional[dict] = None) -> dict:
        """법령명 목록 조회"""
        try:
            if arguments is None:
                arguments = {}
            return await asyncio.to_thread(
                self.repository.list_law_names,
                req.page,
                req.per_page,
                req.query,
                arguments
            )
        except Exception as e:
            return {
                "error": f"법령명 목록 조회 중 오류 발생: {str(e)}",
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }
    
    async def get_law_detail(self, req: GetLawDetailRequest, arguments: Optional[dict] = None) -> dict:
        """법령 상세 조회"""
        try:
            if arguments is None:
                arguments = {}
            return await asyncio.to_thread(
                self.repository.get_law_detail,
                req.law_name,
                arguments
            )
        except Exception as e:
            return {
                "error": f"법령 상세 조회 중 오류 발생: {str(e)}",
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }
    
    async def get_law_articles(self, req: GetLawArticlesRequest, arguments: Optional[dict] = None) -> dict:
        """법령 조문 조회"""
        try:
            if arguments is None:
                arguments = {}
            # law_id와 law_name 둘 중 하나는 필수
            if not req.law_id and not req.law_name:
                return {
                    "error": "law_id 또는 law_name 중 하나는 필수입니다.",
                    "recovery_guide": "법령 ID 또는 법령명 중 하나를 입력해주세요. 예: law_name='형법' 또는 law_id='123456'"
                }
            return await asyncio.to_thread(
                self.repository.get_law_articles,
                req.law_id,
                req.law_name,
                arguments
            )
        except Exception as e:
            return {
                "error": f"법령 조문 조회 중 오류 발생: {str(e)}",
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }
    
    async def get_single_article(self, req: GetSingleArticleRequest, arguments: Optional[dict] = None) -> dict:
        """단일 조문 조회"""
        try:
            if arguments is None:
                arguments = {}
            
            # 파라미터 정규화 (다양한 형식 지원)
            normalized_article_number = normalize_article_number(req.article_number) if req.article_number else None
            normalized_hang = normalize_hang(req.hang) if req.hang else None
            normalized_ho = normalize_ho(req.ho) if req.ho else None
            normalized_mok = normalize_mok(req.mok) if req.mok else None
            
            return await asyncio.to_thread(
                self.repository.get_single_article,
                req.law_id,
                normalized_article_number,
                normalized_hang,
                normalized_ho,
                normalized_mok,
                arguments
            )
        except Exception as e:
            return {
                "error": f"조문 조회 중 오류 발생: {str(e)}",
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }

