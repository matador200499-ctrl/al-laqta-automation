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
import re
import subprocess

import arabic_reshaper
from bidi.algorithm import get_display
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1920, 1080
FONT_PATH = os.environ.get("ARABIC_FONT_PATH", "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf")
FONT_CANDIDATES = (
    FONT_PATH,
    "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
)


def run(cmd: list[str]):
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def load_font(size: int):
    for path in FONT_CANDIDATES:
        if path and os.path.exists(path):
            return ImageFont.truetype(path, size)
    raise FileNotFoundError("لم يتم العثور على خط عربي مناسب")


def rtl_text(text: str):
    """استخدم محرك RAQM الحديث، مع حل بديل للإصدارات التي لا تدعمه."""
    cleaned = re.sub(r"\s+", " ", str(text)).strip()
    try:
        if ImageFont.core.HAVE_RAQM:
            return cleaned, {"direction": "rtl", "language": "ar"}
    except (AttributeError, TypeError):
        pass
    return get_display(arabic_reshaper.reshape(cleaned)), {}


def wrap_arabic(draw, text: str, font, max_width: int):
    """يقسّم النص قبل تشكيله، حتى تظل الكلمات واتجاه السطور صحيحين."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        shown, rtl_args = rtl_text(candidate)
        box = draw.textbbox((0, 0), shown, font=font, stroke_width=3, **rtl_args)
        if current and box[2] - box[0] > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def make_overlay_png(text: str, out_path: str):
    """يرسم نصًا عربيًا واضحًا، مترابطًا، وفي الاتجاه الصحيح."""
    text = re.sub(r"\s+", " ", str(text)).strip()

    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    max_width = WIDTH - 240
    font_size = 76
    while True:
        font = load_font(font_size)
        lines = wrap_arabic(draw, text, font, max_width)
        if len(lines) <= 2 or font_size <= 54:
            break
        font_size -= 4

    line_gap = 22
    rendered = []
    for line in lines:
        shown, rtl_args = rtl_text(line)
        bbox = draw.textbbox((0, 0), shown, font=font, stroke_width=3, **rtl_args)
        rendered.append((shown, rtl_args, bbox, bbox[3] - bbox[1]))

    text_block_h = sum(item[3] for item in rendered) + line_gap * max(0, len(rendered) - 1)
    pad_y = 42
    bar_h = text_block_h + pad_y * 2
    bar_y = HEIGHT - bar_h - 70
    draw.rounded_rectangle(
        [(70, bar_y), (WIDTH - 70, bar_y + bar_h)],
        radius=28,
        fill=(0, 0, 0, 205),
        outline=(255, 255, 255, 55),
        width=2,
    )

    y = bar_y + pad_y
    for shown, rtl_args, bbox, line_h in rendered:
        text_w = bbox[2] - bbox[0]
        x = (WIDTH - text_w) / 2 - bbox[0]
        draw.text(
            (x, y - bbox[1]), shown, font=font,
            fill=(255, 255, 255, 255),
            stroke_width=3, stroke_fill=(0, 0, 0, 255),
            **rtl_args,
        )
        y += line_h + line_gap

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
