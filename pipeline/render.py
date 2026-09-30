"""Video maker: story JSON -> finished 1080x1920 Short (MP4), cover image and SRT captions.

Usage: python3 pipeline/render.py stories/flannan.json output/
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
import scenes as SC  # noqa: E402
from scenes import SCENES, W, H, FONT_BOLD, AMBER  # noqa: E402

FPS = 30
S = 1.12          # background oversize for camera moves
FADE = 0.4        # transition between scenes
CAP_FONT = ImageFont.truetype(FONT_BOLD, 86)
HOOK_FONT = ImageFont.truetype(FONT_BOLD, 118)
LABEL_FONT = ImageFont.truetype(FONT_BOLD, 38)
CAP_Y = 1290


class Cam:
    def __init__(self, x0, y0, cw):
        self.x0, self.y0, self.cw = x0, y0, cw
        self.ch = cw * H / W
        self.k = S * W / cw

    def map(self, x, y):
        return ((x * S - self.x0) * W / self.cw, (y * S - self.y0) * W / self.cw)


def camera(i, u):
    bw, bh = W * S, H * S
    z = 1.015 + 0.075 * u if i % 2 == 0 else 1.09 - 0.075 * u
    cw = bw / z
    ch = cw * H / W
    pan = (u - 0.5) * (bw - cw) * 0.5 * (1 if i % 3 else -1)
    x0 = (bw - cw) / 2 + pan
    y0 = (bh - ch) / 2
    return Cam(x0, y0, cw)


def shot_camera(plan, lt):
    """Camera for this moment of a scene: a new framing on every line, snap moves, a little handheld shake."""
    bw, bh = W * S, H * S
    z, cx, cy, sx, sy = plan.state(lt)
    cw = bw / (1.02 * z)
    ch = cw * H / W
    x0 = min(max(0.0, cx * bw - cw / 2 + sx), bw - cw)
    y0 = min(max(0.0, cy * bh - ch / 2 + sy), bh - ch)
    return Cam(x0, y0, cw)


def word_times(line):
    words = line["text"].split()
    wts = [len(w) + 2 for w in words]
    tot = sum(wts)
    t = line["start"]
    out = []
    for w, k in zip(words, wts):
        d = (line["end"] - line["start"]) * k / tot
        out.append((w, t, t + d))
        t += d
    return out


def caption_chunks(timeline):
    chunks = []
    for sc in timeline:
        for ln in sc["lines"]:
            cur = []
            for w in word_times(ln):
                cur.append(w)
                chars = sum(len(x[0]) for x in cur) + len(cur) - 1
                if len(cur) >= 3 or chars >= 15 or w[0][-1] in ".?!,:।":
                    chunks.append(cur)
                    cur = []
            if cur:
                chunks.append(cur)
    # each chunk stays until the next starts (or its own end + 0.3s)
    out = []
    for i, c in enumerate(chunks):
        start = c[0][1]
        end = chunks[i + 1][0][1] if i + 1 < len(chunks) else c[-1][2] + 0.4
        end = min(end, c[-1][2] + 0.5)
        out.append({"words": c, "start": start, "end": end})
    return out


def draw_caption(img, chunk, t):
    d = ImageDraw.Draw(img)
    words = [w[0].upper() for w in chunk["words"]]
    space = CAP_FONT.getlength(" ")
    widths = [CAP_FONT.getlength(w) for w in words]
    total = sum(widths) + space * (len(words) - 1)
    lines = [list(range(len(words)))]
    if total > W - 160:  # wrap into two lines
        acc, split = 0, len(words)
        for i, wd in enumerate(widths):
            acc += wd + space
            if acc > total / 2:
                split = max(1, i)
                break
        lines = [list(range(split)), list(range(split, len(words)))]
    age = t - chunk["start"]
    # pop in: 0.72 -> 1.12 -> 1.0
    pop = 0.72 + 0.4 * fx.ease_out(age / 0.09) if age < 0.09 else 1.0 + 0.12 * max(0.0, 1 - (age - 0.09) / 0.14)
    for li, idxs in enumerate(lines):
        y = CAP_Y + (li - (len(lines) - 1) / 2) * 104 * pop
        items = []
        for i in idxs:
            w, ws, we = chunk["words"][i]
            active = ws <= t < we
            f = fx.font(FONT_BOLD, 86 * pop * (1.1 if active else 1.0))
            items.append((i, active, f, f.getlength(words[i])))
        gap = space * pop
        x = (W - sum(it[3] for it in items) - gap * (len(items) - 1)) / 2
        for i, active, f, wd in items:
            col = AMBER if active else (255, 255, 255)
            d.text((x + wd / 2, y - (8 if active else 0)), words[i], font=f, fill=col,
                   stroke_width=max(4, int(10 * pop)), stroke_fill=(0, 0, 0), anchor="mm")
            x += wd + gap


def draw_hook(img, text, t):
    if t > 3.0:
        return
    a = 1.0 if t < 2.6 else max(0, 1 - (t - 2.6) / 0.4)
    sc = min(1.0, 0.7 + t * 2.0)
    base = 118
    while base > 60 and ImageFont.truetype(FONT_BOLD, base).getlength(text) > W - 140:
        base -= 4
    font = ImageFont.truetype(FONT_BOLD, int(base * sc))
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(lay).text((W / 2, 300), text, font=font, fill=AMBER + (int(255 * a),),
                             stroke_width=12, stroke_fill=(0, 0, 0, int(255 * a)), anchor="mm")
    img.alpha_composite(lay)


def draw_label(img, label, t):
    if not label:
        return
    a = min(1, t / 0.4)
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    tw = LABEL_FONT.getlength(label)
    x0, y0 = (W - tw) / 2 - 28, 440
    d.rounded_rectangle([x0, y0, x0 + tw + 56, y0 + 66], radius=33, fill=(0, 0, 0, int(150 * a)))
    d.text((W / 2, y0 + 33), label, font=LABEL_FONT, fill=(240, 232, 214, int(255 * a)), anchor="mm")
    img.alpha_composite(lay)


def post_fx():
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    vig = np.clip(1.08 - 0.42 * d ** 1.8, 0.45, 1.0)[..., None].astype(np.float32)
    rng = np.random.default_rng(1)
    grains = [rng.normal(0, 3, (H, W, 1)).astype(np.float32) for _ in range(4)]
    return vig, grains


def fmt_srt(t):
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int((s % 1) * 1000):03d}"


def photo_bg(path, credit=None):
    """Vertical Ken Burns background from a real photo, graded to match the channel look."""
    im = Image.open(path).convert("RGB")
    r = max(W / im.width, H / im.height)
    im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1), Image.LANCZOS)
    x0, y0 = (im.width - W) // 2, (im.height - H) // 2
    im = im.crop((x0, y0, x0 + W, y0 + H))
    a = np.asarray(im).astype(np.float32)
    lum = a.mean(axis=2, keepdims=True)
    a = (lum + (a - lum) * 0.85 - 128) * 1.05 + 118
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

    def overlay(img, draw, t, u, cam, ctx):
        if credit:
            ImageDraw.Draw(img).text((W - 24, 1600), credit, font=ImageFont.truetype(FONT_BOLD, 22),
                                     fill=(235, 235, 235, 210), anchor="rs", stroke_width=2, stroke_fill=(0, 0, 0))
    return im, overlay


def main(story_path, out_dir):
    t0 = time.time()
    story = json.load(open(story_path))
    os.makedirs(out_dir, exist_ok=True)
    sid = story["id"]
    SC.FOLLOW_TEXT = fx.word(fx.lang_of(story), "follow")

    print("1/4 narrating...", flush=True)
    voice, timeline = audio.narrate(story)
    duration = timeline[-1]["end"] + 0.5
    cuts = [sc["start"] for sc in timeline[1:]]
    bed = audio.music(duration, cuts)
    mixed = audio.mix(voice, bed)
    wav = os.path.join(out_dir, f"{sid}.wav")
    audio.save(wav, mixed)
    print(f"   duration {duration:.1f}s", flush=True)

    print("2/4 drawing scenes...", flush=True)
    built = []
    for i, sc in enumerate(timeline):
        rng = np.random.default_rng(100 + i)
        if sc["scene"] == "photo":
            spec = {k: sc[k] for k in ("photo_url", "credit") if sc.get(k)}
            spec.update({k[6:]: sc[k] for k in ("photo_file", "photo_search", "photo_category") if sc.get(k)})
            ph = fx.resolve_photo(spec, out_dir) if spec else None
            if ph:
                fx.record_credit(out_dir, sid, ph["credit"], ph.get("page"))
            bg, ov = (photo_bg(ph["path"], ph["credit"]) if ph else SCENES["question"](rng))
        else:
            bg, ov = SCENES[sc["scene"]](rng)
        bg = bg.resize((int(W * S), int(H * S)), Image.LANCZOS)
        ctx = {"lines": [ln["start"] - sc["start"] for ln in sc["lines"]], "dur": sc["end"] - sc["start"],
               "last": i == len(timeline) - 1}
        focal = fx.focal_points(bg, band=(350 / H, 1150 / H))
        plan = fx.ShotPlan(ctx["lines"], ctx["dur"], focal, seed=i, home=(0.5, 0.5))
        built.append((sc, bg, ov, ctx, plan))

    chunks = caption_chunks(timeline)
    vig, grains = post_fx()
    atmos = fx.Atmosphere(W, H, seed=len(sid))
    opener = fx.build_opener(story, out_dir, W, H, vertical=True)
    t_open = min(5.0, max(2.8, timeline[0]["lines"][0]["end"])) if opener else 0.0

    def scene_frame(i, t):
        sc, bg, ov, ctx, plan = built[i]
        dur = sc["end"] - sc["start"] + (FADE if i + 1 < len(built) else 0)
        lt = t - sc["start"]
        u = min(1, max(0, lt / dur))
        cam = shot_camera(plan, lt)
        crop = bg.crop((int(cam.x0), int(cam.y0), int(cam.x0 + cam.cw), int(cam.y0 + cam.ch)))
        img = crop.resize((W, H), Image.BILINEAR).convert("RGBA")
        ov(img, None, lt, u, cam, ctx)
        draw_label(img, sc.get("label"), lt)
        return img

    print("3/4 rendering frames...", flush=True)
    mp4 = os.path.join(out_dir, f"{sid}.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-maxrate", "8M", "-bufsize", "16M",
           "-pix_fmt", "yuv420p", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", mp4]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    nframes = int(duration * FPS)
    si = 0
    ci = 0
    cover_saved = False
    for f in range(nframes):
        t = f / FPS
        while si + 1 < len(built) and t >= built[si + 1][0]["start"]:
            si += 1
        if t < t_open:
            img = opener.frame(t, t_open)
        else:
            img = scene_frame(si, t)
            if si > 0 and t - built[si][0]["start"] < FADE:
                prev = scene_frame(si - 1, t)
                a = (t - built[si][0]["start"]) / FADE
                img = fx.transition(fx.KINDS[si % len(fx.KINDS)], prev, img, a)
            elif opener and t - t_open < FADE:
                img = fx.transition("flash", opener.frame(t, t_open), img, (t - t_open) / FADE)
        while ci + 1 < len(chunks) and t >= chunks[ci + 1]["start"]:
            ci += 1
        if chunks and chunks[ci]["start"] <= t < chunks[ci]["end"]:
            draw_caption(img, chunks[ci], t)
        draw_hook(img, story.get("hook", ""), t)
        arr = np.asarray(img.convert("RGB"), dtype=np.float32)
        arr *= vig
        atmos.apply(arr, t)
        arr = np.clip(arr + grains[f % 4], 0, 255).astype(np.uint8)
        ff.stdin.write(arr.tobytes())
        if not cover_saved and t >= 1.2:
            Image.fromarray(arr).save(os.path.join(out_dir, f"{sid}_cover.jpg"), quality=92)
            cover_saved = True
        if f % 150 == 0:
            print(f"   frame {f}/{nframes}  ({time.time() - t0:.0f}s)", flush=True)
    ff.stdin.close()
    ff.wait()

    print("4/4 captions file...", flush=True)
    with open(os.path.join(out_dir, f"{sid}.srt"), "w") as fh:
        n = 1
        for sc in timeline:
            for ln in sc["lines"]:
                fh.write(f"{n}\n{fmt_srt(ln['start'])} --> {fmt_srt(ln['end'])}\n{ln['text']}\n\n")
                n += 1
    json.dump(timeline, open(os.path.join(out_dir, f"{sid}_timeline.json"), "w"), indent=1)
    print(f"done in {time.time() - t0:.0f}s -> {mp4}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
