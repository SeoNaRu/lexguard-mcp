"""
Result Normalizer - 검색 결과를 통일된 스키마로 변환
API마다 다른 포맷을 공통 스키마로 정규화
"""
import re
import html
from typing import Dict, List, Optional, Any
from datetime import datetime


# 공통 결과 스키마
class NormalizedResult:
    """정규화된 검색 결과"""
    def __init__(
        self,
        id: str,
        title: str,
        court: Optional[str] = None,
        date: Optional[str] = None,
        summary: Optional[str] = None,
        url: Optional[str] = None,
        raw_score: Optional[float] = None,
        source: str = "unknown",
        raw_data: Optional[Dict] = None
    ):
        self.id = id
        self.title = title
        self.court = court
        self.date = date
        self.summary = summary
        self.url = url
        self.raw_score = raw_score
        self.source = source
        self.raw_data = raw_data or {}
    
    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            "id": self.id,
            "title": self.title,
            "court": self.court,
            "date": self.date,
            "summary": self.summary,
            "url": self.url,
            "raw_score": self.raw_score,
            "source": self.source,
            "raw_data": self.raw_data
        }


def clean_html(text: str) -> str:
    """HTML 태그 및 특수문자 정리"""
    if not text:
        return ""
    
    # HTML 엔티티 디코딩
    text = html.unescape(text)
    
    # HTML 태그 제거
    text = re.sub(r'<[^>]+>', '', text)
    
    # 연속 공백 정리
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def normalize_date(date_str: Optional[str]) -> Optional[str]:
    """날짜 문자열 정규화 (YYYYMMDD 형식으로)"""
    if not date_str:
        return None
    
    # 이미 YYYYMMDD 형식인 경우
    if re.match(r'^\d{8}$', date_str):
        return date_str
    
    # YYYY.MM.DD 형식
    match = re.match(r'(\d{4})\.(\d{2})\.(\d{2})', date_str)
    if match:
        return f"{match.group(1)}{match.group(2)}{match.group(3)}"
    
    # YYYY-MM-DD 형식
    match = re.match(r'(\d{4})-(\d{2})-(\d{2})', date_str)
    if match:
        return f"{match.group(1)}{match.group(2)}{match.group(3)}"
    
    # YYYY/MM/DD 형식
    match = re.match(r'(\d{4})/(\d{2})/(\d{2})', date_str)
    if match:
        return f"{match.group(1)}{match.group(2)}{match.group(3)}"
    
    # 년도만 추출
    year_match = re.search(r'(\d{4})', date_str)
    if year_match:
        return f"{year_match.group(1)}0101"  # 기본값: 1월 1일
    
    return None


def normalize_precedent(precedent_data: Dict, source: str = "law_api") -> Optional[NormalizedResult]:
    """
    판례 데이터를 정규화된 형식으로 변환
    
    Args:
        precedent_data: 원본 판례 데이터 (API 응답)
        source: 데이터 소스 식별자
        
    Returns:
        NormalizedResult 또는 None (파싱 실패 시)
    """
    if not isinstance(precedent_data, dict):
        return None
    
    # ID 추출 (여러 가능한 필드명 시도)
    result_id = (
        precedent_data.get("판례정보일련번호") or
        precedent_data.get("일련번호") or
        precedent_data.get("id") or
        precedent_data.get("precedent_id") or
        ""
    )
    
    if not result_id:
        return None
    
    # 제목 추출
    title = (
        precedent_data.get("사건명") or
        precedent_data.get("case_name") or
        precedent_data.get("제목") or
        precedent_data.get("title") or
        ""
    )
    title = clean_html(title)
    
    # 법원 추출
    court = (
        precedent_data.get("법원명") or
        precedent_data.get("court") or
        precedent_data.get("법원종류명") or
        None
    )
    if court:
        court = clean_html(court)
    
    # 날짜 추출 및 정규화
    date_str = (
        precedent_data.get("선고일자") or
        precedent_data.get("date") or
        precedent_data.get("선고일") or
        None
    )
    date = normalize_date(date_str)
    
    # 요지/요약 추출
    summary = (
        precedent_data.get("판시사항") or
        precedent_data.get("판결요지") or
        precedent_data.get("요지") or
        precedent_data.get("summary") or
        precedent_data.get("판례내용") or
        None
    )
    if summary:
        summary = clean_html(summary)
        # 너무 길면 잘라내기 (500자)
        if len(summary) > 500:
            summary = summary[:500] + "..."
    
    # URL 생성 (API URL 기반)
    url = None
    if result_id:
        url = f"https://www.law.go.kr/DRF/lawService.do?OC=LexGuardKey&target=prec&ID={result_id}&type=HTML"
    
    # 사건번호 (추가 정보)
    case_number = (
        precedent_data.get("사건번호") or
        precedent_data.get("case_number") or
        None
    )
    
    return NormalizedResult(
        id=str(result_id),
        title=title or f"판례 {result_id}",
        court=court,
        date=date,
        summary=summary,
        url=url,
        raw_score=None,  # API에서 제공하지 않음
        source=source,
        raw_data={
            **precedent_data,
            "case_number": case_number
        }
    )


def normalize_law(law_data: Dict, source: str = "law_api") -> Optional[NormalizedResult]:
    """
    법령 데이터를 정규화된 형식으로 변환
    
    Args:
        law_data: 원본 법령 데이터 (API 응답)
        source: 데이터 소스 식별자
        
    Returns:
        NormalizedResult 또는 None
    """
    if not isinstance(law_data, dict):
        return None
    
    # ID 추출
    result_id = (
        law_data.get("법령ID") or
        law_data.get("law_id") or
        law_data.get("id") or
        ""
    )
    
    if not result_id:
        return None
    
    # 제목 (법령명)
    title = (
        law_data.get("법령명한글") or
        law_data.get("법령명") or
        law_data.get("lawNm") or
        law_data.get("lawNmKo") or
        law_data.get("title") or
        ""
    )
    title = clean_html(title)
    
    # 날짜 (시행일)
    date_str = (
        law_data.get("시행일자") or
        law_data.get("시행일") or
        law_data.get("date") or
        None
    )
    date = normalize_date(date_str)
    
    # 요약 (법령 개요)
    summary = (
        law_data.get("법령내용") or
        law_data.get("개요") or
        law_data.get("summary") or
        None
    )
    if summary:
        summary = clean_html(summary)
        if len(summary) > 500:
            summary = summary[:500] + "..."
    
    # URL
    url = None
    if result_id:
        url = f"https://www.law.go.kr/DRF/lawService.do?OC=LexGuardKey&target=law&MST={result_id}&type=HTML"
    
    return NormalizedResult(
        id=str(result_id),
        title=title or f"법령 {result_id}",
        court=None,  # 법령은 법원 없음
        date=date,
        summary=summary,
        url=url,
        raw_score=None,
        source=source,
        raw_data=law_data
    )


def normalize_search_results(
    results: List[Dict],
    result_type: str = "precedent",
    source: str = "law_api"
) -> List[NormalizedResult]:
    """
    검색 결과 리스트를 정규화
    
    Args:
        results: 원본 결과 리스트
        result_type: 결과 타입 ("precedent", "law", "interpretation" 등)
        source: 데이터 소스 식별자
        
    Returns:
        정규화된 결과 리스트
    """
    normalized = []
    
    for item in results:
        if not isinstance(item, dict):
            continue
        
        if result_type == "precedent":
            norm_result = normalize_precedent(item, source)
        elif result_type == "law":
            norm_result = normalize_law(item, source)
        else:
            # 기본 처리 (일반적인 구조)
            result_id = item.get("id") or item.get("일련번호") or ""
            if result_id:
                norm_result = NormalizedResult(
                    id=str(result_id),
                    title=clean_html(item.get("title") or item.get("제목") or ""),
                    court=item.get("court") or item.get("법원명"),
                    date=normalize_date(item.get("date") or item.get("날짜")),
                    summary=clean_html(item.get("summary") or item.get("요지") or ""),
                    url=item.get("url"),
                    raw_score=item.get("score"),
                    source=source,
                    raw_data=item
                )
            else:
                norm_result = None
        
        if norm_result:
            normalized.append(norm_result)
    
    return normalized


def normalize_search_response(
    response: Dict,
    result_type: str = "precedent"
) -> Dict:
    """
    전체 검색 응답을 정규화
    
    Args:
        response: 원본 API 응답
        result_type: 결과 타입
        
    Returns:
        정규화된 응답 딕셔너리
    """
    # 에러가 있으면 그대로 반환
    if "error" in response:
        return response
    
    # 결과 리스트 추출
    results = []
    if result_type == "precedent":
        results = response.get("precedents", [])
    elif result_type == "law":
        results = response.get("laws", [])
    else:
        results = response.get("results", [])
    
    # 정규화
    normalized_results = normalize_search_results(results, result_type)
    
    # 정규화된 응답 구성
    normalized_response = {
        "query": response.get("query"),
        "page": response.get("page", 1),
        "per_page": response.get("per_page", 20),
        "total": response.get("total", len(normalized_results)),
        "normalized_results": [r.to_dict() for r in normalized_results],
        "query_plan": response.get("query_plan"),
        "attempts": response.get("attempts"),
        "fallback_used": response.get("fallback_used", False),
        "api_url": response.get("api_url")
    }
    
    # 원본 결과도 포함 (호환성)
    if result_type == "precedent":
        normalized_response["precedents"] = response.get("precedents", [])
    elif result_type == "law":
        normalized_response["laws"] = response.get("laws", [])
    
    return normalized_response

