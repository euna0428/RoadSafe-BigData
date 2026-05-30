from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import sys
import time

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tqdm import tqdm
from zoneinfo import ZoneInfo

from src.fetch_forecast import fetch_forecast
from src.fetch_incident import fetch_incident
from src.update_live_risk import update_live_risk
from src.make_live_map import make_live_risk_map


STATIC_TABLE_PATH = PROJECT_ROOT / "data" / "processed" / "final_risk_table.csv"
KST = ZoneInfo("Asia/Seoul")

RUN_FOREVER = False
INTERVAL_MINUTES = 10
MAP_TOP_N = None


def run_one_cycle(map_top_n: int | None = MAP_TOP_N):
    steps = [
        ("현재 날씨 수집", lambda: fetch_forecast(sleep_seconds=2.0)),
        ("돌발상황 수집", fetch_incident),
        ("실시간 위험도 갱신", update_live_risk),
        ("카카오 실시간 지도 생성", lambda: make_live_risk_map(top_n=map_top_n)),
    ]

    now_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n=== 실시간 파이프라인 1회 실행 시작 ({now_kst} KST) ===")

    with tqdm(total=len(steps), desc="실시간 파이프라인", ncols=100) as pbar:
        for step_name, step_func in steps:
            print(f"\n>>> 현재 단계: {step_name}")
            step_func()
            pbar.set_postfix_str(step_name)
            pbar.update(1)

    print("\n=== 실시간 파이프라인 1회 실행 완료 ===")


def run_realtime_pipeline(interval_minutes: int = INTERVAL_MINUTES, run_forever: bool = RUN_FOREVER, map_top_n: int | None = MAP_TOP_N):
    if not STATIC_TABLE_PATH.exists():
        raise FileNotFoundError(
            f"기준 정적 테이블이 없습니다: {STATIC_TABLE_PATH}\nmain.py를 먼저 1회 실행해서 final_risk_table.csv를 만든 뒤 시작해 주세요."
        )

    cycle = 1
    while True:
        print(f"\n############################")
        print(f"실시간 갱신 사이클 {cycle} 시작")
        print(f"############################")
        try:
            run_one_cycle(map_top_n=map_top_n)
        except Exception as exc:
            print(f"\n[오류] 사이클 {cycle} 실행 중 예외 발생: {exc}")

        if not run_forever:
            break

        next_run = datetime.now(KST) + timedelta(minutes=interval_minutes)
        print(
            f"\n다음 실행 예정 시각(KST): {next_run.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        time.sleep(interval_minutes * 60)
        cycle += 1


if __name__ == "__main__":
    run_realtime_pipeline()
