from tqdm import tqdm

from src.fetch_koroad_hotspots import fetch_koroad_hotspots
from src.preprocess_accident import preprocess_accident
from src.preprocess_weather_stats import preprocess_weather_stats
from src.make_risk_grade import make_risk_grade
from src.merge_features import build_feature_table
from src.risk_score import make_risk_score
from src.plot_risk_analysis import plot_risk_analysis
from src.make_map import make_risk_map
from src.train_risk_model import train_risk_model
from src.make_project_summary import make_project_summary
from src.audit_dataset import audit_dataset



def main():
    steps = [
        ("사고다발 API 추가 수집", fetch_koroad_hotspots),
        ("사고 데이터 전처리", preprocess_accident),
        ("날씨 데이터 전처리", preprocess_weather_stats),
        ("위험등급 생성", make_risk_grade),
        ("통합 feature 생성", build_feature_table),
        ("위험도 요약 분석", make_risk_score),
        ("그래프 생성", plot_risk_analysis),
        ("지도 생성", make_risk_map),
        ("머신러닝 모델 학습", train_risk_model),
        ("데이터 적용 범위 점검", audit_dataset),
        ("프로젝트 결과 요약", make_project_summary),
    ]

    print("\n=== RoadSafe 전체 분석 파이프라인 시작 ===")

    with tqdm(total=len(steps), desc="전체 파이프라인", ncols=100) as pbar:
        for step_name, step_func in steps:
            print(f"\n>>> 현재 단계: {step_name}")
            step_func()
            pbar.set_postfix_str(step_name)
            pbar.update(1)

    print("\n=== RoadSafe 전체 분석 파이프라인 완료 ===")


if __name__ == "__main__":
    main()
    
