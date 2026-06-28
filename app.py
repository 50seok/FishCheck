import numpy as np
import streamlit as st
from PIL import Image

from src.model import predict, FISH_INFO, CLASS_KO

st.set_page_config(
    page_title="FishCheck — 수산시장 생선 판별기",
    page_icon="🐟",
    layout="centered",
)

st.title("🐟 FishCheck")
st.markdown("**수산시장에서 생선에 속지 않도록 — 사진 한 장으로 어종을 판별합니다**")

st.warning(
    "⚠️ **통 생선(생물) 상태에서만 정확합니다.** "
    "손질·조리된 생선은 판별이 어렵습니다. 참고용으로만 사용하세요.",
    icon="⚠️",
)

with st.sidebar:
    st.header("사용 방법")
    st.markdown(
        """
        1. **사진 업로드** 또는 **카메라** 탭 선택
        2. 생물(통 생선) 상태 사진 준비
        3. 이미지 업로드 → 자동 판별
        4. 결과 카드에서 어종 확인
        """
    )
    st.divider()
    st.header("판별 가능 어종")
    for en, ko in CLASS_KO.items():
        info = FISH_INFO[en]
        st.markdown(f"**{ko}** — {info['특징'][:30]}...")
    st.divider()
    st.caption("YOLOv8 기반 · 학습 데이터: 생물 상태 통 생선")

tab_upload, tab_camera = st.tabs(["📁 사진 업로드", "📷 카메라 촬영"])

img: Image.Image | None = None

with tab_upload:
    uploaded = st.file_uploader(
        "생선 사진을 업로드하세요",
        type=["jpg", "jpeg", "png", "webp"],
        help="전체 체형이 보이는 통 생선 사진을 올려주세요",
    )
    if uploaded:
        try:
            img = Image.open(uploaded)
            img.verify()
            uploaded.seek(0)
            img = Image.open(uploaded)
            st.image(img, caption="업로드된 이미지", use_container_width=True)
        except Exception:
            st.error("이미지 파일만 업로드할 수 있습니다.")
            img = None

with tab_camera:
    shot = st.camera_input("카메라로 생선을 찍어주세요")
    if shot:
        img = Image.open(shot)

if img is not None:
    with st.spinner("어종 분석 중..."):
        result = predict(img)

    st.divider()

    if not result["detected"]:
        st.error("어종을 판별할 수 없습니다. 전체 체형이 보이는 통 생선 사진으로 다시 시도해 주세요.")
    else:
        fish_en    = result["class_en"]
        fish_ko    = result["class_ko"]
        confidence = result["confidence"]
        info       = FISH_INFO.get(fish_en, {})

        if result.get("annotated_image") is not None:
            ann = result["annotated_image"]
            st.image(ann[..., ::-1], caption="탐지 결과 (바운딩 박스)", use_container_width=True)

        col_name, col_conf = st.columns([2, 1])
        with col_name:
            st.markdown(f"## 판별 결과: **{fish_ko}**")
            if info:
                st.caption(f"학명: *{info['학명']}*")
        with col_conf:
            conf_pct = confidence * 100
            color = "green" if conf_pct >= 70 else "orange" if conf_pct >= 50 else "red"
            st.markdown(
                f"<h2 style='color:{color};text-align:right'>{conf_pct:.1f}%</h2>",
                unsafe_allow_html=True,
            )
            st.caption("신뢰도")

        if info:
            st.info(f"**특징**: {info['특징']}")
            st.success(f"**구별 포인트**: {info['구별포인트']}")
            st.warning(f"**주의**: {info['주의']}")

        if result.get("top3") and len(result["top3"]) > 1:
            with st.expander("상위 후보 보기"):
                for det in result["top3"]:
                    st.progress(det["confidence"], text=f"{det['class_ko']}  {det['confidence']*100:.1f}%")

        if confidence < 0.7:
            st.warning("신뢰도가 낮습니다. 전체 체형이 잘 보이는 통 생선 사진으로 다시 시도해 주세요.")
