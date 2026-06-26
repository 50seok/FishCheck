# FishCheck — 프로젝트 STATUS

**마지막 갱신**: 2026-06-26

---

## 인프라

| 항목 | 상태 | 비고 |
|---|---|---|
| GitHub 레포 | ✅ | github.com/50seok/FishCheck (public) |
| Streamlit Cloud | 🔲 대기 | 학습 완료 후 연결 |
| Hugging Face Hub | 🔲 대기 | 모델 학습 후 업로드 |
| Google Colab | 🔲 대기 | notebooks/train_fishcheck.ipynb 실행 필요 |

---

## 마지막 머지 PR

_없음 (초기화 단계)_

---

## 다음 작업

### P0 (필수 — 지금 바로)
- [ ] 어종별 이미지 수집 (`data/collection_guide.md` 참고, 각 200장 목표)
- [ ] Google Colab에서 `notebooks/train_fishcheck.ipynb` 실행 → 모델 학습
- [ ] 학습된 `fishcheck_model.h5` → Hugging Face Hub 업로드

### P1 (모델 학습 후)
- [ ] Hugging Face Hub `repo_id` → `CLAUDE.md` 및 `src/model.py`에 기록
- [ ] `streamlit run app.py` 로컬 테스트
- [ ] Streamlit Cloud 앱 등록 (GitHub 연동)

### P2 (배포 후)
- [ ] 모바일 카메라 입력 테스트
- [ ] 정확도 개선 (데이터 추가 수집, Fine-tuning 재실행)

---

## 알려진 이슈

| # | 내용 | 상태 |
|---|---|---|
| - | 모델 미학습 상태 — HF Hub 연결 전 앱 실행 불가 | 진행중 |
