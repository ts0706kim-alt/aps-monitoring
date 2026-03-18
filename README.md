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
