import json
import os
import re

from groq import Groq


MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
DEFAULT_TOPIC = "سلسلة: عمر وليلى | الحلقة 1 | لقاء غير متوقع يغير كل شيء"


def get_topic() -> str:
    if os.path.exists("manual_topic.txt"):
        try:
            topic = open("manual_topic.txt", "r", encoding="utf-8").read().strip()
            if topic:
                return topic
        except OSError:
            pass
    queued_topic = os.environ.get("VIDEO_TOPIC", "").strip()
    if queued_topic:
        return queued_topic
    return DEFAULT_TOPIC


def parse_episode(topic: str):
    match = re.search(r"سلسلة\s*:\s*([^|]+)\|\s*الحلقة\s*(\d+)\s*\|\s*(.+)", topic)
    if not match:
        return {"series": "قصة لم تنتهِ", "episode": 1, "plot": topic.strip()}
    return {"series": match.group(1).strip(), "episode": int(match.group(2)), "plot": match.group(3).strip()}

def parse_json_response(raw: str) -> dict:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Groq response did not contain a JSON object")
    data = json.loads(text[start:end + 1])
    scenes = data.get("scenes")
    if not isinstance(scenes, list) or len(scenes) < 6 or len(scenes) > 7:
        raise ValueError("Generated JSON must contain 6 or 7 scenes")
    required = ("narration", "onscreen_text", "keywords")
    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict) or any(not str(scene.get(key, "")).strip() for key in required):
            raise ValueError(f"Scene {index} is missing required fields")
    data["title"] = str(data.get("title") or "فيديو جديد - اللقطة").strip()
    data["description"] = str(data.get("description") or "").strip()
    tags = data.get("tags", [])
    data["tags"] = tags if isinstance(tags, list) else []
    return data


def build_prompt(topic: str) -> str:
    info = parse_episode(topic)
    return f"""
أنت كاتب ومخرج محتوى Shorts لقناة يوتيوب عربية اسمها "اللقطة".
نريد قصة درامية رومانسية أصلية ومترابطة، وليست أغنية.

معلومات الحلقة:
- السلسلة: {info["series"]}
- رقم الحلقة: {info["episode"]}
- محور الحلقة: {info["plot"]}

قواعد مهمة:
1) ابدأ بأقوى لحظة أو سؤال خلال أول ثانيتين، بدون مقدمة أو ترحيب.
2) اجعل القصة مفهومة حتى لمن يشاهد هذه الحلقة وحدها.
3) تصاعد واضح: Hook ثم حدث ثم أزمة أو مفاجأة ثم نهاية تشجع على الحلقة التالية.
4) استخدم شخصيات ثابتة وأسماء واضحة وحافظ على استمرارية السلسلة.
5) العامية المصرية السهلة والمفهومة عربيًا.
6) إجمالي الكلام مناسب لفيديو 45 إلى 60 ثانية تقريبًا.
7) من 6 إلى 7 مشاهد قصيرة.
8) onscreen_text قصير جدًا وواضح، من 4 إلى 8 كلمات، ليُقرأ على الهاتف والتلفزيون.
9) لا تستخدم شخصيات عامة أو أغانٍ أو نصوصًا محمية بحقوق نشر.
10) اختم بتشويق طبيعي للحلقة التالية، بدون طلب مبالغ فيه للاشتراك.

أعد JSON صحيح فقط بدون Markdown.
المفاتيح:
- title: عنوان جذاب لا يزيد عن 80 حرفًا، ويحتوي على اسم السلسلة ورقم الحلقة.
- description: وصف قصير، وينتهي بجملة "الحلقة التالية من السلسلة قريبًا."
- tags: من 5 إلى 8 وسوم عربية مناسبة.
- scenes: من 6 إلى 7 مشاهد.

كل مشهد يحتوي على:
- narration: من جملة إلى ثلاث جمل قصيرة.
- onscreen_text: عبارة عربية قصيرة جدًا.
- keywords: من 2 إلى 5 كلمات إنجليزية مناسبة للقطات رومانسية سينمائية.

لا تجعل المشاهد مجرد وصف للصور؛ اجعل كل مشهد يدفع القصة للأمام.
""".strip()
def request_generation(client: Groq, prompt: str):
    return client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=2200,
    )


def repair_json(client: Groq, raw: str) -> dict:
    repair_prompt = f"""
أصلح النص التالي وأعده كـ JSON صحيح نحويًا فقط.
مهم جدًا: لا تضف أي شرح أو Markdown. لا تغيّر المحتوى إلا لإصلاح JSON.
يجب أن يحتوي الناتج على: title, description, tags, scenes.
وكل scene يجب أن يحتوي على: narration, onscreen_text, keywords.
يجب إغلاق كل علامات الاقتباس والأقواس، ووضع فاصلة بين كل خاصيتين متتاليتين.

النص المراد إصلاحه:
{raw}
""".strip()
    repaired = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": repair_prompt}],
        temperature=0.0,
        max_tokens=2200,
    )
    return parse_json_response(repaired.choices[0].message.content or "")


def generate_with_retry(client: Groq, prompt: str) -> dict:
    last_error = None
    raw = ""
    for attempt in range(2):
        try:
            completion = request_generation(client, prompt)
            raw = completion.choices[0].message.content or ""
            return parse_json_response(raw)
        except Exception as error:
            last_error = error
            print(f"Generation attempt {attempt + 1} returned invalid JSON: {error}")
    for attempt in range(2):
        try:
            print(f"Sending JSON repair request ({attempt + 1}/2)...")
            return repair_json(client, raw)
        except Exception as error:
            last_error = error
            print(f"Repair attempt {attempt + 1} failed: {error}")
    raise RuntimeError(f"Groq could not produce valid script JSON after retries: {last_error}")


def main():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")
    topic = get_topic()
    print(f"Generating for topic: {topic} with model {MODEL}")
    client = Groq(api_key=api_key)
    data = generate_with_retry(client, build_prompt(topic))

    script = {"topic": topic, "scenes": data["scenes"]}
    content = {"title": data["title"], "description": data["description"], "tags": data["tags"]}

    os.makedirs("output", exist_ok=True)
    with open("script.json", "w", encoding="utf-8") as file:
        json.dump(script, file, ensure_ascii=False, indent=2)
    with open("content.json", "w", encoding="utf-8") as file:
        json.dump(content, file, ensure_ascii=False, indent=2)

    narration = "\n\n".join(scene["narration"] for scene in script["scenes"])
    for path in ("script.txt", "output/script.txt", "output/story.txt"):
        with open(path, "w", encoding="utf-8") as file:
            file.write(narration)
    print(f"DONE: generated {len(script['scenes'])} scenes")


if __name__ == "__main__":
    main()
