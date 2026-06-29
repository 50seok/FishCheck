"""
YOLOv8 + EfficientNetB0 2단계 파이프라인 (src/model.py 와 완전 독립)

Stage 1: YOLOv8  — 어류 위치 탐지 + bbox 크롭
Stage 2: EfficientNetB0 — 크롭 이미지 정밀 분류

사용 전 준비:
  1. YOLO 크롭 이미지 생성: python tools/make_effnet_crops.py
  2. EfficientNet 학습 후 models/effnet.pt 저장 및 HF Hub 업로드
  3. app.py 에서 model_v2.predict_v2 로 교체
"""
import os
from pathlib import Path

import numpy as np
import streamlit as st
import torch
import torch.nn as nn
import torchvision.models as tv_models
import torchvision.transforms as T
from PIL import Image
from ultralytics import YOLO

# ── 경로 ──────────────────────────────────────────────────────────────────────
YOLO_PATH   = "models/best.pt"
EFFNET_PATH = "models/effnet.pt"
HF_REPO_ID  = os.getenv("HF_REPO_ID", "")

# ── 도메인 상수 (model.py 와 중복 — 의도적 독립 유지) ──────────────────────
SKIP_CLASSES = {"bangeo", "bushiri"}

CLASSES = ["gajami", "gwangeo"]   # EfficientNet 출력 순서 (학습 시 고정)

CLASS_KO = {
    "gajami" : "가자미/도다리",
    "gwangeo": "광어",
}

FISH_INFO = {
    "gajami": {
        "학명": "Pleuronichthys cornutus",
        "특징": "몸이 납작하고 눈이 오른쪽. 입이 작고 체형이 둥글다.",
        "구별포인트": "광어보다 입이 작고 눈 방향이 오른쪽 (좌광우도).",
        "주의": "광어와 혼동 주의 — 눈 방향과 입 크기로 구분",
    },
    "gwangeo": {
        "학명": "Paralichthys olivaceus",
        "특징": "눈이 왼쪽에 몰려 있음. 입이 크고 이빨이 날카롭다.",
        "구별포인트": "눈 방향이 왼쪽 (좌광우도). 도다리보다 입이 큼.",
        "주의": "도다리·가자미와 혼동 주의 — 눈 방향과 입 크기로 구분",
    },
}

MIN_ASPECT = 1.3   # 납작한 어류 최소 가로/세로 비율
YOLO_CONF  = 0.40  # Stage 1은 관대하게 — Stage 2 에서 정밀 판별
EFFNET_CONF = 0.70 # EfficientNet 최소 신뢰도


# ── Stage 1: YOLO 탐지 ────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="[v2] YOLO 모델 로딩 중...")
def load_yolo() -> YOLO:
    if not Path(YOLO_PATH).exists():
        if not HF_REPO_ID:
            raise FileNotFoundError(f"{YOLO_PATH} 없음. HF_REPO_ID 를 설정하세요.")
        from huggingface_hub import hf_hub_download
        Path(YOLO_PATH).parent.mkdir(parents=True, exist_ok=True)
        hf_hub_download(repo_id=HF_REPO_ID, filename="best.pt", local_dir="models")
    return YOLO(YOLO_PATH)


# ── Stage 2: EfficientNet 분류 ────────────────────────────────────────────────
@st.cache_resource(show_spinner="[v2] EfficientNet 모델 로딩 중...")
def load_effnet() -> nn.Module:
    if not Path(EFFNET_PATH).exists():
        if not HF_REPO_ID:
            raise FileNotFoundError(f"{EFFNET_PATH} 없음. 학습 후 HF Hub에 업로드하세요.")
        from huggingface_hub import hf_hub_download
        Path(EFFNET_PATH).parent.mkdir(parents=True, exist_ok=True)
        hf_hub_download(repo_id=HF_REPO_ID, filename="effnet.pt", local_dir="models")

    model = tv_models.efficientnet_b0(weights=None)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, len(CLASSES))
    model.load_state_dict(torch.load(EFFNET_PATH, map_location="cpu"))
    model.eval()
    return model


_effnet_transform = T.Compose([
    T.Resize((224, 224)),
    T.ToTensor(),
    T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])


def _crop(img: Image.Image, xyxy) -> Image.Image:
    x1, y1, x2, y2 = (int(v) for v in xyxy)
    # 크롭 영역을 10% 여백 추가 (눈·입 등 특징 보존)
    w, h = img.size
    pad_x = int((x2 - x1) * 0.10)
    pad_y = int((y2 - y1) * 0.10)
    return img.crop((
        max(0, x1 - pad_x), max(0, y1 - pad_y),
        min(w, x2 + pad_x), min(h, y2 + pad_y),
    ))


def _classify(crop: Image.Image, effnet: nn.Module) -> dict:
    tensor = _effnet_transform(crop.convert("RGB")).unsqueeze(0)
    with torch.no_grad():
        logits = effnet(tensor)[0]
        probs  = torch.softmax(logits, dim=0).tolist()
    return {CLASSES[i]: probs[i] for i in range(len(CLASSES))}


# ── 공개 인터페이스 ────────────────────────────────────────────────────────────
def predict_v2(img: Image.Image) -> dict:
    """
    2단계 파이프라인. 반환 형식은 src/model.py 의 predict() 와 동일.
    app.py 에서 predict_v2 로 교체만 하면 동작.
    """
    yolo   = load_yolo()
    effnet = load_effnet()

    # Stage 1: YOLO 탐지
    yolo_result = yolo(img, verbose=False, conf=YOLO_CONF)[0]

    if yolo_result.boxes is None or len(yolo_result.boxes) == 0:
        return _not_detected()

    # 유효 박스 필터 (skip class + 종횡비)
    candidates = []
    for b in yolo_result.boxes:
        cls_name = yolo_result.names[int(b.cls[0])]
        if cls_name in SKIP_CLASSES:
            continue
        x1, y1, x2, y2 = b.xyxy[0]
        if float((x2 - x1) / (y2 - y1 + 1e-6)) < MIN_ASPECT:
            continue
        candidates.append(b)

    if not candidates:
        return _not_detected()

    # Stage 2: EfficientNet — 가장 큰 bbox 기준으로 분류
    best_box = max(candidates, key=lambda b: float(
        (b.xyxy[0][2] - b.xyxy[0][0]) * (b.xyxy[0][3] - b.xyxy[0][1])
    ))
    crop       = _crop(img, best_box.xyxy[0])
    class_prob = _classify(crop, effnet)

    best_class = max(class_prob, key=class_prob.get)
    confidence = class_prob[best_class]

    if confidence < EFFNET_CONF:
        return _not_detected()

    class_ko = CLASS_KO.get(best_class, best_class)
    top3 = [
        {"class_en": cls, "class_ko": CLASS_KO.get(cls, cls), "confidence": prob}
        for cls, prob in sorted(class_prob.items(), key=lambda x: x[1], reverse=True)
    ]

    return {
        "detected"       : True,
        "class_en"       : best_class,
        "class_ko"       : class_ko,
        "confidence"     : confidence,
        "top3"           : top3,
        "annotated_image": yolo_result.plot(),
    }


def _not_detected() -> dict:
    return {"detected": False, "class_en": None, "class_ko": None, "confidence": 0.0, "top3": []}
