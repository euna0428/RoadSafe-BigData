# RoadSafe Program

RoadSafe는 전국 교통사고 다발지역 데이터, 시간대별·기상상태별 사고 통계, 현재 기상정보, GPS 위치, 카카오 지도/길찾기 API를 결합해 **위험구간 지도 확인 + 웹 내비게이션형 경로 위험 알림**을 제공하는 프로젝트입니다.

## 핵심 기능

- 전국 사고다발지역 표준데이터 기반 위험구간 시각화
- 낮음, 보통, 높음, 매우높음 전체 위험등급 지도 표시
- 시/도, 시/군/구, 위험등급 필터 검색
- 목적지 검색 기능
- 현재 위치에서 목적지까지 경로 위험 분석
- GPS 기반 내 위치 주변 위험구간 20개 표시
- GPS 이동 추적 중 위험구간 알림반경 진입 시 화면 경고
- 브라우저 음성 합성 기반 위험구간 접근 음성 경고
- 현재 날씨와 현재 시간대를 반영한 실시간 위험점수 계산
- Kakao Maps 기반 지도 표시 및 Kakao Mobility 길찾기 REST API 기반 경로 분석

## API 키 적용 상태

현재 프로젝트는 API 키를 코드에 직접 넣지 않고 프로젝트 루트의 `.env` 파일에서 읽습니다.

```env
KMA_SERVICE_KEY=기상청_API_키
KAKAO_JS_KEY=카카오_JavaScript_키
KAKAO_REST_KEY=카카오_REST_API_키
```

- `KMA_SERVICE_KEY`: 기상청 현재 기상정보 수집에 사용합니다.
- `KAKAO_JS_KEY`: 카카오 지도 표시와 장소 검색에 사용합니다.
- `KAKAO_REST_KEY`: 현재 위치에서 목적지까지의 자동차 경로 좌표를 받아오는 데 사용합니다.

`KAKAO_REST_KEY`가 없으면 출발지와 목적지를 직선으로 연결해 임시 분석하므로, 실제 도로 경로 기준 분석을 하려면 REST API 키가 필요합니다.

## 위험도 산정 기준

RoadSafe의 위험도는 단순 사고건수만 기준으로 하지 않습니다. 사고 빈도와 인명피해 심각도를 함께 반영합니다.

```text
사고위험원점수 = 사고건수 × 1 + 사망자수 × 10 + 중상자수 × 5 + 경상자수 × 2 + 부상신고자수 × 1
정적위험점수 = 사고위험원점수를 0~100 범위로 정규화한 값
실시간위험점수 = 정적위험점수 + 기상가중치 + 시간가중치
```

사망자수가 같은 경우에는 중상자수, 경상자수, 부상신고자수, 사고건수 순서로 점수가 갈립니다. 모든 값이 같으면 데이터상 근거가 동일하므로 같은 점수를 부여합니다.

| 점수 구간 | 위험등급 | 알림 반경 |
|---:|---|---:|
| 0~25 | 낮음 | 200m |
| 25 초과~50 | 보통 | 300m |
| 50 초과~75 | 높음 | 400m |
| 75 초과~100 | 매우높음 | 500m |

자세한 기준은 `docs/risk_score_criteria.md`를 확인하세요.

## 실행 준비

프로젝트 폴더로 이동한 뒤 아래 순서로 실행합니다.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

이미 `.venv`가 만들어져 있고 패키지 설치가 끝난 상태라면, 다음 실행부터는 가상환경 활성화 후 바로 실행하면 됩니다.

```bash
.venv\Scripts\activate
```

## 실행 순서

### 1단계: 전체 분석 파이프라인 실행

정적 위험도 테이블, 분석 그래프, 기본 위험지도, 모델 결과를 생성합니다.

```bash
python main.py
```

생성 결과:

```text
data/processed/final_risk_table.csv
outputs/figures/*.png
outputs/maps/risk_map.html
outputs/tables/*.csv
outputs/models/best_risk_model.pkl
```

### 2단계: 현재 날씨와 시간대 반영 실시간 지도 갱신

기상청 API를 호출해 현재 날씨를 수집하고, 현재 시간대와 결합해 실시간 위험도 지도를 다시 생성합니다.

```bash
python src/realtime_runner.py
```

생성 결과:

```text
data/raw/forecast/current_weather.csv
data/processed/live_risk_table.csv
outputs/maps/live_risk_map.html
outputs/tables/live_risk_change_summary.csv
```

### 3단계: 웹 지도 서버 실행

경로 검색과 경로상 위험구간 분석 API를 함께 제공하는 로컬 서버를 실행합니다.

```bash
python src/navigation_server.py
```

터미널에 아래 문구가 나오면 서버가 켜진 상태입니다.

```text
RoadSafe 내비게이션 서버 실행: http://127.0.0.1:8000/
종료: Ctrl + C
```

### 4단계: 브라우저 접속 주소

브라우저에서 아래 주소를 엽니다.

```text
http://127.0.0.1:8000/
```

같은 서버를 localhost로 열 수도 있습니다.

```text
http://localhost:8000/
```

카카오 Developers의 JavaScript SDK 도메인에는 아래 주소가 등록되어 있어야 합니다.

```text
http://127.0.0.1:8000
http://localhost:8000
```

## 화면에서 사용할 수 있는 기능

1. 지역/등급 필터로 기존 위험구간 확인
2. 내 위치 주변 위험구간 확인
3. 목적지 검색
4. 현재 위치에서 목적지까지 경로 위험 분석
5. 이동 중 경로상 위험구간 접근 시 화면 경고 및 음성 경고

## 주요 산출물

| 산출물 | 설명 |
|---|---|
| `outputs/maps/risk_map.html` | 정적 위험도 지도 |
| `outputs/maps/live_risk_map.html` | 현재 날씨/시간대 반영 실시간 위험도 + 경로 분석 지도 |
| `data/processed/final_risk_table.csv` | 정적 위험도 기준 테이블 |
| `data/processed/live_risk_table.csv` | 현재 날씨/시간대 반영 실시간 위험도 테이블 |
| `docs/risk_score_criteria.md` | 위험도 산정 기준 설명 |
| `docs/navigation_extension.md` | 웹 내비게이션형 확장 설명 |

## 보안 주의

`.env` 파일은 실행 편의를 위해 로컬 프로젝트에서만 사용합니다. GitHub 공개 저장소에는 올리지 않습니다. 카카오 JavaScript 키는 웹 지도 SDK 특성상 브라우저에서 확인될 수 있으므로, Kakao Developers에서 JavaScript SDK 도메인을 반드시 `127.0.0.1:8000`, `localhost:8000` 등 필요한 주소로 제한해야 합니다.
