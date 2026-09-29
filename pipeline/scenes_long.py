"""Widescreen (1920x1080) cinematic scene library for long-form documentaries.

Each builder(rng) returns {"layers": [(RGBA canvas, depth)], "overlay": fn}.
Canvases are LW x LH (1.2x the frame) so the camera can pan with parallax:
a layer with depth 1.0 moves fully with the camera pan, depth 0.2 barely moves (far away).
overlay(img, t, u, cam, ctx) draws animated parts; cam.map(x, y, depth) -> frame coords.
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import os as _os


def _font_path(name, system_dir):
    here = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "assets", "fonts", name)
    return here if _os.path.exists(here) else _os.path.join(system_dir, name)



W, H = 1920, 1080
LW, LH = int(W * 1.2), int(H * 1.2)
BOLD = _font_path("Poppins-Bold.ttf", "/usr/share/fonts/truetype/google-fonts")
MED = _font_path("Poppins-Medium.ttf", "/usr/share/fonts/truetype/google-fonts")
SERIF = _font_path("Lora-Variable.ttf", "/usr/share/fonts/truetype/google-fonts")
AMBER = (255, 184, 82)
WARM = (255, 214, 150)
BONE = (226, 218, 198)
CYAN = (90, 200, 220)
INK = (6, 8, 12)


def font(path, size):
    return ImageFont.truetype(path, size)


def grad(stops, w=LW, h=LH):
    ys = np.linspace(0, 1, h)
    pos = [p for p, _ in stops]
    cols = np.array([c for _, c in stops], float)
    ch = [np.interp(ys, pos, cols[:, i]) for i in range(3)]
    arr = np.stack(ch, 1)[:, None, :].repeat(w, 1)
    a = np.full((h, w, 1), 255, np.uint8)
    return Image.fromarray(np.concatenate([arr.astype(np.uint8), a], 2), "RGBA")


def blank():
    return Image.new("RGBA", (LW, LH), (0, 0, 0, 0))


def soft(img, fn, radius):
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    fn(ImageDraw.Draw(lay))
    img.alpha_composite(lay.filter(ImageFilter.GaussianBlur(radius)))
    return img


def clouds(img, rng, n, y0, y1, color, alpha, radius=50):
    def fn(d):
        for _ in range(n):
            x, y = rng.uniform(-200, LW + 200), rng.uniform(y0, y1)
            rx, ry = rng.uniform(200, 520), rng.uniform(50, 130)
            d.ellipse([x - rx, y - ry, x + rx, y + ry], fill=color + (alpha,))
    return soft(img, fn, radius)


def stars(img, rng, n, ymax):
    d = ImageDraw.Draw(img)
    for _ in range(n):
        x, y = rng.uniform(0, LW), rng.uniform(0, ymax)
        b = int(rng.uniform(100, 220))
        r = rng.choice([1, 1, 1.5, 2])
        d.ellipse([x - r, y - r, x + r, y + r], fill=(b, b, min(255, b + 20), 255))
    return img


def ridge(img, rng, base_y, height, color, peaks=7, snow=None, jag=1.0):
    d = ImageDraw.Draw(img)
    xs = np.linspace(-150, LW + 150, peaks)
    pts, tops = [(-150, LH)], []
    for i, x in enumerate(xs):
        top = base_y - rng.uniform(*height)
        px = x + rng.uniform(-60, 60)
        # jagged shoulder
        pts.append((px - 70 * jag, top + rng.uniform(40, 90) * jag))
        pts.append((px, top))
        pts.append((px + 60 * jag, top + rng.uniform(30, 80) * jag))
        tops.append((px, top))
        if i < len(xs) - 1:
            pts.append(((x + xs[i + 1]) / 2, base_y - rng.uniform(40, 140)))
    pts.append((LW + 150, LH))
    d.polygon(pts, fill=color)
    if snow:
        for (x, top) in tops:
            h = rng.uniform(60, 120)
            d.polygon([(x, top), (x - h * 0.9, top + h), (x - h * 0.35, top + h * 0.8), (x, top + h * 1.15),
                       (x + h * 0.45, top + h * 0.75), (x + h * 0.9, top + h)], fill=snow)
    return img


def haze(img, y, height, color, alpha):
    def fn(d):
        d.rectangle([-100, y, LW + 100, y + height], fill=color + (alpha,))
    return soft(img, fn, 60)


def glow_sprite(r, color, strength=1.0):
    s = r * 2
    yy, xx = np.mgrid[0:s, 0:s]
    dist = np.sqrt((xx - r) ** 2 + (yy - r) ** 2) / r
    a = (np.clip(1 - dist, 0, 1) ** 2.2 * 255 * strength).astype(np.uint8)
    rgb = np.zeros((s, s, 3), np.uint8)
    rgb[:] = color
    return Image.fromarray(np.dstack([rgb, a]), "RGBA")


TORCH = glow_sprite(70, (255, 170, 70), 0.85)


def walker(d, x, y, s, phase, col, torch=None, lean=0.0, load=False):
    """Side-view walking figure facing right. (x, y) = feet level. Returns torch tip or None."""
    sw = math.sin(phase)
    hip = (x, y - s * 0.47)
    neck = (x + s * (0.05 + lean), y - s * 0.82)
    r = s * 0.075
    d.ellipse([neck[0] + s * 0.02 - r, neck[1] - s * 0.11 - r, neck[0] + s * 0.02 + r, neck[1] - s * 0.11 + r], fill=col)
    d.line([hip, neck], fill=col, width=max(3, int(s * 0.13)))
    if load:  # bundle on the back
        d.ellipse([neck[0] - s * 0.22, neck[1] - s * 0.02, neck[0] - s * 0.02, neck[1] + s * 0.22], fill=col)
    lw = max(2, int(s * 0.06))
    for k in (1, -1):
        a = sw * 0.45 * k
        knee = (hip[0] + math.sin(a) * s * 0.24, hip[1] + math.cos(a) * s * 0.24)
        foot = (knee[0] + math.sin(a - 0.25) * s * 0.24, y - max(0, math.sin(phase + (0 if k > 0 else math.pi))) * s * 0.03)
        d.line([hip, knee, foot], fill=col, width=lw, joint="curve")
    tip = None
    for k in (1, -1):
        a = -sw * 0.5 * k
        elbow = (neck[0] + math.sin(a) * s * 0.17, neck[1] + s * 0.17)
        if torch and k == 1:
            hand = (neck[0] + s * 0.18, neck[1] + s * 0.02)
            d.line([neck, (neck[0] + s * 0.1, neck[1] + s * 0.14), hand], fill=col, width=int(lw * 0.8), joint="curve")
            tip = (hand[0] + s * 0.06, hand[1] - s * 0.2)
            d.line([hand, tip], fill=(70, 50, 34), width=max(2, int(s * 0.03)))
        else:
            hand = (elbow[0] + math.sin(a + 0.6) * s * 0.15, elbow[1] + s * 0.1)
            d.line([neck, elbow, hand], fill=col, width=int(lw * 0.8), joint="curve")
    return tip


def flame(img, x, y, s, t, seed=0):
    g = TORCH.resize((int(TORCH.width * s), int(TORCH.height * s)))
    img.alpha_composite(g, (int(x - g.width / 2), int(y - g.height / 2)))
    d = ImageDraw.Draw(img)
    fl = 1 + 0.25 * math.sin(t * 17 + seed)
    d.polygon([(x - 6 * s, y + 4 * s), (x + 6 * s, y + 4 * s), (x + 1 * s, y - 20 * s * fl)], fill=(255, 210, 120, 255))
    d.polygon([(x - 3 * s, y + 3 * s), (x + 3 * s, y + 3 * s), (x, y - 11 * s * fl)], fill=(255, 250, 220, 255))


def hail(d, t, n, seed, speed=1500, size=(3, 8), slant=0.18):
    rng = np.random.default_rng(seed)
    for _ in range(n):
        x0, y0 = rng.uniform(-100, W + 300), rng.uniform(0, H)
        fall = (y0 + speed * t * rng.uniform(0.8, 1.2)) % (H + 60)
        x = x0 - slant * fall
        r = rng.uniform(*size)
        d.ellipse([x - r, fall - r, x + r, fall + r], fill=(228, 236, 244, 230))
        d.line([(x + r * 0.4, fall - r * 3), (x, fall)], fill=(228, 236, 244, 60), width=int(r))


def snow(d, t, n, seed, speed=60):
    rng = np.random.default_rng(seed)
    for _ in range(n):
        x0, y0, r = rng.uniform(0, W), rng.uniform(0, H), rng.uniform(1.5, 4.5)
        y = (y0 + speed * t * r / 3) % H
        x = x0 + 30 * math.sin(t * 0.7 + y0)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(240, 245, 250, int(rng.uniform(100, 200))))


def flash(img, t, times, dur=0.1, alpha=90):
    for s in times:
        if s <= t < s + dur:
            img.alpha_composite(Image.new("RGBA", img.size, (210, 225, 255, alpha)))


def skull(d, x, y, s, col=BONE, dark=(28, 28, 32)):
    d.ellipse([x - s, y - s, x + s, y + s * 0.9], fill=col)
    d.rounded_rectangle([x - s * 0.55, y + s * 0.5, x + s * 0.55, y + s * 1.2], radius=int(s * 0.2), fill=col)
    for k in (-1, 1):
        d.ellipse([x + k * s * 0.42 - s * 0.26, y - s * 0.05, x + k * s * 0.42 + s * 0.26, y + s * 0.42], fill=dark)
    d.polygon([(x, y + s * 0.45), (x - s * 0.12, y + s * 0.68), (x + s * 0.12, y + s * 0.68)], fill=dark)


def bone(d, x, y, L, a, col=BONE, w=10):
    x2, y2 = x + L * math.cos(a), y + L * math.sin(a)
    d.line([(x, y), (x2, y2)], fill=col, width=w)
    for (px, py) in ((x, y), (x2, y2)):
        for o in (-1, 1):
            ox, oy = -math.sin(a) * w * 0.55 * o, math.cos(a) * w * 0.55 * o
            d.ellipse([px + ox - w * 0.6, py + oy - w * 0.6, px + ox + w * 0.6, py + oy + w * 0.6], fill=col)


def text_c(d, xy, s, f, fill, **kw):
    d.text(xy, s, font=f, fill=fill, anchor="mm", **kw)


def path_y(x, base, amp, wl, ph=0.0):
    return base - amp * math.sin(x / wl + ph) - amp * 0.35 * math.sin(x / (wl * 0.4) + ph * 2)


# ======================= reconstruction scenes =======================
def cold_open_storm(rng):
    sky = grad([(0, (6, 8, 14)), (0.55, (22, 28, 40)), (1, (30, 36, 46))])
    sky = stars(sky, rng, 60, 300)
    sky = clouds(sky, rng, 22, 40, 520, (44, 50, 62), 170, 60)
    far = ridge(blank(), rng, 820, (300, 520), (30, 36, 48, 255), peaks=6, snow=(120, 132, 148, 255))
    far = haze(far, 760, 160, (40, 46, 58), 120)
    near = blank()
    d = ImageDraw.Draw(near)
    pts = [(x, path_y(x, 900, 60, 420)) for x in range(-100, LW + 101, 20)]
    d.polygon([(-100, LH)] + pts + [(LW + 100, LH)], fill=(12, 14, 18, 255))

    def overlay(img, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        k = cam.k(0.9)
        tips = []
        for i in range(11):
            wx = (i * 190 + t * 38) % (LW + 200) - 100
            fx, fy = cam.map(wx, path_y(wx, 900, 60, 420), 0.9)
            tip = walker(d2, fx, fy, 150 * k, t * 4 + i * 1.3, (4, 5, 7, 255), torch=(i % 3 == 0), lean=0.04, load=(i % 3 == 1))
            if tip:
                tips.append((tip, i))
        for (tx, ty), i in tips:
            flame(img, tx, ty, 0.9 * k, t, i)
        lines = ctx["lines"]
        start = lines[2] if len(lines) > 2 else 6
        if t > start - 0.5:
            n = int(min(260, (t - start + 0.5) * 120))
            hail(ImageDraw.Draw(img), t, n, 3)
        flash(img, t, [start - 0.2, start + 1.6, start + 3.1])
    return {"layers": [(sky, 0.15), (far, 0.4), (near, 0.9)], "overlay": overlay}


def ranger_1942(rng):
    sky = grad([(0, (40, 58, 86)), (0.5, (150, 150, 160)), (0.62, (226, 190, 150)), (1, (80, 88, 96))])
    sky = clouds(sky, rng, 12, 60, 400, (200, 190, 190), 90, 60)
    far = ridge(blank(), rng, 700, (320, 520), (70, 84, 104, 255), peaks=5, snow=(236, 238, 244, 255))
    far = haze(far, 640, 150, (200, 200, 210), 70)
    near = blank()
    d = ImageDraw.Draw(near)
    d.polygon([(-100, 820), (LW + 100, 760), (LW + 100, LH), (-100, LH)], fill=(92, 96, 100, 255))
    d.ellipse([500, 820, 1900, 1080], fill=(170, 205, 222, 255))
    d.ellipse([600, 860, 1800, 1050], fill=(128, 170, 190, 255))
    for _ in range(40):
        x, y = rng.uniform(420, 1980), rng.choice([rng.uniform(800, 850), rng.uniform(1040, 1200)])
        bone(d, x, y, rng.uniform(26, 60), rng.uniform(0, 3.14), w=8)
    for _ in range(9):
        skull(d, rng.uniform(500, 1900), rng.uniform(1060, 1180), 18)
    for _ in range(8):  # bones frozen in the ice
        bone(d, rng.uniform(700, 1700), rng.uniform(900, 1010), rng.uniform(30, 60), rng.uniform(0, 3.14), col=(200, 214, 220), w=7)

    def overlay(img, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        k = cam.k(1.0)
        wx = 150 + min(1, u * 1.4) * 250
        fx, fy = cam.map(wx, 900, 1.0)
        s = 420 * k
        stop = u > 0.7
        walker(d2, fx, fy, s, 0 if stop else t * 3.2, (14, 16, 18, 255))
        # hat + walking stick
        hx, hy = fx + s * 0.07, fy - s * 0.93
        d2.ellipse([hx - s * 0.13, hy - s * 0.02, hx + s * 0.13, hy + s * 0.04], fill=(14, 16, 18))
        d2.rectangle([hx - s * 0.07, hy - s * 0.09, hx + s * 0.07, hy + s * 0.01], fill=(14, 16, 18))
        d2.line([(fx + s * 0.25, fy - s * 0.55), (fx + s * 0.34, fy)], fill=(60, 44, 30), width=int(8 * k))
        snow(d2, t, 60, 5, 40)
    return {"layers": [(sky, 0.15), (far, 0.4), (near, 1.0)], "overlay": overlay}


def pilgrim_caravan(rng):
    sky = grad([(0, (40, 30, 60)), (0.45, (190, 110, 80)), (0.6, (240, 170, 110)), (1, (60, 40, 40))])
    sky = clouds(sky, rng, 14, 60, 420, (230, 140, 110), 90, 60)
    far = ridge(blank(), rng, 720, (320, 560), (90, 60, 80, 255), peaks=6, snow=(255, 214, 190, 255))
    far = haze(far, 650, 160, (230, 160, 120), 80)
    mid = ridge(blank(), rng, 860, (100, 220), (50, 34, 44, 255), peaks=9, jag=0.6)
    near = blank()
    d = ImageDraw.Draw(near)
    pts = [(x, path_y(x, 960, 40, 500, 1.0)) for x in range(-100, LW + 101, 20)]
    d.polygon([(-100, LH)] + pts + [(LW + 100, LH)], fill=(20, 12, 16, 255))

    def overlay(img, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        k = cam.k(0.95)
        col = (16, 10, 14, 255)
        tips = []
        order = ["flag", "w", "drum", "w", "dancer", "dancer", "pal", "w", "w", "flag", "w", "w"]
        for i, kind in enumerate(order):
            wx = 2200 - i * 175 + t * 34
            fx, fy = cam.map(wx, path_y(wx, 960, 40, 500, 1.0), 0.95)
            s = 165 * k
            if kind == "pal":  # palanquin carried by four
                for j in (-0.5, -0.17, 0.17, 0.5):
                    walker(d2, fx + j * s * 1.5, fy, s, t * 4 + j * 3, col)
                bx, by = fx, fy - s * 0.95
                d2.line([(bx - s * 1.0, by + s * 0.1), (bx + s * 1.0, by + s * 0.1)], fill=col, width=int(8 * k))
                d2.rectangle([bx - s * 0.45, by - s * 0.55, bx + s * 0.45, by + s * 0.08], fill=(60, 26, 20, 255))
                d2.polygon([(bx - s * 0.6, by - s * 0.55), (bx + s * 0.6, by - s * 0.55), (bx, by - s * 0.95)], fill=(170, 40, 30, 255))
                d2.rectangle([bx - s * 0.2, by - s * 0.4, bx + s * 0.2, by - s * 0.1], fill=(255, 190, 90, 255))
            elif kind == "dancer":
                ph = t * 6 + i
                cx, cy = fx, fy
                r = s * 0.075
                d2.ellipse([cx - r, cy - s * 0.95 - r, cx + r, cy - s * 0.95 + r], fill=col)
                d2.line([(cx, cy - s * 0.85), (cx, cy - s * 0.45)], fill=col, width=int(s * 0.12))
                sk = 0.25 + 0.08 * math.sin(ph)
                d2.polygon([(cx - s * 0.08, cy - s * 0.5), (cx + s * 0.08, cy - s * 0.5), (cx + s * sk, cy - s * 0.05), (cx - s * sk, cy - s * 0.05)], fill=(120, 30, 40, 255))
                for a in (math.sin(ph) * 1.2, math.pi - math.sin(ph) * 1.2):
                    d2.line([(cx, cy - s * 0.8), (cx + math.cos(a) * s * 0.3, cy - s * 0.8 - abs(math.sin(a)) * s * 0.25)], fill=col, width=int(s * 0.05))
            else:
                tip = walker(d2, fx, fy, s, t * 4 + i, col, torch=(kind == "w" and i % 2 == 1))
                if kind == "flag":
                    d2.line([(fx + s * 0.2, fy - s * 0.6), (fx + s * 0.2, fy - s * 1.7)], fill=col, width=int(5 * k))
                    wv = 8 * math.sin(t * 5 + i)
                    d2.polygon([(fx + s * 0.2, fy - s * 1.7), (fx + s * 0.75, fy - s * 1.58 + wv), (fx + s * 0.2, fy - s * 1.42)], fill=(200, 60, 40, 255))
                if kind == "drum":
                    d2.ellipse([fx + s * 0.05, fy - s * 0.62, fx + s * 0.4, fy - s * 0.38], fill=(110, 60, 30, 255))
                if tip:
                    tips.append((tip, i))
        for (tx, ty), i in tips:
            flame(img, tx, ty, 0.85 * k, t, i)
    return {"layers": [(sky, 0.1), (far, 0.35), (mid, 0.6), (near, 0.95)], "overlay": overlay}


def hail_strike(rng):
    sky = grad([(0, (20, 24, 34)), (0.6, (70, 78, 94)), (1, (40, 44, 52))])
    sky = clouds(sky, rng, 26, 0, 600, (90, 96, 110), 200, 70)
    near = blank()
    d = ImageDraw.Draw(near)
    d.polygon([(-100, 860), (LW + 100, 820), (LW + 100, LH), (-100, LH)], fill=(34, 36, 42, 255))
    for _ in range(30):
        x, y, r = rng.uniform(0, LW), rng.uniform(870, LH), rng.uniform(20, 60)
        d.ellipse([x - r, y - r * 0.5, x + r, y + r * 0.5], fill=(46, 48, 54, 255))

    def overlay(img, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        k = cam.k(1.0)
        col = (6, 7, 9, 255)
        for i, (wx, crouch) in enumerate([(500, 0.0), (760, 0.5), (980, 1.0), (1250, 0.3), (1500, 0.8), (1760, 0.6)]):
            fx, fy = cam.map(wx, 880, 1.0)
            s = 330 * k
            c = min(1, crouch + u * 0.9)
            h = s * (1 - 0.45 * c)
            r = s * 0.075
            hx = fx + s * 0.1 * c
            d2.ellipse([hx - r, fy - h * 0.92 - r, hx + r, fy - h * 0.92 + r], fill=col)
            d2.line([(fx, fy - h * 0.45), (hx, fy - h * 0.82)], fill=col, width=int(s * 0.13))
            d2.line([(fx, fy - h * 0.45), (fx - s * 0.12, fy)], fill=col, width=int(s * 0.07))
            d2.line([(fx, fy - h * 0.45), (fx + s * 0.14 * (1 - c), fy)], fill=col, width=int(s * 0.07))
            # arms shielding the head
            d2.line([(hx, fy - h * 0.8), (hx - s * 0.12, fy - h * 1.02), (hx + s * 0.1, fy - h * 1.08)], fill=col, width=int(s * 0.05), joint="curve")
        hail(ImageDraw.Draw(img), t, 320, 9, speed=1900, size=(4, 11))
        flash(img, t, [0.4, 2.2, 2.35, 4.5], alpha=110)
    return {"layers": [(sky, 0.2), (near, 1.0)], "overlay": overlay}


# ======================= explainer / graphic scenes =======================
def paper_bg(rng, tint=(222, 208, 176)):
    bg = grad([(0, tint), (1, tuple(int(c * 0.8) for c in tint))])
    arr = np.asarray(bg).astype(np.int16)
    noise = rng.normal(0, 6, arr.shape[:2])[..., None]
    arr[..., :3] = np.clip(arr[..., :3] + noise, 0, 255)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def ww2_theory(rng):
    bg = grad([(0, (20, 18, 16)), (1, (40, 34, 28))])
    paper = blank()
    pp = paper_bg(rng).crop((0, 0, 1300, 900))
    pd = ImageDraw.Draw(pp)
    text_c(pd, (650, 90), "THE HIMALAYAN GAZETTE", font(SERIF, 64), (30, 26, 22))
    pd.line([(60, 150), (1240, 150)], fill=(30, 26, 22), width=4)
    text_c(pd, (650, 200), "1942  ·  WARTIME EDITION", font(MED, 30), (60, 52, 44))
    text_c(pd, (650, 320), "BONES FOUND AT", font(BOLD, 92), (24, 20, 16))
    text_c(pd, (650, 430), "MOUNTAIN LAKE", font(BOLD, 92), (24, 20, 16))
    text_c(pd, (650, 520), "Officials ask: Japanese invaders?", font(SERIF, 42), (40, 34, 28))
    for col in range(3):
        for i in range(8):
            x0 = 80 + col * 390
            y = 600 + i * 34
            pd.line([(x0, y), (x0 + rng.uniform(250, 340), y)], fill=(90, 80, 70), width=6)
    pp = pp.rotate(-3, expand=True, resample=Image.BICUBIC)
    paper.alpha_composite(pp, (int(LW / 2 - pp.width / 2), int(LH / 2 - pp.height / 2)))

    def overlay(img, t, u, cam, ctx):
        lines = ctx["lines"]
        if len(lines) > 2 and t >= lines[2]:
            a = min(1, (t - lines[2]) / 0.3)
            sc = max(1.0, 1.5 - (t - lines[2]) * 2)
            st = Image.new("RGBA", (760, 200), (0, 0, 0, 0))
            sd = ImageDraw.Draw(st)
            sd.rounded_rectangle([6, 6, 754, 194], radius=16, fill=(240, 230, 210, int(220 * a)), outline=(190, 40, 36, int(255 * a)), width=12)
            text_c(sd, (380, 100), "RULED OUT", font(BOLD, 96), (190, 40, 36, int(255 * a)))
            st = st.resize((int(760 * sc), int(200 * sc))).rotate(8, expand=True, resample=Image.BICUBIC)
            img.alpha_composite(st, (int(W * 0.68 - st.width / 2), int(H * 0.76 - st.height / 2)))
    return {"layers": [(bg, 0.1), (paper, 0.6)], "overlay": overlay}


def dark_bg(c1=(8, 14, 22), c2=(16, 26, 38)):
    return grad([(0, c1), (1, c2)])


def skull_evidence(rng):
    bg = dark_bg()
    lay = blank()
    d = ImageDraw.Draw(lay)
    cx, cy, s = LW / 2 - 200, LH / 2 + 60, 250
    skull(d, cx, cy, s)
    lay = soft(lay, lambda dd: dd.ellipse([cx - 420, cy - 420, cx + 420, cy + 420], fill=(80, 140, 170, 40)), 80)

    def overlay(img, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        k = cam.k(0.6)
        X, Y = cam.map(cx, cy, 0.6)
        lines = ctx["lines"]
        t1 = lines[1] if len(lines) > 1 else 1
        t2 = lines[2] if len(lines) > 2 else 3
        if t >= t1:  # cracks on the crown
            p = min(1, (t - t1) / 1.2)
            for j, (ox, oy) in enumerate([(-80, -200), (30, -230), (120, -180)]):
                if p > j / 3:
                    x0, y0 = X + ox * k, Y + oy * k
                    d2.line([(x0, y0), (x0 + 18 * k, y0 + 40 * k), (x0 - 6 * k, y0 + 70 * k), (x0 + 12 * k, y0 + 96 * k)], fill=(170, 30, 30), width=int(7 * k))
        if t >= t2:  # round objects falling from above
            for j, ox in enumerate([-80, 30, 120]):
                fall = ((t - t2) * 420 + j * 140) % 420
                bx, by = X + ox * k + 9 * k, Y - 700 * k + fall * k
                d2.ellipse([bx - 26 * k, by - 26 * k, bx + 26 * k, by + 26 * k], fill=(220, 232, 240))
                d2.line([(bx, by - 120 * k), (bx, by - 40 * k)], fill=(220, 232, 240, 120), width=int(5 * k))
        f = font(BOLD, 44)
        fs = font(MED, 32)
        if t >= t1:
            d2.text((1180, 420), "Short, deep cracks", font=font(BOLD, 54), fill=(240, 232, 214))
            d2.text((1180, 484), "on the top of the skull", font=font(MED, 38), fill=(180, 190, 200))
        if t >= t2:
            d2.text((1180, 600), "Blows from above", font=font(BOLD, 54), fill=(240, 232, 214))
            d2.text((1180, 664), "round, hard objects, like hail", font=font(MED, 38), fill=(180, 190, 200))
    return {"layers": [(bg, 0.1), (lay, 0.6)], "overlay": overlay}


def timeline_axis(d, x0, x1, y, years, lo, hi, f):
    d.line([(x0, y), (x1, y)], fill=(150, 160, 170), width=5)
    for yr in years:
        x = x0 + (yr - lo) / (hi - lo) * (x1 - x0)
        d.line([(x, y - 14), (x, y + 14)], fill=(150, 160, 170), width=4)
        d.text((x, y + 48), f"{yr}", font=f, fill=(170, 180, 190), anchor="mm")


def carbon_date(rng):
    bg = dark_bg()

    def overlay(img, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        x0, x1, y, lo, hi = 260, 1660, 640, 600, 1100
        timeline_axis(d2, x0, x1, y, [600, 700, 800, 900, 1000, 1100], lo, hi, font(MED, 34))
        p = min(1, t / 2.0)
        yr = lo + (850 - lo) * (1 - (1 - p) ** 3)
        x = x0 + (yr - lo) / (hi - lo) * (x1 - x0)
        d2.ellipse([x - 26, y - 26, x + 26, y + 26], fill=AMBER)
        d2.line([(x, y - 30), (x, y - 190)], fill=AMBER, width=4)
        d2.text((x, y - 250), f"~{int(round(yr / 10) * 10)} AD", font=font(BOLD, 88), fill=AMBER, anchor="mm")
        d2.text((W / 2, 230), "Oxford radiocarbon date", font=font(MED, 44), fill=(200, 208, 216), anchor="mm")
        lines = ctx["lines"]
        if len(lines) > 2 and t >= lines[2]:
            d2.text((W / 2, 820), "One storm. One night?", font=font(BOLD, 56), fill=(240, 232, 214), anchor="mm")
    return {"layers": [(bg, 0.1)], "overlay": overlay}


def dna_lab_wide(rng):
    bg = dark_bg((4, 12, 18), (8, 26, 34))
    lay = blank()
    lay = soft(lay, lambda d: d.ellipse([LW / 2 - 500, LH / 2 - 500, LW / 2 + 500, LH / 2 + 500], fill=(40, 200, 190, 50)), 120)

    def overlay(img, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        cy = H / 2
        for i in range(40):
            x = 120 + i * 43
            ph = t * 2.0 + i * 0.35
            a = 170 * math.sin(ph)
            depth = math.cos(ph)
            y1, y2 = cy + a, cy - a
            d2.line([(x, y1), (x, y2)], fill=(120, 200, 210, 110), width=4)
            c1 = AMBER if depth > 0 else (170, 110, 50)
            c2 = CYAN if depth < 0 else (50, 120, 130)
            d2.ellipse([x - 12, y1 - 12, x + 12, y1 + 12], fill=c1)
            d2.ellipse([x - 12, y2 - 12, x + 12, y2 + 12], fill=c2)
        # scrolling sequence strip
        f = font(MED, 30)
        seq = "ACGTTGCAAGCTTACGGATCCGTAGCTAGGCTTAACG"
        off = int(t * 6)
        s = "".join(seq[(off + j) % len(seq)] for j in range(60))
        d2.text((W / 2, 900), "  ".join(s[:30]), font=f, fill=(90, 200, 190), anchor="mm")
    return {"layers": [(bg, 0.1), (lay, 0.3)], "overlay": overlay}


def groups_chart(rng):
    bg = dark_bg()

    def overlay(img, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        lines = ctx["lines"]
        groups = [(23, AMBER, "23  South Asian"), (14, CYAN, "14  Eastern Mediterranean"), (1, (200, 120, 230), "1  Southeast Asian")]
        idx = 0
        for gi, (n, col, lab) in enumerate(groups):
            start = lines[gi] if gi < len(lines) else 0
            for j in range(n):
                show = t >= start + j * 0.05
                x = 330 + (idx % 13) * 96
                y = 300 + (idx // 13) * 110
                idx += 1
                if not show:
                    d2.ellipse([x - 30, y - 30, x + 30, y + 30], outline=(60, 70, 80), width=3)
                    continue
                d2.ellipse([x - 12, y - 42, x + 12, y - 18], fill=col)
                d2.rounded_rectangle([x - 20, y - 14, x + 20, y + 34], radius=10, fill=col)
            if t >= start:
                d2.text((330 - 20, 800 + gi * 64), lab, font=font(BOLD, 44), fill=col)
        d2.text((W / 2, 150), "38 skeletons sequenced", font=font(MED, 44), fill=(200, 208, 216), anchor="mm")
    return {"layers": [(bg, 0.1)], "overlay": overlay}


def two_eras(rng):
    bg = dark_bg()

    def overlay(img, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        lines = ctx["lines"]
        x0, x1, y, lo, hi = 200, 1720, 620, 600, 2000
        timeline_axis(d2, x0, x1, y, [600, 800, 1000, 1200, 1400, 1600, 1800, 2000], lo, hi, font(MED, 32))
        X = lambda yr: x0 + (yr - lo) / (hi - lo) * (x1 - x0)
        if len(lines) > 1 and t >= lines[1]:
            for j in range(23):
                d2.ellipse([X(800) - 60 + (j % 6) * 24 - 8, y - 150 - (j // 6) * 24 - 8, X(800) - 60 + (j % 6) * 24 + 8, y - 150 - (j // 6) * 24 + 8], fill=AMBER)
            d2.text((X(800), y - 300), "~800 AD", font=font(BOLD, 56), fill=AMBER, anchor="mm")
        if len(lines) > 2 and t >= lines[2]:
            for j in range(15):
                c = CYAN if j < 14 else (200, 120, 230)
                d2.ellipse([X(1800) - 50 + (j % 5) * 24 - 8, y - 150 - (j // 5) * 24 - 8, X(1800) - 50 + (j % 5) * 24 + 8, y - 150 - (j // 5) * 24 + 8], fill=c)
            d2.text((X(1800), y - 300), "~1800 AD", font=font(BOLD, 56), fill=CYAN, anchor="mm")
        if len(lines) > 3 and t >= lines[3]:
            p = min(1, (t - lines[3]) / 1.0)
            xa, xb = X(800), X(800) + (X(1800) - X(800)) * p
            d2.line([(xa, y + 130), (xb, y + 130)], fill=(240, 232, 214), width=6)
            d2.polygon([(xb, y + 118), (xb + 22, y + 130), (xb, y + 142)], fill=(240, 232, 214))
            d2.text(((X(800) + X(1800)) / 2, y + 190), "1,000 YEARS APART", font=font(BOLD, 50), fill=(240, 232, 214), anchor="mm")
    return {"layers": [(bg, 0.1)], "overlay": overlay}


def diet_cards(rng):
    bg = dark_bg()

    def overlay(img, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        lines = ctx["lines"]
        show2 = len(lines) > 1 and t >= lines[1]
        for i, (title, sub, col) in enumerate([("Eastern Mediterranean group", "mostly wheat and barley-type crops", CYAN),
                                               ("South Asian group", "a more varied diet", AMBER)]):
            if i == 0 and not show2:
                continue
            if i == 1 and not show2:
                continue
            x = 260 + i * 720
            d2.rounded_rectangle([x, 330, x + 660, 750], radius=28, outline=col, width=5, fill=(14, 22, 32))
            d2.text((x + 330, 430), title, font=font(BOLD, 40), fill=col, anchor="mm")
            d2.text((x + 330, 500), sub, font=font(MED, 32), fill=(210, 216, 222), anchor="mm")
            for g in range(7):  # grain stalks
                gx = x + 180 + g * 50
                d2.line([(gx, 690), (gx, 580)], fill=col, width=4)
                for e in range(4):
                    d2.ellipse([gx - 12, 585 + e * 22 - 8, gx, 585 + e * 22 + 8], fill=col)
                    d2.ellipse([gx, 585 + e * 22 - 8, gx + 12, 585 + e * 22 + 8], fill=col)
        d2.text((W / 2, 180), "What their bones say they ate", font=font(MED, 44), fill=(200, 208, 216), anchor="mm")
    return {"layers": [(bg, 0.1)], "overlay": overlay}


def route_map_wide(rng):
    bg = dark_bg((10, 16, 26), (18, 26, 38))
    grid = blank()
    d = ImageDraw.Draw(grid)
    for x in range(0, LW, 80):
        d.line([(x, 0), (x, LH)], fill=(24, 34, 48, 255), width=2)
    for y in range(0, LH, 80):
        d.line([(0, y), (LW, y)], fill=(24, 34, 48, 255), width=2)

    def overlay(img, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        p0, p1 = (360, 560), (1560, 640)
        prog = min(1, u * 1.5)
        n = 90
        for i in range(int(n * prog)):
            s = i / n
            x = p0[0] + (p1[0] - p0[0]) * s
            y = p0[1] + (p1[1] - p0[1]) * s - 300 * math.sin(math.pi * s)
            if i % 2 == 0:
                d2.ellipse([x - 7, y - 7, x + 7, y + 7], fill=(240, 232, 214))
        for (px, py), lab, col in ((p0, "EASTERN MEDITERRANEAN", CYAN), (p1, "ROOPKUND, HIMALAYAS", AMBER)):
            d2.ellipse([px - 24, py - 24, px + 24, py + 24], fill=col)
            d2.text((px, py + 70), lab, font=font(BOLD, 40), fill=col, anchor="mm")
        if prog > 0.6:
            d2.text((W / 2, 150), "about 5,000 km", font=font(BOLD, 52), fill=(240, 232, 214), anchor="mm")
            d2.text((W / 2, 206), "around the year 1800", font=font(MED, 34), fill=(180, 190, 200), anchor="mm")
    return {"layers": [(bg, 0.1), (grid, 0.5)], "overlay": overlay}


def theories(rng):
    bg = dark_bg()

    def overlay(img, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        lines = ctx["lines"]
        cards = [("PILGRIMS?", "joined a Hindu pilgrimage"), ("TRADERS?", "lost on a mountain crossing"), ("FORGOTTEN?", "never written down")]
        for i, (a, b) in enumerate(cards):
            if i < len(lines) and t >= lines[i]:
                p = min(1, (t - lines[i]) / 0.35)
                x = 180 + i * 540
                y = 360 + (1 - p) * 60
                d2.rounded_rectangle([x, y, x + 480, y + 360], radius=28, fill=(16, 24, 34), outline=AMBER if i == 2 else (120, 140, 160), width=5)
                d2.text((x + 240, y + 130), a, font=font(BOLD, 64), fill=(240, 232, 214), anchor="mm")
                d2.text((x + 240, y + 230), b, font=font(MED, 30), fill=(180, 190, 200), anchor="mm")
        if len(lines) > 3 and t >= lines[3]:
            d2.text((W / 2, 860), "Nobody knows.", font=font(BOLD, 64), fill=AMBER, anchor="mm")
    return {"layers": [(bg, 0.1)], "overlay": overlay}


def outro_long(rng):
    sky = grad([(0, (6, 10, 22)), (0.55, (36, 48, 76)), (1, (20, 26, 36))])
    sky = stars(sky, rng, 120, 500)
    far = ridge(blank(), rng, 820, (280, 480), (30, 38, 56, 255), peaks=6, snow=(170, 184, 204, 255))
    near = blank()
    d = ImageDraw.Draw(near)
    d.rectangle([-50, 880, LW + 50, LH], fill=(40, 46, 56, 255))
    d.ellipse([600, 900, 1700, 1040], fill=(130, 166, 186, 255))

    def overlay(img, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        snow(d2, t, 70, 21, 40)
        d2.text((W / 2, 330), "?", font=font(BOLD, 300), fill=(255, 214, 150, 235), anchor="mm")
        lines = ctx["lines"]
        if len(lines) > 3 and t >= lines[3]:
            f = font(BOLD, 52)
            txt = "SUBSCRIBE FOR DAILY MYSTERIES"
            tw = f.getlength(txt)
            x0, y0 = (W - tw) / 2 - 50, 600
            d2.rounded_rectangle([x0, y0, x0 + tw + 100, y0 + 110], radius=55, fill=(214, 40, 40, 245))
            d2.text((W / 2, y0 + 55), txt, font=f, fill=(255, 255, 255), anchor="mm")
    return {"layers": [(sky, 0.15), (far, 0.4), (near, 0.9)], "overlay": overlay}


# ======================= photo scene =======================
def photo_scene(path, credit=None):
    def build(rng):
        im = Image.open(path).convert("RGB")
        # cover-crop to the canvas
        r = max(LW / im.width, LH / im.height)
        im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1), Image.LANCZOS)
        x0, y0 = (im.width - LW) // 2, (im.height - LH) // 2
        im = im.crop((x0, y0, x0 + LW, y0 + LH))
        # gentle documentary grade: slightly cool and contrasty
        a = np.asarray(im).astype(np.float32)
        lum = a.mean(axis=2, keepdims=True)
        a = lum + (a - lum) * 0.88
        a = (a - 128) * 1.06 + 124
        a[..., 2] += 6
        im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).convert("RGBA")

        def overlay(img, t, u, cam, ctx):
            if credit:
                d2 = ImageDraw.Draw(img)
                d2.text((40, H - 40), credit, font=font(MED, 22), fill=(230, 230, 230, 200), anchor="ls",
                        stroke_width=2, stroke_fill=(0, 0, 0, 160))
        return {"layers": [(im, 0.7)], "overlay": overlay}
    return build


def missing_photo(label):
    """Fallback when a photo has not been supplied: illustrated lake."""
    def build(rng):
        sc = outro_long(rng)
        base = sc["overlay"]

        def overlay(img, t, u, cam, ctx):
            snow(ImageDraw.Draw(img), t, 70, 21, 40)
        return {"layers": sc["layers"], "overlay": overlay}
    return build


SCENES = {f.__name__: f for f in [cold_open_storm, ranger_1942, pilgrim_caravan, hail_strike, ww2_theory,
                                  skull_evidence, carbon_date, dna_lab_wide, groups_chart, two_eras, diet_cards,
                                  route_map_wide, theories, outro_long]}


# ======================= reusable, parameterised scenes =======================
# Stories use these with fields on the scene itself, e.g.
#   {"scene": "title_card", "text": "SEPTEMBER 1872", "sub": "Atlantic Ocean", "lines": [...]}
#   {"scene": "timeline", "events": [{"year": 1872, "label": "Found adrift"}, ...], "lines": [...]}
#   {"scene": "route", "from": "NEW YORK", "to": "GENOA", "note": "about 7,000 km", "lines": [...]}
#   {"scene": "facts", "title": "What was found", "facts": ["Six months of food", "..."], "lines": [...]}
#   {"scene": "night_sea" | "night_mountains" | "desert_night" | "forest_night" | "city_night", "lines": [...]}
def _wrap(text, f, width):
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if f.getlength(t) > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = t
    if cur:
        lines.append(cur)
    return lines


def title_card(rng, sc):
    bg = grad([(0, (8, 12, 20)), (1, (22, 28, 40))])
    bg = stars(bg, rng, 90, LH)
    fog = clouds(blank(), rng, 10, LH * 0.5, LH, (60, 70, 84), 70, 70)

    def overlay(img, t, u, cam, ctx):
        d = ImageDraw.Draw(img)
        a = int(255 * min(1, t / 0.8))
        f = font(BOLD, 110 if len(sc.get("text", "")) < 18 else 80)
        for i, ln in enumerate(_wrap(sc.get("text", ""), f, W - 240)):
            d.text((W / 2, H / 2 - 40 + i * 110), ln, font=f, fill=AMBER + (a,), anchor="mm")
        if sc.get("sub"):
            d.text((W / 2, H / 2 + 110), sc["sub"], font=font(MED, 44), fill=(220, 214, 200, a), anchor="mm")
    return {"layers": [(bg, 0.15), (fog, 0.5)], "overlay": overlay}


def timeline(rng, sc):
    bg = dark_bg()
    ev = sc.get("events", [])

    def overlay(img, t, u, cam, ctx):
        d = ImageDraw.Draw(img)
        if not ev:
            return
        x0, x1, y = 180, 1740, 600
        d.line([(x0, y), (x1, y)], fill=(150, 160, 170), width=5)
        lines = ctx["lines"]
        n = len(ev)
        for i, e in enumerate(ev):
            x = x0 + (x1 - x0) * (i / max(1, n - 1) if n > 1 else 0.5)
            show = t >= (lines[min(i, len(lines) - 1)] if lines else 0) - 0.2 or i == 0
            if not show:
                d.ellipse([x - 10, y - 10, x + 10, y + 10], outline=(90, 100, 110), width=3)
                continue
            last = i == n - 1
            col = AMBER if last or e.get("key") else (230, 230, 230)
            d.ellipse([x - 18, y - 18, x + 18, y + 18], fill=col)
            up = i % 2 == 0
            d.text((x, y - 70 if up else y + 70), str(e.get("year", "")), font=font(BOLD, 48), fill=col, anchor="mm")
            for j, ln in enumerate(_wrap(e.get("label", ""), font(MED, 30), 300)):
                yy = (y - 130 - 40 * j) if up else (y + 130 + 40 * j)
                d.text((x, yy), ln, font=font(MED, 30), fill=(210, 216, 222), anchor="mm")
        if sc.get("title"):
            d.text((W / 2, 160), sc["title"], font=font(MED, 44), fill=(200, 208, 216), anchor="mm")
    return {"layers": [(bg, 0.1)], "overlay": overlay}


def route(rng, sc):
    spec = route_map_wide(rng)
    layers = spec["layers"]

    def overlay(img, t, u, cam, ctx):
        d = ImageDraw.Draw(img)
        p0, p1 = (360, 600), (1560, 600)
        prog = min(1, u * 1.5)
        for i in range(int(90 * prog)):
            s = i / 90
            x = p0[0] + (p1[0] - p0[0]) * s
            yy = p0[1] - 300 * math.sin(math.pi * s)
            if i % 2 == 0:
                d.ellipse([x - 7, yy - 7, x + 7, yy + 7], fill=(240, 232, 214))
        for (px, py), lab, col in ((p0, sc.get("from", ""), CYAN), (p1, sc.get("to", ""), AMBER)):
            d.ellipse([px - 24, py - 24, px + 24, py + 24], fill=col)
            d.text((px, py + 70), str(lab).upper(), font=font(BOLD, 40), fill=col, anchor="mm")
        if sc.get("note") and prog > 0.6:
            d.text((W / 2, 170), sc["note"], font=font(BOLD, 52), fill=(240, 232, 214), anchor="mm")
    return {"layers": layers, "overlay": overlay}


def facts(rng, sc):
    bg = dark_bg()
    items = sc.get("facts", [])

    def overlay(img, t, u, cam, ctx):
        d = ImageDraw.Draw(img)
        if sc.get("title"):
            d.text((W / 2, 170), sc["title"], font=font(BOLD, 60), fill=AMBER, anchor="mm")
        lines = ctx["lines"]
        y = 300
        for i, f_ in enumerate(items):
            start = lines[min(i, len(lines) - 1)] if lines else 0
            if t < start - 0.2 and i > 0:
                break
            a = int(255 * min(1, (t - start + 0.2) / 0.4)) if i > 0 else 255
            d.rounded_rectangle([300, y, 1620, y + 110], radius=20, fill=(18, 26, 38, a), outline=(80, 96, 112, a), width=3)
            d.ellipse([340, y + 40, 370, y + 70], fill=AMBER + (a,))
            d.text((400, y + 55), str(f_), font=font(MED, 40), fill=(236, 232, 222, a), anchor="lm")
            y += 140
    return {"layers": [(bg, 0.1)], "overlay": overlay}


def _landscape(sky_stops, ridge_col, snow_col, ground_col, extra=None):
    def build(rng, sc=None):
        sky = grad(sky_stops)
        sky = stars(sky, rng, 100, 500)
        sky = clouds(sky, rng, 10, 60, 450, tuple(min(255, c + 30) for c in sky_stops[1][1]), 80, 60)
        far = ridge(blank(), rng, 800, (220, 420), ridge_col + (255,), peaks=6, snow=(snow_col + (255,)) if snow_col else None)
        near = blank()
        ImageDraw.Draw(near).rectangle([-50, 900, LW + 50, LH], fill=ground_col + (255,))
        if extra:
            extra(near, rng)

        def overlay(img, t, u, cam, ctx):
            snow(ImageDraw.Draw(img), t, 40, 3, 30)
        return {"layers": [(sky, 0.15), (far, 0.4), (near, 0.9)], "overlay": overlay}
    return build


def _sea_extra(img, rng):
    d = ImageDraw.Draw(img)
    for i in range(6):
        y = 910 + i * 45
        d.line([(0, y), (LW, y + rng.uniform(-10, 10))], fill=(40, 70, 90, 255), width=3)


def _forest_extra(img, rng):
    d = ImageDraw.Draw(img)
    for _ in range(70):
        x, h = rng.uniform(-50, LW + 50), rng.uniform(160, 380)
        d.polygon([(x, 900 - h), (x - h * 0.22, 930), (x + h * 0.22, 930)], fill=(8, 14, 12, 255))


def _city_extra(img, rng):
    d = ImageDraw.Draw(img)
    x = -40
    while x < LW:
        w, h = rng.uniform(80, 180), rng.uniform(150, 420)
        d.rectangle([x, 920 - h, x + w, 930], fill=(14, 16, 22, 255))
        for wy in range(int(940 - h), 900, 34):
            for wx in range(int(x + 12), int(x + w - 12), 28):
                if rng.random() < 0.3:
                    d.rectangle([wx, wy, wx + 12, wy + 16], fill=(255, 200, 120, 255))
        x += w + rng.uniform(4, 20)


PARAM_SCENES = {
    "title_card": title_card, "timeline": timeline, "route": route, "facts": facts,
    "night_sea": _landscape([(0, (6, 10, 22)), (0.6, (30, 44, 66)), (1, (10, 20, 30))], (20, 28, 40), None, (16, 34, 48), _sea_extra),
    "night_mountains": _landscape([(0, (8, 12, 26)), (0.55, (40, 52, 80)), (1, (20, 26, 36))], (30, 38, 56), (170, 184, 204), (40, 46, 56)),
    "desert_night": _landscape([(0, (14, 10, 30)), (0.6, (80, 54, 70)), (1, (40, 28, 30))], (70, 48, 44), None, (96, 70, 52)),
    "forest_night": _landscape([(0, (6, 12, 14)), (0.6, (24, 44, 44)), (1, (8, 16, 14))], (14, 26, 24), None, (10, 18, 14), _forest_extra),
    "city_night": _landscape([(0, (10, 10, 24)), (0.6, (50, 40, 70)), (1, (16, 14, 24))], (24, 22, 36), None, (18, 16, 22), _city_extra),
}
