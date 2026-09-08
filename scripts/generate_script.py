import json
import os
import re

from groq import Groq


MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
DEFAULT_TOPIC = "غرائب وألغاز علمية مذهلة"


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
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("Generated JSON does not contain scenes")

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
    return f"""
اكتب سيناريو فيديو عربي مدته نحو 60 ثانية بالعامية المصرية عن: {topic}.
ابدأ بهوك قوي، اذكر 3 نقاط أو صفات مفيدة، واختم بسؤال يشجع المشاهد على التعليق.

أعد JSON صحيح فقط بدون Markdown أو أي نص قبله أو بعده.
استخدم المفاتيح التالية فقط:
- title: عنوان عربي جذاب لا يزيد عن 90 حرفًا
- description: وصف عربي قصير للفيديو
- tags: قائمة من 3 إلى 5 وسوم عربية
- scenes: قائمة من 6 أو 7 مشاهد

كل مشهد يجب أن يحتوي على:
- narration: نص التعليق الصوتي بالعامية المصرية
- onscreen_text: عبارة عربية واضحة من 4 إلى 8 كلمات
- keywords: من 2 إلى 5 كلمات إنجليزية مناسبة للبحث عن فيديوهات Pexels

شكل JSON المطلوب:
{{
  "title": "عنوان عربي جذاب",
  "description": "وصف عربي قصير",
  "tags": ["وسم1", "وسم2", "وسم3"],
  "scenes": [
    {{
      "narration": "نص التعليق الصوتي",
      "onscreen_text": "عبارة قصيرة وواضحة",
      "keywords": "phone vibration psychology"
    }}
  ]
}}

قسّم السيناريو إلى 6 أو 7 مشاهد. اجعل مجموع التعليق الصوتي مناسبًا لنحو 60 ثانية، من دون حشو أو تكرار.
اكتب onscreen_text بالعربية الصحيحة فقط، من دون حروف مفصولة أو كلمات معكوسة،
واجعلها مختصرة جدًا حتى تظهر بخط كبير وواضح على شاشة الهاتف.
""".strip()


def request_generation(client: Groq, prompt: str):
    # Do not use provider-side response_format here. The GPT-OSS model can
    # reject strict JSON validation with json_validate_failed even when the
    # prompt itself is valid. We validate and repair JSON locally instead.
    return client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1800,
    )


def repair_json(client: Groq, raw: str) -> dict:
    repair_prompt = f"""
حوّل النص التالي إلى JSON صحيح فقط، بدون Markdown أو أي نص خارج JSON.
يجب أن يحتوي JSON على title و description و tags و scenes.
كل scene يجب أن يحتوي على narration و onscreen_text و keywords.
لا تغيّر مضمون السيناريو إلا بالقدر اللازم لإصلاح JSON.

النص:
{raw}
""".strip()

    repaired = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": repair_prompt}],
        temperature=0.2,
        max_tokens=1800,
    )
    return parse_json_response(repaired.choices[0].message.content or "")


def main():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    topic = get_topic()
    print(f"Generating for topic: {topic} with model {MODEL}")

    prompt = build_prompt(topic)
    client = Groq(api_key=api_key)
    completion = request_generation(client, prompt)

    raw = completion.choices[0].message.content or ""
    try:
        data = parse_json_response(raw)
    except (ValueError, json.JSONDecodeError) as parse_error:
        print(f"Initial response was not valid JSON: {parse_error}")
        print("Sending one repair request...")
        data = repair_json(client, raw)

    script = {"topic": topic, "scenes": data["scenes"]}
    content = {
        "title": data["title"],
        "description": data["description"],
        "tags": data["tags"],
    }

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
