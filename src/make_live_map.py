from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import math
import shutil

import pandas as pd
from tqdm import tqdm

try:
    from src.make_map import (
        COLOR_BY_GRADE,
        DEFAULT_CENTER,
        DEFAULT_LEVEL,
        OUTPUT_ASSET_DIR,
        OUTPUT_SCRIPT_PATH,
        OUTPUT_STYLE_PATH,
        STATIC_CSS_PATH,
        STATIC_JS_PATH,
        TEMPLATE_PATH,
        build_kakao_sdk_url,
        clean_region_name,
        format_score,
        normalize_grade,
        safe_float,
        safe_text,
        split_region,
        KAKAO_JS_KEY,
        KAKAO_KEY_MODE,
    )
except Exception:  # 직접 실행 대비
    from make_map import (  # type: ignore
        COLOR_BY_GRADE,
        DEFAULT_CENTER,
        DEFAULT_LEVEL,
        OUTPUT_ASSET_DIR,
        OUTPUT_SCRIPT_PATH,
        OUTPUT_STYLE_PATH,
        STATIC_CSS_PATH,
        STATIC_JS_PATH,
        TEMPLATE_PATH,
        build_kakao_sdk_url,
        clean_region_name,
        format_score,
        normalize_grade,
        safe_float,
        safe_text,
        split_region,
        KAKAO_JS_KEY,
        KAKAO_KEY_MODE,
    )


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_MAP_DIR = PROJECT_ROOT / "outputs" / "maps"
INPUT_PATH = PROCESSED_DIR / "live_risk_table.csv"
OUTPUT_PATH = OUTPUT_MAP_DIR / "live_risk_map.html"
DEFAULT_TOP_N = None


def json_safe(value: Any) -> Any:
    """JSON.parse가 처리할 수 없는 NaN/Infinity 값을 null로 변환합니다."""
    if isinstance(value, dict):
        return {key: json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if pd.isna(value):
        return None
    return value


def export_web_assets() -> None:
    OUTPUT_ASSET_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(STATIC_CSS_PATH, OUTPUT_STYLE_PATH)
    shutil.copyfile(STATIC_JS_PATH, OUTPUT_SCRIPT_PATH)


def prepare_live_map_data(df: pd.DataFrame) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    for row in tqdm(
        df.itertuples(index=False),
        total=len(df),
        desc="실시간 지도 데이터 변환",
        leave=False,
        ncols=100,
    ):
        lat = safe_float(getattr(row, "위도", None))
        lon = safe_float(getattr(row, "경도", None))
        if lat is None or lon is None:
            continue

        raw_region = safe_text(getattr(row, "사고다발지역시도시군구", ""))
        sido, sigungu = split_region(raw_region)
        live_grade = normalize_grade(getattr(row, "실시간위험등급", getattr(row, "위험등급", "")))

        records.append(
            {
                "mode": "live",
                "zone_id": safe_text(getattr(row, "zone_id", "")),
                "region": clean_region_name(raw_region),
                "sido": sido,
                "sigungu": sigungu,
                "location_name": safe_text(getattr(row, "사고지역위치명", "")),
                "lat": lat,
                "lon": lon,
                "score": format_score(getattr(row, "실시간위험점수", 0)),
                "grade": live_grade,
                "radius_m": safe_float(getattr(row, "실시간알림반경m", getattr(row, "알림반경m", 0))) or 0,
                "weather": safe_text(getattr(row, "current_weather", "")),
                "time_band": safe_text(getattr(row, "현재시간대", "")),
                "warning": safe_text(getattr(row, "실시간대표경고문구", "")),
                "attention_weather": safe_text(getattr(row, "주의기상상태", "")),
                "attention_time_band": safe_text(getattr(row, "주의시간대", "")),
                "current_weather_raw": safe_text(getattr(row, "current_weather_raw", "")),
                "current_temp_c": format_score(getattr(row, "current_temp_c", "")),
                "humidity_pct": format_score(getattr(row, "humidity_pct", "")),
                "rain_1h_mm": format_score(getattr(row, "rain_1h_mm", "")),
                "wind_speed_ms": format_score(getattr(row, "wind_speed_ms", "")),
                "obs_time": safe_text(getattr(row, "obs_time", "")),
                "collected_at_kst": safe_text(getattr(row, "collected_at_kst", "")),
                "weather_api_status": safe_text(getattr(row, "api_status", "")),
                "weather_cache_status": safe_text(getattr(row, "cache_status", "")),
                "weather_last_error_status": safe_text(getattr(row, "last_error_status", "")),
                "weather_fallback_region": safe_text(getattr(row, "fallback_region_key", "")),
                "weather_fallback_distance_m": format_score(getattr(row, "fallback_distance_m", "")),
                "weather_fallback_note": safe_text(getattr(row, "fallback_note", "")),
                "static_score": format_score(getattr(row, "정적위험점수", 0)),
                "static_grade": normalize_grade(getattr(row, "위험등급", "")),
                "change_score": format_score(getattr(row, "위험변화점수", 0)),
                "change_status": safe_text(getattr(row, "위험변화상태", "")),
                "change_reason": safe_text(getattr(row, "위험변화사유", "")),
                "weather_weight": format_score(getattr(row, "기상가중치", 0)),
                "weather_weight_reason": safe_text(getattr(row, "기상가중치사유", "")),
                "time_weight": format_score(getattr(row, "시간가중치", 0)),
                "time_weight_reason": safe_text(getattr(row, "시간가중치사유", "")),
                "incident_weight": format_score(getattr(row, "돌발상황가중치", "")),
                "incident_reason": safe_text(getattr(row, "돌발상황사유", "")),
                "nearest_incident_distance_m": format_score(getattr(row, "가까운돌발상황거리m", "")),
                "nearest_incident_type": safe_text(getattr(row, "가까운돌발상황유형", "")),
                "nearest_incident_road": safe_text(getattr(row, "가까운돌발상황도로명", "")),
                "nearest_incident_message": safe_text(getattr(row, "가까운돌발상황내용", "")),
                "updated_at": safe_text(getattr(row, "갱신시각KST", "")),
                "accident_count": format_score(getattr(row, "사고건수합", "")),
                "casualty_count": format_score(getattr(row, "사상자수합", "")),
                "death_count": format_score(getattr(row, "사망자수합", "")),
                "serious_injury_count": format_score(getattr(row, "중상자수합", "")),
                "minor_injury_count": format_score(getattr(row, "경상자수합", "")),
                "reported_injury_count": format_score(getattr(row, "부상신고자수합", "")),
                "raw_avg_score": format_score(getattr(row, "평균위험점수", "")),
                "raw_max_score": format_score(getattr(row, "최대위험점수", "")),
                "max_normalized_score": format_score(getattr(row, "최대정규화위험점수", "")),
            }
        )

    return records


def build_live_map_config(risk_data: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "mapMode": "live",
        "pageTitle": "실시간 위험도 지도",
        "pageDescription": "과거 사고 위험도에 현재 날씨와 현재 시간대를 결합해 위험도 변화를 확인합니다.",
        "pageSubDescription": "위험등급과 지역을 선택한 뒤 지도를 불러와 주세요.",
        "riskData": risk_data,
        "colorByGrade": COLOR_BY_GRADE,
        "kakaoKeyExists": bool(KAKAO_JS_KEY),
        "kakaoKeyMode": KAKAO_KEY_MODE,
        "kakaoSdkUrl": build_kakao_sdk_url(KAKAO_JS_KEY),
        "defaultCenter": DEFAULT_CENTER,
        "defaultLevel": DEFAULT_LEVEL,
        "allowedOrigins": ["http://127.0.0.1:8000", "http://localhost:8000"],
    }


def build_live_map_html(risk_data: list[dict[str, Any]]) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    safe_config = json_safe(build_live_map_config(risk_data))
    app_config_json = json.dumps(safe_config, ensure_ascii=False, allow_nan=False)
    return template.format(
        style_href="/outputs/maps/assets/risk_map.css",
        script_href="/outputs/maps/assets/risk_map.js",
        app_config_json=app_config_json,
        very_high_color=COLOR_BY_GRADE["매우높음"],
        high_color=COLOR_BY_GRADE["높음"],
        medium_color=COLOR_BY_GRADE["보통"],
        low_color=COLOR_BY_GRADE["낮음"],
    )


def validate_required_columns(df: pd.DataFrame) -> None:
    required_columns = [
        "사고다발지역시도시군구",
        "사고지역위치명",
        "위도",
        "경도",
        "정적위험점수",
        "실시간위험점수",
        "실시간위험등급",
        "실시간알림반경m",
        "현재시간대",
        "실시간대표경고문구",
    ]
    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise ValueError("live_risk_table.csv 에 필요한 컬럼이 없습니다: " + ", ".join(missing))


def make_live_risk_map(top_n: int | None = DEFAULT_TOP_N) -> pd.DataFrame:
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            f"실시간 위험 테이블이 없습니다: {INPUT_PATH}\nupdate_live_risk.py를 먼저 실행해 주세요."
        )

    print("\n[make_live_risk_map] 시작")

    with tqdm(total=7, desc="카카오 실시간 위험지도 생성", ncols=100) as pbar:
        df = pd.read_csv(INPUT_PATH, encoding="utf-8-sig")
        df.columns = df.columns.str.strip()
        pbar.set_postfix_str("CSV 읽기 완료")
        pbar.update(1)

        validate_required_columns(df)
        df = df.dropna(subset=["위도", "경도"]).copy()
        df["사고다발지역시도시군구"] = df["사고다발지역시도시군구"].apply(clean_region_name)
        df["정적위험점수"] = df["정적위험점수"].apply(format_score)
        df["실시간위험점수"] = df["실시간위험점수"].apply(format_score)
        df = df.sort_values(by=["실시간위험점수", "정적위험점수"], ascending=[False, False]).reset_index(drop=True)
        pbar.set_postfix_str("정렬/정리 완료")
        pbar.update(1)

        if top_n is not None:
            df = df.head(top_n).copy()
        pbar.set_postfix_str(f"지도 표시 대상 {len(df)}개")
        pbar.update(1)

        risk_data = prepare_live_map_data(df)
        pbar.set_postfix_str("지도 데이터 변환 완료")
        pbar.update(1)

        export_web_assets()
        pbar.set_postfix_str("정적 자산 복사 완료")
        pbar.update(1)

        html = build_live_map_html(risk_data)
        OUTPUT_MAP_DIR.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(html, encoding="utf-8")
        pbar.set_postfix_str("HTML 저장 완료")
        pbar.update(1)

        result_df = pd.DataFrame(risk_data)
        pbar.set_postfix_str("완료")
        pbar.update(1)

    print("\n=== make_live_risk_map 완료 ===")
    print("저장 위치:", OUTPUT_PATH)
    print("표시 구간 수:", len(result_df))
    print(f"카카오 키 적용 방식: {KAKAO_KEY_MODE}")
    print("\n실시간 위험등급 분포:")
    print(result_df["grade"].value_counts() if not result_df.empty else "표시 데이터 없음")

    return result_df


if __name__ == "__main__":
    make_live_risk_map()
