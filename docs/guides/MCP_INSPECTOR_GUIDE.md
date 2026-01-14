# MCP Inspector 검증 가이드

MCP 서버가 표준 스펙을 준수하는지 검증하는 가이드입니다.

## 📋 사전 준비

### 1. MCP Inspector 설치

MCP Inspector는 Node.js 기반 도구입니다.

#### Node.js 설치 확인
```bash
node --version
npm --version
```

Node.js가 설치되어 있지 않다면:
- [Node.js 공식 사이트](https://nodejs.org/)에서 설치

#### MCP Inspector 설치
```bash
npm install -g @modelcontextprotocol/inspector
```

또는 npx로 직접 실행:
```bash
npx @modelcontextprotocol/inspector
```

---

## 🔍 검증 방법

### 방법 1: 로컬 서버 검증 (개발 중)

1. **서버 실행**
   ```bash
   # PowerShell
   .\start_server.bat
   
   # 또는 직접 실행
   python -m src.main
   ```

2. **MCP Inspector 실행**
   ```bash
   # Streamable HTTP 방식으로 검증
   npx @modelcontextprotocol/inspector http://localhost:8099/mcp
   ```

3. **검증 결과 확인**
   - Inspector가 서버에 연결하여 스펙 준수 여부를 확인합니다
   - 각 엔드포인트(`initialize`, `tools/list`, `tools/call`)를 테스트합니다
   - 문제가 있으면 오류 메시지와 함께 표시됩니다

### 방법 2: 원격 서버 검증 (배포 후)

배포된 서버의 공개 URL로 검증:

```bash
npx @modelcontextprotocol/inspector https://your-domain.com/mcp
```

---

## ✅ 검증 항목

MCP Inspector는 다음 항목들을 자동으로 검증합니다:

### 1. MCP 스펙 버전
- ✅ 최소 버전 2025-03-26 이상 준수
- ✅ `initialize` 응답에 올바른 `protocolVersion` 포함

### 2. 전송 방식
- ✅ Streamable HTTP 방식 구현
- ✅ SSE (Server-Sent Events) 스트림 정상 작동
- ✅ 올바른 Content-Type 헤더 (`text/event-stream`)

### 3. 엔드포인트
- ✅ `POST /mcp` 엔드포인트 존재
- ✅ `initialize` 메서드 정상 응답
- ✅ `tools/list` 메서드 정상 응답
- ✅ `tools/call` 메서드 정상 응답

### 4. 응답 형식
- ✅ JSON-RPC 2.0 형식 준수
- ✅ 올바른 `id`, `jsonrpc`, `result` 필드
- ✅ 에러 응답 형식 올바름

### 5. 툴 정의
- ✅ 모든 툴에 `name`, `description` 필드 존재
- ✅ 파라미터 스키마 올바름
- ✅ 응답 형식 올바름

---

## 🐛 일반적인 문제 및 해결 방법

### 문제 1: "Connection refused"
**원인**: 서버가 실행되지 않았거나 포트가 다름

**해결**:
```bash
# 서버가 실행 중인지 확인
# 브라우저에서 http://localhost:8099/health 접속 테스트
```

### 문제 2: "Invalid protocol version"
**원인**: MCP 스펙 버전이 올바르지 않음

**해결**: `src/routes/mcp_routes.py`에서 `protocolVersion` 확인
```python
"protocolVersion": "2025-03-26"  # 올바른 버전인지 확인
```

### 문제 3: "SSE stream not found"
**원인**: Streamable HTTP 응답 형식이 올바르지 않음

**해결**: `src/routes/mcp_routes.py`에서 SSE 응답 형식 확인
```python
# Content-Type이 text/event-stream인지 확인
# data: 접두사가 올바르게 포함되어 있는지 확인
```

### 문제 4: "Tool not found"
**원인**: `tools/list`에서 반환한 툴 이름과 `tools/call`에서 사용한 이름이 다름

**해결**: 툴 이름 일관성 확인

---

## 📝 검증 체크리스트

검증 전에 다음을 확인하세요:

- [ ] 서버가 정상적으로 실행 중
- [ ] `http://localhost:8099/health` 접속 가능
- [ ] `http://localhost:8099/mcp` 엔드포인트 존재
- [ ] MCP Inspector 설치 완료
- [ ] Node.js 버전 18 이상

---

## 🎯 검증 결과 예시

### 성공적인 검증
```
✓ MCP Server: http://localhost:8099/mcp
✓ Protocol Version: 2025-03-26
✓ Initialize: OK
✓ Tools/List: OK (18 tools found)
✓ Tools/Call: OK
✓ All checks passed!
```

### 실패한 검증
```
✗ MCP Server: http://localhost:8099/mcp
✗ Protocol Version: Invalid (expected 2025-03-26, got 2024-11-05)
✗ Initialize: Failed
  Error: Protocol version mismatch
```

---

## 📚 참고 자료

- [MCP Inspector 공식 문서](https://modelcontextprotocol.io/docs/tools/inspector)
- [MCP 스펙 문서](https://modelcontextprotocol.io/specification/2025-03-26)
- [MCP Streamable HTTP 스펙](https://modelcontextprotocol.io/specification/2025-03-26/basic/transports#streamable-http)

---

## 💡 팁

1. **개발 중에는 로컬 검증을 자주 실행**
   - 코드 변경 후 즉시 검증하여 문제를 조기에 발견

2. **배포 전 반드시 검증**
   - 원격 서버로 배포하기 전에 로컬에서 검증 완료

3. **CI/CD에 통합**
   - 자동화된 검증을 위해 CI/CD 파이프라인에 Inspector 통합 가능

