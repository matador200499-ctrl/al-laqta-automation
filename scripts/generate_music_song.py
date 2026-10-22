import os,json,requests,time,subprocess
from pathlib import Path

ACE_STEP_URL=os.environ.get("ACE_STEP_API_URL", "").rstrip("/")
ACE_STEP_KEY=os.environ.get("ACE_STEP_API_KEY", "")
R=Path("music_work")
R.mkdir(exist_ok=True)

song_prompt = """Original Egyptian Arabic pop song about two fictional lovers in Cairo.
Around two minutes, with a clear intro, verses, catchy chorus, bridge and outro.
Modern Egyptian pop production, emotional male and female vocals, piano, guitar, warm synths and drums.
Write original lyrics only. Do not imitate or reference any named artist."""

if not ACE_STEP_URL:
    raise RuntimeError(
        "ACE_STEP_API_URL is not configured. Run ACE-Step 1.5 on a GPU machine "
        "and add its URL as a GitHub Actions secret. See README.md."
    )

headers={"Content-Type":"application/json"}
if ACE_STEP_KEY:
    headers["Authorization"]="Bearer "+ACE_STEP_KEY

payload={
    "sample_query": song_prompt,
    "thinking": True,
    "vocal_language": "ar",
    "audio_duration": 120,
    "audio_format": "mp3",
    "model": "acestep-v15-turbo"
}
r=requests.post(f"{ACE_STEP_URL}/release_task",headers=headers,json=payload,timeout=60)
if not r.ok:
    raise RuntimeError(f"ACE-Step submit HTTP {r.status_code}: {r.text[:2000]}")
submitted=r.json()
task_id=(submitted.get("data") or {}).get("task_id")
if not task_id:
    raise RuntimeError("ACE-Step returned no task_id: "+str(submitted)[:2000])

result=None
for _ in range(180):
    q=requests.post(f"{ACE_STEP_URL}/query_result",headers=headers,json={"task_id_list":[task_id]},timeout=60)
    if not q.ok:
        raise RuntimeError(f"ACE-Step query HTTP {q.status_code}: {q.text[:2000]}")
    rows=(q.json().get("data") or [])
    row=rows[0] if rows else {}
    status=row.get("status")
    if status == 1:
        raw=row.get("result", "[]")
        result=json.loads(raw) if isinstance(raw,str) else raw
        break
    if status == 2:
        raise RuntimeError("ACE-Step generation failed: "+str(row)[:2000])
    time.sleep(10)
if not result:
    raise RuntimeError("ACE-Step generation timed out after 30 minutes")

audio_path=result[0].get("file") if isinstance(result,list) else result.get("file")
if not audio_path:
    raise RuntimeError("ACE-Step returned no audio file: "+str(result)[:2000])
audio=requests.get(f"{ACE_STEP_URL}{audio_path}",headers=headers,timeout=180)
if not audio.ok:
    raise RuntimeError(f"ACE-Step audio download HTTP {audio.status_code}: {audio.text[:1000]}")
(R/"song.mp3").write_bytes(audio.content)
lyrics=(result[0].get("lyrics", "") if isinstance(result,list) else result.get("lyrics", ""))
Path("lyrics.txt").write_text(lyrics,encoding="utf-8")
print("ACE-Step song ready", flush=True)

PEXELS_KEY=os.environ.get("PEXELS_API_KEY", "")
if not PEXELS_KEY:
    raise RuntimeError("PEXELS_API_KEY is not configured")
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
subprocess.run(["ffmpeg","-y","-stream_loop","-1","-i",str(R/"visuals.mp4"),"-i",str(R/"song.mp3"),"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart","final_music_video.mp4"],check=True)
Path("content.json").write_text('{"title":"أغنية مصرية أصلية جديدة","description":"أغنية أصلية وكليب سينمائي مولدان بالذكاء الاصطناعي.","tags":["أغاني","موسيقى","أغاني مصرية","أغاني عربية","AI music","كليب"]}',encoding="utf-8")
print("MUSIC VIDEO READY")
