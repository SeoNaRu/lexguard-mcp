"""
Law Interpretation Repository - 법령해석 검색 및 조회 기능
"""
import httpx
from ..utils.http_client import aget
import json
from typing import Optional
from .base import (
    BaseLawRepository,
    logger,
    LAW_API_SEARCH_URL,
    LAW_API_BASE_URL,
    search_cache,
    failure_cache,
    DRF_REQUEST_TIMEOUT_SEC,
)


class LawInterpretationRepository(BaseLawRepository):
    """법령해석 검색 및 조회 관련 기능을 담당하는 Repository.

    부처별 법령해석(CgmExpc) 39개 target을 AGENCY_TARGET_MAP을 통해 지원합니다.
    agency 파라미터가 map에 있으면 해당 부처 전용 target을 사용하고,
    없으면 법제처 통합 해석 target=expc를 사용합니다.
    """

    # 한국어 부처명 → DRF target 코드 (39개 부처별 법령해석)
    AGENCY_TARGET_MAP: dict = {
        "고용노동부": "moelCgmExpc",
        "국토교통부": "molitCgmExpc",
        "기획재정부": "moefCgmExpc",
        "해양수산부": "mofCgmExpc",
        "행정안전부": "moisCgmExpc",
        "기후에너지환경부": "meCgmExpc",
        "관세청": "kcsCgmExpc",
        "국세청": "ntsCgmExpc",
        "교육부": "moeCgmExpc",
        "과학기술정보통신부": "msitCgmExpc",
        "국가보훈부": "mpvaCgmExpc",
        "국방부": "mndCgmExpc",
        "농림축산식품부": "mafraCgmExpc",
        "문화체육관광부": "mcstCgmExpc",
        "법무부": "mojCgmExpc",
        "보건복지부": "mohwCgmExpc",
        "산업통상자원부": "motieCgmExpc",
        "성평등가족부": "mogefCgmExpc",
        "외교부": "mofaCgmExpc",
        "중소벤처기업부": "mssCgmExpc",
        "통일부": "mouCgmExpc",
        "법제처": "molegCgmExpc",
        "식품의약품안전처": "mfdsCgmExpc",
        "인사혁신처": "mpmCgmExpc",
        "기상청": "kmaCgmExpc",
        "국가유산청": "khsCgmExpc",
        "농촌진흥청": "rdaCgmExpc",
        "경찰청": "npaCgmExpc",
        "방위사업청": "dapaCgmExpc",
        "병무청": "mmaCgmExpc",
        "산림청": "kfsCgmExpc",
        "소방청": "nfaCgmExpc",
        "재외동포청": "okaCgmExpc",
        "조달청": "ppsCgmExpc",
        "질병관리청": "kdcaCgmExpc",
        "국가데이터처": "kostatCgmExpc",
        "지식재산처": "kipoCgmExpc",
        "해양경찰청": "kcgCgmExpc",
        "행정중심복합도시건설청": "naaccCgmExpc",
    }

    async def search_law_interpretation(
        self,
        query: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        agency: Optional[str] = None,
        arguments: Optional[dict] = None
    ) -> dict:
        """
        법령해석을 검색합니다.

        Args:
            query: 검색어 (법령해석명 또는 키워드)
            page: 페이지 번호 (기본값: 1)
            per_page: 페이지당 결과 수 (기본값: 20, 최대: 100)
            agency: 부처명 (예: '고용노동부', '국세청')
            arguments: 추가 인자 (API 키 등)

        Returns:
            검색 결과 딕셔너리 또는 {"error": "error message"}
        """
        logger.debug("search_law_interpretation called | query=%r page=%d per_page=%d agency=%r",
                    query, page, per_page, agency)

        if per_page < 1:
            per_page = 1
        if per_page > 100:
            per_page = 100

        cache_key = ("law_interpretation", query or "", page, per_page, agency or "")

        if cache_key in search_cache:
            logger.debug("Cache hit for law interpretation search")
            return search_cache[cache_key]

        if cache_key in failure_cache:
            logger.debug("Failure cache hit, skipping")
            return failure_cache[cache_key]

        try:
            # 부처명에 맞는 target 코드 결정
            target = self.AGENCY_TARGET_MAP.get(agency or "", "expc")

            params = {
                "target": target,
                "type": "JSON",
                "page": page,
                "display": per_page
            }

            if query:
                params["query"] = self.normalize_search_query(query)

            _, api_key_error = self.attach_api_key(params, arguments, LAW_API_SEARCH_URL)
            if api_key_error:
                return api_key_error

            response = await aget(LAW_API_SEARCH_URL, params=params, timeout=DRF_REQUEST_TIMEOUT_SEC)

            invalid_response = self.validate_drf_response(response)
            if invalid_response:
                return invalid_response
            response.raise_for_status()

            try:
                data = response.json()
            except json.JSONDecodeError as e:
                error_msg = f"API 응답이 유효한 JSON 형식이 아닙니다: {str(e)}"
                logger.error("Invalid JSON response | error=%s", str(e))
                return {
                    "error": error_msg,
                    "query": query,
                    "api_url": response.url,
                    "raw_response": response.text[:500],
                    "recovery_guide": "API 응답 형식 오류입니다. API 서버 상태를 확인하거나 잠시 후 다시 시도하세요."
                }

            result = {
                "query": query,
                "page": page,
                "per_page": per_page,
                "agency": agency,
                "total": 0,
                "interpretations": [],
                "api_url": response.url
            }

            # JSON 구조 파싱
            if isinstance(data, dict):
                if "ExpcSearch" in data:
                    expc_search = data["ExpcSearch"]
                    if isinstance(expc_search, dict):
                        result["total"] = expc_search.get("totalCnt", 0)
                        interpretations = expc_search.get("expc", [])
                    else:
                        interpretations = []
                elif "expc" in data:
                    result["total"] = data.get("totalCnt", 0)
                    interpretations = data.get("expc", [])
                else:
                    result["total"] = data.get("totalCnt", 0)
                    interpretations = data.get("expc", [])

                if not isinstance(interpretations, list):
                    interpretations = [interpretations] if interpretations else []

                result["interpretations"] = interpretations[:per_page]

            if result["total"] == 0:
                result["message"] = "검색 결과가 없습니다."

            search_cache[cache_key] = result
            logger.debug("API call successful for law interpretation search | total=%d", result["total"])

            return result

        except httpx.TimeoutException:
            error_msg = "API 호출 타임아웃"
            logger.error(error_msg)
            error_result = {
                "error_code": "API_ERROR_TIMEOUT",
                "missing_reason": "API_ERROR_TIMEOUT",
                "error": error_msg,
                "recovery_guide": "네트워크 응답 시간이 초과되었습니다. 잠시 후 다시 시도하거나, 인터넷 연결을 확인하세요."
            }
            failure_cache[cache_key] = error_result
            return error_result
        except httpx.RequestError as e:
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

    async def get_law_interpretation(
        self,
        interpretation_id: str,
        agency: Optional[str] = None,
        arguments: Optional[dict] = None
    ) -> dict:
        """
        법령해석 상세 정보를 조회합니다.

        Args:
            interpretation_id: 법령해석 일련번호
            arguments: 추가 인자 (API 키 등)

        Returns:
            법령해석 상세 정보 딕셔너리 또는 {"error": "error message"}
        """
        logger.debug("get_law_interpretation called | interpretation_id=%r", interpretation_id)

        cache_key = ("law_interpretation_detail", interpretation_id)

        if cache_key in search_cache:
            logger.debug("Cache hit for law interpretation detail")
            return search_cache[cache_key]

        if cache_key in failure_cache:
            logger.debug("Failure cache hit, skipping")
            return failure_cache[cache_key]

        try:
            target = self.AGENCY_TARGET_MAP.get(agency or "", "expc")
            params = {
                "target": target,
                "type": "JSON",
                "ID": interpretation_id
            }

            _, api_key_error = self.attach_api_key(params, arguments, LAW_API_BASE_URL)
            if api_key_error:
                return api_key_error

            response = await aget(LAW_API_BASE_URL, params=params, timeout=DRF_REQUEST_TIMEOUT_SEC)

            invalid_response = self.validate_drf_response(response)
            if invalid_response:
                return invalid_response
            response.raise_for_status()

            try:
                data = response.json()
            except json.JSONDecodeError as e:
                error_msg = f"API 응답이 유효한 JSON 형식이 아닙니다: {str(e)}"
                logger.error("Invalid JSON response | error=%s", str(e))
                return {
                    "error": error_msg,
                    "interpretation_id": interpretation_id,
                    "api_url": response.url
                }

            result = {
                "interpretation_id": interpretation_id,
                "interpretation": data,
                "api_url": response.url
            }

            search_cache[cache_key] = result
            logger.debug("API call successful for law interpretation detail")

            return result

        except httpx.TimeoutException:
            error_msg = "API 호출 타임아웃"
            logger.error(error_msg)
            error_result = {
                "error_code": "API_ERROR_TIMEOUT",
                "missing_reason": "API_ERROR_TIMEOUT",
                "error": error_msg,
                "interpretation_id": interpretation_id,
                "recovery_guide": "네트워크 응답 시간이 초과되었습니다. 잠시 후 다시 시도하거나, 인터넷 연결을 확인하세요."
            }
            failure_cache[cache_key] = error_result
            return error_result
        except httpx.RequestError as e:
            error_msg = f"API 요청 실패: {str(e)}"
            logger.error(error_msg)
            error_result = {"error": error_msg, "interpretation_id": interpretation_id}
            failure_cache[cache_key] = error_result
            return error_result
        except Exception as e:
            error_msg = f"예상치 못한 오류: {str(e)}"
            logger.exception(error_msg)
            return {
                "error": error_msg,
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }

