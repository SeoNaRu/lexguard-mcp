"""
Health Service - 헬스 체크 비즈니스 로직
"""
import os

import httpx

from src.repositories.base import (
    BaseLawRepository,
    LAW_API_BASE_URL,
    DRF_REQUEST_TIMEOUT_SEC,
)
from src.utils.http_client import aget

_IP_REGISTRATION_GUIDE = (
    "open.law.go.kr [OPEN API > API인증키관리]에서 현재 서버(PC)의 IP가 "
    "등록되어 있는지 확인하세요. 유동 IP 회선은 IP 변경 시 재등록이 필요합니다."
)


class HealthService:
    """헬스 체크 관련 비즈니스 로직을 처리하는 Service"""

    @staticmethod
    async def _check_api_connection() -> dict:
        """실제 DRF API를 1회 호출해 키 인증·IP 등록 상태를 확인합니다.

        반드시 lawService.do(본문 조회)를 사용해야 한다 — lawSearch.do(목록
        검색)는 잘못된 OC/미등록 IP도 통과시키므로 인증 검증이 되지 않는다.
        """
        params = {"target": "law", "type": "JSON", "LM": "근로기준법"}
        _, err = BaseLawRepository.attach_api_key(params, None, LAW_API_BASE_URL)
        if err:
            return {
                "checked": True,
                "status": "failed",
                "error_code": err.get("error_code"),
                "message": err.get("error"),
                "guide": err.get("recovery_guide"),
            }
        try:
            response = await aget(
                LAW_API_BASE_URL, params=params, timeout=DRF_REQUEST_TIMEOUT_SEC
            )
        except httpx.TimeoutException:
            return {
                "checked": True,
                "status": "failed",
                "message": "law.go.kr 응답 타임아웃",
                "guide": "네트워크 상태를 확인한 뒤 잠시 후 다시 시도하세요.",
            }
        except httpx.RequestError as e:
            return {
                "checked": True,
                "status": "failed",
                "message": f"law.go.kr 연결 실패: {e}",
                "guide": "네트워크/방화벽 설정을 확인하세요.",
            }

        invalid = BaseLawRepository.validate_drf_response(response)
        if invalid:
            # 미등록 IP는 인증 오류 또는 HTML 안내 페이지("사용자 정보 검증에
            # 실패하였습니다")로 나타나므로 두 경우 모두 IP 등록 안내를 제공한다.
            return {
                "checked": True,
                "status": "failed",
                "error_code": invalid.get("error_code"),
                "message": invalid.get("error"),
                "guide": _IP_REGISTRATION_GUIDE
                if invalid.get("error_code") in ("API_ERROR_AUTH", "API_ERROR_HTML")
                else invalid.get("recovery_guide"),
            }
        # 미등록 IP/잘못된 키는 HTTP 200 + application/json 본문
        # {"result": "사용자 정보 검증에 실패하였습니다.", ...}으로 오므로
        # validate_drf_response()로는 잡히지 않는다 — 본문 마커로 감지한다.
        if "사용자 정보 검증" in (response.text or ""):
            return {
                "checked": True,
                "status": "failed",
                "error_code": "API_ERROR_AUTH",
                "message": "사용자 정보 검증에 실패했습니다 (미등록 IP 또는 잘못된 API 키).",
                "guide": _IP_REGISTRATION_GUIDE,
            }
        return {
            "checked": True,
            "status": "ok",
            "message": "국가법령정보센터 API 인증·조회가 정상 동작합니다.",
        }

    @staticmethod
    async def check_health(deep: bool = False) -> dict:
        """헬스 체크 - 환경 변수 및 API 키 상태 확인.

        deep=True이면 실제 DRF API를 1회 호출해 키 인증·IP 등록까지 검증한다.
        (/health 인프라 프로브는 deep=False, MCP health 도구는 deep=True)
        """
        api_key = os.environ.get("LAW_API_KEY", "")

        has_api_key = bool(api_key)
        api_key_length = len(api_key) if api_key else 0
        api_key_preview = BaseLawRepository.mask_api_key(api_key) if has_api_key else ""

        env_file_exists = os.path.exists(".env")

        env_vars_status = {
            "LAW_API_KEY": {
                "exists": "LAW_API_KEY" in os.environ,
                "has_value": has_api_key,
                "length": api_key_length,
                "preview": api_key_preview if has_api_key else None
            },
            "LOG_LEVEL": {
                "exists": "LOG_LEVEL" in os.environ,
                "value": os.environ.get("LOG_LEVEL", "INFO (default)")
            },
            "PORT": {
                "exists": "PORT" in os.environ,
                "value": os.environ.get("PORT", "9099 (default)")
            }
        }

        # API 준비 상태 확인
        api_ready = has_api_key  # API 키가 있으면 준비됨

        # Health Check는 항상 HTTP 200을 반환해야 함 (인프라 프로브가 서버
        # 생존 여부만 판단하도록; 상세 상태는 본문 status 필드로 전달)
        result = {
            "status": "ok" if api_ready else "warning",
            "environment": {
                "law_api_key": {
                    "configured": has_api_key,
                    "length": api_key_length,
                    "preview": api_key_preview if has_api_key else None,
                    "source": ".env 파일에서 로드됨" if has_api_key else "설정되지 않음 (선택사항)",
                    "usage": "국가법령정보센터 API의 OC 파라미터로 사용됩니다."
                },
                "env_file": {
                    "exists": env_file_exists,
                    "path": ".env",
                    "loaded": env_file_exists
                },
                "env_vars": env_vars_status,
                "api_ready": api_ready,
                "api_status": "ready" if api_ready else "not_ready",
                "api_status_message": "API 키가 설정되어 있어 검색 기능을 사용할 수 있습니다." if api_ready else "API 키가 설정되지 않아 일부 검색 기능이 제한될 수 있습니다."
            },
            "message": "한국 법령 MCP 서버가 정상적으로 실행 중입니다." if api_ready else "서버는 실행 중이지만 API 키가 설정되지 않았습니다.",
            "note": "LAW_API_KEY가 설정되어 있으면 모든 API 요청의 OC 파라미터에 자동으로 포함됩니다." if api_ready else "LAW_API_KEY를 설정하면 더 많은 검색 기능을 사용할 수 있습니다.",
            "server": "active"
        }

        if deep:
            connection = await HealthService._check_api_connection()
            result["api_connection"] = connection
            if connection["status"] != "ok":
                result["status"] = "warning"
                result["message"] = (
                    "서버는 실행 중이지만 국가법령정보센터 API 연결 확인에 실패했습니다."
                )

        return result
