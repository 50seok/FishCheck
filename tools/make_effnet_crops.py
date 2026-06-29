"""
Roboflow YOLO 어노테이션으로 크롭 이미지 생성 → EfficientNet 학습용

실행:
    python tools/make_effnet_crops.py

출력 구조:
    data/effnet_crops/
        gajami/  (가자미 크롭 이미지)
        gwangeo/ (광어 크롭 이미지)
"""
from pathlib import Path
from PIL import Image

DATASET_DIR = Path("data/fishcheck_v2")
OUTPUT_DIR  = Path("data/effnet_crops")
SPLITS      = ["train", "valid", "test"]
SKIP        = {"bangeo", "bushiri"}
PAD         = 0.10  # bbox 여백 비율


def yolo_to_pixel(cx, cy, bw, bh, img_w, img_h):
    x1 = int((cx - bw / 2) * img_w)
    y1 = int((cy - bh / 2) * img_h)
    x2 = int((cx + bw / 2) * img_w)
    y2 = int((cy + bh / 2) * img_h)
    return x1, y1, x2, y2


def main():
    # 클래스 이름 로드
    data_yaml = DATASET_DIR / "data.yaml"
    import yaml
    with open(data_yaml) as f:
        cfg = yaml.safe_load(f)
    class_names = cfg["names"]

    for cls in class_names:
        if cls not in SKIP:
            (OUTPUT_DIR / cls).mkdir(parents=True, exist_ok=True)

    total = 0
    for split in SPLITS:
        img_dir   = DATASET_DIR / split / "images"
        label_dir = DATASET_DIR / split / "labels"
        if not img_dir.exists():
            continue

        for img_path in img_dir.glob("*.jpg"):
            label_path = label_dir / (img_path.stem + ".txt")
            if not label_path.exists():
                continue

            img = Image.open(img_path).convert("RGB")
            w, h = img.size

            for line in label_path.read_text().strip().splitlines():
                parts = line.split()
                if len(parts) < 5:
                    continue
                cls_id = int(parts[0])
                cls_name = class_names[cls_id]
                if cls_name in SKIP:
                    continue

                cx, cy, bw, bh = map(float, parts[1:5])
                x1, y1, x2, y2 = yolo_to_pixel(cx, cy, bw, bh, w, h)

                pad_x = int((x2 - x1) * PAD)
                pad_y = int((y2 - y1) * PAD)
                crop = img.crop((
                    max(0, x1 - pad_x), max(0, y1 - pad_y),
                    min(w, x2 + pad_x), min(h, y2 + pad_y),
                ))

                if crop.width < 10 or crop.height < 10:
                    continue
                out_path = OUTPUT_DIR / cls_name / f"{img_path.stem}_{cls_id}_{total}.jpg"
                crop.save(out_path, quality=95)
                total += 1

    print(f"완료: {total}장 크롭 → {OUTPUT_DIR}")
    for cls in class_names:
        if cls not in SKIP:
            count = len(list((OUTPUT_DIR / cls).glob("*.jpg")))
            print(f"  {cls}: {count}장")


if __name__ == "__main__":
    main()
