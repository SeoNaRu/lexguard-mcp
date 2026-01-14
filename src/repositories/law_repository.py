"""
Law Repository - 법령 데이터 접근 로직 (통합 클래스)
Repository 패턴: API 호출 로직을 캡슐화
"""
from .law_search import LawSearchRepository
from .law_detail import LawDetailRepository


class LawRepository(LawSearchRepository, LawDetailRepository):
    """
    법령 데이터 접근을 담당하는 통합 Repository
    
    검색 및 조회 기능을 모두 제공합니다.
    - 검색 기능: LawSearchRepository에서 상속
    - 조회 기능: LawDetailRepository에서 상속
    - 공통 유틸리티: BaseLawRepository에서 상속
    """
    pass
