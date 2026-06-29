if __name__ == '__main__':
    import sys, io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    from pathlib import Path
    import torch
    import open_clip
    from PIL import Image

    REVIEWED_DIR = Path(__file__).parent.parent / 'data' / 'reviewed'
    THRESH = 0.22

    DESCRIPTIONS = {
        'bangeo': [
            "whole live yellowtail amberjack fish with symmetric tail fin",
            "Japanese amberjack buri fish with thick yellow stripe on body",
            "live whole amberjack fish in fish tank aquarium",
            "whole fish with rounded stocky body",
        ],
        'bushiri': [
            "whole live hiramasa kingfish with elongated slender body",
            "hiramasa fish with upper tail fin longer than lower",
            "live yellowtail kingfish in aquarium tank",
            "whole fish with streamlined elongated body",
        ],
    }

    NEGATIVE = [
        "sashimi sliced raw fish on plate",
        "person holding fishing rod",
        "cooked fish dish on table",
        "fish fillet without head",
        "fishing boat sea",
        "human hands close up",
    ]

    print("CLIP 모델 로딩 중...")
    model, _, preprocess = open_clip.create_model_and_transforms(
        'ViT-B-32', pretrained='openai'
    )
    tokenizer = open_clip.get_tokenizer('ViT-B-32')
    model.eval()
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model = model.to(device)
    print(f"디바이스: {device}\n")

    def score_image(img_path, pos_texts, neg_texts):
        try:
            image = preprocess(Image.open(img_path).convert('RGB')).unsqueeze(0).to(device)
        except Exception:
            return None, None
        all_texts = pos_texts + neg_texts
        tokens = tokenizer(all_texts).to(device)
        with torch.no_grad():
            img_feat = model.encode_image(image)
            txt_feat = model.encode_text(tokens)
            img_feat = img_feat / img_feat.norm(dim=-1, keepdim=True)
            txt_feat = txt_feat / txt_feat.norm(dim=-1, keepdim=True)
            sims = (img_feat @ txt_feat.T).squeeze(0).cpu().tolist()
        pos_score = max(sims[:len(pos_texts)])
        neg_score = max(sims[len(pos_texts):])
        return pos_score, neg_score

    for cls, pos_texts in DESCRIPTIONS.items():
        img_dir = REVIEWED_DIR / cls
        if not img_dir.exists():
            continue
        images = sorted(img_dir.glob('*.jpg')) + sorted(img_dir.glob('*.png')) + sorted(img_dir.glob('*.jpeg'))
        if not images:
            continue

        print(f"{'='*55}")
        print(f"[{cls}] {len(images)}장 분석 중...")
        print(f"{'='*55}")

        results = []
        for img_path in images:
            pos, neg = score_image(img_path, pos_texts, NEGATIVE)
            if pos is None:
                continue
            net = pos - neg
            results.append((net, pos, neg, img_path.name))
        results.sort(reverse=True)

        good = [r for r in results if r[0] >= THRESH]
        bad  = [r for r in results if r[0] < THRESH]

        print(f"\n[OK] 정합 {len(good)}장 (net >= {THRESH})")
        for net, pos, neg, name in good[:15]:
            print(f"  {name[:36]:<37} net={net:+.3f}  pos={pos:.3f}  neg={neg:.3f}")
        if len(good) > 15:
            print(f"  ... 외 {len(good)-15}장")

        print(f"\n[??] 의심  {len(bad)}장 (net < {THRESH})")
        for net, pos, neg, name in bad:
            print(f"  {name[:36]:<37} net={net:+.3f}  pos={pos:.3f}  neg={neg:.3f}")
        print()