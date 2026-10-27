#!/usr/bin/env python3
"""
pick_topic.py
يختار أول موضوع في topics.txt (قائمة انتظار) عشان تشتغل الأتمتة بدون تدخل بشري،
وينقله لـ used_topics.txt عشان مايتكررش.

لو القائمة فاضية أو الملف مش موجود: يحاول يستدعي Groq API ويولّد دفعة مواضيع جديدة.
لو فشل الطلب أو رجع نتيجة غير صالحة: يستخدم قائمة fallback محلية بدلاً من الخروج.
"""
import sys
import os
import json
import urllib.request
import urllib.error
import random
from typing import List, Optional

TOPICS_FILE = "topics.txt"
USED_FILE = "used_topics.txt"

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
TOPICS_TO_GENERATE = int(os.environ.get("TOPICS_TO_GENERATE", "15"))

STORY_PLOTS = [
    "رسالة وصلت في وقت غلط",
    "سر الصورة القديمة",
    "القرار اللي غيّر كل حاجة",
    "مكالمة من رقم مجهول",
    "لقاء غير متوقع في محطة القطر",
    "حقيقة ظهرت بعد غياب طويل",
    "وعد قديم رجع في أصعب وقت",
    "صورة كشفت سرًا مخفيًا",
    "اختفاء مفاجئ قبل موعد مهم",
    "مواجهة قلبت كل التوقعات",
    "اعتراف اتأخر سنين",
    "الرسالة اللي ماكانش المفروض تتفتح",
]


def is_story_topic(value: str) -> bool:
    return value.strip().startswith("سلسلة:")


def build_next_story_topics(used_topics: List[str]) -> List[str]:
    """Always queue fresh Omar and Salma episodes without reusing an episode number."""
    last_episode = 0
    pattern = re.compile(r"^سلسلة\s*:\s*عمر\s*و\s*سلمى\s*\|\s*الحلقة\s*(\d+)", re.UNICODE)
    for value in used_topics:
        match = pattern.search(value.strip())
        if match:
            last_episode = max(last_episode, int(match.group(1)))

    existing = set(used_topics)
    topics = []
    for episode in range(last_episode + 1, last_episode + 4):
        plot = STORY_PLOTS[(episode - 1) % len(STORY_PLOTS)]
        topic = f"سلسلة: عمر وسلمى | الحلقة {episode} | {plot}"
        if topic not in existing:
            topics.append(topic)
    return topics



# قائمة بديلة محلية تستخدم لو فشل Groq
FALLBACK_TOPICS = [
    "لماذا لا نشعر بدوران الأرض رغم سرعتها الهائلة؟",
    "ماذا يحدث داخل جسمك عندما تشعر بالخوف فجأة؟",
    "ما سر ظاهرة الديجافو ولماذا نشعر أننا عشنا اللحظة من قبل؟",
    "ماذا سيحدث لو اختفت الجاذبية عن الأرض لمدة دقيقة؟",
    "أغرب الكائنات التي تعيش في أعماق البحار",
    "لماذا لا نجد حياة خارج الأرض رغم اتساع الكون؟",
    "أسرار الحضارة المصرية القديمة التي ما زالت تحير العلماء",
    "اختراعات ظهرت بالصدفة وغيرت حياة البشر",
    "كيف تعمل خوارزميات مواقع التواصل ولماذا تعرف ما يجذب انتباهك؟",
    "أخطر أساليب الاحتيال الإلكتروني وكيف تكتشفها",
    "كيف تعرف أن صورة أو فيديو تم صنعه بالذكاء الاصطناعي؟",
    "ألغاز تاريخية لم تُحل حتى الآن",
    "مخلوقات حقيقية تبدو وكأنها من كوكب آخر",
    "حقائق عن جسم الإنسان ستجعلك تعيد التفكير في نفسك",
    "تقنيات نستخدمها اليوم كانت خيالًا علميًا منذ سنوات",
]

CHANNEL_DESCRIPTION = os.environ.get(
    "CHANNEL_TOPIC_PROMPT",
    "قناة يوتيوب عربية تقدم فيديوهات قصيرة متنوعة ومثيرة للاهتمام عن العلوم، النفس، التاريخ، الحضارات، الفضاء، الذكاء الاصطناعي والتكنولوجيا، الاختراعات، غرائب العالم، الألغاز، الحقائق المدهشة والأمن السيبراني. ممنوع توليد قصص رومانسية أو درامية أو حلقات مسلسل.",
)


def read_used_topics() -> List[str]:
    if not os.path.exists(USED_FILE):
        return []
    with open(USED_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def generate_topics_with_groq() -> List[str]:
    """يحاول يستدعي Groq ويرجع قائمة مواضيع جديدة أو [] لو فشل."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("تحذير: متغير GROQ_API_KEY غير موجود في البيئة — سيتم استخدام قائمة محلية بدلاً من Groq", file=sys.stderr)
        return []

    used = read_used_topics()
    used_recent = used[-30:]
    avoid_text = ""
    if used_recent:
        avoid_text = "\nمواضيع اتغطت قبل كده وممنوع تكررها:\n- " + "\n- ".join(used_recent)

    prompt = (
        f"اقترح {TOPICS_TO_GENERATE} أفكار جديدة لفيديوهات معلوماتية قصيرة عن العلوم والتاريخ والفضاء والتكنولوجيا والغرائب والألغاز.\n"
        f"وصف القناة: {CHANNEL_DESCRIPTION}\n"
        f"{avoid_text}\n\n"
        "اكتب كل موضوع في سطر منفصل بس، من غير ترقيم ولا شرح ولا علامات، "
        "وبدون أي نص إضافي قبل أو بعد القائمة. ممنوع اقتراح قصص رومانسية أو شخصيات أو حلقات مسلسل."
    )

    body = json.dumps(
        {
            "model": GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.9,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        GROQ_API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
            try:
                data = json.loads(raw)
            except Exception:
                print("تحذير: استجابة Groq غير قابلة للتحويل إلى JSON:", raw, file=sys.stderr)
                return []
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        print(f"خطأ من Groq API: {e.code} - {err_body}", file=sys.stderr)
        # لو 403 أو غيرها، لا ننهى التنفيذ؛ نرجع قائمة فارغة عشان نستخدم الفالباك
        return []
    except urllib.error.URLError as e:
        print(f"خطأ في الاتصال بـ Groq API: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"خطأ غير متوقع عند الاتصال بـ Groq: {e}", file=sys.stderr)
        return []

    # محاولة استخراج النص من بنية OpenAI-like
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        print(f"رد غير متوقع من Groq API: {data}", file=sys.stderr)
        return []

    new_topics = [line.strip(" -\t") for line in content.splitlines() if line.strip()]
    used_set = set(used)
    unique_topics = []
    seen = set(used_set)
    for topic in new_topics:
        if topic not in seen and not is_story_topic(topic):
            unique_topics.append(topic)
            seen.add(topic)
    new_topics = unique_topics

    if not new_topics:
        print("تحذير: Groq لم يعد مواضيع صالحة بعد فلترة المستخدمة", file=sys.stderr)
        return []

    return new_topics


def ensure_topics_available() -> List[str]:
    """Refresh the queue without repeating used topics and always keep story episodes queued."""
    used = read_used_topics()
    used_set = set(used)
    lines = []
    if os.path.exists(TOPICS_FILE):
        with open(TOPICS_FILE, "r", encoding="utf-8") as f:
            raw_lines = [line.strip() for line in f if line.strip()]
        seen = set()
        for topic in raw_lines:
            if topic not in used_set and topic not in seen:
                lines.append(topic)
                seen.add(topic)

    if not lines:
        print("قائمة المواضيع فاضية أو استُخدمت بالكامل؛ جاري محاولة توليد أفكار جديدة...")
        new_topics = generate_topics_with_groq()
        new_topics = [topic for topic in new_topics if topic not in used_set and not is_story_topic(topic)]

        if not new_topics:
            print("Groq لم يوفر مواضيع جديدة؛ جاري استخدام القائمة المحلية البديلة.", file=sys.stderr)
            new_topics = []
            seen_fallback = set(used_set)
            for topic in FALLBACK_TOPICS:
                if topic not in seen_fallback:
                    new_topics.append(topic)
                    seen_fallback.add(topic)

        if not new_topics:
            raise RuntimeError(
                "كل المواضيع المحلية البديلة استُخدمت وGroq لم يوفر مواضيع جديدة. "
                "أضف أفكارًا جديدة إلى topics.txt أو تحقق من حصة GROQ_API_KEY."
            )
        lines.extend(new_topics)

    # The informational-topic generator intentionally excludes stories, so add fresh
    # Omar and Salma episodes whenever the queue does not already contain three.
    story_count = sum(1 for topic in lines if is_story_topic(topic))
    if story_count < 3:
        fresh_stories = build_next_story_topics(used + lines)
        needed = 3 - story_count
        existing = set(lines)
        for topic in fresh_stories:
            if topic not in existing:
                lines.append(topic)
                existing.add(topic)
                needed -= 1
            if needed <= 0:
                break

    if not lines:
        raise RuntimeError("لا توجد مواضيع متاحة بعد إزالة العناوين المستخدمة.")

    with open(TOPICS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"تم تجهيز {len(lines)} موضوعًا في {TOPICS_FILE}، منها {sum(1 for x in lines if is_story_topic(x))} حلقات قصة.")
    return lines


def main():
    # Temporary one-shot caption-repair render for the already published Faris and Salma episode.
    # This branch is only used by the temporary push trigger and never consumes the queue.
    if os.environ.get("GITHUB_EVENT_NAME") == "push":
        topic = "سلسلة: فارس وسلمى | الحلقة 1 | يوم عادي انتهى برسالة غريبة"
        github_env = os.environ.get("GITHUB_ENV")
        if github_env:
            with open(github_env, "a", encoding="utf-8") as f:
                f.write("VIDEO_TOPIC=" + topic + chr(10))
        print("وضع إصلاح الكتابة: إعادة إنتاج فارس وسلمى الحلقة الأولى فقط.")
        print(f"الموضوع المختار: {topic}")
        return

    lines = ensure_topics_available()

    used = read_used_topics()
    last_types = [is_story_topic(x) for x in used[-2:]]
    # الجدول المطلوب: موضوعان معلوماتيان ثم حلقة قصة واحدة.
    # إذا كانت آخر حلقتين معلوماتيتين، يأتي الدور التالي للقصة.
    want_story = len(last_types) >= 2 and last_types[-1] is False and last_types[-2] is False

    story_topics = [x for x in lines if is_story_topic(x)]
    knowledge_topics = [x for x in lines if not is_story_topic(x)]

    if want_story and story_topics:
        topic = story_topics[0]
    elif knowledge_topics:
        topic = knowledge_topics[0]
    elif story_topics:
        topic = story_topics[0]
    else:
        raise RuntimeError("لا توجد مواضيع متاحة")

    remaining = lines.copy()
    remaining.remove(topic)

    with open(TOPICS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(remaining) + ("\n" if remaining else ""))

    with open(USED_FILE, "a", encoding="utf-8") as f:
        f.write(topic + "\n")

    # نكتب الموضوع في متغير بيئة GitHub Actions
    github_env = os.environ.get("GITHUB_ENV")
    if github_env:
        with open(github_env, "a", encoding="utf-8") as f:
            f.write(f"VIDEO_TOPIC={topic}\n")

    kind = "قصة" if is_story_topic(topic) else "معلوماتي"
    print(f"نوع الفيديو: {kind}")
    print(f"الموضوع المختار: {topic}")
    print(f"باقي {len(remaining)} موضوع في القائمة")

    if len(remaining) <= 4:
        print("::notice::قائمة المواضيع أوشكت تخلص، هيتم توليد دفعة جديدة تلقائيًا في المرة الجاية اللي القائمة تفضى فيها")

if __name__ == "__main__":
    main()
