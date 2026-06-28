# FishCheck 프로젝트 설정

**주요목적**: 수산시장 생선 사기 예방 — 사진 한 장으로 어종을 판별하는 서비스
**대상 어종**: 광어 / 가자미(도다리 포함) — 2종 운영 중 (방어·부시리 제외)
**스택**: Python 3.11 · PyTorch · YOLOv8s (Ultralytics) · Streamlit · Hugging Face Hub
**배포**: Streamlit Cloud (GitHub `master` 브랜치 자동 배포)
**모델**: YOLOv8s Object Detection 2-class, 입력 640×640, 가중치 `best.pt`
**데이터셋**: Roboflow `50seoks-workspace/fishcheck-jqum0` v2 (442장 + 3배 증강)
**학습**: Google Colab 또는 로컬 GPU → `notebooks/train_fishcheck.ipynb`
**가중치 저장**: Hugging Face Hub (학습 완료 후 `HF_REPO_ID` 환경변수로 기록, Streamlit Cloud Secrets에도 설정)
**데이터 원칙**: 통생선(살아있는) 상태 → 회뜨기·손질·낚시대 등 제외
