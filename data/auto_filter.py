"""
FishCheck 이미지 자동 검수 스크립트

3단계 필터링:
  Stage 1 — 기본 품질 (해상도, 파일 크기, 블러, 손상)
  Stage 2 — 중복 제거 (phash 기반)
  Stage 3 — CLIP 의미 필터 (생물 통 생선 vs 조리/손질된 생선)

사용법:
  pip install -r data/requirements_filter.txt
  python data/auto_filter.py

결과:
  통과한 이미지 → data/raw/{어종}/ 유지
  탈락한 이미지 → data/rejected/{어종}/{사유}/ 이동 (삭제 안 함)
"""

import os
import shutil
from pathlib import Path

import numpy as np
from PIL import Image

try:
    import imagehash
except ImportError:
    raise ImportError("pip install imagehash 를 먼저 실행하세요")

try:
    import torch
    from transformers import CLIPModel, CLIPProcessor
    CLIP_AVAILABLE = True
except ImportError:
    print("[경고] torch/transformers 미설치 → Stage 3 (CLIP) 건너뜀")
    print("       pip install -r data/requirements_filter.txt 로 설치 가능")
    CLIP_AVAILABLE = False

# ── 설정 ──────────────────────────────────────────────────────────
RAW_DIR      = Path(__file__).parent / "raw"
REJECTED_DIR = Path(__file__).parent / "rejected"

MIN_RESOLUTION  = 200      # 가로·세로 최소 px
MIN_FILE_SIZE   = 5_000    # 최소 파일 크기 (bytes)
BLUR_THRESHOLD  = 50.0     # Laplacian 분산 (낮을수록 흐림)
HASH_MAX_DIST   = 8        # phash 해밍 거리 (낮을수록 엄격)
CLIP_THRESHOLD  = 0.0      # (생물 점수 - 조리 점수) 최소 마진

WHOLE_PROMPTS = [
    "a photo of a whole fresh raw fish",
    "a whole live fish at fish market",
    "a raw uncooked whole fish",
]
COOKED_PROMPTS = [
    "grilled fish food on plate",
    "fish sashimi dish",
    "cooked fish meal",
    "sliced fish fillet",
    "fish soup stew",
    "fish served as food",
]
# ──────────────────────────────────────────────────────────────────


def load_clip():
    print("[Stage 3] CLIP 모델 로딩 중 (최초 1회 다운로드 ~350MB)...")
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
    proc  = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    model.eval()
    return model, proc


def clip_is_whole_fish(img: Image.Image, model, proc) -> tuple[bool, float]:
    all_prompts = WHOLE_PROMPTS + COOKED_PROMPTS
    inputs = proc(text=all_prompts, images=img, return_tensors="pt", padding=True)
    with torch.no_grad():
        logits = model(**inputs).logits_per_image[0]
        probs = logits.softmax(dim=0).numpy()

    whole_score = float(probs[:len(WHOLE_PROMPTS)].max())
    cooked_score = float(probs[len(WHOLE_PROMPTS):].max())
    margin = whole_score - cooked_score
    return margin >= CLIP_THRESHOLD, margin


def laplacian_variance(img: Image.Image) -> float:
    gray = np.array(img.convert("L"), dtype=np.float32)
    # 간단한 Laplacian 근사 (scipy 없이)
    padded = np.pad(gray, 1, mode="edge")
    lap = (
        padded[:-2, 1:-1] + padded[2:, 1:-1]
        + padded[1:-1, :-2] + padded[1:-1, 2:]
        - 4 * gray
    )
    return float(lap.var())


def move_to_rejected(src: Path, species: str, reason: str):
    dst_dir = REJECTED_DIR / species / reason
    dst_dir.mkdir(parents=True, exist_ok=True)
    shutil.move(str(src), str(dst_dir / src.name))


def filter_species(species_dir: Path, clip_model=None, clip_proc=None) -> dict:
    species = species_dir.name
    images = [
        f for f in species_dir.iterdir()
        if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    ]

    if not images:
        print(f"  [{species}] 이미지 없음 — 건너뜀")
        return {}

    stats = {"total": len(images), "pass": 0, "quality": 0, "duplicate": 0, "clip": 0}
    seen_hashes: dict[str, Path] = {}

    print(f"\n[{species}] {len(images)}장 검수 시작")

    for img_path in images:
        # Stage 1: 기본 품질
        try:
            if img_path.stat().st_size < MIN_FILE_SIZE:
                move_to_rejected(img_path, species, "quality_size")
                stats["quality"] += 1
                continue

            img = Image.open(img_path)
            img.verify()
            img = Image.open(img_path).convert("RGB")  # verify 후 재로딩 필요

            w, h = img.size
            if w < MIN_RESOLUTION or h < MIN_RESOLUTION:
                move_to_rejected(img_path, species, "quality_resolution")
                stats["quality"] += 1
                continue

            if laplacian_variance(img) < BLUR_THRESHOLD:
                move_to_rejected(img_path, species, "quality_blur")
                stats["quality"] += 1
                continue

        except Exception:
            move_to_rejected(img_path, species, "quality_corrupt")
            stats["quality"] += 1
            continue

        # Stage 2: 중복 제거
        try:
            ph = imagehash.phash(img)
            is_dup = False
            for existing_hash_str in seen_hashes:
                if ph - imagehash.hex_to_hash(existing_hash_str) <= HASH_MAX_DIST:
                    move_to_rejected(img_path, species, "duplicate")
                    stats["duplicate"] += 1
                    is_dup = True
                    break
            if is_dup:
                continue
            seen_hashes[str(ph)] = img_path
        except Exception:
            pass

        # Stage 3: CLIP 의미 필터
        if CLIP_AVAILABLE and clip_model is not None:
            try:
                ok, margin = clip_is_whole_fish(img, clip_model, clip_proc)
                if not ok:
                    move_to_rejected(img_path, species, f"clip_cooked")
                    stats["clip"] += 1
                    continue
            except Exception as e:
                print(f"    [CLIP 오류] {img_path.name}: {e}")

        stats["pass"] += 1

    reject = stats["quality"] + stats["duplicate"] + stats["clip"]
    print(f"  결과: {stats['pass']}/{stats['total']} 통과  "
          f"| 탈락 {reject}장 "
          f"(품질 {stats['quality']} / 중복 {stats['duplicate']} / CLIP {stats['clip']})")
    return stats


def main():
    if not RAW_DIR.exists():
        print(f"[오류] {RAW_DIR} 가 없습니다. crawl_images.py 를 먼저 실행하세요.")
        return

    species_dirs = sorted(d for d in RAW_DIR.iterdir() if d.is_dir())
    if not species_dirs:
        print(f"[오류] {RAW_DIR} 에 어종 폴더가 없습니다.")
        return

    clip_model, clip_proc = None, None
    if CLIP_AVAILABLE:
        clip_model, clip_proc = load_clip()

    print("=" * 60)
    print("FishCheck 자동 검수 시작")
    print(f"  Stage 1: 기본 품질 (해상도 {MIN_RESOLUTION}px / 블러 / 손상)")
    print(f"  Stage 2: 중복 제거 (phash 거리 ≤ {HASH_MAX_DIST})")
    print(f"  Stage 3: CLIP {'✅' if CLIP_AVAILABLE else '⚠️ 건너뜀 (설치 필요)'}")
    print("=" * 60)

    total = {"total": 0, "pass": 0, "quality": 0, "duplicate": 0, "clip": 0}
    for sp_dir in species_dirs:
        result = filter_species(sp_dir, clip_model, clip_proc)
        for k in total:
            total[k] += result.get(k, 0)

    print("\n" + "=" * 60)
    print("전체 요약")
    print(f"  총       : {total['total']}장")
    print(f"  최종 통과: {total['pass']}장")
    print(f"  탈락 품질: {total['quality']}장")
    print(f"  탈락 중복: {total['duplicate']}장")
    print(f"  탈락 CLIP: {total['clip']}장")
    print(f"\n탈락 이미지는 data/rejected/ 에 보관됨 (삭제 아님 — 직접 확인 가능)")
    print("검수 완료 후 data/raw/ 를 Google Drive 에 업로드하세요.")


if __name__ == "__main__":
    main()
