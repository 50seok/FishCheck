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

SKIP_CLASSES   = {"bangeo", "bushiri"}
EFFNET_CLASSES = ["gajami", "gwangeo"]

_EFFNET_TF = T.Compose([
    T.Resize((224, 224)),
    T.ToTensor(),
    T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

CLASS_KO = {
    "gajami"          : "가자미/도다리",
    "gwangeo"         : "광어",
    "gajami_head_eye" : "가자미/도다리",
    "gwangeo_head_eye": "광어",
}

_BASE_INFO = {  # noqa: E305
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
FISH_INFO = {
    **_BASE_INFO,
    "gajami_head_eye" : _BASE_INFO["gajami"],
    "gwangeo_head_eye": _BASE_INFO["gwangeo"],
}

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


_HEAD_EYE_CLASSES = {"gwangeo_head_eye", "gajami_head_eye"}

def _draw_bbox(img: Image.Image, xyxy: tuple, label: str, color: tuple) -> np.ndarray:
    x1, y1, x2, y2 = xyxy
    frame = np.array(img.convert("RGB"))[:, :, ::-1].copy()
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
    cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)
    cv2.putText(frame, label, (x1 + 2, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    return frame


def predict(img: Image.Image, use_effnet: bool = False) -> dict:
    yolo   = load_model()
    effnet = load_effnet() if use_effnet else None
    results = yolo(img, verbose=False, conf=0.65)
    result  = results[0]

    if result.boxes is None or len(result.boxes) == 0:
        return {"detected": False, "class_en": None, "class_ko": None, "confidence": 0.0, "top3": []}

    MIN_ASPECT = 1.3
    head_eye_boxes, body_boxes = [], []

    for b in result.boxes:
        cls_name = result.names[int(b.cls[0])]
        if cls_name in SKIP_CLASSES:
            continue
        x1, y1, x2, y2 = b.xyxy[0]
        box = {"cls_name": cls_name, "conf": float(b.conf[0]),
               "xyxy": (int(x1), int(y1), int(x2), int(y2))}
        if cls_name in _HEAD_EYE_CLASSES:
            head_eye_boxes.append(box)
        elif float((x2 - x1) / (y2 - y1 + 1e-6)) >= MIN_ASPECT:
            body_boxes.append(box)

    head_eye_boxes.sort(key=lambda x: x["conf"], reverse=True)
    body_boxes.sort(key=lambda x: x["conf"], reverse=True)

    # head_eye 우선: 눈 위치(좌광우도)가 확실한 판별 근거, EfficientNet 불필요
    if head_eye_boxes:
        best       = head_eye_boxes[0]
        class_en   = best["cls_name"].replace("_head_eye", "")
        class_ko   = CLASS_KO.get(best["cls_name"], class_en)
        confidence = best["conf"]
        annotated  = _draw_bbox(img, best["xyxy"],
                                f"{class_en} (eye) {confidence:.2f}", (0, 200, 255))
        return {
            "detected": True, "class_en": class_en, "class_ko": class_ko,
            "confidence": confidence,
            "top3": [{"class_en": class_en, "class_ko": class_ko, "confidence": confidence}],
            "annotated_image": annotated,
        }

    if not body_boxes:
        return {"detected": False, "class_en": None, "class_ko": None, "confidence": 0.0, "top3": []}

    best = body_boxes[0]

    if effnet is not None:
        x1, y1, x2, y2 = best["xyxy"]
        x = _EFFNET_TF(img.crop((x1, y1, x2, y2)).convert("RGB")).unsqueeze(0)
        with torch.no_grad():
            probs = torch.softmax(effnet(x), dim=1)[0]
        idx        = int(probs.argmax())
        class_en   = EFFNET_CLASSES[idx]
        confidence = float(probs[idx])
        top3 = [
            {"class_en": EFFNET_CLASSES[i],
             "class_ko": CLASS_KO.get(EFFNET_CLASSES[i], EFFNET_CLASSES[i]),
             "confidence": float(probs[i])}
            for i in probs.argsort(descending=True).tolist()
        ]
        annotated = _draw_bbox(img, best["xyxy"], f"{class_en} {confidence:.2f}", (0, 255, 255))
    else:
        class_en   = best["cls_name"]
        confidence = best["conf"]
        seen, top3 = set(), []
        for b in body_boxes:
            if b["cls_name"] not in seen:
                seen.add(b["cls_name"])
                top3.append({"class_en": b["cls_name"],
                             "class_ko": CLASS_KO.get(b["cls_name"], b["cls_name"]),
                             "confidence": b["conf"]})
            if len(top3) == 3:
                break
        annotated = result.plot()

    class_ko = CLASS_KO.get(class_en, class_en)
    return {
        "detected": True, "class_en": class_en, "class_ko": class_ko,
        "confidence": confidence, "top3": top3, "annotated_image": annotated,
    }


@st.cache_resource(show_spinner=False)
def load_clip():
    from transformers import CLIPProcessor, CLIPModel
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    model.eval()
    return model, processor

_CLIP_LABELS = ["a real photograph", "an illustration or drawing or cartoon"]

def is_real_photo(img: Image.Image) -> bool:
    try:
        clip_model, clip_proc = load_clip()
        inputs = clip_proc(text=_CLIP_LABELS, images=img.convert("RGB"),
                           return_tensors="pt", padding=True)
        with torch.no_grad():
            probs = clip_model(**inputs).logits_per_image.softmax(dim=1)[0]
        # probs[0] = real photo 확률
        return float(probs[0]) >= 0.5
    except Exception:
        # CLIP 로드 실패 시 노이즈 휴리스틱 fallback
        gray    = img.convert("L").resize((128, 128))
        blurred = gray.filter(ImageFilter.GaussianBlur(radius=3))
        return float(np.abs(np.array(gray, dtype=np.float32) - np.array(blurred, dtype=np.float32)).mean()) >= 4.5
