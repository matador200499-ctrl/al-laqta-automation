import json
import os
import re

from groq import Groq


MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
DEFAULT_TOPIC = "برج الميزان"


def get_topic() -> str:
    if os.path.exists("manual_topic.txt"):
        try:
            topic = open("manual_topic.txt", "r", encoding="utf-8").read().strip()
            if topic:
                return topic
        except OSError:
            pass
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


def main():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not configured")

    topic = get_topic()
    print(f"Generating for topic: {topic} with model {MODEL}")

    prompt = f"""
اكتب سيناريو فيديو عربي مدته نحو 50 ثانية بالعامية المصرية عن: {topic}.
ابدأ بهوك قوي، اذكر 3 نقاط أو صفات مفيدة، واختم بسؤال يشجع المشاهد على التعليق.

أعد JSON صحيح فقط بدون Markdown بهذا الشكل:
{{
  "title": "عنوان عربي جذاب لا يزيد عن 90 حرفًا",
  "description": "وصف عربي قصير للفيديو",
  "tags": ["وسم1", "وسم2", "وسم3"],
  "scenes": [
    {{
      "narration": "نص التعليق الصوتي للمشهد بالعامية المصرية",
      "onscreen_text": "عبارة عربية قصيرة تظهر على الشاشة",
      "keywords": "2 to 5 English words suitable for a Pexels stock-video search"
    }}
  ]
}}

قسّم السيناريو إلى 5 أو 6 مشاهد. اجعل مجموع التعليق الصوتي مناسبًا لنحو 50 ثانية.
""".strip()

    client = Groq(api_key=api_key)
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=1800,
        response_format={"type": "json_object"},
    )

    data = parse_json_response(completion.choices[0].message.content)
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
