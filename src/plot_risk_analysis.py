from __future__ import annotations

from pathlib import Path
from typing import Iterable

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import pandas as pd
from tqdm import tqdm


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FIGURE_DIR = PROJECT_ROOT / "outputs" / "figures"
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"


NUMERIC_COLUMNS = ["사고건수", "사망자수", "중상자수", "경상자수", "부상신고자수", "위험점수"]


def setup_korean_font() -> None:
    """Windows/Mac/Linux 환경에서 가능한 한글 폰트를 자동 선택한다."""
    candidate_fonts: Iterable[str] = (
        "Malgun Gothic",
        "AppleGothic",
        "NanumGothic",
        "Noto Sans CJK KR",
        "Noto Sans KR",
        "DejaVu Sans",
    )
    installed = {font.name for font in fm.fontManager.ttflist}
    for font_name in candidate_fonts:
        if font_name in installed:
            plt.rcParams["font.family"] = font_name
            break
    plt.rcParams["axes.unicode_minus"] = False


def pct(series: pd.Series) -> pd.Series:
    total = pd.to_numeric(series, errors="coerce").fillna(0).sum()
    if total == 0:
        return pd.Series([0.0] * len(series), index=series.index)
    return (pd.to_numeric(series, errors="coerce").fillna(0) / total * 100).round(2)


def save_bar_chart(series: pd.Series, title: str, xlabel: str, ylabel: str, output_path: Path, rotation: int = 0) -> None:
    plt.figure(figsize=(10, 6))
    series.plot(kind="bar")
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.xticks(rotation=rotation)
    plt.tight_layout()
    plt.savefig(output_path, dpi=180)
    plt.close()


def save_horizontal_bar_chart(series: pd.Series, title: str, xlabel: str, ylabel: str, output_path: Path) -> None:
    plt.figure(figsize=(12, 7))
    series.sort_values(ascending=True).plot(kind="barh")
    plt.title(title)
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.tight_layout()
    plt.savefig(output_path, dpi=180)
    plt.close()


def make_weather_ratio_summary(weather: pd.DataFrame) -> pd.DataFrame:
    weather = weather.copy()
    for col in NUMERIC_COLUMNS:
        if col in weather.columns:
            weather[col] = pd.to_numeric(weather[col], errors="coerce").fillna(0)

    summary = (
        weather.groupby("기상상태", as_index=False)[NUMERIC_COLUMNS]
        .sum()
        .sort_values("사고건수", ascending=False)
        .reset_index(drop=True)
    )

    summary["사고건수비율_pct"] = pct(summary["사고건수"])
    summary["위험점수비율_pct"] = pct(summary["위험점수"])
    summary["사고1건당위험점수"] = (summary["위험점수"] / summary["사고건수"].replace(0, pd.NA)).fillna(0).round(3)
    summary["사망자비율_pct"] = pct(summary["사망자수"])
    summary["중상자비율_pct"] = pct(summary["중상자수"])

    return summary


def make_clear_weather_time_summary(weather: pd.DataFrame) -> pd.DataFrame:
    clear_df = weather[weather["기상상태"].astype(str).str.contains("맑", na=False)].copy()
    if clear_df.empty:
        return pd.DataFrame(columns=["시간대", "사고건수", "위험점수", "맑음내사고비율_pct", "맑음내위험점수비율_pct", "사고1건당위험점수"])

    for col in NUMERIC_COLUMNS:
        if col in clear_df.columns:
            clear_df[col] = pd.to_numeric(clear_df[col], errors="coerce").fillna(0)

    summary = (
        clear_df.groupby("시간대", as_index=False)[NUMERIC_COLUMNS]
        .sum()
        .sort_values("사고건수", ascending=False)
        .reset_index(drop=True)
    )
    summary["맑음내사고비율_pct"] = pct(summary["사고건수"])
    summary["맑음내위험점수비율_pct"] = pct(summary["위험점수"])
    summary["사고1건당위험점수"] = (summary["위험점수"] / summary["사고건수"].replace(0, pd.NA)).fillna(0).round(3)
    return summary


def plot_risk_analysis() -> dict[str, pd.DataFrame]:
    print("\n[plot_risk_analysis] 시작")
    setup_korean_font()

    weather_path = PROCESSED_DIR / "weather_stats_clean.csv"
    accident_path = PROCESSED_DIR / "accident_clean.csv"

    if not weather_path.exists():
        raise FileNotFoundError(f"기상 통계 전처리 파일이 없습니다: {weather_path}")
    if not accident_path.exists():
        raise FileNotFoundError(f"사고 전처리 파일이 없습니다: {accident_path}")

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)

    with tqdm(total=9, desc="그래프 생성", ncols=100) as pbar:
        weather = pd.read_csv(weather_path, encoding="utf-8-sig")
        accident = pd.read_csv(accident_path, encoding="utf-8-sig")
        weather.columns = weather.columns.astype(str).str.strip()
        accident.columns = accident.columns.astype(str).str.strip()
        pbar.set_postfix_str("CSV 읽기 완료")
        pbar.update(1)

        weather_summary = make_weather_ratio_summary(weather)
        weather_summary.to_csv(TABLE_DIR / "weather_ratio_summary.csv", index=False, encoding="utf-8-sig")
        pbar.set_postfix_str("기상 비율 요약표 저장")
        pbar.update(1)

        accident_ratio = weather_summary.set_index("기상상태")["사고건수비율_pct"].sort_values(ascending=False)
        save_bar_chart(
            accident_ratio,
            "기상상태별 사고건수 비율",
            "기상상태",
            "비율(%)",
            FIGURE_DIR / "weather_accident_ratio.png",
        )
        pbar.set_postfix_str("기상 사고건수 비율 그래프 저장")
        pbar.update(1)

        risk_ratio = weather_summary.set_index("기상상태")["위험점수비율_pct"].sort_values(ascending=False)
        save_bar_chart(
            risk_ratio,
            "기상상태별 위험점수 비율",
            "기상상태",
            "비율(%)",
            FIGURE_DIR / "weather_risk_ratio.png",
        )
        save_bar_chart(
            risk_ratio,
            "기상상태별 위험점수 비율",
            "기상상태",
            "비율(%)",
            FIGURE_DIR / "weather_risk.png",
        )
        pbar.set_postfix_str("기상 위험점수 비율 그래프 저장")
        pbar.update(1)

        severity_per_case = weather_summary.set_index("기상상태")["사고1건당위험점수"].sort_values(ascending=False)
        save_bar_chart(
            severity_per_case,
            "기상상태별 사고 1건당 위험점수",
            "기상상태",
            "사고 1건당 위험점수",
            FIGURE_DIR / "weather_severity_per_case.png",
        )
        pbar.set_postfix_str("사고 1건당 위험점수 그래프 저장")
        pbar.update(1)

        clear_summary = make_clear_weather_time_summary(weather)
        clear_summary.to_csv(TABLE_DIR / "clear_weather_time_ratio_summary.csv", index=False, encoding="utf-8-sig")
        if not clear_summary.empty:
            clear_time_ratio = clear_summary.set_index("시간대")["맑음내사고비율_pct"].sort_values(ascending=False)
            save_bar_chart(
                clear_time_ratio,
                "맑은 날 내부 시간대별 사고건수 비율",
                "시간대",
                "맑은 날 내부 비율(%)",
                FIGURE_DIR / "clear_weather_time_ratio.png",
                rotation=45,
            )
        pbar.set_postfix_str("맑음 내부 비율 분석 저장")
        pbar.update(1)

        time_risk = weather.groupby("시간대")["위험점수"].sum().sort_values(ascending=False)
        time_risk_ratio = pct(time_risk).sort_values(ascending=False)
        save_bar_chart(
            time_risk,
            "시간대별 위험점수 합계",
            "시간대",
            "위험점수",
            FIGURE_DIR / "time_risk.png",
            rotation=45,
        )
        save_bar_chart(
            time_risk_ratio,
            "시간대별 위험점수 비율",
            "시간대",
            "비율(%)",
            FIGURE_DIR / "time_risk_ratio.png",
            rotation=45,
        )
        pbar.set_postfix_str("시간대 그래프 저장")
        pbar.update(1)

        top10 = accident.sort_values(by="위험점수", ascending=False).head(10).copy()
        top10["지역라벨"] = top10["사고다발지역시도시군구"].astype(str) + " / " + top10["사고지역위치명"].astype(str)
        save_horizontal_bar_chart(
            top10.set_index("지역라벨")["위험점수"],
            "사고다발지역 위험점수 상위 10개",
            "위험점수",
            "지역",
            FIGURE_DIR / "top10_accident_risk.png",
        )
        pbar.set_postfix_str("top10 그래프 저장")
        pbar.update(1)

        pbar.set_postfix_str("그래프 생성 완료")
        pbar.update(1)

    print("그래프 저장 완료")
    print("저장 폴더:", FIGURE_DIR)
    print("요약표 저장 폴더:", TABLE_DIR)
    return {
        "weather_ratio_summary": weather_summary,
        "clear_weather_time_ratio_summary": clear_summary,
    }


if __name__ == "__main__":
    plot_risk_analysis()
