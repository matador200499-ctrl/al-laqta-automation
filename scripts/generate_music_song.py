import os, json, requests, time, subprocess, random
from pathlib import Path
from urllib.parse import urlparse

FAL_KEY = os.environ.get("FAL_KEY", "").strip()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
R = Path("music_work")
R.mkdir(exist_ok=True)

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
FAL_ENDPOINT = "https://queue.fal.run/fal-ai/ace-step"

SONG_THEMES = [
    "حكاية حب بدأت صدفة في شوارع القاهرة",
    "الاشتياق لشخص بعيد رغم مرور الأيام",
    "بداية جديدة بعد تجربة حب انتهت",
    "ليلة مطر واعتراف متأخر بالمشاعر",
    "حلم بسيط يجمع حبيبين وسط زحمة الحياة",
    "رسالة قديمة أعادت ذكريات جميلة",
    "فرحة الرجوع بعد غياب طويل",
    "حب هادئ يظهر في التفاصيل اليومية",
]
SONG_STYLES = [
    "modern Egyptian Arabic pop, romantic duet, male and female vocals, warm synths, piano, acoustic guitar, steady pop drums",
    "upbeat Egyptian Arabic pop, playful vocal delivery, lively percussion, oud accents, modern bass and claps",
    "emotional Egyptian Arabic pop ballad, expressive lead vocal, piano, cinematic strings, gentle percussion",
]

if not FAL_KEY:
    raise RuntimeError("FAL_KEY is missing. Create an API key at fal.ai and save it in GitHub Actions Secrets.")
if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY is missing. The workflow uses Groq to write original Arabic lyrics.")
if not os.environ.get("PEXELS_API_KEY", "").strip():
    raise RuntimeError("PEXELS_API_KEY is missing. Add it to GitHub Actions Secrets.")

song_theme = os.environ.get("SONG_THEME", "").strip() or random.choice(SONG_THEMES)
song_style = random.choice(SONG_STYLES)

# First write fresh, original Egyptian-colloquial Arabic lyrics; then send those lyrics to fal/ACE-Step.
lyrics_prompt = f"""اكتب كلمات أغنية مصرية أصلية باللهجة المصرية عن الموضوع التالي: {song_theme}
الأسلوب الموسيقي المقترح: {song_style}
الشروط:
- كلمات أصلية بالكامل، من غير اقتباس من أغنية معروفة أو تقليد فنان بعينه.
- إحساس مصري طبيعي، قافية سهلة، لازمة جذابة قابلة للترديد.
- طول مناسب لأغنية مدتها نحو دقيقتين.
- استخدم هذه الأقسام داخل الكلمات: [Verse 1] ثم [Chorus] ثم [Verse 2] ثم [Bridge] ثم [Chorus].
- اكتب باللهجة المصرية، ولا تضع وصفًا للموسيقى داخل الكلمات.
- أعد JSON صالحًا فقط بالمفتاحين title و lyrics، من غير Markdown أو شرح."""

groq_response = requests.post(
    GROQ_API_URL,
    headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
    json={
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "أنت كاتب أغانٍ محترف يكتب كلمات أصلية باللهجة المصرية. أعد JSON صالحًا فقط."},
            {"role": "user", "content": lyrics_prompt},
        ],
        "temperature": 0.9,
    },
    timeout=90,
)
if not groq_response.ok:
    raise RuntimeError(f"Groq lyrics request failed HTTP {groq_response.status_code}: {groq_response.text[:1200]}")
try:
    lyrics_result = groq_response.json()["choices"][0]["message"]["content"].strip()
except (ValueError, KeyError, IndexError, TypeError) as exc:
    raise RuntimeError(f"Unexpected Groq lyrics response: {groq_response.text[:1200]}") from exc

# Tolerate a model adding a JSON code fence despite the instruction.
if lyrics_result.startswith(chr(96) * 3):
    lyrics_result = lyrics_result.split("\n", 1)[1]
    if lyrics_result.endswith(chr(96) * 3):
        lyrics_result = lyrics_result[:-3].strip()
try:
    song_data = json.loads(lyrics_result)
except json.JSONDecodeError:
    start, end = lyrics_result.find("{"), lyrics_result.rfind("}")
    if start < 0 or end <= start:
        raise RuntimeError("Groq did not return a valid JSON object for song lyrics.")
    song_data = json.loads(lyrics_result[start:end + 1])

song_title = str(song_data.get("title", "")).strip()
lyrics = str(song_data.get("lyrics", "")).strip()
if not song_title or len(lyrics) < 100:
    raise RuntimeError("Groq returned an empty title or lyrics that are too short.")
song_title = song_title[:90]
Path("lyrics.txt").write_text(lyrics, encoding="utf-8")
print(f"Original lyrics ready: {song_title}", flush=True)

fal_headers = {"Authorization": f"Key {FAL_KEY}", "Content-Type": "application/json"}
fal_payload = {
    "tags": song_style,
    "lyrics": lyrics,
    "duration": 120,
    "number_of_steps": 27,
}
submitted_response = requests.post(FAL_ENDPOINT, headers=fal_headers, json=fal_payload, timeout=90)
if not submitted_response.ok:
    raise RuntimeError(f"fal ACE-Step submit failed HTTP {submitted_response.status_code}: {submitted_response.text[:1600]}")
submitted = submitted_response.json()
request_id = submitted.get("request_id")
status_url = submitted.get("status_url")
response_url = submitted.get("response_url")
if not request_id or not status_url or not response_url:
    raise RuntimeError("fal returned no request_id/status_url/response_url: " + str(submitted)[:1600])
print(f"fal song task submitted: {request_id}", flush=True)

result_status = None
for attempt in range(180):
    status_response = requests.get(status_url, headers={"Authorization": f"Key {FAL_KEY}"}, timeout=60)
    if not status_response.ok:
        raise RuntimeError(f"fal status check failed HTTP {status_response.status_code}: {status_response.text[:1000]}")
    status_data = status_response.json()
    result_status = str(status_data.get("status", "")).upper()
    if result_status == "COMPLETED":
        break
    if result_status in {"FAILED", "CANCELLED"}:
        raise RuntimeError("fal music generation failed: " + str(status_data)[:1800])
    if attempt % 6 == 0:
        print(f"Waiting for fal music generation ({result_status or 'pending'})...", flush=True)
    time.sleep(10)
else:
    raise RuntimeError("fal music generation timed out after 30 minutes.")

result_response = requests.get(response_url, headers={"Authorization": f"Key {FAL_KEY}"}, timeout=90)
if not result_response.ok:
    raise RuntimeError(f"fal result fetch failed HTTP {result_response.status_code}: {result_response.text[:1200]}")
result = result_response.json()
audio_info = result.get("audio") or {}
audio_url = audio_info.get("url")
if not audio_url:
    raise RuntimeError("fal completed without an audio URL: " + str(result)[:1600])

audio_response = requests.get(audio_url, timeout=180)
if not audio_response.ok:
    raise RuntimeError(f"Audio download failed HTTP {audio_response.status_code}: {audio_response.text[:800]}")
content_type = str(audio_info.get("content_type", audio_response.headers.get("Content-Type", ""))).lower()
url_path = urlparse(audio_url).path.lower()
audio_suffix = ".mp3" if ("mpeg" in content_type or url_path.endswith(".mp3")) else ".wav"
song_audio_path = R / f"song{audio_suffix}"
song_audio_path.write_bytes(audio_response.content)
# Save the lyrics returned by the model when available, otherwise keep the source lyrics.
Path("lyrics.txt").write_text(str(result.get("lyrics") or lyrics), encoding="utf-8")
Path("song_info.json").write_text(
    json.dumps(
        {"title": song_title, "theme": song_theme, "style": song_style, "audio_url": audio_url,
         "request_id": request_id, "duration_requested_seconds": 120},
        ensure_ascii=False, indent=2,
    ),
    encoding="utf-8",
)
print(f"fal song audio ready: {song_audio_path}", flush=True)

PEXELS_KEY = os.environ.get("PEXELS_API_KEY", "").strip()
PEXELS_SEARCH="https://api.pexels.com/videos/search"

scenes=[
"Cairo rooftop at night, fictional young Egyptian man Omar with short dark hair and light beard, black jacket, looking over city lights.",
"Fictional young Egyptian woman Laila with long dark hair and beige jacket arrives at the rooftop and sees Omar.",
"Omar and Laila talk quietly over coffee on a Cairo rooftop, warm lights, natural gestures.",
"Omar and Laila walk together through a quiet Cairo street at night, cinematic tracking shot.",
"Close-up of Laila holding an old photo while Omar looks at it with emotion.",
"Omar and Laila laugh together beside a softly lit bridge in Cairo.",
"Light rain begins and Omar and Laila shelter under an awning, emotional eye contact.",
"They walk through a colorful Cairo street after rain, reflections on wet pavement.",
"Omar and Laila return to the rooftop, Cairo skyline glowing behind them.",
"They exchange a small handwritten note and smile, cinematic close-up.",
"Dawn begins over Cairo as Omar and Laila stand side by side.",
    "Wide final shot of Omar and Laila walking together into the Cairo sunrise."
]

def best_video_url(video):
    files=[f for f in video.get("video_files",[]) if f.get("link") and f.get("width",0)>=1280]
    if not files:
        files=[f for f in video.get("video_files",[]) if f.get("link")]
    return sorted(files,key=lambda f:f.get("width",0))[0]["link"] if files else None

def download_scene(prompt, n):
    terms=prompt.replace(",", " ")
    q=requests.get(PEXELS_SEARCH,headers={"Authorization":PEXELS_KEY},params={
        "query":terms,"orientation":"landscape","size":"medium","per_page":5
    },timeout=30)
    q.raise_for_status()
    videos=q.json().get("videos",[])
    url=best_video_url(videos[0]) if videos else None
    if not url:
        fallback=requests.get(PEXELS_SEARCH,headers={"Authorization":PEXELS_KEY},params={
            "query":"Cairo night city cinematic","orientation":"landscape","size":"medium","per_page":5
        },timeout=30)
        fallback.raise_for_status()
        videos=fallback.json().get("videos",[])
        url=best_video_url(videos[0]) if videos else None
    if not url:
        raise RuntimeError(f"No Pexels video found for scene {n}: {prompt}")
    video=requests.get(url,stream=True,timeout=120)
    video.raise_for_status()
    path=R/f"scene_{n:02d}.mp4"
    with path.open("wb") as out:
        for chunk in video.iter_content(chunk_size=1024*1024):
            if chunk:
                out.write(chunk)
    return path

for n,p in enumerate(scenes,1):
    download_scene(p,n)
    print(f"Pexels scene {n}/{len(scenes)} ready", flush=True)

files=sorted(R.glob("scene_*.mp4"))
(R/"concat.txt").write_text("".join(f"file '{x.resolve()}'\n" for x in files),encoding="utf-8")
subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(R/"concat.txt"),"-an","-c:v","libx264","-pix_fmt","yuv420p",str(R/"visuals.mp4")],check=True)
subprocess.run(["ffmpeg","-y","-stream_loop","-1","-i",str(R/"visuals.mp4"),"-i",str(song_audio_path),"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart","final_music_video.mp4"],check=True)
Path("content.json").write_text(
    json.dumps(
        {
            "title": song_title,
            "description": f"أغنية مصرية أصلية بعنوان: {song_title}. كلمات جديدة وموسيقى مولدة بالذكاء الاصطناعي.\nالموضوع: {song_theme}",
            "tags": ["أغاني", "أغاني مصرية", "أغاني عربية", "موسيقى", "AI music", "كليب", "أغاني جديدة"],
        },
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)
print("MUSIC VIDEO READY")
