"""
Pydantic 모델 정의
모든 요청/응답 스키마를 여기에 정의
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal, List


class SearchLawRequest(BaseModel):
    """법령 검색 요청 모델 (통합: 검색 + 목록 조회)"""
    query: Optional[str] = Field(None, description="법령 검색어 (법령명 또는 키워드, 선택사항. 없으면 전체 목록 반환)")
    page: int = Field(1, description="페이지 번호", ge=1)
    per_page: int = Field(10, description="페이지당 결과 수", ge=1, le=100)


class GetLawRequest(BaseModel):
    """법령 조회 요청 모델 (통합: 상세 + 조문 + 단일 조문)"""
    law_id: Optional[str] = Field(None, description="법령 ID (lawService.do에 사용하는 ID, law_name과 둘 중 하나는 필수)")
    law_name: Optional[str] = Field(None, description="법령명 (예: '119구조·구급에 관한 법률 시행령', law_id와 둘 중 하나는 필수)")
    mode: str = Field("detail", description="조회 모드: 'detail'(상세정보), 'articles'(전체 조문), 'single'(단일 조문)")
    article_number: Optional[str] = Field(None, description="조 번호 (mode='single'일 때 필수, 예: '제1조', '제10조의2')")
    hang: Optional[str] = Field(None, description="항 번호 (mode='single'일 때 선택사항, 예: '제1항', '제2항')")
    ho: Optional[str] = Field(None, description="호 번호 (mode='single'일 때 선택사항, 예: '제2호', '제10호의2')")
    mok: Optional[str] = Field(None, description="목 (mode='single'일 때 선택사항, 예: '가', '나', '다')")


# 하위 호환성을 위한 레거시 모델 (deprecated)
class ListLawNamesRequest(BaseModel):
    """법령명 목록 조회 요청 모델 (deprecated: SearchLawRequest 사용)"""
    page: int = Field(1, description="페이지 번호", ge=1)
    per_page: int = Field(50, description="페이지당 결과 수", ge=1, le=100)
    query: Optional[str] = Field(None, description="검색어 (법령명으로 필터링, 선택사항)")


class GetLawDetailRequest(BaseModel):
    """법령 상세 조회 요청 모델 (deprecated: GetLawRequest 사용)"""
    law_name: str = Field(..., description="법령명 (예: '119구조·구급에 관한 법률 시행령')")

class GetLawArticlesRequest(BaseModel):
    """법령 조문 조회 요청 모델 (deprecated: GetLawRequest 사용)"""
    law_id: Optional[str] = Field(None, description="법령 ID (lawService.do에 사용하는 ID, law_name과 둘 중 하나는 필수)")
    law_name: Optional[str] = Field(None, description="법령명 (예: '119구조·구급에 관한 법률 시행령', law_id와 둘 중 하나는 필수)")

class GetSingleArticleRequest(BaseModel):
    """단일 조문 조회 요청 모델 (deprecated: GetLawRequest 사용)"""
    law_id: str = Field(..., description="법령 ID")
    article_number: str = Field(..., description="조 번호 (예: '제1조', '제10조의2')")
    hang: Optional[str] = Field(None, description="항 번호 (예: '제1항', '제2항')")
    ho: Optional[str] = Field(None, description="호 번호 (예: '제2호', '제10호의2')")
    mok: Optional[str] = Field(None, description="목 (예: '가', '나', '다')")


# 판례 관련 모델
class SearchPrecedentRequest(BaseModel):
    """판례 검색 요청 모델"""
    query: Optional[str] = Field(None, description="검색어 (판례명 또는 키워드)")
    page: int = Field(1, description="페이지 번호", ge=1)
    per_page: int = Field(20, description="페이지당 결과 수", ge=1, le=100)
    court: Optional[str] = Field(None, description="법원 종류 (대법원:400201, 하위법원:400202)")
    date_from: Optional[str] = Field(None, description="시작일자 (YYYYMMDD)")
    date_to: Optional[str] = Field(None, description="종료일자 (YYYYMMDD)")
    use_fallback: bool = Field(False, description="다단계 fallback 전략 사용 여부")
    issue_type: Optional[str] = Field(None, description="쟁점 유형 (예: '근로자성', '재산분할', '부당해고')")
    must_include: Optional[List[str]] = Field(None, description="반드시 포함할 키워드 리스트")


class GetPrecedentRequest(BaseModel):
    """판례 조회 요청 모델"""
    precedent_id: Optional[str] = Field(None, description="판례 일련번호 (precedent_id 또는 case_number 중 하나는 필수)")
    case_number: Optional[str] = Field(None, description="사건번호 (예: '2020다12345', precedent_id 또는 case_number 중 하나는 필수)")


# 법령해석 관련 모델
class SearchLawInterpretationRequest(BaseModel):
    """법령해석 검색 요청 모델"""
    query: Optional[str] = Field(None, description="검색어 (법령해석명 또는 키워드)")
    page: int = Field(1, description="페이지 번호", ge=1)
    per_page: int = Field(20, description="페이지당 결과 수", ge=1, le=100)
    agency: Optional[str] = Field(None, description="부처명 (예: '고용노동부', '국세청')")


class GetLawInterpretationRequest(BaseModel):
    """법령해석 조회 요청 모델"""
    interpretation_id: str = Field(..., description="법령해석 일련번호")


# 행정심판 관련 모델
class SearchAdministrativeAppealRequest(BaseModel):
    """행정심판 검색 요청 모델"""
    query: Optional[str] = Field(None, description="검색어 (행정심판 사건명 또는 키워드)")
    page: int = Field(1, description="페이지 번호", ge=1)
    per_page: int = Field(20, description="페이지당 결과 수", ge=1, le=100)
    date_from: Optional[str] = Field(None, description="시작일자 (YYYYMMDD)")
    date_to: Optional[str] = Field(None, description="종료일자 (YYYYMMDD)")


class GetAdministrativeAppealRequest(BaseModel):
    """행정심판 조회 요청 모델"""
    appeal_id: str = Field(..., description="행정심판 일련번호")


# 위원회 결정문 관련 모델
class SearchCommitteeDecisionRequest(BaseModel):
    """위원회 결정문 검색 요청 모델"""
    committee_type: str = Field(..., description="위원회 종류 (예: '개인정보보호위원회', '금융위원회', '노동위원회')")
    query: Optional[str] = Field(None, description="검색어 (결정문 사건명 또는 키워드)")
    page: int = Field(1, description="페이지 번호", ge=1)
    per_page: int = Field(20, description="페이지당 결과 수", ge=1, le=100)


class GetCommitteeDecisionRequest(BaseModel):
    """위원회 결정문 조회 요청 모델"""
    committee_type: str = Field(..., description="위원회 종류 (예: '개인정보보호위원회', '금융위원회')")
    decision_id: str = Field(..., description="결정문 일련번호")


# 헌재결정 관련 모델
class SearchConstitutionalDecisionRequest(BaseModel):
    """헌재결정 검색 요청 모델"""
    query: Optional[str] = Field(None, description="검색어 (헌재결정 사건명 또는 키워드)")
    page: int = Field(1, description="페이지 번호", ge=1)
    per_page: int = Field(20, description="페이지당 결과 수", ge=1, le=100)
    date_from: Optional[str] = Field(None, description="시작일자 (YYYYMMDD)")
    date_to: Optional[str] = Field(None, description="종료일자 (YYYYMMDD)")


class GetConstitutionalDecisionRequest(BaseModel):
    """헌재결정 조회 요청 모델"""
    decision_id: str = Field(..., description="헌재결정 일련번호")


# 특별행정심판 관련 모델
class SearchSpecialAdministrativeAppealRequest(BaseModel):
    """특별행정심판 검색 요청 모델"""
    tribunal_type: str = Field(..., description="심판원 종류 (예: '조세심판원', '해양안전심판원', '인사혁신처 소청심사위원회')")
    query: Optional[str] = Field(None, description="검색어 (재결례 사건명 또는 키워드)")
    page: int = Field(1, description="페이지 번호", ge=1)
    per_page: int = Field(20, description="페이지당 결과 수", ge=1, le=100)


class GetSpecialAdministrativeAppealRequest(BaseModel):
    """특별행정심판 조회 요청 모델"""
    tribunal_type: str = Field(..., description="심판원 종류 (예: '조세심판원', '해양안전심판원')")
    appeal_id: str = Field(..., description="재결례 일련번호")


# 법령 비교 관련 모델
class CompareLawsRequest(BaseModel):
    """법령 비교 요청 모델"""
    law_name: str = Field(..., description="법령명 (예: '형법', '민법')")
    compare_type: Literal["신구법", "연혁", "3단비교"] = Field(
        "신구법", 
        description="비교 유형: '신구법'(신구법 비교), '연혁'(법령 연혁), '3단비교'(3단 비교)"
    )


# 자치법규 관련 모델
class SearchLocalOrdinanceRequest(BaseModel):
    """자치법규 검색 요청 모델"""
    query: Optional[str] = Field(None, description="검색어 (조례명 또는 키워드)")
    local_government: Optional[str] = Field(None, description="지방자치단체명 (예: '서울시', '부산시')")
    page: int = Field(1, description="페이지 번호", ge=1)
    per_page: int = Field(20, description="페이지당 결과 수", ge=1, le=100)


# 행정규칙 관련 모델
class SearchAdministrativeRuleRequest(BaseModel):
    """행정규칙 검색 요청 모델"""
    query: Optional[str] = Field(None, description="검색어 (행정규칙명 또는 키워드)")
    agency: Optional[str] = Field(None, description="부처명 (예: '고용노동부', '교육부')")
    page: int = Field(1, description="페이지 번호", ge=1)
    per_page: int = Field(20, description="페이지당 결과 수", ge=1, le=100)