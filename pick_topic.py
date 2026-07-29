"""
pick_topic.py
يختار أول موضوع في topics.txt (قائمة انتظار) عشان تشتغل الأتمتة بدون تدخل بشري،
وينقله لـ used_topics.txt عشان مايتكررش.

لو القائمة فاضية أو الملف مش موجود: يستدعي Grok API ويولّد دفعة مواضيع جديدة
تلقائيًا، يحفظها في topics.txt، وبعدين يكمل الاختيار عادي بدون تدخل بشري.
"""
import sys
import os
import json
import urllib.request
import urllib.error

TOPICS_FILE = "topics.txt"
USED_FILE = "used_topics.txt"

GROK_API_URL = "https://api.x.ai/v1/chat/completions"
GROK_MODEL = os.environ.get("GROK_MODEL", "grok-4-latest")
TOPICS_TO_GENERATE = 15

# عدّل السطر ده يوصف مجال القناة بتاعتك عشان المواضيع المولّدة تبقى مناسبة
CHANNEL_DESCRIPTION = os.environ.get(
    "CHANNEL_TOPIC_PROMPT",
    "قناة يوتيوب تنشر فيديوهات قصيرة (شورتس) بالعربي في مجال عام ومثير للاهتمام",
)


def read_used_topics():
    """يقرأ المواضيع المستخدمة قبل كده عشان مايكررهاش."""
    if not os.path.exists(USED_FILE):
        return []
    with open(USED_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def generate_topics_with_grok():
    """يطلب من Grok قائمة مواضيع جديدة ويرجعها كـ list."""
    api_key = os.environ.get("GROK_API_KEY")
    if not api_key:
        print("خطأ: متغير GROK_API_KEY غير موجود في البيئة", file=sys.stderr)
        sys.exit(1)

    used = read_used_topics()
    # ناخد آخر 30 موضوع مستخدم بس عشان الطلب ميبقاش طويل أوي
    used_recent = used[-30:]
    avoid_text = ""
    if used_recent:
        avoid_text = (
            "\nمواضيع اتغطت قبل كده وممنوع تكررها:\n- " + "\n- ".join(used_recent)
        )

    prompt = (
        f"اقترح {TOPICS_TO_GENERATE} موضوع جديد ومختلف لفيديو شورتس قصير.\n"
        f"وصف القناة: {CHANNEL_DESCRIPTION}\n"
        f"{avoid_text}\n\n"
        "اكتب كل موضوع في سطر منفصل بس، من غير ترقيم ولا شرح ولا علامات، "
        "وبدون أي نص إضافي قبل أو بعد القائمة."
    )

    body = json.dumps(
        {
            "model": GROK_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.9,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        GROK_API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        print(f"خطأ من Grok API: {e.code} - {err_body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"خطأ في الاتصال بـ Grok API: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        print(f"رد غير متوقع من Grok API: {data}", file=sys.stderr)
        sys.exit(1)

    new_topics = [line.strip(" -\t") for line in content.splitlines() if line.strip()]
    # فلترة أي تكرار مع المواضيع المستخدمة قبل كده
    used_set = set(used)
    new_topics = [t for t in new_topics if t not in used_set]

    if not new_topics:
        print("خطأ: Grok مرجعش أي مواضيع صالحة", file=sys.stderr)
        sys.exit(1)

    return new_topics


def ensure_topics_available():
    """يتأكد إن topics.txt فيه مواضيع، ولو لأ يولّد جديد تلقائي."""
    lines = []
    if os.path.exists(TOPICS_FILE):
        with open(TOPICS_FILE, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

    if lines:
        return lines

    print("قائمة المواضيع فاضية، جاري توليد مواضيع جديدة تلقائيًا عبر Grok...")
    new_topics = generate_topics_with_grok()

    with open(TOPICS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(new_topics) + "\n")

    print(f"تم توليد {len(new_topics)} موضوع جديد وحفظهم في {TOPICS_FILE}")
    return new_topics


def main():
    lines = ensure_topics_available()

    topic = lines[0]
    remaining = lines[1:]

    with open(TOPICS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(remaining) + ("\n" if remaining else ""))

    with open(USED_FILE, "a", encoding="utf-8") as f:
        f.write(topic + "\n")

    # نكتب الموضوع في متغير بيئة GitHub Actions عشان الخطوات الجاية تستخدمه
    github_env = os.environ.get("GITHUB_ENV")
    if github_env:
        with open(github_env, "a", encoding="utf-8") as f:
            f.write(f"VIDEO_TOPIC={topic}\n")

    print(f"الموضوع المختار: {topic}")
    print(f"باقي {len(remaining)} موضوع في القائمة")

    if len(remaining) <= 4:
        print(
            "::notice::قائمة المواضيع أوشكت تخلص، هيتم توليد دفعة جديدة تلقائيًا "
            "في المرة الجاية اللي القائمة تفضى فيها"
        )


if __name__ == "__main__":
    main()
