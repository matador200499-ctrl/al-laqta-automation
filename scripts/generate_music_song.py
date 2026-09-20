import os,base64,requests,time,subprocess
from pathlib import Path
G=os.environ["GEMINI_API_KEY"]
R=Path("music_work"); R.mkdir(exist_ok=True)
r=requests.post("https://generativelanguage.googleapis.com/v1beta/interactions",headers={"x-goog-api-key":G,"Content-Type":"application/json"},json={"model":"lyria-3.5","input":"Create and sing an original Egyptian Arabic pop song about two fictional lovers in Cairo. Around two minutes. No named artist imitation."},timeout=180)
r.raise_for_status()
j=r.json(); a=j.get("output_audio",{}).get("data")
if not a: raise RuntimeError("No audio returned")
(R/"song.mp3").write_bytes(base64.b64decode(a))
Path("lyrics.txt").write_text(j.get("output_text",""),encoding="utf-8")
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
    x=requests.post("https://generativelanguage.googleapis.com/v1beta/models/veo-3.1-generate-preview:predictLongRunning",headers={"x-goog-api-key":G,"Content-Type":"application/json"},json={"instances":[{"prompt":p+" 8-second realistic cinematic music-video shot, no text, no logos."}],"parameters":{"aspectRatio":"16:9","resolution":"720p","numberOfVideos":1}},timeout=60)
    x.raise_for_status(); op=x.json()["name"]
    while True:
        s=requests.get("https://generativelanguage.googleapis.com/v1beta/"+op,headers={"x-goog-api-key":G},timeout=60); s.raise_for_status(); z=s.json()
        if z.get("done"): break
        time.sleep(10)
    u=z["response"]["generateVideoResponse"]["generatedSamples"][0]["video"]["uri"]
    v=requests.get(u,headers={"x-goog-api-key":G},timeout=180); v.raise_for_status()
    (R/f"scene_{n:02d}.mp4").write_bytes(v.content)
    print(f"scene {n}/12 ready")
