"""
Health Service - 헬스 체크 비즈니스 로직
"""
import os


class HealthService:
    """헬스 체크 관련 비즈니스 로직을 처리하는 Service"""
    
    @staticmethod
    async def check_health() -> dict:
        """헬스 체크 - 환경 변수 및 API 키 상태 확인"""
        api_key = os.environ.get("LAW_API_KEY", "")
        
        has_api_key = bool(api_key)
        api_key_length = len(api_key) if api_key else 0
        api_key_preview = api_key[:8] + "..." if api_key and len(api_key) > 8 else (api_key if api_key else "")
        
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
                "value": os.environ.get("PORT", "8099 (default)")
            }
        }
        
        # Health Check는 항상 HTTP 200을 반환해야 함 (Render가 스핀다운 방지)
        # status가 "ok"가 아니어도 200을 반환하여 서버가 살아있음을 알림
        return {
            "status": "ok",
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
                "api_ready": True
            },
            "message": "한국 법령 MCP 서버가 정상적으로 실행 중입니다.",
            "note": "LAW_API_KEY가 설정되어 있으면 모든 API 요청의 OC 파라미터에 자동으로 포함됩니다.",
            "server": "active"  # Render Health Check를 위한 명시적 상태 표시
        }

