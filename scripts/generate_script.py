import os
import json
from groq import Groq

def generate_script(topic):
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    prompt = f"""
أنت كاتب سكريبت لقناة يوتيوب اسمها "اللقطة" تتكلم عن الأبراج بطريقة مشوقة وغامضة.

الموضوع المطلوب: {topic}

المطلوب:
1. اكتب سكريبت فيديو قصير 45-60 ثانية باللهجة المصرية العامية
2. ابدأ بهوك قوي يشد الانتباه
3. اذكر 3 صفات أو توقعات عن البرج
4. اختم بسؤال يخلي الناس تعلق
5. لا تضع أي عناوين أو أرقام، فقط نص السكريبت جاهز للقراءة مباشرة

السكريبت:
"""

    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.8,
        max_tokens=800,
        top_p=1,
    )

    return completion.choices[0].message.content.strip()

def get_topic():
    # حاول تقرأ من ملفات مختلفة
    if os.path.exists("manual_topic.txt"):
        with open("manual_topic.txt", "r", encoding="utf-8") as f:
            return f.read().strip()

    if os.path.exists("current_topic.txt"):
        with open("current_topic.txt", "r", encoding="utf-8") as f:
            return f.read().strip()

    if os.path.exists("topics.txt"):
        try:
            with open("topics.txt", "r", encoding="utf-8") as f:
                topics = [l.strip() for l in f if l.strip()]
            if topics:
                return topics[0]
        except:
            pass

    return "برج الميزان"

def main():
    os.makedirs("output", exist_ok=True)

    topic = get_topic()
    print(f"Generating for topic: {topic} with model llama-3.3-70b-versatile")

    script = generate_script(topic)

    print(f"Generated script: {script[:100]}...")

    # اكتبه في كل الأماكن المتوقعة عشان اللي بعده يلاقيه
    with open("output/script.txt", "w", encoding="utf-8") as f:
        f.write(script)

    with open("script.txt", "w", encoding="utf-8") as f:
        f.write(script)

    with open("output/story.txt", "w", encoding="utf-8") as f:
        f.write(script)

if __name__ == "__main__":
    main()
