"""
Query Judge - 쿼리 자동 평가기
검색 결과가 질문에 맞는지 점수화하고 다음 행동을 결정
"""
from typing import List, Dict, Optional, Tuple
import re
from ..utils.query_planner import LEGAL_CORE_KEYWORDS


class QueryJudge:
    """쿼리 평가기"""
    
    def __init__(self):
        # 법리 키워드 가중치
        self.legal_keyword_weight = 2.0
        self.fact_keyword_weight = 1.0
        
        # 최소 적합도 점수
        self.min_relevance_threshold = 0.3
        self.good_relevance_threshold = 0.6
    
    def evaluate_results(
        self,
        query: str,
        issue_type: Optional[str],
        results: List[Dict],
        legal_axis_keywords: Optional[List[str]] = None,
        fact_axis_keywords: Optional[List[str]] = None
    ) -> Dict:
        """
        검색 결과의 적합도를 평가
        
        Args:
            query: 원본 쿼리
            issue_type: 쟁점 유형
            results: 검색 결과 리스트 (최대 top-k)
            legal_axis_keywords: 법리축 키워드
            fact_axis_keywords: 사실축 키워드
            
        Returns:
            평가 결과 딕셔너리:
            - relevance_score: 전체 적합도 점수 (0.0 ~ 1.0)
            - missing_aspects: 누락된 측면 리스트
            - next_plan: 다음 행동 계획
            - individual_scores: 각 결과별 점수
        """
        if not results:
            return {
                "relevance_score": 0.0,
                "missing_aspects": ["no_results"],
                "next_plan": {
                    "action": "expand_query",
                    "strategy": "synonym_expansion"
                },
                "individual_scores": []
            }
        
        # 쿼리 키워드 추출
        query_lower = query.lower()
        query_keywords = set(query_lower.split())
        
        # 법리축/사실축 키워드 설정
        if legal_axis_keywords:
            legal_keywords = set([k.lower() for k in legal_axis_keywords])
        else:
            legal_keywords = self._extract_legal_keywords(query)
        
        if fact_axis_keywords:
            fact_keywords = set([k.lower() for k in fact_axis_keywords])
        else:
            fact_keywords = self._extract_fact_keywords(query)
        
        # 각 결과 평가
        individual_scores = []
        for result in results:
            score = self._evaluate_single_result(
                result,
                query_keywords,
                legal_keywords,
                fact_keywords,
                issue_type
            )
            individual_scores.append({
                "result_id": result.get("id") or result.get("판례정보일련번호") or "",
                "title": result.get("title") or result.get("사건명") or "",
                "score": score
            })
        
        # 전체 적합도 점수 (상위 결과들의 평균)
        top_scores = [s["score"] for s in individual_scores[:5]]
        relevance_score = sum(top_scores) / len(top_scores) if top_scores else 0.0
        
        # 누락된 측면 분석
        missing_aspects = self._analyze_missing_aspects(
            results,
            legal_keywords,
            fact_keywords,
            issue_type
        )
        
        # 다음 행동 계획
        next_plan = self._determine_next_plan(
            relevance_score,
            missing_aspects,
            legal_keywords,
            fact_keywords
        )
        
        return {
            "relevance_score": relevance_score,
            "missing_aspects": missing_aspects,
            "next_plan": next_plan,
            "individual_scores": individual_scores,
            "legal_keywords_found": list(legal_keywords),
            "fact_keywords_found": list(fact_keywords)
        }
    
    def _evaluate_single_result(
        self,
        result: Dict,
        query_keywords: set,
        legal_keywords: set,
        fact_keywords: set,
        issue_type: Optional[str]
    ) -> float:
        """
        단일 결과의 적합도 점수 계산 (0.0 ~ 1.0)
        """
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
            result.get("요지") or
            ""
        ).lower()
        
        text = f"{title} {summary}"
        
        score = 0.0
        max_score = 0.0
        
        # 법리축 키워드 매칭 (높은 가중치)
        if legal_keywords:
            legal_matches = sum(1 for kw in legal_keywords if kw in text)
            legal_score = (legal_matches / len(legal_keywords)) * self.legal_keyword_weight
            score += legal_score
            max_score += self.legal_keyword_weight
        
        # 사실축 키워드 매칭
        if fact_keywords:
            fact_matches = sum(1 for kw in fact_keywords if kw in text)
            fact_score = (fact_matches / len(fact_keywords)) * self.fact_keyword_weight
            score += fact_score
            max_score += self.fact_keyword_weight
        
        # 일반 쿼리 키워드 매칭
        if query_keywords:
            query_matches = sum(1 for kw in query_keywords if kw in text)
            query_score = query_matches / len(query_keywords)
            score += query_score
            max_score += 1.0
        
        # issue_type 매칭 보너스
        if issue_type and issue_type.lower() in text:
            score += 0.2
            max_score += 0.2
        
        # 제목 매칭 보너스
        title_matches = sum(1 for kw in query_keywords if kw in title)
        if title_matches > 0:
            score += 0.3
            max_score += 0.3
        
        # 정규화
        if max_score > 0:
            score = min(score / max_score, 1.0)
        
        return score
    
    def _extract_legal_keywords(self, query: str) -> set:
        """법리축 키워드 추출"""
        query_lower = query.lower()
        legal_keywords = set()
        
        # 법리 핵심 키워드 매칭
        for keyword in LEGAL_CORE_KEYWORDS:
            if keyword in query_lower:
                legal_keywords.add(keyword)
        
        # 법령명 패턴 (예: "근로기준법", "민법")
        law_pattern = r'([가-힣]+법)'
        law_matches = re.findall(law_pattern, query)
        legal_keywords.update([m.lower() for m in law_matches])
        
        # 조문 패턴 (예: "제2조", "2조")
        article_pattern = r'제?\s*(\d+)\s*조'
        article_matches = re.findall(article_pattern, query)
        if article_matches:
            legal_keywords.add("조문")
        
        return legal_keywords
    
    def _extract_fact_keywords(self, query: str) -> set:
        """사실축 키워드 추출"""
        query_lower = query.lower()
        fact_keywords = set()
        
        # 사실관계 키워드 (법리 키워드 제외)
        fact_patterns = [
            "프리랜서", "외주", "출퇴근", "전속", "월급", "고정급",
            "해고", "퇴직", "임금", "체불", "계약", "위약",
            "재산", "이혼", "양육", "상속", "손해", "배상"
        ]
        
        for pattern in fact_patterns:
            if pattern in query_lower:
                fact_keywords.add(pattern)
        
        return fact_keywords
    
    def _analyze_missing_aspects(
        self,
        results: List[Dict],
        legal_keywords: set,
        fact_keywords: set,
        issue_type: Optional[str]
    ) -> List[str]:
        """누락된 측면 분석"""
        missing = []
        
        if not results:
            missing.append("no_results")
            return missing
        
        # 결과 텍스트 수집
        all_text = ""
        for result in results[:5]:
            title = (result.get("title") or result.get("사건명") or "").lower()
            summary = (result.get("summary") or result.get("판시사항") or "").lower()
            all_text += f"{title} {summary} "
        
        # 법리축 키워드 누락 체크
        legal_found = sum(1 for kw in legal_keywords if kw in all_text)
        if legal_found == 0 and legal_keywords:
            missing.append("legal_axis_missing")
        elif legal_found < len(legal_keywords) * 0.5:
            missing.append("legal_axis_partial")
        
        # 사실축 키워드 누락 체크
        fact_found = sum(1 for kw in fact_keywords if kw in all_text)
        if fact_found == 0 and fact_keywords:
            missing.append("fact_axis_missing")
        elif fact_found < len(fact_keywords) * 0.5:
            missing.append("fact_axis_partial")
        
        # issue_type 누락 체크
        if issue_type and issue_type.lower() not in all_text:
            missing.append("issue_type_missing")
        
        return missing
    
    def _determine_next_plan(
        self,
        relevance_score: float,
        missing_aspects: List[str],
        legal_keywords: set,
        fact_keywords: set
    ) -> Dict:
        """다음 행동 계획 결정"""
        if relevance_score >= self.good_relevance_threshold:
            return {
                "action": "accept",
                "strategy": None,
                "reason": "relevance_score_high"
            }
        
        if "no_results" in missing_aspects:
            return {
                "action": "expand_query",
                "strategy": "synonym_expansion",
                "reason": "no_results"
            }
        
        if "legal_axis_missing" in missing_aspects:
            return {
                "action": "strengthen_query",
                "strategy": "add_legal_keywords",
                "keywords": list(legal_keywords),
                "reason": "legal_axis_missing"
            }
        
        if "fact_axis_missing" in missing_aspects:
            return {
                "action": "adjust_query",
                "strategy": "replace_fact_keywords",
                "reason": "fact_axis_missing"
            }
        
        if "legal_axis_partial" in missing_aspects or "fact_axis_partial" in missing_aspects:
            return {
                "action": "refine_query",
                "strategy": "combine_axes",
                "reason": "partial_match"
            }
        
        # 기본: 동의어 확장
        return {
            "action": "expand_query",
            "strategy": "synonym_expansion",
            "reason": "low_relevance"
        }


# 전역 인스턴스
_query_judge = None


def get_query_judge() -> QueryJudge:
    """QueryJudge 싱글톤 인스턴스 반환"""
    global _query_judge
    if _query_judge is None:
        _query_judge = QueryJudge()
    return _query_judge

