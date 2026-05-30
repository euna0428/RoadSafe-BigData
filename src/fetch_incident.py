from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
import json
import os
import xml.etree.ElementTree as ET

import pandas as pd
import requests
from dotenv import load_dotenv
from tqdm import tqdm
from zoneinfo import ZoneInfo


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "incident"
OUTPUT_PATH = RAW_DIR / "current_incident.csv"
KST = ZoneInfo("Asia/Seoul")

EVENT_API_URL = "https://openapi.its.go.kr:9443/eventInfo"

DEFAULT_COLUMNS = [
    "incident_id",
    "incident_type",
    "incident_detail_type",
    "road_type",
    "road_name",
    "road_no",
    "direction",
    "lanes_block_type",
    "lanes_blocked",
    "start_time",
    "end_time",
    "lat",
    "lon",
    "link_id",
    "message",
    "source_api",
    "api_status",
    "collected_at_kst",
]


def get_api_key() -> str:
    load_dotenv(PROJECT_ROOT / ".env")
    return (
        os.getenv("ITS_EVENT_API_KEY")
        or os.getenv("ITS_API_KEY")
        or os.getenv("MOLIT_EVENT_API_KEY")
        or ""
    ).strip()


def safe_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, float) and pd.isna(value):
        return default
    return str(value).strip()


def safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        result = float(value)
        if pd.isna(result):
            return None
        return result
    except Exception:
        return None


def parse_datetime_text(value: Any) -> str:
    text = safe_text(value)
    if not text:
        return ""
    for fmt in ("%Y%m%d%H%M%S", "%Y%m%d%H%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            continue
    return text


def find_first(data: dict[str, Any], *keys: str, default: Any = "") -> Any:
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    lowered = {str(k).lower(): v for k, v in data.items()}
    for key in keys:
        v = lowered.get(key.lower())
        if v not in (None, ""):
            return v
    return default


def flatten_json_items(data: Any) -> list[dict[str, Any]]:
    """ITS/공공데이터 응답 구조가 조금 달라도 item 리스트를 찾아낸다."""
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []

    candidate_keys = ("items", "item", "body", "data", "list", "event", "events")
    for key in candidate_keys:
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = flatten_json_items(value)
            if nested:
                return nested

    for value in data.values():
        nested = flatten_json_items(value)
        if nested:
            return nested
    return []


def parse_xml_items(text: str) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []

    items: list[dict[str, Any]] = []
    for element in root.iter():
        children = list(element)
        if not children:
            continue
        child_tags = {child.tag.split("}")[-1] for child in children}
        if {"coordX", "coordY"}.intersection(child_tags) or {"message", "roadName"}.intersection(child_tags):
            row = {child.tag.split("}")[-1]: safe_text(child.text) for child in children}
            if row:
                items.append(row)
    return items


def normalize_incident_row(raw: dict[str, Any], idx: int, collected_at: str) -> dict[str, Any]:
    lon = safe_float(find_first(raw, "coordX", "x", "lon", "longitude", "경도"))
    lat = safe_float(find_first(raw, "coordY", "y", "lat", "latitude", "위도"))
    start_time = parse_datetime_text(find_first(raw, "startDate", "start_time", "돌발일시"))
    end_time = parse_datetime_text(find_first(raw, "endDate", "end_time", "돌발종료일시"))
    incident_type = safe_text(find_first(raw, "eventType", "incident_type", "돌발구분"))
    road_name = safe_text(find_first(raw, "roadName", "road_name", "도로명"))
    link_id = safe_text(find_first(raw, "linkId", "link_id", "링크아이디"))

    incident_id_source = "_".join(part for part in [link_id, start_time, incident_type, road_name] if part)
    incident_id = incident_id_source if incident_id_source else f"INCIDENT_{idx:05d}"

    return {
        "incident_id": incident_id,
        "incident_type": incident_type,
        "incident_detail_type": safe_text(find_first(raw, "eventDetailType", "incident_detail_type", "돌발상세구분")),
        "road_type": safe_text(find_first(raw, "type", "road_type", "도로타입")),
        "road_name": road_name,
        "road_no": safe_text(find_first(raw, "roadNo", "road_no", "도로번호")),
        "direction": safe_text(find_first(raw, "roadDrcType", "direction", "방향")),
        "lanes_block_type": safe_text(find_first(raw, "lanesBlockType", "lanes_block_type", "통제유형")),
        "lanes_blocked": safe_text(find_first(raw, "lanesBlocked", "lanes_blocked", "차단차로")),
        "start_time": start_time,
        "end_time": end_time,
        "lat": lat,
        "lon": lon,
        "link_id": link_id,
        "message": safe_text(find_first(raw, "message", "msg", "돌발내용")),
        "source_api": "ITS_EVENT",
        "api_status": "OK",
        "collected_at_kst": collected_at,
    }


def empty_incident_frame(status: str, collected_at: str) -> pd.DataFrame:
    df = pd.DataFrame(columns=DEFAULT_COLUMNS)
    df.loc[0] = {
        "incident_id": "NO_INCIDENT_DATA",
        "incident_type": "",
        "incident_detail_type": "",
        "road_type": "",
        "road_name": "",
        "road_no": "",
        "direction": "",
        "lanes_block_type": "",
        "lanes_blocked": "",
        "start_time": "",
        "end_time": "",
        "lat": None,
        "lon": None,
        "link_id": "",
        "message": status,
        "source_api": "ITS_EVENT",
        "api_status": status,
        "collected_at_kst": collected_at,
    }
    return df


def request_incident_items(api_key: str, road_type: str = "all", event_type: str = "all") -> list[dict[str, Any]]:
    params = {
        "apiKey": api_key,
        "type": road_type,
        "eventType": event_type,
        "getType": "json",
    }
    response = requests.get(EVENT_API_URL, params=params, timeout=20)
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "").lower()
    if "json" in content_type or response.text.lstrip().startswith(("{", "[")):
        data = response.json()
        result_code = safe_text(find_first(data, "resultCode", "code", default="0"))
        result_msg = safe_text(find_first(data, "resultMsg", "message", default=""))
        if result_code not in ("", "0", "00", "SUCCESS"):
            raise RuntimeError(f"ITS 돌발상황 API 오류: {result_code} / {result_msg}")
        return flatten_json_items(data)

    return parse_xml_items(response.text)


def fetch_incident(road_type: str = "all", event_type: str = "all") -> pd.DataFrame:
    """국토교통부/ITS 돌발상황정보를 수집해 표준 CSV로 저장한다.

    API 키가 아직 없으면 파이프라인이 끊기지 않도록 스키마가 있는 빈 CSV를 만든다.
    실제 수집을 하려면 프로젝트 루트의 .env에 ITS_EVENT_API_KEY 값을 넣는다.
    """
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    collected_at = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    api_key = get_api_key()

    print("\n[fetch_incident] 시작")

    with tqdm(total=4, desc="돌발상황 수집", ncols=100) as pbar:
        if not api_key:
            df = empty_incident_frame("NO_API_KEY", collected_at)
            df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
            pbar.set_postfix_str("API 키 없음 - 빈 스키마 저장")
            pbar.update(4)
            print("\n[안내] ITS_EVENT_API_KEY가 없어 current_incident.csv를 빈 스키마로 생성했습니다.")
            print("저장 위치:", OUTPUT_PATH)
            return df

        pbar.set_postfix_str("API 키 확인")
        pbar.update(1)

        raw_items = request_incident_items(api_key, road_type=road_type, event_type=event_type)
        pbar.set_postfix_str(f"원천 {len(raw_items)}건 수신")
        pbar.update(1)

        rows = [normalize_incident_row(item, idx + 1, collected_at) for idx, item in enumerate(raw_items)]
        df = pd.DataFrame(rows, columns=DEFAULT_COLUMNS)
        if df.empty:
            df = empty_incident_frame("NO_ACTIVE_INCIDENT", collected_at)
        pbar.set_postfix_str("표준 컬럼 변환")
        pbar.update(1)

        df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
        pbar.set_postfix_str("CSV 저장 완료")
        pbar.update(1)

    print("\n=== fetch_incident 완료 ===")
    print("저장 위치:", OUTPUT_PATH)
    print("수집 행 개수:", len(df))
    if not df.empty:
        print(df[["incident_type", "road_name", "lat", "lon", "message", "api_status"]].head())
    return df


if __name__ == "__main__":
    fetch_incident()
