"""공통 스키마 조각 — 여러 도구가 공유하는 page/per_page/error 필드."""

PAGE_PROPS = {
    "page": {"type": "integer", "default": 1, "minimum": 1},
    "per_page": {"type": "integer", "default": 20, "minimum": 1, "maximum": 50},
}

PAGE_PROPS_10 = {
    "page": {"type": "integer", "default": 1, "minimum": 1},
    "per_page": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
}

ERROR_OUTPUT = {
    "error": {"type": ["string", "null"]},
    "error_code": {"type": ["string", "null"]},
}

DISCLAIMER = "판단 유보: 본 도구는 검색 결과만 제공하며 법적 판단을 대신하지 않습니다.\n\n금지: 이모지, 단정적 결론, API 링크 노출"
