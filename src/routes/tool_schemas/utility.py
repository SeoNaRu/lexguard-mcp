"""유틸리티 도구 스키마: health."""

SCHEMAS = [
    {
        "name": "health",
        "priority": 2,
        "category": "utility",
        "description": "서비스 상태를 확인합니다. API 키 설정 상태, 환경 변수, 서버 상태에 더해 국가법령정보센터 API 실제 연결(키 인증·IP 등록)까지 검증합니다. 설치 직후 설정 확인이나 '사용자 정보 검증 실패' 오류 진단에 사용하세요. 예: '서버 상태 확인', 'API 키 설정 확인'.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False,
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "status": {"type": "string"},
                "environment": {"type": "object"},
                "message": {"type": "string"},
                "server": {"type": "string"},
                "api_ready": {"type": "boolean"},
                "api_status": {"type": "string"},
                "api_connection": {"type": "object"},
            },
        },
    },
]
