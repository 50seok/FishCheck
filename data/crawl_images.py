"""
어종별 이미지 자동 수집 스크립트.

사용법:
  pip install icrawler
  python data/crawl_images.py

수집된 이미지는 data/raw/{어종폴더}/ 에 저장됩니다.
collection_guide.md 의 품질 기준에 따라 수동 검수 필수.
"""
import os
from icrawler.builtin import GoogleImageCrawler

# 어종별 검색어 (생물 상태 키워드만 사용)
SPECIES = {
    "gwangeo":  ["활광어", "광어 생물", "olive flounder whole fish"],
    "dodaree":  ["도다리 생물", "봄도다리 낚시", "spotted flounder whole"],
    "gajami":   ["참가자미 생물", "가자미 생선", "flatfish whole body"],
    "bangeo":   ["활방어", "방어 생물", "yellowtail whole fish"],
    "bushiri":  ["부시리 낚시", "부시리 생물", "greater amberjack whole"],
    "ureok":    ["우럭 생물", "조피볼락 낚시", "Korean rockfish whole"],
    "gaebolak": ["개볼락 낚시", "개볼락 생물", "goldeye rockfish"],
}

PER_KEYWORD = 80  # 검색어당 수집 장수 (총 ~240장/어종)
BASE_DIR = os.path.join(os.path.dirname(__file__), "raw")

for folder, keywords in SPECIES.items():
    save_dir = os.path.join(BASE_DIR, folder)
    os.makedirs(save_dir, exist_ok=True)
    for keyword in keywords:
        print(f"[수집] {folder} / {keyword}")
        crawler = GoogleImageCrawler(storage={"root_dir": save_dir})
        crawler.crawl(keyword=keyword, max_num=PER_KEYWORD)

print("\n수집 완료. data/raw/ 폴더를 확인하고 불량 이미지를 수동 삭제하세요.")
print("(조리된 것, 손질된 것, 흐린 사진 제거 필수)")
