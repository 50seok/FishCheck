import os
from pathlib import Path

import cv2
import numpy as np
import streamlit as st
import torch
import torch.nn as nn
import torchvision.models as tv_models
import torchvision.transforms as T
from PIL import Image, ImageFilter
from ultralytics import YOLO

MODEL_PATH  = "models/best.pt"
EFFNET_PATH = "models/effnet.pt"
HF_REPO_ID  = os.getenv("HF_REPO_ID", "")

SKIP_CLASSES = {"bangeo", "bushiri"}

# EfficientNet class order mirrors ImageFolder sorted() on effnet_crops/
EFFNET_CLASSES = ["gajami", "gwangeo"]

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

_EFFNET_TF = T.Compose([
    T.Resize((224, 224)),
    T.ToTensor(),
    T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])


@st.cache_resource(show_spinner="모델 로딩 중... (최초 1회만)")
def load_model() -> YOLO:
    if not Path(MODEL_PATH).exists():
        if not HF_REPO_ID:
            raise FileNotFoundError(
                f"{MODEL_PATH} 없음. HF_REPO_ID 환경변수를 설정하거나 모델 파일을 직접 배치하세요."
            )
        from huggingface_hub import hf_hub_download
        Path(MODEL_PATH).parent.mkdir(parents=True, exist_ok=True)
        hf_hub_download(repo_id=HF_REPO_ID, filename="best.pt", local_dir="models")
    return YOLO(MODEL_PATH)


@st.cache_resource(show_spinner=False)
def load_effnet() -> nn.Module | None:
    if not Path(EFFNET_PATH).exists():
        if not HF_REPO_ID:
            return None
        try:
            from huggingface_hub import hf_hub_download
            Path(EFFNET_PATH).parent.mkdir(parents=True, exist_ok=True)
            hf_hub_download(repo_id=HF_REPO_ID, filename="effnet.pt", local_dir="models")
        except Exception:
            return None
    model = tv_models.efficientnet_b0()
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, len(EFFNET_CLASSES))
    state = torch.load(EFFNET_PATH, map_location="cpu")
    model.load_state_dict(state)
    model.eval()
    return model


def _effnet_classify(effnet: nn.Module, crop: Image.Image) -> tuple[str, float]:
    """EfficientNet으로 크롭 이미지 분류 → (class_en, confidence)"""
    x = _EFFNET_TF(crop.convert("RGB")).unsqueeze(0)
    with torch.no_grad():
        probs = torch.softmax(effnet(x), dim=1)[0]
    idx = int(probs.argmax())
    return EFFNET_CLASSES[idx], float(probs[idx])


def predict(img: Image.Image, use_effnet: bool = True) -> dict:
    yolo   = load_model()
    effnet = load_effnet() if use_effnet else None

    results = yolo(img, verbose=False, conf=0.65)
    result  = results[0]

    if result.boxes is None or len(result.boxes) == 0:
        return {"detected": False, "class_en": None, "class_ko": None, "confidence": 0.0, "top3": []}

    MIN_ASPECT = 1.3
    boxes = []
    for b in result.boxes:
        cls_name = result.names[int(b.cls[0])]
        if cls_name in SKIP_CLASSES:
            continue
        x1, y1, x2, y2 = b.xyxy[0]
        aspect = float((x2 - x1) / (y2 - y1 + 1e-6))
        if aspect < MIN_ASPECT:
            continue
        boxes.append({
            "cls" : int(b.cls[0]),
            "conf": float(b.conf[0]),
            "xyxy": (int(x1), int(y1), int(x2), int(y2)),
        })
    boxes.sort(key=lambda x: x["conf"], reverse=True)

    if not boxes:
        return {"detected": False, "class_en": None, "class_ko": None, "confidence": 0.0, "top3": []}

    best = boxes[0]

    # 2-stage: EfficientNet이 있으면 크롭으로 재분류
    if effnet is not None:
        x1, y1, x2, y2 = best["xyxy"]
        crop = img.crop((x1, y1, x2, y2))
        x = _EFFNET_TF(crop.convert("RGB")).unsqueeze(0)
        with torch.no_grad():
            probs = torch.softmax(effnet(x), dim=1)[0]
        idx        = int(probs.argmax())
        class_en   = EFFNET_CLASSES[idx]
        confidence = float(probs[idx])
        top3 = [
            {"class_en": EFFNET_CLASSES[i], "class_ko": CLASS_KO.get(EFFNET_CLASSES[i], EFFNET_CLASSES[i]), "confidence": float(probs[i])}
            for i in probs.argsort(descending=True).tolist()
        ]
    else:
        class_en   = result.names[best["cls"]]
        confidence = best["conf"]
        seen, top3 = set(), []
        for b in boxes:
            name = result.names[b["cls"]]
            if name not in seen:
                seen.add(name)
                top3.append({"class_en": name, "class_ko": CLASS_KO.get(name, name), "confidence": b["conf"]})
            if len(top3) == 3:
                break

    class_ko = CLASS_KO.get(class_en, class_en)

    # EFF 모드: EfficientNet 결과로 bbox 라벨 재드로잉
    if effnet is not None:
        x1, y1, x2, y2 = best["xyxy"]
        frame = np.array(img.convert("RGB"))[:, :, ::-1].copy()
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
        label = f"{class_en} {confidence:.2f}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 4, y1), (0, 255, 255), -1)
        cv2.putText(frame, label, (x1 + 2, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        annotated = frame
    else:
        annotated = result.plot()

    return {
        "detected"       : True,
        "class_en"       : class_en,
        "class_ko"       : class_ko,
        "confidence"     : confidence,
        "top3"           : top3,
        "annotated_image": annotated,
    }


def is_real_photo(img: Image.Image) -> bool:
    # 1) EXIF 체크 — 카메라 촬영 사진엔 Make/Model/DateTimeOriginal 존재
    CAMERA_TAGS = {271, 272, 306, 36867, 33434}  # Make, Model, DateTime, DateTimeOriginal, ExposureTime
    try:
        exif = img.getexif()
        if exif and any(tag in exif for tag in CAMERA_TAGS):
            return True
    except Exception:
        pass

    # 2) 노이즈 휴리스틱 — 실사는 블러 후에도 grain 잔존
    gray     = img.convert("L").resize((128, 128))
    blurred  = gray.filter(ImageFilter.GaussianBlur(radius=3))
    hf_noise = np.abs(np.array(gray, dtype=np.float32) - np.array(blurred, dtype=np.float32)).mean()
    return hf_noise >= 4.5  # 임계값 상향 (일러스트 오통과 방지)
