# 해커톤 제출 전 검증 체크리스트

## 📋 필수 파일 확인

### ✅ 생성 완료된 파일

- [x] `requirements.txt` - Python 의존성 목록
- [x] `env.example` - 환경 변수 예시 파일
- [x] `README.md` - 프로젝트 설명서
- [x] `pyproject.toml` - 프로젝트 설정

### 📝 확인 사항

- [ ] `.gitignore`에 `.env` 파일이 포함되어 있는지 확인
- [ ] `README.md`에 설치 및 실행 방법이 명확한지 확인
- [ ] 모든 문서가 최신 상태인지 확인

---

## 🔍 MCP Inspector 검증

### 1단계: MCP Inspector 설치

```bash
# Node.js 설치 확인
node --version
npm --version

# MCP Inspector 설치 (전역 설치)
npm install -g @modelcontextprotocol/inspector

# 또는 npx로 직접 실행 (설치 없이)
npx @modelcontextprotocol/inspector
```

### 2단계: 서버 실행

```bash
# PowerShell
.\start_server.bat

# 또는 직접 실행
python -m src.main
```

서버가 정상적으로 실행되었는지 확인:
- 브라우저에서 `http://localhost:8099/health` 접속
- "OK" 응답이 나오면 정상

### 3단계: MCP Inspector 실행

**새 터미널 창에서 실행:**

```bash
# 로컬 서버 검증
npx @modelcontextprotocol/inspector http://localhost:8099/mcp
```

### 4단계: 검증 결과 확인

**성공적인 검증 결과 예시:**
```
✓ MCP Server: http://localhost:8099/mcp
✓ Protocol Version: 2025-03-26
✓ Initialize: OK
✓ Tools/List: OK (18 tools found)
✓ Tools/Call: OK
✓ All checks passed!
```

**실패한 경우:**
- 오류 메시지를 확인하고 문제를 해결
- `MCP_INSPECTOR_GUIDE.md`의 문제 해결 섹션 참고

---

## ✅ MCP 스펙 준수 확인

### 1. 스펙 버전
- [ ] `protocolVersion: "2025-03-26"` 이상
- [ ] `src/routes/mcp_routes.py`에서 확인

### 2. 전송 방식
- [ ] Streamable HTTP 방식 구현
- [ ] SSE (Server-Sent Events) 스트림 정상 작동
- [ ] Content-Type: `text/event-stream`

### 3. 엔드포인트
- [ ] `POST /mcp` 엔드포인트 존재
- [ ] `initialize` 메서드 정상 응답
- [ ] `tools/list` 메서드 정상 응답
- [ ] `tools/call` 메서드 정상 응답

### 4. 응답 형식
- [ ] JSON-RPC 2.0 형식 준수
- [ ] 올바른 `id`, `jsonrpc`, `result` 필드
- [ ] 에러 응답 형식 올바름

---

## 🛠️ 툴 품질 확인

### 툴 목록 확인
```bash
# tools/list 엔드포인트 테스트
curl -X POST http://localhost:8099/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}'
```

### 각 툴 확인 사항
- [ ] 모든 툴에 `name` 필드 존재
- [ ] 모든 툴에 `description` 필드 존재 (한국어)
- [ ] 파라미터 스키마 올바름
- [ ] 툴 이름이 소문자, 언더스코어 사용
- [ ] "kakao" prefix/suffix 미사용

### 툴 동작 테스트
- [ ] `smart_search_tool` - "형법 제250조" 검색 테스트
- [ ] `search_law_tool` - "형법" 검색 테스트
- [ ] `get_law_tool` - 법령 상세 조회 테스트
- [ ] 에러 케이스 처리 확인 (API 키 없을 때 등)

---

## 📊 응답 크기 확인

### 24KB 제한 확인
- [ ] 모든 툴 응답이 24KB 이하인지 확인
- [ ] `src/utils/response_truncator.py`가 정상 작동하는지 확인

테스트 방법:
```python
# Python에서 테스트
import requests
import json

response = requests.post(
    "http://localhost:8099/mcp",
    json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "search_law_tool",
            "arguments": {"query": "형법"}
        }
    }
)

# 응답 크기 확인
print(f"Response size: {len(response.text)} bytes")
assert len(response.text) <= 24 * 1024, "Response too large!"
```

---

## 🔒 보안 확인

- [ ] `.env` 파일이 `.gitignore`에 포함되어 있는지 확인
- [ ] API 키가 코드에 하드코딩되어 있지 않은지 확인
- [ ] 민감한 정보가 로그에 출력되지 않는지 확인

---

## 📝 문서 확인

- [ ] `README.md`가 최신 상태인지 확인
- [ ] 설치 및 실행 방법이 명확한지 확인
- [ ] 모든 문서 링크가 올바른지 확인
- [ ] 예시가 정확한지 확인

---

## 🚀 배포 준비 (원격 서버)

### 배포 전 확인 사항
- [ ] 공개 URL 준비 (예: `https://your-domain.com/mcp`)
- [ ] HTTPS 설정 완료
- [ ] Stateless 서버 설계 확인 (세션 없음)
- [ ] 원격 서버에서도 MCP Inspector 검증 완료

### 원격 서버 검증
```bash
npx @modelcontextprotocol/inspector https://your-domain.com/mcp
```

---

## ✅ 최종 체크리스트

제출 전 최종 확인:

- [ ] 모든 필수 파일 존재
- [ ] MCP Inspector 검증 통과
- [ ] 모든 툴 정상 동작
- [ ] 응답 크기 24KB 이하
- [ ] 문서 최신 상태
- [ ] 보안 확인 완료
- [ ] (선택) 원격 서버 배포 및 검증 완료

---

## 📚 참고 문서

- [MCP Inspector 가이드](./MCP_INSPECTOR_GUIDE.md)
- [해커톤 제출 가이드](./HACKATHON_GUIDE.md)
- [MCP 규격 준수 가이드](./MCP_COMPLIANCE_RULES.md)

