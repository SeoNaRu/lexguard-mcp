# 문제 해결 가이드

## 포트 충돌 오류 (WinError 10013)

### 증상
```
ERROR: [WinError 10013] 액세스 권한에 의해 숨겨진 소켓에 액세스를 시도했습니다
```

### 원인
포트 8099가 이미 다른 프로세스에 의해 사용 중입니다.

### 해결 방법

#### 방법 1: 사용 중인 프로세스 종료 (권장)

**PowerShell:**
```powershell
# 포트 사용 프로세스 확인
netstat -ano | findstr :8099

# 프로세스 종료 (PID를 위 명령어 결과에서 확인)
Stop-Process -Id <PID> -Force
```

**Windows CMD:**
```cmd
netstat -ano | findstr :8099
taskkill /F /PID <PID>
```

#### 방법 2: 다른 포트 사용

**PowerShell:**
```powershell
$env:PORT=8100
python -m uvicorn src.main:api --host 0.0.0.0 --port 8100
```

**Windows CMD:**
```cmd
set PORT=8100
python -m uvicorn src.main:api --host 0.0.0.0 --port 8100
```

#### 방법 3: 자동 스크립트 사용

**PowerShell:**
```powershell
.\start_server.ps1
```

**Windows CMD:**
```cmd
start_server.bat
```

스크립트가 자동으로 포트 충돌을 확인하고 해결합니다.

---

## 상대 Import 오류

### 증상
```
ImportError: attempted relative import with no known parent package
```

### 원인
`python src/main.py`로 직접 실행하면 상대 import가 작동하지 않습니다.

### 해결 방법

**올바른 실행 방법:**
```bash
# 방법 1: uvicorn 사용 (권장)
python -m uvicorn src.main:api --host 0.0.0.0 --port 8099

# 방법 2: 모듈로 실행
python -m src.main
```

**잘못된 실행 방법:**
```bash
python src/main.py  # ❌ 작동하지 않음
```

---

## 관리자 권한 필요 오류

### 증상
포트 바인딩 시 권한 오류 발생

### 해결 방법

1. **다른 포트 사용 (1024 이상):**
   ```bash
   python -m uvicorn src.main:api --host 127.0.0.1 --port 8099
   ```

2. **관리자 권한으로 실행:**
   - PowerShell을 관리자 권한으로 실행
   - 또는 `start_server.ps1`을 관리자 권한으로 실행

---

## Python 모듈을 찾을 수 없음

### 증상
```
ModuleNotFoundError: No module named 'src'
```

### 해결 방법

1. **프로젝트 루트에서 실행:**
   ```bash
   cd C:\Users\seonaru\Desktop\LexGuardMcp
   python -m uvicorn src.main:api --host 0.0.0.0 --port 8099
   ```

2. **의존성 설치 확인:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 일반적인 문제 해결 체크리스트

- [ ] 프로젝트 루트 디렉토리에서 실행했는가?
- [ ] Python이 PATH에 추가되어 있는가? (`python --version` 확인)
- [ ] 모든 의존성이 설치되었는가? (`pip install -r requirements.txt`)
- [ ] 포트 8099가 사용 가능한가? (`netstat -ano | findstr :8099`)
- [ ] `.env` 파일이 올바르게 설정되었는가?
- [ ] `python -m` 옵션을 사용했는가? (직접 실행 대신)

---

## 빠른 테스트

서버가 정상적으로 실행되었는지 확인:

```powershell
# Health 체크
Invoke-WebRequest -Uri "http://localhost:8099/health" -Method GET

# MCP Initialize 테스트
$body = @{
    jsonrpc = "2.0"
    method = "initialize"
    id = 1
    params = @{
        protocolVersion = "2025-03-26"
        capabilities = @{}
    }
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://localhost:8099/mcp" -Method POST -Body $body -ContentType "application/json"
```

