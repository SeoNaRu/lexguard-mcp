"""
MCP Routes - MCP Streamable HTTP 엔드포인트 (3개 핵심 툴만)
Controller 패턴: 요청을 받아 Service를 호출
"""
import json
import asyncio
import copy
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from starlette.requests import ClientDisconnect
from ..services.law_service import LawService
from ..services.health_service import HealthService
from ..services.smart_search_service import SmartSearchService
from ..services.situation_guidance_service import SituationGuidanceService
from ..utils.response_truncator import shrink_response_bytes
import logging

logger = logging.getLogger("lexguard-mcp")


def register_mcp_routes(api: FastAPI, law_service: LawService, health_service: HealthService):
    """MCP Streamable HTTP 엔드포인트 등록 (3개 핵심 툴만)"""
    smart_search_service = SmartSearchService()
    situation_guidance_service = SituationGuidanceService()
    
    # 모든 요청 로깅 미들웨어 (디버깅용) - Health Check 요청 제외
    @api.middleware("http")
    async def log_all_requests(request: Request, call_next):
        is_health_check = (
            request.url.path == "/health" or 
            request.headers.get("render-health-check") == "1"
        )
        
        if not is_health_check:
            logger.info("=" * 80)
            logger.info(f"ALL REQUEST: {request.method} {request.url}")
            logger.info(f"Client: {request.client}")
            logger.info(f"Path: {request.url.path}")
            logger.info(f"Headers: {dict(request.headers)}")
        
        try:
            response = await call_next(request)
            
            if not is_health_check:
                logger.info(f"Response Status: {response.status_code}")
                logger.info("=" * 80)
            
            return response
        except Exception as e:
            logger.exception(f"Request error: {e}")
            if not is_health_check:
                logger.info("=" * 80)
            raise
    
    @api.options("/mcp")
    async def mcp_options(request: Request):
        """CORS preflight 요청 처리"""
        logger.info("MCP OPTIONS request received")
        from fastapi.responses import Response
        return Response(
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Accept, Mcp-Session-Id",
                "Access-Control-Max-Age": "86400"
            }
        )
    
    @api.get("/mcp")
    async def mcp_get_sse_stream(request: Request):
        """MCP Streamable HTTP GET 엔드포인트"""
        accept_header = request.headers.get("Accept", "")
        logger.info("=" * 80)
        logger.info("MCP GET request received")
        logger.info(f"Accept: {accept_header}")
        logger.info(f"Client: {request.client}")
        logger.info(f"Headers: {dict(request.headers)}")
        logger.info("=" * 80)
        
        if accept_header and "text/event-stream" not in accept_header and "*/*" not in accept_header:
            from fastapi import HTTPException
            logger.warning("MCP GET: Unsupported Accept header: %s", accept_header)
            raise HTTPException(status_code=405, detail="Method Not Allowed: SSE stream not supported")
        
        async def server_to_client_stream():
            yield f"data: {json.dumps({'type': 'stream_opened'})}\n\n"
            try:
                while True:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                logger.debug("SSE stream closed by client")
        
        return StreamingResponse(
            server_to_client_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    
    @api.post("/mcp")
    async def mcp_streamable_http(request: Request):
        """
        MCP Streamable HTTP 엔드포인트 (3개 핵심 툴만)
        JSON-RPC 2.0 메시지를 받아서 SSE로 스트리밍 응답
        """
        accept_header = request.headers.get("Accept", "")
        content_type_header = request.headers.get("Content-Type", "")
        session_id_header = request.headers.get("Mcp-Session-Id", "")
        origin_header = request.headers.get("Origin", "")
        # 요청 본문을 먼저 읽어서 캐시 (한 번만 읽을 수 있으므로)
        try:
            cached_body = await request.body()
            cached_body_text = cached_body.decode("utf-8")
        except ClientDisconnect:
            logger.info("⚠️ Client disconnected before POST handler could read body")
            cached_body = b""
            cached_body_text = ""
        except Exception as e:
            logger.error("❌ Failed to read request body in POST handler: %s", e)
            cached_body = b""
            cached_body_text = ""
        
        logger.info("=" * 80)
        logger.info("MCP POST REQUEST RECEIVED")
        logger.info("  Method: POST")
        logger.info("  Path: /mcp")
        logger.info("  Headers:")
        logger.info("    Accept: %s", accept_header)
        logger.info("    Content-Type: %s", content_type_header)
        logger.info("    Mcp-Session-Id: %s", session_id_header or "(없음)")
        logger.info("    Origin: %s", origin_header or "(없음)")
        logger.info("  Body length: %d bytes", len(cached_body))
        if cached_body_text:
            logger.info("  Body preview: %s", cached_body_text[:200])
        logger.info("=" * 80)
        
        async def generate():
            logger.info("=" * 80)
            logger.info("🔄 SSE GENERATE STARTED - Client is consuming the stream")
            logger.info("=" * 80)
            
            body_bytes = cached_body
            body_text = cached_body_text
            
            if not body_bytes:
                logger.warning("⚠️ Empty request body")
                return
            
            try:
                logger.info("📝 Processing MCP request: %s", body_text[:200] if body_text else "empty")
                
                data = json.loads(body_text)
                request_id = data.get("id")
                method = data.get("method")
                params = data.get("params", {})
                
                # initialize 처리
                if method == "initialize":
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "protocolVersion": "2025-06-18",
                            "capabilities": {
                                "tools": {}
                            },
                            "serverInfo": {
                                "name": "lexguard-mcp",
                                "version": "1.0.0"
                            }
                        }
                    }
                    response_json = json.dumps(response, ensure_ascii=False)
                    logger.info("MCP: initialize response | length=%d", len(response_json))
                    logger.info("Response Status: 200")
                    logger.info("=" * 80)
                    yield f"data: {response_json}\n\n"
                
                # notifications/initialized 처리
                elif method == "notifications/initialized":
                    logger.info("Response Status: 200")
                    logger.info("=" * 80)
                    return
                
                # tools/list 처리 (3개 툴만)
                elif method == "tools/list":
                    tools_list = [
                        {
                            "name": "legal_qa_tool",
                            "priority": 1,
                            "category": "integrated",
                            "description": """**범용 법률 QA 툴 (메인 진입점, 최우선 사용 권장)**: 
모든 법률 질문에 완벽하게 대응하는 통합 파이프라인입니다.

**특징**:
- 172개 DRF API 완전 활용
- 10개 도메인 자동 감지 (노동/개인정보/세금/금융/부동산/소비자/환경/보건/교육/교통)
- Intent 세분화 (근로자성/해고/임금 등)
- 시간 조건 자동 파싱 ("최근 5년", "2023년 이후")
- 다단계 검색 (법령→판례→해석→위원회→특별심판)
- 도메인별 최적 검색 순서

**사용 예시**:
- "프리랜서인데 근로자성 인정된 판례 있나요?" → 노동 도메인, 근로기준법+판례+노동위원회
- "개인정보 유출됐는데 어떻게 해야 하나요?" → 개인정보 도메인, 개인정보보호법+위원회 결정
- "최근 3년 부당해고 판례" → 노동+시간조건, 2022년 이후 판례만

**!!! 중요: 답변 작성 필수 규칙 (반드시 준수) !!!**

당신은 법률 전문가입니다. 다음 규칙을 **반드시** 따라야 합니다:

【금지 사항】
❌ "~를 참고하세요", "~를 확인하세요" 같은 막연한 표현 절대 금지
❌ "검토가 필요합니다", "상담을 받으세요" 같은 수동적 표현 금지
❌ "관련 법령은 다음과 같습니다" 후 법령명만 나열 금지
❌ JSON API 링크를 사용자에게 보여주는 것 절대 금지
❌ "자세히 보기" 같은 링크 텍스트 금지

【필수 포함 사항】
✅ **법령 조문 전체 인용**: "근로기준법 제2조 제1항 제1호는 '근로자란...'이라고 정의합니다"
✅ **판례 사건번호와 판시사항**: "대법원 2006다81488 판결은 '실질적 사용종속관계...'라고 판시했습니다"
✅ **구체적 법적 분석**: 왜 문제인지, 어떤 법률 위반인지 명확히 설명
✅ **실무적 조치 방법**: "따라서 ~해야 합니다", "~할 수 있습니다"
✅ **단정적 표현**: "~입니다", "~해야 합니다" (애매한 표현 금지)

【답변 구조】
1️⃣ 법령 조문 인용 (정확한 조문 번호와 내용)
2️⃣ 판례 분석 (사건번호, 판시 내용, 판단 기준)
3️⃣ 법적 분석 (왜 문제인지, 어떤 위험이 있는지)
4️⃣ 실무 조언 (구체적 조치 방법)

**필수 답변 템플릿 (이 형식을 반드시 따르세요)**:

```
📋 법률 상담 결과

귀하의 질문에 대해 관련 법령과 판례를 바탕으로 답변드립니다.

🔍 핵심 쟁점
[사용자 질문의 핵심 쟁점 요약]

📌 관련 법령
[법령명] 제○조 (조문명)
"[조문 내용 인용]"
→ [법령의 의미와 적용]

📌 관련 판례
[판례명 또는 사건번호]
"[판시 내용]"
→ [판례가 시사하는 바]

⚖️ 법적 분석
[구체적인 판단 기준]
- [기준 1]
- [기준 2]

💡 결론
[질문에 대한 명확한 답변]
[실무적 조언]

ℹ️ 안내
본 답변은 법적 판단을 대신하지 않으며, 국가법령정보센터의 공개된 법령·판례 정보를 바탕으로 참고할 수 있는 법적 근거의 실마리를 제공하는 목적입니다.
```

**실제 예시**: "4대보험 안 들었는데 근로자 인정된 사례가 있나요?" 질문에 대한 답변은 위의 템플릿 형식으로 작성하되, 근로기준법 제2조, 대법원 2006다81488 판결 등을 구체적으로 인용하여 답변하세요."

**응답 구조**:
```json
{
  "success": true,
  "has_legal_basis": true,
  "domain": "labor",
  "detected_intent": "labor_worker_status",
  "results": {
    "laws": [...],
    "precedents": [...],
    "interpretations": [...],
    "committee_decisions": [...]
  },
  "sources_count": {"law": 2, "precedent": 3, "interpretation": 1},
  "total_sources": 6,
  "pipeline_version": "v2_complete_coverage"
}
```""",
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
                            "description": """**문서/계약서 조항 분석 툴**: 
계약서·약관 텍스트를 입력받아 조항별 이슈와 법적 근거를 자동으로 찾아줍니다.

**특징**:
- 문서 타입 자동 추론 (labor/lease/terms/other)
- 조항별 이슈 태그 자동 생성
- 문서 타입별 맞춤 검색어 추천
- 금지 키워드 필터링 (용역→임대차 제외)
- 조항별 자동 검색 옵션

**사용 예시**:
- 프리랜서 용역 계약서 → 근로기준법, 근로자성 판례
- 임대차 계약서 → 주택임대차보호법, 보증금 반환 판례
- 서비스 이용약관 → 약관법, 불공정약관 판례

**!!! 중요: 계약서 분석 필수 규칙 (반드시 준수) !!!**

당신은 계약서 검토 전문 변호사입니다. 다음 규칙을 **반드시** 따라야 합니다:

【금지 사항】
❌ "검토가 필요합니다", "참고하세요" 같은 막연한 표현 절대 금지
❌ "관련 법령: 근로기준법" 후 설명 없이 끝내는 것 금지
❌ "~하는 것이 좋습니다" 같은 애매한 권유 금지
❌ "추천 검색어"를 사용자에게 보여주는 것 금지
❌ 조항만 나열하고 구체적 법적 분석 없는 것 금지

【필수 포함 사항】
✅ **조항별 심각도**: "이 조항은 중대한/심각한/경미한 문제가 있습니다"
✅ **위반 법령 조문**: "근로기준법 제23조 제1항은 '사용자는...'라고 규정합니다"
✅ **판례 기준**: "대법원 2006다81488 판결은 '...'라고 판시했습니다"
✅ **구체적 위험**: "만약 소송이 제기되면 이 조항은 무효로 판단될 가능성이 높습니다"
✅ **수정 제안**: "이 조항을 '...'로 수정해야 합니다"

【답변 구조 (조항별)】
1️⃣ 심각도 판단: "[중대/심각/경미] 문제가 있습니다"
2️⃣ 위반 법령: "○○법 제○조는 '...'라고 규정합니다"
3️⃣ 판례 분석: "대법원 ○○판결은 '...'라고 판시했습니다"
4️⃣ 법적 위험: "이 조항은 ○○ 위험이 있습니다"
5️⃣ 구체적 조치: "따라서 '...'로 수정해야 합니다"

**필수 답변 템플릿 (이 형식을 반드시 따르세요)**:

```
📄 [계약서 종류] 검토 결과 (법적 쟁점 요약)

제공해주신 계약서에는 [당사자]에게 불리할 수 있는 조항들이 포함되어 있습니다. 주요 쟁점은 다음과 같습니다.

1️⃣ 제○조 (조항명) – [문제 유형]

"[조항 내용 인용]"

- [구체적 문제점 1]
- [구체적 문제점 2]
- [법적 위험]

📌 관련 법령 실마리
- [법령명] 제○조 (조문명)
- [판례: 사건번호 또는 판시 내용]

2️⃣ 제○조 (조항명) – [문제 유형]

"[조항 내용 인용]"

- [구체적 문제점 1]
- [구체적 문제점 2]
- [법적 위험]

📌 관련 법령 실마리
- [법령명] 제○조
- [판례 또는 법리]

⚠️ 종합 의견

해당 계약서는 형식상 [계약 유형]이지만,
일부 조항은 [당사자]에게 과도하게 불리하거나 무효로 다툼의 여지가 있는 내용을 포함하고 있습니다.

실제 효력 판단이나 분쟁 대응은 개별 사정에 따라 달라질 수 있으므로,
계약 체결 전 또는 분쟁 발생 시에는 **전문가(변호사·법률구조기관)**의 상담을 권장드립니다.

ℹ️ 안내

본 답변은 법적 판단을 대신하지 않으며,
국가법령정보센터의 공개된 법령·판례 정보를 바탕으로
검토 시 참고할 수 있는 법적 근거의 실마리를 제공하는 목적입니다.
```

**실제 답변 예시**:

```
📄 용역 계약서 검토 결과 (법적 쟁점 요약)

제공해주신 용역 계약서에는 을(근로자)에게 불리할 수 있는 조항들이 포함되어 있습니다. 주요 쟁점은 다음과 같습니다.

1️⃣ 제2조 (업무 시간 및 장소) – 근로자성 판단 쟁점

"을은 갑이 지정하는 시간과 장소에서 업무를 수행하여야 하며, 갑의 업무 지시 및 내부 규정을 준수하여야 한다."

- 시간과 장소가 사용자에 의해 일방적으로 지정됨
- 업무 지시 및 내부 규정 준수 의무는 전형적인 사용종속관계
- 계약 형식은 용역이지만 실질은 근로관계일 가능성 높음

📌 관련 법령 실마리
- 근로기준법 제2조 제1항 제1호 (근로자의 정의)
- 대법원 2006다81488: 실질적 사용종속관계가 있으면 근로자로 인정

2️⃣ 제3조 (계약 기간) – 일방적 해지 조항 문제

"갑은 필요 시 사전 통보 없이 계약을 해지할 수 있다."

- 해지 사유와 절차가 명시되지 않음
- 사전 통보 없는 즉시 해지는 근로기준법 위반 소지
- 만약 근로관계로 판단되면 부당해고에 해당

📌 관련 법령 실마리
- 근로기준법 제23조 (해고 제한), 제26조 (해고의 예고)
- 대법원: 정당한 이유 없는 해고는 무효

3️⃣ 제5조 (손해배상) – 과다한 손해배상 조항

"을의 귀책 사유로 손해가 발생한 경우, 을은 그 손해 전부를 배상하여야 한다. 손해액의 산정 기준은 갑이 정한다."

- 손해 전부를 배상한다는 것은 과도한 책임 전가
- 손해액 산정을 일방이 정하는 것은 불공정
- 약관규제법상 무효 조항에 해당할 가능성

📌 관련 법령 실마리
- 민법 제398조 (손해배상의 범위 및 감액)
- 약관규제법 제6조 (불공정 약관조항의 금지)

⚠️ 종합 의견

해당 계약서는 형식상 용역 계약이지만,
일부 조항은 을에게 과도하게 불리하거나 무효로 다툼의 여지가 있는 내용을 포함하고 있습니다.
특히 실질적 사용종속관계가 인정되면 근로관계로 판단될 수 있으므로, 근로기준법상 보호를 받을 수 있습니다.

실제 효력 판단이나 분쟁 대응은 개별 사정에 따라 달라질 수 있으므로,
계약 체결 전 또는 분쟁 발생 시에는 **전문가(변호사·법률구조기관)**의 상담을 권장드립니다.

ℹ️ 안내

본 답변은 법적 판단을 대신하지 않으며,
국가법령정보센터의 공개된 법령·판례 정보를 바탕으로
검토 시 참고할 수 있는 법적 근거의 실마리를 제공하는 목적입니다.
```

**응답 구조**:
```json
{
  "success": true,
  "document_analysis": {
    "document_type": "노동/용역 계약서",
    "document_type_code": "labor",
    "clauses": ["제1조 ...", "제2조 ..."],
    "clause_issues": [...],
    "suggested_queries": ["근로자성 판단 기준", "용역계약 손해배상"]
  },
  "evidence_results": [...],
  "legal_basis_block": {...}
}
```""",
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
                        }
                    ]
                    
                    # MCP 표준 필드만 노출
                    mcp_tools = []
                    for tool in tools_list:
                        annotations = {}
                        if "priority" in tool:
                            annotations["priority"] = tool.get("priority")
                        if "category" in tool:
                            annotations["category"] = tool.get("category")
                        filtered = {
                            "name": tool.get("name"),
                            "description": tool.get("description"),
                            "inputSchema": tool.get("inputSchema"),
                            "outputSchema": tool.get("outputSchema")
                        }
                        filtered = {k: v for k, v in filtered.items() if v is not None}
                        if annotations:
                            filtered["annotations"] = annotations
                        mcp_tools.append(filtered)
                    
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "result": {
                            "tools": mcp_tools
                        }
                    }
                    response_json = json.dumps(response, ensure_ascii=False)
                    logger.info("MCP: tools/list response | length=%d tools_count=%d",
                               len(response_json),
                               len(mcp_tools))
                    yield f"data: {response_json}\n\n"
                
                # tools/call 처리 (3개 툴만)
                elif method == "tools/call":
                    tool_name = params.get("name")
                    arguments = params.get("arguments", {})
                    
                    logger.info("MCP tool call | tool=%s arguments=%s", tool_name, arguments)
                    
                    result = None
                    try:
                        if tool_name == "health":
                            result = await health_service.check_health()
                        
                        elif tool_name == "legal_qa_tool":
                            query = arguments.get("query")
                            max_results = arguments.get("max_results_per_type", 3)
                            logger.debug("Calling comprehensive_search_v2 | query=%s max_results=%d",
                                       query, max_results)
                            result = await smart_search_service.comprehensive_search_v2(
                                query,
                                max_results
                            )
                        
                        elif tool_name == "document_issue_tool":
                            document_text = arguments.get("document_text")
                            auto_search = arguments.get("auto_search", True)
                            max_clauses = arguments.get("max_clauses", 3)
                            max_results = arguments.get("max_results_per_type", 3)
                            logger.debug("Calling document_issue_tool | doc_len=%d auto_search=%s max_clauses=%d max_results=%d",
                                       len(document_text) if document_text else 0,
                                       auto_search, max_clauses, max_results)
                            result = await situation_guidance_service.document_issue_analysis(
                                document_text,
                                auto_search,
                                max_clauses,
                                max_results
                            )
                        
                        else:
                            result = {"error": f"Unknown tool: {tool_name}"}
                    
                    except Exception as e:
                        logger.error("Tool call error | tool=%s error=%s", tool_name, str(e), exc_info=True)
                        result = {"error": str(e)}
                    
                    # Response 생성 및 전송
                    if result:
                        # JSON 직렬화를 위해 데이터 정리
                        def clean_for_json(obj):
                            if isinstance(obj, dict):
                                return {k: clean_for_json(v) for k, v in obj.items()}
                            elif isinstance(obj, list):
                                return [clean_for_json(item) for item in obj]
                            elif isinstance(obj, str):
                                return "".join(ch for ch in obj if ord(ch) not in range(0x00, 0x09) and ord(ch) not in range(0x0B, 0x0D) and ord(ch) not in range(0x0E, 0x20))
                            else:
                                return obj
                        
                        cleaned_result = clean_for_json(result)
                        final_result = copy.deepcopy(cleaned_result)
                        final_result = shrink_response_bytes(final_result, request_id)
                        
                        # MCP 표준 형식으로 변환
                        from ..utils.response_formatter import format_mcp_response
                        mcp_formatted = format_mcp_response(final_result, tool_name)
                        
                        response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "result": mcp_formatted
                        }
                        response_json = json.dumps(response, ensure_ascii=False)
                        logger.info("MCP: Sending final response | tool=%s has_error=%s result_size=%d",
                                   tool_name, "error" in final_result, len(json.dumps(final_result, ensure_ascii=False)))
                        logger.info("MCP: Response JSON length=%d (first 300 chars): %s",
                                   len(response_json), response_json[:300])
                        logger.info("MCP: Yielding SSE event | length=%d", len(response_json))
                        yield f"data: {response_json}\n\n"
                    else:
                        error_response = {
                            "jsonrpc": "2.0",
                            "id": request_id,
                            "error": {
                                "code": -32603,
                                "message": "Tool returned no result"
                            }
                        }
                        yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"
                
                else:
                    error_response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        "error": {
                            "code": -32601,
                            "message": f"Unknown method: {method}"
                        }
                    }
                    yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"
            
            except json.JSONDecodeError as e:
                logger.error("Invalid JSON in request body: %s", e, exc_info=True)
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": "Parse error: Invalid JSON"
                    }
                }
                yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"
            except Exception as e:
                logger.error("MCP request processing error: %s", e, exc_info=True)
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request_id if 'request_id' in locals() else None,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}"
                    }
                }
                yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"
        
        logger.info("MCP POST RESPONSE (SSE)")
        logger.info("  Status: 200")
        logger.info("  Content-Type: text/event-stream")
        logger.info("=" * 80)
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream"
        )

