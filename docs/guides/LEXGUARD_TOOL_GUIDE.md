## LexGuard MCP 툴 개발 가이드

이 파일은 **새 MCP 툴을 추가할 때 따라갈 표준 절차 + 테스트 질문 모음**을 담고 있습니다.  
항상 **이 순서**로 개발하면 구조가 깨지지 않습니다.

---

### 1. 새 툴 추가 전체 흐름

새 툴 하나(`some_feature_tool`)를 만든다고 할 때 진행 순서는 항상 동일합니다.

1. **요구사항/입출력 정의**
   - 어떤 문제를 푸는 툴인가?
   - 입력 파라미터는 무엇인가? (예: `law_id`, `query`, `page` 등)
   - 출력은 어떤 구조여야 하는가? (예: `articles`, `total`, `summary` 등)

2. **스키마 정의 (`src/models/schemas.py`)**
   - 요청 DTO(Pydantic 모델)를 추가합니다.
   - 예시:
     ```python
     class SomeFeatureRequest(BaseModel):
         foo: str = Field(..., description="필수 문자열 파라미터")
         page: int = Field(1, description="페이지 번호", ge=1)
     ```
   - 역할:
     - 입력 값 타입/필수 여부 검증
     - MCP 툴 메타데이터에 들어가는 설명 출처

3. **Repository 메서드 구현 (`src/repositories/law_repository.py`)**
   - 실제로 **law.go.kr 또는 다른 외부 API를 호출하고 파싱**하는 코드 작성
   - 규칙:
     - 네이밍: `def some_feature(self, ...):`
     - **API 키 처리**: 항상 `self.get_api_key(arguments)` 사용
     - HTTP 호출은 반드시 `requests.get(...)` / `requests.post(...)` + `timeout` + `raise_for_status()`
     - HTML 에러 페이지 여부 체크 (이미 있는 코드 패턴 재사용)
     - XML/JSON 파싱 후, **Python dict**로 가공해서 반환

4. **Service 메서드 구현 (`src/services/law_service.py`)**
   - Repository 메서드를 **비동기(`async`)로 감싼 래퍼**를 추가합니다.
   - 규칙:
     - 네이밍: `async def some_feature(self, req: SomeFeatureRequest, arguments: Optional[dict] = None) -> dict:`
     - `asyncio.to_thread(self.repository.some_feature, ...)` 패턴 사용
     - `try/except`로 에러를 잡아서 `"error": "..."` 형태로 반환

5. **MCP 라우트에 연결 (`src/routes/mcp_routes.py`)**
   1. **imports에 스키마 추가**
      ```python
      from ..models.schemas import SearchLawRequest, ..., SomeFeatureRequest
      ```
   2. **`tools/list`에 툴 메타데이터 추가**
      - 툴 이름, 설명, `inputSchema` 정의
   3. **`tools/call`에 실행 분기 추가**
      - `elif tool_name == "some_feature_tool":` 분기
      - `arguments`에서 파라미터 추출 → `SomeFeatureRequest(...)` 생성 → `await law_service.some_feature(...)` 호출

6. **(선택) HTTP 디버깅용 라우트 추가 (`src/routes/http_routes.py`)**
   - 필요할 때만 `/tools/some_feature` 같은 엔드포인트 추가

7. **테스트 질문 추가 (`LEXGUARD_TOOL_GUIDE.md`)**
   - 이 파일의 **툴별 테스트 질문 섹션**에 자연어 질문 예시를 반드시 추가합니다.
   - 나중에 “이 질문이면 어떤 MCP 툴을 써야 하는지”를 판단하는 기준이 됩니다.

---

### 2. 현재 구현된 툴 & 테스트 질문

아래는 **현재 코드 기준으로 구현된 MCP 툴들**과,  
각 툴을 사용하도록 유도하는 **자연어 테스트 질문 예시**입니다.

#### 2.1 `health`

- **역할**: MCP 서버 및 환경 상태 확인 (LAW_API_KEY, .env 등)
- **매핑될 자연어 질문 예시**
  - “지금 한국 법령 MCP 서버 상태 어때?”
  - “LAW_API_KEY 제대로 읽히는지 확인해줘.”
  - “헬스 체크 한번 해줘.”
  - “법령 서버 환경 설정 이상 없는지 점검해줘.”

---

#### 2.2 `search_law_tool`

- **역할**: 법령명/키워드로 법령 검색
- **주요 파라미터**: `query`, (`page`, `per_page`)
- **매핑될 자연어 질문 예시**
  - “형법 관련 법령들 검색해줘.”
  - “개인정보보호법이랑 관련된 법령들 찾아줘.”
  - “노동시간 제한에 대한 법령을 검색해줘.”
  - “손해배상과 관련된 주요 법령들 리스트업 해줘.”
  - “산재 보상에 적용되는 법령들 찾아줘.”

---

#### 2.3 `list_law_names_tool`

- **역할**: 법령명 목록 조회 (전체 + 부분 문자열 필터)
- **주요 파라미터**: (`page`, `per_page`, `query`)
- **매핑될 자연어 질문 예시**
  - “지금 기준으로 주요 법령명 목록 좀 보여줘.”
  - “이름에 ‘구조’가 들어가는 법령들 목록 보여줘.”
  - “환경 관련 법령명들 위에서부터 50개만 보여줘.”
  - “노동으로 시작하는 법령명들 싹 다 리스트로 뽑아줘.”

---

#### 2.4 `get_law_detail_tool`

- **역할**: 법령명으로 법령의 기본 정보/상세를 조회
- **주요 파라미터**: `law_name`
- **매핑될 자연어 질문 예시**
  - “‘형법’ 기본 정보랑 상세 내용 요약해줘.”
  - “‘119구조·구급에 관한 법률 시행령’이 정확히 어떤 법인지 설명해줘.”
  - “‘개인정보 보호법’의 정식 명칭, 제정일, 개정 이력 요약해줘.”
  - “근로기준법의 기본 구조랑 핵심 조항들 개괄적으로 정리해줘.”

---

#### 2.5 `get_law_articles_tool`

- **역할**: 특정 법령의 조문 전체 조회 (법령 ID 기준)
- **주의**: 내부적으로는 `get_law_detail_tool` 등을 통해 `law_id`를 먼저 알아낸 뒤 사용하는 패턴
- **주요 파라미터**: `law_id`
- **매핑될 자연어 질문 예시**
  - “‘형법’ 조문 전체 구조를 보여줘. (장·절·조 단위로 정리해서)”
  - “‘형법’에서 제1조부터 제10조까지 조문 내용만 뽑아서 보여줘.”
  - “‘119구조·구급에 관한 법률 시행령’ 전체 조문을 목록으로 정리해줘.”
  - “‘개인정보 보호법’에서 개인정보 처리의 원칙에 해당하는 조문들만 골라서 보여줘.”
  - “근로기준법에서 해고와 관련된 조문들만 추려서 설명해줘.”

---

### 3. 앞으로 툴을 추가할 때 해야 할 일 체크리스트

새 MCP 툴을 추가할 때마다 **반드시 아래 항목을 확인합니다.**

1. **스키마 추가**
   - `src/models/schemas.py`에 `*Request` 모델 추가
2. **Repository 메서드 추가**
   - `src/repositories/law_repository.py`에 실제 API 호출/파싱 메서드 추가
3. **Service 메서드 추가**
   - `src/services/law_service.py`에 비동기 래퍼 추가
4. **MCP 라우트 연결**
   - `src/routes/mcp_routes.py`:
     - `tools/list`에 툴 메타데이터 추가
     - `tools/call`에 분기(`elif tool_name == "..."`) 추가
5. **(선택) HTTP 디버깅용 엔드포인트**
   - `src/routes/http_routes.py`에 필요 시 추가
6. **이 파일 업데이트**
   - `LEXGUARD_TOOL_GUIDE.md`에:
     - 새 툴 설명 섹션 추가
     - 자연어 테스트 질문 예시 3~5개 이상 추가

이 규칙만 지키면, 나중에 **“이 질문이면 어떤 MCP 툴을 호출할까?”**를 설계할 때도  
이 파일 하나만 보면 전체 맥락을 쉽게 이해할 수 있습니다.


