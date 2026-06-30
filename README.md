# 🐟 FishCheck — 수산시장 생선 판별기

> 수산시장에서 광어·가자미 혼동으로 인한 사기를 막기 위해 만든 AI 판별 서비스입니다.  
> **사진 한 장**으로 어종을 즉시 판별합니다.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://fishcheck.streamlit.app)

---

## 왜 만들었나요?

수산시장에서 저렴한 **광어**를 비싼 **가자미(도다리)** 로 속여 파는 사례가 있습니다.  
두 어종은 외형이 비슷해 일반인이 구분하기 어렵습니다.  
FishCheck는 눈 위치를 분석하는 **좌광우도(左廣右道) 원칙**을 AI로 구현해 누구나 쉽게 판별할 수 있게 합니다.

> **좌광우도**: 생선을 배가 아래를 향하게 놓았을 때 눈이 **왼쪽 → 광어**, **오른쪽 → 가자미/도다리**

---

## 기능

| 기능 | 설명 |
|---|---|
| 📁 사진 업로드 | JPG · PNG · WebP 이미지 업로드 후 자동 판별 |
| 📷 카메라 촬영 | 모바일에서 직접 촬영 후 즉시 판별 |
| 🔍 어종 판별 | 광어 / 가자미(도다리) 2종 판별 |
| 📊 신뢰도 표시 | 판별 신뢰도를 % 로 표시 (녹색/주황/빨강) |
| 🎯 바운딩 박스 | 탐지된 부위를 박스로 시각화 |
| 🚫 이미지 검증 | 일러스트·그림·스크린샷 자동 차단 (CLIP) |

---

## 판별 가능 어종

### 광어 (넙치)
- **학명**: *Paralichthys olivaceus*
- **특징**: 눈이 왼쪽에 몰려 있음. 입이 크고 이빨이 날카로움
- **구별 포인트**: 눈 방향이 **왼쪽** (좌광우도)

### 가자미 / 도다리
- **학명**: *Pleuronichthys cornutus*
- **특징**: 몸이 납작하고 눈이 오른쪽. 입이 작고 체형이 둥근 편
- **구별 포인트**: 눈 방향이 **오른쪽** (좌광우도)

> ⚠️ **통 생선(생물) 상태에서만 정확합니다.** 손질·조리된 생선은 판별이 어렵습니다.

---

## 동작 원리

```
사진 입력
   │
   ▼
[CLIP] 실제 사진 여부 검증
   │ 일러스트/그림이면 → 차단
   ▼
[YOLOv8s] 생선 탐지
   │
   ├─ 눈(head_eye) + 바디 동시 검출
   │      → 눈 X좌표로 좌광우도 판정 (왼쪽=광어 / 오른쪽=가자미)
   │
   └─ 바디만 검출 (신뢰도 70% 이상)
          → 바디 클래스로 판정
   │
   ▼
신뢰도 60% 미만 → 재촬영 안내
신뢰도 60~70%  → 결과 + 낮은 신뢰도 경고
신뢰도 70% 이상 → 정상 결과 출력
```

---

## 기술 스택

| 분류 | 기술 |
|---|---|
| **AI 모델** | YOLOv8s (Ultralytics 8.4.80) — Object Detection |
| **이미지 검증** | CLIP (openai/clip-vit-base-patch32) |
| **딥러닝 프레임워크** | PyTorch |
| **서비스 UI** | Streamlit |
| **모델 저장소** | Hugging Face Hub |
| **데이터셋 관리** | Roboflow |
| **학습 환경** | Google Colab (T4 GPU) |
| **배포** | Streamlit Cloud (GitHub master 자동 배포) |
| **언어** | Python 3.11 |

---

## 모델 정보

| 항목 | 내용 |
|---|---|
| 아키텍처 | YOLOv8s Object Detection |
| 입력 크기 | 640 × 640 |
| 클래스 수 | 4 (gwangeo, gajami, gwangeo_head_eye, gajami_head_eye) |
| 데이터셋 | Roboflow FishCheck v3 — 442장 + 3배 증강 |
| 가중치 | Hugging Face Hub (`50seok/fishcheck-model`) |

---

## 프로젝트 구조

```
FishCheck/
├── app.py                  # Streamlit 메인 앱
├── requirements.txt        # 의존성
├── packages.txt            # 시스템 패키지
├── src/
│   └── model.py            # YOLOv8 추론 + CLIP 검증 파이프라인
├── notebooks/
│   └── train_fishcheck.ipynb  # 모델 학습 노트북 (Colab용)
├── models/                 # best.pt 저장 위치 (자동 다운로드)
├── data/                   # 학습 데이터셋
└── tools/                  # 분석 도구
```

---

## 로컬 실행

```bash
# 1. 저장소 클론
git clone https://github.com/50seok/FishCheck.git
cd FishCheck

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경변수 설정 (.env 파일 생성)
echo "HF_REPO_ID=50seok/fishcheck-model" > .env

# 4. 앱 실행
streamlit run app.py
```

---

## 모델 재학습

`notebooks/train_fishcheck.ipynb` 를 Google Colab에서 실행합니다.

1. 런타임 → T4 GPU 선택
2. Section 2에서 Roboflow API 키 입력
3. 전체 실행 (Ctrl+F9)
4. 학습 완료 후 Section 7에서 `best.pt` → Hugging Face Hub 업로드

---

## 주의사항

- **통 생선(생물) 상태**에서만 정확합니다
- 회뜨기·손질·조리된 생선은 판별 불가
- 현재 광어 / 가자미(도다리) **2종만** 지원합니다
- 참고용 서비스이며, 최종 판단은 전문가에게 문의하세요
