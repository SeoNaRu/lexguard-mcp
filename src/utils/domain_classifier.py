"""
Domain Classifier - 법률 이슈 분류기
사용자 질문/상황을 법률 도메인으로 분류

단일 소스 원칙:
  LEGAL_DOMAINS         - 키워드/동의어 기반 분류 (DomainClassifier 내부 사용)
  SITUATION_DOMAIN_CONFIG - 법령명·기관·키워드가 포함된 상세 설정
                          (SituationGuidanceService 등에서 import해서 사용)
"""
from typing import Dict, List, Tuple


# 상황 분석용 상세 도메인 설정 (법령명 + 기관 + 키워드)
# SituationGuidanceService.LEGAL_DOMAIN_KEYWORDS의 단일 소스
# 단일 소스 원칙: 도메인별 법령·기관·키워드는 이 dict 한 곳만 편집하세요.
# APIRouter.DOMAIN_LAWS / DOMAIN_AGENCIES 도 이 값을 참조합니다.
SITUATION_DOMAIN_CONFIG: Dict[str, Dict] = {
    "개인정보": {
        "laws": ["개인정보보호법", "정보통신망법", "신용정보법"],
        "agencies": ["개인정보보호위원회", "과학기술정보통신부", "금융위원회"],
        "keywords": ["개인정보", "정보보호", "개인정보유출", "개인정보처리"],
    },
    "노동": {
        "laws": [
            "근로기준법", "고용보험법", "산업안전보건법", "최저임금법",
            "근로자퇴직급여 보장법", "파견근로자보호 등에 관한 법률",
        ],
        "agencies": ["고용노동부", "노동위원회", "고용보험심사위원회"],
        "keywords": [
            "근로", "임금", "해고", "퇴직금", "근로시간", "휴가",
            "근로자성", "사용종속", "지휘감독", "위장도급", "용역", "도급",
            "출퇴근", "고정급", "전속",
        ],
    },
    "세금": {
        "laws": ["소득세법", "부가가치세법", "법인세법", "종합소득세법", "국세기본법", "국세징수법"],
        "agencies": ["국세청", "조세심판원", "기획재정부"],
        "keywords": ["세금", "소득세", "부가가치세", "세무조사", "세액공제"],
    },
    "부동산": {
        "laws": ["부동산거래법", "주택법", "건축법", "국토계획법", "부동산거래신고법"],
        "agencies": ["국토교통부", "중앙토지수용위원회"],
        "keywords": ["부동산", "임대차", "전세", "매매", "건축", "토지"],
    },
    "소비자": {
        "laws": ["소비자기본법", "약관법", "전자상거래법", "할부거래법"],
        "agencies": ["공정거래위원회", "국가인권위원회"],
        "keywords": [
            "소비자", "약관", "계약", "환불", "하자",
            "면책", "책임", "손해", "변경", "관할", "준거법", "청약철회",
        ],
    },
    "환경": {
        "laws": ["환경정책기본법", "환경보전법", "대기환경보전법", "수질환경보전법"],
        "agencies": ["환경부", "기후에너지환경부", "중앙환경분쟁조정위원회"],
        "keywords": ["환경", "오염", "폐기물", "대기", "수질"],
    },
    "금융": {
        "laws": ["금융실명거래법", "금융소비자보호법", "은행법", "자본시장법"],
        "agencies": ["금융위원회", "금융감독원"],
        "keywords": ["금융", "대출", "이자", "신용카드", "보험"],
    },
    "건강": {
        "laws": ["의료법", "약사법", "식품의약품법", "국민건강보험법"],
        "agencies": ["보건복지부", "식품의약품안전처", "질병관리청", "건강보험심사평가원"],
        "keywords": ["의료", "건강", "병원", "의료사고", "건강보험"],
    },
    "교육": {
        "laws": ["교육기본법", "초중등교육법", "고등교육법", "사립학교법"],
        "agencies": ["교육부"],
        "keywords": ["교육", "학교", "학생", "교사", "입시"],
    },
    "교통": {
        "laws": ["도로교통법", "자동차관리법", "항공법", "선박법"],
        "agencies": ["국토교통부", "경찰청", "해양경찰청", "해양안전심판원"],
        "keywords": ["교통", "사고", "면허", "과속", "음주운전"],
    },
}


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
    },
    "부동산": {
        "keywords": [
            "부동산", "임대차", "전세", "월세", "보증금", "명도", "주택",
            "토지", "건축", "매매", "임차인", "임대인", "부동산거래신고",
            "임대차보호법", "주택임대차보호법"
        ],
        "synonyms": ["임대", "전월세", "부동산 계약", "임차권"]
    },
    "소비자": {
        "keywords": [
            "소비자", "약관", "환불", "청약철회", "하자", "전자상거래",
            "소비자기본법", "불공정약관", "표시광고", "할부거래", "대금청구"
        ],
        "synonyms": ["소비자 분쟁", "불공정 거래", "계약 해지"]
    },
    "금융": {
        "keywords": [
            "금융", "대출", "이자", "신용카드", "보험", "증권", "펀드",
            "금융소비자", "금융실명거래법", "자본시장법", "대출금리"
        ],
        "synonyms": ["금융상품", "투자", "예금", "적금"]
    },
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

