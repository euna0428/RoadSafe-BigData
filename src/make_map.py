from __future__ import annotations

from pathlib import Path
import json
import os
import shutil
from typing import Any
from dotenv import load_dotenv
from urllib.parse import urlencode

import pandas as pd
from tqdm import tqdm


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_MAP_DIR = PROJECT_ROOT / "outputs" / "maps"
WEB_DIR = PROJECT_ROOT / "src" / "web"
TEMPLATE_PATH = WEB_DIR / "templates" / "risk_map_template.html"
STATIC_CSS_PATH = WEB_DIR / "static" / "css" / "risk_map.css"
STATIC_JS_PATH = WEB_DIR / "static" / "js" / "risk_map.js"
OUTPUT_ASSET_DIR = OUTPUT_MAP_DIR / "assets"
OUTPUT_STYLE_PATH = OUTPUT_ASSET_DIR / "risk_map.css"
OUTPUT_SCRIPT_PATH = OUTPUT_ASSET_DIR / "risk_map.js"

load_dotenv(PROJECT_ROOT / ".env")

KAKAO_JS_KEY = os.getenv("KAKAO_JS_KEY", "").strip()
KAKAO_KEY_MODE = "ENV" if KAKAO_JS_KEY else "MISSING"

COLOR_BY_GRADE = {
    "매우높음": "#d73027",
    "높음": "#fc8d59",
    "보통": "#fee08b",
    "낮음": "#1a9850",
}

DEFAULT_CENTER = {"lat": 36.35, "lon": 127.95}
DEFAULT_LEVEL = 13


def format_score(score: Any) -> Any:
    try:
        return round(float(score), 2)
    except Exception:
        return score


def clean_region_name(region_name: Any) -> str:
    if pd.isna(region_name):
        return ""
    return str(region_name).strip().rstrip("0123456789")


def split_region(region_name: str) -> tuple[str, str]:
    clean_name = clean_region_name(region_name)
    if not clean_name:
        return "", ""

    parts = clean_name.split()
    if len(parts) == 1:
        return parts[0], "전체"
    return parts[0], " ".join(parts[1:])


def safe_float(value: Any) -> float | None:
    try:
        result = float(value)
        if pd.isna(result):
            return None
        return result
    except Exception:
        return None


def normalize_grade(value: Any) -> str:
    text = "" if pd.isna(value) else str(value).strip()
    return text if text in COLOR_BY_GRADE else "보통"


def safe_text(value: Any, default: str = "") -> str:
    if pd.isna(value):
        return default
    return str(value).strip()


def build_kakao_sdk_url(js_key: str) -> str:
    query = urlencode({
        "appkey": js_key,
        "autoload": "false",
        "libraries": "services",
    })
    return f"https://dapi.kakao.com/v2/maps/sdk.js?{query}"


def prepare_risk_map_data(df: pd.DataFrame) -> list[dict]:
    records: list[dict] = []

    for row in tqdm(
        df.itertuples(index=False),
        total=len(df),
        desc="지도 데이터 변환",
        leave=False,
        ncols=100,
    ):
        lat = safe_float(getattr(row, "위도", None))
        lon = safe_float(getattr(row, "경도", None))

        if lat is None or lon is None:
            continue

        raw_region = safe_text(getattr(row, "사고다발지역시도시군구", ""))
        sido, sigungu = split_region(raw_region)

        records.append(
            {
                "zone_id": safe_text(getattr(row, "zone_id", "")),
                "region": clean_region_name(raw_region),
                "sido": sido,
                "sigungu": sigungu,
                "location_name": safe_text(getattr(row, "사고지역위치명", "")),
                "lat": lat,
                "lon": lon,
                "score": format_score(getattr(row, "정적위험점수", 0)),
                "grade": normalize_grade(getattr(row, "위험등급", "")),
                "radius_m": safe_float(getattr(row, "알림반경m", 0)) or 0,
                "weather": safe_text(getattr(row, "주의기상상태", "")),
                "time_band": safe_text(getattr(row, "주의시간대", "")),
                "warning": safe_text(getattr(row, "대표경고문구", "")),
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


def validate_required_columns(df: pd.DataFrame) -> None:
    required_columns = [
        "사고다발지역시도시군구",
        "사고지역위치명",
        "위도",
        "경도",
        "정적위험점수",
        "위험등급",
        "알림반경m",
        "주의기상상태",
        "주의시간대",
        "대표경고문구",
    ]

    missing = [column for column in required_columns if column not in df.columns]
    if missing:
        raise ValueError(
            "final_risk_table.csv 에 필요한 컬럼이 없습니다: " + ", ".join(missing)
        )


def read_text_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"필수 파일이 없습니다: {path}")
    return path.read_text(encoding="utf-8")


def export_web_assets() -> None:
    OUTPUT_ASSET_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(STATIC_CSS_PATH, OUTPUT_STYLE_PATH)
    shutil.copyfile(STATIC_JS_PATH, OUTPUT_SCRIPT_PATH)


def build_map_config(risk_data: list[dict]) -> dict[str, Any]:
    allowed_origins = [
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ]
    return {
        "riskData": risk_data,
        "colorByGrade": COLOR_BY_GRADE,
        "kakaoKeyExists": bool(KAKAO_JS_KEY),
        "kakaoKeyMode": KAKAO_KEY_MODE,
        "kakaoSdkUrl": build_kakao_sdk_url(KAKAO_JS_KEY),
        "defaultCenter": DEFAULT_CENTER,
        "defaultLevel": DEFAULT_LEVEL,
        "allowedOrigins": allowed_origins,
    }


def build_map_html(risk_data: list[dict]) -> str:
    template = read_text_file(TEMPLATE_PATH)
    app_config_json = json.dumps(build_map_config(risk_data), ensure_ascii=False)
    return template.format(
        style_href="/outputs/maps/assets/risk_map.css",
        script_href="/outputs/maps/assets/risk_map.js",
        app_config_json=app_config_json,
        very_high_color=COLOR_BY_GRADE["매우높음"],
        high_color=COLOR_BY_GRADE["높음"],
        medium_color=COLOR_BY_GRADE["보통"],
        low_color=COLOR_BY_GRADE["낮음"],
    )


def make_risk_map() -> pd.DataFrame:
    input_path = PROCESSED_DIR / "final_risk_table.csv"
    output_path = OUTPUT_MAP_DIR / "risk_map.html"

    print("\n[make_risk_map] 시작")

    if not input_path.exists():
        raise FileNotFoundError(f"입력 파일이 없습니다: {input_path}")

    with tqdm(total=7, desc="위험구간 지도 생성", ncols=100) as pbar:
        df = pd.read_csv(input_path, encoding="utf-8-sig")
        df.columns = df.columns.str.strip()
        pbar.set_postfix_str("CSV 읽기 완료")
        pbar.update(1)

        validate_required_columns(df)
        pbar.set_postfix_str("필수 컬럼 검사 완료")
        pbar.update(1)

        df["사고다발지역시도시군구"] = df["사고다발지역시도시군구"].apply(clean_region_name)
        df["정적위험점수"] = df["정적위험점수"].apply(format_score)
        df = df.dropna(subset=["위도", "경도"]).copy()
        pbar.set_postfix_str("데이터 정리 완료")
        pbar.update(1)

        risk_data = prepare_risk_map_data(df)
        pbar.set_postfix_str("지도 데이터 변환 완료")
        pbar.update(1)

        export_web_assets()
        pbar.set_postfix_str("정적 자산 분리 완료")
        pbar.update(1)

        html = build_map_html(risk_data)
        pbar.set_postfix_str("HTML 생성 완료")
        pbar.update(1)

        OUTPUT_MAP_DIR.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")
        pbar.set_postfix_str("HTML 저장 완료")
        pbar.update(1)

    result_df = pd.DataFrame(risk_data)

    print("\n=== make_risk_map 완료 ===")
    print("지도 저장 위치:", output_path)
    print("CSS 저장 위치:", OUTPUT_STYLE_PATH)
    print("JS 저장 위치:", OUTPUT_SCRIPT_PATH)
    print("총 표시 구간 수:", len(result_df))
    print(f"카카오 키 적용 방식: {KAKAO_KEY_MODE}")
    print(f"카카오 키 포함 여부: {'예' if bool(KAKAO_JS_KEY) else '아니오'}")
    print("SDK URL:", build_kakao_sdk_url(KAKAO_JS_KEY) if KAKAO_JS_KEY else "-")

    print("\n위험등급 분포:")
    if not result_df.empty and "grade" in result_df.columns:
        print(result_df["grade"].value_counts())
    else:
        print("표시할 데이터가 없습니다.")

    if not KAKAO_JS_KEY:
        print("\n[경고] 카카오 JavaScript 키가 비어 있습니다.")
        print("risk_map.html 은 생성되지만 실제 지도는 표시되지 않습니다.")
    else:
        print("\n[안내] 현재는 JavaScript 키를 사용합니다.")
        print("[안내] 브라우저에서 지도가 뜨지 않으면 F12 → Network → sdk.js 상태코드를 확인해 주세요.")

    return result_df


if __name__ == "__main__":
    make_risk_map()
