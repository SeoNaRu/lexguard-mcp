# Render 배포 단계별 가이드

## 📋 사전 준비

### 1. GitHub 저장소 확인
- [ ] 프로젝트가 GitHub에 푸시되어 있는지 확인
- [ ] `.env` 파일이 `.gitignore`에 포함되어 있는지 확인

### 2. 필요한 정보
- GitHub 저장소 URL
- LAW_API_KEY (선택사항, 있으면 더 좋음)

---

## 🚀 배포 단계

### 1단계: Render 계정 생성

1. https://render.com 접속
2. "Get Started for Free" 클릭
3. **GitHub 계정으로 로그인** (권장)
   - GitHub 저장소와 자동 연결됨

---

### 2단계: 새 Web Service 생성

1. Render 대시보드에서 **"New +"** 클릭
2. **"Web Service"** 선택
3. **GitHub 저장소 연결**
   - 저장소 목록에서 `LexGuardMcp` 선택
   - 또는 저장소 URL 직접 입력

---

### 3단계: 서비스 설정

다음 정보를 입력:

#### 기본 설정
- **Name**: `lexguard-mcp` (또는 원하는 이름)
- **Region**: `Singapore` (한국에서 가장 가까움) 또는 `Oregon`
- **Branch**: `main` (또는 기본 브랜치)
- **Root Directory**: (비워두기 - 루트 디렉토리)

#### 빌드 및 시작 명령
- **Environment**: `Python 3`
- **Build Command**: 
  ```bash
  pip install -r requirements.txt
  ```
- **Start Command**: 
  ```bash
  python -m src.main
  ```

#### 고급 설정 (선택)
- **Instance Type**: `Free` (무료 티어)
- **Auto-Deploy**: `Yes` (GitHub 푸시 시 자동 배포)

---

### 4단계: 환경 변수 설정

**"Environment"** 섹션에서 다음 환경 변수 추가:

```
PORT=8099
LOG_LEVEL=INFO
RELOAD=false
LAW_API_KEY=your_api_key_here
```

**중요:**
- `LAW_API_KEY`는 실제 API 키로 변경
- API 키가 없으면 비워두어도 됨 (일부 기능만 제한)

---

### 5단계: 배포 시작

1. **"Create Web Service"** 클릭
2. 배포가 자동으로 시작됨
3. 배포 로그 확인 (실시간으로 표시됨)

**예상 시간:** 3-5분

---

### 6단계: 배포 확인

배포가 완료되면:

1. **서비스 URL 확인**
   - Render 대시보드에서 제공되는 URL 확인
   - 예: `https://lexguard-mcp.onrender.com`

2. **Health 엔드포인트 테스트**
   ```
   https://your-service-url.onrender.com/health
   ```
   - 브라우저에서 접속하거나 curl로 확인
   - "OK" 응답이 나오면 성공

3. **MCP 엔드포인트 확인**
   ```
   https://your-service-url.onrender.com/mcp
   ```

---

## ✅ 배포 후 검증

### 1. Health 엔드포인트 확인

브라우저에서 접속:
```
https://your-service-url.onrender.com/health
```

또는 터미널에서:
```bash
curl https://your-service-url.onrender.com/health
```

### 2. MCP Inspector로 검증

```bash
npx @modelcontextprotocol/inspector https://your-service-url.onrender.com/mcp
```

예상 결과:
```
✓ MCP Server: https://your-service-url.onrender.com/mcp
✓ Protocol Version: 2025-03-26
✓ Initialize: OK
✓ Tools/List: OK (20 tools found)
✓ Tools/Call: OK
✓ All checks passed!
```

### 3. 테스트 스크립트 실행

`test_mcp_server.py` 수정:
```python
BASE_URL = "https://your-service-url.onrender.com"
```

```bash
python test_mcp_server.py
```

---

## ⚠️ 주의사항

### 무료 티어 제한

1. **슬리프 모드**
   - 15분간 요청이 없으면 서버가 슬리프 모드로 전환
   - 첫 요청 시 깨어나는데 약 30초 소요
   - 해커톤 제출용으로는 문제없음

2. **리소스 제한**
   - CPU: 0.1 CPU
   - RAM: 512MB
   - 네트워크: 100GB/월

### 해결 방법

- 슬리프 모드 방지: 유료 플랜 ($7/월) 사용
- 또는 무료로 사용하고 첫 요청 지연 시간 안내

---

## 🔧 문제 해결

### 문제 1: 배포 실패

**확인 사항:**
- `requirements.txt` 파일 존재 확인
- `src/main.py` 파일 존재 확인
- 빌드 로그 확인

**해결:**
- Render 대시보드의 "Logs" 탭에서 오류 확인
- 로컬에서 `pip install -r requirements.txt` 테스트

### 문제 2: 서버가 응답하지 않음

**확인 사항:**
- 서버가 슬리프 모드인지 확인 (첫 요청 시 30초 대기)
- Health 엔드포인트 확인

**해결:**
- 첫 요청 후 다시 시도
- 로그에서 오류 확인

### 문제 3: 환경 변수가 적용되지 않음

**확인 사항:**
- 환경 변수 이름 확인 (대소문자 구분)
- 서비스 재시작 필요

**해결:**
- "Manual Deploy" → "Clear build cache & deploy" 실행

---

## 📝 배포 완료 체크리스트

- [ ] Render 계정 생성 완료
- [ ] Web Service 생성 완료
- [ ] 환경 변수 설정 완료
- [ ] 배포 완료 확인
- [ ] Health 엔드포인트 정상 작동
- [ ] MCP Inspector 검증 통과
- [ ] 서비스 URL 저장 (해커톤 제출 시 필요)

---

## 🎉 배포 완료!

배포가 완료되면:
1. 서비스 URL을 `README.md`에 추가 (선택)
2. 해커톤 제출 시 공개 URL로 사용
3. MCP Inspector 검증 완료 확인

---

## 💡 팁

1. **자동 배포**: GitHub에 푸시하면 자동으로 재배포됨
2. **로그 확인**: 문제 발생 시 "Logs" 탭에서 실시간 로그 확인
3. **환경 변수**: 민감한 정보는 환경 변수로 관리
4. **슬리프 모드**: 무료 티어는 15분 비활성 시 슬리프 모드 (해커톤 제출용으로는 문제없음)

---

**배포 중 문제가 발생하면 Render 대시보드의 "Logs" 탭을 확인하세요!**

