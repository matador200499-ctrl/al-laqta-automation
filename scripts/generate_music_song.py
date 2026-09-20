import os,base64,requests
from pathlib import Path
G=os.environ["GEMINI_API_KEY"]
r=requests.post("https://generativelanguage.googleapis.com/v1beta/interactions",headers={"x-goog-api-key":G,"Content-Type":"application/json"},json={"model":"lyria-3.5","input":"Create and sing an original Egyptian Arabic pop song about two fictional lovers in Cairo. Around two minutes. No named artist imitation."},timeout=180)
r.raise_for_status()
a=r.json().get("output_audio",{}).get("data")
if not a: raise RuntimeError("No audio returned")
Path("song.mp3").write_bytes(base64.b64decode(a))
print("SONG READY")
