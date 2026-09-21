"""Create a royalty-free procedural backing track for the narrated song."""
import json
import math
import os
import struct
import subprocess
import wave

SAMPLE_RATE = 44100
OUT_DIR = "music"
WAV_PATH = os.path.join(OUT_DIR, "background.wav")
MP3_PATH = os.path.join(OUT_DIR, "background.mp3")

# D minor / Bb / F / C loop: warm enough for Arabic pop-style spoken lyrics.
CHORDS = ((146.83, 174.61, 220.00), (116.54, 146.83, 174.61),
          (174.61, 220.00, 261.63), (130.81, 164.81, 196.00))


def envelope(t: float, length: float) -> float:
    attack = min(0.04, length / 4)
    release = min(0.12, length / 3)
    if t < attack:
        return t / attack
    if t > length - release:
        return max(0.0, (length - t) / release)
    return 1.0


def render(duration: float):
    os.makedirs(OUT_DIR, exist_ok=True)
    frames = bytearray()
    beat = 60.0 / 96.0
    chord_len = beat * 4
    total = int((duration + 0.5) * SAMPLE_RATE)
    for i in range(total):
        t = i / SAMPLE_RATE
        chord = CHORDS[int(t / chord_len) % len(CHORDS)]
        local = t % chord_len
        pad = sum(math.sin(2 * math.pi * f * t) for f in chord) / 3
        bass = 0.0
        beat_pos = t % beat
        if beat_pos < 0.22:
            bass = math.sin(2 * math.pi * (chord[0] / 2) * t) * envelope(beat_pos, 0.22)
        snare = 0.0
        half = t % (beat * 2)
        if beat < half < beat + 0.13:
            snare = (math.sin(2 * math.pi * 1800 * t) * 0.6 + math.sin(2 * math.pi * 3200 * t) * 0.4) * envelope(half - beat, 0.13)
        hat = 0.0
        eighth = t % (beat / 2)
        if eighth < 0.035:
            hat = math.sin(2 * math.pi * 7000 * t) * envelope(eighth, 0.035)
        # Keep the backing track quiet so Arabic speech remains intelligible.
        sample = max(-1.0, min(1.0, 0.16 * pad + 0.12 * bass + 0.045 * snare + 0.018 * hat))
        value = int(sample * 32767)
        frames.extend(struct.pack("<hh", value, value))
    with wave.open(WAV_PATH, "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(frames)
    subprocess.run(["ffmpeg", "-y", "-i", WAV_PATH, "-codec:a", "libmp3lame", "-b:a", "128k", MP3_PATH], check=True)
    os.remove(WAV_PATH)


def main():
    with open("audio/durations.json", encoding="utf-8") as f:
        duration = sum(json.load(f))
    render(duration)
    print(f"Created {MP3_PATH} ({duration:.1f}s)")


if __name__ == "__main__":
    main()
