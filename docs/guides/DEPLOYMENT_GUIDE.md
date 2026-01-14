# 원격 서버 배포 가이드

LexGuard MCP 서버를 원격 서버에 배포하는 가이드입니다.

## 📋 배포 전 확인 사항

### 필수 확인
- [x] 로컬 서버 정상 작동 확인 완료
- [x] MCP Inspector 로컬 검증 완료
- [x] 모든 테스트 통과 (5/5)
- [ ] 원격 서버 계정 준비
- [ ] 도메인 또는 IP 주소 준비
- [ ] HTTPS 인증서 준비 (권장)

---

## 🚀 배포 옵션

### 옵션 1: 클라우드 플랫폼 (권장)

#### 1.1 Railway
- **장점**: 간단한 배포, 자동 HTTPS, 무료 티어 제공
- **URL**: https://railway.app
- **비용**: 무료 티어 (월 $5 크레딧)

#### 1.2 Render
- **장점**: 무료 티어, 자동 HTTPS, 쉬운 설정
- **URL**: https://render.com
- **비용**: 무료 티어 (15분 비활성 시 슬리프 모드)

#### 1.3 Fly.io
- **장점**: 글로벌 CDN, 빠른 배포
- **URL**: https://fly.io
- **비용**: 무료 티어 제공

#### 1.4 Heroku
- **장점**: 안정적, 널리 사용됨
- **URL**: https://heroku.com
- **비용**: 유료 (무료 티어 종료)

#### 1.5 AWS/GCP/Azure
- **장점**: 확장성, 안정성
- **단점**: 설정 복잡, 비용 발생 가능
- **비용**: 사용량 기반

---

### 옵션 2: VPS (Virtual Private Server)

#### 2.1 DigitalOcean
- **장점**: 간단한 설정, 저렴한 가격
- **URL**: https://digitalocean.com
- **비용**: $6/월부터

#### 2.2 Vultr
- **장점**: 빠른 속도, 다양한 지역
- **URL**: https://vultr.com
- **비용**: $6/월부터

#### 2.3 Linode
- **장점**: 안정적, 좋은 문서
- **URL**: https://linode.com
- **비용**: $5/월부터

---

## 📝 배포 단계 (Railway 예시)

### 1단계: Railway 계정 생성 및 프로젝트 생성

1. https://railway.app 접속
2. GitHub 계정으로 로그인
3. "New Project" 클릭
4. "Deploy from GitHub repo" 선택
5. 저장소 선택

### 2단계: 환경 변수 설정

Railway 대시보드에서:
1. "Variables" 탭 클릭
2. 다음 환경 변수 추가:
   ```
   LAW_API_KEY=your_api_key_here
   PORT=8099
   LOG_LEVEL=INFO
   RELOAD=false
   ```

### 3단계: 배포 설정

Railway는 자동으로 감지하지만, 필요시 `railway.json` 생성:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python -m src.main",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### 4단계: 배포 확인

1. Railway 대시보드에서 배포 상태 확인
2. 배포 완료 후 제공되는 URL 확인 (예: `https://your-app.railway.app`)
3. Health 엔드포인트 확인: `https://your-app.railway.app/health`
4. MCP 엔드포인트 확인: `https://your-app.railway.app/mcp`

---

## 📝 배포 단계 (Render 예시)

### 1단계: Render 계정 생성

1. https://render.com 접속
2. GitHub 계정으로 로그인

### 2단계: 새 Web Service 생성

1. "New +" 클릭
2. "Web Service" 선택
3. GitHub 저장소 연결
4. 설정:
   - **Name**: lexguard-mcp
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python -m src.main`
   - **Port**: 8099

### 3단계: 환경 변수 설정

"Environment" 섹션에서:
```
LAW_API_KEY=your_api_key_here
PORT=8099
LOG_LEVEL=INFO
RELOAD=false
```

### 4단계: 배포 확인

1. Render 대시보드에서 배포 상태 확인
2. 배포 완료 후 제공되는 URL 확인
3. Health 엔드포인트 확인

---

## 📝 배포 단계 (VPS 예시)

### 1단계: 서버 설정

```bash
# 서버 접속
ssh user@your-server-ip

# Python 3.11+ 설치 확인
python3 --version

# Git 설치
sudo apt update
sudo apt install git -y

# 프로젝트 클론
git clone https://github.com/your-username/LexGuardMcp.git
cd LexGuardMcp
```

### 2단계: 의존성 설치

```bash
# Python 가상환경 생성
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 3단계: 환경 변수 설정

```bash
# .env 파일 생성
cp env.example .env
nano .env

# 내용 입력:
# LAW_API_KEY=your_api_key_here
# PORT=8099
# LOG_LEVEL=INFO
# RELOAD=false
```

### 4단계: Systemd 서비스 설정

```bash
# 서비스 파일 생성
sudo nano /etc/systemd/system/lexguard-mcp.service
```

내용:
```ini
[Unit]
Description=LexGuard MCP Server
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/home/your-username/LexGuardMcp
Environment="PATH=/home/your-username/LexGuardMcp/venv/bin"
ExecStart=/home/your-username/LexGuardMcp/venv/bin/python -m src.main
Restart=always

[Install]
WantedBy=multi-user.target
```

### 5단계: Nginx 리버스 프록시 설정

```bash
# Nginx 설치
sudo apt install nginx -y

# 설정 파일 생성
sudo nano /etc/nginx/sites-available/lexguard-mcp
```

내용:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8099;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# 심볼릭 링크 생성
sudo ln -s /etc/nginx/sites-available/lexguard-mcp /etc/nginx/sites-enabled/

# Nginx 재시작
sudo systemctl restart nginx
```

### 6단계: HTTPS 설정 (Let's Encrypt)

```bash
# Certbot 설치
sudo apt install certbot python3-certbot-nginx -y

# SSL 인증서 발급
sudo certbot --nginx -d your-domain.com

# 자동 갱신 설정
sudo certbot renew --dry-run
```

### 7단계: 서비스 시작

```bash
# 서비스 시작
sudo systemctl start lexguard-mcp
sudo systemctl enable lexguard-mcp

# 상태 확인
sudo systemctl status lexguard-mcp
```

---

## ✅ 배포 후 검증

### 1. Health 엔드포인트 확인

```bash
curl https://your-domain.com/health
```

또는 브라우저에서 접속:
```
https://your-domain.com/health
```

### 2. MCP Inspector로 검증

```bash
npx @modelcontextprotocol/inspector https://your-domain.com/mcp
```

예상 결과:
```
✓ MCP Server: https://your-domain.com/mcp
✓ Protocol Version: 2025-03-26
✓ Initialize: OK
✓ Tools/List: OK (20 tools found)
✓ Tools/Call: OK
✓ All checks passed!
```

### 3. 테스트 스크립트 실행

`test_mcp_server.py` 수정:
```python
BASE_URL = "https://your-domain.com"  # 로컬에서 원격 서버로 변경
```

```bash
python test_mcp_server.py
```

---

## 🔒 보안 체크리스트

- [ ] HTTPS 사용 (SSL/TLS 인증서)
- [ ] `.env` 파일이 Git에 포함되지 않음
- [ ] API 키가 코드에 하드코딩되지 않음
- [ ] 방화벽 설정 (필요한 포트만 열기)
- [ ] 정기적인 보안 업데이트

---

## 📊 모니터링

### 로그 확인

**Railway/Render:**
- 대시보드에서 로그 확인

**VPS:**
```bash
# 서비스 로그 확인
sudo journalctl -u lexguard-mcp -f

# 또는 파일 로그
tail -f /var/log/lexguard-mcp.log
```

### 성능 모니터링

- 서버 리소스 사용량 확인
- 응답 시간 모니터링
- 에러율 확인

---

## 🐛 문제 해결

### 문제 1: 서버가 시작되지 않음

**확인 사항:**
- Python 버전 (3.11+)
- 의존성 설치 완료
- 환경 변수 설정
- 포트 충돌

**해결:**
```bash
# 로그 확인
sudo journalctl -u lexguard-mcp -n 50

# 수동 실행으로 오류 확인
python -m src.main
```

### 문제 2: MCP Inspector 검증 실패

**확인 사항:**
- HTTPS 설정
- CORS 설정
- 서버 실행 상태

**해결:**
- Health 엔드포인트 먼저 확인
- 로컬에서 테스트 후 원격 배포

### 문제 3: 응답 시간 느림

**확인 사항:**
- 서버 리소스
- 네트워크 연결
- 캐싱 설정

**해결:**
- 서버 리소스 업그레이드
- CDN 사용 고려

---

## 📚 참고 자료

- [Railway 문서](https://docs.railway.app)
- [Render 문서](https://render.com/docs)
- [Nginx 리버스 프록시](https://nginx.org/en/docs/http/ngx_http_proxy_module.html)
- [Let's Encrypt](https://letsencrypt.org)

---

## 💡 팁

1. **무료 티어 활용**: Railway, Render 등 무료 티어로 시작
2. **자동 배포**: GitHub에 푸시하면 자동 배포되도록 설정
3. **백업**: 정기적으로 데이터 백업
4. **모니터링**: 서버 상태를 정기적으로 확인

---

## ✅ 배포 완료 체크리스트

- [ ] 원격 서버 배포 완료
- [ ] HTTPS 설정 완료
- [ ] Health 엔드포인트 정상 작동
- [ ] MCP Inspector 검증 통과
- [ ] 모든 툴 정상 작동
- [ ] 로그 모니터링 설정
- [ ] 문서 업데이트 (README.md에 배포 URL 추가)

---

**배포 완료 후 해커톤 제출 준비 완료!** 🎉

