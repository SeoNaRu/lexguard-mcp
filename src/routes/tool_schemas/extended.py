"""확장 도구 스키마 5종: 부처별해석·이력·부가정보·별표서식·연계."""
from ._common import DISCLAIMER

SCHEMAS = [
    {
        "name": "ministry_interpretation_tool",
        "priority": 6,
        "category": "law_interpretation",
        "description": f"""특정 부처의 법령해석(질의회신)을 검색합니다. 39개 부처별 전용 법령해석 데이터베이스를 지원합니다.

지원 부처: 고용노동부, 국토교통부, 기획재정부, 해양수산부, 행정안전부, 기후에너지환경부, 관세청, 국세청, 교육부, 과학기술정보통신부, 국가보훈부, 국방부, 농림축산식품부, 문화체육관광부, 법무부, 보건복지부, 산업통상자원부, 성평등가족부, 외교부, 중소벤처기업부, 통일부, 법제처, 식품의약품안전처, 인사혁신처, 기상청, 국가유산청, 농촌진흥청, 경찰청, 방위사업청, 병무청, 산림청, 소방청, 재외동포청, 조달청, 질병관리청, 국가데이터처, 지식재산처, 해양경찰청, 행정중심복합도시건설청

{DISCLAIMER}""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "검색 키워드 (법령해석 제목 또는 내용)",
                },
                "agency": {
                    "type": "string",
                    "description": "부처명 (예: 고용노동부, 국세청, 보건복지부). 반드시 지원 부처 명칭과 일치해야 합니다.",
                },
                "page": {"type": "integer", "default": 1, "minimum": 1},
                "per_page": {"type": "integer", "default": 20, "minimum": 1, "maximum": 50},
            },
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "total": {"type": "integer"},
                "interpretations": {"type": "array"},
                "error": {"type": ["string", "null"]},
                "error_code": {"type": ["string", "null"]},
            },
        },
    },
    {
        "name": "law_history_tool",
        "priority": 5,
        "category": "law_history",
        "description": f"""법령 변경이력 또는 조문별 개정이력을 조회합니다. 특정 법령이 언제, 어떻게 개정되었는지 파악할 때 사용합니다.

search_type 선택:
- "law_change": 법령 변경이력 목록 (lsHstInf)
- "article_change": 일자별 조문 개정이력 (lsJoHstInf 목록)
- "article_detail": 특정 조문의 개정이력 상세 (lsJoHstInf 본문, law_id 필수)

{DISCLAIMER}""",
        "inputSchema": {
            "type": "object",
            "required": ["search_type"],
            "properties": {
                "search_type": {
                    "type": "string",
                    "enum": ["law_change", "article_change", "article_detail"],
                    "description": "조회 유형",
                },
                "query": {"type": "string", "description": "법령명 검색어"},
                "law_id": {"type": "string", "description": "법령 ID (lsId). article_detail에 필수"},
                "article_number": {"type": "string", "description": "조문 번호 (예: 000100)"},
                "date": {"type": "string", "description": "기준 일자 (YYYYMMDD)"},
                "page": {"type": "integer", "default": 1, "minimum": 1},
                "per_page": {"type": "integer", "default": 20, "minimum": 1, "maximum": 50},
            },
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "total": {"type": "integer"},
                "items": {"type": "array"},
                "error": {"type": ["string", "null"]},
            },
        },
    },
    {
        "name": "law_info_tool",
        "priority": 5,
        "category": "law_info",
        "description": f"""법령 부가 정보를 조회합니다. 영문법령, 조약, 법령 체계도, 한눈보기, 법령명 약칭 등을 검색할 수 있습니다.

info_type 선택:
- "english_law": 영문법령 검색 (elaw)
- "treaty": 국제조약 검색 (trty)
- "structure": 법령 체계도 검색 (lsStmd)
- "oneview": 한눈보기 검색 (법령 한눈 요약, oneview)
- "abbreviation": 법령명 약칭 검색 (lsAbrv)
- "deleted": 삭제된 법령·조문 이력 (delHst)

{DISCLAIMER}""",
        "inputSchema": {
            "type": "object",
            "required": ["info_type"],
            "properties": {
                "info_type": {
                    "type": "string",
                    "enum": ["english_law", "treaty", "structure", "oneview", "abbreviation", "deleted"],
                    "description": "조회 유형",
                },
                "query": {"type": "string", "description": "검색 키워드 (법령명, 조약명 등)"},
                "item_id": {"type": "string", "description": "본문 조회 시 ID (법령 ID 또는 조약 ID)"},
                "page": {"type": "integer", "default": 1, "minimum": 1},
                "per_page": {"type": "integer", "default": 20, "minimum": 1, "maximum": 50},
            },
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "total": {"type": "integer"},
                "items": {"type": "array"},
                "data": {"type": ["object", "null"]},
                "error": {"type": ["string", "null"]},
            },
        },
    },
    {
        "name": "law_form_tool",
        "priority": 4,
        "category": "law_form",
        "description": f"""법령·행정규칙·자치법규의 별표서식을 검색합니다. 서식명이나 관련 법령명으로 검색할 수 있습니다.

form_type 선택:
- "law": 법령 별표서식 (licbyl)
- "admin_rule": 행정규칙 별표서식 (admbyl)
- "ordinance": 자치법규 별표서식 (ordinbyl)

{DISCLAIMER}""",
        "inputSchema": {
            "type": "object",
            "required": ["form_type"],
            "properties": {
                "form_type": {
                    "type": "string",
                    "enum": ["law", "admin_rule", "ordinance"],
                    "description": "서식 종류",
                },
                "query": {"type": "string", "description": "서식명 또는 관련 법령명 검색어"},
                "page": {"type": "integer", "default": 1, "minimum": 1},
                "per_page": {"type": "integer", "default": 20, "minimum": 1, "maximum": 50},
            },
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "total": {"type": "integer"},
                "items": {"type": "array"},
                "error": {"type": ["string", "null"]},
            },
        },
    },
    {
        "name": "law_link_tool",
        "priority": 4,
        "category": "law_link",
        "description": f"""법령과 자치법규(조례) 간의 연계 정보를 조회합니다. 특정 법령에 연계된 조례 목록, 소관부처별 연계 현황 등을 확인할 수 있습니다.

link_type 선택:
- "law_to_ordinance": 법령-자치법규 연계 목록 (lnkLs)
- "ordinance_articles": 연계 법령별 조례 조문 목록 (lnkLsOrdJo)
- "by_department": 연계 법령 소관부처별 목록 (lnkDep)
- "linked_ordinance": 연계 조례 목록 (lnkOrd)
- "law_linked_ordinance": 연계 법령별 조례 목록 (lnkLsOrd)
- "by_region": 연계 조례 지자체별 목록 (lnkOrg)

{DISCLAIMER}""",
        "inputSchema": {
            "type": "object",
            "required": ["link_type"],
            "properties": {
                "link_type": {
                    "type": "string",
                    "enum": ["law_to_ordinance", "ordinance_articles", "by_department", "linked_ordinance", "law_linked_ordinance", "by_region"],
                    "description": "조회 유형",
                },
                "query": {"type": "string", "description": "법령명 또는 조례명 검색어"},
                "law_id": {"type": "string", "description": "법령 ID (lsId)"},
                "department": {"type": "string", "description": "소관부처명 또는 코드 (by_department 사용 시)"},
                "region_code": {"type": "string", "description": "지자체 코드 (by_region 사용 시)"},
                "page": {"type": "integer", "default": 1, "minimum": 1},
                "per_page": {"type": "integer", "default": 20, "minimum": 1, "maximum": 50},
            },
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "total": {"type": "integer"},
                "items": {"type": "array"},
                "error": {"type": ["string", "null"]},
            },
        },
    },
]
