import os
from pathlib import Path

import numpy as np
import streamlit as st
from PIL import Image, ImageFilter
from ultralytics import YOLO

MODEL_PATH = "models/best.pt"
# 학습 완료 후 Hugging Face Hub repo ID를 여기에 기록하거나 환경변수로 전달
# 예: HF_REPO_ID=50seoks/fishcheck-model  (Streamlit Cloud → Secrets에 설정)
HF_REPO_ID = os.getenv("HF_REPO_ID", "")

SKIP_CLASSES = {"bangeo", "bushiri"}

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


@st.cache_resource(show_spinner="모델 로딩 중... (최초 1회만)")
def load_model() -> YOLO:
    if not Path(MODEL_PATH).exists():
        if not HF_REPO_ID:
            raise FileNotFoundError(
                f"{MODEL_PATH} 없음. 학습 후 HF_REPO_ID 환경변수를 설정하거나 모델 파일을 직접 배치하세요."
            )
        from huggingface_hub import hf_hub_download
        Path(MODEL_PATH).parent.mkdir(parents=True, exist_ok=True)
        hf_hub_download(repo_id=HF_REPO_ID, filename="best.pt", local_dir="models")
    return YOLO(MODEL_PATH)


def predict(img: Image.Image) -> dict:
    model   = load_model()
    results = model(img, verbose=False, conf=0.65)
    result  = results[0]

    if result.boxes is None or len(result.boxes) == 0:
        return {"detected": False, "class_en": None, "class_ko": None, "confidence": 0.0, "top3": []}

    MIN_ASPECT = 1.3  # 납작한 어류(광어·가자미) 최소 가로/세로 비율
    boxes = []
    for b in result.boxes:
        cls_name = result.names[int(b.cls[0])]
        if cls_name in SKIP_CLASSES:
            continue
        x1, y1, x2, y2 = b.xyxy[0]
        aspect = float((x2 - x1) / (y2 - y1 + 1e-6))
        if aspect < MIN_ASPECT:
            continue
        boxes.append({"cls": int(b.cls[0]), "conf": float(b.conf[0])})
    boxes.sort(key=lambda x: x["conf"], reverse=True)

    if not boxes:
        return {"detected": False, "class_en": None, "class_ko": None, "confidence": 0.0, "top3": []}

    best       = boxes[0]
    class_en   = result.names[best["cls"]]
    class_ko   = CLASS_KO.get(class_en, class_en)
    confidence = best["conf"]

    seen  = set()
    top3  = []
    for b in boxes:
        name = result.names[b["cls"]]
        if name not in seen:
            seen.add(name)
            top3.append({"class_en": name, "class_ko": CLASS_KO.get(name, name), "confidence": b["conf"]})
        if len(top3) == 3:
            break

    return {
        "detected"      : True,
        "class_en"      : class_en,
        "class_ko"      : class_ko,
        "confidence"    : confidence,
        "top3"          : top3,
        "annotated_image": result.plot(),
    }


def is_real_photo(img: Image.Image, threshold: float = 3.0) -> bool:
    """실사 사진 여부 판별.
    실사: 가우시안 블러 후에도 grain/noise 잔존 → hf_noise 높음
    일러스트/그림: 블러하면 평탄해짐 → hf_noise 낮음
    """
    gray = img.convert("L").resize((128, 128))
    blurred = gray.filter(ImageFilter.GaussianBlur(radius=3))
    arr_orig = np.array(gray, dtype=np.float32)
    arr_blur = np.array(blurred, dtype=np.float32)
    hf_noise = np.abs(arr_orig - arr_blur).mean()
    return hf_noise >= threshold
