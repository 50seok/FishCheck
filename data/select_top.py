"""
어종별 상위 N장 선별 스크립트

CLIP으로 각 이미지에 '생물 통 생선' 점수를 매긴 뒤
점수 순 상위 TOP_N장만 data/raw/{어종}/ 에 남기고
나머지는 data/rejected/{어종}/not_selected/ 로 이동.

사용법:
  python data/select_top.py
  python data/select_top.py --top 60   # 장수 조정
"""

import argparse
import shutil
from pathlib import Path

import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

TOP_N   = 80
RAW_DIR = Path(__file__).parent / "raw"
REJ_DIR = Path(__file__).parent / "rejected"
DEVICE  = "cuda" if torch.cuda.is_available() else "cpu"

WHOLE_PROMPTS = [
    "a photo of a whole fresh raw fish",
    "a whole live fish at fish market",
    "a raw uncooked whole fish",
    "a complete fish with scales and fins",
    "a fresh fish laid on ice at seafood market",
]


def load_clip():
    print(f"CLIP 모델 로딩 중 (device={DEVICE})...")
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(DEVICE)
    proc  = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    model.eval()
    return model, proc


def score_image(img: Image.Image, model, proc) -> float:
    inputs = proc(text=WHOLE_PROMPTS, images=img, return_tensors="pt", padding=True)
    inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
    with torch.no_grad():
        logits = model(**inputs).logits_per_image[0]
        probs  = logits.softmax(dim=0).cpu().numpy()
    return float(probs.max())


def select_species(sp_dir: Path, top_n: int, model, proc):
    species = sp_dir.name
    images  = sorted(
        f for f in sp_dir.iterdir()
        if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    )
    if not images:
        print(f"[{species}] 이미지 없음 - 건너뜀")
        return

    print(f"\n[{species}] {len(images)}장 점수 계산 중...")
    scored = []
    for i, p in enumerate(images, 1):
        try:
            img   = Image.open(p).convert("RGB")
            score = score_image(img, model, proc)
            scored.append((score, p))
        except Exception as e:
            print(f"  오류 {p.name}: {e}")
        if i % 20 == 0:
            print(f"  {i}/{len(images)} 완료")

    scored.sort(reverse=True)

    actual_kept = min(top_n, len(scored))
    discard = [p for _, p in scored[actual_kept:]]

    dst_dir = REJ_DIR / species / "not_selected"
    dst_dir.mkdir(parents=True, exist_ok=True)
    for p in discard:
        shutil.move(str(p), str(dst_dir / p.name))

    print(f"  유지: {actual_kept}장 / 이동: {len(discard)}장 -> rejected/{species}/not_selected/")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=TOP_N, help="어종당 유지 장수 (기본 80)")
    args = parser.parse_args()

    model, proc = load_clip()

    sp_dirs = sorted(d for d in RAW_DIR.iterdir() if d.is_dir())
    print(f"\n어종당 상위 {args.top}장 선별 시작")
    print("=" * 50)
    for sp_dir in sp_dirs:
        select_species(sp_dir, args.top, model, proc)

    print("\n" + "=" * 50)
    print("선별 완료. data/raw/ 에 각 어종 상위 이미지만 남았습니다.")
    print("육안 검수 후 불량 이미지를 직접 삭제하세요.")


if __name__ == "__main__":
    main()
