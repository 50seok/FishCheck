# FishCheck — 프로젝트 STATUS

**마지막 갱신**: 2026-06-28

---

## 인프라

| 항목 | 상태 | 비고 |
|---|---|---|
| GitHub 레포 | ✅ | github.com/50seoks/FishCheck (public) |
| Roboflow 데이터셋 | ✅ | fishcheck-jqum0 v2 · 442장 · 3× 증강 (방어/부시리/광어/가자미) |
| Colab 노트북 | ✅ 준비 | notebooks/train_fishcheck.ipynb (YOLOv8 detection) |
| Hugging Face Hub | 🔲 대기 | 모델 학습 완료 후 업로드 |
| Streamlit Cloud | 🔲 대기 | HF Hub 연동 후 등록 |

---

## 마지막 머지 PR

_없음 (변경사항 미커밋 상태 — 학습 완료 후 일괄 커밋 예정)_

---

## 다음 작업

### P0 (필수 — 지금 바로)
- [ ] **Roboflow에서 문제 이미지 삭제** (bangeo 000011/000014/000016.jpg — 텍스트 오버레이 영상 캡처)
- [ ] 로컬 또는 Colab에서 `notebooks/train_fishcheck.ipynb` 실행 → YOLOv8 재학습
- [ ] 학습된 `best.pt` → Hugging Face Hub 업로드
- [ ] `HF_REPO_ID` → CLAUDE.md 기록

### P1 (모델 학습 후)
- [ ] `streamlit run app.py` 로컬 테스트
- [ ] Streamlit Cloud 앱 등록 (GitHub `master` 연동, Secrets에 `HF_REPO_ID` 설정)
- [ ] 변경된 코드 커밋 & 푸시 (app.py / src/model.py / requirements.txt / notebook 등)

### P2 (배포 후)
- [ ] 모바일 카메라 입력 테스트
- [ ] 정확도 개선 — Roboflow 미어노테이션 276장 추가 레이블링 후 v3 생성 → 재학습

---

## 알려진 이슈

| # | 내용 | 상태 |
|---|---|---|
| 1 | Roboflow bangeo 데이터에 텍스트 오버레이 영상 캡처 3장 포함 | 미삭제 (수동 삭제 필요) |
| 2 | models/best.pt 없음 — 재학습 전 앱 실행 불가 | 재학습 후 해결 |
| 3 | src/preprocess.py TF 시대 잔재 파일 (YOLOv8에서 불필요) | 보류 (삭제해도 무방) |
