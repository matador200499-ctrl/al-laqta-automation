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
import re
from typing import List, Optional

TOPICS_FILE = "topics.txt"
USED_FILE = "used_topics.txt"

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
TOPICS_TO_GENERATE = int(os.environ.get("TOPICS_TO_GENERATE", "15"))

def is_story_topic(value: str) -> bool:
    normalized = value.strip()
    serial_markers = (
        "عمر وسلمى", "عمر و سلمى", "عمر وليلى", "عمر و ليلى",
        "سارة وآدم", "سارة و آدم", "حكاية على الكورنيش",
        "بين قلبين", "موعد في المطر", "آخر فرصة", "صدفة العمر", "بعد الغياب",
    )
    return (
        normalized.startswith("سلسلة")
        or "الحلقة" in normalized
        or any(marker in normalized for marker in serial_markers)
    )



def normalize_topic(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[أإآ]", "ا", value)
    value = re.sub(r"ى", "ي", value)
    value = re.sub(r"[ـ\u064B-\u065F\u0670]", "", value)
    value = re.sub(r"[^\w\s]", " ", value)
    return " ".join(value.split())


def topics_are_similar(a: str, b: str) -> bool:
    from difflib import SequenceMatcher
    na, nb = normalize_topic(a), normalize_topic(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    ratio = SequenceMatcher(None, na, nb).ratio()
    ta, tb = set(na.split()), set(nb.split())
    overlap = len(ta & tb) / max(1, len(ta | tb))
    return ratio >= 0.78 or overlap >= 0.72


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
    "لماذا نرى قوس قزح بعد المطر؟",
    "كيف تعرف الطيور طريق الهجرة عبر آلاف الكيلومترات؟",
    "ما الذي يجعل السماء زرقاء وقت الظهر وحمراء عند الغروب؟",
    "كيف تعمل البطارية القابلة للشحن؟",
    "لماذا يلمع المغناطيس على بعض المعادن ولا يجذب غيرها؟",
    "كيف تتكوّن الغيوم من بخار الماء؟",
    "ما سر الأضواء القطبية التي تظهر قرب القطبين؟",
    "كيف تطير الطائرات رغم وزنها الضخم؟",
    "لماذا تلمع عيون القطط في الظلام؟",
    "كيف يقيس العلماء المسافات إلى النجوم البعيدة؟",
    "لماذا تسخن الهواتف المحمولة أثناء الاستخدام؟",
    "كيف يعمل نظام تحديد المواقع GPS من غير إنترنت؟",
    "لماذا لا نسمع الصوت في الفضاء؟",
    "كيف تستطيع النباتات الاستجابة للضوء؟",
    "كيف يتكوّن البرق والرعد؟",
    "ما الذي يجعل بعض المواد عازلة للكهرباء؟",
    "كيف يعمل الرادار على اكتشاف الأجسام البعيدة؟",
    "كيف تُقاس أعماق المحيطات؟",
    "لماذا تبرد الصحراء بسرعة بعد غروب الشمس؟",
    "كيف تصنع الخفافيش خرائط للمكان باستخدام الصوت؟",
    "كيف تتحول الرمال إلى زجاج؟",
    "ما الفرق بين الكويكب والمذنب والشهاب؟",
    "كيف يعرف العلماء عمر الصخور القديمة؟",
    "لماذا تتكوّن فقاعات الصابون على شكل كرات؟",
    "هل تستطيع النباتات التواصل مع بعضها تحت الأرض؟",
    "كيف تعمل الألياف الضوئية على نقل الإنترنت؟",
    "لماذا يطفو الجليد فوق سطح الماء؟",
    "كيف تتكوّن البراكين تحت سطح البحر؟",
    "كيف تعرف النحلة مكان الأزهار وتعود إلى خليتها؟",
    "لماذا يبدو القمر أكبر قرب الأفق؟",
    "كيف تُحفظ البيانات داخل شرائح الذاكرة؟",
    "ما الذي يجعل بعض الحيوانات قادرة على التجدد؟",
    "كيف تعمل الأقمار الصناعية في التنبؤ بالطقس؟",
    "لماذا لا تسقط الأقمار الصناعية مباشرة إلى الأرض؟",
    "كيف تتكوّن الحفريات داخل الصخور؟",
    "كيف يتواصل رواد الفضاء مع الأرض؟",
    "لماذا تتغير نبرة الصوت عند تسجيله؟",
    "كيف تعمل كاميرات الهاتف في الإضاءة الضعيفة؟",
    "ما سر الرياح التي تهب من البحر نحو اليابسة؟",
    "كيف يتكوّن الماس في أعماق الأرض؟",
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
    used_recent = used[-250:]
    avoid_text = ""
    if used_recent:
        avoid_text = "\nمواضيع سبق استخدامها وممنوع تكررها حتى بصياغة مختلفة:\n- " + "\n- ".join(used_recent)

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
    unique_topics = []
    for topic in new_topics:
        if is_story_topic(topic):
            continue
        if any(topics_are_similar(topic, prior) for prior in used):
            continue
        if any(topics_are_similar(topic, prior) for prior in unique_topics):
            continue
        unique_topics.append(topic)
    new_topics = unique_topics

    if not new_topics:
        print("تحذير: Groq لم يعد مواضيع صالحة بعد فلترة المستخدمة", file=sys.stderr)
        return []

    return new_topics


def ensure_topics_available() -> List[str]:
    """Refresh the queue with informational topics only, without repeating used topics."""
    used = read_used_topics()
    used_set = set(used)
    lines = []
    if os.path.exists(TOPICS_FILE):
        with open(TOPICS_FILE, "r", encoding="utf-8") as f:
            raw_lines = [line.strip() for line in f if line.strip()]
        seen = set()
        for topic in raw_lines:
            if is_story_topic(topic):
                continue
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
            # Never recycle topics. Filter exact and near duplicates against history.
            for topic in FALLBACK_TOPICS:
                if is_story_topic(topic):
                    continue
                if any(topics_are_similar(topic, prior) for prior in used):
                    continue
                if any(topics_are_similar(topic, prior) for prior in new_topics):
                    continue
                new_topics.append(topic)

        if not new_topics:
            raise RuntimeError(
                "لا توجد موضوعات معلوماتية محلية متاحة حتى بعد تدوير القائمة؛ "
                "أضف موضوعات جديدة أو قلل عدد الموضوعات المحمية من التكرار."
            )
        lines.extend(new_topics)


    # Remove any serial-story entries before saving the queue.
    lines = [topic for topic in lines if not is_story_topic(topic)]
    if not lines:
        raise RuntimeError("لا توجد مواضيع معلوماتية متاحة بعد إزالة العناوين المستخدمة.")

    with open(TOPICS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"تم تجهيز {len(lines)} موضوعًا معلوماتيًا في {TOPICS_FILE}.")
    return lines


def main():
    lines = ensure_topics_available()
    knowledge_topics = [topic for topic in lines if not is_story_topic(topic)]
    if not knowledge_topics:
        raise RuntimeError("لا توجد مواضيع معلوماتية متاحة")

    topic = knowledge_topics[0]
    remaining = knowledge_topics[1:]

    with open(TOPICS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(remaining) + ("\n" if remaining else ""))

    with open(USED_FILE, "a", encoding="utf-8") as f:
        f.write(topic + "\n")

    github_env = os.environ.get("GITHUB_ENV")
    if github_env:
        with open(github_env, "a", encoding="utf-8") as f:
            f.write(f"VIDEO_TOPIC={topic}\n")

    print("نوع الفيديو: معلوماتي")
    print(f"الموضوع المختار: {topic}")
    print(f"باقي {len(remaining)} موضوع في القائمة")

    if len(remaining) <= 4:
        print("::notice::قائمة المواضيع أوشكت تخلص، سيتم توليد دفعة جديدة عند الحاجة")


if __name__ == "__main__":
    main()
