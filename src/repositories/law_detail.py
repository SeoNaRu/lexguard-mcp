"""
Law Detail Repository - 법령 조회 기능
"""
import httpx
from ..utils.http_client import aget
import json
from typing import Optional
from datetime import datetime
from .base import (
    BaseLawRepository,
    logger,
    LAW_API_BASE_URL,
    LAW_API_SEARCH_URL,
    DRF_REQUEST_TIMEOUT_SEC,
)


class LawDetailRepository(BaseLawRepository):
    """법령 조회 관련 기능을 담당하는 Repository"""

    # DRF API 필드명 후보 목록 (우선순위 순)
    FIELD_MAPPINGS = {
        "law_name": ["법령명한글", "lawNm", "법령명", "lawNmKo"],
        "law_id":   ["법령일련번호", "일련번호", "lawSeq", "lawId", "법령ID", "id"],
    }

    def _get_field(self, item: dict, field: str) -> Optional[str]:
        """FIELD_MAPPINGS 기준으로 item 딕셔너리에서 필드 값을 추출합니다."""
        for key in self.FIELD_MAPPINGS.get(field, []):
            val = item.get(key)
            if val:
                return str(val)
        return None

    def _find_law_item(self, laws: list, query: str) -> Optional[dict]:
        """법령 목록에서 query와 가장 잘 맞는 항목을 반환합니다.
        1순위: 정확 일치, 2순위: 부분 포함, 3순위: 첫 번째 항목.
        """
        if not laws:
            return None
        normalized_query = self.normalize_search_query(query)
        # 1순위: 정확 일치
        for item in laws:
            if isinstance(item, dict):
                item_name = self.normalize_search_query(self._get_field(item, "law_name") or "")
                if normalized_query == item_name:
                    return item
        # 2순위: 부분 포함
        for item in laws:
            if isinstance(item, dict):
                item_name = self.normalize_search_query(self._get_field(item, "law_name") or "")
                if normalized_query in item_name:
                    return item
        # 3순위: 첫 번째
        return laws[0] if isinstance(laws[0], dict) else None

    async def get_law_detail(self, law_name: str, arguments: Optional[dict] = None) -> dict:
        """
        법령 상세 정보를 조회합니다.

        Args:
            law_name: 법령명 (예: "119구조·구급에 관한 법률 시행령")
            arguments: 추가 인자 (API 키 등)

        Returns:
            법령 상세 정보 딕셔너리 또는 {"error": "error message"}
        """
        logger.debug("get_law_detail called | law_name=%r", law_name)

        if not law_name or not law_name.strip():
            error_msg = "법령명이 비어있습니다."
            logger.error(error_msg)
            return {
                "error": error_msg,
                "recovery_guide": "법령명을 입력해주세요. 예: '형법', '민법', '개인정보보호법'"
            }

        try:
            # lawSearch.do를 사용해서 법령 검색 (query 파라미터 사용)
            # 검색 결과에서 법령일련번호를 찾아서 상세 조회
            search_params = {
                "target": "law",
                "type": "JSON",
                "query": self.normalize_search_query(law_name),
                "page": 1,
                "display": 10  # 더 많은 결과를 받아서 정확한 매칭을 위해
            }

            _, api_key_error = self.attach_api_key(search_params, arguments, LAW_API_SEARCH_URL)
            if api_key_error:
                return api_key_error

            # 법령명 검색은 lawSearch.do 사용
            search_response = await aget(LAW_API_SEARCH_URL, params=search_params, timeout=DRF_REQUEST_TIMEOUT_SEC)

            invalid_response = self.validate_drf_response(search_response)
            if invalid_response:
                return invalid_response
            search_response.raise_for_status()

            # JSON에서 법령일련번호 추출
            law_id = None
            law_name_found = None

            try:
                search_data = search_response.json()
                if isinstance(search_data, dict):
                    # LawSearch 래퍼 확인
                    if "LawSearch" in search_data:
                        law_search = search_data["LawSearch"]
                        if isinstance(law_search, dict):
                            laws = law_search.get("law", [])
                        else:
                            laws = []
                    else:
                        laws = search_data.get("law", [])

                    if not isinstance(laws, list):
                        laws = [laws] if laws else []

                    law_item = self._find_law_item(laws, law_name)
                    if law_item:
                        law_id = self._get_field(law_item, "law_id")
                        law_name_found = self._get_field(law_item, "law_name")
            except json.JSONDecodeError as e:
                logger.warning("Failed to parse JSON for law search: %s", str(e))

            if not law_id:
                return {
                    "error": "법령 ID를 찾을 수 없습니다.",
                    "law_name": law_name,
                    "raw_response": search_response.text[:1000],
                    "recovery_guide": "법령명을 정확히 입력해주세요. 예: '형법', '민법', '개인정보보호법'. 법령명이 정확한지 확인하세요."
                }

            # law_id로 상세 정보 조회 (법령일련번호는 MST 파라미터로 사용)
            detail_params = {
                "target": "law",
                "type": "JSON",
                "MST": law_id
            }

            _, api_key_error = self.attach_api_key(detail_params, arguments, LAW_API_BASE_URL)
            if api_key_error:
                return api_key_error

            detail_response = await aget(LAW_API_BASE_URL, params=detail_params, timeout=DRF_REQUEST_TIMEOUT_SEC)

            invalid_response = self.validate_drf_response(detail_response)
            if invalid_response:
                return invalid_response
            detail_response.raise_for_status()

            # detail_response JSON에서 법령일련번호 재확인 (더 정확한 ID)
            detail_data = None
            try:
                detail_data = detail_response.json()
                if isinstance(detail_data, dict):
                    if "LawSearch" in detail_data:
                        law_search = detail_data["LawSearch"]
                        detail_law = law_search.get("법령") or law_search.get("law") if isinstance(law_search, dict) else None
                    else:
                        detail_law = detail_data.get("법령") or detail_data.get("law")

                    if isinstance(detail_law, dict):
                        detail_law_id = self._get_field(detail_law, "law_id")
                        if detail_law_id:
                            law_id = detail_law_id
                        if not law_name_found:
                            law_name_found = self._get_field(detail_law, "law_name")
            except json.JSONDecodeError as e:
                logger.warning("Failed to parse JSON for law detail: %s", str(e))

            return {
                "law_name": law_name_found or law_name,
                "law_id": law_id,
                "detail": json.dumps(detail_data, ensure_ascii=False, indent=2)[:2000] if detail_data else detail_response.text[:2000],
                "api_url": detail_response.url,
                "note": "전체 내용은 API URL에서 확인하세요."
                }

        except httpx.TimeoutException:
            return {
                "error": "API 호출 타임아웃",
                "law_name": law_name,
                "recovery_guide": "네트워크 응답 시간이 초과되었습니다. 잠시 후 다시 시도하거나, 인터넷 연결을 확인하세요."
            }
        except httpx.RequestError as e:
            return {
                "error": f"API 요청 실패: {str(e)}",
                "law_name": law_name
            }
        except Exception as e:
            return {
                "error": f"법령 상세 조회 중 오류: {str(e)}",
                "law_name": law_name
            }

    async def get_law_articles(self, law_id: Optional[str] = None, law_name: Optional[str] = None, arguments: Optional[dict] = None) -> dict:
        """
        특정 법령의 조문 전체를 조회합니다.

        Args:
            law_id: 법령 ID (lawService.do에 사용하는 ID, law_name과 둘 중 하나는 필수)
            law_name: 법령명 (예: "119구조·구급에 관한 법률 시행령", law_id와 둘 중 하나는 필수)
            arguments: 추가 인자 (API 키 등)

        Returns:
            조문 목록이 포함된 딕셔너리 또는 {"error": "error message"}
        """
        logger.debug("get_law_articles called | law_id=%r law_name=%r", law_id, law_name)

        # 법령명이 입력되면 검색해서 ID 찾기
        if law_name and not law_id:
            try:
                search_params = {
                    "target": "law",
                    "type": "JSON",
                    "query": self.normalize_search_query(law_name),
                    "page": 1,
                    "display": 10  # 더 많은 결과를 받아서 정확한 매칭을 위해
                }

                _, api_key_error = self.attach_api_key(search_params, arguments, LAW_API_SEARCH_URL)
                if api_key_error:
                    return api_key_error

                # 법령명 검색은 lawSearch.do 사용
                search_response = await aget(LAW_API_SEARCH_URL, params=search_params, timeout=DRF_REQUEST_TIMEOUT_SEC)

                invalid_response = self.validate_drf_response(search_response)
                if invalid_response:
                    return invalid_response
                search_response.raise_for_status()

                try:
                    search_data = search_response.json()
                    if isinstance(search_data, dict):
                        if "LawSearch" in search_data:
                            law_search = search_data["LawSearch"]
                            if isinstance(law_search, dict):
                                laws = law_search.get("law", [])
                            else:
                                laws = []
                        else:
                            laws = search_data.get("law", [])

                        if not isinstance(laws, list):
                            laws = [laws] if laws else []

                        law_item = self._find_law_item(laws, law_name)
                        if law_item:
                            law_id = self._get_field(law_item, "law_id")
                except json.JSONDecodeError as e:
                    logger.warning("Failed to parse JSON for law search: %s", str(e))

                if not law_id:
                    return {
                        "error": "법령 ID를 찾을 수 없습니다.",
                        "law_name": law_name,
                        "recovery_guide": "법령명을 정확히 입력해주세요. 예: '형법', '민법', '개인정보보호법'. 법령명이 정확한지 확인하세요."
                    }
            except httpx.TimeoutException:
                return {
                    "error": "법령 검색 타임아웃",
                    "law_name": law_name,
                    "recovery_guide": "네트워크 응답 시간이 초과되었습니다. 잠시 후 다시 시도하거나, 인터넷 연결을 확인하세요."
                }
            except httpx.RequestError as e:
                return {
                    "error": f"법령 검색 실패: {str(e)}",
                    "law_name": law_name,
                    "recovery_guide": "네트워크 오류입니다. 잠시 후 다시 시도하거나, 인터넷 연결을 확인하세요."
                }

        if not law_id or not law_id.strip():
            error_msg = "법령 ID 또는 법령명이 필요합니다."
            logger.error(error_msg)
            return {
                "error": error_msg,
                "recovery_guide": "법령 ID 또는 법령명 중 하나는 필수입니다. 예: law_name='형법' 또는 law_id='123456'"
            }

        try:
            # lawService.do API 호출 파라미터 설정
            params = {
                "target": "law",      # 법령 조회
                "type": "JSON",       # JSON 형식 응답
                "MST": law_id          # 법령일련번호는 MST로 사용
            }

            _, api_key_error = self.attach_api_key(params, arguments, LAW_API_BASE_URL)
            if api_key_error:
                return api_key_error

            # API 호출
            response = await aget(LAW_API_BASE_URL, params=params, timeout=DRF_REQUEST_TIMEOUT_SEC)

            invalid_response = self.validate_drf_response(response)
            if invalid_response:
                return invalid_response
            response.raise_for_status()

            # JSON 파싱 시작
            try:
                data = response.json()

                # 법령명 추출
                law_name = None
                law_obj = None

                # LawSearch 래퍼 확인
                if isinstance(data, dict):
                    if "LawSearch" in data:
                        law_search = data["LawSearch"]
                        if isinstance(law_search, dict):
                            law_obj = law_search.get("법령") or law_search.get("law")
                    else:
                        law_obj = data.get("법령") or data.get("law")

                if isinstance(law_obj, dict):
                    law_name = self._get_field(law_obj, "law_name")

                # 조문 목록 추출
                articles = []

                # JSON에서 조문 요소 찾기
                article_list = None
                if isinstance(law_obj, dict):
                    article_list = (law_obj.get("조문") or
                                   law_obj.get("article") or
                                   law_obj.get("articles") or
                                   law_obj.get("조") or
                                   law_obj.get("조문목록"))

                if article_list:
                    if not isinstance(article_list, list):
                        article_list = [article_list]

                    for article_item in article_list:
                        if isinstance(article_item, dict):
                            article_no = (article_item.get("조문번호") or
                                         article_item.get("articleNo") or
                                         article_item.get("조번호") or
                                         article_item.get("articleNum") or
                                         article_item.get("번호"))
                            article_title = (article_item.get("조문제목") or
                                            article_item.get("articleTitle") or
                                            article_item.get("제목") or
                                            article_item.get("title"))
                            article_content = (article_item.get("조문내용") or
                                             article_item.get("articleContent") or
                                             article_item.get("내용") or
                                             article_item.get("content") or
                                             article_item.get("조문") or
                                             article_item.get("text"))

                            # 조문 정보가 하나라도 있으면 추가
                            if article_no or article_content:
                                articles.append({
                                    "article_no": article_no or "번호 없음",
                                    "title": article_title,
                                    "content": article_content or ""
                                })

                result = {
                    "law_id": law_id,
                    "law_name": law_name or "법령명 없음",
                    "articles": articles,
                    "article_count": len(articles),
                    "api_url": response.url
                }

                logger.debug("Successfully parsed law articles | law_id=%s count=%d", law_id, len(articles))
                return result

            except json.JSONDecodeError as e:
                logger.warning("Failed to parse JSON for law articles: %s", str(e))
                # JSON 파싱 실패 시 원본 응답 일부 반환
                return {
                    "error": "JSON 파싱 실패",
                    "law_id": law_id,
                    "raw_response": response.text[:1000],
                    "api_url": response.url,
                    "recovery_guide": "API 응답 형식 오류입니다. API 서버 상태를 확인하거나 잠시 후 다시 시도하세요.",
                    "note": "API 응답 형식이 예상과 다를 수 있습니다."
                }

        except httpx.TimeoutException:
            error_msg = "API 호출 타임아웃"
            logger.error(error_msg)
            return {
                "error": error_msg,
                "law_id": law_id,
                "recovery_guide": "네트워크 응답 시간이 초과되었습니다. 잠시 후 다시 시도하거나, 인터넷 연결을 확인하세요."
            }
        except httpx.RequestError as e:
            error_msg = f"API 요청 실패: {str(e)}"
            logger.error(error_msg)
            return {
                "error": error_msg,
                "law_id": law_id,
                "recovery_guide": "네트워크 오류입니다. 잠시 후 다시 시도하거나, 인터넷 연결을 확인하세요."
            }
        except Exception as e:
            error_msg = f"예상치 못한 오류: {str(e)}"
            logger.exception(error_msg)
            return {
                "error": error_msg,
                "law_id": law_id,
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }

    async def get_single_article(self, law_id: str, article_number: str, hang: Optional[str] = None,
                          ho: Optional[str] = None, mok: Optional[str] = None,
                          arguments: Optional[dict] = None) -> dict:
        """
        특정 법령의 단일 조문을 조회합니다.

        Args:
            law_id: 법령 ID
            article_number: 조 번호 (예: '제1조', '제10조의2')
            hang: 항 번호 (예: '제1항', '제2항') - 선택사항
            ho: 호 번호 (예: '제2호', '제10호의2') - 선택사항
            mok: 목 (예: '가', '나', '다') - 선택사항
            arguments: 추가 인자 (API 키 등)

        Returns:
            조문 내용 딕셔너리 또는 {"error": "error message"}
        """
        logger.debug("get_single_article called | law_id=%s article_number=%s hang=%s ho=%s mok=%s",
                    law_id, article_number, hang, ho, mok)

        if not law_id or not law_id.strip():
            error_msg = "법령 ID가 비어있습니다."
            logger.error(error_msg)
            return {
                "error": error_msg,
                "recovery_guide": "법령 ID를 입력해주세요. 법령명으로 검색하여 법령 ID를 먼저 확인하세요."
            }

        if not article_number or not article_number.strip():
            error_msg = "조 번호가 비어있습니다."
            logger.error(error_msg)
            return {
                "error": error_msg,
                "recovery_guide": "단일 조문 조회 시 조 번호를 입력해주세요. 예: article_number='제1조' 또는 '1'"
            }

        try:
            # 1단계: 법령 상세 정보를 가져와서 시행일자(efYd) 확인
            detail_params = {
                "target": "law",
                "type": "JSON",
                "MST": law_id  # 법령일련번호는 MST로 사용
            }

            _, api_key_error = self.attach_api_key(detail_params, arguments, LAW_API_BASE_URL)
            if api_key_error:
                return api_key_error

            detail_response = await aget(LAW_API_BASE_URL, params=detail_params, timeout=DRF_REQUEST_TIMEOUT_SEC)

            invalid_detail = self.validate_drf_response(detail_response)
            if invalid_detail:
                return invalid_detail
            detail_response.raise_for_status()

            detail_data = detail_response.json()

            # 시행일자(efYd) 추출
            ef_yd = None
            if isinstance(detail_data, dict):
                # 다양한 키 이름으로 시행일자 찾기
                ef_yd = (detail_data.get("시행일자") or
                        detail_data.get("efYd") or
                        detail_data.get("시행일") or
                        detail_data.get("enforcementDate"))

                # 법령 정보에서 시행일자 찾기
                if not ef_yd:
                    law_info = detail_data.get("법령정보") or detail_data.get("lawInfo") or detail_data.get("법령")
                    if isinstance(law_info, dict):
                        ef_yd = (law_info.get("시행일자") or
                                law_info.get("efYd") or
                                law_info.get("시행일"))
                        if not ef_yd:
                            basic_info = law_info.get("기본정보") or law_info.get("basicInfo")
                            if isinstance(basic_info, dict):
                                ef_yd = (basic_info.get("시행일자") or
                                        basic_info.get("efYd") or
                                        basic_info.get("시행일") or
                                        basic_info.get("enforcementDate"))

            # 시행일자가 없으면 오늘 날짜 사용 (YYYYMMDD 형식)
            if not ef_yd:
                ef_yd = datetime.now().strftime("%Y%m%d")
                logger.warning("시행일자를 찾을 수 없어 오늘 날짜를 사용합니다: %s", ef_yd)

            # 2단계: 조문 조회 파라미터 구성
            # 조 번호를 6자리 숫자로 변환
            jo_number = self.parse_article_number(article_number)

            params = {
                "target": "eflawjosub",  # 단일 조문 조회용 target
                "type": "JSON",
                "MST": law_id,  # 법령일련번호는 MST로 사용
                "efYd": ef_yd,
                "JO": jo_number
            }

            # 항 번호 변환 및 추가
            if hang:
                hang_number = self.parse_article_number(hang)
                if hang_number != "000000":
                    params["HANG"] = hang_number

            # 호 번호 변환 및 추가
            if ho:
                ho_number = self.parse_article_number(ho)
                if ho_number != "000000":
                    params["HO"] = ho_number

            # 목 추가
            if mok:
                mok_char = self.parse_mok(mok)
                if mok_char:
                    params["MOK"] = mok_char

            _, api_key_error = self.attach_api_key(params, arguments, LAW_API_BASE_URL)
            if api_key_error:
                return api_key_error

            logger.debug("Calling eflawjosub API | params=%s", {k: v for k, v in params.items() if k != "OC"})

            # 3단계: 단일 조문 조회
            response = await aget(LAW_API_BASE_URL, params=params, timeout=DRF_REQUEST_TIMEOUT_SEC)

            invalid_response = self.validate_drf_response(response)
            if invalid_response:
                return invalid_response
            response.raise_for_status()

            # JSON 파싱
            try:
                data = response.json()

                # 조문 내용 추출
                article_content = None
                article_title = None

                if isinstance(data, dict):
                    # 다양한 키 이름으로 조문 내용 찾기
                    article_content = (data.get("조문내용") or
                                     data.get("articleContent") or
                                     data.get("내용") or
                                     data.get("content") or
                                     data.get("조문") or
                                     data.get("text"))

                    article_title = (data.get("조문제목") or
                                   data.get("articleTitle") or
                                   data.get("제목") or
                                   data.get("title"))

                    # 중첩된 구조에서 찾기
                if not article_content:
                    sub_data = data.get("조문정보") or data.get("articleInfo") or data.get("조문")
                    if isinstance(sub_data, dict):
                            article_content = (sub_data.get("조문내용") or
                                             sub_data.get("articleContent") or
                                             sub_data.get("내용") or
                                             sub_data.get("content"))
                            article_title = (sub_data.get("조문제목") or
                                           sub_data.get("articleTitle") or
                                           sub_data.get("제목"))

                fallback_mode = None
                fallback_source = None
                if not (article_content and str(article_content).strip()):
                    from ..utils.eflawjosub_fallback import atry_recover_article_text
                    recovered, src_url, fb_mode = await atry_recover_article_text(LAW_API_BASE_URL, params)
                    if recovered:
                        article_content = recovered
                        fallback_mode = fb_mode
                        fallback_source = src_url
                        logger.info(
                            "eflawjosub empty JSON; fallback ok | mode=%s law_id=%s jo=%s",
                            fb_mode, law_id, jo_number,
                        )

                result = {
                    "law_id": law_id,
                    "article_number": article_number,
                    "hang": hang,
                    "ho": ho,
                    "mok": mok,
                    "title": article_title or f"{article_number}" + (f" {hang}" if hang else "") + (f" {ho}" if ho else "") + (f" {mok}" if mok else ""),
                    "content": article_content or "조문 내용을 찾을 수 없습니다.",
                    "api_url": response.url
                }

                if fallback_mode and fallback_mode != "none":
                    result["fallback"] = {
                        "mode": fallback_mode,
                        "source_url": fallback_source,
                        "note": "eflawjosub JSON이 비어 있어 HTML 또는 Playwright 폴백으로 본문을 보완했습니다. 운영 환경에서는 약관·리소스 사용을 확인하세요.",
                    }

                if not (article_content and str(article_content).strip()):
                    result["note"] = "조문 내용이 비어있거나 찾을 수 없습니다. API 응답을 확인하세요."
                    result["raw_data"] = str(data)[:500]  # 디버깅용

                logger.debug("Successfully retrieved single article | law_id=%s article=%s", law_id, article_number)
                return result

            except json.JSONDecodeError as e:
                logger.warning("Failed to parse JSON for single article: %s", str(e))
                return {
                    "error": "JSON 파싱 실패",
                    "law_id": law_id,
                    "article_number": article_number,
                    "raw_response": response.text[:1000],
                    "api_url": response.url
                }

        except httpx.TimeoutException:
            error_msg = "API 호출 타임아웃"
            logger.error(error_msg)
            return {
                "error": error_msg,
                "law_id": law_id,
                "article_number": article_number,
                "recovery_guide": "네트워크 응답 시간이 초과되었습니다. 잠시 후 다시 시도하거나, 인터넷 연결을 확인하세요."
            }
        except httpx.RequestError as e:
            error_msg = f"API 요청 실패: {str(e)}"
            logger.error(error_msg)
            return {
                "error": error_msg,
                "law_id": law_id,
                "article_number": article_number,
                "recovery_guide": "네트워크 오류입니다. 잠시 후 다시 시도하거나, 인터넷 연결을 확인하세요."
            }
        except Exception as e:
            error_msg = f"예상치 못한 오류: {str(e)}"
            logger.exception(error_msg)
            return {
                "error": error_msg,
                "law_id": law_id,
                "article_number": article_number,
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }

    async def get_law(self, law_id: Optional[str] = None, law_name: Optional[str] = None,
                mode: str = "detail", article_number: Optional[str] = None,
                hang: Optional[str] = None, ho: Optional[str] = None,
                mok: Optional[str] = None, arguments: Optional[dict] = None) -> dict:
        """
        법령 조회 (통합: 상세 + 조문 + 단일 조문).

        Args:
            law_id: 법령 ID (law_name과 둘 중 하나는 필수)
            law_name: 법령명 (law_id와 둘 중 하나는 필수)
            mode: 조회 모드 - "detail"(상세정보), "articles"(전체 조문), "single"(단일 조문)
            article_number: 조 번호 (mode="single"일 때 필수)
            hang: 항 번호 (mode="single"일 때 선택사항)
            ho: 호 번호 (mode="single"일 때 선택사항)
            mok: 목 (mode="single"일 때 선택사항)
            arguments: 추가 인자 (API 키 등)

        Returns:
            법령 정보 딕셔너리 또는 {"error": "error message"}
        """
        logger.debug("get_law called | law_id=%s law_name=%s mode=%s", law_id, law_name, mode)

        # law_id 또는 law_name 중 하나는 필수
        if not law_id and not law_name:
            error_msg = "law_id 또는 law_name 중 하나는 필수입니다."
            logger.error(error_msg)
            return {
                "error": error_msg,
                "recovery_guide": "법령 ID 또는 법령명 중 하나를 입력해주세요. 예: law_name='형법' 또는 law_id='123456'"
            }

        # mode에 따라 분기
        if mode == "detail":
            # 상세 정보 조회
            if not law_name:
                # law_id만 있으면 먼저 법령명을 찾아야 함
                # 간단하게 get_law_articles를 호출하여 법령명 추출
                articles_result = await self.get_law_articles(law_id, None, arguments)
                if "error" in articles_result:
                    return articles_result
                # articles_result에서 법령명 추출 시도
                law_name_from_result = articles_result.get("law_name") or articles_result.get("법령명")
                if law_name_from_result:
                    return await self.get_law_detail(law_name_from_result, arguments)
                else:
                    return {
                        "error": "법령명을 찾을 수 없습니다. law_name을 제공해주세요.",
                        "recovery_guide": "법령명을 입력해주세요. 예: law_name='형법', '민법', '개인정보보호법'"
                    }
            return await self.get_law_detail(law_name, arguments)

        elif mode == "articles":
            # 전체 조문 조회
            return await self.get_law_articles(law_id, law_name, arguments)

        elif mode == "single":
            # 단일 조문 조회
            if not law_id:
                # law_name만 있으면 먼저 law_id를 찾아야 함
                detail_result = await self.get_law_detail(law_name, arguments)
                if "error" in detail_result:
                    return detail_result
                # detail_result에서 law_id 추출 시도
                law_id_from_result = (detail_result.get("law_id") or
                                     detail_result.get("법령일련번호") or
                                     detail_result.get("일련번호"))
                if law_id_from_result:
                    law_id = str(law_id_from_result)
                else:
                    return {
                        "error": "법령 ID를 찾을 수 없습니다. law_id를 제공해주세요.",
                        "recovery_guide": "법령 ID를 입력해주세요. 또는 law_name을 제공하여 법령 ID를 자동으로 찾을 수 있습니다."
                    }

            if not article_number:
                return {
                    "error": "mode='single'일 때 article_number는 필수입니다.",
                    "recovery_guide": "단일 조문 조회 시 조 번호를 입력해주세요. 예: article_number='제1조' 또는 '1'"
                }

            return await self.get_single_article(law_id, article_number, hang, ho, mok, arguments)

        else:
            error_msg = f"유효하지 않은 mode: {mode}. 'detail', 'articles', 'single' 중 하나를 선택하세요."
            logger.error(error_msg)
            return {
                "error": error_msg,
                "recovery_guide": "법령 조회 중 오류가 발생했습니다. 법령명이나 법령 ID를 확인하거나 잠시 후 다시 시도하세요."
            }

