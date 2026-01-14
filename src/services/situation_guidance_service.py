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
            "keywords": ["근로", "임금", "해고", "퇴직금", "근로시간", "휴가"]
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
            "keywords": ["소비자", "약관", "계약", "환불", "하자"]
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
    
    async def comprehensive_search(
        self,
        situation: str,
        max_results_per_type: int = 5,
        arguments: Optional[dict] = None
    ) -> Dict:
        """
        사용자 상황을 종합적으로 분석하여 관련 법적 정보를 모두 찾기
        
        Args:
            situation: 사용자의 법적 상황 설명
            max_results_per_type: 타입당 최대 결과 수
            arguments: 추가 인자
            
        Returns:
            종합 검색 결과 및 가이드
        """
        # 1. 법적 영역 감지
        domains = self.detect_legal_domain(situation)
        detected_domains = [domain for domain, conf in domains if conf > 0.3]
        
        # 2. 핵심 용어 추출
        key_terms = self.extract_key_terms(situation)
        
        # 3. 관련 법령 검색
        law_results = {}
        # 법령명이 추출되지 않았으면 도메인에서 관련 법령 검색
        if not key_terms["laws"] and detected_domains:
            for domain in detected_domains[:2]:
                domain_config = self.LEGAL_DOMAIN_KEYWORDS.get(domain, {})
                key_terms["laws"].extend(domain_config.get("laws", [])[:2])
        
        if key_terms["laws"]:
            for law_name in key_terms["laws"][:3]:  # 최대 3개 법령
                try:
                    # get_law 시그니처: get_law(law_id=None, law_name=None, mode="detail", ...)
                    result = await asyncio.to_thread(
                        self.law_detail_repo.get_law,
                        None,  # law_id
                        law_name,  # law_name
                        "detail",  # mode
                        None, None, None, None,  # article_number, hang, ho, mok
                        arguments
                    )
                    if "error" not in result:
                        law_results[law_name] = result
                except Exception as e:
                    import logging
                    logger = logging.getLogger("lexguard-mcp")
                    logger.debug(f"Error searching law {law_name}: {e}")
                    pass
        
        # 법령명이 없으면 키워드로 법령 검색
        if not law_results and key_terms["keywords"]:
            for keyword in key_terms["keywords"][:2]:
                try:
                    result = await asyncio.to_thread(
                        self.law_search_repo.search_law,
                        keyword,
                        1,
                        max_results_per_type,
                        arguments
                    )
                    if "error" not in result and result.get("laws"):
                        law_results[f"search_{keyword}"] = result
                        break  # 첫 번째 성공한 검색만 사용
                except:
                    pass
        
        # 4. 유사 판례 검색
        precedent_results = {}
        # 키워드가 없으면 도메인에서 키워드 추출
        if not key_terms["keywords"] and detected_domains:
            for domain in detected_domains[:2]:
                domain_config = self.LEGAL_DOMAIN_KEYWORDS.get(domain, {})
                key_terms["keywords"].extend(domain_config.get("keywords", [])[:3])
        
        search_queries = key_terms["keywords"][:3] if key_terms["keywords"] else [situation[:50]]
        for query in search_queries:
            try:
                result = await asyncio.to_thread(
                    self.precedent_repo.search_precedent,
                    query,
                    1,
                    max_results_per_type,
                    None, None, None,
                    arguments
                )
                # 에러가 없고 precedents가 있으면 추가
                if "error" not in result and result.get("precedents"):
                    precedent_results[query] = result
                # precedents가 없어도 total이 0이 아니면 추가 (빈 결과도 정보)
                elif "error" not in result and result.get("total", 0) > 0:
                    precedent_results[query] = result
            except Exception as e:
                import logging
                logger = logging.getLogger("lexguard-mcp")
                logger.debug(f"Error searching precedent with query '{query}': {e}")
                pass
        
        # 5. 관련 기관 해석 검색
        interpretation_results = {}
        if detected_domains:
            for domain in detected_domains[:2]:
                domain_config = self.LEGAL_DOMAIN_KEYWORDS.get(domain, {})
                agencies = domain_config.get("agencies", [])
                for agency in agencies[:2]:
                    try:
                        result = await asyncio.to_thread(
                            self.interpretation_repo.search_law_interpretation,
                            situation[:100],
                            1,
                            max_results_per_type,
                            agency,
                            arguments
                        )
                        if "error" not in result and (result.get("interpretations") or result.get("total", 0) > 0):
                            interpretation_results[agency] = result
                    except Exception as e:
                        import logging
                        logger = logging.getLogger("lexguard-mcp")
                        logger.debug(f"Error searching interpretation for {agency}: {e}")
                        pass
        
        # 6. 행정심판 사례 검색
        appeal_results = {}
        try:
            result = await asyncio.to_thread(
                self.appeal_repo.search_administrative_appeal,
                situation[:100],
                1,
                max_results_per_type,
                None, None,
                arguments
            )
            if "error" not in result and (result.get("appeals") or result.get("total", 0) > 0):
                appeal_results = result
        except Exception as e:
            import logging
            logger = logging.getLogger("lexguard-mcp")
            logger.debug(f"Error searching administrative appeal: {e}")
            pass
        
        # 7. 위원회 결정문 검색
        committee_results = {}
        if detected_domains:
            for domain in detected_domains[:2]:
                domain_config = self.LEGAL_DOMAIN_KEYWORDS.get(domain, {})
                agencies = domain_config.get("agencies", [])
                for agency in agencies:
                    if "위원회" in agency:
                        try:
                            result = await asyncio.to_thread(
                                self.committee_repo.search_committee_decision,
                                agency,
                                situation[:100],
                                1,
                                max_results_per_type,
                                arguments
                            )
                            if "error" not in result and (result.get("decisions") or result.get("total", 0) > 0):
                                committee_results[agency] = result
                        except Exception as e:
                            import logging
                            logger = logging.getLogger("lexguard-mcp")
                            logger.debug(f"Error searching committee decision for {agency}: {e}")
                            pass
        
        # 8. 가이드 생성
        guidance = self.generate_guidance(
            situation,
            detected_domains,
            key_terms,
            law_results,
            precedent_results,
            interpretation_results
        )
        
        return {
            "situation": situation,
            "detected_domains": detected_domains,
            "key_terms": key_terms,
            "laws": law_results,
            "precedents": precedent_results,
            "interpretations": interpretation_results,
            "administrative_appeals": appeal_results,
            "committee_decisions": committee_results,
            "guidance": guidance,
            "summary": self.generate_summary(
                detected_domains,
                law_results,
                precedent_results,
                interpretation_results
            )
        }
    
    def generate_guidance(
        self,
        situation: str,
        domains: List[str],
        key_terms: Dict,
        law_results: Dict,
        precedent_results: Dict,
        interpretation_results: Dict
    ) -> Dict:
        """
        사용자에게 단계별 가이드 제공
        """
        steps = []
        
        # 1단계: 관련 법령 확인
        if law_results:
            steps.append({
                "step": 1,
                "title": "관련 법령 확인",
                "description": f"다음 법령들이 관련될 수 있습니다: {', '.join(law_results.keys())}",
                "action": "각 법령의 조문을 확인하여 본인의 상황에 적용되는지 검토하세요."
            })
        
        # 2단계: 유사 판례 확인
        if precedent_results:
            steps.append({
                "step": 2,
                "title": "유사 판례 검토",
                "description": f"{len(precedent_results)}개의 유사 판례를 찾았습니다.",
                "action": "유사한 사건이 어떻게 판결되었는지 확인하여 참고하세요."
            })
        
        # 3단계: 기관 해석 확인
        if interpretation_results:
            steps.append({
                "step": 3,
                "title": "관련 기관 해석 확인",
                "description": f"다음 기관들의 공식 해석을 확인하세요: {', '.join(interpretation_results.keys())}",
                "action": "기관의 공식 해석이 본인의 상황에 어떻게 적용되는지 검토하세요."
            })
        
        # 4단계: 행정심판/소청 가능성
        if domains:
            domain_config = self.LEGAL_DOMAIN_KEYWORDS.get(domains[0], {})
            agencies = domain_config.get("agencies", [])
            if agencies:
                steps.append({
                    "step": 4,
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
            summary_parts.append(f"관련 법령 {len(law_results)}개 발견")
        
        if precedent_results:
            total_precedents = sum(len(r.get("precedents", [])) for r in precedent_results.values())
            summary_parts.append(f"유사 판례 {total_precedents}개 발견")
        
        if interpretation_results:
            summary_parts.append(f"기관 해석 {len(interpretation_results)}개 발견")
        
        if not summary_parts:
            return "관련 법적 정보를 찾지 못했습니다. 더 구체적인 상황을 설명해주세요."
        
        return " | ".join(summary_parts)

