import asyncio
import json
import os
import subprocess
from pathlib import Path

# تحديد المسار الرئيسي للمشروع عشان أي ملف يدور عليه يلاقيه
BASE_DIR = Path(__file__).resolve().parent.parent
VOICE = os.environ.get("TTS_VOICE", "ar-EG-ShakirNeural")

async def synthesize(text: str, out_path: str):
    import edge_tts
    # التأكد أن المجلد اللي هيتحفظ فيه الصوت موجود
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
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
    # استخدام المسار الكامل للملف لضمان العثور عليه
    script_path = BASE_DIR / "script.json"
    
    with open(script_path, "r", encoding="utf-8") as f:
        script = json.load(f)

    # إنشاء المجلدات باستخدام المسار الكامل
    audio_dir = BASE_DIR / "audio"
    os.makedirs(audio_dir, exist_ok=True)
    
    durations = []

    for i, scene in enumerate(script["scenes"]):
        out_path = audio_dir / f"scene_{i}.mp3"
        print(f"جاري توليد صوت المشهد {i + 1}/{len(script['scenes'])}...")
        await synthesize(scene["narration"], str(out_path))
        dur = get_duration(str(out_path))
        durations.append(dur)
        print(f"  المدة: {dur:.2f} ثانية")

    # حفظ ملف المدد في مجلد الـ audio
    durations_path = audio_dir / "durations.json"
    with open(durations_path, "w", encoding="utf-8") as f:
        json.dump(durations, f)

    total = sum(durations)
    print(f"\nإجمالي مدة الصوت: {total:.1f} ثانية")

if __name__ == "__main__":
    asyncio.run(main())
