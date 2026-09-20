import os,base64,requests,time,subprocess
from pathlib import Path

G=os.environ["GEMINI_API_KEY"]
R=Path("music_work")
R.mkdir(exist_ok=True)

# Use the standard generateContent endpoint for Lyria 3.5.
# It is officially supported for full-length songs and avoids the
# Interactions endpoint permission path that returned HTTP 403.
song_prompt = """Create and sing an original Egyptian Arabic pop song about two fictional lovers in Cairo.
Around two minutes, with a clear intro, verses, catchy chorus, bridge and outro.
Modern Egyptian pop production, emotional male and female vocals, piano, guitar, warm synths and drums.
Write original lyrics only. Do not imitate or reference any named artist."""

lyria_model = os.getenv("LYRIA_MODEL", "lyria-3.5")
lyria_url = f"https://generativelanguage.googleapis.com/v1beta/models/{lyria_model}:generateContent"
payload = {
    "contents":[{"parts":[{"text":song_prompt}]}],
    "generationConfig":{"responseModalities":["AUDIO","TEXT"]}
}

# Retry only transient rate limits. A daily free-tier limit of zero cannot be
# fixed by sleeping, so fail with the actual remediation instead of burning
# the workflow timeout.
for attempt in range(3):
    r = requests.post(
        lyria_url,
        headers={"x-goog-api-key":G,"Content-Type":"application/json"},
        json=payload,
        timeout=300
    )
    if r.ok:
        break
    if r.status_code != 429:
        raise RuntimeError(f"Lyria API HTTP {r.status_code}: {r.text[:2000]}")
    try:
        err = r.json().get("error", {})
        message = err.get("message", r.text[:2000])
        quota_ids = [
            v.get("quotaId", "")
            for d in err.get("details", [])
            if d.get("@type", "").endswith("QuotaFailure")
            for v in d.get("violations", [])
        ]
    except (ValueError, TypeError):
        message, quota_ids = r.text[:2000], []
    if any("PerDay" in q for q in quota_ids):
        raise RuntimeError(
            "Lyria daily quota is exhausted or disabled for this API project. "
            "Enable billing for the Google AI project or replace GEMINI_API_KEY "
            "with a key from a project that has Lyria quota. Details: " + message
        )
    if attempt == 2:
        raise RuntimeError(f"Lyria rate limit persisted after retries: {message}")
    retry_after = r.headers.get("Retry-After")
    try:
        delay = max(5, min(90, int(float(retry_after)))) if retry_after else 20 * (attempt + 1)
    except ValueError:
        delay = 20 * (attempt + 1)
    print(f"Lyria rate-limited; retrying in {delay}s ({attempt + 1}/3)", flush=True)
    time.sleep(delay)

j=r.json()
audio_data=None
lyrics=[]
for candidate in j.get("candidates",[]):
    for part in candidate.get("content",{}).get("parts",[]):
        if part.get("text"):
            lyrics.append(part["text"])
        inline=part.get("inline_data") or part.get("inlineData")
        if inline and inline.get("data"):
            audio_data=inline["data"]

if not audio_data:
    raise RuntimeError("Lyria returned no audio data. Response: "+str(j)[:2000])

(R/"song.mp3").write_bytes(base64.b64decode(audio_data))
Path("lyrics.txt").write_text("\n\n".join(lyrics),encoding="utf-8")

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

for n,p in enumerate(scenes,1):
    x=requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/veo-3.1-generate-preview:predictLongRunning",
        headers={"x-goog-api-key":G,"Content-Type":"application/json"},
        json={"instances":[{"prompt":p+" 8-second realistic cinematic music-video shot, no text, no logos."}],
              "parameters":{"aspectRatio":"16:9","resolution":"720p","numberOfVideos":1}},
        timeout=60
    )
    if not x.ok:
        raise RuntimeError(f"Veo API HTTP {x.status_code}: {x.text[:2000]}")
    op=x.json()["name"]
    while True:
        s=requests.get("https://generativelanguage.googleapis.com/v1beta/"+op,headers={"x-goog-api-key":G},timeout=60)
        if not s.ok:
            raise RuntimeError(f"Veo polling HTTP {s.status_code}: {s.text[:2000]}")
        z=s.json()
        if z.get("done"):
            break
        time.sleep(10)
    u=z["response"]["generateVideoResponse"]["generatedSamples"][0]["video"]["uri"]
    v=requests.get(u,headers={"x-goog-api-key":G},timeout=180)
    if not v.ok:
        raise RuntimeError(f"Veo download HTTP {v.status_code}: {v.text[:1000]}")
    (R/f"scene_{n:02d}.mp4").write_bytes(v.content)
    print(f"scene {n}/12 ready")

files=sorted(R.glob("scene_*.mp4"))
(R/"concat.txt").write_text("".join("file '"+str(x.resolve())+"\n" for x in files),encoding="utf-8")
subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(R/"concat.txt"),"-an","-c:v","libx264","-pix_fmt","yuv420p",str(R/"visuals.mp4")],check=True)
subprocess.run(["ffmpeg","-y","-stream_loop","-1","-i",str(R/"visuals.mp4"),"-i",str(R/"song.mp3"),"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart","final_music_video.mp4"],check=True)
Path("content.json").write_text('{"title":"أغنية مصرية أصلية جديدة","description":"أغنية أصلية وكليب سينمائي مولدان بالذكاء الاصطناعي.","tags":["أغاني","موسيقى","أغاني مصرية","أغاني عربية","AI music","كليب"]}',encoding="utf-8")
print("MUSIC VIDEO READY")
