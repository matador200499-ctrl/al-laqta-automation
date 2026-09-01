import os
import json
import random
from pathlib import Path
from groq import Groq

# ====== الإعدادات لتجنب 413 ======
# قللنا كل حاجة للنص عشان Groq المجاني مايضربش
MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
MAX_TOKENS = 800 # كان 2000+ وده سبب الـ 413
TEMPERATURE = 0.7

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

TOPICS_FILE = Path("topics.txt")
SELECTED_FILE = Path("scripts/selected_topics.json")
USED_FILE = Path("used_topics.txt")

def pick_topic():
    if SELECTED_FILE.exists():
        try:
            data = json.loads(SELECTED_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                return random.choice(data)
            if isinstance(data, dict) and data.get("topics"):
                return random.choice(data["topics"])
        except:
            pass

    if TOPICS_FILE.exists():
        topics = [t.strip() for t in TOPICS_FILE.read_text(encoding="utf-8").splitlines() if t.strip()]
        if topics:
            # استبعد المستخدم قبل كده
            used = set()
            if USED_FILE.exists():
                used = set([u.strip() for u in USED_FILE.read_text(encoding="utf-8").splitlines()])
            available = [t for t in topics if t not in used]
            return random.choice(available) if available else random.choice(topics)

    return "حكمة اليوم عن الحياة"

def generate_script(topic: str):
    # برومبت قصير جدا عشان الرد يكون صغير وميعديش الـ TPM
    prompt = f"""اكتب سكريبت فيديو قصير 30 ثانية عن: {topic}
    أرجع JSON فقط بهذا الشكل بالظبط، بدون أي كلام إضافي:
    {{"title":"عنوان قصير جذاب","script":["جملة 1 قصيرة","جملة 2 قصيرة","جملة 3 قصيرة","جملة 4 قصيرة","جملة 5 ختامية"],"hashtags":["#حكمة","#اللقطة"]}}
    كل جملة لا تزيد عن 12 كلمة.
    """

    print(f"Generating for topic: {topic} with model {MODEL}")

    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "أنت كاتب سكريبتات محترف. ترد بـ JSON فقط."},
            {"role": "user", "content": prompt}
        ],
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS, # ده أهم سطر يحل الـ 413
        response_format={"type": "json_object"}
    )

    content = completion.choices[0].message.content
    data = json.loads(content)

    # حفظ الموضوع في المستخدم
    with open(USED_FILE, "a", encoding="utf-8") as f:
        f.write(topic + "\n")

    return data

def main():
    topic = os.getenv("VIDEO_TOPIC") or pick_topic()
    data = generate_script(topic)

    # حفظ الناتج
    Path("output").mkdir(exist_ok=True)
    output_path = Path("output/script.json")
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # حفظه كمان في المكان اللي assemble_video بيقرأ منه
    Path("scripts/selected_topics.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Generated successfully:")
    print(json.dumps(data, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
    main()
