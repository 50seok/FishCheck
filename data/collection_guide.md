# FishCheck 데이터 수집 가이드

## 핵심 원칙

> **반드시 생물(살아있거나 죽은 직후의 통 생선) 상태 이미지만 수집**
> 횟감(잘린 것), 구이, 조림, 튀김 등 가공·조리 형태는 **전량 제외**
> 외형 특징이 변형되어 모델이 오학습하므로 엄격히 제외할 것

## 어종별 검색어 & 목표 수량

| 어종 | 권장 검색어 | 제외 검색어 | 목표 수량 |
|---|---|---|---|
| 광어 | "활광어", "광어 생물", "olive flounder fish whole" | "광어회", "광어 횟감", "광어 손질" | 200장 |
| 도다리 | "도다리 생물", "봄도다리 낚시", "spotted flounder whole" | "도다리 쑥국", "도다리회", "도다리 손질" | 200장 |
| 가자미 | "참가자미 생선", "가자미 생물", "flatfish whole body" | "가자미구이", "가자미조림", "가자미 손질" | 200장 |
| 방어 | "활방어", "방어 생물", "yellowtail whole fish" | "방어회", "방어 횟감", "방어 손질" | 200장 |
| 부시리 | "부시리 낚시", "부시리 생물", "greater amberjack whole" | "부시리회", "부시리 횟감" | 200장 |
| 우럭 | "우럭 생물", "조피볼락 낚시", "Korean rockfish whole" | "우럭매운탕", "우럭구이", "우럭 손질" | 200장 |
| 개볼락 | "개볼락 낚시", "개볼락 생물", "goldeye rockfish" | "개볼락구이", "개볼락조림" | 200장 |

**총 목표: 1,400장 (어종당 200장 × 7종)**
**최소 기준: 어종당 100장 (정확도 저하 감수)**

---

## 이미지 품질 기준

✅ **수집 OK**
- 전체 체형 보임 (머리 ~ 꼬리 ~ 지느러미)
- 배경 단순 (수족관 바닥, 얼음 위, 수산시장 진열대)
- 최소 해상도 200×200px 이상
- 다양한 각도 (위에서, 옆에서, 비스듬히)

❌ **수집 제외**
- 손질된 것 (내장 제거, 머리 제거, 필레)
- 조리된 것 (구이, 조림, 튀김, 찜)
- 횟감으로 잘린 것
- 심하게 뭉개지거나 극단적으로 변색된 것
- 다른 어종과 겹쳐서 구분 불가능한 것

---

## 자동 수집 방법 (icrawler 사용)

### 설치
```bash
pip install icrawler
```

### 어종별 수집 스크립트 예시
```python
from icrawler.builtin import GoogleImageCrawler

species_list = {
    "gwangeo":  ["활광어", "광어 생물", "olive flounder whole"],
    "dodaree":  ["도다리 생물", "봄도다리 낚시", "spotted flounder whole"],
    "gajami":   ["참가자미 생물", "가자미 생선", "flatfish whole body"],
    "bangeo":   ["활방어", "방어 생물", "yellowtail whole fish"],
    "bushiri":  ["부시리 낚시", "부시리 생물", "greater amberjack"],
    "ureok":    ["우럭 생물", "조피볼락 낚시", "Korean rockfish whole"],
    "gaebolak": ["개볼락 낚시", "개볼락 생물", "goldeye rockfish"],
}

for folder, keywords in species_list.items():
    for keyword in keywords:
        crawler = GoogleImageCrawler(storage={"root_dir": f"data/raw/{folder}"})
        crawler.crawl(keyword=keyword, max_num=80)
```

### 실행 방법
```bash
python data/crawl_images.py
```
수집 후 `data/raw/{어종}/` 폴더에 이미지 저장됨

---

## 수동 검수 절차

1. 각 폴더 이미지를 육안으로 훑어보며 불량 이미지 삭제
2. 특히 다음 항목 확인:
   - 조리·가공된 생선 → 삭제
   - 레이블 오류 (광어 폴더에 도다리 이미지 등) → 이동 또는 삭제
   - 해상도 낮거나 흐린 것 → 삭제
3. 검수 후 최종 수량 확인

---

## 학습/검증 분할

| 세트 | 비율 | 용도 |
|---|---|---|
| train | 80% | 모델 학습 |
| val | 20% | 학습 중 성능 평가 |

`notebooks/train_fishcheck.ipynb`의 `ImageDataGenerator`가 자동 분할

---

## 어종 구별 포인트 (수집 시 참고)

| 혼동 쌍 | 구별 핵심 |
|---|---|
| 광어 vs 도다리 | 광어: 눈이 왼쪽·입 큼. 도다리: 눈이 오른쪽·입 작음 |
| 광어 vs 가자미 | 가자미: 더 작고 둥글며 측선이 직선. 광어: 크고 측선 굴곡 |
| 방어 vs 부시리 | 부시리: 꼬리지느러미 노란색 없음, 주둥이 더 둥글. 방어: 옆구리 노란 줄 |
| 우럭 vs 개볼락 | 우럭: 전반적으로 어두운 갈색. 개볼락: 주황빛 반점 뚜렷 |
