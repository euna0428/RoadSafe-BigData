from __future__ import annotations

from datetime import datetime
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from typing import Any

import pandas as pd
from tqdm import tqdm
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
RAW_FORECAST_PATH = PROJECT_ROOT / "data" / "raw" / "forecast" / "current_weather.csv"
RAW_INCIDENT_PATH = PROJECT_ROOT / "data" / "raw" / "incident" / "current_incident.csv"
STATIC_PATH = PROCESSED_DIR / "final_risk_table.csv"
OUTPUT_PATH = PROCESSED_DIR / "live_risk_table.csv"
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"
KST = ZoneInfo("Asia/Seoul")

INCIDENT_MATCH_RADIUS_M = 1000
INCIDENT_WEIGHT_MAX = 20


INCIDENT_TYPE_WEIGHT = {
    "교통사고": 20,
    "사고": 20,
    "재난": 18,
    "기상": 16,
    "공사": 12,
    "기타돌발": 10,
    "기타": 8,
}


def safe_text(value: Any, default: str = "") -> str:
    if value is None or pd.isna(value):
        return default
    return str(value).strip()


def safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        result = float(value)
        if pd.isna(result):
            return default
        return result
    except Exception:
        return default


def extract_region_key(region_name: str) -> str:
    if pd.isna(region_name):
        return "기타"
    tokens = str(region_name).strip().split()
    return tokens[0] if tokens else "기타"


def normalize_weather_label(label: str) -> str:
    if pd.isna(label):
        return "알수없음"
    text = str(label).strip()

    if "안개" in text:
        return "안개"
    if "소나기" in text:
        return "비"
    if "비/눈" in text or ("비" in text and "눈" in text):
        return "비/눈"
    if "눈" in text:
        return "눈"
    if "비" in text:
        return "비"
    if "구름" in text or "흐림" in text:
        return "흐림"
    if "맑음" in text or "강수없음" in text:
        return "맑음"
    return text


def classify_risk(score: float) -> str:
    if score <= 25:
        return "낮음"
    if score <= 50:
        return "보통"
    if score <= 75:
        return "높음"
    return "매우높음"


def calc_alert_radius(score: float) -> int:
    if score >= 75:
        return 500
    if score >= 50:
        return 400
    if score >= 25:
        return 300
    return 200


def current_time_band(now_kst: datetime) -> str:
    hour = now_kst.hour
    start = (hour // 2) * 2
    end = start + 2
    return f"{start:02d}시-{end:02d}시"


def weather_weight(current_weather_norm: str, caution_weather_norm: str, rain_1h_mm: Any = 0, wind_speed_ms: Any = 0) -> tuple[int, str]:
    score = 0
    reasons: list[str] = []
    rain = safe_float(rain_1h_mm, 0) or 0
    wind = safe_float(wind_speed_ms, 0) or 0

    if current_weather_norm == caution_weather_norm and current_weather_norm not in {"알수없음", "맑음"}:
        score += 18
        reasons.append("주의기상상태 일치")

    if current_weather_norm in {"비", "비/눈", "눈"}:
        score += 12
        reasons.append("강수/적설 상태")
    elif current_weather_norm in {"흐림", "안개"}:
        score += 6
        reasons.append("시야/구름 상태")

    if rain >= 5:
        score += 8
        reasons.append("시간강수량 5mm 이상")
    elif rain > 0:
        score += 4
        reasons.append("시간강수량 발생")

    if wind >= 9:
        score += 6
        reasons.append("강풍 주의")

    if score == 0:
        reasons.append("기상 가중치 없음")

    return min(score, 30), ", ".join(reasons)


def time_weight(now_band: str, caution_band: str) -> tuple[int, str]:
    caution = str(caution_band).strip()
    if now_band == caution:
        return 10, "주의시간대 일치"
    return 0, "시간 가중치 없음"


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371000
    lat1_r, lon1_r, lat2_r, lon2_r = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r
    a = sin(dlat / 2) ** 2 + cos(lat1_r) * cos(lat2_r) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return radius * c


def normalize_incident_type(label: Any) -> str:
    text = safe_text(label, "기타")
    if "사고" in text:
        return "교통사고"
    if "공사" in text:
        return "공사"
    if "기상" in text or "침수" in text or "결빙" in text:
        return "기상"
    if "재난" in text:
        return "재난"
    if "기타" in text:
        return "기타돌발"
    return text or "기타"


def load_incident_df() -> pd.DataFrame:
    if not RAW_INCIDENT_PATH.exists():
        return pd.DataFrame(columns=["incident_type", "lat", "lon", "message", "road_name", "api_status"])

    incident_df = pd.read_csv(RAW_INCIDENT_PATH, encoding="utf-8-sig")
    incident_df.columns = incident_df.columns.astype(str).str.strip()

    if "api_status" in incident_df.columns:
        incident_df = incident_df[incident_df["api_status"].astype(str).str.upper().eq("OK")].copy()

    for column in ["lat", "lon"]:
        if column not in incident_df.columns:
            incident_df[column] = pd.NA
        incident_df[column] = pd.to_numeric(incident_df[column], errors="coerce")

    return incident_df.dropna(subset=["lat", "lon"]).reset_index(drop=True)


def nearest_incident_info(lat: Any, lon: Any, incident_df: pd.DataFrame) -> dict[str, Any]:
    lat_value = safe_float(lat)
    lon_value = safe_float(lon)
    if lat_value is None or lon_value is None or incident_df.empty:
        return {
            "돌발상황가중치": 0,
            "돌발상황사유": "근접 돌발상황 없음",
            "가까운돌발상황거리m": None,
            "가까운돌발상황유형": "",
            "가까운돌발상황도로명": "",
            "가까운돌발상황내용": "",
        }

    best_distance = None
    best_row = None
    for row in incident_df.itertuples(index=False):
        dist = haversine_m(lat_value, lon_value, float(row.lat), float(row.lon))
        if best_distance is None or dist < best_distance:
            best_distance = dist
            best_row = row

    if best_distance is None or best_row is None or best_distance > INCIDENT_MATCH_RADIUS_M:
        return {
            "돌발상황가중치": 0,
            "돌발상황사유": "근접 돌발상황 없음",
            "가까운돌발상황거리m": round(best_distance, 1) if best_distance is not None else None,
            "가까운돌발상황유형": "",
            "가까운돌발상황도로명": "",
            "가까운돌발상황내용": "",
        }

    incident_type = normalize_incident_type(getattr(best_row, "incident_type", "기타"))
    base_weight = INCIDENT_TYPE_WEIGHT.get(incident_type, 8)
    distance_factor = max(0, 1 - (best_distance / INCIDENT_MATCH_RADIUS_M))
    score = round(min(INCIDENT_WEIGHT_MAX, base_weight * (0.5 + 0.5 * distance_factor)), 2)

    return {
        "돌발상황가중치": score,
        "돌발상황사유": f"{int(best_distance)}m 이내 {incident_type} 발생",
        "가까운돌발상황거리m": round(best_distance, 1),
        "가까운돌발상황유형": incident_type,
        "가까운돌발상황도로명": safe_text(getattr(best_row, "road_name", "")),
        "가까운돌발상황내용": safe_text(getattr(best_row, "message", "")),
    }


def classify_change(delta: float, incident_score: float, weather_score: float) -> str:
    if incident_score >= 10 or (weather_score >= 18 and delta >= 10):
        return "긴급 주의"
    if delta >= 10:
        return "위험 상승"
    if delta <= -10:
        return "위험 완화"
    return "유지"


def build_change_reason(row: pd.Series) -> str:
    reasons: list[str] = []
    for col in ["기상가중치사유", "시간가중치사유", "돌발상황사유"]:
        value = safe_text(row.get(col, ""))
        if value and "없음" not in value:
            reasons.append(value)
    if not reasons:
        return "실시간 조건 변화 없음"
    return " / ".join(reasons)


def update_live_risk() -> pd.DataFrame:
    if not STATIC_PATH.exists():
        raise FileNotFoundError(f"정적 위험 테이블이 없습니다: {STATIC_PATH}")
    if not RAW_FORECAST_PATH.exists():
        raise FileNotFoundError(
            f"현재 날씨 파일이 없습니다: {RAW_FORECAST_PATH}\nfetch_forecast.py를 먼저 실행해 주세요."
        )

    now_kst = datetime.now(KST)
    now_band = current_time_band(now_kst)

    print("\n[update_live_risk] 시작")

    with tqdm(total=10, desc="실시간 위험도 갱신", ncols=100) as pbar:
        static_df = pd.read_csv(STATIC_PATH, encoding="utf-8-sig")
        weather_df = pd.read_csv(RAW_FORECAST_PATH, encoding="utf-8-sig")
        static_df.columns = static_df.columns.str.strip()
        weather_df.columns = weather_df.columns.str.strip()
        pbar.set_postfix_str("CSV 읽기 완료")
        pbar.update(1)

        static_df["region_key"] = static_df["사고다발지역시도시군구"].apply(extract_region_key)
        weather_df["region_key"] = weather_df["region_key"].astype(str).str.strip()
        pbar.set_postfix_str("병합키 생성")
        pbar.update(1)

        weather_cols = [
            "region_key", "current_weather", "current_weather_raw", "current_temp_c",
            "humidity_pct", "rain_1h_mm", "wind_speed_ms", "obs_time", "collected_at_kst", "api_status",
            "cache_status", "last_error_status", "fallback_region_key", "fallback_distance_m", "fallback_note"
        ]
        available_weather_cols = [col for col in weather_cols if col in weather_df.columns]
        live_df = static_df.merge(weather_df[available_weather_cols], on="region_key", how="left")
        pbar.set_postfix_str("정적+현재날씨 병합")
        pbar.update(1)

        live_df["주의기상상태_정규화"] = live_df["주의기상상태"].apply(normalize_weather_label)
        live_df["현재기상상태_정규화"] = live_df["current_weather"].apply(normalize_weather_label)
        live_df["현재시간대"] = now_band
        pbar.set_postfix_str("현재 조건 정규화")
        pbar.update(1)

        weather_scores = []
        weather_reasons = []
        time_scores = []
        time_reasons = []

        for row in tqdm(live_df.itertuples(index=False), total=len(live_df), desc="날씨/시간 가중치", leave=False, ncols=100):
            w_score, w_reason = weather_weight(
                getattr(row, "현재기상상태_정규화"),
                getattr(row, "주의기상상태_정규화"),
                getattr(row, "rain_1h_mm", 0),
                getattr(row, "wind_speed_ms", 0),
            )
            t_score, t_reason = time_weight(now_band, getattr(row, "주의시간대"))
            weather_scores.append(w_score)
            weather_reasons.append(w_reason)
            time_scores.append(t_score)
            time_reasons.append(t_reason)

        live_df["기상가중치"] = weather_scores
        live_df["기상가중치사유"] = weather_reasons
        live_df["시간가중치"] = time_scores
        live_df["시간가중치사유"] = time_reasons
        pbar.set_postfix_str("날씨/시간 가중치 계산 완료")
        pbar.update(1)

        incident_df = load_incident_df()
        incident_infos = []
        for row in tqdm(live_df.itertuples(index=False), total=len(live_df), desc="돌발상황 가중치", leave=False, ncols=100):
            incident_infos.append(nearest_incident_info(getattr(row, "위도", None), getattr(row, "경도", None), incident_df))
        incident_info_df = pd.DataFrame(incident_infos)
        if not incident_info_df.empty:
            live_df = pd.concat([live_df.reset_index(drop=True), incident_info_df.reset_index(drop=True)], axis=1)
        else:
            live_df["돌발상황가중치"] = 0
            live_df["돌발상황사유"] = "근접 돌발상황 없음"
            live_df["가까운돌발상황거리m"] = None
            live_df["가까운돌발상황유형"] = ""
            live_df["가까운돌발상황도로명"] = ""
            live_df["가까운돌발상황내용"] = ""
        pbar.set_postfix_str("돌발상황 가중치 계산 완료")
        pbar.update(1)

        live_df["실시간위험점수"] = (
            pd.to_numeric(live_df["정적위험점수"], errors="coerce").fillna(0)
            + pd.to_numeric(live_df["기상가중치"], errors="coerce").fillna(0)
            + pd.to_numeric(live_df["시간가중치"], errors="coerce").fillna(0)
            + pd.to_numeric(live_df["돌발상황가중치"], errors="coerce").fillna(0)
        ).clip(upper=100).round(2)

        live_df["실시간위험등급"] = live_df["실시간위험점수"].apply(classify_risk)
        live_df["실시간알림반경m"] = live_df["실시간위험점수"].apply(calc_alert_radius)
        live_df["위험변화점수"] = (live_df["실시간위험점수"] - pd.to_numeric(live_df["정적위험점수"], errors="coerce").fillna(0)).round(2)
        live_df["위험변화상태"] = live_df.apply(
            lambda row: classify_change(row["위험변화점수"], row["돌발상황가중치"], row["기상가중치"]), axis=1
        )
        live_df["위험변화사유"] = live_df.apply(build_change_reason, axis=1)
        pbar.set_postfix_str("실시간 점수/변화상태 생성")
        pbar.update(1)

        def make_warning(row: pd.Series) -> str:
            return (
                f"{row['사고지역위치명']}은(는) 현재 {row['실시간위험등급']} 위험구간입니다. "
                f"변화상태는 {row['위험변화상태']}이며, 현재 기상은 {row.get('current_weather', '')}, "
                f"현재 시간대는 {row['현재시간대']}입니다. {row.get('돌발상황사유', '')}"
            )

        live_df["실시간대표경고문구"] = live_df.apply(make_warning, axis=1)
        pbar.set_postfix_str("경고문구 생성")
        pbar.update(1)

        live_df["갱신시각KST"] = now_kst.strftime("%Y-%m-%d %H:%M:%S")
        live_df = live_df.sort_values(
            by=["실시간위험점수", "정적위험점수"], ascending=[False, False]
        ).reset_index(drop=True)
        pbar.set_postfix_str("정렬 완료")
        pbar.update(1)

        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        TABLE_DIR.mkdir(parents=True, exist_ok=True)
        live_df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")

        change_summary = (
            live_df.groupby("위험변화상태", as_index=False)
            .agg(구간수=("zone_id", "count"), 평균실시간위험점수=("실시간위험점수", "mean"), 평균변화점수=("위험변화점수", "mean"))
        )
        change_summary["평균실시간위험점수"] = change_summary["평균실시간위험점수"].round(2)
        change_summary["평균변화점수"] = change_summary["평균변화점수"].round(2)
        change_summary.to_csv(TABLE_DIR / "live_risk_change_summary.csv", index=False, encoding="utf-8-sig")
        pbar.set_postfix_str("CSV 저장 완료")
        pbar.update(1)

    print("\n=== update_live_risk 완료 ===")
    print("저장 위치:", OUTPUT_PATH)
    print("행 개수:", len(live_df))
    print("현재 시간대:", now_band)
    print("\n상위 5개 실시간 위험구간:")
    print(live_df[["zone_id", "사고지역위치명", "정적위험점수", "실시간위험점수", "실시간위험등급", "위험변화상태", "current_weather"]].head())

    return live_df


if __name__ == "__main__":
    update_live_risk()
