"""
Precedent Repository - 판례 검색 및 조회 기능
"""
import requests
import json
from typing import Optional, List, Dict, Tuple
from .base import BaseLawRepository, logger, LAW_API_SEARCH_URL, LAW_API_BASE_URL, search_cache, failure_cache
from ..utils.query_planner import extract_keywords, expand_synonyms, build_query_set, expand_date_range_stepwise
from ..utils.result_normalizer import normalize_search_response
from ..utils.retry_policy import RetryPolicy, ResultQuality
from ..utils.domain_classifier import get_domain_classifier
from ..utils.reranker import get_reranker
from ..utils.evidence_builder import get_evidence_builder
from ..utils.query_telemetry import get_telemetry


class PrecedentRepository(BaseLawRepository):
    """판례 검색 및 조회 관련 기능을 담당하는 Repository"""
    
    def search_precedent(
        self,
        query: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        court: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        arguments: Optional[dict] = None
    ) -> dict:
        """
        판례를 검색합니다.
        
        Args:
            query: 검색어 (판례명 또는 키워드)
            page: 페이지 번호 (기본값: 1)
            per_page: 페이지당 결과 수 (기본값: 20, 최대: 100)
            court: 법원 종류 (대법원:400201, 하위법원:400202)
            date_from: 시작일자 (YYYYMMDD)
            date_to: 종료일자 (YYYYMMDD)
            arguments: 추가 인자 (API 키 등)
            
        Returns:
            검색 결과 딕셔너리 또는 {"error": "error message"}
        """
        logger.debug("search_precedent called | query=%r page=%d per_page=%d", query, page, per_page)
        
        if per_page < 1:
            per_page = 1
        if per_page > 100:
            per_page = 100
        
        cache_key = ("precedent", query or "", page, per_page, court or "", date_from or "", date_to or "")
        
        if cache_key in search_cache:
            logger.debug("Cache hit for precedent search")
            return search_cache[cache_key]
        
        if cache_key in failure_cache:
            logger.debug("Failure cache hit, skipping")
            return failure_cache[cache_key]
        
        api_key = self.get_api_key(arguments)
        
        try:
            params = {
                "target": "prec",
                "type": "JSON",
                "page": page,
                "display": per_page
            }
            
            if query:
                params["query"] = self.normalize_search_query(query)
            
            if court:
                params["org"] = court
            
            if date_from and date_to:
                params["prncYd"] = f"{date_from}~{date_to}"
            elif date_from:
                params["prncYd"] = f"{date_from}~{date_from}"
            elif date_to:
                params["prncYd"] = f"{date_to}~{date_to}"
            
            if api_key:
                params["OC"] = api_key
            
            response = requests.get(LAW_API_SEARCH_URL, params=params, timeout=10)
            response.raise_for_status()
            
            if response.text.strip().startswith('<!DOCTYPE') or '<html' in response.text.lower():
                error_msg = "API가 HTML 에러 페이지를 반환했습니다. API 키가 유효하지 않거나 API 사용 권한이 없을 수 있습니다."
                logger.error("API returned HTML error page")
                return {
                    "error": error_msg,
                    "query": query,
                    "api_url": response.url,
                    "note": "국가법령정보센터 OPEN API 사용을 위해서는 https://open.law.go.kr 에서 회원가입 및 API 활용 신청이 필요합니다.",
                    "recovery_guide": "API 키가 필요합니다. 사용자에게 API 키를 요청하거나, API 키를 환경변수(LAW_API_KEY)로 설정하세요."
                }
            
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                error_msg = f"API 응답이 유효한 JSON 형식이 아닙니다: {str(e)}"
                logger.error("Invalid JSON response | error=%s", str(e))
                return {
                    "error": error_msg,
                    "query": query,
                    "api_url": response.url,
                    "raw_response": response.text[:500]
                }
            
            result = {
                "query": query,
                "page": page,
                "per_page": per_page,
                "total": 0,
                "precedents": [],
                "api_url": response.url
            }
            
            # JSON 구조 파싱
            if isinstance(data, dict):
                if "PrecSearch" in data:
                    prec_search = data["PrecSearch"]
                    if isinstance(prec_search, dict):
                        result["total"] = prec_search.get("totalCnt", 0)
                        precedents = prec_search.get("prec", [])
                    else:
                        precedents = []
                elif "prec" in data:
                    result["total"] = data.get("totalCnt", 0)
                    precedents = data.get("prec", [])
                else:
                    result["total"] = data.get("totalCnt", 0)
                    precedents = data.get("prec", [])
                
                if not isinstance(precedents, list):
                    precedents = [precedents] if precedents else []
                
                result["precedents"] = precedents[:per_page]
            
            if result["total"] == 0:
                result["message"] = "검색 결과가 없습니다."
            
            search_cache[cache_key] = result
            logger.debug("API call successful for precedent search | total=%d", result["total"])
            
            return result
            
        except requests.exceptions.Timeout:
            error_msg = "API 호출 타임아웃"
            logger.error(error_msg)
            error_result = {
                "error": error_msg,
                "recovery_guide": "네트워크 응답 시간이 초과되었습니다. 잠시 후 다시 시도하거나, 인터넷 연결을 확인하세요."
            }
            failure_cache[cache_key] = error_result
            return error_result
        except requests.exceptions.RequestException as e:
            error_msg = f"API 요청 실패: {str(e)}"
            logger.error(error_msg)
            error_result = {
                "error": error_msg,
                "recovery_guide": "네트워크 오류입니다. 잠시 후 다시 시도하거나, 인터넷 연결을 확인하세요."
            }
            failure_cache[cache_key] = error_result
            return error_result
        except Exception as e:
            error_msg = f"예상치 못한 오류: {str(e)}"
            logger.exception(error_msg)
            return {
                "error": error_msg,
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }
    
    def _search_precedent_internal(
        self,
        query: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        court: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        arguments: Optional[dict] = None
    ) -> dict:
        """
        내부 검색 메서드 (캐시 체크 없이 직접 API 호출)
        """
        api_key = self.get_api_key(arguments)
        
        try:
            params = {
                "target": "prec",
                "type": "JSON",
                "page": page,
                "display": per_page
            }
            
            if query:
                params["query"] = self.normalize_search_query(query)
            
            if court:
                params["org"] = court
            
            if date_from and date_to:
                params["prncYd"] = f"{date_from}~{date_to}"
            elif date_from:
                params["prncYd"] = f"{date_from}~{date_from}"
            elif date_to:
                params["prncYd"] = f"{date_to}~{date_to}"
            
            if api_key:
                params["OC"] = api_key
            
            response = requests.get(LAW_API_SEARCH_URL, params=params, timeout=10)
            response.raise_for_status()
            
            if response.text.strip().startswith('<!DOCTYPE') or '<html' in response.text.lower():
                return {
                    "error": "API가 HTML 에러 페이지를 반환했습니다.",
                    "query": query,
                    "api_url": response.url
                }
            
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                return {
                    "error": f"API 응답이 유효한 JSON 형식이 아닙니다: {str(e)}",
                    "query": query,
                    "api_url": response.url
                }
            
            result = {
                "query": query,
                "page": page,
                "per_page": per_page,
                "total": 0,
                "precedents": [],
                "api_url": response.url
            }
            
            # JSON 구조 파싱
            if isinstance(data, dict):
                if "PrecSearch" in data:
                    prec_search = data["PrecSearch"]
                    if isinstance(prec_search, dict):
                        result["total"] = prec_search.get("totalCnt", 0)
                        precedents = prec_search.get("prec", [])
                    else:
                        precedents = []
                elif "prec" in data:
                    result["total"] = data.get("totalCnt", 0)
                    precedents = data.get("prec", [])
                else:
                    result["total"] = data.get("totalCnt", 0)
                    precedents = data.get("prec", [])
                
                if not isinstance(precedents, list):
                    precedents = [precedents] if precedents else []
                
                result["precedents"] = precedents[:per_page]
            
            return result
            
        except requests.exceptions.Timeout:
            return {
                "error": "API 호출 타임아웃",
                "query": query
            }
        except requests.exceptions.RequestException as e:
            return {
                "error": f"API 요청 실패: {str(e)}",
                "query": query
            }
        except Exception as e:
            return {
                "error": f"예상치 못한 오류: {str(e)}",
                "query": query
            }
    
    def search_precedent_with_fallback(
        self,
        query: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        court: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        arguments: Optional[dict] = None,
        issue_type: Optional[str] = None,
        must_include: Optional[List[str]] = None
    ) -> dict:
        """
        다단계 fallback 전략을 사용한 판례 검색
        
        Step A: 원본 쿼리 (기본 날짜 범위: 5년)
        Step B: 키워드 추출 + 동의어 확장
        Step C: 날짜 범위 확장 (5년 → 10년 → 전체)
        Step D: 부분일치 (키워드만)
        
        Returns:
            검색 결과 + attempts 정보 포함
        """
        attempts: List[Dict] = []
        best_result: Optional[dict] = None
        query_plan: List[Dict] = []
        
        # 기본 날짜 범위 설정 (5년)
        if not date_from and not date_to:
            from ..utils.query_planner import calculate_date_range
            date_from, date_to = calculate_date_range(5)
        
        original_query = query
        original_date_from = date_from
        original_date_to = date_to
        
        # 쿼리 세트 생성
        if query:
            query_plan = build_query_set(
                query,
                issue_type=issue_type,
                must_include=must_include
            )
        else:
            query_plan = [{"query": query, "strategy": "original", "priority": 1}]
        
        # Step A: 원본 쿼리로 검색 (5년 범위)
        if query:
            logger.debug("Step A: Original query | query=%r date_from=%r date_to=%r", 
                        query, date_from, date_to)
            result = self._search_precedent_internal(
                query, page, per_page, court, date_from, date_to, arguments
            )
            attempts.append({
                "step": "A",
                "query": query,
                "date_from": date_from,
                "date_to": date_to,
                "strategy": "original",
                "total": result.get("total", 0),
                "success": result.get("total", 0) > 0 and "error" not in result
            })
            
            if result.get("total", 0) > 0 and "error" not in result:
                best_result = result
                logger.debug("Step A succeeded | total=%d", result.get("total", 0))
                
                # Retry Policy로 품질 평가
                retry_policy = RetryPolicy()
                quality = retry_policy.evaluate_quality(
                    result.get("total", 0),
                    result.get("precedents", []),
                    query,
                    must_include
                )
                
                # 품질이 좋으면 바로 반환 (정규화/재랭킹 적용)
                if quality in [ResultQuality.EXCELLENT, ResultQuality.GOOD]:
                    return self._finalize_result(
                        best_result, query_plan, attempts, original_query,
                        issue_type, must_include, False
                    )
                # 품질이 낮으면 계속 fallback 진행
        
        # Step B: 쿼리 세트로 검색 (동의어 확장)
        for q_plan in query_plan[:5]:  # 상위 5개만 시도
            q = q_plan.get("query")
            if not q or q == original_query:
                continue
            
            logger.debug("Step B: Query set | query=%r strategy=%s", 
                        q, q_plan.get("strategy"))
            result = self._search_precedent_internal(
                q, page, per_page, court, date_from, date_to, arguments
            )
            attempts.append({
                "step": "B",
                "query": q,
                "date_from": date_from,
                "date_to": date_to,
                "strategy": q_plan.get("strategy", "unknown"),
                "total": result.get("total", 0),
                "success": result.get("total", 0) > 0 and "error" not in result
            })
            
            if result.get("total", 0) > 0 and "error" not in result:
                if not best_result or result.get("total", 0) > best_result.get("total", 0):
                    best_result = result
                    logger.debug("Step B succeeded | query=%r total=%d", q, result.get("total", 0))
        
        if best_result:
            return {
                **best_result,
                "query_plan": query_plan,
                "attempts": attempts,
                "best_result": best_result,
                "fallback_used": True
            }
        
        # Step C: 날짜 범위 확장 (5년 → 10년 → 전체)
        for step in [1, 2, 3]:  # 1=10년, 2=전체
            expanded_from, expanded_to = expand_date_range_stepwise(
                date_from, date_to, step
            )
            
            if expanded_from == date_from and expanded_to == date_to:
                continue  # 변화 없으면 스킵
            
            logger.debug("Step C: Date expansion | step=%d date_from=%r date_to=%r", 
                        step, expanded_from, expanded_to)
            
            # 원본 쿼리로 다시 시도
            if original_query:
                result = self._search_precedent_internal(
                    original_query, page, per_page, court, expanded_from, expanded_to, arguments
                )
                attempts.append({
                    "step": "C",
                    "query": original_query,
                    "date_from": expanded_from,
                    "date_to": expanded_to,
                    "strategy": f"date_expansion_step_{step}",
                    "total": result.get("total", 0),
                    "success": result.get("total", 0) > 0 and "error" not in result
                })
                
                if result.get("total", 0) > 0 and "error" not in result:
                    if not best_result or result.get("total", 0) > best_result.get("total", 0):
                        best_result = result
                        logger.debug("Step C succeeded | step=%d total=%d", step, result.get("total", 0))
                        break
        
        if best_result:
            return {
                **best_result,
                "query_plan": query_plan,
                "attempts": attempts,
                "best_result": best_result,
                "fallback_used": True
            }
        
        # Step D: 키워드만 추출해서 최소 1개라도 반환 시도
        if original_query:
            keywords = extract_keywords(original_query)
            if keywords:
                keyword_query = " ".join(keywords[:3])  # 상위 3개만
                logger.debug("Step D: Keyword only | query=%r", keyword_query)
                
                result = self._search_precedent_internal(
                    keyword_query, page, per_page, court, None, None, arguments  # 날짜 제한 없음
                )
                attempts.append({
                    "step": "D",
                    "query": keyword_query,
                    "date_from": None,
                    "date_to": None,
                    "strategy": "keyword_only",
                    "total": result.get("total", 0),
                    "success": result.get("total", 0) > 0 and "error" not in result
                })
                
                if result.get("total", 0) > 0 and "error" not in result:
                    best_result = result
                    logger.debug("Step D succeeded | total=%d", result.get("total", 0))
        
        # 최종 결과 반환 (0개여도 attempts 정보 포함)
        if best_result:
            return self._finalize_result(
                best_result, query_plan, attempts, original_query,
                issue_type, must_include, True
            )
        else:
            # 모든 시도 실패
            return {
                "query": original_query,
                "page": page,
                "per_page": per_page,
                "total": 0,
                "precedents": [],
                "normalized_results": [],
                "query_plan": query_plan,
                "attempts": attempts,
                "best_result": None,
                "fallback_used": True,
                "message": "모든 검색 시도가 실패했습니다."
            }
    
    def _finalize_result(
        self,
        best_result: dict,
        query_plan: List[Dict],
        attempts: List[Dict],
        original_query: Optional[str],
        issue_type: Optional[str],
        must_include: Optional[List[str]],
        fallback_used: bool
    ) -> dict:
        """
        최종 결과 정규화 및 후처리
        
        - Domain Classifier로 이슈 분류
        - Reranker로 재랭킹
        - Evidence Builder로 근거 추출
        - Result Normalizer로 정규화
        """
        # Domain Classifier로 이슈 분류
        domain_classifier = get_domain_classifier()
        classified_domains = []
        if original_query:
            classified_domains = domain_classifier.classify(original_query, max_domains=2)
            if classified_domains:
                primary_domain = classified_domains[0][0]
                if not issue_type:
                    issue_type = primary_domain
                    # 도메인 기반 must_include 추가
                    domain_must_include = domain_classifier.get_must_include_for_domain(primary_domain)
                    if domain_must_include:
                        must_include = (must_include or []) + domain_must_include
        
        # Reranker로 재랭킹
        reranker = get_reranker()
        precedents = best_result.get("precedents", [])
        if precedents:
            reranked = reranker.rerank(
                precedents,
                original_query or "",
                issue_type=issue_type,
                must_include=must_include,
                method="keyword_matching"
            )
            best_result["precedents"] = reranked
        
        # Evidence Builder로 근거 추출
        evidence_builder = get_evidence_builder()
        evidence_summary = evidence_builder.build_evidence_summary(
            best_result.get("precedents", [])[:5],  # 상위 5개만
            issue_type=issue_type,
            query=original_query,
            max_evidences=5
        )
        
        # Result Normalizer로 정규화
        normalized_response = normalize_search_response(best_result, result_type="precedent")
        
        # Telemetry 로깅
        telemetry = get_telemetry()
        telemetry.log_query(
            query=original_query or "",
            total=best_result.get("total", 0),
            attempts=len(attempts),
            fallback_used=fallback_used,
            issue_type=issue_type,
            classified_domains=[d[0] for d in classified_domains]
        )
        
        return {
            **normalized_response,
            "query_plan": query_plan,
            "attempts": attempts,
            "best_result": best_result,
            "fallback_used": fallback_used,
            "issue_type": issue_type,
            "classified_domains": [d[0] for d in classified_domains],
            "evidence_summary": evidence_summary
        }
    
    def get_precedent(
        self,
        precedent_id: Optional[str] = None,
        case_number: Optional[str] = None,
        arguments: Optional[dict] = None
    ) -> dict:
        """
        판례 상세 정보를 조회합니다.
        
        Args:
            precedent_id: 판례 일련번호
            case_number: 사건번호 (precedent_id와 둘 중 하나는 필수)
            arguments: 추가 인자 (API 키 등)
            
        Returns:
            판례 상세 정보 딕셔너리 또는 {"error": "error message"}
        """
        logger.debug("get_precedent called | precedent_id=%r case_number=%r", precedent_id, case_number)
        
        if not precedent_id and not case_number:
            return {
                "error": "precedent_id 또는 case_number 중 하나는 필수입니다.",
                "recovery_guide": "판례 일련번호(precedent_id) 또는 사건번호(case_number) 중 하나를 입력해주세요."
            }
        
        # case_number로 검색해서 precedent_id 찾기
        if case_number and not precedent_id:
            search_result = self.search_precedent(query=case_number, per_page=1, arguments=arguments)
            if "error" in search_result:
                return search_result
            
            precedents = search_result.get("precedents", [])
            if precedents and isinstance(precedents[0], dict):
                # 사건번호로 매칭
                for prec in precedents:
                    if prec.get("사건번호") == case_number or prec.get("사건번호", "").endswith(case_number):
                        precedent_id = (prec.get("판례정보일련번호") or 
                                       prec.get("일련번호") or
                                       prec.get("id"))
                        break
                
                if not precedent_id and precedents:
                    # 첫 번째 결과 사용
                    precedent_id = (precedents[0].get("판례정보일련번호") or 
                                   precedents[0].get("일련번호") or
                                   precedents[0].get("id"))
            
            if not precedent_id:
                return {
                    "error": "판례 ID를 찾을 수 없습니다.",
                    "case_number": case_number
                }
        
        cache_key = ("precedent_detail", precedent_id)
        
        if cache_key in search_cache:
            logger.debug("Cache hit for precedent detail")
            return search_cache[cache_key]
        
        if cache_key in failure_cache:
            logger.debug("Failure cache hit, skipping")
            return failure_cache[cache_key]
        
        api_key = self.get_api_key(arguments)
        
        try:
            params = {
                "target": "prec",
                "type": "JSON",
                "ID": precedent_id
            }
            
            if api_key:
                params["OC"] = api_key
            
            response = requests.get(LAW_API_BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            
            if response.text.strip().startswith('<!DOCTYPE') or '<html' in response.text.lower():
                error_msg = "API가 HTML 에러 페이지를 반환했습니다."
                logger.error("API returned HTML error page")
                return {
                    "error": error_msg,
                    "precedent_id": precedent_id,
                    "api_url": response.url
                }
            
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                error_msg = f"API 응답이 유효한 JSON 형식이 아닙니다: {str(e)}"
                logger.error("Invalid JSON response | error=%s", str(e))
                return {
                    "error": error_msg,
                    "precedent_id": precedent_id,
                    "api_url": response.url
                }
            
            result = {
                "precedent_id": precedent_id,
                "precedent": data,
                "api_url": response.url
            }
            
            search_cache[cache_key] = result
            logger.debug("API call successful for precedent detail")
            
            return result
            
        except requests.exceptions.Timeout:
            error_msg = "API 호출 타임아웃"
            logger.error(error_msg)
            error_result = {
                "error": error_msg,
                "precedent_id": precedent_id,
                "recovery_guide": "네트워크 응답 시간이 초과되었습니다. 잠시 후 다시 시도하거나, 인터넷 연결을 확인하세요."
            }
            failure_cache[cache_key] = error_result
            return error_result
        except requests.exceptions.RequestException as e:
            error_msg = f"API 요청 실패: {str(e)}"
            logger.error(error_msg)
            error_result = {"error": error_msg, "precedent_id": precedent_id}
            failure_cache[cache_key] = error_result
            return error_result
        except Exception as e:
            error_msg = f"예상치 못한 오류: {str(e)}"
            logger.exception(error_msg)
            return {
                "error": error_msg,
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }

