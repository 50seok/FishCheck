import streamlit as st
from PIL import Image

from src.model import predict, load_model, load_clip, is_real_photo, FISH_INFO, CLASS_KO

st.set_page_config(
    page_title="FishCheck — 수산시장 생선 판별기",
    page_icon="🐟",
    layout="centered",
)

load_model()
load_clip()  # 앱 시작 시 CLIP 미리 로드

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
    st.caption("YOLOv8 + EfficientNetB0 2단계 · 학습 데이터: 생물 상태 통 생선")


def show_result(img: Image.Image, use_effnet: bool) -> None:
    with st.spinner("📷 이미지 유형 확인 중 (CLIP)..."):
        real = is_real_photo(img)

    if not real:
        st.error(
            "일러스트·그림·스크린샷으로 감지됩니다. 실제 생선 사진만 판별할 수 있습니다.",
            icon="🚫",
        )
        return

    with st.spinner("🔍 어종 분석 중..."):
        result = predict(img, use_effnet=use_effnet)

    st.divider()

    if not result["detected"]:
        st.error("어종을 판별할 수 없습니다. 전체 체형이 보이는 통 생선 사진으로 다시 시도해 주세요.")
        return

    fish_en    = result["class_en"]
    fish_ko    = result["class_ko"]
    confidence = result["confidence"]
    info       = FISH_INFO.get(fish_en, {})

    if result.get("annotated_image") is not None:
        st.image(result["annotated_image"][..., ::-1], caption="탐지 결과 (바운딩 박스)", use_container_width=True)

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


def load_image(uploaded) -> Image.Image | None:
    allowed_mime = {"image/jpeg", "image/png", "image/webp"}
    if uploaded.type not in allowed_mime:
        st.error("jpg / png / webp 이미지 파일만 업로드할 수 있습니다.")
        return None
    try:
        img = Image.open(uploaded)
        img.verify()
        uploaded.seek(0)
        return Image.open(uploaded)
    except Exception:
        st.error("손상된 이미지 파일입니다. 다른 사진을 사용해 주세요.")
        return None


def upload_tab(state_key: str, use_effnet: bool, help_text: str) -> None:
    if state_key in st.session_state:
        img = st.session_state[state_key]
        st.image(img, caption="업로드된 이미지", use_container_width=True)
        if st.button("🗑️ 이미지 지우기", key=f"clear_{state_key}"):
            del st.session_state[state_key]
            st.rerun()
        show_result(img, use_effnet=use_effnet)
    else:
        uploaded = st.file_uploader(
            "생선 사진을 업로드하세요 (jpg / png / webp)",
            key=f"upload_{state_key}",
            help=help_text,
        )
        if uploaded:
            img = load_image(uploaded)
            if img:
                st.session_state[state_key] = img
                st.rerun()


tab_yolo, tab_eff, tab_camera = st.tabs(["📁 사진업로드 YOLO", "📁 사진업로드 EFF", "📷 카메라 촬영"])

with tab_yolo:
    upload_tab("img_yolo", use_effnet=False, help_text="YOLO 단일 모델로 판별합니다.")

with tab_eff:
    upload_tab("img_eff", use_effnet=True, help_text="YOLO 탐지 → EfficientNetB0 분류 2단계로 판별합니다.")

with tab_camera:
    shot = st.camera_input("카메라로 생선을 찍어주세요")
    if shot:
        img = Image.open(shot)
        show_result(img, use_effnet=False)
