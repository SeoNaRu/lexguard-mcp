# LexGuard MCP 서버 설정 가이드

## 현재 문제

1. **`.env` 파일 에러** (15번째 라인)

   - 현재: `; PORT=8100`
   - 수정: `# PORT=8100`
   - **액션**: `.env` 파일을 열어서 15번째 라인의 `;`를 `#`으로 변경하세요

2. **Cursor MCP 연결 문제**
   - Cursor는 HTTP MCP를 완전히 지원하지 않을 수 있습니다
   - stdio transport 방식을 권장합니다

---

## 옵션 1: HTTP Transport (현재 방식 - 실험적)

### `.cursor/mcp.json` 설정:

```json
{
  "mcpServers": {
    "lexguard-mcp": {
      "url": "http://127.0.0.1:8099/mcp"
    }
  }
}
```

**주의**:

- Cursor에서 HTTP MCP 지원이 제한적일 수 있음
- 서버를 별도로 실행해야 함: `python -m src.main`

---

## 옵션 2: stdio Transport (권장)

### `.cursor/mcp.json` 설정:

```json
{
  "mcpServers": {
    "lexguard-mcp": {
      "command": "python",
      "args": ["-m", "src.main_stdio"],
      "cwd": "C:\\Users\\seonaru\\Desktop\\LexGuardMcp",
      "env": {
        "LAW_API_KEY": "LexGuardKey"
      }
    }
  }
}
```

**장점**:

- Cursor가 자동으로 서버 프로세스 관리
- 안정적인 연결
- 별도 서버 실행 불필요

**필요 작업**:

- `src/main_stdio.py` 파일 생성 필요 (stdio 방식용)

---

## 옵션 3: Claude Desktop App 사용 (가장 안정적)

Claude Desktop 앱을 사용하면 MCP가 완전히 지원됩니다:

### `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac)

### `%APPDATA%\Claude\claude_desktop_config.json` (Windows)

```json
{
  "mcpServers": {
    "lexguard-mcp": {
      "command": "python",
      "args": ["-m", "src.main_stdio"],
      "cwd": "C:\\Users\\seonaru\\Desktop\\LexGuardMcp",
      "env": {
        "LAW_API_KEY": "LexGuardKey"
      }
    }
  }
}
```

---

## 즉시 해결 방법

### 1. `.env` 파일 수정

```bash
notepad .env
```

15번째 라인: `; PORT=8100` → `# PORT=8100`

### 2. 서버 재시작

```bash
python -m src.main
```

### 3. 로그 확인

서버 로그에서 다음 메시지를 확인:

- `🔄 SSE generate() started` - 요청이 제대로 처리되는 중
- `MCP request body: {...}` - 요청 본문 확인

### 4. Cursor 재시작

Cursor를 완전히 종료하고 다시 시작

---

## 디버깅

### HTTP 엔드포인트 직접 테스트:

```powershell
# initialize 요청
Invoke-RestMethod -Uri "http://localhost:8099/mcp" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'

# tools/list 요청
Invoke-RestMethod -Uri "http://localhost:8099/mcp" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
```

---

## 권장 사항

**단기**: `.env` 파일을 수정하고 현재 HTTP 방식으로 계속 테스트

**장기**: stdio transport 방식으로 전환하여 안정성 향상

어느 방식을 선택하시겠습니까?

1. HTTP 방식 계속 디버깅
2. stdio 방식으로 전환 (추천)
3. Claude Desktop 앱 사용
