"""
Smart Search Service - 사용자 질문을 분석하여 적절한 API를 자동 선택
"""
import re
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
from ..repositories.law_comparison_repository import LawComparisonRepository


class SmartSearchService:
    """
    사용자 질문을 분석하여 적절한 법적 정보 소스를 자동으로 선택하는 서비스
    
    LLM이 사용자 질문을 받으면:
    1. 질문 의도 분석 (법령, 판례, 법령해석, 행정심판 등)
    2. 적절한 검색 타입 선택
    3. 파라미터 자동 추출
    4. 통합 검색 실행
    """
    
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
        self.comparison_repo = LawComparisonRepository()
        
        # 의도 분류 키워드
        self.intent_keywords = {
            "law": {
                "keywords": ["법령", "법", "조문", "조항", "법률", "시행령", "시행규칙", "법 제", "법률 제"],
                "patterns": [r"법\s*제?\s*\d+조", r"법령\s*제?\s*\d+조", r"\w+법\s*제?\s*\d+조"]
            },
            "precedent": {
                "keywords": ["판례", "대법원", "판결", "선고", "사건", "재판", "법원", "관련 판례", "관련사례"],
                "patterns": [r"판례", r"대법원\s*\d+", r"사건번호", r"관련\s*판례", r"관련\s*사례"]
            },
            "interpretation": {
                "keywords": ["법령해석", "해석", "의견", "해석례", "법제처", "부처 해석"],
                "patterns": [r"법령해석", r"해석\s*의견"]
            },
            "administrative_appeal": {
                "keywords": ["행정심판", "심판", "재결", "행정심판위원회"],
                "patterns": [r"행정심판", r"재결례"]
            },
            "constitutional": {
                "keywords": ["헌법재판소", "헌재", "위헌", "헌법", "헌법재판"],
                "patterns": [r"헌법재판소", r"헌재", r"위헌"]
            },
            "committee": {
                "keywords": ["위원회", "결정문", "개인정보보호위원회", "금융위원회", "노동위원회"],
                "patterns": [r"\w+위원회", r"결정문"]
            },
            "special_appeal": {
                "keywords": ["조세심판원", "해양안전심판원", "특별행정심판"],
                "patterns": [r"조세심판원", r"해양안전심판원", r"특별행정심판"]
            },
            "ordinance": {
                "keywords": ["조례", "규칙", "지방자치", "시조례", "도조례"],
                "patterns": [r"\w+조례", r"지방자치"]
            },
            "rule": {
                "keywords": ["행정규칙", "훈령", "예규", "고시"],
                "patterns": [r"행정규칙", r"훈령", r"예규"]
            },
            "comparison": {
                "keywords": ["비교", "신구법", "연혁", "변경", "개정"],
                "patterns": [r"신구법", r"연혁", r"비교"]
            }
        }
    
    def analyze_intent(self, query: str) -> List[Tuple[str, float]]:
        """
        사용자 질문의 의도를 분석하여 검색 타입과 신뢰도를 반환
        
        Returns:
            [(search_type, confidence), ...] - 신뢰도 순으로 정렬
        """
        query_lower = query.lower()
        scores = {}
        
        for search_type, config in self.intent_keywords.items():
            score = 0.0
            
            # 키워드 매칭
            for keyword in config["keywords"]:
                if keyword in query_lower:
                    score += 1.0
            
            # 패턴 매칭
            for pattern in config.get("patterns", []):
                if re.search(pattern, query, re.IGNORECASE):
                    score += 2.0  # 패턴 매칭이 더 높은 가중치
            
            if score > 0:
                scores[search_type] = score
        
        # 신뢰도 순으로 정렬
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        # 신뢰도를 0-1 범위로 정규화
        if sorted_scores:
            max_score = sorted_scores[0][1]
            normalized = [(st, min(score / max_score, 1.0)) for st, score in sorted_scores]
            
            # 여러 의도 동시 감지: 신뢰도 0.5 이상인 모든 의도 반환
            # 예: "형법 제250조와 관련 판례" → ["law", "precedent"]
            high_confidence = [(st, conf) for st, conf in normalized if conf >= 0.5]
            if len(high_confidence) > 1:
                # 여러 의도가 감지되면 모두 반환
                return high_confidence
            elif high_confidence:
                # 단일 의도지만 신뢰도가 높으면 반환
                return high_confidence
            else:
                # 신뢰도가 낮으면 최상위 1개만 반환
                return normalized[:1]
        
        # 기본값: 법령 검색
        return [("law", 0.5)]
    
    def extract_parameters(self, query: str, search_type: str) -> Dict:
        """
        질문에서 검색 파라미터를 자동 추출
        
        Args:
            query: 사용자 질문
            search_type: 검색 타입
            
        Returns:
            추출된 파라미터 딕셔너리
        """
        params = {"query": query}
        
        # 법령명 추출 (예: "형법", "민법", "개인정보보호법")
        law_name_pattern = r"([가-힣]+법)"
        law_matches = re.findall(law_name_pattern, query)
        if law_matches:
            params["law_name"] = law_matches[0]
        
        # 조문 번호 추출 (예: "제250조", "250조")
        article_pattern = r"제?\s*(\d+)\s*조"
        article_matches = re.findall(article_pattern, query)
        if article_matches:
            # 정규화 유틸리티 사용
            from ..utils.parameter_normalizer import normalize_article_number
            params["article_number"] = normalize_article_number(article_matches[0])
        
        # 항(項) 번호 추출 (예: "제1항", "1항", "첫 번째 항")
        hang_patterns = [
            r"제?\s*(\d+)\s*항",  # "제1항", "1항"
            r"(\d+)\s*번째\s*항",  # "첫 번째 항" (숫자만)
            r"제?\s*(\d+)\s*번\s*항",  # "제1번 항"
        ]
        for pattern in hang_patterns:
            hang_matches = re.findall(pattern, query)
            if hang_matches:
                from ..utils.parameter_normalizer import normalize_hang
                params["hang"] = normalize_hang(hang_matches[0])
                break
        
        # 호(號) 번호 추출 (예: "제2호", "2호", "둘째 호")
        ho_patterns = [
            r"제?\s*(\d+)\s*호",  # "제2호", "2호"
            r"(\d+)\s*번째\s*호",  # "둘째 호" (숫자만)
            r"제?\s*(\d+)\s*번\s*호",  # "제2번 호"
        ]
        for pattern in ho_patterns:
            ho_matches = re.findall(pattern, query)
            if ho_matches:
                from ..utils.parameter_normalizer import normalize_ho
                params["ho"] = normalize_ho(ho_matches[0])
                break
        
        # 목(目) 문자 추출 (예: "가목", "나목", "다목")
        mok_pattern = r"([가-힣])\s*목"
        mok_matches = re.findall(mok_pattern, query)
        if mok_matches:
            from ..utils.parameter_normalizer import normalize_mok
            params["mok"] = normalize_mok(mok_matches[0] + "목")
        
        # 비교 타입 추출 (법령 비교용)
        if search_type == "comparison":
            if "연혁" in query or "변경사항" in query or "개정" in query:
                params["compare_type"] = "연혁"
            elif "3단" in query or "세단계" in query:
                params["compare_type"] = "3단비교"
            else:
                params["compare_type"] = "신구법"  # 기본값
        
        # 날짜 추출 (예: "2023년", "2023.01.01")
        date_pattern = r"(\d{4})[년\.]?\s*(\d{1,2})[월\.]?\s*(\d{1,2})[일]?"
        date_matches = re.findall(date_pattern, query)
        if date_matches:
            year, month, day = date_matches[0]
            params["date"] = f"{year}{month.zfill(2)}{day.zfill(2)}" if day else f"{year}{month.zfill(2)}01"
        
        # 기관명 추출 (위원회, 특별행정심판원, 부처)
        # 위원회 (11개)
        committee_patterns = {
            "개인정보보호위원회": "개인정보보호위원회",
            "금융위원회": "금융위원회",
            "노동위원회": "노동위원회",
            "고용보험심사위원회": "고용보험심사위원회",
            "국민권익위원회": "국민권익위원회",
            "방송미디어통신위원회": "방송미디어통신위원회",
            "산업재해보상보험재심사위원회": "산업재해보상보험재심사위원회",
            "중앙토지수용위원회": "중앙토지수용위원회",
            "중앙환경분쟁조정위원회": "중앙환경분쟁조정위원회",
            "증권선물위원회": "증권선물위원회",
            "국가인권위원회": "국가인권위원회",
        }
        
        # 특별행정심판원 (4개)
        tribunal_patterns = {
            "조세심판원": "조세심판원",
            "해양안전심판원": "해양안전심판원",
            "국민권익위원회": "국민권익위원회",
            "인사혁신처 소청심사위원회": "인사혁신처 소청심사위원회",
        }
        
        # 부처 (39개) - 법령해석/행정규칙 검색용
        agency_patterns = {
            "기획재정부": "기획재정부",
            "국세청": "국세청",
            "관세청": "관세청",
            "고용노동부": "고용노동부",
            "교육부": "교육부",
            "보건복지부": "보건복지부",
            "질병관리청": "질병관리청",
            "식품의약품안전처": "식품의약품안전처",
            "법무부": "법무부",
            "외교부": "외교부",
            "국방부": "국방부",
            "방위사업청": "방위사업청",
            "병무청": "병무청",
            "행정안전부": "행정안전부",
            "경찰청": "경찰청",
            "소방청": "소방청",
            "해양경찰청": "해양경찰청",
            "문화체육관광부": "문화체육관광부",
            "농림축산식품부": "농림축산식품부",
            "농촌진흥청": "농촌진흥청",
            "산림청": "산림청",
            "산업통상부": "산업통상부",
            "중소벤처기업부": "중소벤처기업부",
            "과학기술정보통신부": "과학기술정보통신부",
            "국가데이터처": "국가데이터처",
            "지식재산처": "지식재산처",
            "기상청": "기상청",
            "해양수산부": "해양수산부",
            "국토교통부": "국토교통부",
            "행정중심복합도시건설청": "행정중심복합도시건설청",
            "기후에너지환경부": "기후에너지환경부",
            "통일부": "통일부",
            "국가보훈부": "국가보훈부",
            "성평등가족부": "성평등가족부",
            "재외동포청": "재외동포청",
            "인사혁신처": "인사혁신처",
            "법제처": "법제처",
            "조달청": "조달청",
            "국가유산청": "국가유산청",
        }
        
        # 위원회 매칭
        if search_type == "committee":
            for agency_name, agency_key in committee_patterns.items():
                if agency_name in query:
                    params["committee_type"] = agency_key
                    break
        
        # 특별행정심판원 매칭
        elif search_type == "special_appeal":
            for agency_name, agency_key in tribunal_patterns.items():
                if agency_name in query:
                    params["tribunal_type"] = agency_key
                    break
        
        # 부처 매칭 (법령해석/행정규칙 검색용)
        elif search_type in ["interpretation", "rule"]:
            for agency_name, agency_key in agency_patterns.items():
                if agency_name in query:
                    params["agency"] = agency_key
                    break
        
        # 지방자치단체 매칭 (자치법규 검색용)
        elif search_type == "ordinance":
            # 주요 지방자치단체명 패턴
            local_gov_patterns = {
                "서울": "서울특별시",
                "부산": "부산광역시",
                "대구": "대구광역시",
                "인천": "인천광역시",
                "광주": "광주광역시",
                "대전": "대전광역시",
                "울산": "울산광역시",
                "세종": "세종특별자치시",
                "경기": "경기도",
                "강원": "강원특별자치도",
                "충북": "충청북도",
                "충남": "충청남도",
                "전북": "전북특별자치도",
                "전남": "전라남도",
                "경북": "경상북도",
                "경남": "경상남도",
                "제주": "제주특별자치도",
            }
            
            for pattern, full_name in local_gov_patterns.items():
                if pattern in query:
                    params["local_government"] = full_name
                    break
        
        return params
    
    async def smart_search(
        self,
        query: str,
        search_types: Optional[List[str]] = None,
        max_results_per_type: int = 5,
        arguments: Optional[dict] = None
    ) -> Dict:
        """
        사용자 질문을 분석하여 적절한 검색을 자동으로 수행
        
        Args:
            query: 사용자 질문
            search_types: 강제로 검색할 타입 목록 (None이면 자동 분석)
            max_results_per_type: 타입당 최대 결과 수
            arguments: 추가 인자 (API 키 등)
            
        Returns:
            통합 검색 결과
        """
        import asyncio
        
        # 의도 분석
        clarification_needed = False
        possible_intents = []
        
        # 매우 모호한 질문인지 먼저 확인 (의도 분석 전에)
        query_stripped = query.strip()
        very_ambiguous_keywords = ["법", "법률", "정보", "찾아줘", "알려줘", "확인", "검색", "알려주세요", "찾아주세요"]
        very_ambiguous = (
            len(query_stripped) <= 3 or
            query_stripped in very_ambiguous_keywords
        )
        
        if very_ambiguous:
            clarification_needed = True
            possible_intents = [
                {"type": "law", "description": "법령 검색", "example": "형법 제250조"},
                {"type": "precedent", "description": "판례 검색", "example": "손해배상 판례"},
                {"type": "interpretation", "description": "법령해석 검색", "example": "개인정보보호법 해석"},
                {"type": "administrative_appeal", "description": "행정심판 검색", "example": "행정심판 사례"},
                {"type": "constitutional", "description": "헌재결정 검색", "example": "위헌 결정례"}
            ]
        
        if search_types is None and not clarification_needed:
            intent_results = self.analyze_intent(query)
            # 여러 의도 동시 감지: 신뢰도 0.3 이상인 모든 의도 포함
            # 예: "형법 제250조와 관련 판례" → ["law", "precedent"]
            search_types = [st for st, conf in intent_results if conf > 0.3]
            
            # 모호한 질문 처리: 의도가 명확하지 않으면 법령 검색 기본값
            if not search_types:
                # 매우 모호한 질문인 경우 clarification 필요
                # 단일 단어이거나 매우 짧은 질문인 경우
                query_stripped = query.strip()
                very_ambiguous_keywords = ["법", "법률", "정보", "찾아줘", "알려줘", "확인", "검색", "알려주세요", "찾아주세요"]
                very_ambiguous = (
                    len(query_stripped) <= 3 or
                    query_stripped in very_ambiguous_keywords
                )
                
                if very_ambiguous:
                    clarification_needed = True
                    # 가능한 의도 후보 생성
                    possible_intents = [
                        {"type": "law", "description": "법령 검색", "example": "형법 제250조"},
                        {"type": "precedent", "description": "판례 검색", "example": "손해배상 판례"},
                        {"type": "interpretation", "description": "법령해석 검색", "example": "개인정보보호법 해석"},
                        {"type": "administrative_appeal", "description": "행정심판 검색", "example": "행정심판 사례"},
                        {"type": "constitutional", "description": "헌재결정 검색", "example": "위헌 결정례"}
                    ]
                    # clarification이 필요한 경우 search_types를 설정하지 않음
                else:
                    # "관련" 같은 키워드가 있으면 법령 검색
                    # 단, "찾아줘", "알려줘" 같은 단독 키워드는 이미 very_ambiguous에서 처리됨
                    if "관련" in query:
                        search_types = ["law"]
                    else:
                        search_types = ["law"]  # 기본값
        
        # clarification이 필요한 경우 조기 반환 (search_types 설정 전에)
        if clarification_needed:
            return {
                "success": False,
                "clarification_needed": True,
                "query": query,
                "possible_intents": possible_intents,
                "suggestion": "더 구체적인 질문을 해주시면 정확한 정보를 찾아드릴 수 있습니다. 예: '형법 제250조', '손해배상 판례', '개인정보보호법 해석' 등"
            }
        
        # search_types가 없으면 기본값 설정
        if not search_types:
            search_types = ["law"]  # 기본값
        
        # 파라미터 추출
        all_params = {}
        for st in search_types:
            params = self.extract_parameters(query, st)
            all_params[st] = params
        
        # 병렬 검색 실행
        results = {}
        
        for search_type in search_types[:3]:  # 최대 3개 타입만 검색
            try:
                params = all_params.get(search_type, {"query": query})
                params["per_page"] = max_results_per_type
                params["page"] = 1
                
                if search_type == "law":
                    if "law_name" in params:
                        # get_law 시그니처: get_law(law_id=None, law_name=None, mode="detail", article_number=None, ...)
                        mode = "single" if "article_number" in params else "detail"
                        # 항, 호, 목 파라미터도 전달 (복잡한 파라미터 자동 추출 강화)
                        result = await asyncio.to_thread(
                            self.law_detail_repo.get_law,
                            None,  # law_id
                            params["law_name"],  # law_name
                            mode,  # mode
                            params.get("article_number"),  # article_number
                            params.get("hang"),  # hang (자동 추출)
                            params.get("ho"),  # ho (자동 추출)
                            params.get("mok"),  # mok (자동 추출)
                            arguments
                        )
                    else:
                        result = await asyncio.to_thread(
                            self.law_search_repo.search_law,
                            query,
                            1,
                            max_results_per_type,
                            arguments
                        )
                
                elif search_type == "precedent":
                    result = await asyncio.to_thread(
                        self.precedent_repo.search_precedent,
                        query,
                        1,
                        max_results_per_type,
                        None,
                        None,
                        None,
                        arguments
                    )
                
                elif search_type == "interpretation":
                    result = await asyncio.to_thread(
                        self.interpretation_repo.search_law_interpretation,
                        query,
                        1,
                        max_results_per_type,
                        params.get("agency"),  # 부처명 전달
                        arguments
                    )
                
                elif search_type == "administrative_appeal":
                    result = await asyncio.to_thread(
                        self.appeal_repo.search_administrative_appeal,
                        query,
                        1,
                        max_results_per_type,
                        None,
                        None,
                        arguments
                    )
                
                elif search_type == "constitutional":
                    result = await asyncio.to_thread(
                        self.constitutional_repo.search_constitutional_decision,
                        query,
                        1,
                        max_results_per_type,
                        None,
                        None,
                        arguments
                    )
                
                elif search_type == "committee" and "committee_type" in params:
                    result = await asyncio.to_thread(
                        self.committee_repo.search_committee_decision,
                        params["committee_type"],
                        query,
                        1,
                        max_results_per_type,
                        arguments
                    )
                
                elif search_type == "special_appeal" and "tribunal_type" in params:
                    result = await asyncio.to_thread(
                        self.special_appeal_repo.search_special_administrative_appeal,
                        params["tribunal_type"],
                        query,
                        1,
                        max_results_per_type,
                        arguments
                    )
                
                elif search_type == "ordinance":
                    result = await asyncio.to_thread(
                        self.ordinance_repo.search_local_ordinance,
                        query,
                        None,
                        1,
                        max_results_per_type,
                        arguments
                    )
                
                elif search_type == "rule":
                    result = await asyncio.to_thread(
                        self.rule_repo.search_administrative_rule,
                        query,
                        params.get("agency"),  # 부처명 전달
                        1,
                        max_results_per_type,
                        arguments
                    )
                
                elif search_type == "comparison" and "law_name" in params:
                    # 법령 비교는 law_name이 필요
                    compare_type = params.get("compare_type", "신구법")
                    result = await asyncio.to_thread(
                        self.comparison_repo.compare_laws,
                        params["law_name"],
                        compare_type,
                        arguments
                    )
                
                else:
                    continue
                
                # 결과가 있으면 추가
                if result:
                    # 에러가 없으면 무조건 추가
                    if "error" not in result:
                        results[search_type] = result
                    # 에러가 있어도 부분 결과가 있으면 추가
                    elif (result.get("laws") or result.get("precedents") or 
                          result.get("interpretations") or result.get("appeals") or 
                          result.get("decisions") or result.get("law_name") or 
                          result.get("law_id") or result.get("detail") or
                          result.get("precedent") or result.get("interpretation")):
                        results[search_type] = result
                    else:
                        # 에러만 있고 결과가 없으면 로깅만 하고 추가하지 않음
                        import logging
                        logger = logging.getLogger("lexguard-mcp")
                        logger.debug(f"Result for {search_type} has error and no data: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                import logging
                logger = logging.getLogger("lexguard-mcp")
                logger.exception(f"Error in smart_search for {search_type}: {e}")
                # 에러도 결과에 포함하여 디버깅 가능하게
                results[search_type] = {
                    "error": str(e),
                    "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
                }
        
        # 부분 실패 처리 개선
        successful_types = []
        failed_types = []
        partial_success = False
        
        for search_type, result in results.items():
            # result가 딕셔너리인지 확인
            if not isinstance(result, dict):
                continue
                
            # 에러가 없는 경우
            if "error" not in result:
                successful_types.append(search_type)
            else:
                # 에러가 있지만 부분 결과가 있는지 확인
                has_partial_data = False
                
                # 다양한 결과 필드 확인
                data_fields = [
                    "laws", "precedents", "interpretations", "appeals", "decisions",
                    "law_name", "law_id", "detail", "precedent", "interpretation",
                    "total", "count", "items", "data"
                ]
                
                for field in data_fields:
                    if field in result and result[field]:
                        has_partial_data = True
                        break
                
                # 리스트나 딕셔너리 타입의 결과 확인
                if not has_partial_data:
                    for key, value in result.items():
                        if key != "error" and key != "recovery_guide":
                            if isinstance(value, (list, dict)) and len(value) > 0:
                                has_partial_data = True
                                break
                            elif value and not isinstance(value, str):
                                has_partial_data = True
                                break
                
                if has_partial_data:
                    partial_success = True
                    successful_types.append(search_type)
                else:
                    failed_types.append(search_type)
        
        response = {
            "query": query,
            "detected_intents": search_types,
            "results": results,
            "total_types": len(results),
            "successful_types": successful_types,
            "failed_types": failed_types if failed_types else None,
            "partial_success": partial_success or (successful_types and failed_types)
        }
        
        # 안내 메시지 추가
        if partial_success or (successful_types and failed_types):
            if failed_types:
                response["note"] = f"일부 검색 타입({', '.join(failed_types)})에서 오류가 발생했지만, 다른 타입({', '.join(successful_types)})에서는 결과를 찾았습니다."
            else:
                response["note"] = f"모든 검색 타입({', '.join(successful_types)})에서 결과를 찾았습니다."
        elif successful_types and not failed_types:
            response["note"] = f"모든 검색 타입({', '.join(successful_types)})에서 성공적으로 결과를 찾았습니다."
        elif not successful_types and failed_types:
            response["note"] = f"모든 검색 타입({', '.join(failed_types)})에서 오류가 발생했습니다."
        
        return response

