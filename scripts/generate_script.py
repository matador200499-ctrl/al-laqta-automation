import os
from groq import Groq

def main():
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    topic = "برج الميزان"
    try:
        if os.path.exists("manual_topic.txt"):
            with open("manual_topic.txt","r",encoding="utf-8") as f:
                t=f.read().strip()
                if t: topic=t
    except: pass

    print(f"Generating for topic: {topic} with model llama3-8b-8192")

    completion = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[{"role":"user","content":f"اكتب سكريبت فيديو قصير 50 ثانية بالعامية المصرية عن {topic}. ابدأ بهوك قوي واذكر 3 صفات وخاتمة بسؤال يخلي الناس تعلق"}],
        temperature=0.8,
        max_tokens=800
    )
    script = completion.choices[0].message.content.strip()
    os.makedirs("output", exist_ok=True)
    open("output/script.txt","w",encoding="utf-8").write(script)
    open("script.txt","w",encoding="utf-8").write(script)
    open("output/story.txt","w",encoding="utf-8").write(script)
    print(f"Generated: {script[:150]}")

if __name__ == "__main__":
    main()
