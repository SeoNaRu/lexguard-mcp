# ⚖️ 법실마리 (LexGuard MCP)

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

Cursor에서 MCP 서버를 사용하려면 Settings → MCP Servers에서 위 설정을 추가하세요.

### ChatGPT / Gemini 설정

ChatGPT나 Gemini에서 MCP 서버를 사용하려면 각 플랫폼의 MCP 설정 방법을 참고하세요.

## 🧰 제공 툴

현재 **20개의 툴**을 제공합니다:

### 통합 검색 툴 (우선 사용 권장)

1. **`smart_search_tool`** - 통합 검색 (법령, 판례, 해석 등 자동 검색)
2. **`situation_guidance_tool`** - 상황별 가이드 (법적 상황 종합 분석)

### 법령 관련 툴

3. **`search_law_tool`** - 법령 검색
4. **`get_law_tool`** - 법령 조회 (상세/전체 조문/단일 조문)

### 판례 관련 툴

5. **`search_precedent_tool`** - 판례 검색
6. **`get_precedent_tool`** - 판례 상세 조회

### 법령해석 관련 툴

7. **`search_law_interpretation_tool`** - 법령해석 검색
8. **`get_law_interpretation_tool`** - 법령해석 상세 조회

### 행정심판 관련 툴

9. **`search_administrative_appeal_tool`** - 행정심판 검색
10. **`get_administrative_appeal_tool`** - 행정심판 상세 조회

### 위원회 결정 관련 툴

11. **`search_committee_decision_tool`** - 위원회 결정문 검색
12. **`get_committee_decision_tool`** - 위원회 결정문 상세 조회

### 헌법재판소 관련 툴

13. **`search_constitutional_decision_tool`** - 헌재결정 검색
14. **`get_constitutional_decision_tool`** - 헌재결정 상세 조회

### 특별행정심판 관련 툴

15. **`search_special_administrative_appeal_tool`** - 특별행정심판 검색
16. **`get_special_administrative_appeal_tool`** - 특별행정심판 상세 조회

### 기타 툴

17. **`compare_laws_tool`** - 법령 비교 (신구법, 연혁)
18. **`search_local_ordinance_tool`** - 지방자치단체 조례/규칙 검색
19. **`search_administrative_rule_tool`** - 행정규칙 검색
20. **`health`** - 서비스 상태 확인

**상세 정보**: MCP 서버의 `tools/list` 엔드포인트를 통해 확인할 수 있습니다.

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

### 🧑‍💼 일반인 사용 예시

#### 🔍 통합 검색 툴 (가장 많이 사용)

**smart_search_tool** - 법적으로 문제가 있는지 확인하고 싶을 때

- "이 계약서 괜찮은 거야?"
- "회사에서 갑자기 계약 끝낸다는데 이거 문제 없어?"
- "프리랜서인데 출근 시간 정해놓고 일 시키면 괜찮은 거야?"
- "이거 불공정 계약 같은데 관련 법 있어?"

**situation_guidance_tool** - 내 상황에 맞는 법적 정보가 필요할 때

- "회사에서 해고 통보 받았는데 이유를 안 알려줘"
- "집주인이 보증금 못 준다는데 이게 가능한 거야?"
- "일은 직원처럼 하는데 계약은 용역이래"

#### 📖 법령 검색 및 조회

**search_law_tool** - 법 이름을 몰라도 키워드로 검색

- "해고 관련된 법 뭐 있어?"
- "전세 보증금 보호하는 법 찾아줘"
- "프리랜서 보호해주는 법 있어?"

**get_law_tool** - 특정 법령의 조문 확인

- "근로기준법에서 해고 관련 조항 보여줘"
- "계약 일방 해지에 관한 법 조항 알려줘"
- "손해배상 관련 민법 조문 뭐야?"

#### ⚖️ 판례 검색

**search_precedent_tool** - 유사한 사건의 판례 찾기

- "회사 마음대로 계약 끊은 판례 있어?"
- "프리랜서인데 근로자로 인정된 사례"
- "불공정 계약 무효된 사례"

**get_precedent_tool** - 판례 상세 내용 확인

- "아까 말한 판례 내용 좀 더 알려줘"
- "법원이 어떤 점을 중요하게 봤어?"

#### 🧾 법령해석 및 행정심판

**search_law_interpretation_tool** - 정부의 공식 해석 확인

- "이 법을 정부에서는 어떻게 보고 있어?"
- "근로자 기준에 대한 공식 해석 있어?"

**search_administrative_appeal_tool** - 행정기관 처분 관련 사례

- "구청 결정에 이의 제기한 사례 있어?"
- "과태료 부과 취소된 경우 있어?"

**search_committee_decision_tool** - 위원회 결정문 검색

- "위원회에서 판단한 사례 있어?"
- "분쟁 조정 같은 거에서 나온 결정문"

#### ⚖️ 헌법재판소 결정

**search_constitutional_decision_tool** - 위헌 여부 확인

- "이 법이 헌법에 어긋난다고 나온 적 있어?"
- "재산권 침해라고 인정된 사례"

#### 🔄 기타 기능

**compare_laws_tool** - 법령 변경사항 확인

- "이 법 예전이랑 지금 뭐가 달라?"
- "최근에 바뀐 해고 관련 법 내용"

**search_local_ordinance_tool** - 지방자치단체 조례/규칙

- "서울시 전세 관련 조례 있어?"
- "우리 구청에서 따로 정한 규칙 있어?"

**search_administrative_rule_tool** - 행정규칙 검색

- "부처 내부 규정 같은 것도 있어?"
- "행정기관이 실제로 따르는 기준 뭐야?"

### 🔑 핵심 사용 패턴

일반인은 **툴을 직접 고르지 않고**, 자연스러운 질문을 합니다:

```
일반인 질문 (애매하고, 상황 중심, 감정 포함)
  ↓
smart_search_tool / situation_guidance_tool (자동 선택)
  ↓
필요 시 개별 검색 툴로 상세 조회
```

이 구조로 **"법을 아는 사람"도, "아예 모르는 사람"도 모두 사용 가능**합니다.

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

## 🌐 배포 상태

**배포 완료**: 서버가 Render에 배포되어 공개 URL로 접근 가능합니다.

- **서버 URL**: `https://lexguard-mcp.onrender.com`
- **MCP 엔드포인트**: `https://lexguard-mcp.onrender.com/mcp`
- **Health Check**: `https://lexguard-mcp.onrender.com/health`

## 📝 라이선스

MIT License

---

**이 프로젝트는 일반인들이 AI를 통해 법률 정보를 쉽게 조회할 수 있도록 돕는 변호사 MCP 서버입니다.**
