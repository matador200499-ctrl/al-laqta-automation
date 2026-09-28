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

def parse_json_response(raw: str, is_story: bool) -> dict:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Groq response did not contain a JSON object")
    data = json.loads(text[start:end + 1])
    scenes = data.get("scenes")
    expected_scenes = 6 if is_story else 9
    if not isinstance(scenes, list) or len(scenes) != expected_scenes:
        raise ValueError(f"Generated JSON must contain exactly {expected_scenes} scenes")
    total_words = sum(len(str(scene.get("narration", "")).split()) for scene in scenes)
    if is_story:
        if total_words < 130 or total_words > 190:
            raise ValueError(f"Story narration must contain 130-190 words, got {total_words}")
        min_scene_words, max_scene_words = 18, 35
    else:
        if total_words < 420 or total_words > 480:
            raise ValueError(f"Knowledge narration must contain 420-480 words for about 3 minutes, got {total_words}")
        min_scene_words, max_scene_words = 40, 60
    for index, scene in enumerate(scenes, start=1):
        words = len(str(scene.get("narration", "")).split())
        if words < min_scene_words or words > max_scene_words:
            raise ValueError(f"Scene {index} narration must contain {min_scene_words}-{max_scene_words} words, got {words}")
    required = ("narration", "onscreen_text", "keywords")
    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict) or any(not str(scene.get(key, "")).strip() for key in required):
            raise ValueError(f"Scene {index} is missing required fields")
    data["title"] = str(data.get("title") or "فيديو جديد - اللقطة").strip()
    if not re.search(r"[\u0600-\u06FF]", data["title"]) or re.search(r"[A-Za-z]", data["title"]):
        data["title"] = "حلقة جديدة من اللقطة"
    if is_story:
        data["description"] = "حكاية رومانسية درامية من سلسلة اللقطة، مليانة مشاعر ومفاجآت وتشويق. تابع تطور الأحداث في الحلقات القادمة. الحلقة التالية من السلسلة قريبًا."
        data["tags"] = ["اللقطة", "قصص", "رومانسية", "دراما", "حكايات", "قصص مصرية"]
    else:
        data["description"] = "فيديو معلوماتي من قناة اللقطة يشرح موضوع الحلقة بطريقة بسيطة ومشوقة، مع أهم الحقائق والتفاصيل التي تساعدك تفهم الموضوع في حوالي 3 دقائق."
        data["tags"] = ["اللقطة", "علوم", "معلومات", "حقائق", "تاريخ", "فضاء", "تكنولوجيا"]
    return data
def build_prompt(topic: str) -> str:
    info = parse_episode(topic)
    is_story = topic.strip().startswith("سلسلة:")

    if is_story:
        return f"""
أنت كاتب ومخرج محتوى Shorts لقناة يوتيوب عربية اسمها "اللقطة".
هذه حلقة من مسلسل رومانسي ودرامي مترابط.

معلومات الحلقة:
- السلسلة: {info["series"]}
- رقم الحلقة: {info["episode"]}
- محور الحلقة: {info["plot"]}

القواعد:
1) استخدم عمر وليلى والشخصيات الموجودة في السلسلة فقط، مع استمرارية واضحة.
2) ابدأ بأقوى لحظة خلال أول ثانيتين.
3) عامية مصرية سهلة.
4) بالضبط 6 مشاهد، وإجمالي narration من 130 إلى 190 كلمة.
5) كل مشهد يدفع القصة للأمام وينتهي بتشويق طبيعي.
6) onscreen_text عربي فقط، من 4 إلى 8 كلمات.
7) keywords إنجليزية من 4 إلى 7 كلمات، وتحتوي في كل مشهد على نفس وصف الشخصيات والمكان/الفعل.
8) أعد JSON صحيح فقط بدون Markdown.
9) title عربي ويحتوي اسم السلسلة ورقم الحلقة.
10) description وtags عربية فقط.

المفاتيح:
title, description, tags, scenes
وكل مشهد:
narration, onscreen_text, keywords
""".strip()

    return f"""
أنت كاتب ومخرج محتوى Shorts لقناة يوتيوب عربية اسمها "اللقطة".
هذه الحلقة معلوماتية عن العلوم أو التاريخ أو الفضاء أو التكنولوجيا أو الغرائب والألغاز.
ممنوع تمامًا تحويل الموضوع إلى قصة رومانسية، وممنوع اختراع عمر أو ليلى أو أي شخصيات ثابتة.

موضوع الحلقة:
{topic}

القواعد:
1) ابدأ بمعلومة صادمة أو سؤال قوي خلال أول ثانيتين.
2) اشرح الموضوع بطريقة بسيطة ومشوقة وبالعامية المصرية.
3) بالضبط 9 مشاهد، وإجمالي narration من 420 إلى 480 كلمة ليكون الفيديو حوالي 3 دقائق.
4) كل مشهد حوالي 40 إلى 60 كلمة، ويضيف معلومة جديدة أو يطوّر الشرح بدون تكرار.
5) onscreen_text عربي فقط، من 4 إلى 8 كلمات.
6) keywords إنجليزية من 4 إلى 7 كلمات تصف الشيء/المكان/الفعل الخاص بالمشهد، بدون أسماء شخصيات أو أوصاف رومانسية.
7) أعد JSON صحيح فقط بدون Markdown.
8) title عربي جذاب لا يزيد عن 80 حرفًا.
9) description عربي فقط.
10) tags من 5 إلى 8 وسوم عربية مناسبة.

المفاتيح:
title, description, tags, scenes
وكل مشهد:
narration, onscreen_text, keywords
""".strip()

def request_generation(client: Groq, prompt: str):
    return client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=5000,
        response_format={"type": "json_object"},
    )


def repair_json(client: Groq, raw: str, is_story: bool) -> dict:
    target = (
        "يجب أن يحتوي scenes على 6 مشاهد بالضبط.\n"
        "إجمالي narration من 130 إلى 190 كلمة، وكل مشهد من 18 إلى 35 كلمة."
        if is_story
        else
        "يجب أن يحتوي scenes على 9 مشاهد بالضبط.\n"
        "إجمالي narration من 420 إلى 480 كلمة ليكون الفيديو حوالي 3 دقائق.\n"
        "كل مشهد من 40 إلى 60 كلمة، ويجب أن يضيف معلومة أو يطوّر الشرح بدون تكرار."
    )
    repair_prompt = (
        "أصلح النص التالي وأعده كـ JSON صحيح نحويًا فقط.\n"
        "مهم جدًا: لا تضف أي شرح أو Markdown. لا تغيّر الفكرة الأساسية إلا عند الحاجة لاستكمال الشروط.\n"
        "يجب أن يحتوي الناتج على: title, description, tags, scenes.\n"
        + target + "\n"
        + "كل مشهد يجب أن يكون كائنًا مستقلًا ويحتوي بالضبط على: narration, onscreen_text, keywords.\n"
        + "keywords يجب أن تكون نصًا إنجليزيًا، وليس قائمة.\n"
        + "لا تترك أي حقل فارغًا.\n"
        + "النص المراد إصلاحه:\n"
        + raw
    )
    repaired = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": repair_prompt}],
        temperature=0.0,
        max_tokens=5000,
        response_format={"type": "json_object"},
    )
    return parse_json_response(repaired.choices[0].message.content or "", is_story)
def generate_with_retry(client: Groq, prompt: str, is_story: bool) -> dict:
    last_error = None
    raw = ""
    for attempt in range(2):
        try:
            completion = request_generation(client, prompt)
            raw = completion.choices[0].message.content or ""
            return parse_json_response(raw, is_story)
        except Exception as error:
            last_error = error
            print(f"Generation attempt {attempt + 1} returned invalid JSON: {error}")
    for attempt in range(2):
        try:
            print(f"Sending JSON repair request ({attempt + 1}/2)...")
            return repair_json(client, raw, is_story)
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
    is_story = topic.strip().startswith("سلسلة:")
    data = generate_with_retry(client, build_prompt(topic), is_story)

    content_type = "story" if topic.strip().startswith("سلسلة:") else "knowledge"
    script = {"topic": topic, "content_type": content_type, "scenes": data["scenes"]}
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
