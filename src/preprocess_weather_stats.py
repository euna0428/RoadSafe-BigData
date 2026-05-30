from pathlib import Path
import pandas as pd
from tqdm import tqdm


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "weather_accident_stats"
RAW_FILENAME = "한국도로교통공단_시간대별 기상상태별 교통사고 통계_20241231.csv"
RAW_PATH = RAW_DIR / RAW_FILENAME
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "weather_stats_clean.csv"


def resolve_raw_csv(raw_dir: Path, expected_path: Path) -> Path:
    """한글 파일명이 압축/해제 과정에서 깨져도 raw 폴더 안의 CSV를 자동으로 찾는다."""
    if expected_path.exists():
        return expected_path

    csv_files = sorted(raw_dir.glob("*.csv"))
    if len(csv_files) == 1:
        print(f"[preprocess_weather_stats] 지정 파일명을 찾지 못해 폴더 내 CSV를 사용합니다: {csv_files[0].name}")
        return csv_files[0]

    if len(csv_files) > 1:
        raise FileNotFoundError(
            "기상상태별 사고 통계 원본 CSV 파일명이 일치하지 않고, 폴더 안에 CSV가 여러 개 있습니다.\n"
            f"기대 파일: {expected_path}\n"
            f"현재 CSV 목록: {[p.name for p in csv_files]}\n"
            "해결: 사용할 기상 통계 파일명을 '한국도로교통공단_시간대별 기상상태별 교통사고 통계_20241231.csv'로 변경하거나, "
            "data/raw/weather_accident_stats 폴더에 CSV 파일을 1개만 남겨주세요."
        )

    raise FileNotFoundError(
        "기상상태별 사고 통계 원본 CSV 파일을 찾을 수 없습니다.\n"
        f"기대 위치: {expected_path}\n"
        "해결: 한국도로교통공단 시간대별 기상상태별 교통사고 통계 CSV를 data/raw/weather_accident_stats 폴더에 넣어주세요."
    )


def read_csv_with_fallback(path: Path) -> pd.DataFrame:
    """공공데이터 CSV 인코딩이 cp949/utf-8-sig 중 무엇이든 읽을 수 있게 처리한다."""
    last_error = None
    for encoding in ("cp949", "utf-8-sig", "utf-8"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
    raise last_error


def preprocess_weather_stats():
    print("\n[preprocess_weather_stats] 시작")

    raw_path = resolve_raw_csv(RAW_DIR, RAW_PATH)

    with tqdm(total=7, desc="날씨 통계 전처리", ncols=100) as pbar:
        df = read_csv_with_fallback(raw_path)
        pbar.set_postfix_str("CSV 읽기 완료")
        pbar.update(1)

        df.columns = df.columns.str.strip()
        pbar.set_postfix_str("컬럼명 정리")
        pbar.update(1)

        num_cols = ["사고건수", "사망자수", "중상자수", "경상자수", "부상신고자수"]
        missing_cols = [col for col in num_cols if col not in df.columns]
        if missing_cols:
            raise KeyError(
                "기상 통계 데이터에 필요한 컬럼이 없습니다.\n"
                f"누락 컬럼: {missing_cols}\n"
                f"현재 컬럼: {list(df.columns)}"
            )

        for col in tqdm(num_cols, desc="숫자형 변환", leave=False, ncols=100):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        pbar.set_postfix_str("숫자형 변환 완료")
        pbar.update(1)

        missing = df.isnull().sum()
        pbar.set_postfix_str("결측치 확인")
        pbar.update(1)

        df[num_cols] = df[num_cols].fillna(0)
        pbar.set_postfix_str("결측 0 처리")
        pbar.update(1)

        df["위험점수"] = (
            df["사고건수"] * 1 +
            df["사망자수"] * 10 +
            df["중상자수"] * 5 +
            df["경상자수"] * 2 +
            df["부상신고자수"] * 1
        )
        pbar.set_postfix_str("위험점수 생성")
        pbar.update(1)

        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
        pbar.set_postfix_str("CSV 저장 완료")
        pbar.update(1)

    print("\n=== 날씨 통계 전처리 완료 ===")
    print("사용 원본:", raw_path)
    print("행 개수:", len(df))
    print("저장 위치:", OUTPUT_PATH)
    print("\n=== 결측치 개수 ===")
    print(missing)

    return df


if __name__ == "__main__":
    preprocess_weather_stats()
