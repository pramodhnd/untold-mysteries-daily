"""Long-form documentary renderer (1920x1080, 24 fps).

Usage: python3 pipeline/render_long.py stories/roopkund_long.json photos.json output/
photos.json maps photo keys to {"path": ..., "credit": ...}; missing photos fall back to an illustration.
"""
import json
import math
import os
import subprocess
import sys
import time

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
import audio  # noqa: E402
import fx  # noqa: E402
import scenes_long as SL  # noqa: E402

W, H, LW, LH = SL.W, SL.H, SL.LW, SL.LH
FPS = 24
FADE = 0.5
LINE_GAP, SCENE_GAP, CHAPTER_PRE = 0.32, 0.55, 1.6
SUB_FONT = ImageFont.truetype(SL.MED, 46)
SR = audio.SR


class Cam:
    def __init__(self, z, pan, vy):
        self.z, self.pan, self.vy = z, pan, vy
        self.cw, self.ch = W / z, H / z

    def origin(self, d):
        x = (LW - self.cw) / 2 + self.pan * d
        y = (LH - self.ch) / 2 + self.vy * d
        return (min(max(0.0, x), LW - self.cw), min(max(0.0, y), LH - self.ch))

    def map(self, x, y, d=1.0):
        x0, y0 = self.origin(d)
        return ((x - x0) * self.z, (y - y0) * self.z)

    def k(self, d=1.0):
        return self.z


def camera(i, u):
    e = u * u * (3 - 2 * u)  # ease in-out
    z = 1.0 + 0.07 * e if i % 2 == 0 else 1.07 - 0.07 * e
    direction = 1 if i % 3 != 1 else -1
    pan = (e - 0.5) * 150 * direction
    vy = (e - 0.5) * 30
    return Cam(z, pan, vy)


def shot_camera(plan, lt):
    """New framing on every line: snap zooms toward points of interest, slow drift, handheld shake."""
    z, cx, cy, sx, sy = plan.state(lt)
    return Cam(z, (cx - 0.5) * LW + sx, (cy - 0.5) * LH + sy)


def narrate(story):
    k = audio._tts()
    chunks = [np.zeros(int(0.4 * SR), np.float32)]
    t = 0.4
    timeline = []
    for sc in story["scenes"]:
        s_start = t
        if sc.get("chapter"):
            chunks.append(np.zeros(int(CHAPTER_PRE * SR), np.float32))
            t += CHAPTER_PRE
        lines = []
        for text in sc["lines"]:
            a, sr = audio.speak(k, text, story)
            a = audio._trim(a.astype(np.float32))
            dur = len(a) / SR
            lines.append({"text": text, "start": t, "end": t + dur})
            chunks += [a, np.zeros(int(LINE_GAP * SR), np.float32)]
            t += dur + LINE_GAP
        chunks.append(np.zeros(int(SCENE_GAP * SR), np.float32))
        t += SCENE_GAP
        timeline.append({**sc, "start": s_start, "end": t, "lines": lines})
    return np.concatenate(chunks), timeline


def subtitle_chunks(timeline):
    out = []
    for sc in timeline:
        for ln in sc["lines"]:
            words = ln["text"].split()
            groups, cur = [], []
            for w in words:
                cur.append(w)
                if len(cur) >= 9 or (len(cur) >= 4 and w[-1] in ".,?!:;।"):
                    groups.append(cur)
                    cur = []
            if cur:
                if groups and len(cur) <= 2:
                    groups[-1] += cur
                else:
                    groups.append(cur)
            tot = sum(len(" ".join(g)) for g in groups)
            t = ln["start"]
            for g in groups:
                d = (ln["end"] - ln["start"]) * len(" ".join(g)) / tot
                out.append({"text": " ".join(g), "start": t, "end": t + d + 0.15})
                t += d
    return out


_BAND = None


def draw_sub(img, text):
    global _BAND
    if _BAND is None:  # soft dark band so subtitles stay readable over busy scenes
        a = (np.clip(np.linspace(0, 1, 200), 0, 1) ** 1.5 * 150).astype(np.uint8)
        band = np.zeros((200, W, 4), np.uint8)
        band[..., 3] = a[:, None]
        _BAND = Image.fromarray(band, "RGBA")
    img.alpha_composite(_BAND, (0, H - 200))
    d = ImageDraw.Draw(img)
    d.text((W / 2, H - 78), text, font=SUB_FONT, fill=(255, 255, 255), anchor="mm", stroke_width=5, stroke_fill=(0, 0, 0))


def pill(img, xy, text, fg, bg, size=28, anchor="left"):
    f = ImageFont.truetype(SL.BOLD, size)
    tw = f.getlength(text)
    x, y = xy
    if anchor == "right":
        x -= tw + 48
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    d.rounded_rectangle([x, y, x + tw + 48, y + size + 30], radius=(size + 30) // 2, fill=bg)
    d.text((x + 24, y + (size + 30) / 2), text, font=f, fill=fg, anchor="lm")
    img.alpha_composite(lay)


LANG = "en"


def chapter_card(img, n, title, lt):
    if lt > 2.9:
        return
    a = min(1, lt / 0.4) * (1 if lt < 2.4 else max(0, (2.9 - lt) / 0.5))
    lay = Image.new("RGBA", img.size, (0, 0, 0, int(130 * a)))
    d = ImageDraw.Draw(lay)
    d.text((W / 2, H / 2 - 70), f"{fx.word(LANG, 'chapter')} {n}", font=ImageFont.truetype(SL.BOLD, 36), fill=SL.AMBER + (int(255 * a),), anchor="mm")
    d.text((W / 2, H / 2 + 10), title.upper(), font=ImageFont.truetype(SL.BOLD, 92), fill=(245, 238, 222, int(255 * a)), anchor="mm")
    d.line([(W / 2 - 80, H / 2 + 90), (W / 2 + 80, H / 2 + 90)], fill=SL.AMBER + (int(255 * a),), width=4)
    img.alpha_composite(lay)


def post_fx():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    vig = np.clip(1.06 - 0.3 * d ** 2, 0.55, 1.0)[..., None].astype(np.float32)
    rng = np.random.default_rng(2)
    grains = [rng.normal(0, 3, (H, W, 1)).astype(np.float32) for _ in range(4)]
    return vig, grains


def ts(t):
    m, s = divmod(int(t), 60)
    return f"{m:02d}:{s:02d}"


def fetch_photo(url, out_dir):
    """Download an open-license photo (e.g. Wikimedia Commons) once; return the local path or None."""
    import hashlib
    import urllib.request
    os.makedirs(os.path.join(out_dir, "photos"), exist_ok=True)
    path = os.path.join(out_dir, "photos", hashlib.md5(url.encode()).hexdigest()[:12] + ".jpg")
    if os.path.exists(path):
        return path
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "UntoldMysteriesDaily/1.0 (documentary renderer)"})
        with urllib.request.urlopen(req, timeout=60) as r, open(path, "wb") as fh:
            fh.write(r.read())
        Image.open(path).verify()
        return path
    except Exception as e:  # noqa: BLE001
        print(f"   photo download failed: {e}", flush=True)
        return None


def main(story_path, photos_path, out_dir):
    t0 = time.time()
    story = json.load(open(story_path))
    photos = json.load(open(photos_path)) if photos_path and os.path.exists(photos_path) else {}
    os.makedirs(out_dir, exist_ok=True)
    sid = story["id"]
    global LANG
    LANG = fx.lang_of(story)

    print("1/4 narrating...", flush=True)
    import hashlib
    key = hashlib.md5(json.dumps([[sc["lines"], bool(sc.get("chapter"))] for sc in story["scenes"]] + [story.get("voice"), story.get("speed"), story.get("lang"), LINE_GAP, SCENE_GAP, CHAPTER_PRE]).encode()).hexdigest()
    cache = os.path.join(out_dir, f"{sid}_narration_{key[:10]}.npz")
    if os.path.exists(cache):
        z = np.load(cache, allow_pickle=True)
        voice, timeline = z["voice"], json.loads(str(z["timeline"]))
        print("   (reused cached narration)", flush=True)
    else:
        voice, timeline = narrate(story)
        np.savez(cache, voice=voice, timeline=json.dumps(timeline))
    # re-attach any scene fields edited since caching (labels, photos, flags)
    for sc, src in zip(timeline, story["scenes"]):
        for kk, vv in src.items():
            if kk != "lines":
                sc[kk] = vv
    duration = timeline[-1]["end"] + 1.5
    chapter_starts = [sc["start"] for sc in timeline if sc.get("chapter")]
    bed = audio.music(duration, chapter_starts, seed=11)
    wav = os.path.join(out_dir, f"{sid}.wav")
    audio.save(wav, audio.mix(voice, bed, bed_gain_db=-21))
    print(f"   duration {duration:.1f}s ({duration / 60:.1f} min)", flush=True)

    print("2/4 building scenes...", flush=True)
    built = []
    chap_n = 0
    for i, sc in enumerate(timeline):
        rng = np.random.default_rng(300 + i)
        if sc["scene"] == "photo":
            ph = photos.get(sc.get("photo", ""))
            path = ph["path"] if ph else None
            credit = sc.get("credit") or (ph or {}).get("credit")
            spec = {k: sc[k] for k in ("photo_url", "credit") if sc.get(k)}
            spec.update({k[6:]: sc[k] for k in ("photo_file", "photo_search", "photo_category") if sc.get(k)})
            if spec:
                ph = fx.resolve_photo(spec, out_dir)
                path = ph["path"] if ph else None
                if ph:
                    credit = sc.get("credit") or ph["credit"]
                    fx.record_credit(out_dir, sid, credit, ph.get("page"))
            builder = SL.photo_scene(path, credit) if path and os.path.exists(path) else SL.missing_photo(sc.get("photo"))
            if not (path and os.path.exists(path)):
                print(f"   (photo for scene {i} unavailable, using illustration)", flush=True)
            spec = builder(rng)
        elif sc["scene"] in SL.PARAM_SCENES:
            spec = SL.PARAM_SCENES[sc["scene"]](rng, sc)
        else:
            spec = SL.SCENES[sc["scene"]](rng)
        if sc.get("chapter"):
            chap_n += 1
        ctx = {"lines": [ln["start"] - sc["start"] for ln in sc["lines"]], "dur": sc["end"] - sc["start"], "chapter_n": chap_n}
        flat = None
        for layer, _d in spec["layers"]:
            flat = layer.copy() if flat is None else Image.alpha_composite(flat, layer)
        focal = fx.focal_points(flat, band=(0.15, 0.85))
        lines = ctx["lines"] if not sc.get("chapter") else [2.9] + ctx["lines"][1:]
        plan = fx.ShotPlan(lines, ctx["dur"], focal, seed=i, zmax=1.32, max_shot=4.5)
        built.append((sc, spec, ctx, plan))

    subs = subtitle_chunks(timeline)
    vig, grains = post_fx()
    atmos = fx.Atmosphere(W, H, seed=len(sid), n=40, leak=0.11)
    opener = fx.build_opener(story, out_dir, W, H, vertical=False)
    t_open = min(7.0, max(3.5, timeline[0]["lines"][0]["end"])) if opener else 0.0

    def scene_frame(i, t):
        sc, spec, ctx, plan = built[i]
        dur = sc["end"] - sc["start"] + (FADE if i + 1 < len(built) else 0)
        lt = t - sc["start"]
        u = min(1, max(0, lt / dur))
        cam = shot_camera(plan, lt)
        img = None
        for layer, d in spec["layers"]:
            x0, y0 = cam.origin(d)
            crop = layer.crop((int(x0), int(y0), int(x0 + cam.cw), int(y0 + cam.ch))).resize((W, H), Image.BILINEAR)
            if img is None:
                img = crop.copy()
            else:
                img.alpha_composite(crop)
        spec["overlay"](img, lt, u, cam, ctx)
        card_on = sc.get("chapter") and lt < 2.9
        if sc.get("recon"):
            pill(img, (W - 40, 36), fx.word(LANG, "recon"), SL.AMBER + (255,), (0, 0, 0, 150), 24, anchor="right")
        if sc.get("label") and not card_on:
            pill(img, (40, 36), sc["label"], (240, 232, 214, 255), (0, 0, 0, 150), 26)
        if sc.get("chapter"):
            chapter_card(img, ctx["chapter_n"], sc["chapter"], lt)
        return img

    print("3/4 rendering frames...", flush=True)
    mp4 = os.path.join(out_dir, f"{sid}.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-maxrate", "10M", "-bufsize", "20M",
           "-pix_fmt", "yuv420p", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-shortest",
           "-movflags", "+faststart", mp4]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    nframes = int(duration * FPS)
    si = ci = 0
    for f in range(nframes):
        t = f / FPS
        while si + 1 < len(built) and t >= built[si + 1][0]["start"]:
            si += 1
        if t < t_open:
            img = opener.frame(t, t_open)
        else:
            img = scene_frame(si, t)
            if si > 0 and t - built[si][0]["start"] < FADE:
                kind = "flash" if built[si][0].get("chapter") else fx.KINDS[si % len(fx.KINDS)]
                img = fx.transition(kind, scene_frame(si - 1, t), img, (t - built[si][0]["start"]) / FADE)
            elif opener and t - t_open < FADE:
                img = fx.transition("flash", opener.frame(t, t_open), img, (t - t_open) / FADE)
        while ci + 1 < len(subs) and t >= subs[ci + 1]["start"]:
            ci += 1
        if subs and subs[ci]["start"] <= t < subs[ci]["end"]:
            draw_sub(img, subs[ci]["text"])
        arr = np.asarray(img.convert("RGB"), dtype=np.float32)
        arr *= vig
        atmos.apply(arr, t)
        arr = np.clip(arr + grains[f % 4], 0, 255).astype(np.uint8)
        ff.stdin.write(arr.tobytes())
        if f % 480 == 0:
            print(f"   frame {f}/{nframes}  ({time.time() - t0:.0f}s)", flush=True)
    ff.stdin.close()
    ff.wait()

    print("4/4 captions + chapters...", flush=True)
    with open(os.path.join(out_dir, f"{sid}.srt"), "w") as fh:
        for n, s in enumerate(subs, 1):
            def srt(x):
                h, r = divmod(x, 3600)
                m, s2 = divmod(r, 60)
                return f"{int(h):02d}:{int(m):02d}:{int(s2):02d},{int((s2 % 1) * 1000):03d}"
            fh.write(f"{n}\n{srt(s['start'])} --> {srt(s['end'])}\n{s['text']}\n\n")
    with open(os.path.join(out_dir, f"{sid}_chapters.txt"), "w") as fh:
        fh.write("00:00 Intro\n")
        for sc in timeline:
            if sc.get("chapter"):
                fh.write(f"{ts(sc['start'])} {sc['chapter']}\n")
    json.dump(timeline, open(os.path.join(out_dir, f"{sid}_timeline.json"), "w"), indent=1)
    print(f"done in {time.time() - t0:.0f}s -> {mp4}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None, sys.argv[3] if len(sys.argv) > 3 else "output")
