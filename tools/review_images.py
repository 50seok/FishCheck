"""
수집된 이미지 수동 검수 UI
실행: streamlit run tools/review_images.py
"""
import streamlit as st
from pathlib import Path
import shutil

RAW_DIR    = Path(__file__).parent.parent / 'data' / 'raw'
ACCEPT_DIR = Path(__file__).parent.parent / 'data' / 'reviewed'
REJECT_DIR = Path(__file__).parent.parent / 'data' / 'rejected'

st.set_page_config(page_title='FishCheck 이미지 검수', layout='wide')
st.title('FishCheck 이미지 검수')

# 사이드바
target = st.sidebar.selectbox('어종 선택', ['bangeo (방어)', 'bushiri (부시리)'])
cls = target.split(' ')[0]
cols_per_row = st.sidebar.slider('열 수', 2, 6, 4)

img_dir = RAW_DIR / cls
if not img_dir.exists():
    st.warning(f'{img_dir} 폴더가 없습니다.')
    st.stop()

images = sorted(img_dir.glob('*.jpg')) + sorted(img_dir.glob('*.png')) + sorted(img_dir.glob('*.jpeg'))
if not images:
    st.info(f'{cls} 이미지가 없습니다.')
    st.stop()

# 진행 현황
accept_dir = ACCEPT_DIR / cls
reject_dir = REJECT_DIR / cls
accepted  = len(list(accept_dir.glob('*.*'))) if accept_dir.exists() else 0
rejected  = len(list(reject_dir.glob('*.*'))) if reject_dir.exists() else 0

c1, c2, c3 = st.columns(3)
c1.metric('남은 검수', len(images))
c2.metric('승인', accepted)
c3.metric('삭제', rejected)

st.divider()
st.subheader('삭제할 이미지를 체크하세요')

if 'checked' not in st.session_state:
    st.session_state.checked = {}

tc1, tc2, _ = st.columns([1, 1, 6])
if tc1.button('전체 선택'):
    for img in images:
        st.session_state.checked[img.name] = True
if tc2.button('전체 해제'):
    st.session_state.checked = {}

rows = [images[i:i+cols_per_row] for i in range(0, len(images), cols_per_row)]
for row in rows:
    cols = st.columns(cols_per_row)
    for col, img_path in zip(cols, row):
        with col:
            st.image(str(img_path), use_container_width=True)
            checked = st.checkbox(
                img_path.name[:16],
                value=st.session_state.checked.get(img_path.name, False),
                key=f'chk_{img_path.name}'
            )
            st.session_state.checked[img_path.name] = checked

st.divider()
selected = [img for img in images if st.session_state.checked.get(img.name, False)]
st.write(f'선택(삭제 대상): **{len(selected)}장**')

ac1, ac2 = st.columns(2)
if ac1.button('✅ 나머지 모두 승인', type='primary', disabled=not images):
    accept_dir.mkdir(parents=True, exist_ok=True)
    reject_dir.mkdir(parents=True, exist_ok=True)
    selected_names = {img.name for img in selected}
    ok, rej = 0, 0
    for img in images:
        if img.name in selected_names:
            shutil.move(str(img), reject_dir / img.name)
            rej += 1
        else:
            shutil.move(str(img), accept_dir / img.name)
            ok += 1
    st.session_state.checked = {}
    st.success(f'승인 {ok}장 → data/reviewed/{cls}/  |  삭제 {rej}장')
    st.rerun()

if ac2.button('🗑️ 선택만 삭제', disabled=not selected):
    reject_dir.mkdir(parents=True, exist_ok=True)
    for img in selected:
        shutil.move(str(img), reject_dir / img.name)
    st.session_state.checked = {}
    st.success(f'{len(selected)}장 삭제됨')
    st.rerun()

st.sidebar.divider()
st.sidebar.markdown(f'''
**저장 경로**
- 승인: `data/reviewed/{cls}/`
- 삭제: `data/rejected/{cls}/`
''')