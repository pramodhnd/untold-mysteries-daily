"""Audio: free Kokoro narration with exact line timings, plus original procedural music."""
import numpy as np
import soundfile as sf
from scipy.signal import butter, lfilter

SR = 24000
LINE_GAP = 0.18     # pause after each line
SCENE_GAP = 0.30    # extra pause at scene end
LEAD_IN = 0.25

_kokoro = None


def _tts():
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro
        import os
        base = os.path.join(os.path.dirname(__file__), "..", "models")
        _kokoro = Kokoro(os.path.join(base, "kokoro-v1.0.onnx"), os.path.join(base, "voices-v1.0.bin"))
    return _kokoro


def narrate(story):
    """Synthesize every line; return (audio, timeline).

    timeline = list of scenes: {scene, start, end, lines:[{text, start, end}]}
    """
    k = _tts()
    chunks = [np.zeros(int(LEAD_IN * SR), dtype=np.float32)]
    t = LEAD_IN
    timeline = []
    for sc in story["scenes"]:
        s_start = t
        lines = []
        for text in sc["lines"]:
            audio, sr = k.create(text, voice=story.get("voice", "am_michael"),
                                 speed=story.get("speed", 1.0), lang=story.get("lang", "en-us"))
            assert sr == SR
            audio = _trim(audio.astype(np.float32))
            dur = len(audio) / SR
            lines.append({"text": text, "start": t, "end": t + dur})
            chunks.append(audio)
            chunks.append(np.zeros(int(LINE_GAP * SR), dtype=np.float32))
            t += dur + LINE_GAP
        chunks.append(np.zeros(int(SCENE_GAP * SR), dtype=np.float32))
        t += SCENE_GAP
        timeline.append({**sc, "start": s_start, "end": t, "lines": lines})
    voice = np.concatenate(chunks)
    return voice, timeline


def _trim(a, thresh=0.01):
    idx = np.where(np.abs(a) > thresh)[0]
    if len(idx) == 0:
        return a
    s = max(0, idx[0] - int(0.03 * SR))
    e = min(len(a), idx[-1] + int(0.06 * SR))
    return a[s:e]


def _lowpass(x, cutoff):
    b, a = butter(2, cutoff / (SR / 2), btype="low")
    return lfilter(b, a, x)


def music(duration, cut_times, seed=7):
    """Dark ambient bed: minor drone + wind + soft hits on scene cuts. Fully original."""
    rng = np.random.default_rng(seed)
    n = int(duration * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    # drone: A minor stack, slowly breathing, lightly detuned
    for f, g in [(55.0, 0.5), (110.0, 0.35), (130.81, 0.18), (164.81, 0.22), (220.0, 0.08)]:
        lfo = 0.6 + 0.4 * np.sin(2 * np.pi * (0.05 + f / 5000) * t + rng.uniform(0, 6))
        out += g * lfo * (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 1.003 * t))
    # wind
    noise = rng.standard_normal(n)
    wind = _lowpass(noise, 500) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.11 * t) ** 2)
    out += 0.9 * wind / (np.abs(wind).max() + 1e-9)
    # soft sub hit + whoosh at each cut
    for c in cut_times:
        i = int(c * SR)
        L = int(1.2 * SR)
        if i + L > n:
            L = n - i
        if L <= 0:
            continue
        tt = np.arange(L) / SR
        hit = np.sin(2 * np.pi * 48 * tt) * np.exp(-tt * 4.0)
        wh = _lowpass(rng.standard_normal(L), 1800) * np.exp(-((tt - 0.15) ** 2) / 0.02)
        out[i:i + L] += 1.2 * hit + 0.6 * wh / (np.abs(wh).max() + 1e-9)
    # fade in/out
    fade = np.minimum(1, np.minimum(t / 1.5, (duration - t) / 1.5))
    out *= np.clip(fade, 0, 1)
    out /= np.abs(out).max() + 1e-9
    return out.astype(np.float32)


def mix(voice, bed, bed_gain_db=-19.0):
    n = max(len(voice), len(bed))
    v = np.pad(voice, (0, n - len(voice)))
    m = np.pad(bed, (0, n - len(bed))) * (10 ** (bed_gain_db / 20))
    out = v / (np.abs(v).max() + 1e-9) * 0.89 + m
    out /= max(1.0, np.abs(out).max() / 0.97)
    return out.astype(np.float32)


def save(path, audio):
    sf.write(path, audio, SR)
