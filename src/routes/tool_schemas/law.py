"""법령 직접 조회 도구 스키마: law_article_tool, law_comparison_tool."""

SCHEMAS = [
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
                "hang": {"type": "string", "description": "항 번호 (예: '1', '2')"},
                "ho": {"type": "string", "description": "호 번호 (예: '1', '2')"},
                "mok": {"type": "string", "description": "목 번호 (예: '가', '나')"}
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
]
