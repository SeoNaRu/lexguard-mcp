# ⚖️ 한국 법률/판례 검색 MCP

법은 필요할 때마다 늘 멀고 어렵게 느껴집니다.
높은 수임료와 낯선 전문 용어 때문에, 많은 사람들은 법의 도움을 받는 것 자체를 부담스러워합니다.

법실마리는 이런 거리감을 조금이라도 줄이고 싶다는 마음에서 시작된 MCP입니다.
사람의 말로 질문하면 AI가 먼저 이해하고, 국가법령정보센터의 공식 데이터를 바탕으로 법령, 조문, 판례, 법령해석, 행정심판, 헌재결정 등 법적 근거의 실마리를 찾아 제공합니다.
판단을 대신하지는 않지만, 법을 처음 마주하는 순간이 덜 어렵고 덜 무섭기를 바랍니다.

**예시**:

- "형법 제1조 내용 알려줘"
- "개인정보보호법 관련 법령 검색해줘"
- "근로기준법에서 해고 관련 조문 찾아줘"

## ✨ 주요 기능

- **통합 법률 QA** - 법령, 판례, 해석, 위원회 결정 등을 자동으로 검색하여 종합 답변 제공 🔍
- **문서 분석** - 계약서/약관 분석 후 조항별 법적 이슈 자동 검출 📋
- **172개 DRF API 활용** - 국가법령정보센터의 모든 API를 완전 통합 🚀
- **도메인 자동 감지** - 10개 법률 도메인 자동 분류 (노동/개인정보/세금/금융 등) 🎯
- **시간 조건 파싱** - "최근 5년", "2023년 이후" 등 자연어 시간 표현 자동 처리 ⏰

## 🛠️ 기술 스택

- **FastAPI** - HTTP 서버 및 MCP Streamable HTTP 구현
- **Pydantic** - 데이터 검증
- **Requests** - HTTP 요청
- **Cachetools** - TTL 캐싱
- **Python-dotenv** - 환경 변수 관리

## 📦 설치 및 설정

### 1) 의존성 설치

```bash
pip install -r requirements.txt
```

### 2) API 키 발급 (선택사항)

1. [국가법령정보센터 OPEN API](https://open.law.go.kr/) 접속
2. 회원가입 및 OPEN API 신청
3. API 키 발급

> 💡 **참고**: API 키 없이도 일부 기능을 사용할 수 있지만, API 키가 있으면 더 많은 기능과 안정적인 서비스를 이용할 수 있습니다.

### 3) .env 파일 생성

```bash
cp env.example .env
```

`.env` 파일을 다음과 같이 작성합니다:

```env
LAW_API_KEY=your_api_key_here  # 선택사항
LOG_LEVEL=INFO
PORT=8099
```

## 🚀 서버 실행

### 직접 실행 (권장)

**uvicorn 사용:**

```bash
python -m uvicorn src.main:api --host 0.0.0.0 --port 8099
```

**또는:**

```bash
python -m src.main
```

서버는 기본적으로 `http://localhost:8099`에서 실행됩니다.

> ⚠️ **참고**: `python src/main.py`는 상대 import 문제로 작동하지 않을 수 있습니다. `python -m` 옵션을 사용하세요.

### 포트 충돌 해결

포트 8099가 이미 사용 중인 경우:

1. **다른 포트 사용:**

   ```bash
   $env:PORT=8100; python -m uvicorn src.main:api --host 0.0.0.0 --port 8100
   ```

2. **사용 중인 프로세스 종료:**

   ```powershell
   # 포트 사용 프로세스 확인
   netstat -ano | findstr :8099

   # 프로세스 종료 (PID를 위 명령어 결과에서 확인)
   Stop-Process -Id <PID> -Force
   ```

서버는 기본적으로 `http://localhost:8099`에서 실행됩니다.

## 🔌 MCP 클라이언트 설정

### 원격 서버 사용 (권장)

배포된 서버를 사용하는 경우:

**Claude Desktop 설정:**

```json
{
  "mcpServers": {
    "lexguard-mcp": {
      "url": "https://lexguard-mcp.onrender.com/mcp"
    }
  }
}
```

### 로컬 서버 사용

로컬에서 실행하는 경우:

**파일 위치:**

- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**설정 예시:**

```json
{
  "mcpServers": {
    "lexguard-mcp": {
      "command": "python",
      "args": ["-m", "src.main"],
      "cwd": "C:/Users/seonaru/Desktop/LexGuardMcp",
      "env": {
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### Cursor 설정

**파일 위치**: `%USERPROFILE%\.cursor\mcp.json` (Windows)

**로컬 서버 사용**:

```json
{
  "mcpServers": {
    "lexguard-mcp": {
      "url": "http://127.0.0.1:8099/mcp"
    }
  }
}
```

**원격 서버 사용**:

```json
{
  "mcpServers": {
    "lexguard-mcp": {
      "url": "https://lexguard-mcp.onrender.com/mcp"
    }
  }
}
```

> ⚠️ **주의**: Cursor에서 MCP 설정 변경 후에는 Cursor를 완전히 재시작해야 합니다.

### ChatGPT / Gemini 설정

ChatGPT나 Gemini에서 MCP 서버를 사용하려면 각 플랫폼의 MCP 설정 방법을 참고하세요.

## 🧰 제공 툴

현재 **3개의 핵심 툴**을 제공합니다:

### 1. 🎯 legal_qa_tool (범용 법률 QA 툴)

**메인 진입점 - 모든 법률 질문에 사용**

- 172개 DRF API 완전 활용
- 10개 도메인 자동 감지 (노동/개인정보/세금/금융/부동산/소비자/환경/보건/교육/교통)
- Intent 세분화 (근로자성/해고/임금 등)
- 시간 조건 자동 파싱 ("최근 5년", "2023년 이후")
- 다단계 검색 (법령→판례→해석→위원회→특별심판)
- 도메인별 최적 검색 순서

**사용 예시**:

```
"프리랜서인데 근로자성 인정된 판례 있나요?"
→ 노동 도메인, 근로기준법+판례+노동위원회

"개인정보 유출됐는데 어떻게 해야 하나요?"
→ 개인정보 도메인, 개인정보보호법+위원회 결정

"최근 3년 부당해고 판례"
→ 노동+시간조건, 2022년 이후 판례만
```

### 2. 📄 document_issue_tool (문서/계약서 분석 툴)

**계약서·약관 조항별 이슈 자동 분석**

- 문서 타입 자동 추론 (labor/lease/terms/other)
- 조항별 이슈 태그 자동 생성
- 문서 타입별 맞춤 검색어 추천
- 금지 키워드 필터링 (용역→임대차 제외)
- 조항별 자동 검색 옵션

**사용 예시**:

```
프리랜서 용역 계약서 → 근로기준법, 근로자성 판례
임대차 계약서 → 주택임대차보호법, 보증금 반환 판례
서비스 이용약관 → 약관법, 불공정약관 판례
```

### 3. 🏥 health (서비스 상태 확인)

**API 키 설정 상태 및 서버 상태 확인**

- API 키 설정 여부 확인
- 환경 변수 상태 점검
- 서버 실행 상태 확인

**상세 정보**: MCP 서버의 `tools/list` 엔드포인트를 통해 확인할 수 있습니다.

> 💡 **참고**: 이전 버전의 20개 개별 툴은 통합되어 `legal_qa_tool`과 `document_issue_tool`에서 자동으로 호출됩니다.

## 🧪 테스트

### Python 테스트 스크립트

서버가 정상적으로 동작하는지 확인:

```bash
python test_mcp.py
```

**테스트 항목**:

- Initialize 요청
- Tools/List 조회
- Health Check 도구 호출

**예상 출력**:

```
MCP Server Test Started
Server URL: http://127.0.0.1:8099/mcp

Found 3 tools:
  - legal_qa_tool
  - document_issue_tool
  - health

Status: ok
API Key: configured
All tests completed!
```

### 수동 테스트

**Health Check (HTTP GET)**:

```bash
curl http://127.0.0.1:8099/health
```

**MCP Initialize**:

```bash
curl -X POST http://127.0.0.1:8099/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}'
```

## 🏗️ 프로젝트 구조

```
LexGuardMcp/
├── src/
│   ├── main.py                              # FastAPI 서버 + MCP 엔드포인트
│   ├── config/
│   │   └── settings.py                      # 설정 및 로깅
│   ├── routes/
│   │   ├── mcp_routes.py                    # MCP Streamable HTTP 라우트
│   │   └── http_routes.py                   # 일반 HTTP 라우트
│   ├── services/
│   │   ├── smart_search_service.py          # 통합 검색 (legal_qa_tool)
│   │   ├── situation_guidance_service.py    # 문서 분석 (document_issue_tool)
│   │   ├── health_service.py                # Health Check
│   │   ├── law_service.py                   # 법령 서비스
│   │   ├── precedent_service.py             # 판례 서비스
│   │   ├── law_interpretation_service.py    # 법령해석 서비스
│   │   └── ...                              # 기타 서비스들
│   ├── repositories/
│   │   ├── base.py                          # 공통 유틸리티
│   │   ├── law_search.py                    # 법령 검색
│   │   ├── precedent_repository.py          # 판례 검색
│   │   └── ...                              # 172개 DRF API 연동
│   ├── utils/
│   │   ├── domain_classifier.py             # 도메인 자동 감지
│   │   ├── query_planner.py                 # 검색 계획 수립
│   │   ├── evidence_builder.py              # 법적 근거 구성
│   │   └── response_truncator.py            # 응답 크기 최적화
│   └── models/
│       └── schemas.py                       # 요청/응답 스키마
├── api_crawler/
│   ├── api_index.json                       # API 인덱스 (172개)
│   └── apis/                                # 개별 API 메타데이터
├── test_mcp.py                              # MCP 서버 테스트 스크립트
└── README.md                                # 이 파일
```

## 🔑 API 키 우선순위

서버는 다음 순서로 API 키를 찾습니다:

1. **우선순위 1**: `arguments.env.LAW_API_KEY` (메인 서버에서 전달)
2. **우선순위 2**: `.env` 파일의 `LAW_API_KEY` (로컬 개발용)

## ⚠️ 중요 사항

- 국가법령정보센터 API는 사용량 제한이 있을 수 있습니다. 이 서버는 캐싱을 통해 불필요한 요청을 줄입니다.
- **절대 `.env` 파일을 커밋하지 마세요!** 이미 `.gitignore`에 포함되어 있습니다.
- MCP 스펙에 따라 응답 크기는 제한될 수 있습니다. `response_truncator.py`가 자동으로 최적화합니다.

## 🔧 최근 개선 사항 (v2.0)

### 안정성 개선

- ✅ Graceful shutdown 개선으로 서버 종료 시 에러 제거
- ✅ ClientDisconnect 예외 처리로 클라이언트 연결 끊김 에러 방지
- ✅ MCP 요청 본문 사전 읽기 및 캐싱으로 디버깅 향상
- ✅ 모든 예외 처리에 명시적 로깅 추가

### 통합 및 최적화

- ✅ 20개 개별 툴 → 3개 핵심 툴로 통합 (legal_qa_tool, document_issue_tool, health)
- ✅ 172개 DRF API 완전 통합 (이전 159개에서 확장)
- ✅ 도메인 자동 감지 시스템 (10개 법률 도메인)
- ✅ Intent 세분화 (근로자성/해고/임금 등)
- ✅ 시간 조건 자동 파싱 ("최근 5년", "2023년 이후")
- ✅ 도메인별 최적 검색 순서 적용

## 🎯 사용 사례

### 🧑‍💼 일반인 사용 예시

#### 🔍 legal_qa_tool - 범용 법률 QA (가장 많이 사용)

**모든 법률 질문에 사용 가능**

- "프리랜서인데 근로자성 인정된 판례 있나요?"
  → 노동 도메인 자동 감지, 근로기준법 + 판례 + 노동위원회 통합 검색

- "개인정보 유출됐는데 어떻게 해야 하나요?"
  → 개인정보 도메인, 개인정보보호법 + 위원회 결정 자동 조회

- "최근 3년 부당해고 판례 보여줘"
  → 시간 조건 파싱, 2022년 이후 판례만 자동 필터링

- "전세 보증금 반환 관련 법 있어?"
  → 부동산 도메인, 주택임대차보호법 + 판례 통합

- "환불 거부하는데 소비자보호법 위반 아닌가요?"
  → 소비자 도메인, 소비자기본법 + 약관법 + 관련 판례

#### 📄 document_issue_tool - 문서/계약서 분석

**계약서나 약관을 붙여넣으면 자동 분석**

- **프리랜서 용역 계약서**:

  ```
  "이 계약서 문제 없는지 확인해줘"
  → 문서 타입: labor(노동)
  → 이슈: 근로자성 판단, 일방적 해지권, 손해배상 과다
  → 관련 법령: 근로기준법 + 판례 자동 검색
  ```

- **임대차 계약서**:

  ```
  "전세 계약서인데 이상한 조항 있나요?"
  → 문서 타입: lease(임대차)
  → 이슈: 보증금 반환 조건, 계약 갱신권
  → 관련 법령: 주택임대차보호법 + 판례
  ```

- **서비스 이용약관**:
  ```
  "이 약관 불공정한 거 아닌가요?"
  → 문서 타입: terms(약관)
  → 이슈: 일방적 변경권, 과도한 면책 조항
  → 관련 법령: 약관법 + 소비자보호법 + 판례
  ```

#### 🏥 health - 서버 상태 확인

**API 키 설정 및 서버 상태 점검**

- "서버 상태 확인해줘"
  → API 키 설정 여부, 환경 변수 상태, 서버 실행 상태 확인

### 🔑 핵심 사용 패턴

```
일반인 질문 (자연스러운 한국어)
  ↓
AI가 자동으로 적절한 툴 선택
  ↓
legal_qa_tool: 질문 형태 → 자동 도메인 감지 → 통합 검색
document_issue_tool: 문서 제공 → 타입 추론 → 조항별 분석
  ↓
법령 + 판례 + 해석 + 위원회 결정 등 종합 답변
```

**특징**:

- 사용자는 툴을 직접 선택하지 않음
- AI가 질문 의도를 파악하여 자동 처리
- 법률 용어를 몰라도 자연스러운 질문 가능
- 관련된 모든 법적 근거를 한 번에 제공

### 👨‍💻 개발자

**아키텍처**:

- **레이어드 아키텍처**: Routes → Services → Repositories
- **MCP Streamable HTTP**: SSE(Server-Sent Events) 기반 실시간 스트리밍
- **TTL 캐싱**: 검색 결과 30분, 실패 요청 5분 캐시
- **자동 재시도**: 네트워크 오류 시 exponential backoff

**새 기능 추가**:

- Service Layer에 비즈니스 로직 구현
- Repository Layer에서 DRF API 호출
- `api_crawler/apis/` 폴더에 API 메타데이터 추가
- `smart_search_service.py`에서 도메인별 검색 전략 정의

**테스트**:

```bash
# MCP 서버 테스트
python test_mcp.py

# 개별 서비스 테스트
python -c "from src.services.smart_search_service import SmartSearchService; ..."
```

## 📤 프로젝트 공유

다른 사람과 공유할 때:

✅ **공유 가능:**

- 모든 소스 코드 파일
- `requirements.txt`, `pyproject.toml`
- `env.example` 파일
- 모든 문서 파일

❌ **절대 공유하지 마세요:**

- `.env` 파일 (개인 API 키 포함)

## 🌐 배포 상태

**배포 완료**: 서버가 Render에 배포되어 공개 URL로 접근 가능합니다.

- **서버 URL**: `https://lexguard-mcp.onrender.com`
- **MCP 엔드포인트**: `https://lexguard-mcp.onrender.com/mcp`
- **Health Check**: `https://lexguard-mcp.onrender.com/health`

## 📝 라이선스

MIT License

## 🤝 기여

이슈 및 풀 리퀘스트는 언제나 환영합니다!

## 📞 문의

- 버그 리포트: GitHub Issues
- 기능 요청: GitHub Issues

---

**법실마리(LexGuard MCP) - 법률 정보의 실마리를 찾아드립니다.**

법은 어렵지만, 첫 실마리를 잡는 것은 쉬워질 수 있습니다.  
이 프로젝트는 AI를 통해 누구나 법률 정보에 쉽게 접근할 수 있도록 돕는 것을 목표로 합니다.
