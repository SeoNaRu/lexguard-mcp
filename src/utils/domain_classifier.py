"""
Domain Classifier - 법률 이슈 분류기
사용자 질문/상황을 법률 도메인으로 분류
"""
from typing import List, Dict, Tuple, Optional
import re


# 법률 도메인 정의
LEGAL_DOMAINS = {
    "근로자성": {
        "keywords": ["프리랜서", "근로자성", "사용종속관계", "지휘감독", "위장도급", "특수형태근로종사자",
                    "도급계약", "위탁계약", "출퇴근", "전속성", "고정급", "근로기준법"],
        "synonyms": ["근로관계", "종속관계", "근로자 판단", "사실상 근로관계"]
    },
    "부당해고": {
        "keywords": ["해고", "부당해고", "정리해고", "해직", "징계해고", "권리남용", "정당한 사유"],
        "synonyms": ["고용종료", "고용계약 해지", "근로계약 해지"]
    },
    "임금체불": {
        "keywords": ["임금", "체불", "미지급", "급여", "봉급", "월급", "퇴직금", "상여금", "수당"],
        "synonyms": ["임금 지급", "임금 청구", "임금 체불"]
    },
    "재산분할": {
        "keywords": ["재산분할", "이혼", "재산", "부부재산", "분할청구", "재산분할소송"],
        "synonyms": ["재산 분할", "이혼 재산", "부부 재산"]
    },
    "양육권": {
        "keywords": ["양육권", "양육", "친권", "자녀", "양육비", "면접교섭권"],
        "synonyms": ["자녀 양육", "양육 책임", "양육 결정"]
    },
    "손해배상": {
        "keywords": ["손해배상", "배상", "불법행위", "과실", "과실상계", "손해"],
        "synonyms": ["배상 청구", "손해 보상", "불법 행위"]
    },
    "계약": {
        "keywords": ["계약", "계약서", "위약", "위약금", "계약해지", "계약위반", "계약불이행"],
        "synonyms": ["계약 해지", "계약 위반", "계약 파기"]
    },
    "개인정보": {
        "keywords": ["개인정보", "유출", "침해", "개인정보보호법", "정보보호", "개인정보 처리"],
        "synonyms": ["개인정보 보호", "정보 유출", "프라이버시"]
    },
    "세금": {
        "keywords": ["세금", "소득세", "부가세", "과세", "세무", "납세", "세법"],
        "synonyms": ["세금 부과", "세금 납부", "세무 문제"]
    },
    "상속": {
        "keywords": ["상속", "상속분", "상속재산", "유산", "상속인", "상속세"],
        "synonyms": ["상속 재산", "유산 상속", "상속 분할"]
    }
}


class DomainClassifier:
    """법률 도메인 분류기"""
    
    def __init__(self):
        self.domains = LEGAL_DOMAINS
    
    def classify(
        self,
        query: str,
        max_domains: int = 3
    ) -> List[Tuple[str, float]]:
        """
        질문을 법률 도메인으로 분류
        
        Args:
            query: 사용자 질문
            max_domains: 최대 반환 도메인 수
            
        Returns:
            (도메인명, 점수) 튜플 리스트 (점수 높은 순)
        """
        query_lower = query.lower()
        scores = {}
        
        for domain_name, domain_config in self.domains.items():
            score = 0.0
            
            # 키워드 매칭
            keywords = domain_config.get("keywords", [])
            for keyword in keywords:
                if keyword.lower() in query_lower:
                    score += 1.0
            
            # 동의어 매칭 (가중치 낮게)
            synonyms = domain_config.get("synonyms", [])
            for synonym in synonyms:
                if synonym.lower() in query_lower:
                    score += 0.5
            
            if score > 0:
                scores[domain_name] = score
        
        # 점수 정규화 (0.0 ~ 1.0)
        if scores:
            max_score = max(scores.values())
            normalized_scores = {
                domain: score / max_score
                for domain, score in scores.items()
            }
        else:
            normalized_scores = {}
        
        # 점수 높은 순으로 정렬
        sorted_domains = sorted(
            normalized_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        return sorted_domains[:max_domains]
    
    def get_domain_keywords(
        self,
        domain: str
    ) -> List[str]:
        """
        특정 도메인의 키워드 리스트 반환
        
        Args:
            domain: 도메인명
            
        Returns:
            키워드 리스트
        """
        domain_config = self.domains.get(domain)
        if not domain_config:
            return []
        
        return domain_config.get("keywords", [])
    
    def get_must_include_for_domain(
        self,
        domain: str
    ) -> List[str]:
        """
        특정 도메인에 대한 must_include 키워드 추천
        
        Args:
            domain: 도메인명
            
        Returns:
            must_include 키워드 리스트
        """
        domain_config = self.domains.get(domain)
        if not domain_config:
            return []
        
        keywords = domain_config.get("keywords", [])
        
        # 법리 키워드 우선 (법령명, 핵심 개념)
        legal_keywords = [
            kw for kw in keywords
            if any(legal_term in kw for legal_term in ["법", "관계", "권", "의무", "책임"])
        ]
        
        # 법리 키워드가 있으면 그것을 우선, 없으면 일반 키워드
        return legal_keywords[:2] if legal_keywords else keywords[:2]
    
    def classify_with_confidence(
        self,
        query: str,
        min_confidence: float = 0.3
    ) -> List[str]:
        """
        신뢰도가 높은 도메인만 반환
        
        Args:
            query: 사용자 질문
            min_confidence: 최소 신뢰도 (0.0 ~ 1.0)
            
        Returns:
            도메인명 리스트
        """
        classified = self.classify(query)
        return [
            domain for domain, score in classified
            if score >= min_confidence
        ]


# 전역 인스턴스
_domain_classifier = None


def get_domain_classifier() -> DomainClassifier:
    """DomainClassifier 싱글톤 인스턴스 반환"""
    global _domain_classifier
    if _domain_classifier is None:
        _domain_classifier = DomainClassifier()
    return _domain_classifier

