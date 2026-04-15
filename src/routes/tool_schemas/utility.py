"""유틸리티 도구 스키마: health."""

SCHEMAS = [
    {
        "name": "health",
        "priority": 2,
        "category": "utility",
        "description": "서비스 상태를 확인합니다. API 키 설정 상태, 환경 변수, 서버 상태 등을 확인할 때 사용합니다. 예: '서버 상태 확인', 'API 키 설정 확인'.",
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
            },
        },
    },
]
