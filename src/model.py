import os
import streamlit as st
import tensorflow as tf
from huggingface_hub import hf_hub_download
from PIL import Image

from src.preprocess import preprocess

# ── 학습 완료 후 아래 값을 실제 Hugging Face repo_id로 교체하세요 ──
HF_REPO_ID = "your-hf-username/fishcheck-model"
HF_FILENAME = "fishcheck_model.h5"
# ─────────────────────────────────────────────────────────────────

CLASS_NAMES = ["가자미", "개볼락", "광어", "도다리", "방어", "부시리", "우럭"]

FISH_INFO = {
    "가자미": {
        "학명": "Pleuronichthys cornutus",
        "특징": "몸이 납작하고 둥근 편. 측선이 거의 직선.",
        "구별포인트": "광어·도다리보다 작고 둥글다. 측선이 직선에 가까움.",
        "주의": "광어, 도다리와 체형 유사 — 크기와 측선 형태로 구분",
    },
    "개볼락": {
        "학명": "Sebastes thompsoni",
        "특징": "주황~노란 반점이 몸 전체에 뚜렷하게 분포.",
        "구별포인트": "우럭보다 색이 밝고 반점이 선명하다.",
        "주의": "우럭과 혼동 주의 — 반점 색과 선명도로 구분",
    },
    "광어": {
        "학명": "Paralichthys olivaceus",
        "특징": "눈이 왼쪽에 몰려 있음. 입이 크고 이빨이 날카롭다.",
        "구별포인트": "눈 방향이 왼쪽(좌광우도 기억법). 도다리보다 입이 큼.",
        "주의": "도다리·가자미와 혼동 주의 — 눈 방향과 입 크기로 구분",
    },
    "도다리": {
        "학명": "Pleuronichthys cornutus",
        "특징": "눈이 오른쪽에 몰려 있음. 입이 작고 체형이 둥글다.",
        "구별포인트": "눈 방향이 오른쪽(좌광우도). 광어보다 입이 작음.",
        "주의": "광어·가자미와 혼동 주의 — 눈 방향으로 가장 쉽게 구분",
    },
    "방어": {
        "학명": "Seriola quinqueradiata",
        "특징": "옆구리에 노란색 가로줄이 있음. 꼬리지느러미도 노란빛.",
        "구별포인트": "부시리보다 노란 줄이 진하고 주둥이가 더 뾰족하다.",
        "주의": "부시리와 혼동 주의 — 노란 줄 선명도와 주둥이 모양으로 구분",
    },
    "부시리": {
        "학명": "Seriola lalandi",
        "특징": "꼬리지느러미에 노란색이 없거나 희미하다.",
        "구별포인트": "주둥이가 방어보다 둥글고, 옆 노란 줄이 흐리다.",
        "주의": "방어와 혼동 주의 — 꼬리 색상과 주둥이 모양으로 구분",
    },
    "우럭": {
        "학명": "Sebastes schlegelii",
        "특징": "전체적으로 어두운 갈색~회색 계열. 반점이 흐리거나 없음.",
        "구별포인트": "개볼락보다 색이 어둡고 반점이 불분명하다.",
        "주의": "개볼락과 혼동 주의 — 전체 색상 명도로 구분",
    },
}


@st.cache_resource(show_spinner="모델 로딩 중... (최초 1회만)")
def load_model() -> tf.keras.Model:
    """Hugging Face Hub에서 모델 가중치를 다운로드하고 캐싱."""
    token = os.environ.get("HF_TOKEN")
    path = hf_hub_download(
        repo_id=HF_REPO_ID,
        filename=HF_FILENAME,
        token=token,
    )
    return tf.keras.models.load_model(path)


def predict(img: Image.Image) -> dict:
    """
    어종 예측.

    Returns:
        {
            "class": str,           # 예측 어종 (한국어)
            "confidence": float,    # 신뢰도 0~1
            "all_probs": list[dict] # 전체 어종 확률 [{"name": str, "prob": float}, ...]
        }
    """
    model = load_model()
    tensor = preprocess(img)
    probs = model.predict(tensor, verbose=0)[0]

    top_idx = int(probs.argmax())
    return {
        "class": CLASS_NAMES[top_idx],
        "confidence": float(probs[top_idx]),
        "all_probs": [
            {"name": CLASS_NAMES[i], "prob": float(probs[i])}
            for i in range(len(CLASS_NAMES))
        ],
    }
