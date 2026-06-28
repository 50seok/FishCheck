"""
YOLOv8 detection 모델 및 CLASS_KO / FISH_INFO 검증 테스트.
모델 가중치(best.pt) 없이도 실행 가능.
"""
import pytest
from PIL import Image
import numpy as np

from src.model import CLASS_KO, FISH_INFO

EXPECTED_CLASSES = {"bangeo", "bushiri", "gajami", "gwangeo"}


def test_class_ko_count():
    assert len(CLASS_KO) == 4


def test_class_ko_keys():
    assert set(CLASS_KO.keys()) == EXPECTED_CLASSES


def test_fish_info_all_classes_covered():
    for en in EXPECTED_CLASSES:
        assert en in FISH_INFO, f"{en} 이 FISH_INFO에 없습니다"
        assert "학명" in FISH_INFO[en]
        assert "특징" in FISH_INFO[en]
        assert "구별포인트" in FISH_INFO[en]
        assert "주의" in FISH_INFO[en]


def test_class_ko_values_not_empty():
    for en, ko in CLASS_KO.items():
        assert ko, f"{en} 의 한국어 이름이 비어 있습니다"


@pytest.mark.skipif(
    not __import__("pathlib").Path("models/best.pt").exists(),
    reason="models/best.pt 없음 — 학습 후 실행"
)
def test_predict_returns_expected_keys():
    from src.model import predict
    dummy = Image.fromarray(np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8))
    result = predict(dummy)
    assert "detected" in result
    assert "class_en" in result
    assert "class_ko" in result
    assert "confidence" in result
    assert "top3" in result
