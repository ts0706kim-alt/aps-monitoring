# 모니터링 프로그램 (Buds4 Pro & AirPods Pro3)

글로벌 채널(Amazon, Samsung.com, Currys 등)에서 **가격**, **리뷰 수**, **평점**, **프로모션**을 수집하는 모니터링 솔루션입니다.

---

## 다른 사람이 다운로드해서 바로 쓰는 방법 (가장 쉬운 순서)

### 1. Python 설치 (없는 경우만)

- [python.org](https://www.python.org/downloads/) 에서 **Python 3.10 이상** 다운로드 후 설치
- 설치 시 **"Add Python to PATH"** 체크

### 2. 프로젝트 다운로드

**방법 A – Git 사용 시**
```bash
git clone https://github.com/ts0706kim-alt/aps-monitoring.git
cd aps-monitoring
```

**방법 B – ZIP으로 받기**
- GitHub 저장소 페이지에서 **Code → Download ZIP** 클릭
- ZIP 압축 해제 후 해당 폴더로 이동

### 3. 한 번만 설치 (Windows)

폴더 안에서 **아래 중 하나**만 실행하면 됩니다.

- **`install_once.bat`** 더블클릭  
  → 가상환경 생성, 패키지 설치, Playwright 브라우저 설치까지 자동 진행

또는 PowerShell을 연 뒤:
```powershell
cd "다운로드한_폴더_경로"
.\setup_windows.ps1
```

### 4. 실행

- **`run_app.bat`** 더블클릭  
  → 웹 앱이 실행되면 브라우저에서 **http://127.0.0.1:5000** 접속

**정리:** 처음 한 번만 `install_once.bat` 실행 → 이후에는 `run_app.bat`만 더블클릭하면 됩니다.

---

## 주요 기능

- **웹 UI**: 브라우저에서 모니터링 실행 및 결과 조회
- **엑셀 다운로드**: 수집 결과를 `.xlsx`로 저장
- **Playwright 기반**: JavaScript 렌더링 사이트 지원
- **다국가**: US, UK 등 채널 동시 모니터링

## 요구사항

- Python 3.10+
- Playwright (Chromium) — `install_once.bat` 또는 `setup_windows.ps1` 실행 시 자동 설치

## 수동 설치 (원할 경우)

```bash
git clone https://github.com/ts0706kim-alt/aps-monitoring.git
cd aps-monitoring
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
playwright install chromium
```

## 설정

`targets.csv`에 모니터링할 URL을 지정합니다.

| 컬럼        | 설명                  |
|-------------|-----------------------|
| Country     | US, UK, DE 등         |
| Channel     | Amazon, Best Buy 등   |
| URL         | 상품 페이지 URL       |
| Product_Name| 상품명                |

기존 `targets.csv`를 수정하거나 `config_template.csv`를 복사해 새로 작성할 수 있습니다.

### 이메일 발송 설정 (데일리 + 이메일 사용 시)

`email_config.json.example`을 복사해 `email_config.json`을 만들고 SMTP 정보를 입력합니다.

```json
{
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "use_tls": true,
  "username": "your_email@gmail.com",
  "password": "your_app_password",
  "from_addr": "your_email@gmail.com",
  "to_addrs": ["recipient@example.com"],
  "subject_prefix": "[APS 모니터링] "
}
```

- **Gmail**: [앱 비밀번호](https://myaccount.google.com/apppasswords) 생성 후 `password`에 입력
- **네이버**: `smtp.naver.com`, 포트 587
- `email_config.json`은 `.gitignore`에 포함되어 있어 저장소에 올라가지 않습니다

## 사용법

### 웹 앱으로 실행 (권장)

- **`run_app.bat`** 더블클릭 후 브라우저에서 **http://127.0.0.1:5000** 접속  
또는 터미널에서 `python app.py` / `py app.py`

1. **모니터링 실행** 버튼 클릭 (약 1~4분 소요)
2. 결과 테이블 확인
3. **엑셀 다운로드**로 `.xlsx` 저장

### 콘솔에서만 실행 (엑셀만 생성)

- **`run_monitor.bat`** 더블클릭 또는 `python playwright_monitor.py`

## 데일리 자동 실행 (Windows)

매일 정해진 시각에 모니터링을 자동 실행하려면 **Windows 작업 스케줄러**에 등록하면 됩니다.

### 1. 등록

PowerShell에서 프로젝트 폴더로 이동한 뒤 실행합니다.

```powershell
.\register_daily_task.ps1
```

- 기본: **매일 오전 9시**에 모니터링 실행 (결과만 엑셀 저장)
- **이메일 발송 포함** (매일 오후 12시, 결과 Excel 첨부):
  ```powershell
  .\register_daily_task.ps1 -WithEmail
  ```
- 실행 시각 변경: `.\register_daily_task.ps1 -Time "18:30"` (오후 6시 30분)
- 작업 이름 변경: `.\register_daily_task.ps1 -TaskName "My-APS-Daily"`

### 2. 확인/수정

- **작업 스케줄러** (`Win + R` → `taskschd.msc`) 실행
- **작업 스케줄러 라이브러리**에서 `APS-Monitoring-Daily` 찾기
- 더블클릭하여 트리거(실행 시각), 조건, 설정 변경 가능

### 3. 해제

```powershell
.\unregister_daily_task.ps1
```

### 스케줄 실행 시 참고

- **로그**: 매 실행 시 `logs` 폴더에 `monitor_YYYYMMDD_HHMMSS.log` 로 저장됩니다.
- **결과 파일**: 엑셀은 `aps_monitoring_result.xlsx`(또는 타임스탬프 붙은 파일)에 저장됩니다.
- **이메일**: `-WithEmail` 옵션 사용 시 결과 Excel이 첨부되어 지정된 수신자에게 발송됩니다.
- **PC 전원**: 노트북이라면 “절전 시에도 작업 실행 허용” 등은 작업 스케줄러에서 해당 작업 속성 → **조건** 탭에서 설정할 수 있습니다.

## PC 없이 실행 (GitHub Actions)

PC를 켜지 않아도 **GitHub 서버**에서 매일 모니터링을 실행하고 이메일로 결과를 발송할 수 있습니다.

### 1. GitHub Secrets 설정

저장소 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret 이름 | 설명 | 필수 |
|-------------|------|------|
| `EMAIL_USERNAME` | SMTP 로그인 이메일 | ✓ |
| `EMAIL_PASSWORD` | SMTP 비밀번호 (Gmail: 앱 비밀번호) | ✓ |
| `EMAIL_TO` | 수신자 이메일 (여러 명: `a@x.com,b@y.com`) | ✓ |
| `EMAIL_FROM` | 발신자 표시 (선택, 기본: EMAIL_USERNAME) | |
| `EMAIL_SMTP_SERVER` | SMTP 서버 (선택, 기본: smtp.gmail.com) | |
| `EMAIL_SMTP_PORT` | SMTP 포트 (선택, 기본: 587) | |

### 2. 자동 실행

- **기본**: 매일 **12:00 KST**(한국 시간 정오)에 자동 실행
- **수동 실행**: 저장소 → **Actions** → **APS Daily Monitor** → **Run workflow**

### 3. 실행 시각 변경

`.github/workflows/daily-monitor.yml`에서 `cron` 값을 수정합니다. (UTC 기준)

```yaml
# 예: 09:00 KST = 00:00 UTC
- cron: "0 0 * * *"
```

### 4. 참고

- 일부 사이트(Amazon 등)는 데이터센터 IP를 차단할 수 있어, GitHub에서 실행 시 실패할 수 있습니다.
- 실패 시 **Actions** 탭에서 결과 파일을 다운로드할 수 있습니다.

## 출력 컬럼

| 컬럼         | 설명           |
|--------------|----------------|
| date         | 수집 일자      |
| country      | 국가           |
| channel      | 채널명         |
| product_name | 상품명         |
| final_url    | 최종 리다이렉트 URL |
| price        | 가격           |
| currency     | 통화 (USD, GBP, EUR) |
| rating       | 평점           |
| review_count | 리뷰 개수      |
| promo_text   | 프로모션 메시지 |

## 주의사항

- **차단 방지**: 사이트별 요청 간격을 두고 있으나, 과도한 실행 시 IP 차단될 수 있습니다.
- **페이지 구조 변경**: 각 사이트가 HTML을 변경하면 파싱이 깨질 수 있어 주기적으로 점검이 필요합니다.
- **개발 서버**: `app.py`는 Flask 개발 서버를 사용합니다. 운영 환경에서는 Gunicorn 등 WSGI 서버 사용을 권장합니다.

## 라이선스

MIT (또는 프로젝트에 맞게 설정)
