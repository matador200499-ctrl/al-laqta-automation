"""
generate_script.py
يستخدم Groq API لتوليد عنوان + وصف + تاجز + سكريبت مقسّم لمشاهد.
النتيجة بتتحفظ في script.json و content.json.
"""
import json
import os
import re
import sys
import time

from openai import OpenAI

CHANNEL_STYLE = """
أنت كاتب سكريبتات لقناة يوتيوب اسمها "اللقطة - Al Laqta".
أسلوب القناة: محتوى مشوق ومحترم بعيد عن الإسفاف والعناوين المضللة (Clickbait).
النبرة: سينمائية، تحليلية، تكشف تفاصيل يغفل عنها الجمهور.
""".strip()


def build_prompt(topic: str) -> str:
    return f"""{CHANNEL_STYLE}
الموضوع: "{topic}"
اكتب سكريبت فيديو طويل واحترافي مدته 15 دقيقة كاملة (حوالي 2500-3000 كلمة عربية موزعة
على 30-35 مشهد). كل مشهد لازم يكون:
- narration: فقرة سرد طويلة بالعربية الفصحى المبسطة (80-100 كلمة) تشرح تفاصيل الموضوع بعمق.
- keywords: كلمتين أو 3 بالإنجليزية تصف مشهد فيديو حقيقي مناسب (وصف بصري عام زي "ancient library atmosphere")
- onscreen_text: جملة قصيرة (3-6 كلمات) بالعربي تظهر على الشاشة.
مهم جدًا: رجّعلي الناتج بصيغة JSON فقط وحصرًا، أول حرف في ردك لازم يكون {{ وآخر حرف لازم يكون }}.
ممنوع أي نص، شرح، أو تعليق قبل أو بعد الـ JSON، وممنوع علامات ماركداون:
{{
  "title": "عنوان جذاب لا يتجاوز 70 حرف",
  "description": "وصف الفيديو ليوتيوب، 3 إلى 5 أسطر",
  "tags": ["تاج1", "تاج2", "...حتى 12 تاج"],
  "scenes": [
    {{"narration": "...", "keywords": "...", "onscreen_text": "..."}}
  ]
}}
"""


def model_candidates(client):
    """Return active Groq models, preferring the current production replacement."""
    preferred = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b").strip()
    fallback_order = [
        preferred,
        "openai/gpt-oss-120b",
        "qwen/qwen3.6-27b",
        "openai/gpt-oss-20b",
    ]
    fallback_order = list(dict.fromkeys(model for model in fallback_order if model))

    try:
        active_ids = {model.id for model in client.models.list().data}
    except Exception as error:
        print(
            f"تحذير: تعذر قراءة قائمة نماذج Groq ({error.__class__.__name__}). "
            "سيتم استخدام النموذج الافتراضي مباشرة.",
            file=sys.stderr,
        )
        return fallback_order

    available = [model for model in fallback_order if model in active_ids]
    if not available:
        raise RuntimeError(
            "لا يوجد نموذج متاح من قائمة Groq الحالية. "
            "تحقق من GROQ_MODEL أو من صلاحيات مفتاح GROQ_API_KEY."
        )
    return available


def try_generate(client, topic, model):
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": build_prompt(topic)}],
        max_tokens=8000,
    )
    raw_text = response.choices[0].message.content.strip()
    cleaned = re.sub(r"^```json\s*|\s*```$", "", raw_text)
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)
    cleaned = re.sub(r"[\x00-\x1f]+", " ", cleaned)
    data = json.loads(cleaned, strict=False)
    if not data.get("scenes"):
        raise ValueError("لا توجد مشاهد في الناتج")
    return data, raw_text


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
    models = model_candidates(client)
    print(f"نماذج Groq المرشحة: {', '.join(models)}")

    data = None
    last_error = None
    last_raw = None
    max_attempts = 4
    for attempt in range(1, max_attempts + 1):
        model = models[(attempt - 1) % len(models)]
        try:
            print(f"محاولة رقم {attempt} من {max_attempts} باستخدام {model}...")
            data, last_raw = try_generate(client, topic, model)
            print(f"نجحت المحاولة باستخدام {model}.")
            break
        except (json.JSONDecodeError, ValueError) as error:
            last_error = error
            print(f"فشلت المحاولة {attempt}: {error}", file=sys.stderr)
            if attempt < max_attempts:
                time.sleep(3)
        except Exception as error:
            last_error = error
            print(
                f"فشل طلب Groq في المحاولة {attempt} ({error.__class__.__name__}): {error}",
                file=sys.stderr,
            )
            if attempt < max_attempts:
                time.sleep(3)

    if data is None:
        print(
            f"خطأ: فشلت كل المحاولات ({max_attempts}) في توليد JSON صحيح: {last_error}",
            file=sys.stderr,
        )
        if last_raw:
            print(last_raw, file=sys.stderr)
        sys.exit(1)

    with open("script.json", "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    with open("content.json", "w", encoding="utf-8") as file:
        json.dump(
            {"title": data["title"], "description": data["description"], "tags": data["tags"]},
            file,
            ensure_ascii=False,
            indent=2,
        )
    print(f"تم توليد سكريبت من {len(data['scenes'])} مشهد بنجاح.")


if __name__ == "__main__":
    main()
