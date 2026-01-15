"""
API Router - 완벽한 DRF API 라우팅 시스템
172개의 DRF API를 체계적으로 관리하고 질문/문서 타입에 따라 자동 선택
"""
from typing import List, Dict, Optional, Tuple
from enum import Enum


class APICategory(str, Enum):
    """API 카테고리"""
    LAW = "law"                          # 현행법령
    PRECEDENT = "precedent"              # 판례
    CONSTITUTIONAL = "constitutional"     # 헌재결정
    ADMINISTRATIVE_APPEAL = "admin_appeal"  # 행정심판
    LAW_INTERPRETATION = "interpretation"   # 법령해석
    COMMITTEE_DECISION = "committee"        # 위원회 결정
    SPECIAL_TRIBUNAL = "special_tribunal"   # 특별행정심판
    LOCAL_ORDINANCE = "ordinance"           # 자치법규
    ADMINISTRATIVE_RULE = "admin_rule"      # 행정규칙
    LAW_COMPARISON = "comparison"           # 신구법/비교
    LAW_HISTORY = "history"                 # 법령 연혁


class DomainType(str, Enum):
    """법적 영역 타입"""
    LABOR = "labor"                      # 노동/근로
    PERSONAL_INFO = "personal_info"      # 개인정보
    TAX = "tax"                          # 세금/조세
    FINANCE = "finance"                  # 금융
    REAL_ESTATE = "real_estate"          # 부동산
    CONSUMER = "consumer"                # 소비자
    ENVIRONMENT = "environment"          # 환경
    HEALTH = "health"                    # 보건/의료
    EDUCATION = "education"              # 교육
    TRAFFIC = "traffic"                  # 교통
    GENERAL = "general"                  # 일반


class APIRouter:
    """
    완벽한 API 라우팅 시스템
    - 질문/문서 분석 → 적절한 API 선택
    - 다단계 검색 전략
    - 172개 DRF API 완전 활용
    """
    
    # 도메인별 주요 법령
    DOMAIN_LAWS = {
        DomainType.LABOR: [
            "근로기준법", "고용보험법", "산업안전보건법", "최저임금법", 
            "근로자퇴직급여 보장법", "파견근로자보호 등에 관한 법률"
        ],
        DomainType.PERSONAL_INFO: [
            "개인정보보호법", "정보통신망법", "신용정보법"
        ],
        DomainType.TAX: [
            "소득세법", "법인세법", "부가가치세법", "국세기본법", "국세징수법"
        ],
        DomainType.FINANCE: [
            "금융실명거래법", "금융소비자보호법", "은행법", "자본시장법"
        ],
        DomainType.REAL_ESTATE: [
            "주택법", "건축법", "국토계획법", "부동산거래신고법"
        ],
        DomainType.CONSUMER: [
            "소비자기본법", "약관법", "전자상거래법", "할부거래법"
        ],
        DomainType.ENVIRONMENT: [
            "환경정책기본법", "대기환경보전법", "수질환경보전법"
        ],
        DomainType.HEALTH: [
            "의료법", "약사법", "국민건강보험법", "식품의약품법"
        ],
        DomainType.EDUCATION: [
            "교육기본법", "초중등교육법", "고등교육법", "사립학교법"
        ],
        DomainType.TRAFFIC: [
            "도로교통법", "자동차관리법", "항공법", "선박법"
        ]
    }
    
    # 도메인별 주요 부처 (법령해석용)
    DOMAIN_AGENCIES = {
        DomainType.LABOR: ["고용노동부"],
        DomainType.PERSONAL_INFO: ["과학기술정보통신부", "개인정보보호위원회"],
        DomainType.TAX: ["기획재정부", "국세청", "조세심판원"],
        DomainType.FINANCE: ["금융위원회", "금융감독원"],
        DomainType.REAL_ESTATE: ["국토교통부", "중앙토지수용위원회"],
        DomainType.CONSUMER: ["공정거래위원회"],
        DomainType.ENVIRONMENT: ["기후에너지환경부", "중앙환경분쟁조정위원회"],
        DomainType.HEALTH: ["보건복지부", "식품의약품안전처", "질병관리청"],
        DomainType.EDUCATION: ["교육부"],
        DomainType.TRAFFIC: ["국토교통부", "경찰청", "해양경찰청"]
    }
    
    # 도메인별 위원회
    DOMAIN_COMMITTEES = {
        DomainType.LABOR: ["노동위원회", "고용보험심사위원회", "산업재해보상보험재심사위원회"],
        DomainType.PERSONAL_INFO: ["개인정보보호위원회"],
        DomainType.TAX: ["조세심판원"],
        DomainType.FINANCE: ["금융위원회", "증권선물위원회"],
        DomainType.REAL_ESTATE: ["중앙토지수용위원회"],
        DomainType.CONSUMER: ["국민권익위원회", "공정거래위원회"],
        DomainType.ENVIRONMENT: ["중앙환경분쟁조정위원회"],
        DomainType.TRAFFIC: ["해양안전심판원"]
    }
    
    # 특별행정심판원
    SPECIAL_TRIBUNALS = [
        "조세심판원",
        "해양안전심판원",
        "인사혁신처_소청심사위원회",
        "국민권익위원회"
    ]
    
    def __init__(self):
        pass
    
    def detect_domain(self, query: str, document_text: Optional[str] = None) -> DomainType:
        """
        질문/문서에서 법적 영역 감지
        
        Args:
            query: 사용자 질문
            document_text: 문서 전문 (옵션)
            
        Returns:
            DomainType
        """
        text = (query + " " + (document_text or "")).lower()
        
        # 노동
        if any(kw in text for kw in ["근로", "노동", "해고", "퇴직금", "임금", "프리랜서", "용역", "근로자", "사용종속", "4대보험"]):
            return DomainType.LABOR
        
        # 개인정보
        if any(kw in text for kw in ["개인정보", "프라이버시", "정보유출", "개인정보처리", "신용정보"]):
            return DomainType.PERSONAL_INFO
        
        # 세금/조세
        if any(kw in text for kw in ["세금", "소득세", "부가가치세", "법인세", "종합소득세", "조세", "국세", "지방세"]):
            return DomainType.TAX
        
        # 금융
        if any(kw in text for kw in ["금융", "대출", "이자", "신용카드", "보험", "증권", "펀드"]):
            return DomainType.FINANCE
        
        # 부동산
        if any(kw in text for kw in ["부동산", "임대차", "전세", "매매", "건축", "토지", "주택", "보증금"]):
            return DomainType.REAL_ESTATE
        
        # 소비자
        if any(kw in text for kw in ["소비자", "약관", "환불", "청약철회", "하자", "계약"]):
            return DomainType.CONSUMER
        
        # 환경
        if any(kw in text for kw in ["환경", "오염", "폐기물", "대기", "수질"]):
            return DomainType.ENVIRONMENT
        
        # 보건/의료
        if any(kw in text for kw in ["의료", "병원", "의료사고", "건강보험", "약", "의사", "간호사"]):
            return DomainType.HEALTH
        
        # 교육
        if any(kw in text for kw in ["교육", "학교", "학생", "교사", "입시", "학원"]):
            return DomainType.EDUCATION
        
        # 교통
        if any(kw in text for kw in ["교통", "사고", "면허", "과속", "음주운전", "자동차"]):
            return DomainType.TRAFFIC
        
        return DomainType.GENERAL
    
    def plan_api_sequence(
        self, 
        query: str, 
        domain: DomainType,
        intent: str,
        document_text: Optional[str] = None
    ) -> List[Tuple[APICategory, Dict[str, any]]]:
        """
        도메인과 Intent에 따라 API 호출 순서 계획
        
        Args:
            query: 질문
            domain: 법적 영역
            intent: Intent (labor_worker_status, labor_termination 등)
            document_text: 문서 전문 (옵션)
            
        Returns:
            [(APICategory, params), ...] - 호출 순서대로
        """
        sequence = []
        
        # 1단계: 항상 관련 법령 먼저
        law_params = {
            "query": query,
            "target_laws": self.DOMAIN_LAWS.get(domain, []),
            "priority": "high"
        }
        sequence.append((APICategory.LAW, law_params))
        
        # 2단계: 판례 (실무 중요도 높음)
        if intent != "law_only":
            precedent_params = {
                "query": query,
                "domain": domain.value
            }
            sequence.append((APICategory.PRECEDENT, precedent_params))
        
        # 3단계: 법령해석 (부처별)
        agencies = self.DOMAIN_AGENCIES.get(domain, [])
        if agencies:
            for agency in agencies[:2]:  # 최대 2개 부처
                interp_params = {
                    "query": query,
                    "agency": agency
                }
                sequence.append((APICategory.LAW_INTERPRETATION, interp_params))
        
        # 4단계: 위원회 결정 (도메인별)
        committees = self.DOMAIN_COMMITTEES.get(domain, [])
        if committees:
            for committee in committees[:2]:  # 최대 2개 위원회
                committee_params = {
                    "query": query,
                    "committee": committee
                }
                sequence.append((APICategory.COMMITTEE_DECISION, committee_params))
        
        # 5단계: 행정심판 (해당되는 경우)
        if intent in ["administrative_dispute", "appeal"]:
            sequence.append((APICategory.ADMINISTRATIVE_APPEAL, {"query": query}))
        
        # 6단계: 특별행정심판 (세금/해양 등)
        if domain == DomainType.TAX:
            sequence.append((APICategory.SPECIAL_TRIBUNAL, {"query": query, "tribunal": "조세심판원"}))
        
        # 7단계: 헌재결정 (위헌 관련)
        if "위헌" in query or "헌법" in query:
            sequence.append((APICategory.CONSTITUTIONAL, {"query": query}))
        
        # 8단계: 자치법규 (지역 관련)
        if any(kw in query for kw in ["조례", "지방", "시", "도", "구"]):
            sequence.append((APICategory.LOCAL_ORDINANCE, {"query": query}))
        
        # 9단계: 행정규칙 (세부 집행 기준)
        if "기준" in query or "지침" in query or "예규" in query:
            sequence.append((APICategory.ADMINISTRATIVE_RULE, {"query": query}))
        
        # 10단계: 법령 비교/연혁 (시간 조건 있을 때)
        if any(kw in query for kw in ["개정", "변경", "예전", "이전", "비교", "달라진"]):
            sequence.append((APICategory.LAW_COMPARISON, {"query": query}))
            sequence.append((APICategory.LAW_HISTORY, {"query": query}))
        
        return sequence
    
    def get_api_priorities(self, domain: DomainType) -> Dict[APICategory, int]:
        """
        도메인별 API 우선순위 (1-10, 높을수록 중요)
        """
        # 기본 우선순위
        base_priorities = {
            APICategory.LAW: 10,
            APICategory.PRECEDENT: 9,
            APICategory.LAW_INTERPRETATION: 8,
            APICategory.COMMITTEE_DECISION: 7,
            APICategory.ADMINISTRATIVE_APPEAL: 6,
            APICategory.CONSTITUTIONAL: 5,
            APICategory.SPECIAL_TRIBUNAL: 4,
            APICategory.LOCAL_ORDINANCE: 3,
            APICategory.ADMINISTRATIVE_RULE: 2,
            APICategory.LAW_COMPARISON: 1,
            APICategory.LAW_HISTORY: 1
        }
        
        # 도메인별 조정
        if domain == DomainType.LABOR:
            # 노동: 위원회 결정 중요도 높임
            base_priorities[APICategory.COMMITTEE_DECISION] = 9
        elif domain == DomainType.TAX:
            # 세금: 특별행정심판(조세심판원) 중요도 높임
            base_priorities[APICategory.SPECIAL_TRIBUNAL] = 9
        elif domain == DomainType.PERSONAL_INFO:
            # 개인정보: 위원회 결정 중요도 높임
            base_priorities[APICategory.COMMITTEE_DECISION] = 10
        
        return base_priorities
    
    def suggest_related_apis(self, domain: DomainType, current_category: APICategory) -> List[APICategory]:
        """
        현재 API 카테고리 기반으로 관련 API 추천
        """
        related = []
        
        if current_category == APICategory.LAW:
            related = [
                APICategory.PRECEDENT,
                APICategory.LAW_INTERPRETATION,
                APICategory.LAW_COMPARISON
            ]
        elif current_category == APICategory.PRECEDENT:
            related = [
                APICategory.LAW,
                APICategory.COMMITTEE_DECISION,
                APICategory.LAW_INTERPRETATION
            ]
        elif current_category == APICategory.LAW_INTERPRETATION:
            related = [
                APICategory.LAW,
                APICategory.ADMINISTRATIVE_RULE,
                APICategory.COMMITTEE_DECISION
            ]
        
        return related

