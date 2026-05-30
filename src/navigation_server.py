from __future__ import annotations

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import json
import math
import os
from typing import Any

import pandas as pd
import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LIVE_RISK_PATH = PROJECT_ROOT / "data" / "processed" / "live_risk_table.csv"
STATIC_RISK_PATH = PROJECT_ROOT / "data" / "processed" / "final_risk_table.csv"
LIVE_MAP_PATH = PROJECT_ROOT / "outputs" / "maps" / "live_risk_map.html"
KAKAO_DIRECTIONS_URL = "https://apis-navi.kakaomobility.com/v1/directions"
DEFAULT_PORT = 8000
ROUTE_MATCH_BUFFER_M = 500
DESTINATION_NEARBY_RADIUS_M = 1500
MAX_ROUTE_RISK_COUNT = 300
MAX_DESTINATION_RISK_COUNT = 80
ALLOWED_ROUTE_PRIORITIES = {"RECOMMEND", "TIME", "DISTANCE"}
ROUTE_PRIORITY_ALIASES = {
    "": "DISTANCE",
    "BEST": "RECOMMEND",
    "RECOMMEND": "RECOMMEND",
    "FASTEST": "TIME",
    "TIME": "TIME",
    "SHORTEST": "DISTANCE",
    "DISTANCE": "DISTANCE",
}

load_dotenv(PROJECT_ROOT / ".env")


def get_kakao_rest_key() -> str:
    return (
        os.getenv("KAKAO_REST_KEY")
        or os.getenv("KAKAO_MOBILITY_REST_KEY")
        or os.getenv("KAKAO_API_REST_KEY")
        or ""
    ).strip()


def normalize_route_priority(value: str | None) -> str:
    raw = (value or "").strip().upper()
    normalized = ROUTE_PRIORITY_ALIASES.get(raw, raw)
    if normalized not in ALLOWED_ROUTE_PRIORITIES:
        return "DISTANCE"
    return normalized


def safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        num = float(value)
        if pd.isna(num) or math.isinf(num):
            return default
        return num
    except Exception:
        return default


def safe_text(value: Any, default: str = "") -> str:
    if value is None or pd.isna(value):
        return default
    return str(value).strip()


def parse_lon_lat(value: str) -> tuple[float, float]:
    parts = [item.strip() for item in value.split(",")]
    if len(parts) != 2:
        raise ValueError("좌표는 '경도,위도' 형식이어야 합니다.")
    lon = float(parts[0])
    lat = float(parts[1])
    if not (-180 <= lon <= 180 and -90 <= lat <= 90):
        raise ValueError("좌표 범위가 올바르지 않습니다.")
    return lon, lat


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371000
    to_rad = math.radians
    d_lat = to_rad(lat2 - lat1)
    d_lon = to_rad(lon2 - lon1)
    a = math.sin(d_lat / 2) ** 2 + math.cos(to_rad(lat1)) * math.cos(to_rad(lat2)) * math.sin(d_lon / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def point_segment_distance_m(point_lat: float, point_lon: float, a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    ref_lat = math.radians((point_lat + a_lat + b_lat) / 3)
    meter_per_lat = 111_320
    meter_per_lon = 111_320 * math.cos(ref_lat)
    px, py = point_lon * meter_per_lon, point_lat * meter_per_lat
    ax, ay = a_lon * meter_per_lon, a_lat * meter_per_lat
    bx, by = b_lon * meter_per_lon, b_lat * meter_per_lat
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0, min(1, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def min_distance_to_route_m(lat: float, lon: float, route_points: list[dict[str, float]]) -> float:
    if not route_points:
        return math.inf
    if len(route_points) == 1:
        only = route_points[0]
        return haversine_m(lat, lon, only["lat"], only["lon"])
    best = math.inf
    for idx in range(len(route_points) - 1):
        a = route_points[idx]
        b = route_points[idx + 1]
        dist = point_segment_distance_m(lat, lon, a["lat"], a["lon"], b["lat"], b["lon"])
        if dist < best:
            best = dist
    return best


def load_risk_rows() -> pd.DataFrame:
    path = LIVE_RISK_PATH if LIVE_RISK_PATH.exists() else STATIC_RISK_PATH
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = df.columns.astype(str).str.strip()
    return df


def normalize_risk_row(row: pd.Series, distance_to_route_m: float | None = None, distance_to_destination_m: float | None = None, source: str = "route") -> dict[str, Any]:
    grade = safe_text(row.get("실시간위험등급", row.get("위험등급", "보통")), "보통")
    score = safe_float(row.get("실시간위험점수", row.get("정적위험점수", 0)), 0) or 0
    radius = safe_float(row.get("실시간알림반경m", row.get("알림반경m", 300)), 300) or 300

    def rounded(value: Any) -> float | None:
        num = safe_float(value)
        return round(num, 2) if num is not None else None

    return {
        "source": source,
        "zone_id": safe_text(row.get("zone_id", "")),
        "location_name": safe_text(row.get("사고지역위치명", "위험구간")),
        "region": safe_text(row.get("사고다발지역시도시군구", "")),
        "lat": safe_float(row.get("위도")),
        "lon": safe_float(row.get("경도")),
        "score": round(score, 2),
        "grade": grade,
        "radius_m": int(radius),
        "distance_to_route_m": round(distance_to_route_m, 1) if distance_to_route_m is not None and math.isfinite(distance_to_route_m) else None,
        "distance_to_destination_m": round(distance_to_destination_m, 1) if distance_to_destination_m is not None and math.isfinite(distance_to_destination_m) else None,
        "warning": safe_text(row.get("실시간대표경고문구", row.get("대표경고문구", ""))),
        "weather": safe_text(row.get("current_weather", row.get("주의기상상태", ""))),
        "time_band": safe_text(row.get("현재시간대", row.get("주의시간대", ""))),
        "attention_weather": safe_text(row.get("주의기상상태", "")),
        "attention_time_band": safe_text(row.get("주의시간대", "")),
        "static_score": rounded(row.get("정적위험점수")),
        "static_grade": safe_text(row.get("위험등급", "")),
        "change_score": rounded(row.get("위험변화점수")),
        "change_status": safe_text(row.get("위험변화상태", "")),
        "change_reason": safe_text(row.get("위험변화사유", "")),
        "weather_weight": rounded(row.get("기상가중치")),
        "weather_weight_reason": safe_text(row.get("기상가중치사유", "")),
        "time_weight": rounded(row.get("시간가중치")),
        "time_weight_reason": safe_text(row.get("시간가중치사유", "")),
        "incident_weight": rounded(row.get("돌발상황가중치")),
        "incident_reason": safe_text(row.get("돌발상황사유", "")),
        "nearest_incident_distance_m": rounded(row.get("가까운돌발상황거리m")),
        "nearest_incident_type": safe_text(row.get("가까운돌발상황유형", "")),
        "nearest_incident_road": safe_text(row.get("가까운돌발상황도로명", "")),
        "nearest_incident_message": safe_text(row.get("가까운돌발상황내용", "")),
        "current_weather_raw": safe_text(row.get("current_weather_raw", "")),
        "current_temp_c": rounded(row.get("current_temp_c")),
        "humidity_pct": rounded(row.get("humidity_pct")),
        "rain_1h_mm": rounded(row.get("rain_1h_mm")),
        "wind_speed_ms": rounded(row.get("wind_speed_ms")),
        "obs_time": safe_text(row.get("obs_time", "")),
        "collected_at_kst": safe_text(row.get("collected_at_kst", "")),
        "weather_api_status": safe_text(row.get("api_status", "")),
        "weather_cache_status": safe_text(row.get("cache_status", "")),
        "weather_last_error_status": safe_text(row.get("last_error_status", "")),
        "weather_fallback_region": safe_text(row.get("fallback_region_key", "")),
        "weather_fallback_distance_m": rounded(row.get("fallback_distance_m")),
        "weather_fallback_note": safe_text(row.get("fallback_note", "")),
        "updated_at": safe_text(row.get("갱신시각KST", "")),
        "accident_count": rounded(row.get("사고건수합")),
        "casualty_count": rounded(row.get("사상자수합")),
        "death_count": rounded(row.get("사망자수합")),
        "serious_injury_count": rounded(row.get("중상자수합")),
        "minor_injury_count": rounded(row.get("경상자수합")),
        "reported_injury_count": rounded(row.get("부상신고자수합")),
        "raw_avg_score": rounded(row.get("평균위험점수")),
        "raw_max_score": rounded(row.get("최대위험점수")),
        "max_normalized_score": rounded(row.get("최대정규화위험점수")),
    }


def sort_risks(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grade_order = {"매우높음": 0, "높음": 1, "보통": 2, "낮음": 3}
    return sorted(
        items,
        key=lambda item: (
            grade_order.get(item.get("grade"), 9),
            item.get("distance_to_route_m") if item.get("distance_to_route_m") is not None else math.inf,
            item.get("distance_to_destination_m") if item.get("distance_to_destination_m") is not None else math.inf,
            -safe_float(item.get("score"), 0),
        ),
    )


def match_risks_to_route(route_points: list[dict[str, float]], risk_df: pd.DataFrame | None = None) -> list[dict[str, Any]]:
    df = load_risk_rows() if risk_df is None else risk_df
    if df.empty or not route_points:
        return []
    matched: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        lat = safe_float(row.get("위도"))
        lon = safe_float(row.get("경도"))
        if lat is None or lon is None:
            continue
        radius = safe_float(row.get("실시간알림반경m", row.get("알림반경m", 300)), 300) or 300
        dist = min_distance_to_route_m(lat, lon, route_points)
        if dist <= max(radius, ROUTE_MATCH_BUFFER_M):
            matched.append(normalize_risk_row(row, distance_to_route_m=dist, source="route"))
    return sort_risks(matched)[:MAX_ROUTE_RISK_COUNT]


def match_risks_near_destination(destination_lat: float, destination_lon: float, route_zone_ids: set[str], risk_df: pd.DataFrame | None = None) -> list[dict[str, Any]]:
    df = load_risk_rows() if risk_df is None else risk_df
    if df.empty:
        return []
    matched: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        zone_id = safe_text(row.get("zone_id", ""))
        if zone_id and zone_id in route_zone_ids:
            continue
        lat = safe_float(row.get("위도"))
        lon = safe_float(row.get("경도"))
        if lat is None or lon is None:
            continue
        dist = haversine_m(destination_lat, destination_lon, lat, lon)
        if dist <= DESTINATION_NEARBY_RADIUS_M:
            matched.append(normalize_risk_row(row, distance_to_destination_m=dist, source="destination"))
    return sort_risks(matched)[:MAX_DESTINATION_RISK_COUNT]


def extract_route_points(kakao_response: dict[str, Any]) -> list[dict[str, float]]:
    routes = kakao_response.get("routes") or []
    if not routes:
        return []
    points: list[dict[str, float]] = []
    for section in routes[0].get("sections", []):
        for road in section.get("roads", []):
            vertices = road.get("vertexes") or []
            for idx in range(0, len(vertices), 2):
                try:
                    lon = float(vertices[idx])
                    lat = float(vertices[idx + 1])
                except Exception:
                    continue
                if not points or points[-1]["lat"] != lat or points[-1]["lon"] != lon:
                    points.append({"lat": lat, "lon": lon})
    return points


def extract_route_summary(kakao_response: dict[str, Any]) -> dict[str, Any]:
    routes = kakao_response.get("routes") or []
    if not routes:
        return {}
    summary = routes[0].get("summary", {})
    return {
        "distance_m": summary.get("distance"),
        "duration_sec": summary.get("duration"),
        "fare": summary.get("fare", {}),
        "priority": summary.get("priority", ""),
    }


def request_kakao_route(origin: str, destination: str, priority: str) -> tuple[dict[str, Any], list[dict[str, float]], dict[str, Any], str]:
    rest_key = get_kakao_rest_key()
    route_priority = normalize_route_priority(priority)
    origin_lon, origin_lat = parse_lon_lat(origin)
    dest_lon, dest_lat = parse_lon_lat(destination)
    if not rest_key:
        points = [{"lat": origin_lat, "lon": origin_lon}, {"lat": dest_lat, "lon": dest_lon}]
        summary = {
            "distance_m": round(haversine_m(origin_lat, origin_lon, dest_lat, dest_lon)),
            "duration_sec": None,
            "priority": "FALLBACK_STRAIGHT_LINE",
            "requested_priority": route_priority,
        }
        return {"routes": []}, points, summary, "NO_KAKAO_REST_KEY"
    params = {
        "origin": origin,
        "destination": destination,
        "priority": route_priority,
        "car_fuel": "GASOLINE",
        "car_hipass": "false",
        "alternatives": "false",
        "road_details": "true",
    }
    headers = {"Authorization": f"KakaoAK {rest_key}"}
    response = requests.get(KAKAO_DIRECTIONS_URL, params=params, headers=headers, timeout=20)
    response.raise_for_status()
    data = response.json()
    points = extract_route_points(data)
    summary = extract_route_summary(data)
    summary["requested_priority"] = route_priority
    if not summary.get("priority"):
        summary["priority"] = route_priority
    if not points:
        points = [{"lat": origin_lat, "lon": origin_lon}, {"lat": dest_lat, "lon": dest_lon}]
        summary.setdefault("distance_m", round(haversine_m(origin_lat, origin_lon, dest_lat, dest_lon)))
        summary.setdefault("duration_sec", None)
        return data, points, summary, "KAKAO_ROUTE_EMPTY_FALLBACK"
    return data, points, summary, "OK"


def json_response(handler: SimpleHTTPRequestHandler, payload: dict[str, Any], status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


class NavigationHandler(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/route":
            self.handle_route_api(parsed.query)
            return
        if parsed.path in {"/", ""}:
            self.path = "/outputs/maps/live_risk_map.html"
        return super().do_GET()

    def handle_route_api(self, query: str) -> None:
        try:
            params = parse_qs(query)
            origin = params.get("origin", [""])[0]
            destination = params.get("destination", [""])[0]
            priority = normalize_route_priority(params.get("priority", ["DISTANCE"])[0])
            if not origin or not destination:
                raise ValueError("origin과 destination이 필요합니다. 형식: 경도,위도")
            dest_lon, dest_lat = parse_lon_lat(destination)
            _, route_points, summary, api_status = request_kakao_route(origin, destination, priority)
            risk_df = load_risk_rows()
            route_risks = match_risks_to_route(route_points, risk_df)
            route_zone_ids = {safe_text(item.get("zone_id")) for item in route_risks if safe_text(item.get("zone_id"))}
            destination_risks = match_risks_near_destination(dest_lat, dest_lon, route_zone_ids, risk_df)
            all_risks = route_risks + destination_risks
            json_response(self, {
                "api_status": api_status,
                "requested_priority": priority,
                "summary": summary,
                "route_points": route_points,
                "route_risks": route_risks,
                "destination_risks": destination_risks,
                "all_risks": all_risks,
                "risk_count": len(all_risks),
                "route_risk_count": len(route_risks),
                "destination_risk_count": len(destination_risks),
                "route_match_buffer_m": ROUTE_MATCH_BUFFER_M,
                "destination_nearby_radius_m": DESTINATION_NEARBY_RADIUS_M,
                "risk_dataset_rows": int(len(risk_df)),
            })
        except Exception as exc:
            json_response(self, {"api_status": "ERROR", "message": str(exc)}, status=400)


def run_server(port: int = DEFAULT_PORT) -> None:
    os.chdir(PROJECT_ROOT)
    server = ThreadingHTTPServer(("127.0.0.1", port), NavigationHandler)
    print(f"RoadSafe 내비게이션 서버 실행: http://127.0.0.1:{port}/")
    print(f"지도 파일: {LIVE_MAP_PATH}")
    print("종료: Ctrl + C")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
