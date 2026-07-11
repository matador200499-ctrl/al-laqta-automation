"""
generate_script.py
ظٹط³طھط®ط¯ظ… Groq API ظ„طھظˆظ„ظٹط¯ ط¹ظ†ظˆط§ظ† + ظˆطµظپ + طھط§ط¬ط² + ط³ظƒط±ظٹط¨طھ ظ…ظ‚ط³ظ‘ظ… ظ„ظ…ط´ط§ظ‡ط¯.
ط§ظ„ظ†طھظٹط¬ط© ط¨طھطھط­ظپط¸ ظپظٹ script.json ظˆ content.json.
"""
import os
import sys
import json
import re
from openai import OpenAI

CHANNEL_STYLE = """
ط£ظ†طھ ظƒط§طھط¨ ط³ظƒط±ظٹط¨طھط§طھ ظ„ظ‚ظ†ط§ط© ظٹظˆطھظٹظˆط¨ ط§ط³ظ…ظ‡ط§ "ط§ظ„ظ„ظ‚ط·ط© - Al Laqta".
ط£ط³ظ„ظˆط¨ ط§ظ„ظ‚ظ†ط§ط©: ظ…ط­طھظˆظ‰ ظ…ط´ظˆظ‚ ظˆظ…ط­طھط±ظ… ط¨ط¹ظٹط¯ ط¹ظ† ط§ظ„ط¥ط³ظپط§ظپ ظˆط§ظ„ط¹ظ†ط§ظˆظٹظ† ط§ظ„ظ…ط¶ظ„ظ„ط© (Clickbait).
ط§ظ„ظ†ط¨ط±ط©: ط³ظٹظ†ظ…ط§ط¦ظٹط©طŒ طھط­ظ„ظٹظ„ظٹط©طŒ طھظƒط´ظپ طھظپط§طµظٹظ„ ظٹط؛ظپظ„ ط¹ظ†ظ‡ط§ ط§ظ„ط¬ظ…ظ‡ظˆط±.
""".strip()

def build_prompt(topic: str) -> str:
    return f"""{CHANNEL_STYLE}
ط§ظ„ظ…ظˆط¶ظˆط¹: "{topic}"
ط§ظƒطھط¨ ط³ظƒط±ظٹط¨طھ ظپظٹط¯ظٹظˆ ط·ظˆظ„ظ‡ ظٹظƒظپظٹ ظ„ظ†ط·ظ‚ طµظˆطھظٹ ظ…ط¯طھظ‡ ظ…ظ† 3 ط¥ظ„ظ‰ 4 ط¯ظ‚ط§ط¦ظ‚ (ط­ظˆط§ظ„ظٹ 550-700 ظƒظ„ظ…ط© ط¹ط±ط¨ظٹط© ظ…ظˆط²ط¹ط©
ط¹ظ„ظ‰ 9-12 ظ…ط´ظ‡ط¯). ظƒظ„ ظ…ط´ظ‡ط¯ ظ„ط§ط²ظ… ظٹظƒظˆظ†:
- narration: ظپظ‚ط±ط© ط³ط±ط¯ ط¨ط§ظ„ط¹ط±ط¨ظٹط© ط§ظ„ظپطµط­ظ‰ ط§ظ„ظ…ط¨ط³ط·ط© (50-80 ظƒظ„ظ…ط©)
- keywords: ظƒظ„ظ…طھظٹظ† ط£ظˆ 3 ط¨ط§ظ„ط¥ظ†ط¬ظ„ظٹط²ظٹط© طھطµظپ ظ…ط´ظ‡ط¯ ظپظٹط¯ظٹظˆ ط­ظ‚ظٹظ‚ظٹ ظ…ظ†ط§ط³ط¨ (ظˆطµظپ ط¨طµط±ظٹ ط¹ط§ظ… ط²ظٹ "city traffic aerial")
- onscreen_text: ط¬ظ…ظ„ط© ظ‚طµظٹط±ط© ط¬ط¯ظ‹ط§ (3-6 ظƒظ„ظ…ط§طھ) ط¨ط§ظ„ط¹ط±ط¨ظٹ طھطھظƒطھط¨ ط¹ظ„ظ‰ ط§ظ„ط´ط§ط´ط©
ط±ط¬ظ‘ط¹ظ„ظٹ ط§ظ„ظ†ط§طھط¬ ط¨طµظٹط؛ط© JSON ظپظ‚ط· ط¨ط¯ظˆظ† ط£ظٹ ظ†طµ ط¥ط¶ط§ظپظٹ ظ‚ط¨ظ„ظ‡ ط£ظˆ ط¨ط¹ط¯ظ‡طŒ ظˆط¨ط¯ظˆظ† ط¹ظ„ط§ظ…ط§طھ ظ…ط§ط±ظƒط¯ط§ظˆظ†:
{{
  "title": "ط¹ظ†ظˆط§ظ† ط¬ط°ط§ط¨ ظ„ط§ ظٹطھط¬ط§ظˆط² 70 ط­ط±ظپ",
  "description": "ظˆطµظپ ط§ظ„ظپظٹط¯ظٹظˆ ظ„ظٹظˆطھظٹظˆط¨طŒ 3 ط¥ظ„ظ‰ 5 ط£ط³ط·ط±",
  "tags": ["طھط§ط¬1", "طھط§ط¬2", "...ط­طھظ‰ 12 طھط§ط¬"],
  "scenes": [
    {{"narration": "...", "keywords": "...", "onscreen_text": "..."}}
  ]
}}
"""

def main():
    topic = os.environ.get("VIDEO_TOPIC")
    if not topic:
        print("ط®ط·ط£: ظ„ط§ط²ظ… طھط­ط¯ط¯ VIDEO_TOPIC", file=sys.stderr)
        sys.exit(1)
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        print("ط®ط·ط£: GROQ_API_KEY ط؛ظٹط± ظ…ظˆط¬ظˆط¯", file=sys.stderr)
        sys.exit(1)
    client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": build_prompt(topic)}],
        max_tokens=8000,
    )
    raw_text = response.choices[0].message.content.strip()
    cleaned = re.sub(r"^```json\s*|\s*```$", "", raw_text)
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)
    cleaned = re.sub(r"[\x00-\x1f]+", " ", cleaned)
    try:
        data = json.loads(cleaned, strict=False)
    except json.JSONDecodeError as e:
        print(f"ط®ط·ط£: طھط¹ط°ط± طھظپط³ظٹط± ظ…ط®ط±ط¬ط§طھ Groq ظƒظ€ JSON: {e}", file=sys.stderr)
        print(raw_text, file=sys.stderr)
        sys.exit(1)
    if not data.get("scenes"):
        print("ط®ط·ط£: ظ„ط§ طھظˆط¬ط¯ ظ…ط´ط§ظ‡ط¯ ظپظٹ ط§ظ„ظ†ط§طھط¬", file=sys.stderr)
        sys.exit(1)
    with open("script.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    with open("content.json", "w", encoding="utf-8") as f:
        json.dump(
            {"title": data["title"], "description": data["description"], "tags": data["tags"]},
            f, ensure_ascii=False, indent=2,
        )
    print(f"طھظ… طھظˆظ„ظٹط¯ ط³ظƒط±ظٹط¨طھ ظ…ظ† {len(data['scenes'])} ظ…ط´ظ‡ط¯ ط¨ظ†ط¬ط§ط­.")

if __name__ == "__main__":
    main()