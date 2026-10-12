"""
generate_voice.py
يولّد تعليقًا صوتيًا عربيًا لكل مشهد باستخدام Edge TTS، مع بديل Google TTS
إذا تعذّر الوصول إلى خدمة Edge. ينتج audio/scene_N.mp3 وملف مدد المشاهد.
"""

import asyncio
import json
import os
import subprocess

VOICE = os.environ.get("TTS_VOICE", "ar-EG-ShakirNeural")
MIN_AUDIO_BYTES = 512


def remove_partial_file(path: str) -> None:
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError as error:
        print(f"تعذر حذف ملف صوت غير مكتمل {path}: {error}")


def validate_audio_file(path: str) -> None:
    if not os.path.isfile(path):
        raise RuntimeError("خدمة الصوت لم تنشئ الملف")
    if os.path.getsize(path) < MIN_AUDIO_BYTES:
        raise RuntimeError("ملف الصوت الناتج فارغ أو غير مكتمل")


async def synthesize(text: str, out_path: str) -> None:
    """Try Edge TTS twice, then fall back to Google Translate TTS."""
    import edge_tts

    edge_error = None
    for attempt in range(1, 3):
        remove_partial_file(out_path)
        try:
            communicate = edge_tts.Communicate(text, VOICE, rate="+0%")
            await communicate.save(out_path)
            validate_audio_file(out_path)
            print(f"  تم توليد الصوت باستخدام Edge TTS (المحاولة {attempt})")
            return
        except Exception as error:
            edge_error = error
            remove_partial_file(out_path)
            print(
                f"  فشل Edge TTS في المحاولة {attempt}/2: "
                f"{type(error).__name__}: {error}"
            )
            if attempt < 2:
                await asyncio.sleep(2 * attempt)

    print("  جاري استخدام بديل الصوت Google TTS...")
    try:
        from gtts import gTTS

        fallback_tld = os.environ.get("GTTS_TLD", "com")
        tts = gTTS(text=text, lang="ar", tld=fallback_tld, slow=False)
        await asyncio.to_thread(tts.save, out_path)
        validate_audio_file(out_path)
        print("  تم توليد الصوت باستخدام Google TTS كبديل.")
    except Exception as fallback_error:
        remove_partial_file(out_path)
        raise RuntimeError(
            "فشل توليد الصوت عبر Edge TTS والبديل Google TTS. "
            f"Edge TTS: {edge_error}; Google TTS: {fallback_error}"
        ) from fallback_error


def get_duration(path: str) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", path,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    duration = float(result.stdout.strip())
    if duration <= 0:
        raise RuntimeError(f"مدة صوت غير صالحة في الملف: {path}")
    return duration


async def main() -> None:
    with open("script.json", "r", encoding="utf-8") as file:
        script = json.load(file)

    scenes = script.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise RuntimeError("script.json لا يحتوي على مشاهد صالحة لتوليد الصوت")

    os.makedirs("audio", exist_ok=True)
    durations = []

    for i, scene in enumerate(scenes):
        narration = str(scene.get("narration", "")).strip()
        if not narration:
            raise RuntimeError(f"المشهد {i + 1} لا يحتوي على نص للتعليق الصوتي")

        out_path = f"audio/scene_{i}.mp3"
        print(f"جاري توليد صوت المشهد {i + 1}/{len(scenes)}...")
        await synthesize(narration, out_path)
        duration = get_duration(out_path)
        durations.append(duration)
        print(f"  المدة: {duration:.2f} ثانية")

    with open("audio/durations.json", "w", encoding="utf-8") as file:
        json.dump(durations, file)

    total = sum(durations)
    print(f"\nإجمالي مدة الصوت: {total:.1f} ثانية (~{total / 60:.1f} دقيقة)")


if __name__ == "__main__":
    asyncio.run(main())
