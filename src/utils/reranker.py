"""
Reranker - 검색 결과 재랭킹
API 기본 정렬을 쟁점 적합도 기준으로 재정렬
"""
from typing import List, Dict, Optional
import re
import math
from ..utils.query_planner import LEGAL_CORE_KEYWORDS


class Reranker:
    """검색 결과 재랭킹"""
    
    def __init__(self):
        # 법리 키워드 가중치
        self.legal_keyword_weight = 2.0
        self.general_keyword_weight = 1.0
    
    def rerank(
        self,
        results: List[Dict],
        query: str,
        issue_type: Optional[str] = None,
        must_include: Optional[List[str]] = None,
        method: str = "keyword_matching"
    ) -> List[Dict]:
        """
        검색 결과 재랭킹
        
        Args:
            results: 원본 결과 리스트
            query: 검색 쿼리
            issue_type: 쟁점 유형
            must_include: 필수 포함 키워드
            method: 재랭킹 방법 ("keyword_matching", "bm25", "hybrid")
            
        Returns:
            재랭킹된 결과 리스트
        """
        if not results:
            return results
        
        if method == "keyword_matching":
            return self._rerank_by_keyword_matching(results, query, issue_type, must_include)
        elif method == "bm25":
            return self._rerank_by_bm25(results, query, issue_type, must_include)
        elif method == "hybrid":
            # 하이브리드: 키워드 매칭 + BM25
            keyword_results = self._rerank_by_keyword_matching(results, query, issue_type, must_include)
            bm25_results = self._rerank_by_bm25(results, query, issue_type, must_include)
            return self._merge_rankings(keyword_results, bm25_results)
        else:
            return results
    
    def _rerank_by_keyword_matching(
        self,
        results: List[Dict],
        query: str,
        issue_type: Optional[str],
        must_include: Optional[List[str]]
    ) -> List[Dict]:
        """
        키워드 매칭 기반 재랭킹
        
        간단한 버전: 제목/요지에 키워드 포함 여부로 점수 계산
        """
        query_lower = query.lower()
        query_keywords = set(query_lower.split())
        
        # must_include 키워드 추가
        if must_include:
            query_keywords.update([k.lower() for k in must_include])
        
        # issue_type 키워드 추가
        if issue_type:
            query_keywords.update(issue_type.lower().split())
        
        # 점수 계산
        scored_results = []
        for result in results:
            score = self._calculate_relevance_score(
                result,
                query_keywords,
                query_lower
            )
            scored_results.append({
                **result,
                "_rerank_score": score
            })
        
        # 점수 높은 순으로 정렬
        scored_results.sort(key=lambda x: x.get("_rerank_score", 0), reverse=True)
        
        # _rerank_score 제거 (내부 필드)
        for result in scored_results:
            result.pop("_rerank_score", None)
        
        return scored_results
    
    def _calculate_relevance_score(
        self,
        result: Dict,
        query_keywords: set,
        query_lower: str
    ) -> float:
        """
        결과의 관련성 점수 계산 (0.0 ~ 1.0)
        
        Args:
            result: 결과 딕셔너리
            query_keywords: 쿼리 키워드 집합
            query_lower: 소문자 쿼리
            
        Returns:
            관련성 점수
        """
        score = 0.0
        
        # 제목 추출
        title = (
            result.get("title") or
            result.get("사건명") or
            result.get("case_name") or
            result.get("제목") or
            ""
        ).lower()
        
        # 요지/요약 추출
        summary = (
            result.get("summary") or
            result.get("판시사항") or
            result.get("판결요지") or
            result.get("요지") or
            ""
        ).lower()
        
        # 전체 텍스트
        text = f"{title} {summary}"
        
        # 키워드 매칭 점수
        matched_keywords = 0
        legal_keywords_matched = 0
        
        for keyword in query_keywords:
            if keyword in text:
                matched_keywords += 1
                # 법리 키워드인지 확인
                if any(legal_term in keyword for legal_term in LEGAL_CORE_KEYWORDS):
                    legal_keywords_matched += 1
        
        # 기본 점수 (매칭된 키워드 비율)
        if query_keywords:
            keyword_score = matched_keywords / len(query_keywords)
            score += keyword_score * self.general_keyword_weight
        
        # 법리 키워드 보너스
        if legal_keywords_matched > 0:
            score += legal_keywords_matched * (self.legal_keyword_weight - self.general_keyword_weight)
        
        # 제목 매칭 보너스 (제목에 키워드가 있으면 더 높은 점수)
        title_matches = sum(1 for kw in query_keywords if kw in title)
        if title_matches > 0:
            score += title_matches * 0.3
        
        # 정규화 (0.0 ~ 1.0)
        max_possible_score = (
            len(query_keywords) * self.general_keyword_weight +
            len(query_keywords) * (self.legal_keyword_weight - self.general_keyword_weight) +
            len(query_keywords) * 0.3
        )
        
        if max_possible_score > 0:
            score = min(score / max_possible_score, 1.0)
        
        return score
    
    def _rerank_by_bm25(
        self,
        results: List[Dict],
        query: str,
        issue_type: Optional[str],
        must_include: Optional[List[str]]
    ) -> List[Dict]:
        """
        BM25 알고리즘 기반 재랭킹
        
        BM25는 TF-IDF의 개선 버전으로, 텍스트 검색에서 널리 사용됨
        """
        if not results:
            return results
        
        # 쿼리 키워드 추출
        query_lower = query.lower()
        query_keywords = set(query_lower.split())
        
        if must_include:
            query_keywords.update([k.lower() for k in must_include])
        
        if issue_type:
            query_keywords.update(issue_type.lower().split())
        
        # 문서 컬렉션 구축 (모든 결과의 텍스트)
        documents = []
        for result in results:
            title = (
                result.get("title") or
                result.get("사건명") or
                result.get("case_name") or
                ""
            )
            summary = (
                result.get("summary") or
                result.get("판시사항") or
                result.get("판결요지") or
                result.get("요지") or
                ""
            )
            text = f"{title} {summary}".lower()
            documents.append({
                "result": result,
                "text": text,
                "tokens": self._tokenize(text)
            })
        
        # BM25 파라미터
        k1 = 1.5  # 용어 빈도 정규화 파라미터
        b = 0.75  # 길이 정규화 파라미터
        avg_doc_length = sum(len(doc["tokens"]) for doc in documents) / len(documents) if documents else 1
        
        # IDF 계산 (간단한 버전)
        idf_scores = {}
        for keyword in query_keywords:
            df = sum(1 for doc in documents if keyword in doc["text"])
            if df > 0:
                idf_scores[keyword] = math.log((len(documents) - df + 0.5) / (df + 0.5) + 1.0)
            else:
                idf_scores[keyword] = 0.0
        
        # 각 문서의 BM25 점수 계산
        scored_docs = []
        for doc in documents:
            score = 0.0
            doc_length = len(doc["tokens"])
            
            for keyword in query_keywords:
                # TF (Term Frequency)
                tf = doc["tokens"].count(keyword)
                
                # BM25 점수 계산
                if tf > 0:
                    idf = idf_scores.get(keyword, 0.0)
                    numerator = idf * tf * (k1 + 1)
                    denominator = tf + k1 * (1 - b + b * (doc_length / avg_doc_length))
                    score += numerator / denominator
            
            # 법리 키워드 보너스
            for keyword in query_keywords:
                if any(legal_term in keyword for legal_term in LEGAL_CORE_KEYWORDS):
                    if keyword in doc["text"]:
                        score += 0.5
            
            scored_docs.append({
                **doc["result"],
                "_bm25_score": score
            })
        
        # 점수 높은 순으로 정렬
        scored_docs.sort(key=lambda x: x.get("_bm25_score", 0), reverse=True)
        
        # 내부 점수 필드 제거
        for doc in scored_docs:
            doc.pop("_bm25_score", None)
        
        return scored_docs
    
    def _tokenize(self, text: str) -> List[str]:
        """간단한 토크나이징 (공백 기준)"""
        # 한글/영어/숫자만 추출
        tokens = re.findall(r'[가-힣a-zA-Z0-9]+', text.lower())
        return tokens
    
    def _merge_rankings(
        self,
        results1: List[Dict],
        results2: List[Dict]
    ) -> List[Dict]:
        """
        두 랭킹 결과를 병합 (Borda Count 방식)
        """
        # 결과 ID 매핑
        id_to_rank1 = {}
        id_to_rank2 = {}
        
        for i, result in enumerate(results1):
            result_id = result.get("id") or result.get("판례정보일련번호") or str(i)
            id_to_rank1[result_id] = len(results1) - i  # 높은 순위일수록 높은 점수
        
        for i, result in enumerate(results2):
            result_id = result.get("id") or result.get("판례정보일련번호") or str(i)
            id_to_rank2[result_id] = len(results2) - i
        
        # 모든 결과 ID 수집
        all_ids = set(id_to_rank1.keys()) | set(id_to_rank2.keys())
        
        # 점수 합산
        scored_results = {}
        for result_id in all_ids:
            score = id_to_rank1.get(result_id, 0) + id_to_rank2.get(result_id, 0)
            scored_results[result_id] = score
        
        # 결과 매핑
        all_results = {r.get("id") or r.get("판례정보일련번호") or str(i): r 
                       for i, r in enumerate(results1 + results2)}
        
        # 점수 높은 순으로 정렬
        sorted_ids = sorted(scored_results.items(), key=lambda x: x[1], reverse=True)
        
        merged = []
        seen = set()
        for result_id, score in sorted_ids:
            if result_id in all_results and result_id not in seen:
                merged.append(all_results[result_id])
                seen.add(result_id)
        
        return merged


# 전역 인스턴스
_reranker = None


def get_reranker() -> Reranker:
    """Reranker 싱글톤 인스턴스 반환"""
    global _reranker
    if _reranker is None:
        _reranker = Reranker()
    return _reranker

