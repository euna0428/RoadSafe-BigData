from pathlib import Path
import pandas as pd
from tqdm import tqdm

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

ACCIDENT_INPUT = PROCESSED_DIR / "accident_clean.csv"
WEATHER_INPUT = PROCESSED_DIR / "weather_stats_clean.csv"
ACCIDENT_OUTPUT = PROCESSED_DIR / "accident_final.csv"
WEATHER_OUTPUT = PROCESSED_DIR / "weather_stats_final.csv"


def _make_grade_df(df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    """위험점수 컬럼을 기준으로 정규화 점수와 위험등급을 생성한다."""
    df = df.copy()
    df.columns = df.columns.astype(str).str.strip()

    score_candidates = [
        "위험점수",
        "risk_score",
        "평균위험점수",
        "최대위험점수",
    ]

    score_col = None
    for col in score_candidates:
        if col in df.columns:
            score_col = col
            break

    if score_col is None:
        raise KeyError(
            f"[{dataset_name}] 위험점수 컬럼이 없습니다. "
            f"현재 컬럼: {list(df.columns)}"
        )

    if score_col != "위험점수":
        df["위험점수"] = df[score_col]

    df["위험점수"] = pd.to_numeric(df["위험점수"], errors="coerce")
    missing_before = int(df["위험점수"].isnull().sum())
    df["위험점수"] = df["위험점수"].fillna(0)

    min_score = float(df["위험점수"].min())
    max_score = float(df["위험점수"].max())

    if max_score == min_score:
        df["정규화위험점수"] = 100.0
    else:
        df["정규화위험점수"] = (
            (df["위험점수"] - min_score) / (max_score - min_score) * 100
        ).round(2)

    def label_risk(score: float) -> str:
        if score <= 25:
            return "낮음"
        elif score <= 50:
            return "보통"
        elif score <= 75:
            return "높음"
        else:
            return "매우높음"

    df["위험등급"] = df["정규화위험점수"].apply(label_risk)

    return df, missing_before



def make_risk_grade():
    print("\n[make_risk_grade] 시작")

    if not ACCIDENT_INPUT.exists():
        raise FileNotFoundError(f"사고 전처리 파일이 없습니다: {ACCIDENT_INPUT}")
    if not WEATHER_INPUT.exists():
        raise FileNotFoundError(f"날씨 전처리 파일이 없습니다: {WEATHER_INPUT}")

    with tqdm(total=6, desc="위험등급 생성", ncols=100) as pbar:
        accident_df = pd.read_csv(ACCIDENT_INPUT, encoding="utf-8-sig")
        weather_df = pd.read_csv(WEATHER_INPUT, encoding="utf-8-sig")
        pbar.set_postfix_str("전처리 CSV 읽기 완료")
        pbar.update(1)

        accident_final, accident_missing = _make_grade_df(accident_df, "accident_clean")
        pbar.set_postfix_str("사고 위험등급 생성 완료")
        pbar.update(1)

        weather_final, weather_missing = _make_grade_df(weather_df, "weather_stats_clean")
        pbar.set_postfix_str("날씨 위험등급 생성 완료")
        pbar.update(1)

        ACCIDENT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        accident_final.to_csv(ACCIDENT_OUTPUT, index=False, encoding="utf-8-sig")
        pbar.set_postfix_str("accident_final 저장 완료")
        pbar.update(1)

        weather_final.to_csv(WEATHER_OUTPUT, index=False, encoding="utf-8-sig")
        pbar.set_postfix_str("weather_stats_final 저장 완료")
        pbar.update(1)

        pbar.set_postfix_str("위험등급 생성 완료")
        pbar.update(1)

    print("\n=== 위험등급 생성 완료 ===")
    print("사고 파일 저장 위치:", ACCIDENT_OUTPUT)
    print("날씨 파일 저장 위치:", WEATHER_OUTPUT)
    print("사고 위험점수 결측치 처리 개수:", accident_missing)
    print("날씨 위험점수 결측치 처리 개수:", weather_missing)

    print("\n=== 사고 위험등급 분포 ===")
    print(accident_final["위험등급"].value_counts().sort_index())

    print("\n=== 날씨 위험등급 분포 ===")
    print(weather_final["위험등급"].value_counts().sort_index())

    return accident_final, weather_final


if __name__ == "__main__":
    make_risk_grade()
