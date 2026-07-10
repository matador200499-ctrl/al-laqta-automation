"""
generate_voice.py
يولّد تعليق صوتي عربي لكل مشهد باستخدام edge-tts (خدمة تحويل نص لصوت مجانية).

بيقرأ المشاهد من script.json، وينتج لكل مشهد ملف صوت في audio/scene_N.mp3
+ ملف durations.json فيه مدة كل مشهد بالثواني.
"""

import asyncio
import json
import os
import subprocess

VOICE = os.environ.get("TTS_VOICE", "ar-EG-ShakirNeural")


async def synthesize(text: str, out_path: str):
    import edge_tts
    communicate = edge_tts.Communicate(text, VOICE, rate="+0%")
    await communicate.save(out_path)


def get_duration(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())


async def main():
    with open("script.json", "r", encoding="utf-8") as f:
        script = json.load(f)

    os.makedirs("audio", exist_ok=True)
    durations = []

    for i, scene in enumerate(script["scenes"]):
        out_path = f"audio/scene_{i}.mp3"
        print(f"جاري توليد صوت المشهد {i + 1}/{len(script['scenes'])}...")
        await synthesize(scene["narration"], out_path)
        dur = get_duration(out_path)
        durations.append(dur)
        print(f"  المدة: {dur:.2f} ثانية")

    with open("audio/durations.json", "w", encoding="utf-8") as f:
        json.dump(durations, f)

    total = sum(durations)
    print(f"\nإجمالي مدة الصوت: {total:.1f} ثانية (~{total / 60:.1f} دقيقة)")


if __name__ == "__main__":
    asyncio.run(main())
