"""단순 조회 도구 스키마 8종: 판례·해석·심판·위원회·자치법규·행정규칙."""
from ._common import DISCLAIMER

SCHEMAS = [
    {
        "name": "precedent_lookup_tool",
        "priority": 1,
        "category": "precedent",
        "description": f"""판례만 검색합니다. 사건번호가 있으면 case_number, 없으면 keyword로 검색하세요. 통합 legal_qa_tool보다 판례에 집중할 때 사용합니다.

{DISCLAIMER}""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string", "description": "판례 검색 키워드 (사건번호가 없을 때)"},
                "case_number": {"type": "string", "description": "사건번호 (예: 2023다12345, 2021도4321). 있으면 우선 사용"},
                "page": {"type": "integer", "default": 1, "minimum": 1},
                "per_page": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50, "description": "페이지당 건수"},
                "court": {"type": "string", "description": "법원 필터(코드). 생략 시 전체"},
                "date_from": {"type": "string", "description": "선고일 시작 YYYYMMDD"},
                "date_to": {"type": "string", "description": "선고일 종료 YYYYMMDD"}
            },
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "total": {"type": "integer"},
                "precedents": {"type": "array"},
                "error": {"type": "string"},
                "error_code": {"type": "string"}
            }
        }
    },
    {
        "name": "interpretation_tool",
        "priority": 1,
        "category": "interpretation",
        "description": f"""법령해석(행정기관 해석례 등)만 검색합니다. 해석·유권해석 실마리가 필요할 때 legal_qa_tool 대신 사용합니다.

{DISCLAIMER}""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "법령해석 검색어"},
                "page": {"type": "integer", "default": 1, "minimum": 1},
                "per_page": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
                "agency": {"type": "string", "description": "부처명 필터 (예: 고용노동부, 국세청). 지원되는 명칭만 적용"}
            },
            "required": ["query"]
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "total": {"type": "integer"},
                "interpretations": {"type": "array"},
                "error": {"type": "string"},
                "error_code": {"type": "string"}
            }
        }
    },
    {
        "name": "administrative_appeal_tool",
        "priority": 1,
        "category": "administrative_appeal",
        "description": f"""행정심판 재결만 검색합니다. 행정심판·재결례 실마리가 필요할 때 legal_qa_tool 대신 사용합니다.

{DISCLAIMER}""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "행정심판 재결 검색어"},
                "page": {"type": "integer", "default": 1, "minimum": 1},
                "per_page": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
                "date_from": {"type": "string", "description": "재결일 시작 YYYYMMDD"},
                "date_to": {"type": "string", "description": "재결일 종료 YYYYMMDD"}
            },
            "required": ["query"]
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "total": {"type": "integer"},
                "appeals": {"type": "array"},
                "error": {"type": "string"},
                "error_code": {"type": "string"}
            }
        }
    },
    {
        "name": "constitutional_decision_tool",
        "priority": 1,
        "category": "constitutional",
        "description": f"""헌법재판소 결정만 검색합니다. 위헌·헌법소원 등 헌재 실마리가 필요할 때 legal_qa_tool 대신 사용합니다.

{DISCLAIMER}""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "헌재결정 검색어"},
                "page": {"type": "integer", "default": 1, "minimum": 1},
                "per_page": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
                "date_from": {"type": "string", "description": "YYYYMMDD"},
                "date_to": {"type": "string", "description": "YYYYMMDD"},
            },
            "required": ["query"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "total": {"type": "integer"},
                "decisions": {"type": "array"},
                "error": {"type": "string"},
                "error_code": {"type": "string"},
            },
        },
    },
    {
        "name": "committee_decision_tool",
        "priority": 1,
        "category": "committee",
        "description": f"""독립위원회 등 결정문만 검색합니다. committee_type은 API가 지원하는 정확한 명칭이어야 합니다 (예: 개인정보보호위원회, 금융위원회, 노동위원회 등).

{DISCLAIMER}""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "committee_type": {"type": "string", "description": "위원회 명칭 (저장소 COMMITTEE_TARGET_MAP 키와 일치)"},
                "query": {"type": "string", "description": "결정문 검색어"},
                "page": {"type": "integer", "default": 1, "minimum": 1},
                "per_page": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
            },
            "required": ["committee_type", "query"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "total": {"type": "integer"},
                "decisions": {"type": "array"},
                "error": {"type": "string"},
                "error_code": {"type": "string"},
            },
        },
    },
    {
        "name": "special_administrative_appeal_tool",
        "priority": 1,
        "category": "special_appeal",
        "description": f"""특별행정심판원 재결만 검색합니다. tribunal_type은 조세심판원·해양안전심판원 등 저장소가 지원하는 정확한 명칭이어야 합니다.

{DISCLAIMER}""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tribunal_type": {"type": "string", "description": "심판원 명칭 (TRIBUNAL_TARGET_MAP 키와 일치)"},
                "query": {"type": "string", "description": "재결 검색어"},
                "page": {"type": "integer", "default": 1, "minimum": 1},
                "per_page": {"type": "integer", "default": 10, "minimum": 1, "maximum": 50},
            },
            "required": ["tribunal_type", "query"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "total": {"type": "integer"},
                "appeals": {"type": "array"},
                "error": {"type": "string"},
                "error_code": {"type": "string"},
            },
        },
    },
    {
        "name": "local_ordinance_tool",
        "priority": 1,
        "category": "ordinance",
        "description": f"""자치법규(조례 등)만 검색합니다. 지역 조례·규칙 실마리가 필요할 때 legal_qa_tool 대신 사용할 수 있습니다. query와 local_government 중 하나 이상을 넣으세요.

{DISCLAIMER}""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "조례명 또는 검색 키워드"},
                "local_government": {"type": "string", "description": "지방자치단체 명칭 필터 (예: 서울시, 부산시)"},
                "page": {"type": "integer", "default": 1, "minimum": 1},
                "per_page": {"type": "integer", "default": 20, "minimum": 1, "maximum": 50},
            },
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "total": {"type": "integer"},
                "ordinances": {"type": "array"},
                "error": {"type": ["string", "null"]},
                "error_code": {"type": ["string", "null"]},
            },
        },
    },
    {
        "name": "administrative_rule_tool",
        "priority": 1,
        "category": "admin_rule",
        "description": f"""행정규칙만 검색합니다. 부처 훈령·예규 등 실마리가 필요할 때 legal_qa_tool 대신 사용할 수 있습니다. query와 agency 중 하나 이상을 넣으세요.

{DISCLAIMER}""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "행정규칙명 또는 검색 키워드"},
                "agency": {"type": "string", "description": "부처명 (예: 고용노동부, 교육부). 저장소 매핑에 있는 명칭만 기관 필터로 적용될 수 있습니다."},
                "page": {"type": "integer", "default": 1, "minimum": 1},
                "per_page": {"type": "integer", "default": 20, "minimum": 1, "maximum": 50},
            },
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "total": {"type": "integer"},
                "rules": {"type": "array"},
                "error": {"type": ["string", "null"]},
                "error_code": {"type": ["string", "null"]},
            },
        },
    },
]
