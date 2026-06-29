"""
어종별 이미지 자동 수집 스크립트.
사용법: python data/crawl_images.py
수집된 이미지는 data/raw/{어종폴더}/ 에 저장됩니다.
"""
import os
from icrawler.builtin import BingImageCrawler, GoogleImageCrawler

SPECIES = {
    "bangeo": [
        "방어 수산시장 수족관",
        "방어 활어 수족관",
        "대방어 수족관 생물",
        "방어 통생선 생물",
        "수산시장 방어 통째",
        "japanese amberjack fish whole",
        "buri fish aquarium",
        "yellowtail whole fish market",
    ],
    "bushiri": [
        "부시리 수산시장 수족관",
        "부시리 활어 수족관",
        "부시리 생물 통째",
        "수산시장 부시리",
        "hiramasa fish whole",
        "hiramasa kingfish aquarium",
        "yellowtail kingfish whole fish market",
    ],
}

PER_KEYWORD = 50
BASE_DIR = os.path.join(os.path.dirname(__file__), "raw")

for folder, keywords in SPECIES.items():
    save_dir = os.path.join(BASE_DIR, folder)
    os.makedirs(save_dir, exist_ok=True)
    for keyword in keywords:
        print(f"[수집] {folder} / {keyword}")
        crawler = BingImageCrawler(storage={"root_dir": save_dir})
        crawler.crawl(keyword=keyword, max_num=PER_KEYWORD)

print("\n수집 완료. data/raw/ 폴더를 확인하세요.")