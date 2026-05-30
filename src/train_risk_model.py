from pathlib import Path
import pickle

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from tqdm import tqdm
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    classification_report,
    confusion_matrix,
    balanced_accuracy_score,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
FIGURE_DIR = PROJECT_ROOT / "outputs" / "figures"
TABLE_DIR = PROJECT_ROOT / "outputs" / "tables"
MODEL_DIR = PROJECT_ROOT / "outputs" / "models"

FEATURE_PATH = PROCESSED_DIR / "risk_features.csv"
RESULT_PATH = TABLE_DIR / "model_result.csv"
IMPORTANCE_PATH = TABLE_DIR / "feature_importance.csv"
REPORT_PATH = TABLE_DIR / "classification_report.txt"
MODEL_PATH = MODEL_DIR / "best_risk_model.pkl"
CONFUSION_PATH = FIGURE_DIR / "confusion_matrix.png"
CONFUSION_TABLE_PATH = TABLE_DIR / "confusion_matrix.csv"
CONFUSION_RATIO_PATH = TABLE_DIR / "confusion_matrix_ratio.csv"
CLASS_COUNT_PATH = TABLE_DIR / "class_distribution.csv"
EVAL_NOTE_PATH = TABLE_DIR / "model_evaluation_note.txt"

TARGET_COL = "위험등급"

BASE_FEATURES = [
    "사고유형수",
    "사고건수합",
    "사상자수합",
    "사망자수합",
    "중상자수합",
    "경상자수합",
    "부상신고자수합",
]

LABEL_ORDER = ["낮음", "보통", "높음", "매우높음"]

RANDOM_STATE = 42
TEST_SIZE = 0.2


def set_korean_font():
    candidates = [
        "Malgun Gothic",
        "AppleGothic",
        "NanumGothic",
        "Noto Sans CJK KR",
    ]
    available_fonts = {font.name for font in fm.fontManager.ttflist}

    for font_name in candidates:
        if font_name in available_fonts:
            plt.rcParams["font.family"] = font_name
            break

    plt.rcParams["axes.unicode_minus"] = False


def draw_confusion_matrix(cm, labels, save_path):
    plt.figure(figsize=(7, 6))
    plt.imshow(cm, interpolation="nearest", cmap="Blues")
    plt.title("위험등급 분류 Confusion Matrix")
    plt.colorbar()

    ticks = range(len(labels))
    plt.xticks(ticks, labels, rotation=45)
    plt.yticks(ticks, labels)
    plt.xlabel("예측값")
    plt.ylabel("실제값")

    threshold = cm.max() / 2 if cm.size else 0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            plt.text(
                j,
                i,
                format(cm[i, j], "d"),
                ha="center",
                va="center",
                color="white" if cm[i, j] > threshold else "black",
            )

    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()


def make_class_count_df(total_y, train_y, test_y):
    rows = []
    for split_name, series in [("total", total_y), ("train", train_y), ("test", test_y)]:
        counts = series.value_counts().reindex(LABEL_ORDER, fill_value=0)
        total_count = int(counts.sum())
        for label, count in counts.items():
            ratio = round((count / total_count) * 100, 2) if total_count else 0.0
            rows.append(
                {
                    "split": split_name,
                    "위험등급": label,
                    "개수": int(count),
                    "비율(%)": ratio,
                }
            )
    return pd.DataFrame(rows)


def train_risk_model():
    print("\n[train_risk_model] 시작")

    set_korean_font()

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    if not FEATURE_PATH.exists():
        raise FileNotFoundError(f"risk_features.csv 파일이 없습니다: {FEATURE_PATH}")

    with tqdm(total=12, desc="머신러닝 모델 학습", ncols=100, leave=False) as pbar:
        df = pd.read_csv(FEATURE_PATH, encoding="utf-8-sig")
        pbar.set_postfix_str("risk_features 읽기 완료")
        pbar.update(1)

        df.columns = df.columns.str.strip()
        pbar.set_postfix_str("컬럼명 정리")
        pbar.update(1)

        use_features = [col for col in BASE_FEATURES if col in df.columns]

        dropped_constant_cols = []
        for col in use_features[:]:
            if df[col].nunique(dropna=False) <= 1:
                dropped_constant_cols.append(col)
                use_features.remove(col)

        if len(use_features) == 0:
            raise ValueError("학습에 사용할 feature가 없습니다. risk_features.csv 컬럼을 확인해 주세요.")

        pbar.set_postfix_str("feature 선택 완료")
        pbar.update(1)

        model_df = df[use_features + [TARGET_COL]].dropna().copy()
        X = model_df[use_features]
        y = model_df[TARGET_COL]
        pbar.set_postfix_str("학습 데이터 준비")
        pbar.update(1)

        class_counts = y.value_counts()
        stratify_y = y if class_counts.min() >= 2 else None

        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=TEST_SIZE,
            random_state=RANDOM_STATE,
            stratify=stratify_y,
        )
        pbar.set_postfix_str("train/test 분리")
        pbar.update(1)

        class_count_df = make_class_count_df(y, y_train, y_test)
        class_count_df.to_csv(CLASS_COUNT_PATH, index=False, encoding="utf-8-sig")
        pbar.set_postfix_str("등급별 개수 저장")
        pbar.update(1)

        models = {
            "DecisionTree": DecisionTreeClassifier(
                max_depth=5,
                min_samples_leaf=10,
                class_weight="balanced",
                random_state=RANDOM_STATE,
            ),
            "RandomForest": RandomForestClassifier(
                n_estimators=200,
                max_depth=8,
                min_samples_leaf=5,
                class_weight="balanced",
                random_state=RANDOM_STATE,
                n_jobs=-1,
            ),
        }

        result_rows = []
        trained_models = {}

        for model_name, model in models.items():
            model.fit(X_train, y_train)
            pred = model.predict(X_test)

            trained_models[model_name] = model

            result_rows.append(
                {
                    "model": model_name,
                    "accuracy": round(accuracy_score(y_test, pred), 4),
                    "weighted_f1": round(f1_score(y_test, pred, average="weighted", zero_division=0), 4),
                    "macro_f1": round(f1_score(y_test, pred, average="macro", zero_division=0), 4),
                    "balanced_accuracy": round(balanced_accuracy_score(y_test, pred), 4),
                }
            )

        result_df = pd.DataFrame(result_rows).sort_values(
            by=["macro_f1", "balanced_accuracy", "weighted_f1", "accuracy"],
            ascending=False,
        ).reset_index(drop=True)

        result_df.to_csv(RESULT_PATH, index=False, encoding="utf-8-sig")
        pbar.set_postfix_str("모델 성능 저장")
        pbar.update(1)

        best_model_name = result_df.loc[0, "model"]
        best_model = trained_models[best_model_name]
        best_pred = best_model.predict(X_test)
        pbar.set_postfix_str("최적 모델 선택")
        pbar.update(1)

        report_labels = [label for label in LABEL_ORDER if label in y.unique()]
        report_text = classification_report(
            y_test,
            best_pred,
            labels=report_labels,
            target_names=report_labels,
            zero_division=0,
        )

        with open(REPORT_PATH, "w", encoding="utf-8-sig") as f:
            f.write("[사용 feature]\n")
            for col in use_features:
                f.write(f"- {col}\n")

            if dropped_constant_cols:
                f.write("\n[자동 제외된 상수 feature]\n")
                for col in dropped_constant_cols:
                    f.write(f"- {col}\n")

            f.write("\n[등급별 데이터 개수]\n")
            f.write(class_count_df.to_string(index=False))
            f.write("\n\n[Best Model]\n")
            f.write(f"- {best_model_name}\n\n")
            f.write(report_text)

        pbar.set_postfix_str("classification report 저장")
        pbar.update(1)

        cm_labels = [label for label in LABEL_ORDER if label in y_test.unique() or label in best_pred]
        cm = confusion_matrix(y_test, best_pred, labels=cm_labels)

        cm_df = pd.DataFrame(
            cm,
            index=[f"실제_{x}" for x in cm_labels],
            columns=[f"예측_{x}" for x in cm_labels],
        )
        cm_df.to_csv(CONFUSION_TABLE_PATH, encoding="utf-8-sig", index_label="실제값")

        row_sum = cm.sum(axis=1, keepdims=True)
        cm_ratio = pd.DataFrame(
            ((cm / row_sum) * 100).round(2),
            index=[f"실제_{x}" for x in cm_labels],
            columns=[f"예측_{x}" for x in cm_labels],
        ).fillna(0)
        cm_ratio.to_csv(CONFUSION_RATIO_PATH, encoding="utf-8-sig", index_label="실제값")

        draw_confusion_matrix(cm, cm_labels, CONFUSION_PATH)

        if hasattr(best_model, "feature_importances_"):
            importance_df = pd.DataFrame(
                {
                    "feature": use_features,
                    "importance": best_model.feature_importances_,
                }
            ).sort_values(by="importance", ascending=False)
        else:
            importance_df = pd.DataFrame(columns=["feature", "importance"])

        importance_df.to_csv(IMPORTANCE_PATH, index=False, encoding="utf-8-sig")

        with open(MODEL_PATH, "wb") as f:
            pickle.dump(
                {
                    "model_name": best_model_name,
                    "model": best_model,
                    "features": use_features,
                    "label_order": LABEL_ORDER,
                },
                f,
            )

        pbar.set_postfix_str("혼동행렬/중요도/모델 저장")
        pbar.update(1)

        with open(EVAL_NOTE_PATH, "w", encoding="utf-8-sig") as f:
            f.write("[모델 해석 주의사항]\n")
            f.write("1. accuracy가 높아도 등급별 데이터가 불균형하면 소수 등급 성능이 낮을 수 있습니다.\n")
            f.write("2. 이 프로젝트의 위험등급은 사고 통계 기반 점수에서 만들어진 값이므로,\n")
            f.write("   현재 모델은 규칙 기반 위험등급을 얼마나 잘 재현하는지 보는 성격이 강합니다.\n")
            f.write("3. 발표에서는 accuracy보다 macro_f1, balanced_accuracy, confusion matrix를 함께 설명하는 것이 안전합니다.\n")
        pbar.set_postfix_str("평가 주의사항 저장")
        pbar.update(1)

    print("\n=== train_risk_model 완료 ===")
    print("사용 feature:", use_features)

    if dropped_constant_cols:
        print("자동 제외된 상수 feature:", dropped_constant_cols)

    print("최적 모델:", best_model_name)

    print("\n[전체 등급별 데이터 개수]")
    print(class_count_df[class_count_df["split"] == "total"][["위험등급", "개수", "비율(%)"]].to_string(index=False))

    print("\n[테스트용 등급별 데이터 개수]")
    print(class_count_df[class_count_df["split"] == "test"][["위험등급", "개수", "비율(%)"]].to_string(index=False))

    print("\n모델 비교 결과:")
    print(result_df)

    print("\n분류 리포트:")
    print(report_text)

    print("\n혼동행렬:")
    print(cm_df)

    print("\n저장 위치")
    print("- 성능표:", RESULT_PATH)
    print("- 중요도표:", IMPORTANCE_PATH)
    print("- 리포트:", REPORT_PATH)
    print("- 혼동행렬 이미지:", CONFUSION_PATH)
    print("- 혼동행렬 표:", CONFUSION_TABLE_PATH)
    print("- 혼동행렬 비율표:", CONFUSION_RATIO_PATH)
    print("- 등급별 개수표:", CLASS_COUNT_PATH)
    print("- 평가 주의사항:", EVAL_NOTE_PATH)
    print("- 모델 파일:", MODEL_PATH)

    return result_df


if __name__ == "__main__":
    train_risk_model()
