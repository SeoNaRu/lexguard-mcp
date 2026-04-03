---
name: lexguard-mcp-dev
description: LexGuard MCP (한국 법률 MCP 서버) 개발 가이드. 새로운 MCP 툴 추가, Repository/Service 작성, MCP JSON-RPC 엔드포인트 수정, 법령 API 연동, 테스트 작성 시 사용. 아키텍처 패턴, 국가법령정보센터 API 규칙, 응답 형식을 자동으로 준수.
---

# LexGuard MCP 개발 가이드

## 아키텍처 패턴

```
MCP Client → POST /mcp (JSON-RPC 2.0) → mcp_routes.py → Service → Repository → law.go.kr API
```

**레이어 규칙:**
- `routes/mcp_routes.py` — JSON-RPC 파싱, SSE 스트리밍, tools/list·call, prompts/list·get
- `services/` — 비즈니스 로직, 여러 Repository 조합
- `repositories/` — 단일 법령 API 연동, BaseLawRepository 상속 필수
- `utils/` — 공통 파싱/포맷팅 (수정 시 기존 함수 재사용 우선)

## 새 MCP 툴 추가 체크리스트

1. **tools/list에 툴 스키마 추가** (`mcp_routes.py` 내 `tools_list` 배열)
2. **tools/call에 분기 추가** (tool_name 조건문)
3. **Service 메서드 작성** (기존 `SmartSearchService` 패턴 참고)
4. **README.md 업데이트**

## 새 Repository 패턴

```python
from .base import BaseLawRepository, search_cache, failure_cache, logger
import requests

class FooRepository(BaseLawRepository):
    def search_foo(self, query: str, page: int = 1, per_page: int = 10, arguments=None):
        cache_key = f"foo:{query}:{page}"
        if cache_key in search_cache:
            return search_cache[cache_key]
        if cache_key in failure_cache:
            return failure_cache[cache_key]

        params = {"target": "...", "type": "JSON", "query": query, ...}
        api_key, err = self.attach_api_key(params, arguments)
        if err:
            return err

        try:
            resp = requests.get(LAW_API_BASE_URL, params=params, timeout=10)
            validation_err = self.validate_drf_response(resp)
            if validation_err:
                failure_cache[cache_key] = validation_err
                return validation_err
            # 파싱 로직
            result = {"success": True, ...}
            search_cache[cache_key] = result
            return result
        except requests.exceptions.Timeout:
            return {"error_code": "API_ERROR_TIMEOUT", "error": "타임아웃"}
        except Exception as e:
            return {"error": str(e)}
```

## MCP JSON-RPC 응답 형식

```python
# tools/list 내 툴 스키마 구조
{
    "name": "tool_name",
    "description": "설명...\n\n금지: 이모지, 단정적 결론",
    "inputSchema": {
        "type": "object",
        "properties": {"query": {"type": "string", "description": "..."}},
        "required": ["query"]
    }
}

# tools/call 최종 응답 (format_mcp_response 통과)
{
    "jsonrpc": "2.0", "id": request_id,
    "result": {"content": [{"type": "text", "text": "..."}], "isError": False}
}

# prompts/list 응답
{
    "jsonrpc": "2.0", "id": request_id,
    "result": {"prompts": [{"name": "...", "description": "...", "arguments": [...]}]}
}
```

## 법령 API 핵심 규칙

- **API 키**: `BaseLawRepository.attach_api_key(params, arguments)` 반드시 사용
- **캐시**: `search_cache[key]` (30분), `failure_cache[key]` (5분)
- **에러 코드**: `API_ERROR_AUTH` / `API_ERROR_HTML` / `API_ERROR_TIMEOUT` / `API_ERROR_OTHER`
- **URL**: `LAW_API_BASE_URL` (lawService.do) / `LAW_API_SEARCH_URL` (lawSearch.do)
- **응답 검증**: `validate_drf_response(response)` 항상 호출

## 답변 품질 규칙 (A 타입)

툴 description에 반드시 포함:
```
금지: 이모지, 타이틀, 조문 전체 인용, 단정적 결론, API 링크 노출
필수: 판단 유보 문장, 추가 정보 요청
```

## 테스트 작성

```bash
# 실행
pytest tests/ -v

# 개별 파일
pytest tests/test_smart_search.py -v
```

테스트는 `tests/` 폴더에 작성. API 키 불필요한 순수 로직 테스트 우선.
Service는 `asyncio.run()` 또는 `pytest-asyncio` 사용.

## 자주 쓰는 파일 위치

| 목적 | 파일 |
|------|------|
| MCP 엔드포인트 수정 | `src/routes/mcp_routes.py` |
| 검색 파이프라인 | `src/services/smart_search_service.py` |
| 문서 분석 | `src/services/situation_guidance_service.py` |
| 응답 포맷 | `src/utils/response_formatter.py` |
| 캐시/기본 | `src/repositories/base.py` |
| 도메인 분류 | `src/utils/domain_classifier.py` |
