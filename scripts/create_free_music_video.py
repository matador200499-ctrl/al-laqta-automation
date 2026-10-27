#!/usr/bin/env python3
"""Build a YouTube music video from a freely generated song already saved in music_input/song.mp3.

Song generation is done manually with the public ACE-Step 1.5 Hugging Face Space.
This keeps generation free and avoids paid music APIs. This script handles visuals and video assembly.
"""
import json
import os
import subprocess
from pathlib import Path
import requests

ROOT = Path(".")
SONG_PATH = ROOT / "music_input" / "song.mp3"
WORK = ROOT / "music_work"
WORK.mkdir(exist_ok=True)

PEXELS_KEY = os.environ.get("PEXELS_API_KEY", "").strip()
SONG_TITLE = os.environ.get("SONG_TITLE", "").strip() or "أغنية مصرية جديدة"
SONG_THEME = os.environ.get("SONG_THEME", "").strip() or "أغنية مصرية أصلية"
PEXELS_SEARCH = "https://api.pexels.com/videos/search"

if not SONG_PATH.is_file():
    raise RuntimeError(
        "Missing music_input/song.mp3. Generate a song for free in the official ACE-Step Space, "
        "download it as MP3, then upload it to this repository at music_input/song.mp3."
    )
if SONG_PATH.stat().st_size < 50_000:
    raise RuntimeError("music_input/song.mp3 is too small to be a valid song file.")
if not PEXELS_KEY:
    raise RuntimeError("PEXELS_API_KEY is missing from GitHub Actions Secrets.")

def run(cmd):
    subprocess.run(cmd, check=True)

def ffprobe_duration(path):
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(path),
        ],
        check=True, capture_output=True, text=True,
    )
    duration = float(result.stdout.strip())
    if duration < 10:
        raise RuntimeError("Song duration is unexpectedly short.")
    return duration

def search_and_download(query, index):
    resp = requests.get(
        PEXELS_SEARCH,
        headers={"Authorization": PEXELS_KEY},
        params={"query": query, "orientation": "portrait", "size": "medium", "per_page": 8},
        timeout=45,
    )
    resp.raise_for_status()
    videos = resp.json().get("videos", [])
    if not videos and query != "cinematic Cairo city night":
        resp = requests.get(
            PEXELS_SEARCH,
            headers={"Authorization": PEXELS_KEY},
            params={"query": "cinematic Cairo city night", "orientation": "portrait", "size": "medium", "per_page": 8},
            timeout=45,
        )
        resp.raise_for_status()
        videos = resp.json().get("videos", [])
    if not videos:
        raise RuntimeError("Pexels did not return clips for query: " + query)

    # Prefer portrait clips and decent resolution; landscape clips are cropped to vertical later.
    def rank(video):
        files = [f for f in video.get("video_files", []) if f.get("link")]
        if not files:
            return (-1, -1)
        best = max(files, key=lambda f: int(f.get("height") or 0))
        portrait = int(best.get("height") or 0) >= int(best.get("width") or 0)
        return (1 if portrait else 0, int(best.get("height") or 0))

    videos = sorted(videos, key=rank, reverse=True)
    chosen = videos[(index - 1) % min(len(videos), 4)]
    files = [f for f in chosen.get("video_files", []) if f.get("link")]
    if not files:
        raise RuntimeError("Pexels result has no downloadable video.")
    file_info = max(files, key=lambda f: int(f.get("height") or 0))
    url = file_info["link"]
    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()
    raw_path = WORK / ("raw_{:02d}.mp4".format(index))
    with raw_path.open("wb") as out:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                out.write(chunk)
    return raw_path

def main():
    duration = ffprobe_duration(SONG_PATH)
    # Use a set of reusable, portrait-oriented cinematic themes. Keep this independent from story/info queues.
    queries = [
        "Cairo city night cinematic",
        "couple walking city at sunset",
        "romantic city lights bokeh",
        "rain on city street night",
        "sunrise over city skyline",
        "coffee shop warm lights",
        "Nile river Cairo evening",
        "night drive city lights",
        "old city street sunset",
        "cinematic clouds golden hour",
        "abstract colorful concert lights",
        "stars night sky city",
    ]
    normalized = []
    for i, query in enumerate(queries, 1):
        raw = search_and_download(query, i)
        normalized_path = WORK / ("scene_{:02d}.mp4".format(i))
        run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-i", str(raw), "-t", "12",
            "-vf", "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1,fps=25,format=yuv420p",
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "25",
            "-movflags", "+faststart", str(normalized_path),
        ])
        normalized.append(normalized_path)
        print("Prepared portrait clip {}/{}".format(i, len(queries)), flush=True)

    concat_file = WORK / "concat.txt"
    concat_file.write_text(
        "".join("file '{}'\n".format(path.resolve().as_posix()) for path in normalized),
        encoding="utf-8",
    )
    visuals_path = WORK / "visuals.mp4"
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c", "copy", "-an", str(visuals_path),
    ])

    # Loop the visuals if needed and stop exactly when the song ends.
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-stream_loop", "-1", "-i", str(visuals_path), "-i", str(SONG_PATH),
        "-map", "0:v:0", "-map", "1:a:0",
        "-t", str(duration), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart", "final_music_video.mp4",
    ])

    music_hashtags = ["#اللقطة", "#أغاني_مصرية", "#أغاني_عربية", "#موسيقى", "#Shorts"]
    if any(word in SONG_THEME for word in ("رومانسي", "حب", "عاطفي", "حنين", "عمر وسلمى", "عمر وسلما")):
        music_hashtags.insert(3, "#أغاني_رومانسية")
    content = {
        "title": SONG_TITLE[:90],
        "description": (
            "🎵 " + SONG_TITLE + "\n\n"
            + "أغنية عربية أصلية من قناة اللقطة.\n"
            + "موضوع الأغنية: " + SONG_THEME + ".\n\n"
            + "❤️ لو الأغنية عجبتك، اعمل إعجاب واكتب لنا رأيك في التعليقات.\n\n"
            + " ".join(music_hashtags)
        ),
        "tags": ["أغاني", "أغاني مصرية", "أغاني عربية", "موسيقى", "كليب", "أغاني جديدة", "موسيقى رومانسية", "ACE-Step"],
        "hashtags": music_hashtags,
        "category_id": "10",
        "content_type": "music",
    }
    (ROOT / "content.json").write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Free music video assembled successfully.", flush=True)
    print("Duration: {:.1f} seconds".format(duration), flush=True)
    print("Output: final_music_video.mp4", flush=True)

if __name__ == "__main__":
    main()
