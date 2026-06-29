"""
YouTube 방어/부시리 이미지 수집 스크립트 v2
- 수족관/어류도감/생물 키워드로 검색 (낚시 영상 제외)
- confidence 0.6 이상 + 바운딩박스 15% 이상인 프레임만 저장
"""

if __name__ == '__main__':
    import os, sys, time, hashlib, argparse
    from pathlib import Path
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent.parent / '.env')

    import cv2
    import yt_dlp
    from ultralytics import YOLO

    QUERIES = {
        'bangeo': [
            '방어 수족관',
            '방어 어류도감',
            '방어 생선 close up',
            'yellowtail amberjack aquarium',
            'amberjack fish close up underwater',
            'japanese amberjack fish',
            'buri fish japan aquarium',
        ],
        'bushiri': [
            '부시리 수족관',
            '부시리 어류도감',
            'hiramasa aquarium fish',
            'kingfish amberjack aquarium',
            'hiramasa close up fish',
        ],
    }

    # 제목에 이 단어 있으면 스킵
    SKIP_KEYWORDS = [
        '회', '요리', '회뜨기', '초밥', 'sashimi', 'sushi', 'recipe',
        '레시피', '손질', '먹방', '낚시', 'fishing', 'catch', 'caught',
        'jigging', '쿠킹', 'cooking', 'fillet', '포뜨기',
    ]

    FRAME_INTERVAL_SEC   = 2
    MAX_VIDEOS_PER_QUERY = 5
    CONF_THRESHOLD       = 0.60   # 상향
    MIN_BOX_RATIO        = 0.15   # 프레임 면적 대비 최소 박스 비율
    IMG_SIZE             = (640, 640)
    OUTPUT_ROOT = Path(__file__).parent / 'raw_youtube'
    MODEL_PATH  = Path(__file__).parent.parent / 'models' / 'best.pt'

    TARGET_CLASS = {'bangeo': 0, 'bushiri': 1}

    parser = argparse.ArgumentParser()
    parser.add_argument('--target', choices=['bangeo', 'bushiri', 'all'], default='all')
    parser.add_argument('--max-videos', type=int, default=MAX_VIDEOS_PER_QUERY)
    parser.add_argument('--interval',   type=int, default=FRAME_INTERVAL_SEC)
    parser.add_argument('--conf',       type=float, default=CONF_THRESHOLD)
    parser.add_argument('--no-filter',  action='store_true')
    args = parser.parse_args()

    targets = list(QUERIES.keys()) if args.target == 'all' else [args.target]

    model = None
    if not args.no_filter:
        if MODEL_PATH.exists():
            print(f"모델 로드: {MODEL_PATH}")
            model = YOLO(str(MODEL_PATH))
        else:
            print(f"[경고] 모델 없음 — --no-filter 모드로 전환")

    YDL_SEARCH_OPTS = {'quiet': True, 'no_warnings': True, 'extract_flat': True}
    YDL_STREAM_OPTS = {'quiet': True, 'no_warnings': True, 'format': 'best[height<=720]/best'}

    def is_skip(title: str) -> bool:
        t = title.lower()
        return any(k in t for k in SKIP_KEYWORDS)

    def get_stream_url(video_url: str):
        try:
            with yt_dlp.YoutubeDL(YDL_STREAM_OPTS) as ydl:
                info = ydl.extract_info(video_url, download=False)
                return info.get('url')
        except Exception as e:
            print(f"  스트림 URL 실패: {e}")
            return None

    def img_hash(frame) -> str:
        return hashlib.md5(frame.tobytes()).hexdigest()[:12]

    def extract_frames(stream_url, out_dir, target_cls, interval_sec, conf):
        cap = cv2.VideoCapture(stream_url)
        if not cap.isOpened():
            print("  캡처 열기 실패")
            return 0

        fps  = cap.get(cv2.CAP_PROP_FPS) or 30
        h_px = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        w_px = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        frame_area = h_px * w_px

        step = max(1, int(fps * interval_sec))
        saved, seen, frame_idx = 0, set(), 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % step == 0:
                h = img_hash(frame)
                if h in seen:
                    frame_idx += 1
                    continue
                seen.add(h)

                keep = True
                if model is not None and target_cls is not None:
                    results = model(frame, verbose=False, conf=conf)
                    boxes = results[0].boxes
                    if boxes is None or len(boxes) == 0:
                        keep = False
                    else:
                        cls_ids  = boxes.cls.cpu().numpy().astype(int)
                        xyxy_all = boxes.xyxy.cpu().numpy()
                        keep = False
                        for cls_id, xyxy in zip(cls_ids, xyxy_all):
                            if int(cls_id) == int(target_cls):
                                bw = xyxy[2] - xyxy[0]
                                bh = xyxy[3] - xyxy[1]
                                box_area = bw * bh
                                # 프레임 대비 MIN_BOX_RATIO 이상이어야 저장
                                if frame_area > 0 and (box_area / frame_area) >= MIN_BOX_RATIO:
                                    keep = True
                                    break

                if keep:
                    img = cv2.resize(frame, IMG_SIZE)
                    fname = out_dir / f"{h}_{frame_idx:06d}.jpg"
                    cv2.imwrite(str(fname), img)
                    saved += 1

            frame_idx += 1

        cap.release()
        return saved

    total_saved = 0

    for target in targets:
        cls_id  = TARGET_CLASS.get(target) if model else None
        out_dir = OUTPUT_ROOT / target
        out_dir.mkdir(parents=True, exist_ok=True)
        print(f"\n{'='*50}\n수집 대상: {target}  ->  {out_dir}")

        for query in QUERIES[target]:
            print(f"\n[검색] {query}")
            search_url = f"ytsearch{args.max_videos}:{query}"

            try:
                with yt_dlp.YoutubeDL(YDL_SEARCH_OPTS) as ydl:
                    info    = ydl.extract_info(search_url, download=False)
                    entries = info.get('entries', [])
            except Exception as e:
                print(f"  검색 실패: {e}")
                continue

            for entry in entries:
                title   = entry.get('title', '')
                vid_id  = entry.get('id', '')
                vid_url = f"https://www.youtube.com/watch?v={vid_id}"

                if is_skip(title):
                    print(f"  [스킵] {title[:60]}")
                    continue

                print(f"  [{vid_id}] {title[:60]}")
                stream_url = get_stream_url(vid_url)
                if not stream_url:
                    continue

                n = extract_frames(stream_url, out_dir, cls_id,
                                   args.interval, args.conf)
                print(f"  -> 저장 {n}장")
                total_saved += n
                time.sleep(1)

    print(f"\n완료 — 총 {total_saved}장 저장됨")
    print(f"저장 위치: {OUTPUT_ROOT}")