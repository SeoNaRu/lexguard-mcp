# Render 빠른 배포 가이드

## ⚡ 5분 안에 배포하기

### 1단계: Render 접속 및 로그인 (1분)

1. https://render.com 접속
2. "Get Started for Free" 클릭
3. **GitHub 계정으로 로그인** (가장 빠름)

---

### 2단계: Web Service 생성 (2분)

1. 대시보드에서 **"New +"** 클릭
2. **"Web Service"** 선택
3. GitHub 저장소 연결:
   - 저장소 목록에서 `LexGuardMcp` 선택
   - 또는 저장소 URL 입력

---

### 3단계: 설정 입력 (1분)

다음 정보를 입력:

**기본 정보:**
- **Name**: `lexguard-mcp`
- **Region**: `Singapore` (한국에서 가까움)
- **Branch**: `main`

**빌드 설정:**
- **Environment**: `Python 3`
- **Build Command**: 
  ```
  pip install -r requirements.txt
  ```
- **Start Command**: 
  ```
  python -m src.main
  ```

**인스턴스:**
- **Instance Type**: `Free` 선택

---

### 4단계: 환경 변수 설정 (1분)

**"Environment"** 섹션에서 다음 추가:

```
PORT=8099
LOG_LEVEL=INFO
RELOAD=false
LAW_API_KEY=LexGuardKey
```

> 💡 `LAW_API_KEY`는 실제 API 키로 변경하세요. 없으면 비워두어도 됩니다.

---

### 5단계: 배포 시작

1. **"Create Web Service"** 클릭
2. 배포가 자동으로 시작됨
3. **3-5분 대기** (빌드 및 배포 진행)

---

### 6단계: 배포 확인

배포 완료 후:

1. **서비스 URL 확인**
   - Render 대시보드에서 URL 확인
   - 예: `https://lexguard-mcp.onrender.com`

2. **Health 체크**
   ```
   https://your-service-url.onrender.com/health
   ```
   - 브라우저에서 접속하여 "OK" 확인

3. **MCP 엔드포인트 확인**
   ```
   https://your-service-url.onrender.com/mcp
   ```

---

## ✅ 배포 완료!

이제 다음을 실행하세요:

```bash
npx @modelcontextprotocol/inspector https://your-service-url.onrender.com/mcp
```

---

## ⚠️ 무료 티어 주의사항

- **슬리프 모드**: 15분간 요청이 없으면 서버가 잠듦
- **첫 요청 지연**: 슬리프 모드에서 깨어나는데 약 30초 소요
- **해결**: 해커톤 제출용으로는 문제없음 (심사 시 요청하면 깨어남)

---

## 🐛 문제 발생 시

1. **배포 실패**: Render 대시보드 → "Logs" 탭 확인
2. **서버 응답 없음**: 슬리프 모드일 수 있음 (30초 대기 후 재시도)
3. **환경 변수 오류**: "Manual Deploy" → "Clear build cache & deploy"

---

**자세한 내용은 `RENDER_DEPLOYMENT_STEPS.md` 참고하세요!**

