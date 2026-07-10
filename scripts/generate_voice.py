import asyncio
import json
import os
import edge_tts
import subprocess

async def main():
    # البحث عن الملف في المجلد الرئيسي (خارج مجلد scripts)
    input_file = "script.json"
    
    if not os.path.exists(input_file):
        print(f"خطأ: الملف {input_file} غير موجود في المجلد الرئيسي!")
        # المحاولة مرة أخرى في مجلد scripts كخطة بديلة
        input_file = "scripts/script.json"
        if not os.path.exists(input_file):
            exit(1)

    with open(input_file, "r", encoding="utf-8") as f:
        script = json.load(f)

    if not os.path.exists("audio"):
        os.makedirs("audio")

    durations = []
    for i, scene in enumerate(script["scenes"]):
        out_path = f"audio/scene_{i}.mp3"
        print(f"جاري توليد صوت المشهد {i+1}...")
        communicate = edge_tts.Communicate(scene["narration"], "ar-EG-ShakirNeural")
        await communicate.save(out_path)
        
        # حساب المدة
        result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", out_path], capture_output=True, text=True)
        dur = float(result.stdout.strip())
        durations.append(dur)

    with open("audio/durations.json", "w", encoding="utf-8") as f:
        json.dump(durations, f)

if __name__ == "__main__":
    asyncio.run(main())
