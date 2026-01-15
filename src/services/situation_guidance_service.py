"""
Situation-Based Legal Guidance Service
사용자의 상황을 분석하여 관련 법령, 판례, 해석, 심판례를 종합적으로 찾아주는 서비스
"""
import re
import asyncio
from typing import Optional, Dict, List, Tuple
from ..repositories.law_repository import LawRepository
from ..repositories.law_detail import LawDetailRepository
from ..repositories.precedent_repository import PrecedentRepository
from ..repositories.law_interpretation_repository import LawInterpretationRepository
from ..repositories.administrative_appeal_repository import AdministrativeAppealRepository
from ..repositories.constitutional_decision_repository import ConstitutionalDecisionRepository
from ..repositories.committee_decision_repository import CommitteeDecisionRepository
from ..repositories.special_administrative_appeal_repository import SpecialAdministrativeAppealRepository
from ..repositories.local_ordinance_repository import LocalOrdinanceRepository
from ..repositories.administrative_rule_repository import AdministrativeRuleRepository


class SituationGuidanceService:
    """
    사용자의 법적 상황을 분석하여:
    1. 관련 법령 자동 검색
    2. 유사 판례 찾기
    3. 관련 기관 해석 확인
    4. 행정심판/위원회 결정 사례 찾기
    5. 단계별 가이드 제공
    """
    
    # 법적 영역별 키워드 매핑
    LEGAL_DOMAIN_KEYWORDS = {
        "개인정보": {
            "laws": ["개인정보보호법", "정보통신망법", "신용정보법"],
            "agencies": ["개인정보보호위원회", "과학기술정보통신부", "금융위원회"],
            "keywords": ["개인정보", "정보보호", "개인정보유출", "개인정보처리"]
        },
        "노동": {
            "laws": ["근로기준법", "고용보험법", "산업안전보건법", "최저임금법"],
            "agencies": ["고용노동부", "노동위원회", "고용보험심사위원회"],
            "keywords": [
                "근로", "임금", "해고", "퇴직금", "근로시간", "휴가",
                "근로자성", "사용종속", "지휘감독", "위장도급", "용역", "도급",
                "출퇴근", "고정급", "전속"
            ]
        },
        "세금": {
            "laws": ["소득세법", "부가가치세법", "법인세법", "종합소득세법"],
            "agencies": ["국세청", "조세심판원", "기획재정부"],
            "keywords": ["세금", "소득세", "부가가치세", "세무조사", "세액공제"]
        },
        "부동산": {
            "laws": ["부동산거래법", "주택법", "건축법", "국토계획법"],
            "agencies": ["국토교통부", "중앙토지수용위원회"],
            "keywords": ["부동산", "임대차", "전세", "매매", "건축", "토지"]
        },
        "소비자": {
            "laws": ["소비자기본법", "약관법", "전자상거래법"],
            "agencies": ["공정거래위원회", "국가인권위원회"],
            "keywords": [
                "소비자", "약관", "계약", "환불", "하자",
                "면책", "책임", "손해", "변경", "관할", "준거법", "청약철회"
            ]
        },
        "환경": {
            "laws": ["환경보전법", "대기환경보전법", "수질환경보전법"],
            "agencies": ["환경부", "중앙환경분쟁조정위원회"],
            "keywords": ["환경", "오염", "폐기물", "대기", "수질"]
        },
        "금융": {
            "laws": ["금융실명거래법", "금융소비자보호법", "은행법"],
            "agencies": ["금융위원회", "금융감독원"],
            "keywords": ["금융", "대출", "이자", "신용카드", "보험"]
        },
        "건강": {
            "laws": ["의료법", "식품의약품법", "국민건강보험법"],
            "agencies": ["보건복지부", "식품의약품안전처", "건강보험심사평가원"],
            "keywords": ["의료", "건강", "병원", "의료사고", "건강보험"]
        },
        "교육": {
            "laws": ["교육기본법", "초중등교육법", "고등교육법"],
            "agencies": ["교육부"],
            "keywords": ["교육", "학교", "학생", "교사", "입시"]
        },
        "교통": {
            "laws": ["도로교통법", "자동차관리법", "항공법"],
            "agencies": ["국토교통부", "해양안전심판원"],
            "keywords": ["교통", "사고", "면허", "과속", "음주운전"]
        }
    }
    
    def __init__(self):
        self.law_search_repo = LawRepository()
        self.law_detail_repo = LawDetailRepository()
        self.precedent_repo = PrecedentRepository()
        self.interpretation_repo = LawInterpretationRepository()
        self.appeal_repo = AdministrativeAppealRepository()
        self.constitutional_repo = ConstitutionalDecisionRepository()
        self.committee_repo = CommitteeDecisionRepository()
        self.special_appeal_repo = SpecialAdministrativeAppealRepository()
        self.ordinance_repo = LocalOrdinanceRepository()
        self.rule_repo = AdministrativeRuleRepository()
    
    def detect_legal_domain(self, situation: str) -> List[Tuple[str, float]]:
        """
        사용자 상황에서 법적 영역을 감지
        
        Returns:
            [(domain, confidence), ...] - 신뢰도 순으로 정렬
        """
        situation_lower = situation.lower()
        scores = {}
        
        for domain, config in self.LEGAL_DOMAIN_KEYWORDS.items():
            score = 0.0
            
            # 법령명 매칭
            for law in config["laws"]:
                if law in situation:
                    score += 3.0
            
            # 기관명 매칭
            for agency in config["agencies"]:
                if agency in situation:
                    score += 2.0
            
            # 키워드 매칭
            for keyword in config["keywords"]:
                if keyword in situation_lower:
                    score += 1.0
            
            if score > 0:
                scores[domain] = score
        
        # 신뢰도 순으로 정렬
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        if sorted_scores:
            max_score = sorted_scores[0][1]
            normalized = [(domain, min(score / max_score, 1.0)) for domain, score in sorted_scores]
            return normalized
        
        return []
    
    def extract_key_terms(self, situation: str) -> Dict:
        """
        상황에서 핵심 용어 추출
        """
        terms = {
            "laws": [],
            "agencies": [],
            "keywords": [],
            "dates": [],
            "amounts": []
        }
        
        # 법령명 추출
        law_pattern = r"([가-힣]+법)"
        laws = re.findall(law_pattern, situation)
        terms["laws"] = list(set(laws))
        
        # 기관명 추출
        agency_keywords = [
            "위원회", "부", "청", "처", "원", "심판원"
        ]
        for keyword in agency_keywords:
            pattern = f"([가-힣]+{keyword})"
            agencies = re.findall(pattern, situation)
            terms["agencies"].extend(agencies)
        terms["agencies"] = list(set(terms["agencies"]))
        
        # 날짜 추출
        date_pattern = r"(\d{4})[년\.]?\s*(\d{1,2})[월\.]?\s*(\d{1,2})[일]?"
        dates = re.findall(date_pattern, situation)
        terms["dates"] = dates
        
        # 금액 추출
        amount_pattern = r"(\d+)[만천억]?원"
        amounts = re.findall(amount_pattern, situation)
        terms["amounts"] = amounts
        
        return terms
    
    def normalize_query_for_search(self, situation: str, domains: List[str], key_terms: Dict) -> str:
        """
        긴 문장을 검색용 키워드로 정규화
        """
        # 도메인별 대표 키워드 (상황 기반 가중치 반영)
        domain_keywords = []
        situation_lower = situation.lower()
        for domain in domains[:2]:
            config = self.LEGAL_DOMAIN_KEYWORDS.get(domain, {})
            keywords = config.get("keywords", [])
            prioritized = []
            if domain == "노동":
                if any(k in situation for k in ["프리랜서", "용역", "도급"]):
                    prioritized.extend(["근로자성", "지휘감독", "사용종속", "위장도급"])
                if "해고" in situation:
                    prioritized.extend(["부당해고", "징계", "해고예고"])
                if "출퇴근" in situation or "근로시간" in situation:
                    prioritized.extend(["출퇴근", "근로시간", "고정급", "전속"])
            # 우선 키워드 + 기본 키워드 병합
            for k in prioritized:
                if k not in domain_keywords:
                    domain_keywords.append(k)
            for k in keywords:
                if k not in domain_keywords:
                    domain_keywords.append(k)
            # 도메인별 최대 6개만 사용
            domain_keywords = domain_keywords[:6]
        
        # 문장 내 핵심 키워드 추출
        text = situation
        # 조사/어미 제거
        for qw in ["인가", "인지", "인가요", "인지요", "알려줘", "찾아줘", "확인", "가능", "해줘"]:
            text = text.replace(qw, "")
        
        keywords = re.findall(r'[가-힣]{2,}', text)
        keywords = [k for k in keywords if k not in ["이", "그", "저", "및", "관련", "문제", "확인"]]
        keywords = list(dict.fromkeys(keywords))  # 순서 유지 중복 제거
        
        merged = []
        # 법령명은 우선 포함하되, 키워드도 함께 유지
        for law in key_terms.get("laws", [])[:2]:
            if law not in merged:
                merged.append(law)
        for k in domain_keywords:
            if k not in merged:
                merged.append(k)
        for k in keywords:
            if k not in merged:
                merged.append(k)
        
        # 최대 8개로 제한
        return " ".join(merged[:8]) if merged else situation[:50]

    def build_document_analysis(self, situation: str) -> Optional[Dict]:
        """
        문서 입력 감지 및 조항별 이슈/근거 힌트 분석
        """
        has_clause_pattern = bool(re.search(r"제\s*\d+\s*조", situation))
        if not any(keyword in situation for keyword in ["계약서", "약관", "임대인", "임차인"]) and not has_clause_pattern:
            return None

        issues = []
        clauses = []

        # 조항 단위 추출 (예: "제1조 ...")
        clause_pattern = re.compile(r'(제\s*\d+\s*조[^\n]*)', re.MULTILINE)
        matches = clause_pattern.findall(situation)
        for m in matches:
            clause_text = m.strip()
            clauses.append(clause_text)

        # 문서 전체 기준 핵심 쟁점 탐지
        if "즉시" in situation and "해지" in situation:
            issues.append({
                "issue": "일방적 즉시 해지 조항",
                "risk": "해지 요건·사유가 불명확하거나 과도할 수 있음",
                "needs_review": True,
                "related_clause": "해지"
            })
        if "보증금" in situation and "반환" in situation and "지연" in situation:
            issues.append({
                "issue": "보증금 반환 지연 조항",
                "risk": "지연 사유/기간이 불명확할 수 있음",
                "needs_review": True,
                "related_clause": "보증금 반환"
            })
        if "내부 기준" in situation or "내부기준" in situation:
            issues.append({
                "issue": "일방 기준 준용",
                "risk": "외부에 공개되지 않은 기준으로 의무가 확장될 수 있음",
                "needs_review": True,
                "related_clause": "특약"
            })
        if "계약 기간" in situation and ("갱신" in situation or "연장" in situation):
            issues.append({
                "issue": "갱신/연장 조건",
                "risk": "갱신 조건이 불명확할 수 있음",
                "needs_review": True,
                "related_clause": "계약 기간"
            })
        if "환불" in situation and ("불가" in situation or "없다" in situation):
            issues.append({
                "issue": "환불 제한 조항",
                "risk": "환불/청약철회 제한이 과도할 수 있음",
                "needs_review": True,
                "related_clause": "환불"
            })
        if "책임" in situation and ("지지 않는다" in situation or "면책" in situation):
            issues.append({
                "issue": "책임 제한/면책 조항",
                "risk": "손해배상 책임 제한이 과도할 수 있음",
                "needs_review": True,
                "related_clause": "책임 제한"
            })
        if "약관" in situation and "변경" in situation and ("사전 고지 없이" in situation or "사전고지 없이" in situation):
            issues.append({
                "issue": "약관 일방 변경",
                "risk": "사전 고지 없는 변경은 불공정 약관 소지가 있음",
                "needs_review": True,
                "related_clause": "약관 변경"
            })
        if "관할" in situation and ("본점" in situation or "회사" in situation):
            issues.append({
                "issue": "관할 법원 조항",
                "risk": "소비자에게 불리한 전속관할일 수 있음",
                "needs_review": True,
                "related_clause": "관할"
            })

        # 조항별 키워드 매핑
        clause_issues = []
        for clause in clauses:
            issue_tags = []
            if "해지" in clause:
                issue_tags.append("해지 요건")
            if "보증금" in clause and "반환" in clause:
                issue_tags.append("보증금 반환")
            if "특약" in clause or "내부 기준" in clause:
                issue_tags.append("특약 효력")
            if "계약 기간" in clause or "기간" in clause:
                issue_tags.append("계약 기간/갱신")
            if "환불" in clause or "청약철회" in clause:
                issue_tags.append("환불 제한")
            if "책임" in clause or "손해" in clause or "면책" in clause:
                issue_tags.append("책임 제한")
            if "약관" in clause and "변경" in clause:
                issue_tags.append("약관 변경")
            if "관할" in clause or "준거법" in clause:
                issue_tags.append("관할 불리")

            if issue_tags:
                clause_issues.append({
                    "clause": clause,
                    "issue_tags": issue_tags
                })

        # 조항별 근거 조회 힌트 생성
        clause_basis_hints = []
        for item in clause_issues:
            hints = []
            for tag in item.get("issue_tags", []):
                if tag == "해지 요건":
                    hints.extend(["민법 임대차 해지 요건", "임대차 계약 해지 요건"])
                elif tag == "보증금 반환":
                    hints.extend(["주택임대차보호법 보증금 반환", "임대차 보증금 반환 판례"])
                elif tag == "특약 효력":
                    hints.extend(["임대차 계약서 특약 효력", "약관법 불공정약관"])
                elif tag == "계약 기간/갱신":
                    hints.extend(["임대차 계약 갱신 요건", "주택임대차보호법 갱신요구권"])
                elif tag == "환불 제한":
                    hints.extend(["약관법 환불 제한", "전자상거래 청약철회 제한", "소비자기본법 환불"])
                elif tag == "책임 제한":
                    hints.extend(["약관법 손해배상 책임 제한", "면책조항 약관법", "고의과실 면책 무효"])
                elif tag == "약관 변경":
                    hints.extend(["약관 변경 사전고지", "사업자 일방 변경 약관법"])
                elif tag == "관할 불리":
                    hints.extend(["전속관할 약관 무효", "소비자 관할 약관 불리"])
            if hints:
                clause_basis_hints.append({
                    "clause": item.get("clause"),
                    "suggested_queries": list(dict.fromkeys(hints))[:5]
                })

        is_labor_contract = any(
            keyword in situation for keyword in [
                "근로", "근로자", "임금", "프리랜서", "용역", "도급", "위탁",
                "사용종속", "지휘", "감독", "출퇴근"
            ]
        )
        is_lease = any(
            keyword in situation for keyword in [
                "임대차", "임대인", "임차인", "보증금", "전세"
            ]
        )

        if is_labor_contract:
            suggested_queries = [
                "근로자성 판단 기준",
                "사용종속관계 판단 요소",
                "지휘감독 여부 판례",
                "위장도급 판단 기준",
                "임금 전액지급 원칙",
                "해지 손해배상 예정액 감액",
                "근로기준법 제2조 근로자 정의",
                "프리랜서 근로자성 판례"
            ]
        elif is_lease:
            suggested_queries = [
                "주택임대차보호법 보증금 반환",
                "민법 임대차 계약 해지 요건",
                "임대차 계약서 특약 효력",
                "임대차 계약 갱신 요건",
                "주택임대차보호법 갱신요구권",
                "임대차 보증금 반환 판례"
            ]
        else:
            suggested_queries = [
                "약관법 환불 제한",
                "약관법 손해배상 책임 제한",
                "약관 변경 사전고지",
                "전속관할 약관 무효",
                "계약 해지 요건",
                "손해배상 예정액 감액"
            ]

        return {
            "detected": True,
            "document_type": "계약서",
            "clauses": clauses[:10],
            "clause_issues": clause_issues[:10],
            "clause_basis_hints": clause_basis_hints[:10],
            "issues": issues,
            "suggested_queries": suggested_queries,
            "note": "문서 조항별로 법령·판례 근거를 조회해야 합니다.",
            "document_basis_plan": [
                "조항별 쟁점 태그를 확인",
                "각 조항의 suggested_queries로 법령/판례 검색",
                "근거 결과를 법적 근거 요약 블록에 반영"
            ]
        }
    
    async def comprehensive_search(
        self,
        situation: str,
        max_results_per_type: int = 5,
        arguments: Optional[dict] = None
    ) -> Dict:
        """
        사용자 상황을 종합적으로 분석하여 관련 법적 정보를 모두 찾기
        내부적으로 smart_search_tool을 호출하여 실제 법적 근거를 포함합니다.
        
        Args:
            situation: 사용자의 법적 상황 설명
            max_results_per_type: 타입당 최대 결과 수
            arguments: 추가 인자
            
        Returns:
            종합 검색 결과 및 가이드 (has_legal_basis, sources_count, missing_reason 포함)
        """
        # 1. 법적 영역 감지
        domains = self.detect_legal_domain(situation)
        detected_domains = [domain for domain, conf in domains if conf > 0.3]
        
        # 2. 핵심 용어 추출
        key_terms = self.extract_key_terms(situation)
        
        # 3. smart_search_tool 호출하여 실제 법적 근거 검색
        from ..services.smart_search_service import SmartSearchService
        smart_search_service = SmartSearchService()
        
        # 상황에서 검색 타입 자동 결정
        search_types = []
        if detected_domains:
            # 도메인별로 관련 검색 타입 추가
            for domain in detected_domains[:2]:
                if domain == "노동":
                    search_types.extend(["precedent", "law", "interpretation"])
                elif domain == "개인정보":
                    search_types.extend(["law", "interpretation", "committee"])
                elif domain == "세금":
                    search_types.extend(["law", "interpretation", "administrative_appeal"])
                else:
                    search_types.extend(["precedent", "law", "interpretation"])
        
        # 중복 제거 (순서 보장)
        seen = set()
        dedup = []
        for t in search_types:
            if t not in seen:
                seen.add(t)
                dedup.append(t)
        search_types = dedup[:3]  # 최대 3개
        
        # 검색 쿼리 정규화 (긴 문장 방지)
        normalized_query = self.normalize_query_for_search(situation, detected_domains, key_terms)
        
        # smart_search 호출
        smart_result = await smart_search_service.smart_search(
            normalized_query,
            search_types if search_types else None,
            max_results_per_type,
            arguments
        )
        
        # smart_search 결과에서 데이터 추출
        results = smart_result.get("results", {})
        law_results = results.get("law", {})
        precedent_results = results.get("precedent", {})
        interpretation_results = results.get("interpretation", {})
        appeal_results = results.get("administrative_appeal", {})
        
        # 에러만 있는 결과는 근거로 취급하지 않음
        def has_law_data(payload: dict) -> bool:
            if not isinstance(payload, dict):
                return False
            if "error" in payload:
                return False
            if payload.get("laws"):
                return True
            if payload.get("law_name"):
                return True
            return False
        
        def has_precedent_data(payload: dict) -> bool:
            if not isinstance(payload, dict):
                return False
            if "error" in payload:
                return False
            return bool(payload.get("precedents"))
        
        def has_interpretation_data(payload: dict) -> bool:
            if not isinstance(payload, dict):
                return False
            if "error" in payload:
                return False
            return bool(payload.get("interpretations"))
        
        def has_appeal_data(payload: dict) -> bool:
            if not isinstance(payload, dict):
                return False
            if "error" in payload:
                return False
            return bool(payload.get("appeals"))
        
        law_results_clean = law_results if has_law_data(law_results) else {}
        precedent_results_clean = precedent_results if has_precedent_data(precedent_results) else {}
        interpretation_results_clean = interpretation_results if has_interpretation_data(interpretation_results) else {}
        appeal_results_clean = appeal_results if has_appeal_data(appeal_results) else {}
        
        # 에러 정보는 별도로 보존 (error/api_error/text/html 대응)
        def collect_error(payload: dict) -> Optional[dict]:
            if not isinstance(payload, dict):
                return None
            content_type = payload.get("content_type") or payload.get("api_error", {}).get("content_type")
            if "error" in payload or "api_error" in payload:
                return payload
            if isinstance(content_type, str) and content_type.lower().startswith("text/html"):
                return payload
            return None
        
        errors = {}
        law_error = collect_error(law_results)
        if law_error:
            errors["law"] = law_error
        precedent_error = collect_error(precedent_results)
        if precedent_error:
            errors["precedent"] = precedent_error
        interpretation_error = collect_error(interpretation_results)
        if interpretation_error:
            errors["interpretation"] = interpretation_error
        appeal_error = collect_error(appeal_results)
        if appeal_error:
            errors["administrative_appeal"] = appeal_error
        
        # sources_count 계산
        sources_count = {
            "law": len(law_results_clean.get("laws", [])) if isinstance(law_results_clean, dict) and "laws" in law_results_clean else (1 if law_results_clean and "law_name" in law_results_clean else 0),
            "precedent": len(precedent_results_clean.get("precedents", [])) if isinstance(precedent_results_clean, dict) and "precedents" in precedent_results_clean else 0,
            "interpretation": len(interpretation_results_clean.get("interpretations", [])) if isinstance(interpretation_results_clean, dict) and "interpretations" in interpretation_results_clean else 0,
            "administrative_appeal": len(appeal_results_clean.get("appeals", [])) if isinstance(appeal_results_clean, dict) and "appeals" in appeal_results_clean else 0
        }
        
        # has_legal_basis 판단
        total_sources = sum(sources_count.values())
        has_legal_basis = total_sources > 0
        
        # missing_reason 판단
        missing_reason = None
        if not has_legal_basis:
            # API 에러 여부 확인
            api_error_found = False
            html_error_found = False
            for payload in [law_results, precedent_results, interpretation_results, appeal_results]:
                if isinstance(payload, dict):
                    content_type = payload.get("content_type") or payload.get("api_error", {}).get("content_type")
                    if payload.get("error_code") == "API_ERROR_HTML":
                        html_error_found = True
                    if (payload.get("error_code") == "API_ERROR_HTML" or "api_error" in payload or
                        ("error" in payload and "api_url" in payload) or
                        (isinstance(content_type, str) and content_type.lower().startswith("text/html"))):
                        api_error_found = True
                        break
            if api_error_found:
                missing_reason = "API_ERROR_HTML" if html_error_found else "API_ERROR"
            else:
                # API 준비 상태 확인
                from ..repositories.base import BaseLawRepository
                api_key = BaseLawRepository.get_api_key(None)
                if BaseLawRepository.is_placeholder_key(api_key):
                    missing_reason = "API_NOT_READY"
                else:
                    missing_reason = "NO_MATCH"
        
        # 법적 근거 요약
        legal_basis_summary = {
            "has_legal_basis": has_legal_basis,
            "types": [k for k, v in sources_count.items() if v > 0],
            "counts": sources_count,
            "missing_reason": missing_reason
        }
        
        # 문서 입력 감지 및 분석 (계약서/약관 등)
        document_analysis = self.build_document_analysis(situation)
        
        # legal_basis_block_text 생성 (상단 요약용)
        citations_titles = []
        for c in smart_result.get("citations", []) if isinstance(smart_result, dict) else []:
            if isinstance(c, dict):
                title = c.get("name") or c.get("case_number") or c.get("id")
                if title:
                    citations_titles.append(str(title))
        fallback_titles = []
        if isinstance(smart_result, dict):
            fb = smart_result.get("fallback_legal_basis")
            if fb and isinstance(fb, dict):
                for item in fb.get("items", [])[:3]:
                    if isinstance(item, dict) and item.get("title"):
                        fallback_titles.append(item.get("title"))
        if has_legal_basis:
            legal_basis_block_text = (
                "법적 근거 요약: "
                f"유형={','.join(legal_basis_summary.get('types', [])) or '없음'}, "
                f"근거 수={sum(sources_count.values())}. "
                f"주요 근거={', '.join(citations_titles) if citations_titles else '없음'}"
            )
        else:
            legal_basis_block_text = (
                "법적 근거 요약: "
                f"근거를 찾지 못했습니다({missing_reason}). "
                f"대체 근거={', '.join(fallback_titles) if fallback_titles else '없음'}"
            )
        
        # 가이드 생성
        guidance = self.generate_guidance(
            situation,
            detected_domains,
            key_terms,
            law_results_clean,
            precedent_results_clean,
            interpretation_results_clean,
            missing_reason,
            normalized_query
        )
        
        success_transport = True
        success_search = has_legal_basis
        
        return {
            "success_transport": success_transport,
            "success_search": success_search,
            "success": success_transport,
            "has_legal_basis": has_legal_basis,
            "situation": situation,
            "detected_domains": detected_domains,
            "laws": law_results_clean,
            "precedents": precedent_results_clean,
            "interpretations": interpretation_results_clean,
            "administrative_appeals": appeal_results_clean,
            "sources_count": sources_count,
            "guidance": guidance,
            "legal_basis_summary": legal_basis_summary,
            "citations": smart_result.get("citations", []) if isinstance(smart_result, dict) else [],
            "one_line_answer": smart_result.get("one_line_answer") if isinstance(smart_result, dict) else None,
            "fallback_legal_basis": smart_result.get("fallback_legal_basis") if isinstance(smart_result, dict) else None,
            "legal_basis_block_text": legal_basis_block_text,
            "missing_reason": missing_reason,
            "document_analysis": document_analysis,
            "errors": errors,
            "response_policy": {
                "must_include": ["legal_basis_block_text", "legal_basis_block", "legal_basis_summary"],
                "preferred_order": ["legal_basis_block_text", "legal_basis_block", "one_line_answer"],
                "if_has_legal_basis_false": "no_conclusions",
                "when_api_error": "explain_api_error_and_request_retry"
            },
            "summary": self.generate_summary(
                detected_domains,
                law_results_clean,
                precedent_results_clean,
                interpretation_results_clean
            )
        }
    
    async def document_issue_analysis(
        self,
        document_text: str,
        arguments: Optional[dict] = None,
        auto_search: bool = True,
        max_clauses: int = 3,
        max_results_per_type: int = 3
    ) -> Dict:
        """
        문서(계약서/약관 등) 입력에 대한 조항별 이슈 및 조회 힌트 분석
        """
        analysis = self.build_document_analysis(document_text or "")
        evidence_results = []
        evidence_summary = {
            "searched_clauses": 0,
            "has_legal_basis": False,
            "missing_reason": "NO_SEARCH"
        }
        risk_findings = []
        
        def count_sources(payload: Optional[dict]) -> int:
            if not isinstance(payload, dict):
                return 0
            sources_count = payload.get("sources_count")
            if isinstance(sources_count, dict):
                return sum(int(v or 0) for v in sources_count.values())
            results = payload.get("results", {}) if isinstance(payload.get("results"), dict) else {}
            law_count = 0
            precedent_count = 0
            interpretation_count = 0
            if isinstance(results.get("law"), dict):
                law_count = len(results.get("law", {}).get("laws", []))
            if isinstance(results.get("precedent"), dict):
                precedent_count = len(results.get("precedent", {}).get("precedents", []))
            if isinstance(results.get("interpretation"), dict):
                interpretation_count = len(results.get("interpretation", {}).get("interpretations", []))
            # fallback: citations가 있으면 근거로 간주
            if not (law_count or precedent_count or interpretation_count):
                citations = payload.get("citations")
                if isinstance(citations, list) and citations:
                    return len(citations)
            return law_count + precedent_count + interpretation_count
        
        def collect_precedents(payload: Optional[dict]) -> List[str]:
            if not isinstance(payload, dict):
                return []
            results = payload.get("results", {}) if isinstance(payload.get("results"), dict) else {}
            precedents = results.get("precedent", {}).get("precedents", []) if isinstance(results.get("precedent", {}), dict) else []
            names = []
            for item in precedents:
                if isinstance(item, dict):
                    name = item.get("case_name") or item.get("caseNumber") or item.get("case_number")
                    if name:
                        names.append(name)
            return names[:5]
        
        def collect_citations(payload: Optional[dict]) -> List[dict]:
            if not isinstance(payload, dict):
                return []
            citations = payload.get("citations", [])
            return citations[:5] if isinstance(citations, list) else []
        
        # 조항별 자동 검색 (옵션)
        if auto_search and analysis and analysis.get("clause_basis_hints"):
            from ..services.smart_search_service import SmartSearchService
            smart_search_service = SmartSearchService()
            
            for item in analysis.get("clause_basis_hints", [])[:max_clauses]:
                clause = item.get("clause")
                queries = item.get("suggested_queries", [])[:]
                # 최소 2개 이상의 쿼리 보장 (fallback 포함)
                if len(queries) < 2 and analysis.get("suggested_queries"):
                    for q in analysis.get("suggested_queries", []):
                        if q not in queries:
                            queries.append(q)
                queries = queries[:2]
                if not queries:
                    continue
                
                clause_citations = []
                clause_precedents = []
                clause_sources = 0
                
                for query in queries:
                    result = await smart_search_service.smart_search(
                        query,
                        ["law", "precedent", "interpretation"],
                        max_results_per_type,
                        arguments
                    )
                    evidence_results.append({
                        "clause": clause,
                        "query": query,
                        "result": result
                    })
                    clause_sources += count_sources(result)
                    clause_citations.extend(collect_citations(result))
                    clause_precedents.extend(collect_precedents(result))
                
                clause_has_legal_basis = clause_sources > 0 or len(clause_citations) > 0
                risk_level = "high" if clause_has_legal_basis else "medium"
                why = None
                if clause_citations:
                    first = clause_citations[0]
                    if isinstance(first, dict):
                        why = first.get("article") or first.get("article_number") or first.get("name")
                if not why:
                    why = queries[0] if queries else None
                
                risk_findings.append({
                    "clause": clause,
                    "risk_level": risk_level,
                    "why": why,
                    "precedents": list(dict.fromkeys(clause_precedents))[:5],
                    "citations": clause_citations[:5]
                })
            
            # 요약 집계
            evidence_summary["searched_clauses"] = len({r.get("clause") for r in evidence_results})
            evidence_summary["has_legal_basis"] = any(
                count_sources(r.get("result")) > 0 or len(collect_citations(r.get("result"))) > 0
                for r in evidence_results
            )
            # missing_reason 집계
            if evidence_summary["has_legal_basis"]:
                evidence_summary["missing_reason"] = None
            else:
                reasons = [r.get("result", {}).get("missing_reason") for r in evidence_results]
                if "API_ERROR_HTML" in reasons:
                    evidence_summary["missing_reason"] = "API_ERROR_HTML"
                elif "API_ERROR" in reasons:
                    evidence_summary["missing_reason"] = "API_ERROR"
                elif "API_NOT_READY" in reasons:
                    evidence_summary["missing_reason"] = "API_NOT_READY"
                else:
                    evidence_summary["missing_reason"] = "NO_MATCH"
        elif auto_search and analysis and not analysis.get("clause_basis_hints"):
            evidence_summary["missing_reason"] = "NO_HINTS"
        elif not analysis:
            evidence_summary["missing_reason"] = "NO_DOCUMENT"
        
        total_citations = []
        for item in evidence_results:
            total_citations.extend(collect_citations(item.get("result")))
        total_citations = total_citations[:10]
        
        legal_basis_summary = {
            "has_legal_basis": evidence_summary["has_legal_basis"],
            "types": ["law", "precedent", "interpretation"] if evidence_summary["has_legal_basis"] else [],
            "counts": {
                "citations": len(total_citations),
                "clauses": evidence_summary["searched_clauses"]
            },
            "missing_reason": evidence_summary["missing_reason"]
        }
        risk_summary = []
        for item in risk_findings[:5]:
            if isinstance(item, dict):
                risk_summary.append({
                    "clause": item.get("clause"),
                    "risk_level": item.get("risk_level"),
                    "why": item.get("why"),
                    "precedents": (item.get("precedents") or [])[:2],
                    "citations": (item.get("citations") or [])[:2]
                })
        legal_basis_block = {
            "summary": legal_basis_summary,
            "citations": total_citations,
            "risk_summary": risk_summary,
            "fallback": None,
            "missing_reason": evidence_summary["missing_reason"]
        }
        if evidence_summary["has_legal_basis"]:
            legal_basis_block_text = (
                "법적 근거 요약: "
                f"유형={','.join(legal_basis_summary.get('types', [])) or '없음'}, "
                f"근거 수={legal_basis_summary['counts'].get('citations', 0)}."
            )
        else:
            if evidence_summary["missing_reason"] == "API_ERROR_HTML":
                legal_basis_block_text = (
                    "법적 근거 요약: API가 HTML 안내 페이지를 반환하여 근거를 가져오지 못했습니다."
                )
            else:
                legal_basis_block_text = (
                    "법적 근거 요약: "
                    f"근거를 찾지 못했습니다({evidence_summary['missing_reason']}). "
                    "문서 분석 결과를 기반으로 조항별 검색을 진행하세요."
                )
        retry_plan = None
        if analysis and analysis.get("suggested_queries"):
            retry_plan = {
                "suggested_queries": analysis.get("suggested_queries", [])[:6],
                "note": "추천 검색어로 법령/판례 검색을 재시도하세요."
            }
        
        return {
            "success_transport": True,
            "success_search": evidence_summary["has_legal_basis"],
            "success": True,
            "has_legal_basis": evidence_summary["has_legal_basis"],
            "missing_reason": evidence_summary["missing_reason"],
            "document_text": document_text,
            "document_analysis": analysis,
            "answer": {
                "risk_findings": risk_findings
            },
            "evidence_results": evidence_results,
            "evidence_summary": evidence_summary,
            "legal_basis_summary": legal_basis_summary,
            "legal_basis_block": legal_basis_block,
            "legal_basis_block_text": legal_basis_block_text,
            "retry_plan": retry_plan,
            "response_policy": {
                "must_include": ["document_analysis", "legal_basis_block_text", "legal_basis_block", "retry_plan"],
                "preferred_order": ["legal_basis_block_text", "document_analysis"],
                "if_has_legal_basis_false": "no_conclusions",
                "when_api_error": "explain_api_error_and_request_retry"
            }
        }
    
    def generate_guidance(
        self,
        situation: str,
        domains: List[str],
        key_terms: Dict,
        law_results: Dict,
        precedent_results: Dict,
        interpretation_results: Dict,
        missing_reason: Optional[str] = None,
        normalized_query: Optional[str] = None
    ) -> Dict:
        """
        사용자에게 단계별 가이드 제공
        """
        steps = []
        
        # 0단계: API 에러 안내 (근거 조회 실패 시 최우선)
        if missing_reason == "API_ERROR":
            steps.append({
                "step": len(steps) + 1,
                "title": "API 근거 조회 실패(HTML)",
                "description": "국가법령정보센터에서 HTML 응답을 반환하여 근거를 조회하지 못했습니다.",
                "action": f"재시도 검색어 제안: {normalized_query}" if normalized_query else "검색어를 짧은 키워드로 줄여 다시 시도하세요."
            })
        
        # 1단계: 관련 법령 확인
        if law_results:
            law_names = []
            if isinstance(law_results, dict):
                if law_results.get("law_name"):
                    law_names.append(law_results.get("law_name"))
                if isinstance(law_results.get("laws"), list):
                    for item in law_results.get("laws", [])[:5]:
                        if isinstance(item, dict):
                            name = item.get("법령명한글") or item.get("lawNm") or item.get("법령명")
                            if name:
                                law_names.append(name)
            law_names = [n for n in law_names if n]
            if law_names:
                steps.append({
                    "step": len(steps) + 1,
                    "title": "관련 법령 확인",
                    "description": f"다음 법령들이 관련될 수 있습니다: {', '.join(law_names)}",
                    "action": "각 법령의 조문을 확인하여 본인의 상황에 적용되는지 검토하세요."
                })
        
        # 2단계: 유사 판례 확인
        if precedent_results:
            precedent_count = 0
            if isinstance(precedent_results, dict):
                if "precedents" in precedent_results and isinstance(precedent_results.get("precedents"), list):
                    precedent_count = len(precedent_results.get("precedents"))
                elif "total" in precedent_results:
                    precedent_count = int(precedent_results.get("total", 0) or 0)
            if precedent_count > 0:
                steps.append({
                    "step": len(steps) + 1,
                    "title": "유사 판례 검토",
                    "description": f"{precedent_count}개의 유사 판례를 찾았습니다.",
                    "action": "유사한 사건이 어떻게 판결되었는지 확인하여 참고하세요."
                })
        
        # 3단계: 기관 해석 확인
        if interpretation_results:
            agencies = []
            if isinstance(interpretation_results, dict):
                if "interpretations" in interpretation_results and isinstance(interpretation_results.get("interpretations"), list):
                    for item in interpretation_results.get("interpretations", [])[:5]:
                        if isinstance(item, dict):
                            agency = item.get("agency_name") or item.get("agency")
                            if agency:
                                agencies.append(agency)
            agencies = [a for a in agencies if a]
            if agencies:
                steps.append({
                    "step": len(steps) + 1,
                    "title": "관련 기관 해석 확인",
                    "description": f"다음 기관들의 공식 해석을 확인하세요: {', '.join(agencies)}",
                    "action": "기관의 공식 해석이 본인의 상황에 어떻게 적용되는지 검토하세요."
                })
        
        # 4단계: 행정심판/소청 가능성 (근거 있을 때만 후순위로)
        has_any_evidence = bool(law_results or precedent_results or interpretation_results)
        if has_any_evidence and domains:
            domain_config = self.LEGAL_DOMAIN_KEYWORDS.get(domains[0], {})
            agencies = domain_config.get("agencies", [])
            if agencies:
                steps.append({
                    "step": len(steps) + 1,
                    "title": "행정심판/소청 고려",
                    "description": f"관련 기관({', '.join(agencies[:2])})에 행정심판이나 소청을 제기할 수 있습니다.",
                    "action": "유사한 행정심판 사례를 참고하여 절차를 확인하세요."
                })
        
        # 5단계: 전문가 상담 권장
        steps.append({
            "step": len(steps) + 1,
            "title": "전문가 상담 권장",
            "description": "복잡한 법적 문제는 변호사나 법률 전문가의 상담을 받는 것이 좋습니다.",
            "action": "본인의 상황을 정확히 파악하기 위해 전문가와 상담하세요."
        })
        
        return {
            "steps": steps,
            "total_steps": len(steps),
            "estimated_time": f"{len(steps) * 30}분"
        }
    
    def generate_summary(
        self,
        domains: List[str],
        law_results: Dict,
        precedent_results: Dict,
        interpretation_results: Dict
    ) -> str:
        """
        검색 결과 요약 생성
        """
        summary_parts = []
        
        if domains:
            summary_parts.append(f"법적 영역: {', '.join(domains)}")
        
        if law_results:
            law_count = 0
            if isinstance(law_results, dict):
                if isinstance(law_results.get("laws"), list):
                    law_count = len(law_results.get("laws"))
                elif law_results.get("law_name"):
                    law_count = 1
            summary_parts.append(f"관련 법령 {law_count}개 발견")
        
        if precedent_results:
            total_precedents = 0
            if isinstance(precedent_results, dict):
                if isinstance(precedent_results.get("precedents"), list):
                    total_precedents = len(precedent_results.get("precedents"))
                elif precedent_results.get("total"):
                    total_precedents = int(precedent_results.get("total", 0) or 0)
            summary_parts.append(f"유사 판례 {total_precedents}개 발견")
        
        if interpretation_results:
            interpretation_count = 0
            if isinstance(interpretation_results, dict) and isinstance(interpretation_results.get("interpretations"), list):
                interpretation_count = len(interpretation_results.get("interpretations"))
            summary_parts.append(f"기관 해석 {interpretation_count}개 발견")
        
        if not summary_parts:
            return "관련 법적 정보를 찾지 못했습니다. 더 구체적인 상황을 설명해주세요."
        
        return " | ".join(summary_parts)

