from pathlib import Path
import pandas as pd
from tqdm import tqdm


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"

FINAL_RISK_PATH = PROCESSED_DIR / "final_risk_table.csv"
LIVE_RISK_PATH = PROCESSED_DIR / "live_risk_table.csv"
MODEL_RESULT_PATH = TABLE_DIR / "model_result.csv"
FEATURE_IMPORTANCE_PATH = TABLE_DIR / "feature_importance.csv"
CLASS_COUNT_PATH = TABLE_DIR / "class_distribution.csv"
CONFUSION_RATIO_PATH = TABLE_DIR / "confusion_matrix_ratio.csv"
EVAL_NOTE_PATH = TABLE_DIR / "model_evaluation_note.txt"

TOP_STATIC_PATH = TABLE_DIR / "top10_static_risk.csv"
TOP_LIVE_PATH = TABLE_DIR / "top10_live_risk.csv"
SUMMARY_PATH = TABLE_DIR / "project_summary.txt"


def find_first_column(df, candidates):
    for col in candidates:
        if col in df.columns:
            return col
    return None


def make_project_summary():
    print("\n[make_project_summary] 시작")

    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    summary_lines = []

    with tqdm(total=7, desc="프로젝트 결과 요약", ncols=100) as pbar:
        if FINAL_RISK_PATH.exists():
            static_df = pd.read_csv(FINAL_RISK_PATH, encoding="utf-8-sig")
            static_df.columns = static_df.columns.str.strip()

            static_location_col = find_first_column(static_df, ["사고지역위치명", "사고지점명", "location"])
            static_score_col = find_first_column(static_df, ["정적위험점수", "위험점수", "score"])
            static_grade_col = find_first_column(static_df, ["위험등급"])
            static_time_col = find_first_column(static_df, ["주의시간대"])
            static_weather_col = find_first_column(static_df, ["주의기상상태"])
            static_msg_col = find_first_column(static_df, ["대표경고문구"])

            if static_score_col is not None:
                top_static = static_df.sort_values(by=static_score_col, ascending=False).head(10).copy()
                save_cols = [
                    col for col in [
                        "zone_id",
                        static_location_col,
                        static_score_col,
                        static_grade_col,
                        static_time_col,
                        static_weather_col,
                        static_msg_col,
                    ] if col is not None and col in top_static.columns
                ]
                top_static[save_cols].to_csv(TOP_STATIC_PATH, index=False, encoding="utf-8-sig")

                summary_lines.append("[정적 위험구간 상위 10개]")
                for _, row in top_static.iterrows():
                    loc = row[static_location_col] if static_location_col else "위치정보없음"
                    score = row[static_score_col]
                    grade = row[static_grade_col] if static_grade_col else "등급없음"
                    summary_lines.append(f"- {loc} | 점수: {score} | 등급: {grade}")
            else:
                summary_lines.append("[정적 위험도] 점수 컬럼을 찾지 못했습니다.")
        else:
            summary_lines.append("[정적 위험도] final_risk_table.csv 파일이 없습니다.")
        pbar.set_postfix_str("정적 위험도 요약 완료")
        pbar.update(1)

        if LIVE_RISK_PATH.exists():
            live_df = pd.read_csv(LIVE_RISK_PATH, encoding="utf-8-sig")
            live_df.columns = live_df.columns.str.strip()

            live_location_col = find_first_column(live_df, ["사고지역위치명", "사고지점명", "location"])
            live_score_col = find_first_column(live_df, ["실시간위험점수", "실시간위험도", "live_risk_score", "정적위험점수"])
            live_grade_col = find_first_column(live_df, ["실시간위험등급", "위험등급"])
            live_weather_col = find_first_column(live_df, ["current_weather", "현재날씨", "기상상태"])

            if live_score_col is not None:
                top_live = live_df.sort_values(by=live_score_col, ascending=False).head(10).copy()
                save_cols = [
                    col for col in [
                        "zone_id",
                        live_location_col,
                        live_score_col,
                        live_grade_col,
                        live_weather_col,
                    ] if col is not None and col in top_live.columns
                ]
                top_live[save_cols].to_csv(TOP_LIVE_PATH, index=False, encoding="utf-8-sig")

                summary_lines.append("\n[실시간 위험구간 상위 10개]")
                for _, row in top_live.iterrows():
                    loc = row[live_location_col] if live_location_col else "위치정보없음"
                    score = row[live_score_col]
                    grade = row[live_grade_col] if live_grade_col else "등급없음"
                    weather = row[live_weather_col] if live_weather_col else "날씨정보없음"
                    summary_lines.append(f"- {loc} | 점수: {score} | 등급: {grade} | 날씨: {weather}")
            else:
                summary_lines.append("\n[실시간 위험도] 점수 컬럼을 찾지 못했습니다.")
        else:
            summary_lines.append("\n[실시간 위험도] live_risk_table.csv 파일이 없습니다.")
        pbar.set_postfix_str("실시간 위험도 요약 완료")
        pbar.update(1)

        if MODEL_RESULT_PATH.exists():
            model_df = pd.read_csv(MODEL_RESULT_PATH, encoding="utf-8-sig")
            model_df.columns = model_df.columns.str.strip()
            if not model_df.empty:
                best_row = model_df.iloc[0]
                summary_lines.append("\n[최고 성능 모델]")
                summary_lines.append(f"- 모델명: {best_row['model']}")
                summary_lines.append(f"- 정확도: {best_row['accuracy']}")
                summary_lines.append(f"- weighted_f1: {best_row['weighted_f1']}")
                summary_lines.append(f"- macro_f1: {best_row['macro_f1']}")
                if 'balanced_accuracy' in best_row.index:
                    summary_lines.append(f"- balanced_accuracy: {best_row['balanced_accuracy']}")
            else:
                summary_lines.append("\n[모델 성능] model_result.csv가 비어 있습니다.")
        else:
            summary_lines.append("\n[모델 성능] model_result.csv 파일이 없습니다.")
        pbar.set_postfix_str("모델 성능 요약 완료")
        pbar.update(1)

        if FEATURE_IMPORTANCE_PATH.exists():
            feature_df = pd.read_csv(FEATURE_IMPORTANCE_PATH, encoding="utf-8-sig")
            feature_df.columns = feature_df.columns.str.strip()
            if not feature_df.empty and "feature" in feature_df.columns and "importance" in feature_df.columns:
                top_features = feature_df.sort_values(by="importance", ascending=False).head(5)
                summary_lines.append("\n[중요 feature 상위 5개]")
                for _, row in top_features.iterrows():
                    summary_lines.append(f"- {row['feature']} : {round(row['importance'], 4)}")
            else:
                summary_lines.append("\n[중요 feature] feature_importance.csv가 비어 있습니다.")
        else:
            summary_lines.append("\n[중요 feature] feature_importance.csv 파일이 없습니다.")
        pbar.set_postfix_str("중요 feature 요약 완료")
        pbar.update(1)

        if CLASS_COUNT_PATH.exists():
            class_df = pd.read_csv(CLASS_COUNT_PATH, encoding="utf-8-sig")
            class_df.columns = class_df.columns.str.strip()
            total_df = class_df[class_df["split"] == "total"].copy() if "split" in class_df.columns else class_df.copy()
            if not total_df.empty:
                summary_lines.append("\n[전체 등급별 데이터 개수]")
                for _, row in total_df.iterrows():
                    summary_lines.append(f"- {row['위험등급']} : {int(row['개수'])}개 ({row['비율(%)']}%)")
            else:
                summary_lines.append("\n[등급별 데이터 개수] class_distribution.csv가 비어 있습니다.")
        else:
            summary_lines.append("\n[등급별 데이터 개수] class_distribution.csv 파일이 없습니다.")
        pbar.set_postfix_str("등급별 개수 요약 완료")
        pbar.update(1)

        if CONFUSION_RATIO_PATH.exists():
            cm_ratio_df = pd.read_csv(CONFUSION_RATIO_PATH, encoding="utf-8-sig", index_col=0)
            summary_lines.append("\n[혼동행렬 해석 요약]")
            for idx in cm_ratio_df.index:
                row = cm_ratio_df.loc[idx].astype(float)
                best_col = row.idxmax()
                best_val = row.max()
                actual_label = str(idx).replace("실제_", "")
                pred_label = str(best_col).replace("예측_", "")
                summary_lines.append(f"- 실제 {actual_label} 데이터는 예측 {pred_label}로 {best_val}% 가장 많이 분류되었습니다.")
        else:
            summary_lines.append("\n[혼동행렬 해석] confusion_matrix_ratio.csv 파일이 없습니다.")

        if EVAL_NOTE_PATH.exists():
            note_text = Path(EVAL_NOTE_PATH).read_text(encoding="utf-8-sig")
            summary_lines.append("\n[모델 해석 주의사항]")
            for line in note_text.splitlines():
                if line.strip() and not line.startswith("["):
                    summary_lines.append(f"- {line.strip()}")
        pbar.set_postfix_str("혼동행렬 해석 요약 완료")
        pbar.update(1)

        with open(SUMMARY_PATH, "w", encoding="utf-8-sig") as f:
            f.write("교통사고 위험도 분석 프로젝트 결과 요약\n")
            f.write("=" * 50 + "\n\n")
            for line in summary_lines:
                f.write(line + "\n")

        print("\n=== make_project_summary 완료 ===")
        print("저장 위치:")
        print(f"- 정적 위험구간 TOP10: {TOP_STATIC_PATH}")
        print(f"- 실시간 위험구간 TOP10: {TOP_LIVE_PATH}")
        print(f"- 프로젝트 요약 txt: {SUMMARY_PATH}")

        pbar.set_postfix_str("완료")
        pbar.update(1)


if __name__ == "__main__":
    make_project_summary()
