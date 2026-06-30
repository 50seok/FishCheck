import os
from pathlib import Path

import numpy as np
import streamlit as st
import torch
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from ultralytics import YOLO

MODEL_PATH = "models/best.pt"
HF_REPO_ID = os.getenv("HF_REPO_ID", "")

SKIP_CLASSES = {"bangeo", "bushiri"}

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


_HEAD_EYE_CLASSES = {"gwangeo_head_eye", "gajami_head_eye"}

def _draw_bbox(img: Image.Image, xyxy: tuple, label: str, color: tuple) -> np.ndarray:
    x1, y1, x2, y2 = xyxy
    out = img.convert("RGB").copy()
    draw = ImageDraw.Draw(out)
    pil_color = tuple(color[::-1])  # BGR→RGB
    draw.rectangle([x1, y1, x2, y2], outline=pil_color, width=2)
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except Exception:
        font = ImageFont.load_default()
    tw, th = draw.textsize(label, font=font) if hasattr(draw, "textsize") else (len(label) * 8, 14)
    draw.rectangle([x1, y1 - th - 4, x1 + tw + 4, y1], fill=pil_color)
    draw.text((x1 + 2, y1 - th - 2), label, fill=(0, 0, 0), font=font)
    return np.array(out)[:, :, ::-1]


BODY_CONF_MIN = 0.70  # 바디만으로 판정할 때 최소 신뢰도

def predict(img: Image.Image) -> dict:
    yolo    = load_model()
    w, _    = img.size
    # 눈 박스는 낮은 conf에서도 검출 필요 → 0.15로 낮춤
    results = yolo(img, verbose=False, conf=0.15)
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
               "xyxy": (int(x1), int(y1), int(x2), int(y2)),
               "cx_norm": float((x1 + x2) / 2 / w)}
        if cls_name in _HEAD_EYE_CLASSES:
            head_eye_boxes.append(box)
        elif float((x2 - x1) / (y2 - y1 + 1e-6)) >= MIN_ASPECT:
            body_boxes.append(box)

    head_eye_boxes.sort(key=lambda x: x["conf"], reverse=True)
    body_boxes.sort(key=lambda x: x["conf"], reverse=True)

    # 눈 검출 우선: 바디도 함께 잡혀야 납작한 생선으로 인정 (우럭 등 오판 방지)
    if head_eye_boxes and body_boxes:
        best       = head_eye_boxes[0]
        # ponytail: 눈 클래스명은 부정확, X좌표가 신뢰도 높음 (테스트 검증)
        class_en   = "gwangeo" if best["cx_norm"] < 0.5 else "gajami"
        class_ko   = CLASS_KO[class_en]
        confidence = best["conf"]
        annotated  = _draw_bbox(img, best["xyxy"],
                                f"{class_en} (eye) {confidence:.2f}", (0, 200, 255))
        return {
            "detected": True, "class_en": class_en, "class_ko": class_ko,
            "confidence": confidence,
            "top3": [{"class_en": class_en, "class_ko": class_ko, "confidence": confidence}],
            "annotated_image": annotated,
        }

    # 바디 fallback: conf >= 0.70 이상일 때만 판정
    body_boxes = [b for b in body_boxes if b["conf"] >= BODY_CONF_MIN]
    if not body_boxes:
        return {"detected": False, "class_en": None, "class_ko": None, "confidence": 0.0, "top3": []}

    best = body_boxes[0]
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
