from pathlib import Path
import pandas as pd
from tqdm import tqdm


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def classify_risk(score: float) -> str:
    if score <= 25:
        return "낮음"
    elif score <= 50:
        return "보통"
    elif score <= 75:
        return "높음"
    else:
        return "매우높음"


def calc_alert_radius(score: float) -> int:
    if score >= 75:
        return 500
    elif score >= 50:
        return 400
    elif score >= 25:
        return 300
    else:
        return 200


def build_feature_table():
    accident_path = PROCESSED_DIR / "accident_final.csv"
    weather_path = PROCESSED_DIR / "weather_stats_final.csv"
    feature_path = PROCESSED_DIR / "risk_features.csv"
    final_table_path = PROCESSED_DIR / "final_risk_table.csv"

    print("\n[build_feature_table] 시작")

    with tqdm(total=9, desc="통합 feature 테이블 생성", ncols=100) as pbar:
        accident = pd.read_csv(accident_path, encoding="utf-8-sig")
        weather = pd.read_csv(weather_path, encoding="utf-8-sig")
        pbar.set_postfix_str("CSV 읽기 완료")
        pbar.update(1)

        accident.columns = accident.columns.str.strip()
        weather.columns = weather.columns.str.strip()
        pbar.set_postfix_str("컬럼명 정리")
        pbar.update(1)

        group_cols = ["사고다발지역시도시군구", "사고지역위치명", "위도", "경도"]

        zone_df = (
            accident.groupby(group_cols, as_index=False)
            .agg(
                사고유형수=("사고유형구분", "nunique"),
                사고유형구분_목록=("사고유형구분", lambda x: ", ".join(sorted(set(map(str, x))))),
                사고연도_최소=("사고연도", "min"),
                사고연도_최대=("사고연도", "max"),
                사고건수합=("사고건수", "sum"),
                사상자수합=("사상자수", "sum"),
                사망자수합=("사망자수", "sum"),
                중상자수합=("중상자수", "sum"),
                경상자수합=("경상자수", "sum"),
                부상신고자수합=("부상신고자수", "sum"),
                평균위험점수=("위험점수", "mean"),
                최대위험점수=("위험점수", "max"),
                평균정규화위험점수=("정규화위험점수", "mean"),
                최대정규화위험점수=("정규화위험점수", "max"),
            )
            .copy()
        )
        pbar.set_postfix_str("사고구간 집계 완료")
        pbar.update(1)

        zone_df.insert(0, "zone_id", [f"ZONE_{i:05d}" for i in range(1, len(zone_df) + 1)])
        zone_df["위험등급"] = zone_df["평균정규화위험점수"].apply(classify_risk)
        zone_df["알림반경m"] = zone_df["평균정규화위험점수"].apply(calc_alert_radius)
        pbar.set_postfix_str("위험등급/반경 생성")
        pbar.update(1)

        weather_by_condition = (
            weather.groupby("기상상태", as_index=False)["위험점수"]
            .sum()
            .sort_values("위험점수", ascending=False)
            .reset_index(drop=True)
        )
        weather_by_time = (
            weather.groupby("시간대", as_index=False)["위험점수"]
            .sum()
            .sort_values("위험점수", ascending=False)
            .reset_index(drop=True)
        )
        representative_weather = weather_by_condition.iloc[0]["기상상태"]
        representative_time = weather_by_time.iloc[0]["시간대"]
        pbar.set_postfix_str("대표 위험 날씨/시간대 계산")
        pbar.update(1)

        non_clear_weather = weather[~weather["기상상태"].astype(str).str.contains("맑음", na=False)].copy()
        if len(non_clear_weather) > 0:
            caution_weather = (
                non_clear_weather.groupby("기상상태", as_index=False)["위험점수"]
                .sum()
                .sort_values("위험점수", ascending=False)
                .iloc[0]["기상상태"]
            )
            caution_time = (
                non_clear_weather.groupby("시간대", as_index=False)["위험점수"]
                .sum()
                .sort_values("위험점수", ascending=False)
                .iloc[0]["시간대"]
            )
        else:
            caution_weather = representative_weather
            caution_time = representative_time

        weather_mean_score = round(weather["위험점수"].mean(), 2)
        weather_max_score = round(weather["위험점수"].max(), 2)
        pbar.set_postfix_str("주의 날씨/시간대 계산")
        pbar.update(1)

        zone_df["대표위험기상상태"] = representative_weather
        zone_df["대표위험시간대"] = representative_time
        zone_df["주의기상상태"] = caution_weather
        zone_df["주의시간대"] = caution_time
        zone_df["날씨평균위험점수"] = weather_mean_score
        zone_df["날씨최대위험점수"] = weather_max_score
        zone_df["대표경고문구"] = zone_df.apply(
            lambda row: (
                f"{row['사고지역위치명']}은(는) {row['위험등급']} 위험구간입니다. "
                f"특히 {row['주의시간대']} / {row['주의기상상태']} 조건에서 주의가 필요합니다."
            ),
            axis=1,
        )
        pbar.set_postfix_str("경고문구 생성")
        pbar.update(1)

        zone_df = zone_df.sort_values(
            by=["평균정규화위험점수", "최대위험점수", "사고건수합"],
            ascending=[False, False, False]
        ).reset_index(drop=True)
        zone_df["zone_id"] = [f"ZONE_{i:05d}" for i in range(1, len(zone_df) + 1)]
        pbar.set_postfix_str("정렬 및 ID 재부여")
        pbar.update(1)

        feature_cols = [
            "zone_id", "사고다발지역시도시군구", "사고지역위치명", "위도", "경도",
            "사고유형수", "사고유형구분_목록", "사고연도_최소", "사고연도_최대",
            "사고건수합", "사상자수합", "사망자수합", "중상자수합", "경상자수합", "부상신고자수합",
            "평균위험점수", "최대위험점수", "평균정규화위험점수", "최대정규화위험점수",
            "위험등급", "대표위험기상상태", "대표위험시간대", "주의기상상태", "주의시간대",
            "날씨평균위험점수", "날씨최대위험점수", "알림반경m", "대표경고문구"
        ]
        risk_features = zone_df[feature_cols].copy()
        risk_features.to_csv(feature_path, index=False, encoding="utf-8-sig")

        final_cols = [
            "zone_id", "사고다발지역시도시군구", "사고지역위치명", "위도", "경도",
            "사고유형수", "사고유형구분_목록", "사고연도_최소", "사고연도_최대",
            "사고건수합", "사상자수합", "사망자수합", "중상자수합", "경상자수합", "부상신고자수합",
            "평균위험점수", "최대위험점수", "평균정규화위험점수", "최대정규화위험점수",
            "위험등급", "알림반경m", "주의기상상태", "주의시간대", "대표경고문구"
        ]
        final_risk_table = risk_features[final_cols].copy()
        final_risk_table = final_risk_table.rename(columns={"평균정규화위험점수": "정적위험점수"})
        final_risk_table.to_csv(final_table_path, index=False, encoding="utf-8-sig")
        pbar.set_postfix_str("CSV 저장 완료")
        pbar.update(1)

    print("\n=== build_feature_table 완료 ===")
    print("risk_features 저장:", feature_path)
    print("final_risk_table 저장:", final_table_path)
    print("생성 행 개수:", len(risk_features))

    print("\n상위 5개 위험구간:")
    print(risk_features[["zone_id", "사고지역위치명", "평균정규화위험점수", "위험등급", "알림반경m"]].head())

    return risk_features, final_risk_table


if __name__ == "__main__":
    build_feature_table()
