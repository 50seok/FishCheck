"""
preprocess 함수 shape 검증 테스트.
모델 가중치 없이 실행 가능 (HF Hub 연결 불필요).
"""
import numpy as np
import pytest
from PIL import Image

from src.preprocess import preprocess, IMG_SIZE
from src.model import CLASS_NAMES, FISH_INFO


def make_dummy_image(width=300, height=400) -> Image.Image:
    arr = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
    return Image.fromarray(arr)


def test_preprocess_output_shape():
    img = make_dummy_image()
    tensor = preprocess(img)
    assert tensor.shape == (1, IMG_SIZE, IMG_SIZE, 3)


def test_preprocess_value_range():
    img = make_dummy_image()
    tensor = preprocess(img)
    assert tensor.min() >= 0.0
    assert tensor.max() <= 1.0


def test_preprocess_accepts_various_sizes():
    for size in [(100, 100), (640, 480), (1920, 1080)]:
        img = make_dummy_image(*size)
        tensor = preprocess(img)
        assert tensor.shape == (1, IMG_SIZE, IMG_SIZE, 3)


def test_class_names_count():
    assert len(CLASS_NAMES) == 7


def test_fish_info_all_classes_covered():
    for name in CLASS_NAMES:
        assert name in FISH_INFO, f"{name} 이 FISH_INFO에 없습니다"
        assert "특징" in FISH_INFO[name]
        assert "구별포인트" in FISH_INFO[name]
        assert "주의" in FISH_INFO[name]
