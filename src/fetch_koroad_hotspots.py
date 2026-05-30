from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
import math
import os
import time
import xml.etree.ElementTree as ET

import pandas as pd
import requests
from dotenv import load_dotenv
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXTRA_DIR = PROJECT_ROOT / "data" / "raw" / "accident_extra"
FREQUENTZONE_OUTPUT = EXTRA_DIR / "koroad_frequentzone_lg.csv"
VIOLATION_OUTPUT = EXTRA_DIR / "koroad_frequentzone_lgr_violt.csv"
COMBINED_OUTPUT = PROJECT_ROOT / "data" / "raw" / "koroad_api" / "koroad_api_accident_extra.csv"

FREQUENTZONE_URL = "https://apis.data.go.kr/B552061/frequentzoneLg/getRestFrequentzoneLg"
VIOLATION_URL = "https://apis.data.go.kr/B552061/frequentzoneLgrViolt/getRestFrequentzoneLgrViolt"

BASE_COLUMNS = [
    "사고지역관리번호",
    "사고연도",
    "사고유형구분",
    "위치코드",
    "사고다발지역시도시군구",
    "사고지역위치명",
    "사고건수",
    "사상자수",
    "사망자수",
    "중상자수",
    "경상자수",
    "부상신고자수",
    "위도",
    "경도",
    "사고다발지역폴리곤정보",
    "데이터기준일자",
    "제공기관코드",
    "제공기관명",
    "원천API",
    "API연도코드",
]

REGION_CODES = [
    ("11", "680", "서울특별시", "강남구"), ("11", "740", "서울특별시", "강동구"), ("11", "305", "서울특별시", "강북구"), ("11", "500", "서울특별시", "강서구"),
    ("11", "620", "서울특별시", "관악구"), ("11", "215", "서울특별시", "광진구"), ("11", "530", "서울특별시", "구로구"), ("11", "545", "서울특별시", "금천구"),
    ("11", "350", "서울특별시", "노원구"), ("11", "320", "서울특별시", "도봉구"), ("11", "230", "서울특별시", "동대문구"), ("11", "590", "서울특별시", "동작구"),
    ("11", "440", "서울특별시", "마포구"), ("11", "410", "서울특별시", "서대문구"), ("11", "650", "서울특별시", "서초구"), ("11", "200", "서울특별시", "성동구"),
    ("11", "290", "서울특별시", "성북구"), ("11", "710", "서울특별시", "송파구"), ("11", "470", "서울특별시", "양천구"), ("11", "560", "서울특별시", "영등포구"),
    ("11", "170", "서울특별시", "용산구"), ("11", "380", "서울특별시", "은평구"), ("11", "110", "서울특별시", "종로구"), ("11", "140", "서울특별시", "중구"), ("11", "260", "서울특별시", "중랑구"),
    ("26", "440", "부산광역시", "강서구"), ("26", "410", "부산광역시", "금정구"), ("26", "710", "부산광역시", "기장군"), ("26", "290", "부산광역시", "남구"),
    ("26", "170", "부산광역시", "동구"), ("26", "260", "부산광역시", "동래구"), ("26", "230", "부산광역시", "부산진구"), ("26", "320", "부산광역시", "북구"),
    ("26", "530", "부산광역시", "사상구"), ("26", "380", "부산광역시", "사하구"), ("26", "140", "부산광역시", "서구"), ("26", "500", "부산광역시", "수영구"),
    ("26", "470", "부산광역시", "연제구"), ("26", "200", "부산광역시", "영도구"), ("26", "110", "부산광역시", "중구"), ("26", "350", "부산광역시", "해운대구"),
    ("27", "200", "대구광역시", "남구"), ("27", "290", "대구광역시", "달서구"), ("27", "710", "대구광역시", "달성군"), ("27", "140", "대구광역시", "동구"),
    ("27", "230", "대구광역시", "북구"), ("27", "170", "대구광역시", "서구"), ("27", "260", "대구광역시", "수성구"), ("27", "110", "대구광역시", "중구"), ("27", "720", "대구광역시", "군위군"),
    ("28", "710", "인천광역시", "강화군"), ("28", "245", "인천광역시", "계양구"), ("28", "200", "인천광역시", "남동구"), ("28", "140", "인천광역시", "동구"),
    ("28", "177", "인천광역시", "미추홀구"), ("28", "237", "인천광역시", "부평구"), ("28", "260", "인천광역시", "서구"), ("28", "185", "인천광역시", "연수구"),
    ("28", "720", "인천광역시", "옹진군"), ("28", "110", "인천광역시", "중구"),
    ("29", "200", "광주광역시", "광산구"), ("29", "155", "광주광역시", "남구"), ("29", "110", "광주광역시", "동구"), ("29", "170", "광주광역시", "북구"), ("29", "140", "광주광역시", "서구"),
    ("30", "230", "대전광역시", "대덕구"), ("30", "110", "대전광역시", "동구"), ("30", "170", "대전광역시", "서구"), ("30", "200", "대전광역시", "유성구"), ("30", "140", "대전광역시", "중구"),
    ("31", "140", "울산광역시", "남구"), ("31", "170", "울산광역시", "동구"), ("31", "200", "울산광역시", "북구"), ("31", "710", "울산광역시", "울주군"), ("31", "110", "울산광역시", "중구"),
    ("36", "110", "세종특별자치시", "세종특별자치시"),
    ("41", "820", "경기도", "가평군"), ("41", "281", "경기도", "고양시덕양구"), ("41", "285", "경기도", "고양시일산동구"), ("41", "287", "경기도", "고양시일산서구"),
    ("41", "290", "경기도", "과천시"), ("41", "210", "경기도", "광명시"), ("41", "610", "경기도", "광주시"), ("41", "310", "경기도", "구리시"),
    ("41", "410", "경기도", "군포시"), ("41", "570", "경기도", "김포시"), ("41", "360", "경기도", "남양주시"), ("41", "250", "경기도", "동두천시"),
    ("41", "192", "경기도", "부천시소사구"), ("41", "194", "경기도", "부천시오정구"), ("41", "196", "경기도", "부천시원미구"),
    ("41", "135", "경기도", "성남시분당구"), ("41", "131", "경기도", "성남시수정구"), ("41", "133", "경기도", "성남시중원구"),
    ("41", "113", "경기도", "수원시권선구"), ("41", "117", "경기도", "수원시영통구"), ("41", "111", "경기도", "수원시장안구"), ("41", "115", "경기도", "수원시팔달구"),
    ("41", "390", "경기도", "시흥시"), ("41", "273", "경기도", "안산시단원구"), ("41", "271", "경기도", "안산시상록구"), ("41", "550", "경기도", "안성시"),
    ("41", "173", "경기도", "안양시동안구"), ("41", "171", "경기도", "안양시만안구"), ("41", "630", "경기도", "양주시"), ("41", "830", "경기도", "양평군"),
    ("41", "670", "경기도", "여주시"), ("41", "800", "경기도", "연천군"), ("41", "370", "경기도", "오산시"), ("41", "463", "경기도", "용인시기흥구"),
    ("41", "465", "경기도", "용인시수지구"), ("41", "461", "경기도", "용인시처인구"), ("41", "430", "경기도", "의왕시"), ("41", "150", "경기도", "의정부시"),
    ("41", "500", "경기도", "이천시"), ("41", "480", "경기도", "파주시"), ("41", "220", "경기도", "평택시"), ("41", "650", "경기도", "포천시"),
    ("41", "450", "경기도", "하남시"), ("41", "590", "경기도", "화성시"),
    ("51", "150", "강원특별자치도", "강릉시"), ("51", "820", "강원특별자치도", "고성군"), ("51", "170", "강원특별자치도", "동해시"), ("51", "230", "강원특별자치도", "삼척시"),
    ("51", "210", "강원특별자치도", "속초시"), ("51", "800", "강원특별자치도", "양구군"), ("51", "830", "강원특별자치도", "양양군"), ("51", "750", "강원특별자치도", "영월군"),
    ("51", "130", "강원특별자치도", "원주시"), ("51", "810", "강원특별자치도", "인제군"), ("51", "770", "강원특별자치도", "정선군"), ("51", "780", "강원특별자치도", "철원군"),
    ("51", "110", "강원특별자치도", "춘천시"), ("51", "190", "강원특별자치도", "태백시"), ("51", "760", "강원특별자치도", "평창군"), ("51", "720", "강원특별자치도", "홍천군"),
    ("51", "790", "강원특별자치도", "화천군"), ("51", "730", "강원특별자치도", "횡성군"),
    ("43", "760", "충청북도", "괴산군"), ("43", "800", "충청북도", "단양군"), ("43", "720", "충청북도", "보은군"), ("43", "740", "충청북도", "영동군"),
    ("43", "730", "충청북도", "옥천군"), ("43", "770", "충청북도", "음성군"), ("43", "150", "충청북도", "제천시"), ("43", "745", "충청북도", "증평군"),
    ("43", "750", "충청북도", "진천군"), ("43", "111", "충청북도", "청주시상당구"), ("43", "112", "충청북도", "청주시서원구"), ("43", "114", "충청북도", "청주시청원구"),
    ("43", "113", "충청북도", "청주시흥덕구"), ("43", "130", "충청북도", "충주시"),
    ("44", "250", "충청남도", "계룡시"), ("44", "150", "충청남도", "공주시"), ("44", "710", "충청남도", "금산군"), ("44", "230", "충청남도", "논산시"),
    ("44", "270", "충청남도", "당진시"), ("44", "180", "충청남도", "보령시"), ("44", "760", "충청남도", "부여군"), ("44", "210", "충청남도", "서산시"),
    ("44", "770", "충청남도", "서천군"), ("44", "200", "충청남도", "아산시"), ("44", "810", "충청남도", "예산군"), ("44", "130", "충청남도", "천안시"),
    ("44", "131", "충청남도", "천안시동남구"), ("44", "133", "충청남도", "천안시서북구"), ("44", "790", "충청남도", "청양군"), ("44", "825", "충청남도", "태안군"), ("44", "800", "충청남도", "홍성군"),
    ("52", "790", "전북특별자치도", "고창군"), ("52", "130", "전북특별자치도", "군산시"), ("52", "210", "전북특별자치도", "김제시"), ("52", "190", "전북특별자치도", "남원시"),
    ("52", "730", "전북특별자치도", "무주군"), ("52", "800", "전북특별자치도", "부안군"), ("52", "770", "전북특별자치도", "순창군"), ("52", "710", "전북특별자치도", "완주군"),
    ("52", "140", "전북특별자치도", "익산시"), ("52", "750", "전북특별자치도", "임실군"), ("52", "740", "전북특별자치도", "장수군"), ("52", "113", "전북특별자치도", "전주시덕진구"),
    ("52", "111", "전북특별자치도", "전주시완산구"), ("52", "180", "전북특별자치도", "정읍시"), ("52", "720", "전북특별자치도", "진안군"),
    ("46", "810", "전라남도", "강진군"), ("46", "770", "전라남도", "고흥군"), ("46", "720", "전라남도", "곡성군"), ("46", "230", "전라남도", "광양시"),
    ("46", "730", "전라남도", "구례군"), ("46", "170", "전라남도", "나주시"), ("46", "710", "전라남도", "담양군"), ("46", "110", "전라남도", "목포시"),
    ("46", "840", "전라남도", "무안군"), ("46", "780", "전라남도", "보성군"), ("46", "150", "전라남도", "순천시"), ("46", "910", "전라남도", "신안군"),
    ("46", "130", "전라남도", "여수시"), ("46", "870", "전라남도", "영광군"), ("46", "830", "전라남도", "영암군"), ("46", "890", "전라남도", "완도군"),
    ("46", "880", "전라남도", "장성군"), ("46", "800", "전라남도", "장흥군"), ("46", "900", "전라남도", "진도군"), ("46", "860", "전라남도", "함평군"),
    ("46", "820", "전라남도", "해남군"), ("46", "790", "전라남도", "화순군"),
    ("47", "290", "경상북도", "경산시"), ("47", "130", "경상북도", "경주시"), ("47", "830", "경상북도", "고령군"), ("47", "190", "경상북도", "구미시"),
    ("47", "150", "경상북도", "김천시"), ("47", "280", "경상북도", "문경시"), ("47", "920", "경상북도", "봉화군"), ("47", "250", "경상북도", "상주시"),
    ("47", "840", "경상북도", "성주군"), ("47", "170", "경상북도", "안동시"), ("47", "770", "경상북도", "영덕군"), ("47", "760", "경상북도", "영양군"),
    ("47", "210", "경상북도", "영주시"), ("47", "230", "경상북도", "영천시"), ("47", "900", "경상북도", "예천군"), ("47", "940", "경상북도", "울릉군"),
    ("47", "930", "경상북도", "울진군"), ("47", "730", "경상북도", "의성군"), ("47", "820", "경상북도", "청도군"), ("47", "750", "경상북도", "청송군"),
    ("47", "850", "경상북도", "칠곡군"), ("47", "111", "경상북도", "포항시남구"), ("47", "113", "경상북도", "포항시북구"),
    ("48", "310", "경상남도", "거제시"), ("48", "880", "경상남도", "거창군"), ("48", "820", "경상남도", "고성군"), ("48", "250", "경상남도", "김해시"),
    ("48", "840", "경상남도", "남해군"), ("48", "270", "경상남도", "밀양시"), ("48", "240", "경상남도", "사천시"), ("48", "860", "경상남도", "산청군"),
    ("48", "330", "경상남도", "양산시"), ("48", "720", "경상남도", "의령군"), ("48", "170", "경상남도", "진주시"), ("48", "740", "경상남도", "창녕군"),
    ("48", "125", "경상남도", "창원시마산합포구"), ("48", "127", "경상남도", "창원시마산회원구"), ("48", "123", "경상남도", "창원시성산구"), ("48", "121", "경상남도", "창원시의창구"),
    ("48", "129", "경상남도", "창원시진해구"), ("48", "220", "경상남도", "통영시"), ("48", "850", "경상남도", "하동군"), ("48", "730", "경상남도", "함안군"),
    ("48", "870", "경상남도", "함양군"), ("48", "890", "경상남도", "합천군"),
    ("50", "130", "제주특별자치도", "서귀포시"), ("50", "110", "제주특별자치도", "제주시"),
]

FREQUENTZONE_YEARS = {
    "2024": "2025119",
    "2023": "2024056",
    "2022": "2023026",
    "2021": "2022046",
    "2020": "2021056",
    "2019": "2020087",
    "2018": "2019056",
    "2017": "2018074",
}

VIOLATION_YEARS = {
    "2024_신호위반": ("2024", "2025111", "신호위반"),
    "2024_중앙선침범": ("2024", "2025110", "중앙선침범"),
    "2023_신호위반": ("2023", "2024052", "신호위반"),
    "2023_중앙선침범": ("2023", "2024050", "중앙선침범"),
    "2022_신호위반": ("2022", "2023022", "신호위반"),
    "2022_중앙선침범": ("2022", "2023021", "중앙선침범"),
    "2021_신호위반": ("2021", "2022044", "신호위반"),
    "2021_중앙선침범": ("2021", "2021043", "중앙선침범"),
    "2020_신호위반": ("2020", "2021054", "신호위반"),
    "2020_중앙선침범": ("2020", "2021053", "중앙선침범"),
    "2019_신호위반": ("2019", "2020083", "신호위반"),
    "2019_중앙선침범": ("2019", "2020081", "중앙선침범"),
    "2018_신호위반": ("2018", "2019049", "신호위반"),
    "2018_중앙선침범": ("2018", "2019048", "중앙선침범"),
    "2017_신호위반": ("2017", "2018042", "신호위반"),
    "2017_중앙선침범": ("2017", "2018040", "중앙선침범"),
}


def read_env_flag(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def get_key(*names: str) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def safe_float(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return None
        return result
    except Exception:
        return None


def safe_int(value: Any) -> int:
    try:
        if value in (None, ""):
            return 0
        return int(float(value))
    except Exception:
        return 0


def parse_json_items(data: Any) -> tuple[list[dict[str, Any]], int, str, str]:
    if not isinstance(data, dict):
        return [], 0, "", "INVALID_JSON"
    header = data.get("header") or data.get("response", {}).get("header") or {}
    body = data.get("body") or data.get("response", {}).get("body") or {}
    result_code = clean_text(header.get("resultCode", data.get("resultCode", "")))
    result_msg = clean_text(header.get("resultMsg", data.get("resultMsg", "")))
    total_count = safe_int(body.get("totalCount", data.get("totalCount", 0)))
    items = body.get("items", data.get("items", []))
    if isinstance(items, dict):
        items = items.get("item", [])
    if isinstance(items, dict):
        items = [items]
    if not isinstance(items, list):
        items = []
    return [item for item in items if isinstance(item, dict)], total_count, result_code, result_msg


def parse_xml_items(text: str) -> tuple[list[dict[str, Any]], int, str, str]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return [], 0, "", "XML_PARSE_ERROR"
    result_code = ""
    result_msg = ""
    total_count = 0
    for element in root.iter():
        tag = element.tag.split("}")[-1]
        if tag == "resultCode":
            result_code = clean_text(element.text)
        elif tag == "resultMsg":
            result_msg = clean_text(element.text)
        elif tag == "totalCount":
            total_count = safe_int(element.text)
    rows = []
    for item in root.iter():
        tag = item.tag.split("}")[-1]
        if tag != "item":
            continue
        row = {child.tag.split("}")[-1]: clean_text(child.text) for child in list(item)}
        if row:
            rows.append(row)
    return rows, total_count, result_code, result_msg


def call_api(url: str, api_key: str, year_code: str, sido: str, gugun: str, page_no: int, num_rows: int) -> tuple[list[dict[str, Any]], int, str, str]:
    params = {
        "ServiceKey": api_key,
        "searchYearCd": year_code,
        "siDo": sido,
        "guGun": gugun,
        "type": "json",
        "numOfRows": str(num_rows),
        "pageNo": str(page_no),
    }
    response = requests.get(url, params=params, timeout=8)
    response.raise_for_status()
    text = response.text.strip()
    if text.startswith("{"):
        return parse_json_items(response.json())
    return parse_xml_items(response.text)


def normalize_item(item: dict[str, Any], source_name: str, accident_type: str, accident_year: str, year_code: str) -> dict[str, Any]:
    afos_fid = clean_text(item.get("afos_fid"))
    afos_id = clean_text(item.get("afos_id"))
    spot_cd = clean_text(item.get("spot_cd"))
    bjd_cd = clean_text(item.get("bjd_cd"))
    source_id = "_".join(part for part in [source_name, year_code, afos_fid, afos_id, spot_cd] if part)
    return {
        "사고지역관리번호": source_id,
        "사고연도": safe_int(accident_year),
        "사고유형구분": accident_type,
        "위치코드": spot_cd or bjd_cd,
        "사고다발지역시도시군구": clean_text(item.get("sido_sgg_nm")),
        "사고지역위치명": clean_text(item.get("spot_nm")),
        "사고건수": safe_int(item.get("occrrnc_cnt")),
        "사상자수": safe_int(item.get("caslt_cnt")),
        "사망자수": safe_int(item.get("dth_dnv_cnt")),
        "중상자수": safe_int(item.get("se_dnv_cnt")),
        "경상자수": safe_int(item.get("sl_dnv_cnt")),
        "부상신고자수": safe_int(item.get("wnd_dnv_cnt")),
        "위도": safe_float(item.get("la_crd")),
        "경도": safe_float(item.get("lo_crd")),
        "사고다발지역폴리곤정보": clean_text(item.get("geom_json")),
        "데이터기준일자": datetime.now().strftime("%Y-%m-%d"),
        "제공기관코드": "B552061",
        "제공기관명": "한국도로교통공단",
        "원천API": source_name,
        "API연도코드": year_code,
    }


def selected_frequentzone_years() -> list[tuple[str, str]]:
    scope = os.getenv("KOROAD_YEAR_SCOPE", "latest").strip().lower()
    if scope == "all":
        return list(FREQUENTZONE_YEARS.items())
    latest_year = max(FREQUENTZONE_YEARS.keys())
    return [(latest_year, FREQUENTZONE_YEARS[latest_year])]


def selected_violation_years() -> list[tuple[str, str, str]]:
    scope = os.getenv("KOROAD_YEAR_SCOPE", "latest").strip().lower()
    values = list(VIOLATION_YEARS.values())
    if scope == "all":
        return values
    return [item for item in values if item[0] == "2024"]


def collect_endpoint(url: str, api_key: str, source_name: str, jobs: list[tuple[str, str, str]], output_path: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    page_size = int(os.getenv("KOROAD_NUM_OF_ROWS", "100"))
    sleep_seconds = float(os.getenv("KOROAD_REQUEST_SLEEP", "0.03"))
    total_jobs = len(jobs) * len(REGION_CODES)
    failures = 0
    consecutive_failures = 0
    max_consecutive_failures = int(os.getenv("KOROAD_MAX_CONSECUTIVE_FAILURES", "2"))

    with tqdm(total=total_jobs, desc=source_name, ncols=100) as pbar:
        for accident_year, year_code, accident_type in jobs:
            for sido, gugun, _, _ in REGION_CODES:
                page_no = 1
                while True:
                    try:
                        items, total_count, result_code, result_msg = call_api(url, api_key, year_code, sido, gugun, page_no, page_size)
                    except Exception:
                        failures += 1
                        consecutive_failures += 1
                        break
                    if result_code and result_code not in {"00", "NORMAL_CODE"}:
                        if result_code not in {"03"}:
                            failures += 1
                            consecutive_failures += 1
                        else:
                            consecutive_failures = 0
                        break
                    consecutive_failures = 0
                    for item in items:
                        row = normalize_item(item, source_name, accident_type, accident_year, year_code)
                        if row["위도"] is not None and row["경도"] is not None:
                            rows.append(row)
                    if not total_count or page_no * page_size >= total_count:
                        break
                    page_no += 1
                    if sleep_seconds > 0:
                        time.sleep(sleep_seconds)
                pbar.set_postfix_str(f"수집 {len(rows)}건 / 실패 {failures}건")
                pbar.update(1)
                if consecutive_failures >= max_consecutive_failures:
                    pbar.update(total_jobs - pbar.n)
                    break
                if sleep_seconds > 0:
                    time.sleep(sleep_seconds)
            if consecutive_failures >= max_consecutive_failures:
                break

    df = pd.DataFrame(rows, columns=BASE_COLUMNS)
    if not df.empty:
        df = df.drop_duplicates(subset=["사고지역관리번호", "사고유형구분", "사고지역위치명", "위도", "경도"]).reset_index(drop=True)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
    elif output_path.exists():
        df = pd.read_csv(output_path, encoding="utf-8-sig")
    else:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
    return df


def fetch_koroad_hotspots() -> pd.DataFrame:
    load_dotenv(PROJECT_ROOT / ".env")
    EXTRA_DIR.mkdir(parents=True, exist_ok=True)

    if not read_env_flag("KOROAD_FETCH_ENABLED", True):
        frames = []
        for path in [FREQUENTZONE_OUTPUT, VIOLATION_OUTPUT]:
            if path.exists():
                frames.append(pd.read_csv(path, encoding="utf-8-sig"))
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=BASE_COLUMNS)

    frequentzone_key = get_key("KOROAD_FREQUENTZONE_API_KEY", "KOROAD_API_KEY", "SERVICE_KEY", "KMA_SERVICE_KEY")
    violation_key = get_key("KOROAD_VIOLATION_API_KEY", "KOROAD_API_KEY", "SERVICE_KEY", "KMA_SERVICE_KEY")

    frames: list[pd.DataFrame] = []
    print("\n[fetch_koroad_hotspots] 시작")

    if frequentzone_key:
        jobs = [(year, code, "지자체별 일반사고") for year, code in selected_frequentzone_years()]
        frames.append(collect_endpoint(FREQUENTZONE_URL, frequentzone_key, "KOROAD_FREQUENTZONE_LG", jobs, FREQUENTZONE_OUTPUT))
    else:
        print("지자체별 사고다발지역 API 키가 없습니다.")

    if violation_key:
        frames.append(collect_endpoint(VIOLATION_URL, violation_key, "KOROAD_FREQUENTZONE_LGR_VIOLT", selected_violation_years(), VIOLATION_OUTPUT))
    else:
        print("법규위반별 사고다발지역 API 키가 없습니다.")

    frames = [frame for frame in frames if frame is not None and not frame.empty]
    if frames:
        combined = pd.concat(frames, ignore_index=True)
        combined = combined.drop_duplicates(subset=["사고지역관리번호", "사고유형구분", "사고지역위치명", "위도", "경도"]).reset_index(drop=True)
    else:
        combined = pd.DataFrame(columns=BASE_COLUMNS)

    COMBINED_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(COMBINED_OUTPUT, index=False, encoding="utf-8-sig")
    print("\n=== fetch_koroad_hotspots 완료 ===")
    print("수집 행 개수:", len(combined))
    print("저장 위치:", COMBINED_OUTPUT)
    return combined


if __name__ == "__main__":
    fetch_koroad_hotspots()
