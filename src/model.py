import os
from pathlib import Path

import streamlit as st
from PIL import Image
from ultralytics import YOLO

MODEL_PATH = "models/best.pt"
# 학습 완료 후 Hugging Face Hub repo ID를 여기에 기록하거나 환경변수로 전달
# 예: HF_REPO_ID=50seoks/fishcheck-model  (Streamlit Cloud → Secrets에 설정)
HF_REPO_ID = os.getenv("HF_REPO_ID", "")

CLASS_KO = {
    "bangeo" : "방어",
    "bushiri": "부시리",
    "gajami" : "가자미/도다리",
    "gwangeo": "광어",
}

FISH_INFO = {
    "bangeo": {
        "학명": "Seriola quinqueradiata",
        "특징": "옆구리에 노란색 가로줄이 있음. 꼬리지느러미도 노란빛.",
        "구별포인트": "부시리보다 노란 줄이 진하고 주둥이가 더 뾰족하다.",
        "주의": "부시리와 혼동 주의 — 노란 줄 선명도와 주둥이 모양으로 구분",
    },
    "bushiri": {
        "학명": "Seriola lalandi",
        "특징": "꼬리지느러미에 노란색이 없거나 희미하다.",
        "구별포인트": "주둥이가 방어보다 둥글고, 옆 노란 줄이 흐리다.",
        "주의": "방어와 혼동 주의 — 꼬리 색상과 주둥이 모양으로 구분",
    },
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
    results = model(img, verbose=False)
    result  = results[0]

    if result.boxes is None or len(result.boxes) == 0:
        return {"detected": False, "class_en": None, "class_ko": None, "confidence": 0.0, "top3": []}

    boxes = sorted(
        [{"cls": int(b.cls[0]), "conf": float(b.conf[0])} for b in result.boxes],
        key=lambda x: x["conf"], reverse=True,
    )

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
