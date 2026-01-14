"""
Retry & Broadening Policy - 검색 실패/저품질 시 자동 전략 변경
0 결과 또는 저품질 결과일 때 자동으로 검색 전략을 조정
"""
from typing import Dict, List, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger("lexguard-mcp")


class ResultQuality(Enum):
    """결과 품질 등급"""
    EXCELLENT = "excellent"  # 관련성 높고 충분한 결과
    GOOD = "good"  # 관련성 있고 적절한 결과
    FAIR = "fair"  # 관련성 있지만 부족한 결과
    POOR = "poor"  # 관련성 낮거나 부족한 결과
    EMPTY = "empty"  # 결과 없음


class RetryStrategy(Enum):
    """재시도 전략"""
    EXPAND_DATE_RANGE = "expand_date_range"  # 날짜 범위 확장
    EXPAND_SYNONYMS = "expand_synonyms"  # 동의어 확장
    ADD_MUST_INCLUDE = "add_must_include"  # 필수 키워드 추가
    REMOVE_EXCLUDE = "remove_exclude"  # 제외 키워드 제거
    SIMPLIFY_QUERY = "simplify_query"  # 쿼리 단순화
    KEYWORD_ONLY = "keyword_only"  # 키워드만 사용
    NO_DATE_LIMIT = "no_date_limit"  # 날짜 제한 제거


class RetryPolicy:
    """재시도 정책 엔진"""
    
    def __init__(self):
        # 품질 판단 기준
        self.min_results_for_good = 3  # 최소 결과 수
        self.max_results_for_good = 100  # 최대 결과 수 (너무 많으면 노이즈)
        self.min_results_for_excellent = 5
        
    def evaluate_quality(
        self,
        total: int,
        results: List[Dict],
        query: str,
        must_include: Optional[List[str]] = None
    ) -> ResultQuality:
        """
        결과 품질 평가
        
        Args:
            total: 전체 결과 수
            results: 결과 리스트
            query: 검색 쿼리
            must_include: 필수 포함 키워드
            
        Returns:
            ResultQuality 등급
        """
        if total == 0:
            return ResultQuality.EMPTY
        
        if total < self.min_results_for_good:
            return ResultQuality.POOR
        
        if total > self.max_results_for_good:
            return ResultQuality.POOR  # 너무 많으면 노이즈
        
        # 결과가 적절한 범위에 있으면 GOOD
        if self.min_results_for_good <= total <= self.max_results_for_good:
            # 관련성 체크 (간단한 버전)
            relevance_score = self._check_relevance(results, query, must_include)
            if relevance_score > 0.7:
                return ResultQuality.EXCELLENT
            elif relevance_score > 0.4:
                return ResultQuality.GOOD
            else:
                return ResultQuality.FAIR
        
        return ResultQuality.GOOD
    
    def _check_relevance(
        self,
        results: List[Dict],
        query: str,
        must_include: Optional[List[str]] = None
    ) -> float:
        """
        결과의 관련성 점수 계산 (0.0 ~ 1.0)
        
        간단한 버전: 제목/요지에 쿼리 키워드 포함 여부
        """
        if not results:
            return 0.0
        
        query_lower = query.lower()
        query_keywords = set(query_lower.split())
        
        if must_include:
            query_keywords.update([k.lower() for k in must_include])
        
        relevant_count = 0
        for result in results[:10]:  # 상위 10개만 체크
            # 제목/요지 추출
            title = (
                result.get("title") or
                result.get("사건명") or
                result.get("case_name") or
                ""
            ).lower()
            
            summary = (
                result.get("summary") or
                result.get("판시사항") or
                result.get("판결요지") or
                ""
            ).lower()
            
            text = f"{title} {summary}"
            
            # 키워드 매칭
            matched_keywords = sum(1 for kw in query_keywords if kw in text)
            if matched_keywords > 0:
                relevant_count += 1
        
        return relevant_count / min(len(results), 10)
    
    def determine_strategy(
        self,
        quality: ResultQuality,
        current_query: str,
        date_from: Optional[str],
        date_to: Optional[str],
        must_include: Optional[List[str]],
        exclude: Optional[List[str]],
        attempt_count: int
    ) -> Tuple[Optional[RetryStrategy], Dict]:
        """
        재시도 전략 결정
        
        Args:
            quality: 결과 품질
            current_query: 현재 쿼리
            date_from: 현재 시작일
            date_to: 현재 종료일
            must_include: 현재 필수 키워드
            exclude: 현재 제외 키워드
            attempt_count: 시도 횟수
            
        Returns:
            (전략, 전략 파라미터) 튜플
        """
        if quality == ResultQuality.EXCELLENT or quality == ResultQuality.GOOD:
            return None, {}  # 재시도 불필요
        
        if attempt_count > 5:
            # 너무 많이 시도했으면 중단
            logger.warning("Max retry attempts reached")
            return None, {}
        
        # EMPTY 또는 POOR인 경우 전략 결정
        if quality == ResultQuality.EMPTY:
            # 1차: 날짜 범위 확장
            if date_from or date_to:
                if attempt_count == 1:
                    return RetryStrategy.EXPAND_DATE_RANGE, {
                        "years": 10  # 10년으로 확장
                    }
                elif attempt_count == 2:
                    return RetryStrategy.NO_DATE_LIMIT, {}
            
            # 2차: 동의어 확장
            if attempt_count <= 2:
                return RetryStrategy.EXPAND_SYNONYMS, {}
            
            # 3차: 쿼리 단순화
            if attempt_count == 3:
                return RetryStrategy.SIMPLIFY_QUERY, {}
            
            # 4차: 키워드만
            if attempt_count >= 4:
                return RetryStrategy.KEYWORD_ONLY, {}
        
        elif quality == ResultQuality.POOR:
            # 결과가 너무 많으면 필터 강화
            # 결과가 너무 적으면 필터 완화
            
            # must_include가 없으면 법리 키워드 추가
            if not must_include:
                return RetryStrategy.ADD_MUST_INCLUDE, {
                    "keywords": self._extract_legal_keywords(current_query)
                }
            
            # exclude가 있으면 제거
            if exclude:
                return RetryStrategy.REMOVE_EXCLUDE, {}
        
        elif quality == ResultQuality.FAIR:
            # 관련성 향상을 위해 must_include 추가
            if not must_include or len(must_include) < 2:
                return RetryStrategy.ADD_MUST_INCLUDE, {
                    "keywords": self._extract_legal_keywords(current_query)
                }
        
        return None, {}
    
    def _extract_legal_keywords(self, query: str) -> List[str]:
        """
        쿼리에서 법리 키워드 추출
        
        간단한 버전: 하드코딩된 법리 키워드 매칭
        """
        from .query_planner import LEGAL_CORE_KEYWORDS
        
        query_lower = query.lower()
        found_keywords = []
        
        for keyword in LEGAL_CORE_KEYWORDS:
            if keyword in query_lower:
                found_keywords.append(keyword)
        
        return found_keywords[:3]  # 최대 3개
    
    def apply_strategy(
        self,
        strategy: RetryStrategy,
        current_query: str,
        date_from: Optional[str],
        date_to: Optional[str],
        must_include: Optional[List[str]],
        exclude: Optional[List[str]],
        strategy_params: Dict
    ) -> Dict:
        """
        전략을 실제 파라미터 변경으로 적용
        
        Returns:
            업데이트된 검색 파라미터 딕셔너리
        """
        new_params = {
            "query": current_query,
            "date_from": date_from,
            "date_to": date_to,
            "must_include": must_include or [],
            "exclude": exclude or []
        }
        
        if strategy == RetryStrategy.EXPAND_DATE_RANGE:
            from .query_planner import calculate_date_range
            years = strategy_params.get("years", 10)
            new_params["date_from"], new_params["date_to"] = calculate_date_range(years)
        
        elif strategy == RetryStrategy.NO_DATE_LIMIT:
            new_params["date_from"] = None
            new_params["date_to"] = None
        
        elif strategy == RetryStrategy.EXPAND_SYNONYMS:
            # 쿼리 자체는 변경하지 않고, 동의어 확장 플래그만 설정
            new_params["expand_synonyms"] = True
        
        elif strategy == RetryStrategy.ADD_MUST_INCLUDE:
            keywords = strategy_params.get("keywords", [])
            if keywords:
                new_params["must_include"] = (must_include or []) + keywords
        
        elif strategy == RetryStrategy.REMOVE_EXCLUDE:
            new_params["exclude"] = []
        
        elif strategy == RetryStrategy.SIMPLIFY_QUERY:
            from .query_planner import extract_keywords
            keywords = extract_keywords(current_query)
            new_params["query"] = " ".join(keywords[:3])  # 상위 3개만
        
        elif strategy == RetryStrategy.KEYWORD_ONLY:
            from .query_planner import extract_keywords
            keywords = extract_keywords(current_query)
            new_params["query"] = " ".join(keywords[:2])  # 상위 2개만
            new_params["date_from"] = None
            new_params["date_to"] = None
        
        return new_params

