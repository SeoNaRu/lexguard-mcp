"""MCP tools/list 스키마 정의.

mcp_routes.py의 tools/list 핸들러에서 인라인으로 관리되던
도구 스키마를 이 파일에서 일괄 관리합니다.
새 도구를 추가할 때는 TOOLS_LIST 에 항목만 추가하면 됩니다.
"""
from ..utils.document_issue_prompts import DOCUMENT_ISSUE_TOOL_DESCRIPTION_TEXT

TOOLS_LIST = [
    {
        "name": "legal_qa_tool",
        "priority": 1,
        "category": "integrated",
        "description": """법률 질문에 대한 법적 근거의 실마리를 제공합니다. 법령, 판례, 행정해석, 위원회 결정례 등을 통합 검색합니다.
통합 법률 검색·근거 실마리의 기본 진입점입니다. 출처가 한정된 검색(판례만, 해석만, 심판만 등)은 해당 전용 툴을 우선 검토하세요.

답변 형식 (A 타입, 반드시 준수):
1) 한 줄 방향 제시 (예: 문제가 될 가능성이 있는 사안입니다)
2) 체크리스트 3개 이하 (판단 포인트)
3) 관련 법령/판례 방향만 언급 (조문 전체 인용 금지)
4) 판단 유보 문장 (본 답변은 법적 판단을 대신하지 않으며...)
5) 추가 정보 요청

금지: 이모지, 타이틀(법률 상담 결과 등), 조문 전체 인용, 단정적 결론, API 링크 노출""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "사용자의 법률 질문 (예: '프리랜서 근로자성 판례', '최근 5년 부당해고 판례', '개인정보보호법 해석')"
                },
                "max_results_per_type": {
                    "type": "integer",
                    "description": "타입당 최대 결과 수",
                    "default": 3,
                    "minimum": 1,
                    "maximum": 10
                }
            },
            "required": ["query"]
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "success_transport": {"type": "boolean"},
                "success_search": {"type": "boolean"},
                "has_legal_basis": {"type": "boolean"},
                "query": {"type": "string"},
                "domain": {"type": "string"},
                "detected_intent": {"type": "string"},
                "results": {"type": "object"},
                "sources_count": {"type": "object"},
                "total_sources": {"type": "integer"},
                "missing_reason": {"type": ["string", "null"]},
                "elapsed_seconds": {"type": "number"},
                "pipeline_version": {"type": "string"}
            }
        }
    },
    {
        "name": "document_issue_tool",
        "priority": 1,
        "category": "document",
        "description": DOCUMENT_ISSUE_TOOL_DESCRIPTION_TEXT,
        "inputSchema": {
            "type": "object",
            "properties": {
                "document_text": {
                    "type": "string",
                    "description": "계약서/약관 등 문서 텍스트"
                },
                "auto_search": {
                    "type": "boolean",
                    "description": "조항별 추천 검색어로 자동 검색 수행 여부",
                    "default": True
                },
                "max_clauses": {
                    "type": "integer",
                    "description": "자동 검색할 조항 수 제한",
                    "default": 3,
                    "minimum": 1,
                    "maximum": 10
                },
                "max_results_per_type": {
                    "type": "integer",
                    "description": "타입당 최대 결과 수",
                    "default": 3,
                    "minimum": 1,
                    "maximum": 10
                }
            },
            "required": ["document_text"]
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "success_transport": {"type": "boolean"},
                "success_search": {"type": "boolean"},
                "auto_search": {"type": "boolean"},
                "analysis_success": {"type": "boolean"},
                "has_legal_basis": {"type": "boolean"},
                "document_analysis": {"type": "object"},
                "evidence_results": {"type": "array"},
                "missing_reason": {"type": ["string", "null"]},
                "legal_basis_block": {"type": "object"}
            }
        }
    },
    {
        "name": "law_article_tool",
        "priority": 1,
        "category": "law",
        "description": """특정 법령의 조문을 직접 정밀 조회합니다. 법령명과 조문번호를 알고 있을 때 사용하세요.
법령 신구·연혁·3단 비교가 필요하면 law_comparison_tool을 사용하세요.

답변 형식 (A 타입, 반드시 준수):
1) 조문 내용 요약 (인용 최소화)
2) 실무적 의미 한 줄 설명
3) 판단 유보 문장 (본 답변은 법적 판단을 대신하지 않으며...)

금지: 이모지, 조문 전체 인용, 단정적 결론""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "law_name": {
                    "type": "string",
                    "description": "법령명 (예: 근로기준법, 민법, 형법, 개인정보보호법)"
                },
                "article_number": {
                    "type": "string",
                    "description": "조문 번호 (예: '50', '2', '110'). 생략 시 법령 전체 개요 반환"
                },
                "hang": {
                    "type": "string",
                    "description": "항 번호 (예: '1', '2')"
                },
                "ho": {
                    "type": "string",
                    "description": "호 번호 (예: '1', '2')"
                },
                "mok": {
                    "type": "string",
                    "description": "목 번호 (예: '가', '나')"
                }
            },
            "required": ["law_name"]
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "law_name": {"type": "string"},
                "article_number": {"type": ["string", "null"]},
                "law_id": {"type": ["string", "null"]},
                "detail": {"type": ["object", "null"]},
                "error": {"type": ["string", "null"]}
            }
        }
    },
    {
        "name": "law_comparison_tool",
        "priority": 1,
        "category": "law",
        "description": """국가법령정보센터 API 기준으로 법령 신구·연혁·3단 비교 결과를 조회합니다. 비교·연혁 조회가 목적일 때 사용하세요. 일반 법률 질문·판례 검색은 legal_qa_tool 또는 전용 툴을 쓰세요.

판단 유보: 본 도구는 조회 결과만 제공하며 법적 판단을 대신하지 않습니다.

금지: 이모지, 단정적 결론, API 링크 노출""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "law_name": {
                    "type": "string",
                    "description": "비교할 법령명 (예: 형법, 민법, 근로기준법)",
                },
                "compare_type": {
                    "type": "string",
                    "description": "비교 유형: 신구법(신·구법 대비), 연혁(법령 연혁), 3단비교",
                    "enum": ["신구법", "연혁", "3단비교"],
                    "default": "신구법",
                },
            },
            "required": ["law_name"],
        },
        "outputSchema": {
            "type": "object",
            "properties": {
                "law_name": {"type": "string"},
                "law_id": {"type": ["string", "null"]},
                "compare_type": {"type": "string"},
                "comparison": {"type": "object"},
                "error": {"type": ["string", "null"]},
                "error_code": {"type": ["string", "null"]},
                "recovery_guide": {"type": ["string", "null"]},
            },
        },
    },
    {
        "name": "precedent_lookup_tool",
        "priority": 1,
        "category": "precedent",
        "description": """판례만 검색합니다. 사건번호가 있으면 case_number, 없으면 keyword로 검색하세요. 통합 legal_qa_tool보다 판례에 집중할 때 사용합니다.

판단 유보: 본 도구는 검색 결과만 제공하며 법적 판단을 대신하지 않습니다. 추가 사실관계 확인을 요청하세요.

금지: 이모지, 조문 전체 인용, 단정적 결론, API 링크 노출""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "판례 검색 키워드 (사건번호가 없을 때)"
                },
                "case_number": {
                    "type": "string",
                    "description": "사건번호 (예: 2023다12345, 2021도4321). 있으면 우선 사용"
                },
                "page": {"type": "integer", "default": 1, "minimum": 1},
                "per_page": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 50,
                    "description": "페이지당 건수"
                },
                "court": {
                    "type": "string",
                    "description": "법원 필터(코드). 생략 시 전체"
                },
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
        "description": """법령해석(행정기관 해석례 등)만 검색합니다. 해석·유권해석 실마리가 필요할 때 legal_qa_tool 대신 사용합니다.

판단 유보: 본 도구는 검색 결과만 제공하며 법적 판단을 대신하지 않습니다.

금지: 이모지, 단정적 결론, API 링크 노출""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "법령해석 검색어"
                },
                "page": {"type": "integer", "default": 1, "minimum": 1},
                "per_page": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 50
                },
                "agency": {
                    "type": "string",
                    "description": "부처명 필터 (예: 고용노동부, 국세청). 지원되는 명칭만 적용"
                }
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
        "description": """행정심판 재결만 검색합니다. 행정심판·재결례 실마리가 필요할 때 legal_qa_tool 대신 사용합니다.

판단 유보: 본 도구는 검색 결과만 제공하며 법적 판단을 대신하지 않습니다.

금지: 이모지, 단정적 결론, API 링크 노출""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "행정심판 재결 검색어"
                },
                "page": {"type": "integer", "default": 1, "minimum": 1},
                "per_page": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 50
                },
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
        "description": """헌법재판소 결정만 검색합니다. 위헌·헌법소원 등 헌재 실마리가 필요할 때 legal_qa_tool 대신 사용합니다.

판단 유보: 본 도구는 검색 결과만 제공하며 법적 판단을 대신하지 않습니다.

금지: 이모지, 단정적 결론, API 링크 노출""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "헌재결정 검색어"},
                "page": {"type": "integer", "default": 1, "minimum": 1},
                "per_page": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 50,
                },
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
        "description": """독립위원회 등 결정문만 검색합니다. committee_type은 API가 지원하는 정확한 명칭이어야 합니다 (예: 개인정보보호위원회, 금융위원회, 노동위원회 등).

판단 유보: 본 도구는 검색 결과만 제공하며 법적 판단을 대신하지 않습니다.

금지: 이모지, 단정적 결론, API 링크 노출""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "committee_type": {
                    "type": "string",
                    "description": "위원회 명칭 (저장소 COMMITTEE_TARGET_MAP 키와 일치)",
                },
                "query": {"type": "string", "description": "결정문 검색어"},
                "page": {"type": "integer", "default": 1, "minimum": 1},
                "per_page": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 50,
                },
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
        "description": """특별행정심판원 재결만 검색합니다. tribunal_type은 조세심판원·해양안전심판원 등 저장소가 지원하는 정확한 명칭이어야 합니다.

판단 유보: 본 도구는 검색 결과만 제공하며 법적 판단을 대신하지 않습니다.

금지: 이모지, 단정적 결론, API 링크 노출""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tribunal_type": {
                    "type": "string",
                    "description": "심판원 명칭 (TRIBUNAL_TARGET_MAP 키와 일치)",
                },
                "query": {"type": "string", "description": "재결 검색어"},
                "page": {"type": "integer", "default": 1, "minimum": 1},
                "per_page": {
                    "type": "integer",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 50,
                },
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
        "description": """자치법규(조례 등)만 검색합니다. 지역 조례·규칙 실마리가 필요할 때 legal_qa_tool 대신 사용할 수 있습니다. query와 local_government 중 하나 이상을 넣으세요.

판단 유보: 본 도구는 검색 결과만 제공하며 법적 판단을 대신하지 않습니다.

금지: 이모지, 단정적 결론, API 링크 노출""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "조례명 또는 검색 키워드",
                },
                "local_government": {
                    "type": "string",
                    "description": "지방자치단체 명칭 필터 (예: 서울시, 부산시)",
                },
                "page": {"type": "integer", "default": 1, "minimum": 1},
                "per_page": {
                    "type": "integer",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 50,
                },
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
        "description": """행정규칙만 검색합니다. 부처 훈령·예규 등 실마리가 필요할 때 legal_qa_tool 대신 사용할 수 있습니다. query와 agency 중 하나 이상을 넣으세요.

판단 유보: 본 도구는 검색 결과만 제공하며 법적 판단을 대신하지 않습니다.

금지: 이모지, 단정적 결론, API 링크 노출""",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "행정규칙명 또는 검색 키워드",
                },
                "agency": {
                    "type": "string",
                    "description": "부처명 (예: 고용노동부, 교육부). 저장소 매핑에 있는 명칭만 기관 필터로 적용될 수 있습니다.",
                },
                "page": {"type": "integer", "default": 1, "minimum": 1},
                "per_page": {
                    "type": "integer",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 50,
                },
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
    {
        "name": "ministry_interpretation_tool",
        "priority": 6,
        "category": "law_interpretation",
        "description": """특정 부처의 법령해석(질의회신)을 검색합니다. 39개 부처별 전용 법령해석 데이터베이스를 지원합니다.

지원 부처: 고용노동부, 국토교통부, 기획재정부, 해양수산부, 행정안전부, 기후에너지환경부, 관세청, 국세청, 교육부, 과학기술정보통신부, 국가보훈부, 국방부, 농림축산식품부, 문화체육관광부, 법무부, 보건복지부, 산업통상자원부, 성평등가족부, 외교부, 중소벤처기업부, 통일부, 법제처, 식품의약품안전처, 인사혁신처, 기상청, 국가유산청, 농촌진흥청, 경찰청, 방위사업청, 병무청, 산림청, 소방청, 재외동포청, 조달청, 질병관리청, 국가데이터처, 지식재산처, 해양경찰청, 행정중심복합도시건설청

판단 유보: 본 도구는 검색 결과만 제공하며 법적 판단을 대신하지 않습니다.

금지: 이모지, 단정적 결론, API 링크 노출""",
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
        "description": """법령 변경이력 또는 조문별 개정이력을 조회합니다. 특정 법령이 언제, 어떻게 개정되었는지 파악할 때 사용합니다.

search_type 선택:
- "law_change": 법령 변경이력 목록 (lsHstInf)
- "article_change": 일자별 조문 개정이력 (lsJoHstInf 목록)
- "article_detail": 특정 조문의 개정이력 상세 (lsJoHstInf 본문, law_id 필수)

판단 유보: 본 도구는 검색 결과만 제공하며 법적 판단을 대신하지 않습니다.""",
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
        "description": """법령 부가 정보를 조회합니다. 영문법령, 조약, 법령 체계도, 한눈보기, 법령명 약칭 등을 검색할 수 있습니다.

info_type 선택:
- "english_law": 영문법령 검색 (elaw)
- "treaty": 국제조약 검색 (trty)
- "structure": 법령 체계도 검색 (lsStmd)
- "oneview": 한눈보기 검색 (법령 한눈 요약, oneview)
- "abbreviation": 법령명 약칭 검색 (lsAbrv)
- "deleted": 삭제된 법령·조문 이력 (delHst)

판단 유보: 본 도구는 검색 결과만 제공하며 법적 판단을 대신하지 않습니다.""",
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
        "description": """법령·행정규칙·자치법규의 별표서식을 검색합니다. 서식명이나 관련 법령명으로 검색할 수 있습니다.

form_type 선택:
- "law": 법령 별표서식 (licbyl)
- "admin_rule": 행정규칙 별표서식 (admbyl)
- "ordinance": 자치법규 별표서식 (ordinbyl)

판단 유보: 본 도구는 검색 결과만 제공하며 법적 판단을 대신하지 않습니다.""",
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
        "description": """법령과 자치법규(조례) 간의 연계 정보를 조회합니다. 특정 법령에 연계된 조례 목록, 소관부처별 연계 현황 등을 확인할 수 있습니다.

link_type 선택:
- "law_to_ordinance": 법령-자치법규 연계 목록 (lnkLs)
- "ordinance_articles": 연계 법령별 조례 조문 목록 (lnkLsOrdJo)
- "by_department": 연계 법령 소관부처별 목록 (lnkDep)
- "linked_ordinance": 연계 조례 목록 (lnkOrd)
- "law_linked_ordinance": 연계 법령별 조례 목록 (lnkLsOrd)
- "by_region": 연계 조례 지자체별 목록 (lnkOrg)

판단 유보: 본 도구는 검색 결과만 제공하며 법적 판단을 대신하지 않습니다.""",
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
    {
        "name": "health",
        "priority": 2,
        "category": "utility",
        "description": "서비스 상태를 확인합니다. API 키 설정 상태, 환경 변수, 서버 상태 등을 확인할 때 사용합니다. 예: '서버 상태 확인', 'API 키 설정 확인'.",
        "inputSchema": {
            "type": "object",
            "additionalProperties": False
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
                "api_status": {"type": "string"}
            }
        }
    },
]
