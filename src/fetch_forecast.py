from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple
import time

import pandas as pd
import requests
from dotenv import load_dotenv
from tqdm import tqdm
import os
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "forecast"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_PATH = RAW_DIR / "current_weather.csv"
KST = ZoneInfo("Asia/Seoul")

NCST_URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
FCST_URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtFcst"
DEFAULT_SLEEP_SECONDS = 2.0
REQUEST_RETRY_COUNT = 3
RETRY_BASE_DELAY_SECONDS = 1.5
UNKNOWN_WEATHER = "알수없음"


try:
    from src.config import SERVICE_KEY as CONFIG_SERVICE_KEY
except Exception:
    try:
        from config import SERVICE_KEY as CONFIG_SERVICE_KEY
    except Exception:
        CONFIG_SERVICE_KEY = "YOUR_API_KEY_HERE"



def latlon_to_grid(lat: float, lon: float) -> Tuple[int, int]:
    import math

    re = 6371.00877
    grid = 5.0
    slat1 = 30.0
    slat2 = 60.0
    olon = 126.0
    olat = 38.0
    xo = 43
    yo = 136

    degrad = math.pi / 180.0
    re = re / grid
    slat1 = slat1 * degrad
    slat2 = slat2 * degrad
    olon = olon * degrad
    olat = olat * degrad

    sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5)
    sf = (sf ** sn) * math.cos(slat1) / sn
    ro = math.tan(math.pi * 0.25 + olat * 0.5)
    ro = re * sf / (ro ** sn)

    ra = math.tan(math.pi * 0.25 + (lat) * degrad * 0.5)
    ra = re * sf / (ra ** sn)
    theta = lon * degrad - olon

    if theta > math.pi:
        theta -= 2.0 * math.pi
    if theta < -math.pi:
        theta += 2.0 * math.pi

    theta *= sn
    x = int(ra * math.sin(theta) + xo + 0.5)
    y = int(ro - ra * math.cos(theta) + yo + 0.5)

    return x, y


def get_service_key() -> str:
    load_dotenv(PROJECT_ROOT / ".env")
    service_key = (
        os.getenv("KMA_SERVICE_KEY")
        or os.getenv("SERVICE_KEY")
        or CONFIG_SERVICE_KEY
    )
    if not service_key or service_key == "YOUR_API_KEY_HERE":
        raise ValueError(
            "기상청 API 인증키가 없습니다. 프로젝트 루트의 .env 파일에 KMA_SERVICE_KEY=발급키 를 넣어 주세요."
        )
    return service_key


def extract_region_key(region_name: str) -> str:
    if pd.isna(region_name):
        return "기타"
    tokens = str(region_name).strip().split()
    return tokens[0] if tokens else "기타"


def get_latest_ncst_base(now_kst: datetime) -> Tuple[str, str]:
    candidate = now_kst.replace(minute=0, second=0, microsecond=0)
    if now_kst.minute < 45:
        candidate -= timedelta(hours=1)
    return candidate.strftime("%Y%m%d"), candidate.strftime("%H00")


def get_latest_fcst_base(now_kst: datetime) -> Tuple[str, str]:
    if now_kst.minute >= 45:
        candidate = now_kst.replace(minute=30, second=0, microsecond=0)
    else:
        candidate = (now_kst - timedelta(hours=1)).replace(minute=30, second=0, microsecond=0)
    return candidate.strftime("%Y%m%d"), candidate.strftime("%H%M")


def safe_float(value, default=None):
    try:
        return float(value)
    except Exception:
        return default


def request_items(url: str, params: Dict[str, str], timeout: int = 20, max_retries: int = REQUEST_RETRY_COUNT) -> List[dict]:
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()

            header = data.get("response", {}).get("header", {})
            result_code = header.get("resultCode")
            result_msg = header.get("resultMsg")
            if result_code != "00":
                raise RuntimeError(f"API 오류: {result_code} / {result_msg}")

            items = (
                data.get("response", {})
                .get("body", {})
                .get("items", {})
                .get("item", [])
            )
            return items
        except Exception as exc:
            last_error = exc
            if attempt >= max_retries - 1:
                break
            error_status = normalize_api_error(exc)
            if error_status in {"LIMITED_429", "TIMEOUT", "ERROR"}:
                time.sleep(RETRY_BASE_DELAY_SECONDS * (attempt + 1))
                continue
            break

    raise last_error or RuntimeError("API 요청 실패")


def choose_nearest_forecast_value(items: List[dict], category: str, now_kst: datetime) -> str | None:
    candidates = []
    for item in items:
        if item.get("category") != category:
            continue
        fcst_date = item.get("fcstDate")
        fcst_time = item.get("fcstTime")
        if not fcst_date or not fcst_time:
            continue
        try:
            dt = datetime.strptime(f"{fcst_date}{fcst_time}", "%Y%m%d%H%M").replace(tzinfo=KST)
            gap = abs((dt - now_kst).total_seconds())
            candidates.append((gap, item.get("fcstValue"), dt))
        except Exception:
            continue

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def map_now_weather(pty_value: str | None, sky_value: str | None) -> Tuple[str, str]:
    pty_map = {
        "0": "강수없음",
        "1": "비",
        "2": "비/눈",
        "3": "눈",
        "4": "소나기",
        "5": "비",
        "6": "비/눈",
        "7": "눈",
    }
    sky_map = {
        "1": "맑음",
        "3": "구름많음",
        "4": "흐림",
    }

    if pty_value is not None and str(pty_value) in pty_map and str(pty_value) != "0":
        label = pty_map[str(pty_value)]
        return label, label

    sky_label = sky_map.get(str(sky_value), "알수없음")
    return sky_label, sky_label


def fetch_one_region_weather(service_key: str, region_key: str, lat: float, lon: float, now_kst: datetime) -> dict:
    nx, ny = latlon_to_grid(lat, lon)
    ncst_base_date, ncst_base_time = get_latest_ncst_base(now_kst)
    fcst_base_date, fcst_base_time = get_latest_fcst_base(now_kst)

    ncst_params = {
        "serviceKey": service_key,
        "pageNo": "1",
        "numOfRows": "1000",
        "dataType": "JSON",
        "base_date": ncst_base_date,
        "base_time": ncst_base_time,
        "nx": str(nx),
        "ny": str(ny),
    }
    fcst_params = {
        "serviceKey": service_key,
        "pageNo": "1",
        "numOfRows": "1000",
        "dataType": "JSON",
        "base_date": fcst_base_date,
        "base_time": fcst_base_time,
        "nx": str(nx),
        "ny": str(ny),
    }

    ncst_items = request_items(NCST_URL, ncst_params)
    fcst_items = request_items(FCST_URL, fcst_params)

    ncst_dict = {item.get("category"): item.get("obsrValue") for item in ncst_items}
    sky_value = choose_nearest_forecast_value(fcst_items, "SKY", now_kst)

    current_weather_raw, current_weather = map_now_weather(ncst_dict.get("PTY"), sky_value)

    obs_time = f"{ncst_base_date} {ncst_base_time}"
    return {
        "region_key": region_key,
        "query_lat": round(float(lat), 6),
        "query_lon": round(float(lon), 6),
        "nx": nx,
        "ny": ny,
        "base_date_ncst": ncst_base_date,
        "base_time_ncst": ncst_base_time,
        "base_date_fcst": fcst_base_date,
        "base_time_fcst": fcst_base_time,
        "obs_time": obs_time,
        "current_weather_raw": current_weather_raw,
        "current_weather": current_weather,
        "current_temp_c": safe_float(ncst_dict.get("T1H")),
        "humidity_pct": safe_float(ncst_dict.get("REH")),
        "rain_1h_mm": safe_float(ncst_dict.get("RN1"), 0.0),
        "wind_speed_ms": safe_float(ncst_dict.get("WSD")),
        "api_status": "OK",
        "cache_status": "LIVE",
        "cache_collected_at_kst": None,
        "last_error_status": "",
    }


def normalize_api_error(exc: Exception) -> str:
    text = str(exc)
    if "429" in text or "Too Many Requests" in text:
        return "LIMITED_429"
    if "SERVICE_KEY" in text or "인증" in text or "Unauthorized" in text or "401" in text:
        return "AUTH_ERROR"
    if "timeout" in text.lower():
        return "TIMEOUT"
    return "ERROR"


def is_usable_weather(value) -> bool:
    if pd.isna(value):
        return False
    text = str(value).strip()
    return bool(text) and text != UNKNOWN_WEATHER


def load_previous_weather_cache() -> dict[str, dict]:
    if not OUTPUT_PATH.exists():
        return {}

    try:
        previous_df = pd.read_csv(OUTPUT_PATH, encoding="utf-8-sig")
    except Exception:
        return {}

    if previous_df.empty or "region_key" not in previous_df.columns:
        return {}

    previous_df.columns = previous_df.columns.astype(str).str.strip()
    cache: dict[str, dict] = {}
    for record in previous_df.to_dict("records"):
        region_key = str(record.get("region_key", "")).strip()
        if not region_key:
            continue
        if not is_usable_weather(record.get("current_weather")):
            continue
        cache[region_key] = record
    return cache


def make_unknown_weather_record(region_key: str, lat: float, lon: float, status: str) -> dict:
    nx, ny = latlon_to_grid(lat, lon)
    return {
        "region_key": region_key,
        "query_lat": round(float(lat), 6),
        "query_lon": round(float(lon), 6),
        "nx": nx,
        "ny": ny,
        "base_date_ncst": None,
        "base_time_ncst": None,
        "base_date_fcst": None,
        "base_time_fcst": None,
        "obs_time": None,
        "current_weather_raw": UNKNOWN_WEATHER,
        "current_weather": UNKNOWN_WEATHER,
        "current_temp_c": None,
        "humidity_pct": None,
        "rain_1h_mm": None,
        "wind_speed_ms": None,
        "api_status": status,
        "cache_status": "MISS",
        "cache_collected_at_kst": None,
        "last_error_status": status if status != "OK" else "",
    }


def make_cached_weather_record(region_key: str, lat: float, lon: float, error_status: str, previous_cache: dict[str, dict]) -> dict:
    cached = previous_cache.get(region_key)
    if not cached:
        return make_unknown_weather_record(region_key, lat, lon, error_status)

    record = dict(cached)
    nx, ny = latlon_to_grid(lat, lon)
    record.update({
        "region_key": region_key,
        "query_lat": round(float(lat), 6),
        "query_lon": round(float(lon), 6),
        "nx": record.get("nx") if pd.notna(record.get("nx")) else nx,
        "ny": record.get("ny") if pd.notna(record.get("ny")) else ny,
        "api_status": f"CACHED_{error_status}",
        "cache_status": "HIT",
        "cache_collected_at_kst": record.get("collected_at_kst"),
        "last_error_status": error_status,
    })
    return record




def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    import math
    r = 6371000.0
    p1 = math.radians(float(lat1))
    p2 = math.radians(float(lat2))
    dp = math.radians(float(lat2) - float(lat1))
    dl = math.radians(float(lon2) - float(lon1))
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def apply_nearest_weather_fallback(result_df: pd.DataFrame) -> pd.DataFrame:
    if result_df.empty or "current_weather" not in result_df.columns:
        return result_df

    df = result_df.copy()
    for column in ["cache_status", "cache_collected_at_kst", "last_error_status", "fallback_region_key", "fallback_distance_m", "fallback_note"]:
        if column not in df.columns:
            df[column] = ""

    usable_mask = df["current_weather"].apply(is_usable_weather)
    usable_df = df[usable_mask].copy()
    if usable_df.empty:
        return df

    weather_columns = [
        "current_weather_raw", "current_weather", "current_temp_c", "humidity_pct", "rain_1h_mm", "wind_speed_ms",
        "base_date_ncst", "base_time_ncst", "base_date_fcst", "base_time_fcst", "obs_time"
    ]

    for idx, row in df[~usable_mask].iterrows():
        lat = safe_float(row.get("query_lat"))
        lon = safe_float(row.get("query_lon"))
        if lat is None or lon is None:
            continue

        best_index = None
        best_distance = None
        for candidate_idx, candidate in usable_df.iterrows():
            candidate_lat = safe_float(candidate.get("query_lat"))
            candidate_lon = safe_float(candidate.get("query_lon"))
            if candidate_lat is None or candidate_lon is None:
                continue
            dist = distance_m(lat, lon, candidate_lat, candidate_lon)
            if best_distance is None or dist < best_distance:
                best_distance = dist
                best_index = candidate_idx

        if best_index is None:
            continue

        source = usable_df.loc[best_index]
        for column in weather_columns:
            if column in df.columns and column in source.index:
                df.at[idx, column] = source[column]

        original_status = str(row.get("api_status", "ERROR") or "ERROR")
        df.at[idx, "api_status"] = "FALLBACK_NEAREST_REGION"
        df.at[idx, "cache_status"] = "NEAREST_FALLBACK"
        df.at[idx, "last_error_status"] = original_status
        df.at[idx, "fallback_region_key"] = source.get("region_key", "")
        df.at[idx, "fallback_distance_m"] = round(float(best_distance or 0), 1)
        df.at[idx, "fallback_note"] = f"{source.get('region_key', '')} 지역 기상값 대체 적용"

    return df

def fetch_forecast(sleep_seconds: float = DEFAULT_SLEEP_SECONDS) -> pd.DataFrame:
    input_path = PROCESSED_DIR / "final_risk_table.csv"
    if not input_path.exists():
        raise FileNotFoundError(
            f"실시간용 기준 테이블이 없습니다: {input_path}\nmain.py를 먼저 1회 실행해서 final_risk_table.csv를 생성해 주세요."
        )

    service_key = get_service_key()
    now_kst = datetime.now(KST)
    previous_cache = load_previous_weather_cache()

    print("\n[fetch_forecast] 시작")

    with tqdm(total=6, desc="현재 날씨 수집", ncols=100) as pbar:
        base_df = pd.read_csv(input_path, encoding="utf-8-sig")
        base_df.columns = base_df.columns.str.strip()
        pbar.set_postfix_str("기준 테이블 읽기 완료")
        pbar.update(1)

        base_df = base_df.dropna(subset=["위도", "경도"]).copy()
        base_df["region_key"] = base_df["사고다발지역시도시군구"].apply(extract_region_key)
        region_df = (
            base_df.groupby("region_key", as_index=False)
            .agg(query_lat=("위도", "median"), query_lon=("경도", "median"))
            .sort_values("region_key")
            .reset_index(drop=True)
        )
        pbar.set_postfix_str("대표 지역 좌표 생성")
        pbar.update(1)

        result_rows: List[dict] = []
        pbar.set_postfix_str(f"{len(region_df)}개 지역 API 준비")
        pbar.update(1)

        for row in tqdm(region_df.itertuples(index=False), total=len(region_df), desc="지역별 API 호출", leave=False, ncols=100):
            try:
                record = fetch_one_region_weather(
                    service_key=service_key,
                    region_key=row.region_key,
                    lat=float(row.query_lat),
                    lon=float(row.query_lon),
                    now_kst=now_kst,
                )
            except Exception as exc:
                error_status = normalize_api_error(exc)
                record = make_cached_weather_record(
                    region_key=row.region_key,
                    lat=float(row.query_lat),
                    lon=float(row.query_lon),
                    error_status=error_status,
                    previous_cache=previous_cache,
                )
            result_rows.append(record)
            time.sleep(sleep_seconds)

        pbar.set_postfix_str("API 수집 완료")
        pbar.update(1)

        result_df = pd.DataFrame(result_rows)
        result_df["collected_at_kst"] = now_kst.strftime("%Y-%m-%d %H:%M:%S")
        result_df = apply_nearest_weather_fallback(result_df)
        result_df = result_df.sort_values("region_key").reset_index(drop=True)
        pbar.set_postfix_str("결과 테이블 정리")
        pbar.update(1)

        RAW_DIR.mkdir(parents=True, exist_ok=True)
        result_df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
        pbar.set_postfix_str("CSV 저장 완료")
        pbar.update(1)

    print("\n=== fetch_forecast 완료 ===")
    print("수집 시각(KST):", now_kst.strftime("%Y-%m-%d %H:%M:%S"))
    print("저장 위치:", OUTPUT_PATH)
    status_series = result_df["api_status"].astype(str)
    live_count = (status_series == "OK").sum()
    cached_count = status_series.str.startswith("CACHED_").sum()
    fallback_count = (status_series == "FALLBACK_NEAREST_REGION").sum()
    error_count = ((status_series != "OK") & ~status_series.str.startswith("CACHED_") & (status_series != "FALLBACK_NEAREST_REGION")).sum()
    unknown_count = (result_df["current_weather"] == UNKNOWN_WEATHER).sum()
    print("수집 지역 수:", len(result_df))
    print("실시간 정상 응답 수:", live_count)
    print("기존 정상값 재사용 수:", cached_count)
    print("인접 지역 기상값 대체 수:", fallback_count)
    print("날씨 미확인 수:", unknown_count)
    print("캐시/대체 없이 실패한 수:", error_count)

    return result_df


if __name__ == "__main__":
    fetch_forecast()
