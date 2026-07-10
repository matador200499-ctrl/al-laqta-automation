"""
generate_script.py
يستخدم Groq API لتوليد عنوان + وصف + تاجز + سكريبت مقسّم لمشاهد.
النتيجة بتتحفظ في script.json و content.json.
"""
import os
import sys
import json
import re
from openai import OpenAI

CHANNEL_STYLE = """
أنت كاتب سكريبتات لقناة يوتيوب اسمها "اللقطة - Al Laqta".
أسلوب القناة: محتوى مشوق ومحترم بعيد عن الإسفاف والعناوين المضللة (Clickbait).
النبرة: سينمائية، تحليلية، تكشف تفاصيل يغفل عنها الجمهور.
""".strip()

def build_prompt(topic: str) -> str:
    return f"""{CHANNEL_STYLE}
الموضوع: "{topic}"
اكتب سكريبت فيديو طوله يكفي لنطق صوتي مدته من 3 إلى 4 دقائق (حوالي 550-700 كلمة عربية موزعة
على 9-12 مشهد). كل مشهد لازم يكون:
- narration: فقرة سرد بالعربية الفصحى المبسطة (50-80 كلمة)
- keywords: كلمتين أو 3 بالإنجليزية تصف مشهد فيديو حقيقي مناسب (وصف بصري عام زي "city traffic aerial")
- onscreen_text: جملة قصيرة جدًا (3-6 كلمات) بالعربي تتكتب على الشاشة
رجّعلي الناتج بصيغة JSON فقط بدون أي نص إضافي قبله أو بعده، وبدون علامات ماركداون:
{{
  "title": "عنوان جذاب لا يتجاوز 70 حرف",
  "description": "وصف الفيديو ليوتيوب، 3 إلى 5 أسطر",
  "tags": ["تاج1", "تاج2", "...حتى 12 تاج"],
  "scenes": [
    {{"narration": "...", "keywords": "...", "onscreen_text": "..."}}
  ]
}}
"""

def main():
    topic = os.environ.get("VIDEO_TOPIC")
    if not topic:
        print("خطأ: لازم تحدد VIDEO_TOPIC", file=sys.stderr)
        sys.exit(1)
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("خطأ: GROQ_API_KEY غير موجود", file=sys.stderr)
        sys.exit(1)
    client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": build_prompt(topic)}],
        max_tokens=8000,
        response_format={"type": "json_object"},
    )
    )
   raw_text = response.choices[0].message.content.strip()
    cleaned = re.sub(r"^```json\s*|\s*```$", "", raw_text)
    # استخراج الجزء بين أول { وآخر } فقط، وتنظيف الرموز التالفة
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)
    cleaned = re.sub(r"[\x00-\x1f]+", " ", cleaned)
    try:
        data = json.loads(cleaned, strict=False)
    except json.JSONDecodeError as e:
        print(f"خطأ: تعذر تفسير مخرجات Groq كـ JSON: {e}", file=sys.stderr)
        print(raw_text, file=sys.stderr)
        sys.exit(1)
    if not data.get("scenes"):
        print("خطأ: لا توجد مشاهد في الناتج", file=sys.stderr)
        sys.exit(1)
    with open("script.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    with open("content.json", "w", encoding="utf-8") as f:
        json.dump(
            {"title": data["title"], "description": data["description"], "tags": data["tags"]},
            f, ensure_ascii=False, indent=2,
        )
    print(f"تم توليد سكريبت من {len(data['scenes'])} مشهد بنجاح.")

if __name__ == "__main__":
    main()
