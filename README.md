# APS 모니터링 (Buds4 Pro)

글로벌 채널(Amazon, Best Buy, Samsung.com, Currys, Mediamarkt 등)에서 **가격**, **리뷰 수**, **평점**, **프로모션**을 수집하는 모니터링 솔루션입니다.

## 주요 기능

- **웹 UI**: 브라우저에서 모니터링 실행 및 결과 조회
- **엑셀 다운로드**: 수집 결과를 `.xlsx`로 저장
- **Playwright 기반**: JavaScript 렌더링 사이트 지원
- **다국가**: US, UK, DE 등 3개국 채널 동시 모니터링

## 요구사항

- Python 3.9+
- Playwright (브라우저 자동화)

## 설치

### 1. 저장소 클론

```bash
git clone https://github.com/YOUR_USERNAME/aps-monitoring.git
cd aps-monitoring
```

### 2. 가상환경 생성 (권장)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. 패키지 설치

```bash
pip install -r requirements.txt
```

### 4. Playwright 브라우저 설치

```bash
playwright install chromium
```

### (Windows) 가장 쉬운 설치 방법

PowerShell에서 아래 한 번만 실행하면 됩니다.

```powershell
.\setup_windows.ps1
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

## 사용법

### 웹 앱으로 실행

```bash
python app.py
```

브라우저에서 **http://127.0.0.1:5000** 접속 후:

1. **모니터링 실행** 버튼 클릭 (약 1~4분 소요)
2. 결과 테이블 확인
3. **엑셀 다운로드**로 `.xlsx` 저장

### Windows에서 빠른 실행

```bash
run_app.bat
```

### 콘솔(엑셀 생성)로 실행

```bash
run_monitor.bat
```

## 데일리 자동 실행 (Windows)

매일 정해진 시각에 모니터링을 자동 실행하려면 **Windows 작업 스케줄러**에 등록하면 됩니다.

### 1. 등록

PowerShell에서 프로젝트 폴더로 이동한 뒤 실행합니다.

```powershell
.\register_daily_task.ps1
```

- 기본: **매일 오전 9시**에 `run_monitor_scheduled.bat` 실행
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
- **결과 파일**: `playwright_monitor.py`가 생성하는 엑셀은 프로젝트 폴더의 `aps_monitoring_result.xlsx`(또는 타임스탬프 붙은 파일)에 저장됩니다.
- **PC 전원**: 노트북이라면 “절전 시에도 작업 실행 허용” 등은 작업 스케줄러에서 해당 작업 속성 → **조건** 탭에서 설정할 수 있습니다.

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
