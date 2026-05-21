"""
Local Ordinance Repository - 자치법규 검색 기능
"""
import httpx
from ..utils.http_client import aget
import json
from typing import Optional
from .base import (
    BaseLawRepository,
    logger,
    LAW_API_SEARCH_URL,
    search_cache,
    failure_cache,
    DRF_REQUEST_TIMEOUT_SEC,
)


# 광역자치단체 이름 → org 코드 (law.go.kr DRF API 기준)
# org 코드 예시: 서울특별시=6110000 (API 문서 확인값)
#
# Source: law.go.kr DRF Open API 코드표 + PR #16(2026-05-21) 검증.
# Last verified: 2026-05-21 (서울/부산/경기/제주 라이브 호출에서 정상 매칭 확인).
# 갱신 시 단위 테스트(tests/test_local_ordinance_codes.py) 회귀 확인 필수.
_ORG_CODE_MAP: dict[str, str] = {
    "서울특별시": "6110000", "서울시": "6110000", "서울": "6110000",
    "부산광역시": "6260000", "부산시": "6260000", "부산": "6260000",
    "대구광역시": "6270000", "대구시": "6270000", "대구": "6270000",
    "인천광역시": "6280000", "인천시": "6280000", "인천": "6280000",
    "광주광역시": "6290000", "광주시": "6290000", "광주": "6290000",
    "대전광역시": "6300000", "대전시": "6300000", "대전": "6300000",
    "울산광역시": "6310000", "울산시": "6310000", "울산": "6310000",
    "세종특별자치시": "5690000", "세종시": "5690000", "세종": "5690000",
    "경기도": "6410000", "경기": "6410000",
    "강원특별자치도": "6420000", "강원도": "6420000", "강원": "6420000",
    "충청북도": "6430000", "충북": "6430000",
    "충청남도": "6440000", "충남": "6440000",
    "전북특별자치도": "6450000", "전라북도": "6450000", "전북": "6450000",
    "전라남도": "6460000", "전남": "6460000",
    "경상북도": "6470000", "경북": "6470000",
    "경상남도": "6480000", "경남": "6480000",
    "제주특별자치도": "6500000", "제주도": "6500000", "제주": "6500000",
}


# 시·군·구 이름 → sborg 코드
# 구조: {org_code: {district_name: sborg_code}}
# "중구" 등 동명 구가 여러 시에 존재하므로 org_code를 키로 중첩 구성.
#
# Source: PR #16(2026-05-21) 도입. 일부 데이터는 약 10년 전 자료 기반이므로
# 행정구역 신설/개편 발생 시 갱신 필요(예: 미추홀구 신설 등). 갱신 시
# tests/test_local_ordinance_codes.py 회귀 확인 필수.
# Last verified: 2026-05-21.
_SBORG_CODE_MAP: dict[str, dict[str, str]] = {
    "6110000": {  # 서울특별시
        "종로구": "3000000",
        "중구": "3010000",
        "용산구": "3020000",
        "성동구": "3030000",
        "광진구": "3040000",
        "동대문구": "3050000",
        "중랑구": "3060000",
        "성북구": "3070000",
        "강북구": "3080000",
        "도봉구": "3090000",
        "노원구": "3100000",
        "은평구": "3110000",
        "서대문구": "3120000",
        "마포구": "3130000",
        "양천구": "3140000",
        "강서구": "3150000",
        "구로구": "3160000",
        "금천구": "3170000",
        "영등포구": "3180000",
        "동작구": "3190000",
        "관악구": "3200000",
        "서초구": "3210000",
        "강남구": "3220000",
        "송파구": "3230000",
        "강동구": "3240000",
    },
    "6260000": {  # 부산광역시
        "중구": "3250000",
        "서구": "3260000",
        "동구": "3270000",
        "영도구": "3280000",
        "부산진구": "3290000",
        "동래구": "3300000",
        "남구": "3310000",
        "북구": "3320000",
        "해운대구": "3330000",
        "사하구": "3340000",
        "금정구": "3350000",
        "강서구": "3360000",
        "연제구": "3370000",
        "수영구": "3380000",
        "사상구": "3390000",
        "기장군": "3400000",
    },
    "6270000": {  # 대구광역시
        "중구": "3410000",
        "동구": "3420000",
        "서구": "3430000",
        "남구": "3440000",
        "북구": "3450000",
        "수성구": "3460000",
        "달서구": "3470000",
        "달성군": "3480000",
    },
    "6280000": {  # 인천광역시
        "중구": "3490000",
        "동구": "3500000",
        "미추홀구": "3510500",
        "연수구": "3520000",
        "남동구": "3530000",
        "부평구": "3540000",
        "계양구": "3550000",
        "서구": "3560000",
        "강화군": "3570000",
        "옹진군": "3580000",
    },
    "6290000": {  # 광주광역시
        "동구": "3590000",
        "서구": "3600000",
        "남구": "3610000",
        "북구": "3620000",
        "광산구": "3630000",
    },
    "6300000": {  # 대전광역시
        "동구": "3640000",
        "중구": "3650000",
        "서구": "3660000",
        "유성구": "3670000",
        "대덕구": "3680000",
    },
    "6310000": {  # 울산광역시
        "중구": "3690000",
        "남구": "3700000",
        "동구": "3710000",
        "북구": "3720000",
        "울주군": "3730000",
    },
    "6410000": {  # 경기도
        "수원시": "3740000",
        "성남시": "3780000",
        "의정부시": "3820000",
        "안양시": "3830000",
        "부천시": "3860000",
        "광명시": "3900000",
        "평택시": "3910000",
        "동두천시": "3920000", "동두천": "3920000",
        "안산시": "3930000",
        "고양시": "3940000",
        "과천시": "3970000",
        "구리시": "3980000",
        "남양주시": "3990000", "남양주": "3990000",
        "오산시": "4000000",
        "시흥시": "4010000",
        "군포시": "4020000",
        "의왕시": "4030000",
        "하남시": "4040000",
        "용인시": "4050000",
        "파주시": "4060000",
        "이천시": "4070000",
        "안성시": "4080000",
        "김포시": "4090000",
        "연천군": "4140000",
        "가평군": "4160000",
        "양평군": "4170000",
        "화성시": "5530000",
        "광주시": "5540000",
        "양주시": "5590000",
        "포천시": "5600000",
        "여주시": "5700000",
    },
    "6420000": {  # 강원도 (강원특별자치도)
        "춘천시": "4180000",
        "원주시": "4190000",
        "강릉시": "4200000",
        "동해시": "4210000",
        "태백시": "4220000",
        "속초시": "4230000",
        "삼척시": "4240000",
        "홍천군": "4250000",
        "횡성군": "4260000",
        "영월군": "4270000",
        "평창군": "4280000",
        "정선군": "4290000",
        "철원군": "4300000",
        "화천군": "4310000",
        "양구군": "4320000",
        "인제군": "4330000",
        "고성군": "4340000",
        "양양군": "4350000",
    },
    "6430000": {  # 충청북도
        "충주시": "4390000",
        "제천시": "4400000",
        "보은군": "4420000",
        "옥천군": "4430000",
        "영동군": "4440000",
        "진천군": "4450000",
        "괴산군": "4460000",
        "음성군": "4470000",
        "단양군": "4480000",
        "증평군": "5570000",
        "청주시": "5710000",
    },
    "6440000": {  # 충청남도
        "천안시": "4490000",
        "공주시": "4500000",
        "보령시": "4510000",
        "아산시": "4520000",
        "서산시": "4530000",
        "논산시": "4540000",
        "금산군": "4550000",
        "연기군": "4560000",
        "부여군": "4570000",
        "서천군": "4580000",
        "청양군": "4590000",
        "홍성군": "4600000",
        "예산군": "4610000",
        "태안군": "4620000",
        "계룡시": "5580000",
        "당진시": "5680000",
    },
    "6450000": {  # 전라북도 (전북특별자치도)
        "전주시": "4640000",
        "군산시": "4670000",
        "익산시": "4680000",
        "정읍시": "4690000",
        "남원시": "4700000",
        "김제시": "4710000",
        "완주군": "4720000",
        "진안군": "4730000",
        "무주군": "4740000",
        "장수군": "4750000",
        "임실군": "4760000",
        "순창군": "4770000",
        "고창군": "4780000",
        "부안군": "4790000",
    },
    "6460000": {  # 전라남도
        "목포시": "4800000",
        "여수시": "4810000",
        "순천시": "4820000",
        "나주시": "4830000",
        "광양시": "4840000",
        "담양군": "4850000",
        "곡성군": "4860000",
        "구례군": "4870000",
        "고흥군": "4880000",
        "보성군": "4890000",
        "화순군": "4900000",
        "장흥군": "4910000",
        "강진군": "4920000",
        "해남군": "4930000",
        "영암군": "4940000",
        "무안군": "4950000",
        "함평군": "4960000",
        "영광군": "4970000",
        "장성군": "4980000",
        "완도군": "4990000",
        "진도군": "5000000",
        "신안군": "5010000",
    },
    "6470000": {  # 경상북도
        "포항시": "5020000",
        "경주시": "5050000",
        "김천시": "5060000",
        "안동시": "5070000",
        "구미시": "5080000",
        "영주시": "5090000",
        "영천시": "5100000",
        "상주시": "5110000",
        "문경시": "5120000",
        "경산시": "5130000",
        "군위군": "5140000",
        "의성군": "5150000",
        "청송군": "5160000",
        "영양군": "5170000",
        "영덕군": "5180000",
        "청도군": "5190000",
        "고령군": "5200000",
        "성주군": "5210000",
        "칠곡군": "5220000",
        "예천군": "5230000",
        "봉화군": "5240000",
        "울진군": "5250000",
        "울릉군": "5260000",
    },
    "6480000": {  # 경상남도
        "진주시": "5310000",
        "통영시": "5330000",
        "사천시": "5340000",
        "김해시": "5350000",
        "밀양시": "5360000",
        "거제시": "5370000",
        "양산시": "5380000",
        "의령군": "5390000",
        "함안군": "5400000",
        "창녕군": "5410000",
        "고성군": "5420000",
        "남해군": "5430000",
        "하동군": "5440000",
        "산청군": "5450000",
        "함양군": "5460000",
        "거창군": "5470000",
        "합천군": "5480000",
        "창원시": "5670000",
    },
    "6500000": {  # 제주특별자치도
        "제주시": "6510000",
        "서귀포시": "6520000",
    },
}


def _resolve_org_code(name: str) -> str | None:
    """지자체 이름 또는 이미 숫자 코드인 경우 org 코드를 반환한다."""
    if name.isdigit():
        return name
    return _ORG_CODE_MAP.get(name.strip())


def _resolve_sborg_code(org_code: str, name: str) -> str | None:
    """시·군·구 이름 또는 이미 숫자 코드인 경우 sborg 코드를 반환한다."""
    if name.isdigit():
        return name
    return _SBORG_CODE_MAP.get(org_code, {}).get(name.strip())


class LocalOrdinanceRepository(BaseLawRepository):
    """자치법규 검색 관련 기능을 담당하는 Repository"""

    async def search_local_ordinance(
        self,
        query: Optional[str] = None,
        local_government: Optional[str] = None,
        sub_local_government: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        arguments: Optional[dict] = None
    ) -> dict:
        """자치법규를 검색합니다."""
        logger.debug(
            "search_local_ordinance called | query=%r local_government=%r sub_local_government=%r page=%d per_page=%d",
            query, local_government, sub_local_government, page, per_page,
        )

        if per_page < 1:
            per_page = 1
        if per_page > 100:
            per_page = 100

        cache_key = ("local_ordinance", query or "", local_government or "", sub_local_government or "", page, per_page)

        if cache_key in search_cache:
            return search_cache[cache_key]
        if cache_key in failure_cache:
            return failure_cache[cache_key]

        try:
            params = {
                "target": "ordin",  # API 문서: target=ordin
                "type": "JSON",
                "page": page,
                "display": per_page
            }

            if query:
                params["query"] = self.normalize_search_query(query)

            if local_government:
                org_code = _resolve_org_code(local_government)
                if org_code:
                    params["org"] = org_code
                else:
                    return {
                        "error_code": "INVALID_INPUT",
                        "error": f"지원하지 않는 지자체 명칭입니다: '{local_government}'",
                        "recovery_guide": "광역자치단체 명칭을 사용하세요. 예: 서울, 경기도, 부산광역시",
                    }

                if sub_local_government:
                    sborg_code = _resolve_sborg_code(org_code, sub_local_government)
                    if sborg_code:
                        params["sborg"] = sborg_code
                    else:
                        return {
                            "error_code": "INVALID_INPUT",
                            "error": f"지원하지 않는 시·군·구 명칭입니다: '{sub_local_government}'",
                            "recovery_guide": "시·군·구 명칭 또는 sborg 코드를 직접 입력하세요. 예: 구로구, 3160000",
                        }
            elif sub_local_government:
                return {
                    "error_code": "INVALID_INPUT",
                    "error": "sub_local_government를 사용하려면 local_government(광역자치단체)도 함께 지정해야 합니다.",
                    "recovery_guide": "예: local_government='서울', sub_local_government='구로구'",
                }

            _, api_key_error = self.attach_api_key(params, arguments, LAW_API_SEARCH_URL)
            if api_key_error:
                return api_key_error

            response = await aget(LAW_API_SEARCH_URL, params=params, timeout=DRF_REQUEST_TIMEOUT_SEC)

            if not response.text or not response.text.strip():
                return {
                    "error": "API가 빈 응답을 반환했습니다. API 키가 필요하거나 권한이 없을 수 있습니다.",
                    "query": query,
                    "local_government": local_government,
                    "api_url": response.url,
                    "note": "국가법령정보센터 OPEN API 사용을 위해서는 https://open.law.go.kr 에서 회원가입 및 API 활용 신청이 필요합니다."
                }

            invalid_response = self.validate_drf_response(response)
            if invalid_response:
                return invalid_response
            response.raise_for_status()

            try:
                data = response.json()
            except json.JSONDecodeError as e:
                return {
                    "error": f"API 응답이 유효한 JSON 형식이 아닙니다: {str(e)}",
                    "query": query,
                    "local_government": local_government,
                    "api_url": response.url,
                    "recovery_guide": "API 응답 형식 오류입니다. API 서버 상태를 확인하거나 잠시 후 다시 시도하세요.",
                    "raw_response": response.text[:200] if response.text else "Empty response"
                }

            result = {
                "query": query,
                "local_government": local_government,
                "page": page,
                "per_page": per_page,
                "total": 0,
                "ordinances": [],
                "api_url": response.url
            }

            if isinstance(data, dict):
                # 자치법규 응답은 항목 배열의 키가 일관되지 않다.
                # 실측: OrdinSearch.law 사용. 일부 응답에서는 ordin 사용.
                # 양쪽 모두 fallback으로 탐색한다.
                if "OrdinSearch" in data:
                    ordin_search = data["OrdinSearch"]
                    if isinstance(ordin_search, dict):
                        total_raw = ordin_search.get("totalCnt", 0)
                        try:
                            result["total"] = int(total_raw)
                        except (TypeError, ValueError):
                            result["total"] = 0
                        ordinances = (
                            ordin_search.get("law")
                            or ordin_search.get("ordin")
                            or []
                        )
                    else:
                        ordinances = []
                else:
                    total_raw = data.get("totalCnt", 0)
                    try:
                        result["total"] = int(total_raw)
                    except (TypeError, ValueError):
                        result["total"] = 0
                    ordinances = (
                        data.get("law")
                        or data.get("ordin")
                        or []
                    )

                if not isinstance(ordinances, list):
                    ordinances = [ordinances] if ordinances else []

                result["ordinances"] = ordinances[:per_page]

            # total은 있는데 목록이 비어 있는 경우 메타 정보 추가
            if result["total"] and not result["ordinances"]:
                result["note"] = "API 응답에서 totalCnt는 있으나 자치법규 목록이 비어 있습니다. 국가법령정보센터 응답 구조를 확인하세요."

            search_cache[cache_key] = result
            return result

        except httpx.TimeoutException:
            error_result = {
                "error": "API 호출 타임아웃",
                "recovery_guide": "네트워크 응답 시간이 초과되었습니다. 잠시 후 다시 시도하거나, 인터넷 연결을 확인하세요."
            }
            failure_cache[cache_key] = error_result
            return error_result
        except httpx.RequestError as e:
            error_result = {
                "error": f"API 요청 실패: {str(e)}",
                "recovery_guide": "네트워크 오류입니다. 잠시 후 다시 시도하거나, 인터넷 연결을 확인하세요."
            }
            failure_cache[cache_key] = error_result
            return error_result
        except Exception as e:
            logger.exception("예상치 못한 오류")
            return {
                "error": f"예상치 못한 오류: {str(e)}",
                "recovery_guide": "시스템 오류가 발생했습니다. 서버 로그를 확인하거나 관리자에게 문의하세요."
            }

    async def get_ordinance_fields(
        self,
        arguments: Optional[dict] = None,
    ) -> dict:
        """자치법규 분야 목록 조회 (target=ordinfd).

        분야 코드 목록을 조회하여 자치법규 검색 시 분야 필터 기준으로 활용합니다.
        """
        cache_key = ("ordinfd",)
        if cache_key in search_cache:
            return search_cache[cache_key]
        if cache_key in failure_cache:
            return failure_cache[cache_key]

        try:
            params: dict = {"target": "ordinfd", "type": "JSON"}
            _, err = self.attach_api_key(params, arguments, LAW_API_SEARCH_URL)
            if err:
                return err

            response = await aget(LAW_API_SEARCH_URL, params=params, timeout=DRF_REQUEST_TIMEOUT_SEC)
            invalid = self.validate_drf_response(response)
            if invalid:
                failure_cache[cache_key] = invalid
                return invalid
            response.raise_for_status()

            try:
                data = response.json()
            except Exception as e:
                return {"error": f"JSON 파싱 오류: {e}"}

            result = {"data": data, "api_url": str(response.url)}
            search_cache[cache_key] = result
            return result

        except httpx.TimeoutException:
            err = {
                "error_code": "API_ERROR_TIMEOUT",
                "missing_reason": "API_ERROR_TIMEOUT",
                "error": "API 호출 타임아웃",
                "recovery_guide": "잠시 후 다시 시도하세요.",
            }
            failure_cache[cache_key] = err
            return err
        except httpx.RequestError as e:
            return {"error": f"API 요청 실패: {e}"}
        except Exception as e:
            logger.exception("get_ordinance_fields 오류")
            return {"error": f"예상치 못한 오류: {e}"}

