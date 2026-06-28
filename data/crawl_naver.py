"""
Naver 이미지 검색 크롤러 (FishCheck용)

사용법:
  pip install requests beautifulsoup4
  python data/crawl_naver.py

수집 이미지 → data/raw/{어종}/ (기존 이미지 유지, 추가 저장)
"""
import json
import re
import time
import urllib.parse
from pathlib import Path

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
    "Referer": "https://www.naver.com/",
}

SPECIES = {
    "bushiri":  ["부시리 낚시", "부시리 생물", "부시리 수산시장", "부시리 조황", "히라마사 낚시"],
    "gaebolak": ["개볼락 낚시", "개볼락 생물", "개볼락 수산시장", "개볼락 조황", "황볼락 낚시"],
    "ureok":    ["우럭 낚시", "우럭 생물", "우럭 수산시장", "우럭 조황", "쏨뱅이 낚시"],
}

PER_KEYWORD = 100
BASE_DIR = Path(__file__).parent / "raw"


def fetch_naver_image_urls(keyword: str, max_num: int, session: requests.Session) -> list[str]:
    urls: list[str] = []
    start = 1

    while len(urls) < max_num:
        encoded = urllib.parse.quote(keyword)
        page_url = (
            f"https://search.naver.com/search.naver"
            f"?where=image&sm=tab_jum&query={encoded}&start={start}"
        )
        try:
            resp = session.get(page_url, timeout=15)
            resp.raise_for_status()
        except Exception as e:
            print(f"  [요청 오류] {e}")
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        found = 0

        # 스크립트 태그 내 JSON 파싱 (Naver 현행 포맷)
        for script in soup.find_all("script"):
            if not script.string:
                continue
            matches = re.findall(
                r'"(?:url|thumb|originalUrl)"\s*:\s*"(https?://[^"]+\.(?:jpg|jpeg|png|webp)(?:\?[^"]*)?)"',
                script.string,
                re.IGNORECASE,
            )
            for m in matches:
                if m not in urls:
                    urls.append(m)
                    found += 1

        if found == 0:
            print(f"  [경고] 더 이상 URL 없음 (start={start})")
            break

        start += 50
        time.sleep(0.4)

    return urls[:max_num]


def download_image(url: str, save_path: Path, session: requests.Session) -> bool:
    try:
        resp = session.get(url, timeout=10, stream=True)
        resp.raise_for_status()
        if "image" not in resp.headers.get("Content-Type", ""):
            return False
        with open(save_path, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        return True
    except Exception:
        return False


def crawl_species(folder: str, keywords: list[str]):
    save_dir = BASE_DIR / folder
    save_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update(HEADERS)

    img_count = len(list(save_dir.iterdir()))

    for keyword in keywords:
        print(f"[수집] {folder} / {keyword}")
        urls = fetch_naver_image_urls(keyword, PER_KEYWORD, session)
        print(f"  URL {len(urls)}개 확보")

        saved = 0
        for url in urls:
            save_path = save_dir / f"{folder}_{img_count:04d}.jpg"
            if download_image(url, save_path, session):
                img_count += 1
                saved += 1
            time.sleep(0.15)

        print(f"  {saved}장 저장 완료")


if __name__ == "__main__":
    print("=" * 50)
    print("FishCheck — Naver 이미지 크롤러")
    print(f"어종 {len(SPECIES)}종 / 키워드당 {PER_KEYWORD}장 목표")
    print("=" * 50)

    for folder, keywords in SPECIES.items():
        crawl_species(folder, keywords)

    print("\n수집 완료. auto_filter.py 를 실행해 검수하세요.")
