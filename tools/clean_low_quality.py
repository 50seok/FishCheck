"""
낮은 품질 이미지 정리 스크립트.

삭제 기준:
  1. 미탐지 (모델이 아무것도 감지 못함)
  2. 방어(bangeo)로 예측됐으나 신뢰도 <= 40%
  3. 부시리(bushiri)로 예측됐으나 신뢰도 <= 40%

대상 폴더: data/raw/bangeo, data/raw/bushiri
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PIL import Image
from ultralytics import YOLO

MODEL_PATH = os.path.join(ROOT, "models", "best.pt")
IMG_EXTS   = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
THRESHOLD  = 0.40

FOLDERS = [
    os.path.join(ROOT, "data", "raw", "bangeo"),
    os.path.join(ROOT, "data", "raw", "bushiri"),
]


def should_delete(pred_en: str, conf: float) -> tuple:
    if pred_en == "none":
        return True, "미탐지"
    if pred_en == "bangeo" and conf <= THRESHOLD:
        return True, f"방어 저신뢰도 ({conf*100:.1f}%)"
    if pred_en == "bushiri" and conf <= THRESHOLD:
        return True, f"부시리 저신뢰도 ({conf*100:.1f}%)"
    return False, ""


def main():
    print("모델 로딩 중...")
    model = YOLO(MODEL_PATH)

    to_delete = []

    for folder in FOLDERS:
        folder_name = os.path.basename(folder)
        paths = [
            os.path.join(folder, fn)
            for fn in sorted(os.listdir(folder))
            if os.path.splitext(fn)[1].lower() in IMG_EXTS
        ]
        print(f"\n[{folder_name}] {len(paths)}장 검사 중...")

        for path in paths:
            try:
                img = Image.open(path).convert("RGB")
                img.load()
            except Exception as e:
                print(f"  [SKIP] {os.path.basename(path)}: {e}")
                continue

            yolo_res = model(img, verbose=False)
            r        = yolo_res[0]

            if len(r.boxes) == 0:
                pred_en = "none"
                conf    = 0.0
            else:
                dets    = sorted(
                    [{"en": r.names[int(b.cls[0])], "conf": float(b.conf[0])} for b in r.boxes],
                    key=lambda x: x["conf"], reverse=True,
                )
                pred_en = dets[0]["en"]
                conf    = dets[0]["conf"]

            delete, reason = should_delete(pred_en, conf)
            if delete:
                to_delete.append((path, reason))
                print(f"  삭제 대상: {os.path.basename(path):38s}  {reason}")

    print(f"\n{'='*60}")
    print(f"총 삭제 대상: {len(to_delete)}장")
    print("삭제를 진행합니다...")

    deleted = 0
    for path, reason in to_delete:
        try:
            os.remove(path)
            deleted += 1
        except Exception as e:
            print(f"  [오류] {path}: {e}")

    print(f"\n삭제 완료: {deleted}장")

    for folder in FOLDERS:
        remaining = sum(
            1 for fn in os.listdir(folder)
            if os.path.splitext(fn)[1].lower() in IMG_EXTS
        )
        print(f"  {os.path.basename(folder)}: {remaining}장 남음")


if __name__ == "__main__":
    main()
