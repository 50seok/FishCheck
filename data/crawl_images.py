"""
어종별 이미지 자동 수집 스크립트.

사용법:
  pip install icrawler
  python data/crawl_images.py

수집된 이미지는 data/raw/{어종폴더}/ 에 저장됩니다.
collection_guide.md 의 품질 기준에 따라 수동 검수 필수.
"""
import os
from icrawler.builtin import BingImageCrawler

# 어종별 검색어 — 한국어 중심, 영어는 어종명+fish 조합으로 한정
SPECIES = {
    "bangeo": [
        "방어 통생선", "방어 생물 수산시장", "방어 횟감 통째",
        "방어 생선 전체", "Japanese amberjack whole fish",
        "yellowtail fish whole raw", "방어 낚시 통째",
    ],
}

PER_KEYWORD = 80  # 검색어당 수집 장수 (총 ~560장/어종)
BASE_DIR = os.path.join(os.path.dirname(__file__), "raw")

for folder, keywords in SPECIES.items():
    save_dir = os.path.join(BASE_DIR, folder)
    os.makedirs(save_dir, exist_ok=True)
    for keyword in keywords:
        print(f"[수집] {folder} / {keyword}")
        crawler = BingImageCrawler(storage={"root_dir": save_dir})
        crawler.crawl(keyword=keyword, max_num=PER_KEYWORD)

print("\n수집 완료. data/raw/ 폴더를 확인하고 불량 이미지를 수동 삭제하세요.")
print("(조리된 것, 손질된 것, 흐린 사진 제거 필수)")
