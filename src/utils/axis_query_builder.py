"""
Axis Query Builder - 법리축/사실축 분리 쿼리 생성
법리 키워드와 사실 키워드를 분리하여 단계적 검색 전략 수립
"""
from typing import List, Dict, Optional, Tuple
from ..utils.query_planner import LEGAL_CORE_KEYWORDS, extract_keywords


# 법리축 키워드 사전
LEGAL_AXIS_KEYWORDS = {
    "근로자성": ["근로자성", "사용종속관계", "지휘감독", "종속관계", "근로관계"],
    "근로기준법": ["근로기준법", "근기법", "제2조", "근로자 정의"],
    "임금": ["임금", "급여", "보수", "근로의 대가"],
    "해고": ["해고", "부당해고", "정당한 사유", "권리남용"],
    "계약": ["계약", "계약서", "위약", "계약위반"],
    "손해배상": ["손해배상", "불법행위", "과실", "과실상계"],
    "재산분할": ["재산분할", "부부재산", "재산분할청구"],
    "상속": ["상속", "상속분", "상속재산", "유산"]
}

# 사실축 키워드 패턴
FACT_AXIS_PATTERNS = [
    "프리랜서", "외주", "도급", "위탁", "계약직",
    "출퇴근", "근무시간", "근무장소", "통제",
    "전속", "배타적", "겸직",
    "월급", "고정급", "수수료", "성과급",
    "해고당함", "퇴직", "사직",
    "임금체불", "미지급", "체불",
    "이혼", "재산", "부동산",
    "자녀", "양육", "친권"
]


class AxisQueryBuilder:
    """법리축/사실축 분리 쿼리 빌더"""
    
    def __init__(self):
        self.legal_axis_keywords = LEGAL_AXIS_KEYWORDS
        self.fact_axis_patterns = FACT_AXIS_PATTERNS
    
    def build_axis_queries(
        self,
        query: str,
        issue_type: Optional[str] = None
    ) -> Dict:
        """
        법리축/사실축 분리 쿼리 세트 생성
        
        Args:
            query: 원본 쿼리
            issue_type: 쟁점 유형
            
        Returns:
            쿼리 전략 딕셔너리:
            - legal_axis: 법리축 키워드 리스트
            - fact_axis: 사실축 키워드 리스트
            - query_plan: 단계별 쿼리 전략
        """
        # 법리축 키워드 추출
        legal_axis = self._extract_legal_axis(query, issue_type)
        
        # 사실축 키워드 추출
        fact_axis = self._extract_fact_axis(query)
        
        # 쿼리 전략 생성
        query_plan = self._build_query_plan(legal_axis, fact_axis, query)
        
        return {
            "legal_axis": legal_axis,
            "fact_axis": fact_axis,
            "query_plan": query_plan,
            "original_query": query
        }
    
    def _extract_legal_axis(
        self,
        query: str,
        issue_type: Optional[str]
    ) -> List[str]:
        """법리축 키워드 추출"""
        legal_keywords = []
        query_lower = query.lower()
        
        # issue_type 기반 법리 키워드
        if issue_type:
            issue_keywords = self.legal_axis_keywords.get(issue_type, [])
            for kw in issue_keywords:
                if kw.lower() in query_lower or kw in query:
                    legal_keywords.append(kw)
        
        # 법리 핵심 키워드 매칭
        for keyword in LEGAL_CORE_KEYWORDS:
            if keyword in query_lower:
                legal_keywords.append(keyword)
        
        # 법령명 추출
        import re
        law_pattern = r'([가-힣]+법)'
        law_matches = re.findall(law_pattern, query)
        legal_keywords.extend(law_matches)
        
        # 조문 추출
        article_pattern = r'제?\s*(\d+)\s*조'
        article_matches = re.findall(article_pattern, query)
        if article_matches:
            # 법령명과 조문 결합
            for law in law_matches:
                legal_keywords.append(f"{law} 제{article_matches[0]}조")
        
        # 중복 제거 및 정렬
        legal_keywords = list(dict.fromkeys(legal_keywords))
        
        return legal_keywords[:5]  # 최대 5개
    
    def _extract_fact_axis(self, query: str) -> List[str]:
        """사실축 키워드 추출"""
        fact_keywords = []
        query_lower = query.lower()
        
        # 사실 패턴 매칭
        for pattern in self.fact_axis_patterns:
            if pattern in query_lower:
                fact_keywords.append(pattern)
        
        # 일반 키워드 추출 (법리 키워드 제외)
        all_keywords = extract_keywords(query)
        legal_keywords_set = set(LEGAL_CORE_KEYWORDS)
        
        for kw in all_keywords:
            if kw not in legal_keywords_set and len(kw) >= 2:
                fact_keywords.append(kw)
        
        # 중복 제거
        fact_keywords = list(dict.fromkeys(fact_keywords))
        
        return fact_keywords[:5]  # 최대 5개
    
    def _build_query_plan(
        self,
        legal_axis: List[str],
        fact_axis: List[str],
        original_query: str
    ) -> List[Dict]:
        """단계별 쿼리 전략 생성"""
        query_plan = []
        
        # 1차: 법리축만 (넓게)
        if legal_axis:
            query_plan.append({
                "step": 1,
                "strategy": "legal_axis_only",
                "query": " ".join(legal_axis[:3]),  # 상위 3개만
                "priority": 1,
                "description": "법리축 키워드만으로 넓게 검색"
            })
        
        # 2차: 법리축 AND 사실축 (정밀)
        if legal_axis and fact_axis:
            # 법리축 상위 2개 + 사실축 상위 2개
            combined = " ".join(legal_axis[:2] + fact_axis[:2])
            query_plan.append({
                "step": 2,
                "strategy": "legal_and_fact",
                "query": combined,
                "priority": 2,
                "description": "법리축과 사실축 결합하여 정밀 검색"
            })
        
        # 3차: 사실축만 (법리축이 너무 좁을 때)
        if fact_axis and not legal_axis:
            query_plan.append({
                "step": 3,
                "strategy": "fact_axis_only",
                "query": " ".join(fact_axis[:3]),
                "priority": 3,
                "description": "사실축 키워드만으로 검색"
            })
        
        # 4차: 원본 쿼리 (fallback)
        query_plan.append({
            "step": 4,
            "strategy": "original",
            "query": original_query,
            "priority": 4,
            "description": "원본 쿼리로 검색"
        })
        
        return query_plan
    
    def refine_query_by_axis(
        self,
        legal_axis: List[str],
        fact_axis: List[str],
        missing_aspects: List[str]
    ) -> List[str]:
        """
        누락된 측면에 따라 쿼리 정제
        
        Args:
            legal_axis: 법리축 키워드
            fact_axis: 사실축 키워드
            missing_aspects: 누락된 측면 리스트
            
        Returns:
            정제된 쿼리 리스트
        """
        refined_queries = []
        
        if "legal_axis_missing" in missing_aspects:
            # 법리축 강화
            if legal_axis:
                refined_queries.append(" ".join(legal_axis))
        
        if "fact_axis_missing" in missing_aspects:
            # 사실축 강화
            if fact_axis:
                refined_queries.append(" ".join(fact_axis))
        
        if "legal_axis_partial" in missing_aspects or "fact_axis_partial" in missing_aspects:
            # 법리축 + 사실축 결합
            if legal_axis and fact_axis:
                refined_queries.append(" ".join(legal_axis[:2] + fact_axis[:2]))
        
        return refined_queries


# 전역 인스턴스
_axis_query_builder = None


def get_axis_query_builder() -> AxisQueryBuilder:
    """AxisQueryBuilder 싱글톤 인스턴스 반환"""
    global _axis_query_builder
    if _axis_query_builder is None:
        _axis_query_builder = AxisQueryBuilder()
    return _axis_query_builder

