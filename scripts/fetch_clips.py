"""
fetch_clips.py
يجلب مقطع فيديو ستوك مجاني (بدون حقوق) من Pexels لكل مشهد في script.json،
بناءً على كلمات البحث (keywords) اللي ولّدها Claude لكل مشهد.

يحتاج PEXELS_API_KEY (مجاني - تسجيل في https://www.pexels.com/api/).
النتيجة: clips/scene_0.mp4, clips/scene_1.mp4, ...
"""

import json
import os
import sys
import requests

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
SEARCH_URL = "https://api.pexels.com/videos/search"


def find_best_video_file(video: dict) -> str | None:
    """يختار أفضل جودة متاحة بدقة HD تقريبًا (1280x720 أو أعلى) لتقليل حجم التحميل."""
    files = sorted(
        [f for f in video["video_files"] if f.get("width") and f["width"] >= 1280],
        key=lambda f: f["width"],
    )
    if files:
        return files[0]["link"]
    # fallback لأي جودة متاحة لو مفيش HD
    if video["video_files"]:
        return video["video_files"][0]["link"]
    return None


def search_clip(keywords: str) -> str | None:
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": keywords, "orientation": "landscape", "size": "medium", "per_page": 5}
    resp = requests.get(SEARCH_URL, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    videos = data.get("videos", [])
    if not videos:
        return None
    return find_best_video_file(videos[0])


def download(url: str, out_path: str):
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)


def main():
    if not PEXELS_API_KEY:
        print("خطأ: PEXELS_API_KEY غير موجود", file=sys.stderr)
        sys.exit(1)

    with open("script.json", "r", encoding="utf-8") as f:
        script = json.load(f)

    os.makedirs("clips", exist_ok=True)

    for i, scene in enumerate(script["scenes"]):
        keywords = scene["keywords"]
        out_path = f"clips/scene_{i}.mp4"
        print(f"جاري البحث عن مقطع للمشهد {i + 1}: \"{keywords}\"...")

        url = search_clip(keywords)
        if not url:
            # لو مفيش نتيجة، جرّب كلمة بحث عامة أوسع كبديل
            print(f"  لا توجد نتائج لـ \"{keywords}\"، جاري المحاولة بكلمة أعم...")
            fallback_keyword = keywords.split()[0] if keywords.split() else "abstract background"
            url = search_clip(fallback_keyword) or search_clip("abstract background")

        if not url:
            print(f"  تحذير: تعذر إيجاد مقطع للمشهد {i + 1}، هيتم تخطيه", file=sys.stderr)
            continue

        download(url, out_path)
        print(f"  تم التحميل: {out_path}")


if __name__ == "__main__":
    main()
