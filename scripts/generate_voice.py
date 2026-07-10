import asyncio
import json
import os
import subprocess

# هذا السكريبت سيقرأ من المجلد الرئيسي مباشرة لضمان عدم ضياع الملفات
INPUT_FILE = "script.json"
AUDIO_DIR = "audio"
OUTPUT_DURATIONS = "audio/durations.json"

async def synthesize(text: str, out_path: str):
    import edge_tts
    # استخدام المسار كما هو دون تعقيدات
    communicate = edge_tts.Communicate(text, "ar-EG-ShakirNeural", rate="+0%")
    await communicate.save(out_path)

def get_duration(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())

async def main():
    # التأكد من وجود المجلد
    if not os.path.exists(AUDIO_DIR):
        os.makedirs(AUDIO_DIR)

    # قراءة الملف من المجلد الرئيسي
    if not os.path.exists(INPUT_FILE):
        print(f"خطأ: الملف {INPUT_FILE} غير موجود في المجلد الرئيسي!")
        exit(1)

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        script = json.load(f)

    durations = []
    for i, scene in enumerate(script["scenes"]):
        out_path = f"{AUDIO_DIR}/scene_{i}.mp3"
        print(f"جاري توليد صوت المشهد {i + 1}...")
        await synthesize(scene["narration"], out_path)
        dur = get_duration(out_path)
        durations.append(dur)

    with open(OUTPUT_DURATIONS, "w", encoding="utf-8") as f:
        json.dump(durations, f)
    
    print("تم توليد الصوت والمدد بنجاح.")

if __name__ == "__main__":
    asyncio.run(main())
