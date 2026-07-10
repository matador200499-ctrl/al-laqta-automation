"""
pick_topic.py
يختار أول موضوع في topics.txt (قائمة انتظار) عشان تشتغل الأتمتة بدون تدخل بشري،
وينقله لـ used_topics.txt عشان مايتكررش.

لازم تحدّث topics.txt بشكل دوري (موضوع في كل سطر) عشان القائمة متخلصش.
"""

import sys

TOPICS_FILE = "topics.txt"
USED_FILE = "used_topics.txt"


def main():
    try:
        with open(TOPICS_FILE, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print("خطأ: ملف topics.txt غير موجود", file=sys.stderr)
        sys.exit(1)

    if not lines:
        print("خطأ: قائمة المواضيع فاضية! ضيف مواضيع جديدة في topics.txt", file=sys.stderr)
        sys.exit(1)

    topic = lines[0]
    remaining = lines[1:]

    with open(TOPICS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(remaining) + ("\n" if remaining else ""))

    with open(USED_FILE, "a", encoding="utf-8") as f:
        f.write(topic + "\n")

    # نكتب الموضوع في متغير بيئة GitHub Actions عشان الخطوات الجاية تستخدمه
    github_env = __import__("os").environ.get("GITHUB_ENV")
    if github_env:
        with open(github_env, "a", encoding="utf-8") as f:
            f.write(f"VIDEO_TOPIC={topic}\n")

    print(f"الموضوع المختار: {topic}")
    print(f"باقي {len(remaining)} موضوع في القائمة")

    if len(remaining) <= 4:
        print("::warning::قائمة المواضيع أوشكت تخلص! ضيف مواضيع جديدة في topics.txt قريبًا")


if __name__ == "__main__":
    main()
