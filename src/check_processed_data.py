import pandas as pd

weather = pd.read_csv("data/processed/weather_stats_clean.csv", encoding="utf-8-sig")
accident = pd.read_csv("data/processed/accident_clean.csv", encoding="utf-8-sig")

print("===== weather_stats_clean =====")
print("크기:", weather.shape)
print("컬럼:", list(weather.columns))
print(weather.head())

print("\n===== accident_clean =====")
print("크기:", accident.shape)
print("컬럼:", list(accident.columns))
print(accident.head())

print("\n===== 기상상태별 위험점수 합계 =====")
weather_risk_by_weather = weather.groupby("기상상태")["위험점수"].sum().sort_values(ascending=False)
print(weather_risk_by_weather)

print("\n===== 시간대별 위험점수 합계 =====")
weather_risk_by_time = weather.groupby("시간대")["위험점수"].sum().sort_values(ascending=False)
print(weather_risk_by_time)

print("\n===== 사고다발지역 위험점수 상위 10개 =====")
top10_accident = accident.sort_values(by="위험점수", ascending=False)[
    ["사고연도", "사고유형구분", "사고다발지역시도시군구", "사고지역위치명", "사고건수", "사상자수", "위험점수"]
].head(10)
print(top10_accident)
