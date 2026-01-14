"""
Evidence Builder - 근거 조각 추출 및 태깅
검색 결과에서 인용 가능한 근거를 추출하고 쟁점과 연결
"""
from typing import List, Dict, Optional
import re


class Evidence:
    """근거 조각"""
    def __init__(
        self,
        text: str,
        source: str,
        source_id: str,
        source_url: Optional[str] = None,
        issue_tags: Optional[List[str]] = None,
        relevance_score: float = 0.0,
        auto_tags: Optional[List[str]] = None
    ):
        self.text = text
        self.source = source  # "precedent", "law", "interpretation" 등
        self.source_id = source_id
        self.source_url = source_url
        self.issue_tags = issue_tags or []
        self.relevance_score = relevance_score
        self.auto_tags = auto_tags or []  # 자동 생성된 태그
    
    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            "text": self.text,
            "source": self.source,
            "source_id": self.source_id,
            "source_url": self.source_url,
            "issue_tags": self.issue_tags,
            "relevance_score": self.relevance_score,
            "auto_tags": self.auto_tags
        }


class EvidenceBuilder:
    """근거 추출기"""
    
    def __init__(self):
        # 최대 근거 길이 (문자)
        self.max_evidence_length = 300
        
        # 자동 태그 패턴
        self.tag_patterns = {
            "지휘감독": ["지휘", "감독", "지시", "명령", "통제"],
            "전속성": ["전속", "배타적", "독점", "겸직 금지"],
            "보수 성격": ["임금", "급여", "보수", "수수료", "성과급", "고정급"],
            "근로자성 판단": ["근로자성", "사용종속관계", "종속", "근로관계"],
            "해고": ["해고", "부당해고", "정당한 사유", "권리남용"],
            "임금": ["임금", "체불", "미지급", "지급"],
            "계약": ["계약", "위약", "계약위반", "계약해지"],
            "손해배상": ["손해배상", "불법행위", "과실", "배상"]
        }
    
    def extract_evidence(
        self,
        result: Dict,
        issue_type: Optional[str] = None,
        query: Optional[str] = None
    ) -> List[Evidence]:
        """
        결과에서 근거 조각 추출
        
        Args:
            result: 검색 결과 딕셔너리
            issue_type: 쟁점 유형
            query: 검색 쿼리
            
        Returns:
            Evidence 리스트
        """
        evidences = []
        
        # 판례인 경우
        if "판시사항" in result or "판결요지" in result or "사건명" in result:
            evidences.extend(self._extract_precedent_evidence(result, issue_type, query))
        
        # 법령인 경우
        elif "법령명" in result or "법령ID" in result:
            evidences.extend(self._extract_law_evidence(result, issue_type, query))
        
        # 일반 결과
        else:
            evidences.extend(self._extract_general_evidence(result, issue_type, query))
        
        return evidences
    
    def _extract_precedent_evidence(
        self,
        result: Dict,
        issue_type: Optional[str],
        query: Optional[str]
    ) -> List[Evidence]:
        """판례에서 근거 추출"""
        evidences = []
        
        # 판시사항 (가장 중요)
        판시사항 = result.get("판시사항") or result.get("판시사항")
        if 판시사항:
            evidence_text = self._truncate_text(판시사항)
            if evidence_text:
                auto_tags = self._generate_auto_tags(evidence_text, issue_type)
                evidences.append(Evidence(
                    text=evidence_text,
                    source="precedent",
                    source_id=str(result.get("판례정보일련번호") or result.get("id") or ""),
                    source_url=result.get("url"),
                    issue_tags=[issue_type] if issue_type else [],
                    relevance_score=self._calculate_relevance(evidence_text, query, issue_type),
                    auto_tags=auto_tags
                ))
        
        # 판결요지
        판결요지 = result.get("판결요지") or result.get("요지")
        if 판결요지:
            evidence_text = self._truncate_text(판결요지)
            if evidence_text:
                auto_tags = self._generate_auto_tags(evidence_text, issue_type)
                evidences.append(Evidence(
                    text=evidence_text,
                    source="precedent",
                    source_id=str(result.get("판례정보일련번호") or result.get("id") or ""),
                    source_url=result.get("url"),
                    issue_tags=[issue_type] if issue_type else [],
                    relevance_score=self._calculate_relevance(evidence_text, query, issue_type),
                    auto_tags=auto_tags
                ))
        
        # 사건명 (간단한 근거)
        사건명 = result.get("사건명") or result.get("case_name") or result.get("title")
        if 사건명 and len(사건명) < 100:
            auto_tags = self._generate_auto_tags(사건명, issue_type)
            evidences.append(Evidence(
                text=사건명,
                source="precedent",
                source_id=str(result.get("판례정보일련번호") or result.get("id") or ""),
                source_url=result.get("url"),
                issue_tags=[issue_type] if issue_type else [],
                relevance_score=0.5,  # 사건명은 낮은 점수
                auto_tags=auto_tags
            ))
        
        return evidences
    
    def _extract_law_evidence(
        self,
        result: Dict,
        issue_type: Optional[str],
        query: Optional[str]
    ) -> List[Evidence]:
        """법령에서 근거 추출"""
        evidences = []
        
        # 법령명
        법령명 = result.get("법령명한글") or result.get("법령명") or result.get("title")
        if 법령명:
            auto_tags = self._generate_auto_tags(법령명, issue_type)
            evidences.append(Evidence(
                text=법령명,
                source="law",
                source_id=str(result.get("법령ID") or result.get("id") or ""),
                source_url=result.get("url"),
                issue_tags=[issue_type] if issue_type else [],
                relevance_score=0.6,
                auto_tags=auto_tags
            ))
        
        # 조문 내용 (있는 경우)
        조문 = result.get("조문내용") or result.get("article_content")
        if 조문:
            evidence_text = self._truncate_text(조문)
            if evidence_text:
                auto_tags = self._generate_auto_tags(evidence_text, issue_type)
                evidences.append(Evidence(
                    text=evidence_text,
                    source="law",
                    source_id=str(result.get("법령ID") or result.get("id") or ""),
                    source_url=result.get("url"),
                    issue_tags=[issue_type] if issue_type else [],
                    relevance_score=self._calculate_relevance(evidence_text, query, issue_type),
                    auto_tags=auto_tags
                ))
        
        return evidences
    
    def _extract_general_evidence(
        self,
        result: Dict,
        issue_type: Optional[str],
        query: Optional[str]
    ) -> List[Evidence]:
        """일반 결과에서 근거 추출"""
        evidences = []
        
        # 요약/요지
        summary = result.get("summary") or result.get("요지") or result.get("내용")
        if summary:
            evidence_text = self._truncate_text(summary)
            if evidence_text:
                auto_tags = self._generate_auto_tags(evidence_text, issue_type)
                evidences.append(Evidence(
                    text=evidence_text,
                    source=result.get("source", "unknown"),
                    source_id=str(result.get("id") or ""),
                    source_url=result.get("url"),
                    issue_tags=[issue_type] if issue_type else [],
                    relevance_score=self._calculate_relevance(evidence_text, query, issue_type),
                    auto_tags=auto_tags
                ))
        
        # 제목
        title = result.get("title") or result.get("제목")
        if title and len(title) < 100:
            auto_tags = self._generate_auto_tags(title, issue_type)
            evidences.append(Evidence(
                text=title,
                source=result.get("source", "unknown"),
                source_id=str(result.get("id") or ""),
                source_url=result.get("url"),
                issue_tags=[issue_type] if issue_type else [],
                relevance_score=0.5,
                auto_tags=auto_tags
            ))
        
        return evidences
    
    def _truncate_text(self, text: str) -> str:
        """텍스트를 최대 길이로 자르기"""
        if not text:
            return ""
        
        text = text.strip()
        if len(text) <= self.max_evidence_length:
            return text
        
        # 문장 단위로 자르기
        sentences = re.split(r'[.!?。！？]\s*', text)
        truncated = ""
        for sentence in sentences:
            if len(truncated + sentence) > self.max_evidence_length:
                break
            truncated += sentence + ". "
        
        if not truncated:
            # 문장 단위로 자를 수 없으면 단순 자르기
            truncated = text[:self.max_evidence_length] + "..."
        
        return truncated.strip()
    
    def _calculate_relevance(
        self,
        text: str,
        query: Optional[str],
        issue_type: Optional[str]
    ) -> float:
        """
        텍스트의 관련성 점수 계산 (0.0 ~ 1.0)
        
        간단한 버전: 키워드 매칭
        """
        if not text or not query:
            return 0.5
        
        text_lower = text.lower()
        query_lower = query.lower()
        query_keywords = set(query_lower.split())
        
        # 키워드 매칭
        matched = sum(1 for kw in query_keywords if kw in text_lower)
        if query_keywords:
            score = matched / len(query_keywords)
        else:
            score = 0.5
        
        # issue_type 매칭 보너스
        if issue_type and issue_type.lower() in text_lower:
            score = min(score + 0.2, 1.0)
        
        return score
    
    def _generate_auto_tags(self, text: str, issue_type: Optional[str]) -> List[str]:
        """
        텍스트에서 자동으로 태그 생성
        
        Args:
            text: 근거 텍스트
            issue_type: 쟁점 유형
            
        Returns:
            자동 생성된 태그 리스트
        """
        tags = []
        text_lower = text.lower()
        
        # 태그 패턴 매칭
        for tag_name, patterns in self.tag_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    tags.append(tag_name)
                    break  # 한 태그당 한 번만 추가
        
        # issue_type 기반 태그 추가
        if issue_type:
            tags.append(issue_type)
        
        return list(dict.fromkeys(tags))  # 중복 제거
    
    def build_evidence_summary(
        self,
        results: List[Dict],
        issue_type: Optional[str] = None,
        query: Optional[str] = None,
        max_evidences: int = 5
    ) -> Dict:
        """
        여러 결과에서 근거를 추출하여 요약
        
        Args:
            results: 검색 결과 리스트
            issue_type: 쟁점 유형
            query: 검색 쿼리
            max_evidences: 최대 근거 수
            
        Returns:
            근거 요약 딕셔너리
        """
        all_evidences = []
        
        for result in results:
            evidences = self.extract_evidence(result, issue_type, query)
            all_evidences.extend(evidences)
        
        # 관련성 점수로 정렬
        all_evidences.sort(key=lambda e: e.relevance_score, reverse=True)
        
        # 상위 근거만 선택
        top_evidences = all_evidences[:max_evidences]
        
        return {
            "total_evidences": len(all_evidences),
            "top_evidences": [e.to_dict() for e in top_evidences],
            "issue_type": issue_type,
            "query": query
        }


# 전역 인스턴스
_evidence_builder = None


def get_evidence_builder() -> EvidenceBuilder:
    """EvidenceBuilder 싱글톤 인스턴스 반환"""
    global _evidence_builder
    if _evidence_builder is None:
        _evidence_builder = EvidenceBuilder()
    return _evidence_builder

