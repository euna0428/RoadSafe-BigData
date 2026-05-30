from pathlib import Path
import pandas as pd
from tqdm import tqdm


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def make_risk_score():
    print("\n[make_risk_score] 시작")

    weather_path = PROCESSED_DIR / "weather_stats_final.csv"
    accident_path = PROCESSED_DIR / "accident_final.csv"

    with tqdm(total=5, desc="위험도 요약 분석", ncols=100) as pbar:
        weather = pd.read_csv(weather_path, encoding="utf-8-sig")
        accident = pd.read_csv(accident_path, encoding="utf-8-sig")
        pbar.set_postfix_str("CSV 읽기 완료")
        pbar.update(1)

        weather_by_condition = weather.groupby("기상상태")["위험점수"].sum().sort_values(ascending=False)
        pbar.set_postfix_str("기상상태 분석")
        pbar.update(1)

        weather_by_time = weather.groupby("시간대")["위험점수"].sum().sort_values(ascending=False)
        pbar.set_postfix_str("시간대 분석")
        pbar.update(1)

        top5_accident = accident.sort_values(by="위험점수", ascending=False)[
            ["사고연도", "사고유형구분", "사고다발지역시도시군구", "사고지역위치명", "사고건수", "사상자수", "위험점수", "위험등급"]
        ].head(5)
        pbar.set_postfix_str("상위 사고구간 분석")
        pbar.update(1)

        pbar.set_postfix_str("등급 분포 확인")
        pbar.update(1)

    print("===== 교통사고 위험도 분석 결과 요약 =====")

    print("\n[1] 가장 위험한 기상상태")
    print(weather_by_condition.head(3))

    print("\n[2] 가장 위험한 시간대")
    print(weather_by_time.head(5))

    print("\n[3] 사고다발지역 상위 5개")
    print(top5_accident)

    print("\n[4] weather 위험등급 분포")
    print(weather["위험등급"].value_counts())

    print("\n[5] accident 위험등급 분포")
    print(accident["위험등급"].value_counts())

    return {
        "weather_by_condition": weather_by_condition,
        "weather_by_time": weather_by_time,
        "top5_accident": top5_accident
    }


if __name__ == "__main__":
    make_risk_score()
