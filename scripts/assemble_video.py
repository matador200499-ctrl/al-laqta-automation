"""
assemble_video.py
يجمّع الفيديو النهائي:
1. لكل مشهد: يقص/يكرر مقطع الستوك عشان يطابق مدة الصوت بالظبط + يحوّله لـ 1920x1080
2. يولّد صورة شفافة (PNG) فيها النص العربي المكتوب على الشاشة لكل مشهد (باستخدام PIL
   مع دعم تشكيل الحروف العربي)، ويظهرها كـ overlay فوق المقطع
3. يلزّق كل المشاهد مع بعض بالترتيب (concat)
4. يلزّق كل ملفات الصوت مع بعض ويضيفهم كـ trak صوت للفيديو النهائي

الناتج: final_video.mp4
"""

import json
import os
import subprocess

import arabic_reshaper
from bidi.layout import get_display
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1920, 1080
FONT_PATH = os.environ.get("ARABIC_FONT_PATH", "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf")


def run(cmd: list[str]):
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def make_overlay_png(text: str, out_path: str):
    """يرسم شريط نص أسفل الشاشة بالعربي (تشكيل صحيح للحروف + اتجاه من اليمين لليسار)."""
    reshaped = arabic_reshaper.reshape(text)
    bidi_text = get_display(reshaped)

    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_size = 64
    font = ImageFont.truetype(FONT_PATH, font_size)

    bbox = draw.textbbox((0, 0), bidi_text, font=font)
    text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]

    bar_h = text_h + 80
    bar_y = HEIGHT - bar_h - 60
    draw.rectangle([(0, bar_y), (WIDTH, bar_y + bar_h)], fill=(0, 0, 0, 160))

    x = (WIDTH - text_w) / 2
    y = bar_y + (bar_h - text_h) / 2 - bbox[1]
    draw.text((x, y), bidi_text, font=font, fill=(255, 255, 255, 255))

    img.save(out_path)


def prepare_scene(i: int, duration: float):
    clip_in = f"clips/scene_{i}.mp4"
    overlay_png = f"overlays/scene_{i}.png"
    scene_out = f"segments/scene_{i}.mp4"

    if not os.path.exists(clip_in):
        # لو المقطع مفقود، اعمل خلفية سودة بديلة بنفس المدة
        run([
            "ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c=black:s={WIDTH}x{HEIGHT}:d={duration}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", clip_in.replace("clips", "segments_tmp"),
        ])
        clip_in = clip_in.replace("clips", "segments_tmp")

    # يقص/يكرر المقطع عشان يطابق مدة الصوت بالظبط، ويحوّله لمقاس موحد
    run([
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", clip_in,
        "-i", overlay_png,
        "-filter_complex",
        f"[0:v]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},setsar=1[bg];[bg][1:v]overlay=0:0[outv]",
        "-map", "[outv]", "-t", str(duration),
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        scene_out,
    ])
    return scene_out


def main():
    with open("script.json", "r", encoding="utf-8") as f:
        script = json.load(f)
    with open("audio/durations.json", "r", encoding="utf-8") as f:
        durations = json.load(f)

    os.makedirs("overlays", exist_ok=True)
    os.makedirs("segments", exist_ok=True)
    os.makedirs("segments_tmp", exist_ok=True)

    scene_files = []
    for i, scene in enumerate(script["scenes"]):
        make_overlay_png(scene["onscreen_text"], f"overlays/scene_{i}.png")
        scene_out = prepare_scene(i, durations[i])
        scene_files.append(scene_out)

    # 1) لزق كل مقاطع الفيديو مع بعض
    with open("segments/concat_list.txt", "w") as f:
        for s in scene_files:
            f.write(f"file '{os.path.abspath(s)}'\n")
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "segments/concat_list.txt",
        "-c", "copy", "video_only.mp4",
    ])

    # 2) لزق كل ملفات الصوت مع بعض
    with open("audio/concat_list.txt", "w") as f:
        for i in range(len(script["scenes"])):
            f.write(f"file '{os.path.abspath(f'audio/scene_{i}.mp3')}'\n")
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "audio/concat_list.txt",
        "-c", "copy", "full_audio.mp3",
    ])

    # 3) دمج الصوت مع الفيديو
    run([
        "ffmpeg", "-y", "-i", "video_only.mp4", "-i", "full_audio.mp3",
        "-c:v", "copy", "-c:a", "aac", "-shortest", "final_video.mp4",
    ])

    print("تم إنشاء الفيديو النهائي: final_video.mp4")


if __name__ == "__main__":
    main()
