from pathlib import Path
import pandas as pd
from tqdm import tqdm


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "accident_hotspot"
RAW_FILENAME = "전국교통사고다발지역표준데이터.csv"
RAW_PATH = RAW_DIR / RAW_FILENAME
EXTRA_RAW_DIR = PROJECT_ROOT / "data" / "raw" / "accident_extra"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "accident_clean.csv"


def resolve_raw_csvs(raw_dir: Path, expected_path: Path, extra_raw_dir: Path) -> list[Path]:
    main_files: list[Path] = []
    if expected_path.exists():
        main_files.append(expected_path)
    else:
        main_files.extend(sorted(raw_dir.glob("*.csv")))

    extra_files = sorted(extra_raw_dir.glob("*.csv")) if extra_raw_dir.exists() else []
    files: list[Path] = []
    seen: set[Path] = set()
    for file_path in [*main_files, *extra_files]:
        resolved = file_path.resolve()
        if resolved not in seen:
            files.append(file_path)
            seen.add(resolved)

    if not files:
        raise FileNotFoundError(
            "사고 원본 CSV 파일을 찾을 수 없습니다.\n"
            f"기대 위치: {expected_path}\n"
            f"추가 데이터 위치: {extra_raw_dir}\n"
            "해결: 사고 데이터 CSV를 data/raw/accident_hotspot 또는 data/raw/accident_extra 폴더에 넣어주세요."
        )
    return files


def read_csv_with_fallback(path: Path) -> pd.DataFrame:
    last_error = None
    for encoding in ("cp949", "utf-8-sig", "utf-8"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
    raise last_error


def preprocess_accident():
    print("\n[preprocess_accident] 시작")

    raw_paths = resolve_raw_csvs(RAW_DIR, RAW_PATH, EXTRA_RAW_DIR)

    with tqdm(total=8, desc="사고 데이터 전처리", ncols=100) as pbar:
        frames = []
        for raw_path in raw_paths:
            frame = read_csv_with_fallback(raw_path)
            frame["원본파일명"] = raw_path.name
            frames.append(frame)
        df = pd.concat(frames, ignore_index=True)
        pbar.set_postfix_str(f"CSV {len(raw_paths)}개 읽기 완료")
        pbar.update(1)

        df.columns = df.columns.str.strip()
        pbar.set_postfix_str("컬럼명 정리")
        pbar.update(1)

        use_cols = [
            "사고지역관리번호", "사고연도", "사고유형구분", "사고다발지역시도시군구", "사고지역위치명",
            "사고건수", "사상자수", "사망자수", "중상자수", "경상자수", "부상신고자수",
            "위도", "경도", "원본파일명"
        ]
        missing_cols = [col for col in use_cols if col not in df.columns]
        if missing_cols:
            raise KeyError(
                "사고 데이터에 필요한 컬럼이 없습니다.\n"
                f"누락 컬럼: {missing_cols}\n"
                f"현재 컬럼: {list(df.columns)}"
            )
        df = df[use_cols].copy()
        pbar.set_postfix_str("주요 컬럼 선택")
        pbar.update(1)

        num_cols = ["사고건수", "사상자수", "사망자수", "중상자수", "경상자수", "부상신고자수", "위도", "경도"]
        for col in tqdm(num_cols, desc="숫자형 변환", leave=False, ncols=100):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        pbar.set_postfix_str("숫자형 변환 완료")
        pbar.update(1)

        missing = df.isnull().sum()
        pbar.set_postfix_str("결측치 확인")
        pbar.update(1)

        df = df.dropna(subset=["위도", "경도"])
        df = df.drop_duplicates(subset=["사고지역관리번호", "사고유형구분", "사고지역위치명", "위도", "경도"]).reset_index(drop=True)
        pbar.set_postfix_str("위도/경도 결측 제거")
        pbar.update(1)

        fill_cols = ["사고건수", "사상자수", "사망자수", "중상자수", "경상자수", "부상신고자수"]
        df[fill_cols] = df[fill_cols].fillna(0)
        pbar.set_postfix_str("기타 결측 0 처리")
        pbar.update(1)

        df["위험점수"] = (
            df["사고건수"] * 1 +
            df["사망자수"] * 10 +
            df["중상자수"] * 5 +
            df["경상자수"] * 2 +
            df["부상신고자수"] * 1
        )
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
        pbar.set_postfix_str("CSV 저장 완료")
        pbar.update(1)

    print("\n=== 사고 데이터 전처리 완료 ===")
    print("사용 원본:", [path.name for path in raw_paths])
    print("행 개수:", len(df))
    print("저장 위치:", OUTPUT_PATH)
    print("\n=== 결측치 개수 ===")
    print(missing)

    return df


if __name__ == "__main__":
    preprocess_accident()
