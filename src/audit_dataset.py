from pathlib import Path
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "accident_hotspot"
EXTRA_DIR = PROJECT_ROOT / "data" / "raw" / "accident_extra"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"


def read_csv_any(path: Path) -> pd.DataFrame:
    last_error = None
    for encoding in ("utf-8-sig", "cp949", "utf-8"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except Exception as exc:
            last_error = exc
    raise last_error


def collect_raw_files() -> list[Path]:
    files = []
    for folder in (RAW_DIR, EXTRA_DIR):
        if folder.exists():
            files.extend(sorted(folder.glob("*.csv")))
    unique = []
    seen = set()
    for path in files:
        resolved = path.resolve()
        if resolved not in seen:
            unique.append(path)
            seen.add(resolved)
    return unique


def audit_dataset() -> pd.DataFrame:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    raw_total = 0
    raw_files = collect_raw_files()
    for path in raw_files:
        df = read_csv_any(path)
        raw_total += len(df)
        rows.append({"구분": "원본CSV", "파일명": path.name, "행수": len(df), "비고": "사고다발지역 원본"})

    for name in ["accident_clean.csv", "accident_final.csv", "risk_features.csv", "final_risk_table.csv", "live_risk_table.csv"]:
        path = PROCESSED_DIR / name
        if path.exists():
            df = read_csv_any(path)
            rows.append({"구분": "처리결과", "파일명": name, "행수": len(df), "비고": "전체 원본 기반 생성"})

    raw_df = pd.concat([read_csv_any(path) for path in raw_files], ignore_index=True) if raw_files else pd.DataFrame()
    if not raw_df.empty:
        for col in ["사고유형구분", "사고연도", "제공기관명", "데이터기준일자"]:
            if col in raw_df.columns:
                summary = raw_df[col].astype(str).value_counts().reset_index()
                summary.columns = [col, "행수"]
                summary.to_csv(TABLE_DIR / f"data_audit_{col}.csv", index=False, encoding="utf-8-sig")

    result = pd.DataFrame(rows)
    result.to_csv(TABLE_DIR / "data_coverage_summary.csv", index=False, encoding="utf-8-sig")
    with open(TABLE_DIR / "data_coverage_summary.txt", "w", encoding="utf-8-sig") as f:
        f.write("RoadSafe 데이터 적용 범위\n")
        f.write("=" * 40 + "\n")
        f.write(f"원본 CSV 파일 수: {len(raw_files)}\n")
        f.write(f"원본 행 수: {raw_total}\n")
        for _, row in result.iterrows():
            f.write(f"- {row['구분']} / {row['파일명']} / {row['행수']}행 / {row['비고']}\n")
    print(result)
    return result


if __name__ == "__main__":
    audit_dataset()
