[![MCP Badge](https://lobehub.com/badge/mcp-full/seonaru-lexguard-mcp)](https://lobehub.com/mcp/seonaru-lexguard-mcp)

# ⚖️ LexGuard MCP (법실마리)

> **한국 법률·판례·법령해석을 AI가 이해하기 쉬운 형태로 연결하는 MCP 서버**
> 국가법령정보센터(Open Law) 공식 데이터를 기반으로, 법령·조문·판례·법령해석·행정심판·헌재결정을 **하나의 질문 흐름**으로 제공합니다.

- 🌐 **MCP Endpoint**: [https://lexguard-mcp.onrender.com/mcp](https://lexguard-mcp.onrender.com/mcp)
- ❤️ **Health Check**: [https://lexguard-mcp.onrender.com/health](https://lexguard-mcp.onrender.com/health)
- 📦 **GitHub Repo**: [https://github.com/SeoNaRu/lexguard-mcp](https://github.com/SeoNaRu/lexguard-mcp)

---

## 🧭 Why LexGuard?

법은 필요할 때마다 멀고 어렵게 느껴집니다.
높은 비용, 낯선 용어, 어디서부터 찾아야 할지 모르는 구조.

**LexGuard MCP(법실마리)** 는 이 문제에서 출발했습니다.

- 사용자는 **사람의 말**로 질문하고
- AI는 질문 의도를 이해한 뒤
- **공식 법령·판례 데이터**를 근거로 실마리를 제공합니다.

> ❗ 판단이나 법률 자문을 대신하지 않습니다.
> 다만, _법을 처음 마주하는 순간을 덜 어렵게_ 만드는 것을 목표로 합니다.

---

## ✨ Core Features

- 🔍 **통합 법률 QA**
  법령 · 판례 · 법령해석 · 행정심판 · 헌재결정 자동 종합

- 📄 **문서 / 계약서 분석**
  계약서·약관을 붙여넣으면 조항별 법적 이슈 자동 감지

- 🧠 **도메인 자동 분류**
  노동 / 개인정보 / 부동산 / 소비자 / 세금 / 금융 등 10개 법률 도메인

- ⏰ **자연어 시간 조건 파싱**
  “최근 3년”, “2023년 이후” 같은 표현 자동 처리

- 🚀 **172개 국가법령정보센터 DRF API 완전 통합**

---

## 🧰 Provided MCP Tools

### 1️⃣ `legal_qa_tool` — 범용 법률 QA (Main Entry)

모든 법률 질문의 **단일 진입점**입니다.

**Capabilities**

- 도메인 자동 감지
- 질문 의도(Intent) 분해
- 법령 → 판례 → 해석 → 위원회 순차 탐색
- 시간 조건 필터링

**Example Prompts**

```
프리랜서인데 근로자성 인정된 판례 있나요?
최근 3년 부당해고 판례 알려줘
개인정보 유출됐는데 법적으로 어떻게 되나요?
```

---

### 2️⃣ `document_issue_tool` — 계약서 / 약관 분석

문서를 붙여넣으면 **조항 단위로 법적 이슈를 추출**합니다.

**Supported Types**

- labor (근로/용역)
- lease (임대차)
- terms (이용약관)

**Example**

```
이 프리랜서 계약서 문제 있는지 봐줘
```

---

### 3️⃣ `health` — 서버 상태 확인

- MCP 서버 동작 여부
- API Key 설정 여부

---

## 🧩 Prompt Templates (LobeHub Score 대응)

### 📌 Prompt 1 — 법령 근거 포함 답변

```
질문에 대해 반드시 관련 법령 조문 번호와 판례 요지를 함께 알려주세요.
```

### 📌 Prompt 2 — 판례 요약형

```
관련 판례를 사실관계 / 쟁점 / 판단요지로 나눠 요약해주세요.
```

### 📌 Prompt 3 — 계약서 위험조항 점검

```
아래 계약서에서 법적으로 문제될 수 있는 조항을 항목별로 정리해주세요.
```

---

## 📚 Resource URI Scheme (LobeHub Score 대응)

LexGuard MCP는 검색 결과를 **Resource URI** 형태로도 제공합니다.

- `law://{law_id}` — 법령 본문
- `case://{case_id}` — 판례 원문
- `interpret://{interpret_id}` — 법령해석

Example:

```
law://근로기준법-제23조
case://대법원-2019다12345
```

---

## 📦 Installation

### ✅ Method 1. Local (Python)

```bash
pip install -r requirements.txt
python -m src.main
```

---

### ✅ Method 2. Docker (Recommended)

```bash
docker build -t lexguard-mcp .
docker run -p 8099:8099 lexguard-mcp
```

---

### ✅ Method 3. MCP Client (One‑click)

#### Claude Desktop

```json
{
  "mcpServers": {
    "lexguard-mcp": {
      "url": "https://lexguard-mcp.onrender.com/mcp"
    }
  }
}
```

#### Cursor

```json
{
  "mcpServers": {
    "lexguard-mcp": {
      "url": "https://lexguard-mcp.onrender.com/mcp"
    }
  }
}
```

---

## 🏗 Architecture

- Routes → Services → Repositories
- MCP Streamable HTTP (SSE)
- TTL Cache (30m success / 5m fail)
- Exponential Backoff Retry

---

## 📜 License

MIT License

---

## 🙌 Contribution

Issues & PRs are always welcome.

---

> **LexGuard MCP — 법률 정보의 실마리를 찾아드립니다.**
> 법은 어렵지만, 첫 실마리는 쉬워질 수 있습니다.
