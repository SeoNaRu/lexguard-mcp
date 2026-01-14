# ⚖️ 변호사 MCP (LexGuard MCP)

일반인들이 AI를 통해 법률 정보를 쉽게 조회할 수 있도록 도와주는 MCP 서버입니다.

## 🎯 프로젝트 목적

변호사 없이도 기본적인 법률 정보를 확인할 수 있도록, AI에 이 MCP를 장착하면 자연어로 법령을 검색하고 조문을 확인할 수 있습니다.

**예시**:

- "형법 제1조 내용 알려줘"
- "개인정보보호법 관련 법령 검색해줘"
- "근로기준법에서 해고 관련 조문 찾아줘"

## ✨ 주요 기능

- **법령 검색** - 법령명이나 키워드로 법령 검색 🔍
- **법령 상세 조회** - 특정 법령의 상세 정보 조회 📋
- **조문 조회** - 법령의 조문 전체 또는 단일 조문 조회 📖
- **법령명 목록** - 전체 법령명 목록 조회 및 필터링 📝
- **159개 API 지원** - 국가법령정보센터의 모든 API 활용 가능 🚀

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

### Claude Desktop

`claude_desktop_config.json`에 다음을 추가합니다:

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

### ChatGPT / Gemini 설정

ChatGPT나 Gemini에서 MCP 서버를 사용하려면 각 플랫폼의 MCP 설정 방법을 참고하세요.

## 🧰 제공 툴

현재 **7개의 핵심 툴**을 제공합니다:

1. **`health`** - 서비스 상태 확인
2. **`search_law_tool`** - 법령 검색
3. **`list_law_names_tool`** - 법령명 목록 조회
4. **`get_law_detail_tool`** - 법령 상세 정보 조회
5. **`get_law_articles_tool`** - 법령 조문 전체 목록 조회
6. **`get_single_article_tool`** - 단일 조문 조회
7. **`list_available_apis`** - 사용 가능한 API 목록 조회 (159개)

**상세 정보**: MCP 서버의 `tools/list` 엔드포인트를 통해 확인할 수 있습니다.

## 📚 문서

모든 가이드 문서는 [`docs/guides/`](./docs/guides/) 폴더에 있습니다.

### 주요 가이드
- **[해커톤 제출 가이드](./docs/guides/HACKATHON_GUIDE.md)** - 해커톤 제출 전 체크리스트 ⭐
- **[배포 가이드](./docs/guides/DEPLOYMENT_GUIDE.md)** - 원격 서버 배포 가이드 ⭐
- **[검증 체크리스트](./docs/guides/VERIFICATION_CHECKLIST.md)** - 해커톤 제출 전 검증 체크리스트
- **[MCP Inspector 가이드](./docs/guides/MCP_INSPECTOR_GUIDE.md)** - MCP Inspector 검증 가이드

### 개발 가이드
- **[툴 추가 가이드](./docs/guides/TOOL_ADDITION_GUIDE.md)** - 새 툴 추가 방법
- **[개발 가이드](./docs/guides/LEXGUARD_TOOL_GUIDE.md)** - 개발 가이드
- **[MCP 규격 준수](./docs/guides/MCP_COMPLIANCE_RULES.md)** - MCP 심사 가이드

### 기능 가이드
- **[스마트 검색 가이드](./docs/guides/SMART_SEARCH_GUIDE.md)** - 스마트 검색 사용법
- **[상황별 가이드](./docs/guides/SITUATION_GUIDANCE_GUIDE.md)** - 상황별 가이드 사용법

### 문제 해결
- **[문제 해결 가이드](./docs/guides/TROUBLESHOOTING.md)** - 자주 발생하는 문제 해결

**전체 문서 목록**: [`docs/guides/README.md`](./docs/guides/README.md)

## 🏗️ 프로젝트 구조

```
LexGuardMcp/
├── src/
│   ├── main.py              # FastAPI 서버 + MCP 엔드포인트
│   ├── routes/
│   │   └── mcp_routes.py    # MCP 라우트 (툴 등록)
│   ├── services/
│   │   └── law_service.py   # 비즈니스 로직
│   ├── repositories/
│   │   ├── law_search.py    # 법령 검색
│   │   └── law_detail.py    # 법령 조회
│   └── models/
│       └── schemas.py       # 요청/응답 스키마
├── api_crawler/
│   ├── api_index.json       # API 인덱스 (159개)
│   └── apis/                # 개별 API 메타데이터
├── TOOLS_LIST.md            # 툴 목록
├── TOOL_ADDITION_GUIDE.md   # 툴 추가 가이드
└── README.md                # 이 파일
```

## 🔑 API 키 우선순위

서버는 다음 순서로 API 키를 찾습니다:

1. **우선순위 1**: `arguments.env.LAW_API_KEY` (메인 서버에서 전달)
2. **우선순위 2**: `.env` 파일의 `LAW_API_KEY` (로컬 개발용)

## ⚠️ 중요 사항

- 국가법령정보센터 API는 사용량 제한이 있을 수 있습니다. 이 서버는 캐싱을 통해 불필요한 요청을 줄입니다.
- **절대 `.env` 파일을 커밋하지 마세요!** 이미 `.gitignore`에 포함되어 있습니다.
- MCP 스펙에 따라 응답 크기는 24k를 초과하면 안 됩니다.

## 🎯 사용 사례

### 일반인 사용자

- "형법 제1조 내용 알려줘"
- "개인정보보호법 관련 법령 검색해줘"
- "근로기준법에서 해고 관련 조문 찾아줘"

### 개발자

- 새로운 툴 추가: [TOOL_ADDITION_GUIDE.md](./TOOL_ADDITION_GUIDE.md) 참고
- API 메타데이터 활용: `api_crawler/` 폴더 참고

## 📤 프로젝트 공유

다른 사람과 공유할 때:

✅ **공유 가능:**

- 모든 소스 코드 파일
- `requirements.txt`, `pyproject.toml`
- `env.example` 파일
- 모든 문서 파일

❌ **절대 공유하지 마세요:**

- `.env` 파일 (개인 API 키 포함)

## 🏆 해커톤 제출

해커톤에 제출하기 전에 [HACKATHON_GUIDE.md](./HACKATHON_GUIDE.md)를 확인하세요.

## 📝 라이선스

MIT License

---

**이 프로젝트는 일반인들이 AI를 통해 법률 정보를 쉽게 조회할 수 있도록 돕는 변호사 MCP 서버입니다.**
