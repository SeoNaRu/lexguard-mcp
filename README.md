[![MCP Badge](https://lobehub.com/badge/mcp-full/seonaru-lexguard-mcp)](https://lobehub.com/mcp/seonaru-lexguard-mcp)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-green)
![License](https://img.shields.io/badge/License-MIT-yellow)
![CI](https://github.com/SeoNaRu/lexguard-mcp/actions/workflows/ci.yml/badge.svg)

# ⚖️ LexGuard MCP (법실마리)

> **한국 법령·판례·법령해석을 AI가 이해하기 쉬운 형태로 연결하는 MCP 서버**
>
> 국가법령정보센터(Open Law) 공식 데이터를 기반으로, 법령·조문·판례·법령해석·행정심판·헌재결정을 **하나의 질문 흐름**으로 제공합니다.

- **MCP Endpoint**: [https://lexguard-mcp.onrender.com/mcp](https://lexguard-mcp.onrender.com/mcp)
- **Health Check**: [https://lexguard-mcp.onrender.com/health](https://lexguard-mcp.onrender.com/health)
- **GitHub**: [https://github.com/SeoNaRu/lexguard-mcp](https://github.com/SeoNaRu/lexguard-mcp)

### 빠른 연결 (복붙)

원격 MCP만 쓸 때는 아래 JSON을 클라이언트 설정에 그대로 넣을 수 있습니다.

- Cursor: [`examples/cursor-mcp.remote.json`](examples/cursor-mcp.remote.json) 내용을 `.cursor/mcp.json` 등에 병합
- Claude Desktop: [`examples/claude-desktop-mcp.remote.json`](examples/claude-desktop-mcp.remote.json) → `claude_desktop_config.json`의 `mcpServers`에 병합

**한 줄 로컬 실행 (Docker):** 저장소 루트에서 `docker compose up --build` 후 MCP URL은 `http://localhost:9099/mcp` 입니다. (API 키: `LAW_API_KEY=발급키 docker compose up --build`)

마켓플레이스·크롤러용 정적 메타: [`mcp/manifest.json`](mcp/manifest.json) · 프롬프트 색인 [`prompts/`](prompts/) · 리소스 URI 안내 [`resources/README.md`](resources/README.md) · Cursor 개발 스킬 [`.cursor/skills/lexguard-mcp-dev/SKILL.md`](.cursor/skills/lexguard-mcp-dev/SKILL.md)

---

## Why LexGuard?

법은 필요할 때마다 멀고 어렵게 느껴집니다.
높은 비용, 낯선 용어, 어디서부터 찾아야 할지 모르는 구조.

**LexGuard MCP(법실마리)** 는 이 문제에서 출발했습니다.

- 사용자는 **사람의 말**로 질문하고
- AI는 질문 의도를 분석한 뒤
- **공식 법령·판례 데이터**를 근거로 실마리를 제공합니다.

> 판단이나 법률 자문을 대신하지 않습니다.
> 다만, _법을 처음 마주하는 순간을 덜 어렵게_ 만드는 것을 목표로 합니다.

---

## Core Features

| 기능 | 설명 |
|------|------|
| **통합 법률 QA** | 법령·판례·법령해석·행정심판·헌재결정 병렬 종합 탐색 |
| **조문 정밀 조회** | 법령명 + 조문번호로 특정 조항 직접 조회 |
| **문서·계약서 분석** | 계약서·약관 붙여넣기만으로 조항별 법적 이슈 자동 감지 |
| **판례 번호 직접 감지** | `2023다12345`, `2021헌마123` 형식 자동 인식 후 즉시 검색 |
| **도메인 자동 분류** | 노동·개인정보·부동산·소비자·세금·금융 등 10개 법률 도메인 |
| **자연어 시간 조건** | "최근 3년", "2023년 이후" 등 자연어 시간 표현 자동 파싱 |
| **Reranker 파이프라인** | 검색 결과를 쿼리 적합도(BM25 + Keyword Hybrid) 기준으로 재정렬 |
| **병렬 검색** | `asyncio.gather` 기반 멀티 API 동시 호출로 응답 속도 최소화 |
| **Rate Limiting** | IP당 60 req/min 제한으로 남용 방지 |

---

## MCP Tools

### `legal_qa_tool` — 범용 법률 QA

모든 법률 질문의 단일 진입점입니다. 질문 하나로 법령·판례·해석·위원회 결정례를 병렬 탐색하고 종합합니다. 출처가 한정된 검색(판례만, 해석만 등)은 각 전용 툴을 검토할 수 있습니다.

**Capabilities**

- 10개 도메인 자동 분류
- 질문 의도(Intent) 다중 감지 및 우선순위 정렬
- 법령 → 판례 → 해석 → 위원회 병렬 탐색
- 자연어 시간 조건 필터링 (`date_from` / `date_to` 자동 변환)

**Input Schema**

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `query` | string | ✅ | 사용자의 법률 질문 |
| `max_results_per_type` | integer | — | 타입당 최대 결과 수 (기본값: 3, 최대: 10) |

**Example Prompts**

```
프리랜서인데 근로자성 인정된 판례 있나요?
최근 3년 부당해고 판례 알려줘
개인정보 유출됐는데 법적으로 어떻게 되나요?
2023다12345 판례 찾아줘
```

---

### `law_article_tool` — 법령 조문 정밀 조회

법령명과 조문번호를 알고 있을 때 특정 조항을 직접 조회합니다. `legal_qa_tool`이 "탐색"이라면, 이 툴은 "정확한 조회"입니다.

**Input Schema**

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `law_name` | string | ✅ | 법령명 (예: 근로기준법, 민법) |
| `article_number` | string | — | 조문 번호 (예: `50`, `2`). 생략 시 법령 개요 반환 |
| `hang` | string | — | 항 번호 (예: `1`, `2`) |
| `ho` | string | — | 호 번호 (예: `1`, `2`) |
| `mok` | string | — | 목 번호 (예: `가`, `나`) |

**Example Prompts**

```
근로기준법 제50조 내용 알려줘
민법 제750조 3항이 뭐야?
개인정보보호법 제17조
```

---

### `law_comparison_tool` — 법령 신구·연혁·3단 비교

법령명을 기준으로 신구법 대비, 연혁, 3단 비교 결과를 조회합니다. 조문 원문 조회는 `law_article_tool`, 일반 질문은 `legal_qa_tool`을 사용하세요.

**Input Schema**

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `law_name` | string | ✅ | 법령명 (예: 형법, 민법) |
| `compare_type` | string | — | `신구법` · `연혁` · `3단비교` (기본값: `신구법`) |

**Example Prompts**

```
근로기준법 신구법 비교 보여줘
민법 연혁 조회
```

---

### `document_issue_tool` — 계약서·약관 분석

문서를 붙여넣으면 조항 단위로 법적 이슈를 추출하고, 관련 법령·판례를 자동 검색합니다.

**Input Schema**

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `document_text` | string | ✅ | 계약서·약관 전문 |
| `auto_search` | boolean | — | 조항별 자동 법령 검색 여부 (기본값: true) |
| `max_clauses` | integer | — | 분석할 최대 조항 수 (기본값: 3) |
| `max_results_per_type` | integer | — | 타입당 최대 결과 수 (기본값: 3) |

**Supported Document Types**

- `labor` — 근로계약서 / 용역계약서
- `lease` — 임대차 계약서
- `terms` — 이용약관

**Example Prompts**

```
이 프리랜서 계약서 문제 있는지 봐줘
아래 임대차 계약서에서 불리한 조항 찾아줘
```

---

### `health` — 서버 상태 확인

MCP 서버 동작 여부, API Key 설정 상태, 환경 변수를 확인합니다.

---

### 전용 검색 툴 (출처 한정)

통합 검색(`legal_qa_tool`) 대신 **특정 데이터만** 찾을 때 사용합니다.

| 툴 이름 | 용도 | 주요 입력 |
|---------|------|-----------|
| `precedent_lookup_tool` | 판례만 | `keyword` 또는 `case_number` |
| `interpretation_tool` | 법령해석·유권해석 등 | `query`, 선택 `agency` |
| `administrative_appeal_tool` | 행정심판 재결만 | `query`, 선택 기간 |
| `constitutional_decision_tool` | 헌법재판소 결정만 | `query`, 선택 기간 |
| `committee_decision_tool` | 독립위원회 등 결정문 | `committee_type`, `query` |
| `special_administrative_appeal_tool` | 특별행정심판원 재결 | `tribunal_type`, `query` |
| `local_ordinance_tool` | 자치법규(조례 등)만 | `query` 또는 `local_government` 중 하나 이상 |
| `administrative_rule_tool` | 행정규칙만 | `query` 또는 `agency` 중 하나 이상 |

---

## MCP Prompts

`prompts/list` 및 `prompts/get` 엔드포인트를 지원합니다.

| Prompt 이름 | 설명 |
|-------------|------|
| `legal_basis_answer` | 관련 법령 조문 번호와 판례 요지를 포함한 답변 요청 |
| `precedent_summary` | 판례를 사실관계 / 쟁점 / 판단요지로 요약 |
| `contract_risk_check` | 범용 계약·약관 위험 조항 점검. **근로·용역 전용 고밀도 검토**는 `labor_contract_review` 또는 `document_issue_tool`(문서가 labor로 분류될 때)을 사용하세요. |
| `labor_contract_review` | 근로·용역 계약서 조항별 조문·위험도·수정방향 검토(B 타입) |
| `legal_qa` | 특정 상황에 대한 법률적 관점 설명 |

---

## MCP Resources

`resources/list` 및 `resources/read` 엔드포인트를 지원합니다.

### URI Scheme

| 형식 | 설명 | 예시 |
|------|------|------|
| `law://{법령명}` | 법령 본문 조회 | `law://근로기준법` |
| `case://{검색어}` | 판례 검색 (상위 5건) | `case://부당해고` |
| `interpret://{검색어}` | 법령해석 검색 (상위 5건) | `interpret://근로자성` |

### Featured Resources (기본 제공)

근로기준법, 민법, 형법, 개인정보보호법, 상법, 국가공무원법, 행정소송법 등 주요 법령을 즉시 조회할 수 있습니다.

---

## Installation

### Method 1. Local (Python)

```bash
git clone https://github.com/SeoNaRu/lexguard-mcp
cd lexguard-mcp
pip install -r requirements.txt
cp .env.example .env   # LAW_API_KEY 설정
python -m src.main
```

### Method 2. Docker Compose (권장 · 한 줄에 가깝게)

```bash
git clone https://github.com/SeoNaRu/lexguard-mcp
cd lexguard-mcp
cp .env.example .env   # LAW_API_KEY 편집
docker compose up --build
```

브라우저/클라이언트 MCP URL: `http://localhost:9099/mcp` · 헬스: `http://localhost:9099/health`

### Method 3. Docker (run만)

```bash
docker build -t lexguard-mcp .
docker run -p 9099:9099 -e LAW_API_KEY=your_key lexguard-mcp
```

### Method 4. Remote MCP (호스팅 URL)

**Claude Desktop** (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "lexguard-mcp": {
      "url": "https://lexguard-mcp.onrender.com/mcp"
    }
  }
}
```

**Cursor** (`.cursor/mcp.json`)

[`examples/cursor-mcp.remote.json`](examples/cursor-mcp.remote.json) 파일과 동일:

```json
{
  "mcpServers": {
    "lexguard-mcp": {
      "url": "https://lexguard-mcp.onrender.com/mcp"
    }
  }
}
```

### API Key 발급

국가법령정보센터 Open API 키가 필요합니다.

1. [https://open.law.go.kr](https://open.law.go.kr) 회원가입
2. API 활용 신청
3. `.env`에 `LAW_API_KEY=발급받은키` 설정

---

## Architecture

```
Client (Cursor / Claude)
    │ JSON-RPC 2.0 over SSE
    ▼
FastAPI  (/mcp POST)
    │ Rate Limiting (slowapi, 60 req/min/IP)
    ▼
MCP Routes  (tools/call · prompts/get · resources/read)
    │
    ▼
Services  (SmartSearchService · SituationGuidanceService)
    │ asyncio.gather (병렬 멀티 API 호출)
    ▼
Repositories  (Law · Precedent · Interpretation · Appeal · Constitutional …)
    │ httpx (동기/비동기 HTTP 클라이언트)
    │ TTLCache (검색 결과 30분 / 실패 5분)
    │ Exponential Backoff Retry
    ▼
국가법령정보센터 DRF API  (172개 엔드포인트)
```

**검색 파이프라인**

```
질문 입력
    → 판례 번호 패턴 조기 감지 (2023다12345 / 2021헌마123)
    → 도메인 분류 + 의도(Intent) 분석
    → 시간 조건 파싱
    → asyncio.gather 병렬 API 호출
    → Reranker (BM25 + Keyword Hybrid 재정렬)
    → 응답 포매팅
```

**주요 기술 스택**

| 구분 | 사용 기술 |
|------|-----------|
| Web Framework | FastAPI + Uvicorn |
| MCP Transport | Streamable HTTP (SSE) |
| HTTP Client | httpx (sync + async) |
| Cache | cachetools TTLCache |
| Rate Limiting | slowapi |
| Search Ranking | BM25 + Keyword Hybrid Reranker |
| CI/CD | GitHub Actions (Python 3.11 / 3.12) |
| Testing | pytest + pytest-asyncio |

---

## Development

```bash
# 테스트 실행
pytest tests/ -v

# 린트
ruff check src/

# 로컬 서버 (자동 재로드)
RELOAD=true python -m src.main
```

---

## License

전문은 저장소 루트의 [`LICENSE`](LICENSE) 파일을 따릅니다.

- **사용:** MIT와 동일하게 연구·개인·상업적 이용, 수정·배포·재판매까지 허용됩니다.
- **판매·유료 제공 시:** 이 소프트웨어를 단독으로 판매하거나, 제품·서비스에 포함해 판매하는 경우 **저작권 표시와 본 라이선스 문구**를 최종 이용자에게 전달되는 자료(문서, 크레딧·라이선스 화면, 패키지 메타데이터 등)에 포함해야 합니다.

본 안내는 요약이며 법적 효력은 `LICENSE` 원문이 우선합니다.

---

## Contribution

Issues & PRs are always welcome.
법률 도메인 데이터, 검색 품질 개선, 새로운 MCP 툴 아이디어 모두 환영합니다.

---

> **LexGuard MCP — 법률 정보의 실마리를 찾아드립니다.**
> 법은 어렵지만, 첫 실마리는 쉬워질 수 있습니다.
