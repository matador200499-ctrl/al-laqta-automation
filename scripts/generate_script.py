import random
import os

def get_topic():
    # التحقق إذا كان هناك موضوع محدد مدخل من GitHub Actions
    manual_topic = os.getenv("MANUAL_TOPIC")
    
    if manual_topic and manual_topic.strip():
        return manual_topic
    
    # إذا لم يوجد، نختار موضوع عشوائي من ملف topics.txt
    try:
        with open("topics.txt", "r", encoding="utf-8") as f:
            topics = [line.strip() for line in f if line.strip()]
        
        if not topics:
            raise ValueError("ملف topics.txt فارغ!")
            
        return random.choice(topics)
    except FileNotFoundError:
        print("خطأ: ملف topics.txt غير موجود")
        exit(1)

# استدعاء الوظيفة
selected_topic = get_topic()
print(f"الموضوع المختار هو: {selected_topic}")

# هنا يكمل باقي كود السكريبت الخاص بك...
