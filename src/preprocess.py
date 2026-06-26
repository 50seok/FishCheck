import numpy as np
from PIL import Image

IMG_SIZE = 224


def preprocess(img: Image.Image) -> np.ndarray:
    """PIL 이미지를 EfficientNetB0 입력 텐서로 변환."""
    img = img.convert("RGB").resize((IMG_SIZE, IMG_SIZE))
    arr = np.array(img, dtype=np.float32) / 255.0
    return np.expand_dims(arr, axis=0)  # (1, 224, 224, 3)
