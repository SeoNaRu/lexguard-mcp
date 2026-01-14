"""
Query Planner - 검색 쿼리 생성 및 최적화 유틸리티
자연어 질문 → 검색 API용 쿼리 세트 변환
"""
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta


# 한국어 불용어 리스트 (조사, 요청 표현 등)
KOREAN_STOPWORDS = {
    # 조사
    "이", "가", "을", "를", "에", "에서", "의", "와", "과", "로", "으로", "도", "만", "부터", "까지", "에게", "한테",
    # 요청 표현
    "해줘", "해주세요", "해줘요", "알려줘", "알려주세요", "찾아줘", "찾아주세요", "확인해줘", "확인해주세요",
    "알려줘요", "찾아줘요", "확인해줘요", "주세요", "해줘요",
    # 일반 불용어
    "문제", "확인", "질문", "문의", "것", "때", "경우", "때문", "위해", "대해", "관련", "대한",
    "처럼", "같이", "이런", "저런", "그런", "어떤", "무엇", "어떻게", "왜", "언제", "어디",
    "있어요", "있습니다", "있어", "없어요", "없습니다", "없어",
    "입니다", "입니다", "이에요", "예요", "이야", "야",
    "뭐", "뭔", "뭘", "뭐야", "뭐예요",
    # 법률 검색에 불필요한 일반 동사
    "하다", "되다", "이다", "있다", "없다", "알다", "모르다", "보다", "듣다", "말하다",
}


# 법률 핵심 키워드 (우선순위 높음)
LEGAL_CORE_KEYWORDS = {
    "근로", "종속", "지휘", "감독", "출퇴근", "전속", "도급", "위장", "프리랜서",
    "임금", "퇴직금", "해고", "부당", "계약", "고용", "근로자", "사용자",
    "법률", "법령", "조문", "항", "호", "목",
    "판례", "결정", "심판", "재판", "소송",
    "재산", "분할", "상속", "혼인", "이혼",
    "손해", "배상", "계약", "위약", "불법",
    "개인정보", "보호", "유출", "침해",
    "세금", "소득세", "부가세", "과세",
}


# 동의어 사전 (법리 축 유지)
LEGAL_SYNONYMS: Dict[str, List[str]] = {
    # 근로자성 관련
    "프리랜서": ["위장도급", "특수형태근로종사자", "도급계약", "위탁계약"],
    "근로자성": ["사용종속관계", "지휘감독", "종속적 노무제공", "근로관계"],
    "사용종속관계": ["근로자성", "종속관계", "지휘감독관계"],
    "지휘감독": ["근로자성", "사용종속관계", "종속성"],
    "출퇴근": ["근무시간", "근무장소", "통제"],
    "전속성": ["전속근로", "배타적 근로"],
    
    # 임금 관련
    "임금": ["급여", "봉급", "월급", "보수"],
    "퇴직금": ["퇴직급여", "퇴직보상금"],
    "해고": ["해직", "정리해고", "부당해고"],
    
    # 계약 관련
    "계약": ["계약서", "합의", "약정"],
    "위약": ["위약금", "손해배상"],
    
    # 재산 관련
    "재산분할": ["재산분할청구", "재산분할소송"],
    "상속": ["상속분", "상속재산"],
}


def remove_stopwords(text: str) -> str:
    """
    한국어 불용어를 제거합니다.
    
    Args:
        text: 입력 텍스트
        
    Returns:
        불용어가 제거된 텍스트
    """
    words = text.split()
    filtered_words = [w for w in words if w not in KOREAN_STOPWORDS]
    return " ".join(filtered_words)


def extract_keywords(text: str, min_length: int = 2) -> List[str]:
    """
    텍스트에서 핵심 키워드를 추출합니다.
    불용어 제거 + 법률 핵심 키워드 우선순위 적용
    
    Args:
        text: 입력 텍스트
        min_length: 최소 키워드 길이
        
    Returns:
        추출된 키워드 리스트 (우선순위 순)
    """
    # 1. 불용어 제거
    cleaned = remove_stopwords(text)
    
    # 2. 단어 분리 (공백 기준)
    words = cleaned.split()
    
    # 3. 핵심 키워드 우선순위 적용
    core_keywords = []
    other_keywords = []
    
    for word in words:
        word = word.strip()
        if len(word) < min_length:
            continue
        
        # 법률 핵심 키워드인지 확인 (부분 일치)
        is_core = any(core in word or word in core for core in LEGAL_CORE_KEYWORDS)
        
        if is_core:
            core_keywords.append(word)
        else:
            other_keywords.append(word)
    
    # 핵심 키워드 우선, 나머지 키워드 후순
    return core_keywords + other_keywords


def expand_synonyms(query: str, preserve_legal_axis: bool = True) -> List[str]:
    """
    동의어를 확장하여 쿼리 세트를 생성합니다.
    법리 축을 유지하면서 확장합니다.
    
    Args:
        query: 원본 쿼리
        preserve_legal_axis: 법리 축 유지 여부
        
    Returns:
        확장된 쿼리 리스트 (원본 포함)
    """
    queries = [query]  # 원본 포함
    
    words = query.split()
    expanded_queries = []
    
    for word in words:
        if word in LEGAL_SYNONYMS:
            synonyms = LEGAL_SYNONYMS[word]
            for synonym in synonyms:
                # 원본 단어를 동의어로 치환
                new_query = query.replace(word, synonym)
                if new_query != query:
                    expanded_queries.append(new_query)
    
    # 중복 제거
    queries.extend(expanded_queries)
    return list(dict.fromkeys(queries))  # 순서 유지하면서 중복 제거


def build_query_set(
    original_query: str,
    issue_type: Optional[str] = None,
    must_include: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None
) -> List[Dict[str, any]]:
    """
    검색 쿼리 세트를 생성합니다.
    
    Args:
        original_query: 원본 자연어 쿼리
        issue_type: 쟁점 유형 (예: "근로자성", "재산분할")
        must_include: 반드시 포함할 키워드 리스트
        exclude: 제외할 키워드 리스트
        
    Returns:
        쿼리 세트 리스트 (각 쿼리는 dict 형태)
    """
    query_set = []
    
    # 1차: 원본 쿼리 (키워드 추출)
    keywords = extract_keywords(original_query)
    if keywords:
        query_set.append({
            "query": " ".join(keywords),
            "strategy": "keyword_extraction",
            "priority": 1
        })
    
    # 2차: must_include와 결합
    if must_include:
        combined = " ".join(must_include + keywords[:3])
        query_set.append({
            "query": combined,
            "strategy": "must_include_combined",
            "priority": 2
        })
    
    # 3차: 동의어 확장
    if keywords:
        base_query = " ".join(keywords[:3])  # 상위 3개 키워드만
        expanded = expand_synonyms(base_query)
        for i, eq in enumerate(expanded[1:], start=1):  # 원본 제외
            query_set.append({
                "query": eq,
                "strategy": f"synonym_expansion_{i}",
                "priority": 3
            })
    
    # 4차: issue_type 기반 쿼리
    if issue_type:
        issue_keywords = extract_keywords(issue_type)
        if issue_keywords:
            query_set.append({
                "query": " ".join(issue_keywords),
                "strategy": "issue_type_based",
                "priority": 4
            })
    
    # exclude 적용
    if exclude:
        query_set = [
            q for q in query_set
            if not any(ex in q["query"] for ex in exclude)
        ]
    
    # priority 순으로 정렬
    query_set.sort(key=lambda x: x["priority"])
    
    return query_set


def calculate_date_range(years_back: int) -> Tuple[Optional[str], Optional[str]]:
    """
    현재 날짜 기준으로 N년 전부터 현재까지의 날짜 범위를 계산합니다.
    
    Args:
        years_back: 몇 년 전부터 (예: 5 = 5년 전부터)
        
    Returns:
        (date_from, date_to) 튜플 (YYYYMMDD 형식)
    """
    today = datetime.now()
    start_date = today - timedelta(days=years_back * 365)
    
    date_from = start_date.strftime("%Y%m%d")
    date_to = today.strftime("%Y%m%d")
    
    return date_from, date_to


def expand_date_range_stepwise(
    current_date_from: Optional[str],
    current_date_to: Optional[str],
    step: int = 1
) -> Tuple[Optional[str], Optional[str]]:
    """
    날짜 범위를 단계적으로 확장합니다.
    5년(기본) → 10년 → 전체
    
    Args:
        current_date_from: 현재 시작일 (YYYYMMDD) - 사용 안 함, step 기준으로 계산
        current_date_to: 현재 종료일 (YYYYMMDD) - 사용 안 함, step 기준으로 계산
        step: 확장 단계 (1=10년, 2=전체)
        
    Returns:
        확장된 (date_from, date_to) 튜플
    """
    if step == 1:
        # 10년
        return calculate_date_range(10)
    elif step >= 2:
        # 전체 (날짜 제한 없음)
        return None, None
    else:
        # 기본값: 5년 (이미 적용된 상태)
        return calculate_date_range(5)

