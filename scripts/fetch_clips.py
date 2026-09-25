"""
fetch_clips.py
يجلب مقطعًا واحدًا لزوجين متناسقين من Pexels ثم يعيد استخدامه
في كل مشاهد الحلقة، حتى لا تتغير الشخصيات بين المشاهد.
"""

import json
import os
import shutil
import sys

import requests

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
SEARCH_URL = "https://api.pexels.com/videos/search"

# نبحث عن زوجين في لقطة واحدة ثم نستخدم نفس الفيديو في كل المشاهد.
# ده لا يضمن شخصيات بعينها من Pexels، لكنه يضمن أن كل مشاهد الحلقة
# تستخدم نفس الأشخاص فعليًا بدل اختيار أشخاص مختلفين لكل مشهد.
CHARACTER_QUERY = "young Arab couple romantic walking together"

def find_best_video_file(video: dict) -> str | None:
    files = sorted(
        [f for f in video.get("video_files", []) if f.get("width") and f["width"] >= 1280],
        key=lambda f: f["width"],
    )
    if files:
        return files[0]["link"]
    files = video.get("video_files", [])
    return files[0]["link"] if files else None


def search_clip(query: str) -> str | None:
    headers = {"Authorization": PEXELS_API_KEY}
    params = {
        "query": query,
        "orientation": "landscape",
        "size": "medium",
        "per_page": 10,
    }
    resp = requests.get(SEARCH_URL, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    videos = resp.json().get("videos", [])
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

    base_clip = "clips/character_base.mp4"
    print(f"جاري اختيار فيديو أساسي ثابت للشخصيات: {CHARACTER_QUERY}")

    url = search_clip(CHARACTER_QUERY)
    if not url:
        print("لم توجد نتيجة للبحث الأساسي، جاري تجربة بحث أوسع...")
        url = search_clip("young couple romantic") or search_clip("romantic couple")

    if not url:
        print("خطأ: تعذر إيجاد فيديو أساسي للشخصيات", file=sys.stderr)
        sys.exit(1)

    download(url, base_clip)
    print(f"تم تحميل الفيديو الأساسي: {base_clip}")

    # نفس الملف بالضبط لكل مشهد = نفس الشخصيات في الحلقة كلها.
    for i, _scene in enumerate(script["scenes"]):
        out_path = f"clips/scene_{i}.mp4"
        shutil.copyfile(base_clip, out_path)
        print(f"تم تثبيت نفس الشخصيات في المشهد {i + 1}: {out_path}")


if __name__ == "__main__":
    main()
