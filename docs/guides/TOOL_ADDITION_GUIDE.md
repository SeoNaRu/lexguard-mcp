# 툴 추가 가이드

변호사 MCP에 새로운 툴을 추가하는 방법을 단계별로 설명합니다.

## 📋 사전 준비

1. **요구사항 정의**
   - 어떤 법률 정보를 제공할 툴인가?
   - 사용자가 어떤 질문을 할 때 이 툴을 사용할까?
   - 필요한 입력 파라미터는 무엇인가?

2. **API 확인**
   - `api_crawler/api_index.json`에서 사용할 API 확인
   - 또는 `list_available_apis` 툴로 사용 가능한 API 확인

---

## 🛠️ 툴 추가 단계

### 1단계: 스키마 정의 (`src/models/schemas.py`)

요청 파라미터를 정의하는 Pydantic 모델을 추가합니다.

**예시**:
```python
class SearchPrecedentRequest(BaseModel):
    query: str = Field(..., description="판례 검색어 (예: '손해배상', '계약해지')")
    page: int = Field(1, description="페이지 번호", ge=1)
    per_page: int = Field(10, description="페이지당 결과 수", ge=1, le=50)
```

**규칙**:
- `Field(..., description="...")` 형식으로 필수 파라미터 정의
- `Field(기본값, description="...")` 형식으로 선택 파라미터 정의
- `ge`, `le` 등으로 값 범위 제한
- Description은 **한국어로 명확하게** 작성 (AI가 이해하기 쉽게)

---

### 2단계: Repository 메서드 구현 (`src/repositories/`)

실제 API를 호출하고 파싱하는 로직을 작성합니다.

**파일 선택**:
- 법령 관련: `law_repository.py` 또는 `law_search.py`, `law_detail.py`
- 새로운 카테고리: 새 파일 생성 또는 적절한 파일에 추가

**예시**:
```python
def search_precedent(self, query: str, page: int = 1, per_page: int = 10, 
                     arguments: Optional[dict] = None) -> dict:
    """
    판례를 검색합니다.
    
    Args:
        query: 검색어
        page: 페이지 번호
        per_page: 페이지당 결과 수
        arguments: 추가 인자 (API 키 등)
        
    Returns:
        검색 결과 딕셔너리 또는 {"error": "error message"}
    """
    logger.debug("search_precedent called | query=%r page=%d per_page=%d", 
                 query, page, per_page)
    
    if not query or not query.strip():
        return {"error": "검색어가 비어있습니다."}
    
    # API 키 가져오기
    api_key = self.get_api_key(arguments)
    
    try:
        # API 호출
        params = {
            "target": "prec",
            "type": "JSON",
            "query": query,
            "page": page,
            "num": per_page
        }
        
        if api_key:
            params["OC"] = api_key
        
        response = requests.get(LAW_API_SEARCH_URL, params=params, timeout=10)
        response.raise_for_status()
        
        # HTML 에러 페이지 확인
        if response.text.strip().startswith('<!DOCTYPE') or '<html' in response.text.lower():
            return {
                "error": "API가 HTML 에러 페이지를 반환했습니다.",
                "note": "API 키가 유효하지 않거나 API 사용 권한이 없을 수 있습니다."
            }
        
        # JSON 파싱
        data = response.json()
        
        # 결과 가공
        result = {
            "query": query,
            "total": data.get("totalCnt", 0),
            "page": page,
            "per_page": per_page,
            "precedents": data.get("prec", [])
        }
        
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API 호출 실패: {str(e)}")
        return {"error": f"판례 검색 중 오류 발생: {str(e)}"}
```

**규칙**:
- 항상 `self.get_api_key(arguments)` 사용
- `timeout=10` 설정 필수
- HTML 에러 페이지 체크 필수
- 에러는 `{"error": "..."}` 형태로 반환
- 로깅 추가 (`logger.debug`, `logger.error`)

---

### 3단계: Service 메서드 구현 (`src/services/law_service.py`)

Repository 메서드를 비동기로 감싸는 Service 메서드를 추가합니다.

**예시**:
```python
async def search_precedent(self, req: SearchPrecedentRequest, 
                          arguments: Optional[dict] = None) -> dict:
    """판례 검색"""
    try:
        if arguments is None:
            arguments = {}
        return await asyncio.to_thread(
            self.repository.search_precedent,
            req.query,
            req.page,
            req.per_page,
            arguments
        )
    except Exception as e:
        return {"error": f"판례 검색 중 오류 발생: {str(e)}"}
```

**규칙**:
- `asyncio.to_thread`로 동기 메서드를 비동기로 변환
- `try/except`로 에러 처리
- 에러는 `{"error": "..."}` 형태로 반환

---

### 4단계: MCP 라우트 연결 (`src/routes/mcp_routes.py`)

#### 4-1. Import 추가

```python
from ..models import SearchLawRequest, ..., SearchPrecedentRequest
```

#### 4-2. `tools/list`에 툴 메타데이터 추가

`tools/list` 메서드의 `tools_list` 배열에 새 툴을 추가합니다.

**예시**:
```python
{
    "name": "search_precedent_tool",
    "description": "판례를 검색합니다. 판례명, 사건번호, 판결 요지 등으로 검색할 수 있습니다.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "판례 검색어 (예: '손해배상', '계약해지', '불법행위')"
            },
            "page": {
                "type": "integer",
                "description": "페이지 번호",
                "default": 1,
                "minimum": 1
            },
            "per_page": {
                "type": "integer",
                "description": "페이지당 결과 수",
                "default": 10,
                "minimum": 1,
                "maximum": 50
            }
        },
        "required": ["query"]
    }
}
```

**규칙**:
- `name`: 소문자, 언더스코어 사용 (예: `search_precedent_tool`)
- `description`: **한국어로 명확하게** 작성, 사용자가 어떤 질문을 할 때 사용하는지 명시
- `inputSchema`: JSON Schema 형식으로 정확히 작성
- `required`: 필수 파라미터만 포함

#### 4-3. `tools/call`에 실행 분기 추가

`tools/call` 메서드의 `elif` 분기에 새 툴 처리 로직을 추가합니다.

**예시**:
```python
elif tool_name == "search_precedent_tool":
    query = arguments.get("query")
    if not query:
        result = {"error": "필수 파라미터 누락: query"}
    else:
        page = arguments.get("page", 1)
        per_page = arguments.get("per_page", 10)
        req = SearchPrecedentRequest(query=query, page=page, per_page=per_page)
        logger.debug("Calling search_precedent | query=%s page=%d per_page=%d", 
                     query, page, per_page)
        result = await law_service.search_precedent(req, None)
```

**규칙**:
- 필수 파라미터 검증 필수
- 기본값 설정
- 로깅 추가
- Service 메서드 호출

---

### 5단계: 테스트

1. **서버 재시작**
   ```bash
   python -m src.main
   ```

2. **툴 목록 확인**
   - MCP 클라이언트에서 `tools/list` 호출하여 새 툴이 나타나는지 확인

3. **툴 실행 테스트**
   - 실제 파라미터로 `tools/call` 호출
   - 응답이 정상적으로 오는지 확인
   - 에러 케이스도 테스트

4. **자연어 질문 테스트**
   - AI에게 자연어로 질문하여 올바른 툴이 호출되는지 확인

---

### 6단계: 문서 업데이트

#### `TOOLS_LIST.md` 업데이트

새 툴에 대한 섹션을 추가합니다:

```markdown
### 8. `search_precedent_tool` - 판례 검색

**설명**: 판례를 검색합니다...

**사용된 API**: 
- `판례 목록 조회` (API ID: 386)

**파라미터**: ...

**사용 예시**: ...
```

#### `LEXGUARD_TOOL_GUIDE.md` 업데이트

테스트 질문 예시를 추가합니다:

```markdown
#### 2.8 `search_precedent_tool`

- **역할**: 판례 검색
- **매핑될 자연어 질문 예시**
  - "손해배상 관련 판례 검색해줘"
  - "계약해지 판례 찾아줘"
  ...
```

---

## ✅ 체크리스트

툴 추가 시 다음 사항을 확인하세요:

- [ ] 스키마 정의 완료 (`src/models/schemas.py`)
- [ ] Repository 메서드 구현 완료
- [ ] Service 메서드 구현 완료
- [ ] MCP 라우트 연결 완료 (`tools/list`, `tools/call`)
- [ ] Import 문 추가 완료
- [ ] 로깅 추가 완료
- [ ] 에러 처리 완료
- [ ] API 키 처리 완료
- [ ] 타임아웃 설정 완료
- [ ] HTML 에러 페이지 체크 완료
- [ ] 테스트 완료
- [ ] `TOOLS_LIST.md` 업데이트 완료
- [ ] `LEXGUARD_TOOL_GUIDE.md` 업데이트 완료

---

## 🎯 툴 설계 원칙

### 1. 사용자 중심 설계
- 일반인이 이해하기 쉬운 툴 이름과 설명
- 자연어 질문에 매핑되기 쉬운 구조

### 2. 명확한 입력/출력
- 필수/선택 파라미터 명확히 구분
- 응답 구조 일관성 유지

### 3. 에러 처리
- 모든 에러 케이스 처리
- 사용자 친화적인 에러 메시지

### 4. 성능 고려
- 적절한 타임아웃 설정
- 캐싱 활용 (필요시)

### 5. MCP 스펙 준수
- 응답 크기 24k 이하
- JSON Schema 정확히 작성
- Description 명확하게 작성

---

## 📚 참고 자료

- [MCP 심사 가이드](./MCP_COMPLIANCE_RULES.md) - 툴 설계 시 반드시 참고
- [개발 가이드](./LEXGUARD_TOOL_GUIDE.md) - 기존 툴 구현 패턴 참고
- [툴 목록](./TOOLS_LIST.md) - 기존 툴 구조 참고

---

## 💡 팁

1. **기존 툴 패턴 따르기**: `search_law_tool`이나 `get_law_detail_tool`의 구현 패턴을 참고하세요.

2. **API 메타데이터 활용**: `api_crawler/apis/` 폴더의 JSON 파일을 참고하여 API 파라미터를 정확히 파악하세요.

3. **테스트 질문 작성**: 툴을 추가한 후 실제 사용자가 할 법한 자연어 질문을 여러 개 작성해보세요.

4. **에러 케이스 고려**: API 키 없음, 네트워크 오류, 잘못된 파라미터 등 다양한 에러 케이스를 테스트하세요.

