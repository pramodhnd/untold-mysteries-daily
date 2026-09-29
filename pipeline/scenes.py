"""Illustrated scene library. Every scene is drawn from code: original art, no stock or AI-video costs.

Each builder returns (background RGB image in design space 1080x1920, overlay function).
overlay(img, draw, t, u, cam, ctx): draws animated parts on the camera-transformed frame.
  t = seconds into scene, u = 0..1 progress, cam.map(x, y) maps design coords to frame coords,
  ctx["lines"] = line start times relative to the scene.
"""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import os as _os


def _font_path(name, system_dir):
    here = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "assets", "fonts", name)
    return here if _os.path.exists(here) else _os.path.join(system_dir, name)



W, H = 1080, 1920
NAVY = (9, 16, 28)
DEEP = (14, 28, 44)
TEAL = (26, 60, 74)
STEEL = (58, 82, 96)
FOAM = (200, 220, 225)
AMBER = (255, 184, 82)
WARM = (255, 214, 150)
BONE = (232, 224, 204)
INK = (6, 9, 14)
RED = (196, 44, 40)
FONT_BOLD = _font_path("Poppins-Bold.ttf", "/usr/share/fonts/truetype/google-fonts")
FONT_HAND = _font_path("Lora-Italic-Variable.ttf", "/usr/share/fonts/truetype/google-fonts")


# ---------- helpers ----------
def vgrad(stops, w=W, h=H):
    ys = np.linspace(0, 1, h)
    pos = [p for p, _ in stops]
    cols = np.array([c for _, c in stops], dtype=float)
    ch = [np.interp(ys, pos, cols[:, i]) for i in range(3)]
    arr = np.stack(ch, axis=1)[:, None, :].repeat(w, axis=1)
    return Image.fromarray(arr.astype(np.uint8), "RGB")


def radial(img, cx, cy, r, color, strength=0.6):
    w, h = img.size
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / r
    m = np.clip(1 - d, 0, 1) ** 2 * strength
    a = np.asarray(img).astype(float)
    a = a * (1 - m[..., None]) + np.array(color, float) * m[..., None]
    return Image.fromarray(a.clip(0, 255).astype(np.uint8), "RGB")


def soft_layer(base, fn, radius):
    lay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    fn(ImageDraw.Draw(lay))
    lay = lay.filter(ImageFilter.GaussianBlur(radius))
    out = base.convert("RGBA")
    out.alpha_composite(lay)
    return out.convert("RGB")


def clouds(base, rng, n, y0, y1, color, alpha, radius=40):
    def fn(d):
        for _ in range(n):
            x = rng.uniform(-100, W + 100)
            y = rng.uniform(y0, y1)
            rx, ry = rng.uniform(120, 320), rng.uniform(40, 110)
            d.ellipse([x - rx, y - ry, x + rx, y + ry], fill=color + (alpha,))
    return soft_layer(base, fn, radius)


def stars(base, rng, n, ymax):
    d = ImageDraw.Draw(base)
    for _ in range(n):
        x, y = rng.uniform(0, W), rng.uniform(0, ymax)
        b = int(rng.uniform(90, 200))
        r = rng.choice([1, 1, 1.5, 2])
        d.ellipse([x - r, y - r, x + r, y + r], fill=(b, b, min(255, b + 20)))
    return base


def island(d, rng, cx, top, width, base_y, color):
    pts = [(cx - width / 2 - 80, base_y)]
    steps = 14
    for i in range(steps + 1):
        x = cx - width / 2 + width * i / steps
        edge = abs(i - steps / 2) / (steps / 2)
        y = top + (edge ** 2.2) * (base_y - top) * 0.85 + rng.uniform(-14, 14)
        pts.append((x, y))
    pts.append((cx + width / 2 + 80, base_y))
    d.polygon(pts, fill=color)


def lighthouse(d, x, base_y, h, lit=True):
    """Draw tower; return lamp centre (design coords)."""
    bw, tw = h * 0.20, h * 0.13
    top_y = base_y - h
    d.polygon([(x - bw / 2, base_y), (x + bw / 2, base_y), (x + tw / 2, top_y), (x - tw / 2, top_y)], fill=(210, 205, 195))
    for k in range(3):  # dark bands
        y0 = base_y - h * (0.25 + k * 0.27)
        y1 = y0 - h * 0.11
        f0 = (base_y - y0) / h
        f1 = (base_y - y1) / h
        w0 = bw + (tw - bw) * f0
        w1 = bw + (tw - bw) * f1
        d.polygon([(x - w0 / 2, y0), (x + w0 / 2, y0), (x + w1 / 2, y1), (x - w1 / 2, y1)], fill=(60, 64, 72))
    d.rectangle([x - tw * 0.75, top_y - 8, x + tw * 0.75, top_y + 4], fill=(40, 44, 50))
    lamp_h = h * 0.12
    glass = WARM if lit else (70, 80, 88)
    d.rectangle([x - tw * 0.45, top_y - 8 - lamp_h, x + tw * 0.45, top_y - 8], fill=glass)
    d.polygon([(x - tw * 0.6, top_y - 8 - lamp_h), (x + tw * 0.6, top_y - 8 - lamp_h), (x, top_y - 8 - lamp_h - h * 0.08)], fill=(40, 44, 50))
    return (x, top_y - 8 - lamp_h / 2)


def keeper_house(d, x, base_y, w, h, color, window=None):
    d.rectangle([x, base_y - h, x + w, base_y], fill=color)
    d.polygon([(x - 10, base_y - h), (x + w + 10, base_y - h), (x + w / 2, base_y - h - h * 0.5)], fill=color)
    if window:
        d.rectangle([x + w * 0.2, base_y - h * 0.65, x + w * 0.38, base_y - h * 0.35], fill=window)


def sea(draw, cam, t, y, amp, wl, speed, color, phase=0.0):
    pts = []
    for i in range(-2, 50):
        x = i * W / 46
        yy = y + amp * math.sin((x / wl) * 2 * math.pi + t * speed + phase) \
            + amp * 0.4 * math.sin((x / (wl * 0.37)) * 2 * math.pi - t * speed * 1.7 + phase)
        pts.append(cam.map(x, yy))
    pts += [(W + 50, H + 50), (-50, H + 50)]
    draw.polygon(pts, fill=color)


def rain(draw, t, rng_seed, n=140, color=(170, 190, 200), slant=0.28, speed=2600):
    rng = np.random.default_rng(rng_seed)
    xs = rng.uniform(-200, W + 200, n)
    ys = rng.uniform(0, H, n)
    ls = rng.uniform(30, 70, n)
    for x, y, l in zip(xs, ys, ls):
        fall = (y + speed * t) % (H + 100)
        yy = fall - 50
        xx = x - slant * fall
        draw.line([(xx, yy), (xx - slant * l, yy + l)], fill=color + (110,), width=2)


def dust(draw, t, seed, n=40, color=(255, 230, 190)):
    rng = np.random.default_rng(seed)
    for _ in range(n):
        x0, y0 = rng.uniform(0, W), rng.uniform(200, 1500)
        sp = rng.uniform(8, 25)
        x = x0 + 30 * math.sin(t * 0.4 + x0)
        y = (y0 - sp * t) % 1500 + 200
        r = rng.uniform(1.5, 3.5)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=color + (int(rng.uniform(40, 110)),))


def figure_run(draw, x, y, s, color, phase):
    """Running silhouette; (x, y) = feet level, s = height."""
    sw = math.sin(phase)
    head = (x + s * 0.06, y - s * 0.92)
    r = s * 0.075
    draw.ellipse([head[0] - r, head[1] - r, head[0] + r, head[1] + r], fill=color)
    hip = (x, y - s * 0.48)
    neck = (x + s * 0.05, y - s * 0.82)
    lw = int(s * 0.07)
    draw.line([hip, neck], fill=color, width=int(s * 0.14))
    # legs
    for k in (1, -1):
        a = sw * 0.7 * k
        knee = (hip[0] + math.sin(a) * s * 0.26, hip[1] + math.cos(a) * s * 0.24)
        foot = (knee[0] + math.sin(a - 0.6 * k * (1 if a > 0 else -1)) * s * 0.24 - s * 0.05 * k, y - max(0, k * sw) * s * 0.05)
        draw.line([hip, knee, foot], fill=color, width=lw, joint="curve")
    # arms
    for k in (1, -1):
        a = -sw * 0.8 * k
        elbow = (neck[0] + math.sin(a) * s * 0.2, neck[1] + s * 0.16)
        hand = (elbow[0] + math.sin(a + 0.8) * s * 0.16, elbow[1] + s * 0.06)
        draw.line([neck, elbow, hand], fill=color, width=int(lw * 0.8), joint="curve")


def figure_stand(draw, x, y, s, color):
    r = s * 0.08
    draw.ellipse([x - r, y - s * 0.92 - r, x + r, y - s * 0.92 + r], fill=color)
    draw.polygon([(x - s * 0.14, y - s * 0.82), (x + s * 0.14, y - s * 0.82), (x + s * 0.18, y - s * 0.35), (x - s * 0.18, y - s * 0.35)], fill=color)
    draw.rectangle([x - s * 0.12, y - s * 0.36, x - s * 0.02, y], fill=color)
    draw.rectangle([x + s * 0.02, y - s * 0.36, x + s * 0.12, y], fill=color)


def steamship(d, x, y, s, color, smoke=None):
    d.polygon([(x - s, y - s * 0.12), (x + s, y - s * 0.12), (x + s * 0.85, y + s * 0.1), (x - s * 0.9, y + s * 0.1)], fill=color)
    d.rectangle([x - s * 0.45, y - s * 0.32, x + s * 0.25, y - s * 0.12], fill=color)
    d.rectangle([x - s * 0.1, y - s * 0.62, x + s * 0.02, y - s * 0.3], fill=color)
    d.line([(x + s * 0.55, y - s * 0.12), (x + s * 0.55, y - s * 0.75)], fill=color, width=max(2, int(s * 0.025)))
    d.line([(x - s * 0.7, y - s * 0.12), (x - s * 0.7, y - s * 0.6)], fill=color, width=max(2, int(s * 0.025)))


# ---------- scenes ----------
def lighthouse_night(rng):
    bg = vgrad([(0, NAVY), (0.45, DEEP), (0.62, TEAL), (1, DEEP)])
    bg = stars(bg, rng, 120, 700)
    bg = clouds(bg, rng, 14, 150, 750, (70, 95, 110), 90, 45)
    d = ImageDraw.Draw(bg)
    island(d, rng, 560, 930, 700, 1300, (16, 22, 28))
    keeper_house(d, 640, 960, 150, 70, (22, 28, 34), window=(120, 90, 50))
    lamp = lighthouse(d, 520, 975, 330, lit=True)

    def overlay(img, draw, t, u, cam, ctx):
        lx, ly = cam.map(*lamp)
        beam = Image.new("RGBA", img.size, (0, 0, 0, 0))
        bd = ImageDraw.Draw(beam)
        ang = t * 0.9
        for wdeg, a in [(0.12, 26), (0.07, 34), (0.03, 60)]:
            for side in (0, math.pi):
                a0 = ang + side
                L = 1600
                p1 = (lx + L * math.cos(a0 - wdeg), ly + L * 0.28 * math.sin(a0 - wdeg))
                p2 = (lx + L * math.cos(a0 + wdeg), ly + L * 0.28 * math.sin(a0 + wdeg))
                bd.polygon([(lx, ly), p1, p2], fill=WARM + (a,))
        r = 34
        bd.ellipse([lx - r, ly - r, lx + r, ly + r], fill=WARM + (120,))
        img.alpha_composite(beam)
        d2 = ImageDraw.Draw(img)
        sea(d2, cam, t, 1235, 16, 360, 1.3, (18, 44, 56))
        sea(d2, cam, t, 1300, 22, 300, 1.7, (12, 30, 42), 1.0)
        rain(d2, t, 11, n=90)
    return bg, overlay


def ship_passing(rng):
    bg = vgrad([(0, NAVY), (0.5, (20, 34, 48)), (0.66, (30, 58, 70)), (1, DEEP)])
    bg = clouds(bg, rng, 16, 100, 900, (60, 80, 92), 110, 50)
    d = ImageDraw.Draw(bg)
    island(d, rng, 830, 1030, 360, 1210, (18, 24, 30))
    lighthouse(d, 820, 1060, 170, lit=False)

    def overlay(img, draw, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        sea(d2, cam, t, 1180, 12, 420, 1.0, (22, 48, 60))
        sx = -150 + u * 760
        x, y = cam.map(sx, 1175)
        steamship(d2, x, y, 150 * cam.k, (8, 12, 18))
        # ship's lamp + dark question at lighthouse
        d2.ellipse([x + 60 * cam.k - 6, y - 70 * cam.k - 6, x + 60 * cam.k + 6, y - 70 * cam.k + 6], fill=AMBER)
        # smoke puffs
        for i in range(6):
            px = x - 10 * cam.k - i * 45 * cam.k
            py = y - 95 * cam.k - i * 22 * cam.k - 8 * math.sin(t * 2 + i)
            r = (18 + i * 9) * cam.k
            d2.ellipse([px - r, py - r, px + r, py + r], fill=(40, 52, 62, max(0, 150 - i * 22)))
        sea(d2, cam, t, 1245, 18, 330, 1.5, (14, 34, 46), 0.7)
        rain(d2, t, 5, n=60)
    return bg, overlay


def relief_boat(rng):
    bg = vgrad([(0, (40, 52, 62)), (0.5, (78, 92, 100)), (0.64, (60, 80, 88)), (1, (24, 40, 50))])
    bg = clouds(bg, rng, 18, 80, 800, (110, 122, 128), 90, 50)
    d = ImageDraw.Draw(bg)
    # cliff wall on the right with landing steps
    d.polygon([(560, 1250), (600, 760), (700, 640), (1080, 600), (1080, 1300)], fill=(26, 32, 36))
    for i in range(9):
        y = 1180 - i * 52
        d.rectangle([610 + i * 16, y, 690 + i * 16, y + 12], fill=(70, 74, 72))
    lighthouse(d, 900, 650, 230, lit=False)
    keeper_house(d, 760, 660, 110, 60, (34, 40, 44))

    def overlay(img, draw, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        sea(d2, cam, t, 1215, 10, 400, 1.1, (40, 66, 76))
        bx = 120 + u * 260
        x, y = cam.map(bx, 1210)
        s = (95 + u * 40) * cam.k
        steamship(d2, x, y, s, (14, 18, 22))
        sea(d2, cam, t, 1270, 14, 300, 1.4, (26, 48, 58), 2.0)
    return bg, overlay


def interior(rng):
    bg = vgrad([(0, (26, 22, 20)), (0.7, (44, 36, 30)), (1, (20, 16, 14))])
    d = ImageDraw.Draw(bg)
    # floor
    d.rectangle([0, 1350, W, H], fill=(30, 24, 20))
    for i in range(12):
        d.line([(i * 100, 1350), (i * 100 - 200, H)], fill=(22, 18, 15), width=4)
    # door (closed)
    d.rectangle([120, 520, 470, 1350], fill=(62, 44, 32))
    for yy in (580, 960):
        d.rectangle([160, yy, 430, yy + 320], outline=(44, 30, 22), width=10)
    d.ellipse([420, 930, 446, 956], fill=(170, 140, 80))
    # clock
    cx, cy, r = 780, 520, 120
    d.ellipse([cx - r - 14, cy - r - 14, cx + r + 14, cy + r + 14], fill=(70, 48, 30))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(222, 212, 188))
    for k in range(12):
        a = k / 12 * 2 * math.pi
        d.line([(cx + math.sin(a) * r * 0.82, cy - math.cos(a) * r * 0.82), (cx + math.sin(a) * r * 0.95, cy - math.cos(a) * r * 0.95)], fill=(40, 30, 24), width=6)
    # stopped hands
    d.line([(cx, cy), (cx + math.sin(2.2) * r * 0.5, cy - math.cos(2.2) * r * 0.5)], fill=(30, 24, 20), width=10)
    d.line([(cx, cy), (cx + math.sin(5.6) * r * 0.75, cy - math.cos(5.6) * r * 0.75)], fill=(30, 24, 20), width=6)
    # bed (unmade)
    d.rectangle([560, 1060, 1080, 1360], fill=(52, 38, 28))
    blanket = [(560, 1080)]
    for i in range(13):
        x = 560 + i * 45
        blanket.append((x, 1040 + (22 if i % 2 else -10) + rng.uniform(-8, 8)))
    blanket += [(1080, 1030), (1080, 1300), (600, 1310), (570, 1200)]
    d.polygon(blanket, fill=(140, 130, 112))
    d.ellipse([900, 990, 1060, 1070], fill=(200, 192, 176))
    bg = radial(bg, 760, 700, 800, (255, 200, 140), 0.18)

    def overlay(img, draw, t, u, cam, ctx):
        dust(ImageDraw.Draw(img), t, 3)
    return bg, overlay


def coats(rng):
    bg = vgrad([(0, (22, 20, 20)), (1, (36, 30, 26))])
    d = ImageDraw.Draw(bg)
    d.rectangle([140, 560, 940, 620], fill=(70, 50, 34))
    hooks = [260, 540, 820]
    for hx in hooks:
        d.rectangle([hx - 10, 600, hx + 10, 660], fill=(150, 140, 120))
        d.arc([hx - 30, 630, hx + 10, 690], 0, 180, fill=(150, 140, 120), width=8)
    # the one coat left behind (yellow oilskin) on the middle hook
    x = 540
    coat = [(x - 40, 680), (x + 40, 680), (x + 150, 760), (x + 175, 1180), (x + 110, 1200), (x + 105, 860),
            (x + 95, 1280), (x - 95, 1280), (x - 105, 860), (x - 110, 1200), (x - 175, 1180), (x - 150, 760)]
    d.polygon(coat, fill=(214, 160, 40))
    d.line([(x, 700), (x, 1270)], fill=(160, 110, 24), width=6)
    for yy in range(760, 1250, 90):
        d.ellipse([x - 22, yy, x - 8, yy + 14], fill=(120, 84, 20))
    d.polygon([(x - 40, 680), (x, 760), (x + 40, 680)], fill=(160, 110, 24))
    # ghost outlines where two coats should be
    for hx in (260, 820):
        d.line([(hx - 60, 700), (hx - 110, 1180), (hx + 110, 1180), (hx + 60, 700)], fill=(60, 52, 46), width=4)
    bg = radial(bg, 540, 900, 700, (255, 220, 160), 0.25)

    def overlay(img, draw, t, u, cam, ctx):
        dust(ImageDraw.Draw(img), t, 9, n=30)
    return bg, overlay


def running_figure(rng):
    bg = vgrad([(0, (8, 12, 20)), (0.6, (16, 26, 36)), (1, (10, 16, 22))])
    bg = clouds(bg, rng, 12, 80, 600, (40, 56, 66), 120, 50)
    d = ImageDraw.Draw(bg)
    d.rectangle([0, 1250, W, H], fill=(14, 18, 22))
    # doorway of the house, left, warm light spilling
    d.rectangle([40, 600, 360, 1250], fill=(22, 26, 30))
    d.rectangle([110, 820, 280, 1250], fill=(255, 196, 120))
    bg = radial(bg, 200, 1200, 520, (255, 190, 110), 0.35)

    def overlay(img, draw, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        # flash of lightning early
        if 0.9 < t < 1.02:
            img.alpha_composite(Image.new("RGBA", img.size, (200, 220, 255, 70)))
        fx = 300 + u * 520
        x, y = cam.map(fx, 1250)
        figure_run(d2, x, y, 330 * cam.k, (4, 6, 10), t * 9)
        rain(d2, t, 21, n=170, speed=3000)
    return bg, overlay


def west_landing(rng):
    bg = vgrad([(0, (20, 28, 36)), (0.55, (40, 56, 64)), (1, (16, 26, 32))])
    bg = clouds(bg, rng, 14, 60, 700, (70, 86, 94), 110, 50)
    d = ImageDraw.Draw(bg)
    d.polygon([(0, 700), (380, 760), (620, 900), (760, 1260), (0, 1400)], fill=(28, 32, 34))
    d.polygon([(0, 780), (340, 830), (560, 950), (640, 1100), (0, 1200)], fill=(40, 44, 44))
    # bent iron railings along the path
    posts = [(80, 800), (190, 815), (300, 835), (410, 870), (500, 920)]
    for i, (x, y) in enumerate(posts):
        lean = [0, 8, 40, 95, 150][i]
        d.line([(x, y), (x + lean, y - 120 + lean * 0.3)], fill=(110, 110, 104), width=10)
    rail = [(80, 690), (190, 700), (330, 725), (470, 820), (560, 900)]
    d.line(rail, fill=(120, 120, 112), width=9, joint="curve")
    # smashed box: planks scattered
    for (x, y, a) in [(420, 1010, 0.4), (470, 1060, -0.7), (360, 1080, 1.2), (520, 1000, 2.2)]:
        L = 110
        d.line([(x, y), (x + L * math.cos(a), y + L * math.sin(a))], fill=(120, 86, 50), width=22)
    d.rectangle([250, 1000, 330, 1060], fill=(96, 68, 40))

    def overlay(img, draw, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        sea(d2, cam, t, 1260, 30, 280, 2.0, (30, 60, 72))
        # spray bursts against the cliff
        burst = (t % 2.2) / 2.2
        for i in range(26):
            a = -math.pi / 2 + (i - 13) * 0.08
            rr = burst * (180 + (i % 5) * 50)
            px, py = cam.map(760 + math.cos(a) * rr * 0.9, 1250 + math.sin(a) * rr)
            s = 10 + (i % 4) * 5
            d2.ellipse([px - s, py - s, px + s, py + s], fill=FOAM + (int(180 * (1 - burst)),))
        sea(d2, cam, t, 1330, 24, 240, 2.4, (18, 40, 52), 1.3)
    return bg, overlay


def giant_wave(rng):
    bg = vgrad([(0, (10, 14, 22)), (0.6, (24, 38, 48)), (1, (12, 20, 28))])
    bg = clouds(bg, rng, 10, 60, 500, (50, 64, 74), 100, 50)
    d = ImageDraw.Draw(bg)
    d.polygon([(0, 1260), (0, 1120), (260, 1100), (420, 1180), (480, 1300)], fill=(20, 24, 26))

    def overlay(img, draw, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        k = cam.k
        # three tiny keepers on the rock
        for i, fx in enumerate((120, 175, 230)):
            x, y = cam.map(fx, 1110)
            figure_stand(d2, x, y, 70 * k, (4, 6, 8))
        # the wave: rises and curls toward the rock
        rise = min(1, u * 1.3)
        base_x = 1180 - rise * 380
        crest_y = 1300 - rise * 820
        pts = []
        for i in range(0, 41):
            s = i / 40
            x = base_x - 700 * s
            y = 1300 - (1300 - crest_y) * math.sin(s * math.pi * 0.62)
            pts.append((x, y + 10 * math.sin(t * 3 + i)))
        lip = pts[-1]
        curl = [(lip[0] - 40 - 140 * rise, lip[1] + 60), (lip[0] - 80 - 160 * rise, lip[1] + 220 * rise)]
        poly = [(W + 200, 1400), (W + 200, 1300)] + [(p[0], p[1]) for p in pts] + curl + [(lip[0] + 60, lip[1] + 300), (base_x - 100, 1400)]
        d2.polygon([cam.map(*p) for p in poly], fill=(24, 62, 76))
        inner = [(p[0] + 40, p[1] + 40) for p in pts[5:]]
        if len(inner) > 2:
            d2.line([cam.map(*p) for p in inner], fill=(40, 92, 104), width=int(40 * k))
        for i, p in enumerate(pts[18:] + curl):
            fx, fy = cam.map(p[0], p[1])
            r = (14 + (i % 3) * 8) * k
            d2.ellipse([fx - r, fy - r, fx + r, fy + r], fill=FOAM + (200,))
        sea(d2, cam, t, 1330, 20, 260, 2.2, (16, 38, 48))
        rain(d2, t, 31, n=80)
    return bg, overlay


def logbook(rng):
    bg = vgrad([(0, (22, 16, 12)), (1, (40, 28, 20))])
    d = ImageDraw.Draw(bg)
    for i in range(10):
        d.line([(0, 300 + i * 150 + rng.uniform(-20, 20)), (W, 320 + i * 150)], fill=(30, 22, 16), width=3)
    # open book
    d.polygon([(90, 560), (530, 600), (530, 1330), (70, 1290)], fill=(226, 214, 184))
    d.polygon([(550, 600), (990, 560), (1010, 1290), (550, 1330)], fill=(232, 220, 190))
    d.line([(540, 600), (540, 1330)], fill=(160, 144, 116), width=8)
    font = ImageFont.truetype(FONT_HAND, 40)
    words = ["Storm", "wind", "never", "seen", "before", "sea", "rough", "Ducat", "quiet", "praying", "God", "over", "all"]
    for side, x0 in ((0, 120), (1, 590)):
        for i in range(12):
            y = 660 + i * 52
            x = x0
            while True:
                w = words[int(rng.integers(len(words)))]
                if x + font.getlength(w) > x0 + 375:
                    break
                d.text((x, y), w, font=font, fill=(60, 50, 44))
                x += font.getlength(w + " ")
    bg = radial(bg, 850, 400, 700, (255, 190, 110), 0.3)

    def overlay(img, draw, t, u, cam, ctx):
        lines = ctx["lines"]
        show = t >= (lines[2] if len(lines) > 2 else 0.6 * ctx["dur"])
        if not show:
            return
        age = t - (lines[2] if len(lines) > 2 else 0)
        sc = max(1.0, 1.6 - age * 3)
        stamp = Image.new("RGBA", (760, 220), (0, 0, 0, 0))
        sd = ImageDraw.Draw(stamp)
        sd.rounded_rectangle([8, 8, 752, 212], radius=18, fill=(246, 236, 214, 230), outline=RED + (245,), width=12)
        f = ImageFont.truetype(FONT_BOLD, 66)
        sd.text((380, 78), "ADDED DECADES", font=f, fill=RED + (235,), anchor="mm")
        sd.text((380, 152), "LATER", font=f, fill=RED + (235,), anchor="mm")
        stamp = stamp.resize((int(760 * sc * cam.k), int(220 * sc * cam.k)))
        stamp = stamp.rotate(-9, expand=True, resample=Image.BICUBIC)
        cx, cy = cam.map(540, 930)
        img.alpha_composite(stamp, (int(cx - stamp.width / 2), int(cy - stamp.height / 2)))
    return bg, overlay


def question(rng):
    bg = vgrad([(0, (8, 12, 20)), (0.55, (30, 40, 56)), (0.64, (64, 60, 70)), (1, (12, 18, 26))])
    bg = stars(bg, rng, 90, 600)
    d = ImageDraw.Draw(bg)
    island(d, rng, 540, 1170, 520, 1330, (10, 14, 18))
    lighthouse(d, 520, 1195, 190, lit=False)
    f = ImageFont.truetype(FONT_BOLD, 460)
    glow = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).text((540, 560), "?", font=f, fill=AMBER + (160,), anchor="mm")
    glow = glow.filter(ImageFilter.GaussianBlur(30))
    bgA = bg.convert("RGBA")
    bgA.alpha_composite(glow)
    ImageDraw.Draw(bgA).text((540, 560), "?", font=f, fill=(255, 214, 150, 235), anchor="mm")
    bg = bgA.convert("RGB")

    def overlay(img, draw, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        sea(d2, cam, t, 1300, 12, 380, 1.0, (18, 30, 42))
        lines = ctx["lines"]
        if len(lines) >= 3 and t >= lines[2]:
            f2 = ImageFont.truetype(FONT_BOLD, 54)
            txt = "FOLLOW FOR DAILY MYSTERIES"
            tw = f2.getlength(txt)
            x0, y0 = (W - tw) / 2 - 36, 870
            d2.rounded_rectangle([x0, y0, x0 + tw + 72, y0 + 96], radius=48, fill=(255, 184, 82, 240))
            d2.text((W / 2, y0 + 48), txt, font=f2, fill=(20, 16, 10), anchor="mm")
    return bg, overlay


SCENES = {f.__name__: f for f in [lighthouse_night, ship_passing, relief_boat, interior, coats,
                                  running_figure, west_landing, giant_wave, logbook, question]}


# ================= Roopkund scenes =================
ICE = (170, 205, 220)
SNOW = (225, 234, 240)


def mountains(d, rng, base_y, peaks, color, snow=SNOW, height=(350, 600)):
    xs = np.linspace(-100, W + 100, peaks)
    pts = [(-100, base_y)]
    tops = []
    for i, x in enumerate(xs):
        top = base_y - rng.uniform(*height)
        pts.append((x + rng.uniform(-40, 40), top))
        tops.append((pts[-1][0], top))
        if i < len(xs) - 1:
            pts.append(((x + xs[i + 1]) / 2, base_y - rng.uniform(80, 200)))
    pts.append((W + 100, base_y))
    d.polygon(pts, fill=color)
    for (x, top) in tops:
        h = rng.uniform(70, 120)
        d.polygon([(x, top), (x - h * 0.8, top + h), (x - h * 0.3, top + h * 0.8), (x, top + h * 1.1),
                   (x + h * 0.4, top + h * 0.75), (x + h * 0.8, top + h)], fill=snow)


def skull(d, x, y, s, col=(222, 214, 196), dark=(30, 30, 34)):
    d.ellipse([x - s, y - s, x + s, y + s * 0.9], fill=col)
    d.rounded_rectangle([x - s * 0.55, y + s * 0.5, x + s * 0.55, y + s * 1.2], radius=int(s * 0.2), fill=col)
    for k in (-1, 1):
        d.ellipse([x + k * s * 0.42 - s * 0.26, y - s * 0.05, x + k * s * 0.42 + s * 0.26, y + s * 0.42], fill=dark)
    d.polygon([(x, y + s * 0.45), (x - s * 0.12, y + s * 0.68), (x + s * 0.12, y + s * 0.68)], fill=dark)
    for k in range(-2, 3):
        d.line([(x + k * s * 0.18, y + s * 0.85), (x + k * s * 0.18, y + s * 1.15)], fill=dark, width=max(2, int(s * 0.05)))


def bone(d, x, y, L, a, col=(214, 206, 188), w=10):
    x2, y2 = x + L * math.cos(a), y + L * math.sin(a)
    d.line([(x, y), (x2, y2)], fill=col, width=w)
    for (px, py) in ((x, y), (x2, y2)):
        for o in (-1, 1):
            ox, oy = -math.sin(a) * w * 0.55 * o, math.cos(a) * w * 0.55 * o
            d.ellipse([px + ox - w * 0.6, py + oy - w * 0.6, px + ox + w * 0.6, py + oy + w * 0.6], fill=col)


def snowfall(draw, t, seed, n=110, speed=90):
    rng = np.random.default_rng(seed)
    for _ in range(n):
        x0, y0 = rng.uniform(0, W), rng.uniform(0, H)
        r = rng.uniform(2, 6)
        y = (y0 + speed * t * (r / 4)) % H
        x = x0 + 25 * math.sin(t * 0.8 + y0)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=(240, 245, 250, int(rng.uniform(120, 220))))


def himalaya_lake(rng):
    bg = vgrad([(0, (12, 20, 40)), (0.4, (40, 60, 92)), (0.55, (120, 130, 150)), (1, (36, 44, 56))])
    bg = stars(bg, rng, 80, 400)
    d = ImageDraw.Draw(bg)
    mountains(d, rng, 1000, 6, (46, 56, 74), height=(380, 620))
    mountains(d, rng, 1080, 7, (30, 38, 52), snow=(190, 204, 214), height=(200, 380))
    d.rectangle([0, 1060, W, H], fill=(58, 66, 74))
    d.ellipse([90, 1080, 990, 1330], fill=ICE)
    d.ellipse([160, 1110, 920, 1300], fill=(150, 190, 208))
    for _ in range(26):  # bones on the shore
        x = rng.uniform(80, 1000)
        y = rng.choice([rng.uniform(1300, 1420), rng.uniform(1050, 1100)])
        bone(d, x, y, rng.uniform(26, 50), rng.uniform(0, 3.14), w=7)
    for _ in range(6):
        skull(d, rng.uniform(120, 960), rng.uniform(1320, 1430), 16)

    def overlay(img, draw, t, u, cam, ctx):
        snowfall(ImageDraw.Draw(img), t, 4, n=80)
    return bg, overlay


def bones_close(rng):
    bg = vgrad([(0, (60, 70, 82)), (1, (30, 36, 44))])
    d = ImageDraw.Draw(bg)
    for _ in range(40):  # rocks
        x, y, r = rng.uniform(-50, W + 50), rng.uniform(500, 1600), rng.uniform(40, 120)
        g = int(rng.uniform(50, 80))
        d.ellipse([x - r, y - r * 0.7, x + r, y + r * 0.7], fill=(g, g + 6, g + 12))
    d.polygon([(0, 1250), (W, 1180), (W, H), (0, H)], fill=(150, 186, 200))
    for _ in range(18):
        bone(d, rng.uniform(100, 980), rng.uniform(700, 1150), rng.uniform(60, 140), rng.uniform(0, 3.14), w=16)
    skull(d, 380, 860, 90)
    skull(d, 720, 980, 70)
    skull(d, 560, 640, 55)
    bg = radial(bg, 540, 850, 700, (255, 240, 220), 0.18)

    def overlay(img, draw, t, u, cam, ctx):
        snowfall(ImageDraw.Draw(img), t, 8, n=60, speed=60)
    return bg, overlay


def hailstorm(rng):
    bg = vgrad([(0, (8, 10, 16)), (0.6, (26, 32, 42)), (1, (14, 18, 24))])
    bg = clouds(bg, rng, 16, 60, 700, (46, 52, 62), 140, 50)
    d = ImageDraw.Draw(bg)
    mountains(d, rng, 1150, 5, (22, 26, 34), snow=(120, 130, 140), height=(250, 450))
    d.polygon([(0, 1250), (W, 1120), (W, H), (0, H)], fill=(30, 34, 40))

    def overlay(img, draw, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        if 1.2 < t < 1.32 or 3.0 < t < 3.08:
            img.alpha_composite(Image.new("RGBA", img.size, (220, 230, 255, 80)))
        for i in range(9):  # line of pilgrims on the ridge
            fx = 80 + i * 105 + u * 60
            fy = 1245 - fx * (130 / W)
            x, y = cam.map(fx, fy)
            figure_stand(d2, x, y, 110 * cam.k, (6, 8, 10))
        rng2 = np.random.default_rng(12)
        for _ in range(120):  # hailstones
            x0, y0 = rng2.uniform(0, W + 200), rng2.uniform(0, H)
            y = (y0 + 1500 * t) % H
            x = x0 - 0.2 * y
            r = rng2.uniform(4, 9)
            d2.ellipse([x - r, y - r, x + r, y + r], fill=(230, 238, 245, 220))
    return bg, overlay


def dna_lab(rng):
    bg = vgrad([(0, (6, 14, 22)), (1, (10, 30, 40))])
    d = ImageDraw.Draw(bg)
    for i in range(7):  # lab shelf with test tubes
        x = 120 + i * 130
        d.rounded_rectangle([x, 1180, x + 40, 1400], radius=18, outline=(90, 150, 170), width=4)
        d.rounded_rectangle([x + 4, 1300, x + 36, 1396], radius=14, fill=(40, 190, 170))
    d.rectangle([60, 1400, 1020, 1420], fill=(60, 80, 90))
    bg = radial(bg, 540, 700, 600, (40, 200, 190), 0.25)

    def overlay(img, draw, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        cx = W / 2
        for i in range(22):
            y = 330 + i * 38
            ph = t * 2.2 + i * 0.45
            a = 170 * math.sin(ph)
            depth = math.cos(ph)
            x1, x2 = cx + a, cx - a
            d2.line([(x1, y), (x2, y)], fill=(120, 200, 210, 150), width=5)
            c1 = (255, 184, 82) if depth > 0 else (180, 120, 60)
            c2 = (90, 220, 200) if depth < 0 else (50, 130, 120)
            d2.ellipse([x1 - 13, y - 13, x1 + 13, y + 13], fill=c1)
            d2.ellipse([x2 - 13, y - 13, x2 + 13, y + 13], fill=c2)
    return bg, overlay


def two_groups(rng):
    bg = vgrad([(0, (10, 16, 26)), (1, (22, 30, 44))])

    def overlay(img, draw, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        lines = ctx["lines"]
        fb = ImageFont.truetype(FONT_BOLD, 50)
        fs = ImageFont.truetype(FONT_BOLD, 38)
        # timeline
        y = 1080
        d2.line([(90, y), (990, y)], fill=(160, 170, 180), width=6)
        for x, lab in ((240, "800 AD"), (840, "1800 AD")):
            d2.ellipse([x - 16, y - 16, x + 16, y + 16], fill=(230, 230, 230))
            d2.text((x, y + 60), lab, font=fb, fill=(240, 232, 214), anchor="mm")
        d2.text((540, y - 40), "1,000 YEARS APART", font=fs, fill=(150, 160, 170), anchor="mm")
        # group A: 23 figures, amber
        for k in range(23):
            gx = 110 + (k % 8) * 36
            gy = 780 + (k // 8) * 90
            figure_stand(d2, gx, gy, 70, (255, 184, 82))
        d2.text((240, 590), "23  SOUTH ASIAN", font=fs, fill=(255, 184, 82), anchor="mm")
        # group B appears with line 2
        if len(lines) > 1 and t >= lines[1]:
            a = min(1.0, (t - lines[1]) / 0.4)
            for k in range(14):
                gx = 730 + (k % 5) * 44
                gy = 780 + (k // 5) * 90
                figure_stand(d2, gx, gy, 70, (90, 200, 220, int(255 * a)))
            d2.text((840, 590), "14  GREEK & CRETAN", font=fs, fill=(90, 200, 220, int(255 * a)), anchor="mm")
    return bg, overlay


def route_map(rng):
    bg = vgrad([(0, (12, 18, 28)), (1, (20, 28, 40))])
    d = ImageDraw.Draw(bg)
    for i in range(0, W, 60):
        d.line([(i, 300), (i, 1450)], fill=(22, 32, 44), width=2)
    for j in range(300, 1450, 60):
        d.line([(0, j), (W, j)], fill=(22, 32, 44), width=2)

    def overlay(img, draw, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        fb = ImageFont.truetype(FONT_BOLD, 44)
        p0, p1 = (270, 700), (840, 1000)
        n = 60
        prog = min(1, u * 1.6)
        for i in range(int(n * prog)):
            s = i / n
            x = p0[0] + (p1[0] - p0[0]) * s
            y = p0[1] + (p1[1] - p0[1]) * s - 260 * math.sin(math.pi * s)
            if i % 2 == 0:
                d2.ellipse([x - 6, y - 6, x + 6, y + 6], fill=(240, 232, 214))
        for (px, py), lab, col in ((p0, "GREECE & CRETE", (90, 200, 220)), (p1, "HIMALAYAS", (255, 184, 82))):
            d2.ellipse([px - 22, py - 22, px + 22, py + 22], fill=col)
            d2.text((px, py + 70), lab, font=fb, fill=col, anchor="mm")
        if prog > 0.5:
            fq = ImageFont.truetype(FONT_BOLD, 150)
            d2.text((555, 400), "?", font=fq, fill=(255, 214, 150, 230), anchor="mm")
    return bg, overlay


def question_lake(rng):
    bg = vgrad([(0, (8, 12, 26)), (0.5, (40, 52, 80)), (1, (20, 26, 36))])
    bg = stars(bg, rng, 100, 600)
    d = ImageDraw.Draw(bg)
    mountains(d, rng, 1150, 6, (30, 38, 54), height=(250, 420))
    d.rectangle([0, 1140, W, H], fill=(44, 52, 60))
    d.ellipse([200, 1170, 880, 1300], fill=(140, 176, 196))
    f = ImageFont.truetype(FONT_BOLD, 400)
    glow = Image.new("RGBA", bg.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).text((540, 540), "?", font=f, fill=AMBER + (160,), anchor="mm")
    glow = glow.filter(ImageFilter.GaussianBlur(30))
    bgA = bg.convert("RGBA")
    bgA.alpha_composite(glow)
    ImageDraw.Draw(bgA).text((540, 540), "?", font=f, fill=(255, 214, 150, 235), anchor="mm")
    bg = bgA.convert("RGB")

    def overlay(img, draw, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        snowfall(d2, t, 14, n=60)
        lines = ctx["lines"]
        if lines and t >= lines[-1]:
            f2 = ImageFont.truetype(FONT_BOLD, 54)
            txt = "FOLLOW FOR DAILY MYSTERIES"
            tw = f2.getlength(txt)
            x0, y0 = (W - tw) / 2 - 36, 840
            d2.rounded_rectangle([x0, y0, x0 + tw + 72, y0 + 96], radius=48, fill=(255, 184, 82, 240))
            d2.text((W / 2, y0 + 48), txt, font=f2, fill=(20, 16, 10), anchor="mm")
    return bg, overlay


SCENES.update({f.__name__: f for f in [himalaya_lake, bones_close, hailstorm, dna_lab, two_groups, route_map, question_lake]})


# ================= shared helper =================
def follow_pill(d2, ctx, t, y0=880):
    """'Follow' call-to-action pill, shown from the last line of a closing scene (3+ lines)."""
    lines = ctx["lines"]
    if len(lines) >= 3 and t >= lines[-1]:
        f2 = ImageFont.truetype(FONT_BOLD, 54)
        txt = "FOLLOW FOR DAILY MYSTERIES"
        tw = f2.getlength(txt)
        x0 = (W - tw) / 2 - 36
        d2.rounded_rectangle([x0, y0, x0 + tw + 72, y0 + 96], radius=48, fill=(255, 184, 82, 240))
        d2.text((W / 2, y0 + 48), txt, font=f2, fill=(20, 16, 10), anchor="mm")


def stamp(img, cam, text_lines, cx=540, cy=930, t_age=1.0, rot=-9):
    sc = max(1.0, 1.6 - t_age * 3)
    st = Image.new("RGBA", (760, 110 + 80 * len(text_lines)), (0, 0, 0, 0))
    sd = ImageDraw.Draw(st)
    sd.rounded_rectangle([8, 8, 752, st.height - 8], radius=18, fill=(246, 236, 214, 230), outline=RED + (245,), width=12)
    f = ImageFont.truetype(FONT_BOLD, 66)
    for i, ln in enumerate(text_lines):
        sd.text((380, st.height / 2 + (i - (len(text_lines) - 1) / 2) * 80), ln, font=f, fill=RED + (235,), anchor="mm")
    st = st.resize((int(st.width * sc * cam.k), int(st.height * sc * cam.k)))
    st = st.rotate(rot, expand=True, resample=Image.BICUBIC)
    x, y = cam.map(cx, cy)
    img.alpha_composite(st, (int(x - st.width / 2), int(y - st.height / 2)))


# ================= Voynich manuscript =================
VELLUM = (222, 206, 168)
INKB = (78, 58, 40)


def _glyph(d, x, y, s, rng, col=INKB):
    k = int(rng.integers(6))
    w = max(2, int(s * 0.12))
    if k == 0:
        d.arc([x, y, x + s, y + s], 200, 520, fill=col, width=w)
    elif k == 1:
        d.line([(x, y + s), (x + s * 0.3, y), (x + s * 0.6, y + s), (x + s, y + s * 0.2)], fill=col, width=w)
    elif k == 2:
        d.ellipse([x, y + s * 0.3, x + s * 0.7, y + s], outline=col, width=w)
        d.line([(x + s * 0.7, y + s * 0.6), (x + s * 0.7, y - s * 0.3)], fill=col, width=w)
    elif k == 3:
        d.arc([x, y, x + s * 0.6, y + s], 90, 270, fill=col, width=w)
        d.arc([x + s * 0.4, y, x + s, y + s], 270, 450, fill=col, width=w)
    elif k == 4:
        d.line([(x, y + s), (x + s * 0.5, y), (x + s, y + s)], fill=col, width=w)
        d.line([(x + s * 0.2, y + s * 0.6), (x + s * 0.8, y + s * 0.6)], fill=col, width=w)
    else:
        d.arc([x, y + s * 0.2, x + s, y + s * 1.2], 180, 360, fill=col, width=w)
        d.line([(x + s * 0.5, y + s * 0.2), (x + s * 0.5, y + s)], fill=col, width=w)


def voynich_page(rng):
    """An illustrated page in an unknown script: strange plant, glyph lines appear one by one."""
    bg = vgrad([(0, (20, 14, 10)), (1, (34, 24, 16))])
    d = ImageDraw.Draw(bg)
    d.rounded_rectangle([110, 330, 970, 1180], radius=14, fill=VELLUM)
    for i in range(40):  # foxing spots
        x, y, r = rng.uniform(130, 950), rng.uniform(350, 1160), rng.uniform(4, 16)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(208, 188, 146))
    # the strange plant
    cx = 540
    for k in range(7):  # roots
        a = math.pi * (0.15 + 0.7 * k / 6)
        d.line([(cx, 1000), (cx + 170 * math.cos(a), 1000 + 110 * math.sin(a))], fill=(150, 104, 60), width=10)
    d.line([(cx, 1000), (cx - 10, 720), (cx + 6, 560)], fill=(70, 120, 70), width=16, joint="curve")
    for sgn, y in ((-1, 820), (1, 760), (-1, 690), (1, 640)):
        d.ellipse([cx + sgn * 20 - (190 if sgn < 0 else 0), y - 40, cx + sgn * 20 + (190 if sgn > 0 else 0), y + 40], fill=(92, 150, 86))
    d.ellipse([cx - 80, 470, cx + 90, 580], fill=(70, 110, 170))
    d.ellipse([cx - 40, 440, cx + 50, 520], fill=(170, 60, 60))
    bg = radial(bg, 540, 700, 800, (255, 200, 130), 0.18)
    grng = np.random.default_rng(7)
    rows = []
    for r in range(4):
        y = 1040 + r * 34 if r < 2 else 380 + (r - 2) * 34
        row = []
        x = 170
        while x < 900:
            s = grng.uniform(16, 24)
            row.append((x, y, s, int(grng.integers(1000))))
            x += s * 1.25 + (22 if grng.random() < 0.18 else 0)
        rows.append(row)

    def overlay(img, draw, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        n_total = sum(len(r) for r in rows)
        shown = int(n_total * min(1, t / max(1.0, ctx["dur"] * 0.8)))
        c = 0
        for row in rows:
            for (x, y, s, seed) in row:
                if c >= shown:
                    break
                px, py = cam.map(x, y)
                _glyph(d2, px, py, s * cam.k, np.random.default_rng(seed))
                c += 1
        dust(d2, t, 4, n=25)
    return bg, overlay


def cipher_dice(rng):
    """Dice and playing cards turning plain words into strange script (the 2025 Naibbe cipher idea)."""
    bg = vgrad([(0, (10, 14, 22)), (1, (26, 20, 18))])
    d = ImageDraw.Draw(bg)
    d.rectangle([0, 1120, W, H], fill=(40, 26, 18))
    bg = radial(bg, 540, 760, 700, (255, 190, 110), 0.22)

    def overlay(img, draw, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        k = cam.k
        # two tumbling dice
        for i, (dx, dy) in enumerate(((330, 560), (560, 600))):
            ang = t * (2.4 if i else 1.8) * (1 - min(1, u * 1.4))
            s = 110 * k
            x, y = cam.map(dx, dy)
            pts = [(x + s * math.cos(ang + a), y + s * math.sin(ang + a)) for a in (math.pi / 4, 3 * math.pi / 4, 5 * math.pi / 4, 7 * math.pi / 4)]
            d2.polygon(pts, fill=(238, 232, 220), outline=(120, 110, 100))
            n = (int(t * 3) + i * 2) % 6 + 1 if u < 0.7 else 5 - i
            spots = {1: [(0, 0)], 2: [(-.4, -.4), (.4, .4)], 3: [(-.4, -.4), (0, 0), (.4, .4)], 4: [(-.4, -.4), (.4, -.4), (-.4, .4), (.4, .4)],
                     5: [(-.4, -.4), (.4, -.4), (0, 0), (-.4, .4), (.4, .4)], 6: [(-.4, -.45), (.4, -.45), (-.4, 0), (.4, 0), (-.4, .45), (.4, .45)]}[n]
            for sx, sy in spots:
                rx = sx * math.cos(ang) - sy * math.sin(ang)
                ry = sx * math.sin(ang) + sy * math.cos(ang)
                px, py = x + rx * s * 0.95, y + ry * s * 0.95
                d2.ellipse([px - 11 * k, py - 11 * k, px + 11 * k, py + 11 * k], fill=(30, 26, 22))
        # fanned cards
        for j in range(3):
            a = (j - 1) * 14 - 8
            card = Image.new("RGBA", (170, 250), (0, 0, 0, 0))
            cd = ImageDraw.Draw(card)
            cd.rounded_rectangle([0, 0, 169, 249], radius=14, fill=(246, 240, 226), outline=(150, 40, 36), width=5)
            cd.text((85, 125), ["I", "V", "X"][j], font=ImageFont.truetype(FONT_BOLD, 90), fill=(150, 40, 36), anchor="mm")
            card = card.resize((int(170 * k), int(250 * k))).rotate(a, expand=True, resample=Image.BICUBIC)
            x, y = cam.map(800 + j * 40, 560 + abs(j - 1) * 20)
            img.alpha_composite(card, (int(x - card.width / 2), int(y - card.height / 2)))
        # plain word -> strange glyphs
        f = ImageFont.truetype(FONT_HAND, 64)
        x, y = cam.map(540, 850)
        d2.text((x, y), "herba", font=f, fill=(240, 232, 214), anchor="mm")
        ax, ay = cam.map(540, 930)
        d2.polygon([(ax - 22 * k, ay - 14 * k), (ax + 22 * k, ay - 14 * k), (ax, ay + 18 * k)], fill=AMBER)
        grng = np.random.default_rng(3)
        m = int(9 * min(1, u * 1.8))
        for g in range(m):
            gx, gy = cam.map(330 + g * 48, 990)
            _glyph(d2, gx, gy, 34 * k, grng, col=(255, 214, 150))
        follow_pill(d2, ctx, t, y0=1150)
    return bg, overlay


# ================= Carroll A. Deering =================
def schooner(d, x, y, s, hull=(20, 22, 26), sail=(214, 206, 186), masts=5, tilt=0.0):
    """Five-masted schooner silhouette; (x, y) = waterline centre, s = half length."""
    hp = [(x - s, y - s * 0.1), (x + s * 1.05, y - s * 0.14), (x + s * 0.9, y + s * 0.06), (x - s * 0.92, y + s * 0.06)]
    d.polygon(hp, fill=hull)
    for i in range(masts):
        mx = x - s * 0.75 + i * (1.5 * s / (masts - 1))
        top = y - s * 0.95
        d.line([(mx, y - s * 0.1), (mx + tilt * s, top)], fill=hull, width=max(2, int(s * 0.02)))
        d.polygon([(mx + 6, y - s * 0.16), (mx + tilt * s * 0.9 + 6, top + s * 0.08), (mx + s * 0.28 + tilt * s * 0.5, y - s * 0.2)], fill=sail)
    d.line([(x + s * 1.05, y - s * 0.14), (x + s * 1.45, y - s * 0.4)], fill=hull, width=max(2, int(s * 0.02)))


def schooner_aground(rng):
    """A five-masted schooner stuck on the shoals at dawn, sails set, surf breaking, nobody aboard."""
    bg = vgrad([(0, (26, 30, 44)), (0.45, (120, 96, 96)), (0.6, (180, 140, 110)), (0.66, (60, 84, 96)), (1, (16, 30, 40))])
    bg = clouds(bg, rng, 16, 250, 950, (150, 130, 130), 90, 50)
    d = ImageDraw.Draw(bg)
    schooner(d, 560, 1080, 330, tilt=0.12)
    bg = radial(bg, 700, 980, 500, (255, 200, 150), 0.25)

    def overlay(img, draw, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        sea(d2, cam, t, 1100, 14, 300, 1.4, (30, 56, 68))
        burst = (t % 1.8) / 1.8
        for i in range(30):  # surf breaking on the shoal
            px, py = cam.map(250 + i * 22, 1105 - burst * (60 + (i % 5) * 30))
            s = (8 + (i % 4) * 5) * cam.k
            d2.ellipse([px - s, py - s, px + s, py + s], fill=FOAM + (int(200 * (1 - burst)),))
        sea(d2, cam, t, 1170, 20, 260, 2.0, (18, 40, 52), 0.8)
        # a lone gull over the empty ship
        gx, gy = cam.map(200 + u * 300, 520 + 20 * math.sin(t * 3))
        d2.line([(gx - 26, gy), (gx, gy + 10 * math.sin(t * 8)), (gx + 26, gy)], fill=(20, 20, 24), width=5)
    return bg, overlay


def bottle_message(rng):
    """A message in a bottle on the beach; the note is stamped HOAX on the last line."""
    bg = vgrad([(0, (22, 30, 42)), (0.5, (60, 70, 80)), (0.6, (150, 132, 104)), (1, (120, 100, 76))])
    d = ImageDraw.Draw(bg)
    for i in range(8):
        d.line([(0, 1000 + i * 40), (W, 990 + i * 44)], fill=(132, 112, 86), width=3)
    # bottle
    d.rounded_rectangle([160, 960, 560, 1090], radius=60, fill=(60, 110, 80))
    d.rectangle([540, 995, 680, 1055], fill=(60, 110, 80))
    d.rectangle([680, 990, 720, 1060], fill=(150, 110, 70))
    d.line([(200, 985), (500, 985)], fill=(140, 190, 150), width=8)
    # the note, unrolled
    d.polygon([(420, 500), (930, 540), (900, 920), (390, 880)], fill=(236, 226, 200))
    f = ImageFont.truetype(FONT_HAND, 46)
    for i, ln in enumerate(["Deering captured", "by oil burning", "boat ...", "~~~ ~~ ~~~~"]):
        d.text((450, 560 + i * 80), ln, font=f, fill=(60, 50, 44))
    bg = radial(bg, 660, 700, 600, (255, 210, 150), 0.2)

    def overlay(img, draw, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        sea(d2, cam, t, 1180, 10, 360, 0.9, (40, 70, 84, 180))
        lines = ctx["lines"]
        if len(lines) >= 2 and t >= lines[1]:
            stamp(img, cam, ["FORGED"], cx=660, cy=710, t_age=t - lines[1])
    return bg, overlay


# ================= Tunguska =================
def taiga_blast(rng):
    """Siberian forest at dawn; a fireball streaks down and bursts in the sky with a white flash."""
    bg = vgrad([(0, (20, 26, 48)), (0.5, (90, 90, 120)), (0.68, (190, 150, 120)), (0.72, (40, 50, 44)), (1, (16, 22, 18))])
    d = ImageDraw.Draw(bg)
    for _ in range(90):
        x, h = rng.uniform(-40, W + 40), rng.uniform(120, 300)
        yb = 1150 + rng.uniform(-20, 40)
        d.polygon([(x, yb - h), (x - h * 0.2, yb), (x + h * 0.2, yb)], fill=(12, 20, 16))
    d.rectangle([0, 1170, W, H], fill=(12, 18, 14))

    def overlay(img, draw, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        k = cam.k
        fly = min(1, t / 2.2)
        bx, by = 1000 - 460 * fly, 250 + 380 * fly
        if fly < 1:
            for i in range(24):  # smoke trail
                s = i / 24
                px, py = cam.map(bx + 460 * fly * s * 0.9 + 12 * s, by - 380 * fly * s * 0.9)
                r = (10 + 30 * s) * k
                d2.ellipse([px - r, py - r, px + r, py + r], fill=(200, 190, 180, int(160 * (1 - s))))
            x, y = cam.map(bx, by)
            r = 38 * k
            glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ImageDraw.Draw(glow).ellipse([x - r * 3, y - r * 3, x + r * 3, y + r * 3], fill=(255, 190, 90, 110))
            img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(20)))
            d2.ellipse([x - r, y - r, x + r, y + r], fill=(255, 244, 210))
        else:
            age = t - 2.2
            a = max(0, 1 - age / 1.2)
            if a > 0:
                img.alpha_composite(Image.new("RGBA", img.size, (255, 246, 220, int(230 * a))))
            x, y = cam.map(540, 630)
            rr = (80 + age * 260) * k
            ring = Image.new("RGBA", img.size, (0, 0, 0, 0))
            ImageDraw.Draw(ring).ellipse([x - rr, y - rr * 0.6, x + rr, y + rr * 0.6], outline=(255, 200, 120, int(200 * max(0.15, 1 - age / 4))), width=int(16 * k))
            img.alpha_composite(ring.filter(ImageFilter.GaussianBlur(6)))
            d2.ellipse([x - 60 * k, y - 60 * k, x + 60 * k, y + 60 * k], fill=(255, 220, 160, int(255 * max(0.3, a))))
    return bg, overlay


def fallen_forest(rng):
    """Aerial view: trees flattened outward in a huge radial pattern around an empty centre - no crater."""
    bg = vgrad([(0, (34, 40, 30)), (1, (26, 32, 24))])
    d = ImageDraw.Draw(bg)
    cx, cy = 540, 760
    for _ in range(900):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(120, 620)
        x, y = cx + r * math.cos(a), cy + r * math.sin(a) * 0.95
        if not (330 < y < 1180):
            continue
        L = rng.uniform(26, 50)
        d.line([(x, y), (x + L * math.cos(a), y + L * math.sin(a))], fill=(92, 74, 52), width=5)
    for _ in range(40):  # scorched trees still standing in the middle
        a, r = rng.uniform(0, 2 * math.pi), rng.uniform(0, 100)
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        d.ellipse([x - 5, y - 5, x + 5, y + 5], fill=(24, 20, 18))
    bg = radial(bg, cx, cy, 300, (60, 50, 40), 0.4)

    def overlay(img, draw, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        k = cam.k
        x, y = cam.map(cx, cy)
        lines = ctx["lines"]
        if len(lines) > 1 and t < lines[1]:
            return
        r = (130 + 12 * math.sin(t * 3)) * k
        d2.ellipse([x - r, y - r, x + r, y + r], outline=AMBER + (220,), width=int(8 * k))
        d2.text((x, y - r - 40 * k), "NO CRATER", font=ImageFont.truetype(FONT_BOLD, int(64 * k)), fill=AMBER, anchor="mm",
                stroke_width=int(4 * k), stroke_fill=(10, 10, 10))
        follow_pill(d2, ctx, t, y0=1060)
    return bg, overlay


# ================= Antikythera =================
def gear(d, x, y, r, teeth, ang, col, w=None):
    pts = []
    for i in range(teeth * 2):
        a = ang + i * math.pi / teeth
        rr = r if i % 2 == 0 else r * 0.88
        pts.append((x + rr * math.cos(a), y + rr * math.sin(a)))
    d.polygon(pts, fill=col)
    d.ellipse([x - r * 0.68, y - r * 0.68, x + r * 0.68, y + r * 0.68], fill=tuple(max(0, c - 40) for c in col[:3]) + col[3:])
    for s in range(4):
        a = ang + s * math.pi / 2
        d.line([(x, y), (x + r * 0.66 * math.cos(a), y + r * 0.66 * math.sin(a))], fill=col, width=max(3, int(r * 0.1)))
    d.ellipse([x - r * 0.12, y - r * 0.12, x + r * 0.12, y + r * 0.12], fill=(30, 30, 30))


def sponge_divers(rng):
    """Underwater: a diver descends to an ancient wreck, amphorae and a corroded bronze lump on the seabed."""
    bg = vgrad([(0, (20, 70, 90)), (0.5, (10, 40, 60)), (1, (4, 16, 26))])
    d = ImageDraw.Draw(bg)
    d.polygon([(0, 1100), (300, 1060), (700, 1090), (W, 1050), (W, H), (0, H)], fill=(40, 46, 44))
    d.polygon([(260, 1070), (720, 1040), (800, 1100), (200, 1120)], fill=(46, 34, 26))  # wreck timbers
    for i in range(6):
        d.line([(300 + i * 80, 1080), (330 + i * 80, 960 + (i % 2) * 40)], fill=(56, 40, 30), width=14)
    for (x, y, a) in [(180, 1080, 0.5), (820, 1060, -0.4), (880, 1100, 0.2)]:  # amphorae
        amph = Image.new("RGBA", (80, 200), (0, 0, 0, 0))
        ad = ImageDraw.Draw(amph)
        ad.ellipse([10, 40, 70, 170], fill=(150, 90, 60))
        ad.rectangle([30, 10, 50, 50], fill=(150, 90, 60))
        ad.polygon([(30, 170), (50, 170), (40, 198)], fill=(150, 90, 60))
        amph = amph.rotate(math.degrees(a), expand=True)
        bg.paste(amph, (int(x - amph.width / 2), int(y - amph.height / 2)), amph)
    d = ImageDraw.Draw(bg)
    d.ellipse([500, 1000, 620, 1060], fill=(60, 96, 80))  # the green corroded lump

    def overlay(img, draw, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        k = cam.k
        # light rays
        rays = Image.new("RGBA", img.size, (0, 0, 0, 0))
        rd = ImageDraw.Draw(rays)
        for i in range(5):
            x0 = cam.map(150 + i * 200 + 40 * math.sin(t * 0.6 + i), 0)[0]
            rd.polygon([(x0, 0), (x0 + 60 * k, 0), (x0 + 240 * k, img.height), (x0 + 120 * k, img.height)], fill=(170, 220, 230, 26))
        img.alpha_composite(rays)
        # diver descending, rope above
        dy = 420 + u * 420
        x, y = cam.map(560, dy)
        d2.line([(x, 0), (x, y - 60 * k)], fill=(180, 170, 140), width=int(4 * k))
        d2.ellipse([x - 26 * k, y - 90 * k, x + 26 * k, y - 38 * k], fill=(10, 16, 20))
        d2.polygon([(x - 30 * k, y - 40 * k), (x + 30 * k, y - 40 * k), (x + 20 * k, y + 60 * k), (x - 20 * k, y + 60 * k)], fill=(10, 16, 20))
        for sgn in (-1, 1):
            d2.line([(x + sgn * 12 * k, y + 55 * k), (x + sgn * (20 + 10 * math.sin(t * 4)) * k, y + 140 * k)], fill=(10, 16, 20), width=int(18 * k))
            d2.line([(x + sgn * 26 * k, y - 30 * k), (x + sgn * 60 * k, y + 20 * k + sgn * 8 * math.sin(t * 3) * k)], fill=(10, 16, 20), width=int(14 * k))
        for i in range(8):  # bubbles
            by = (y - 100 * k) - ((t * 140 + i * 90) % 600) * k
            bx = x + 14 * k * math.sin(t * 3 + i)
            r = (4 + i % 3 * 3) * k
            d2.ellipse([bx - r, by - r, bx + r, by + r], outline=(200, 230, 240, 170), width=2)
    return bg, overlay


def gear_mechanism(rng):
    """Bronze gears turning inside a shoebox-sized case, with a dial for Sun, Moon and eclipses."""
    bg = vgrad([(0, (12, 16, 22)), (1, (24, 22, 20))])
    d = ImageDraw.Draw(bg)
    d.rounded_rectangle([150, 380, 930, 1140], radius=24, fill=(52, 40, 28), outline=(90, 70, 44), width=10)
    bg = radial(bg, 540, 760, 600, (255, 190, 110), 0.2)

    def overlay(img, draw, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        k = cam.k
        specs = [(430, 700, 190, 44, 0.25, (176, 132, 70)), (690, 560, 110, 26, -0.42, (150, 120, 70)),
                 (720, 870, 130, 30, -0.36, (190, 146, 80)), (330, 990, 90, 20, 0.52, (140, 110, 64)),
                 (560, 1010, 70, 16, -0.66, (170, 130, 76))]
        for (x, y, r, n, w, col) in specs:
            px, py = cam.map(x, y)
            gear(d2, px, py, r * k, n, t * w, col + (255,))
        # front pointer with Sun & Moon
        px, py = cam.map(430, 700)
        a = t * 0.5 - math.pi / 2
        d2.line([(px, py), (px + 170 * k * math.cos(a), py + 170 * k * math.sin(a))], fill=(240, 220, 170), width=int(6 * k))
        d2.ellipse([px + 170 * k * math.cos(a) - 18 * k, py + 170 * k * math.sin(a) - 18 * k,
                    px + 170 * k * math.cos(a) + 18 * k, py + 170 * k * math.sin(a) + 18 * k], fill=AMBER)
        b = t * 1.3
        mx, my = px + 110 * k * math.cos(b), py + 110 * k * math.sin(b)
        d2.ellipse([mx - 14 * k, my - 14 * k, mx + 14 * k, my + 14 * k], fill=(220, 226, 236))
        d2.ellipse([mx - 6 * k, my - 14 * k, mx + 16 * k, my + 14 * k], fill=(30, 30, 36))
        follow_pill(d2, ctx, t, y0=1170)
    return bg, overlay


SCENES.update({f.__name__: f for f in [voynich_page, cipher_dice, schooner_aground, bottle_message,
                                       taiga_blast, fallen_forest, sponge_divers, gear_mechanism]})


# ================= Wow! signal =================
def big_ear(rng):
    """A flat field radio telescope under a starry Ohio sky; a faint beam pulses while stars drift past."""
    bg = vgrad([(0, (6, 10, 22)), (0.55, (20, 30, 52)), (0.66, (44, 50, 66)), (0.7, (18, 24, 22)), (1, (10, 14, 14))])
    bg = stars(bg, rng, 160, 1000)
    d = ImageDraw.Draw(bg)
    # tilting flat reflector (back) and parabolic wall (front), seen from the side
    d.polygon([(90, 1080), (360, 700), (400, 720), (150, 1100)], fill=(70, 82, 96))
    for i in range(7):
        y = 740 + i * 52
        d.line([(360 - i * 38, y - 30), (395 - i * 36, y - 12)], fill=(40, 48, 58), width=4)
    d.polygon([(700, 1110), (1000, 720), (1040, 740), (760, 1130)], fill=(86, 98, 112))
    d.rectangle([140, 1110, 1000, 1150], fill=(120, 126, 132))  # aluminium ground plane
    d.rectangle([0, 1150, W, H], fill=(12, 16, 14))
    # feed horns in the middle
    d.rectangle([500, 1000, 560, 1110], fill=(40, 44, 50))
    d.polygon([(480, 1000), (580, 1000), (560, 960), (500, 960)], fill=(60, 66, 74))
    bg = radial(bg, 530, 980, 260, (255, 184, 82), 0.18)

    def overlay(img, draw, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        k = cam.k
        for i in range(30):  # drifting stars (Earth turning)
            x = (i * 137 + t * 40) % 1080
            y = 380 + (i * 71) % 520
            px, py = cam.map(x, y)
            d2.ellipse([px - 3 * k, py - 3 * k, px + 3 * k, py + 3 * k], fill=(230, 236, 255, 200))
        # incoming signal: rings travelling down to the feed
        x, y = cam.map(530, 960)
        for j in range(3):
            ph = (t * 0.6 + j / 3) % 1
            r = (60 + 420 * (1 - ph)) * k
            d2.arc([x - r, y - r * 1.1, x + r, y + r * 0.2], 200, 340, fill=AMBER + (int(230 * ph),), width=int(6 * k))
        follow_pill(d2, ctx, t, y0=1180)
    return bg, overlay


def wow_printout(rng):
    """1977 computer printout of columns of characters; one column 6EQUJ5 gets circled in red and 'Wow!' is written."""
    bg = vgrad([(0, (20, 18, 16)), (1, (34, 30, 26))])
    d = ImageDraw.Draw(bg)
    d.rectangle([150, 360, 930, 1160], fill=(236, 232, 214))
    for y in range(380, 1160, 60):  # tractor holes & green bars
        d.ellipse([162, y, 180, y + 18], fill=(40, 36, 32))
        d.ellipse([900, y, 918, y + 18], fill=(40, 36, 32))
    for y in range(360, 1160, 120):
        d.rectangle([190, y, 890, y + 60], fill=(214, 230, 206))
    f = ImageFont.truetype(FONT_BOLD, 44)
    cols = [200, 290, 380, 470, 560, 650, 740, 820]
    wow = "6EQUJ5"
    for r in range(12):
        y = 390 + r * 62
        for ci, x in enumerate(cols):
            if ci == 4 and 3 <= r < 9:
                ch = wow[r - 3]
            else:
                ch = str(int(rng.integers(0, 4))) if rng.random() < 0.6 else " "
            d.text((x + 20, y), ch, font=f, fill=(50, 50, 56))
    bg = radial(bg, 540, 760, 700, (255, 220, 170), 0.15)

    def overlay(img, draw, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        k = cam.k
        lines = ctx["lines"]
        t1 = lines[1] if len(lines) > 1 else 1.5
        if t < t1 * 0.6:
            return
        p = min(1, (t - t1 * 0.6) / 0.8)
        x0, y0 = cam.map(560, 560)
        x1, y1 = cam.map(640, 960)
        d2.arc([x0, y0, x1, y1], -90, -90 + 360 * p, fill=RED + (240,), width=int(9 * k))
        if t >= t1:
            fh = ImageFont.truetype(FONT_HAND, int(96 * k))
            x, y = cam.map(770, 700)
            d2.text((x, y), "Wow!", font=fh, fill=RED + (240,), anchor="mm")
        follow_pill(d2, ctx, t, y0=1040)
    return bg, overlay


# ================= Jatinga =================
def jatinga_fog(rng):
    """A hill village on a foggy moonless night; lanterns glow and dazed birds fly down toward the lights."""
    bg = vgrad([(0, (8, 12, 18)), (0.5, (30, 40, 44)), (0.75, (46, 56, 56)), (1, (14, 18, 16))])
    d = ImageDraw.Draw(bg)
    for layer, (col, base) in enumerate([((22, 30, 30), 900), ((16, 22, 22), 1020)]):
        pts = [(0, H)]
        for x in range(0, W + 60, 60):
            pts.append((x, base - 120 * math.sin(x / 260 + layer) - 50 * math.sin(x / 90)))
        pts.append((W, H))
        d.polygon(pts, fill=col)
    for x in (120, 420, 760):  # bamboo huts
        d.polygon([(x, 1080), (x + 90, 1010), (x + 180, 1080)], fill=(10, 14, 12))
        d.rectangle([x + 20, 1080, x + 160, 1150], fill=(12, 16, 14))
        d.rectangle([x + 70, 1100, x + 100, 1140], fill=(255, 190, 100))
    d.rectangle([0, 1150, W, H], fill=(10, 12, 10))
    lamps = [(300, 980), (600, 940), (920, 990)]
    for (x, y) in lamps:
        d.line([(x, y), (x, 1150)], fill=(30, 26, 20), width=8)
        bg = radial(bg, x, y, 200, (255, 190, 100), 0.45)

    def overlay(img, draw, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        k = cam.k
        for (x, y) in lamps:
            px, py = cam.map(x, y)
            r = (16 + 2 * math.sin(t * 9 + x)) * k
            d2.ellipse([px - r, py - r, px + r, py + r], fill=(255, 226, 160, 255))
        fog = Image.new("RGBA", img.size, (0, 0, 0, 0))
        fd = ImageDraw.Draw(fog)
        for i in range(6):
            x = ((i * 300 + t * 30) % 1500) - 300
            px, py = cam.map(x, 700 + i * 70)
            fd.ellipse([px - 260 * k, py - 50 * k, px + 260 * k, py + 50 * k], fill=(170, 184, 184, 40))
        img.alpha_composite(fog.filter(ImageFilter.GaussianBlur(28)))
        for i in range(9):  # birds spiralling toward the lamps
            lx, ly = lamps[i % 3]
            ph = ((t * 0.25 + i * 0.11) % 1)
            a = i * 1.7 + ph * 5
            rr = 420 * (1 - ph) + 30
            bx, by = lx + rr * math.cos(a), ly - 40 + rr * 0.6 * math.sin(a)
            px, py = cam.map(bx, by)
            s = 30 * k
            fl = math.sin(t * 14 + i) * s * 0.6
            d2.line([(px - s, py - fl), (px, py), (px + s, py - fl)], fill=(20, 22, 22, 255), width=int(5 * k))
        follow_pill(d2, ctx, t, y0=1180)
    return bg, overlay


# ================= Nazca =================
SAND = (176, 138, 98)


def _hummingbird(scale=1.0, cx=540, cy=760):
    pts = [(0, -380), (8, -210), (40, -180), (40, -120), (60, -90), (300, -200), (280, -160), (310, -150), (270, -110),
           (300, -90), (240, -60), (60, -20), (50, 80), (90, 260), (40, 200), (0, 300), (-40, 200), (-90, 260), (-50, 80),
           (-60, -20), (-240, -60), (-300, -90), (-270, -110), (-310, -150), (-280, -160), (-300, -200), (-60, -90),
           (-40, -120), (-40, -180), (-8, -210), (0, -380)]
    return [(cx + x * scale, cy + y * scale) for x, y in pts]


def nazca_desert(rng):
    """Aerial view of the reddish Nazca desert; a giant bird figure is traced line by line in amber."""
    bg = vgrad([(0, (150, 112, 80)), (1, (120, 88, 62))])
    d = ImageDraw.Draw(bg)
    for _ in range(1600):
        x, y = rng.uniform(0, W), rng.uniform(0, H)
        c = int(rng.uniform(-18, 18))
        d.point((x, y), fill=(SAND[0] + c, SAND[1] + c, SAND[2] + c))
    for _ in range(5):  # long straight lines crossing the plain
        x0, y0 = rng.uniform(0, W), rng.uniform(300, 500)
        a = rng.uniform(0.9, 2.2)
        d.line([(x0, y0), (x0 + 1400 * math.cos(a), y0 + 1400 * math.sin(a))], fill=(206, 176, 136), width=6)
    pts = _hummingbird(1.0, cy=800)
    d.line(pts, fill=(200, 168, 128), width=10)
    bg = radial(bg, 540, 760, 700, (40, 26, 18), 0.25)

    def overlay(img, draw, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        k = cam.k
        p = min(1, t / 3.5)
        n = len(pts) - 1
        seg = p * n
        drawn = [cam.map(*pts[0])]
        for i in range(1, n + 1):
            if i <= seg:
                drawn.append(cam.map(*pts[i]))
            else:
                f = seg - (i - 1)
                if f > 0:
                    x0, y0 = pts[i - 1]
                    x1, y1 = pts[i]
                    drawn.append(cam.map(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f))
                break
        if len(drawn) > 1:
            d2.line(drawn, fill=AMBER + (240,), width=int(9 * k), joint="curve")
        # a tiny plane shadow crossing, for scale
        x, y = cam.map(-100 + (t * 90) % 1300, 420)
        d2.polygon([(x, y), (x - 40 * k, y - 8 * k), (x - 40 * k, y + 8 * k)], fill=(40, 30, 24, 160))
        d2.line([(x - 20 * k, y - 30 * k), (x - 20 * k, y + 30 * k)], fill=(40, 30, 24, 160), width=int(8 * k))
        follow_pill(d2, ctx, t, y0=1180)
    return bg, overlay


def ai_scan(rng):
    """A grid of satellite tiles of desert; a scanner sweeps across and flags faint hidden figures; a counter climbs to 303."""
    bg = vgrad([(0, (10, 12, 16)), (1, (18, 20, 24))])
    d = ImageDraw.Draw(bg)
    tiles = []
    for r in range(5):
        for c in range(4):
            x0, y0 = 120 + c * 215, 380 + r * 150
            col = (130 + int(rng.uniform(-14, 14)), 100 + int(rng.uniform(-10, 10)), 72)
            d.rectangle([x0, y0, x0 + 200, y0 + 136], fill=col)
            for _ in range(60):
                px, py = x0 + rng.uniform(0, 200), y0 + rng.uniform(0, 136)
                d.point((px, py), fill=(170, 140, 104))
            if rng.random() < 0.4:
                cx, cy = x0 + 100, y0 + 68
                s = rng.uniform(22, 36)
                d.ellipse([cx - s, cy - s * 0.7, cx + s, cy + s * 0.7], outline=(158, 126, 92), width=3)
                d.line([(cx - s, cy), (cx - s - 18, cy + 20)], fill=(158, 126, 92), width=3)
                tiles.append((x0, y0))
    fb = ImageFont.truetype(FONT_BOLD, 40)
    d.text((540, 1150), "SATELLITE + AI SURVEY", font=fb, fill=(140, 150, 160), anchor="mm")

    def overlay(img, draw, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        k = cam.k
        sx = 120 + (t * 260) % 860
        x0, y0 = cam.map(sx, 370)
        x1, y1 = cam.map(sx, 1130)
        d2.line([(x0, y0), (x1, y1)], fill=(120, 220, 255, 200), width=int(6 * k))
        for (tx, ty) in tiles:
            if t * 260 >= tx - 120:
                a, b = cam.map(tx + 4, ty + 4)
                c, e = cam.map(tx + 196, ty + 132)
                d2.rectangle([a, b, c, e], outline=AMBER + (240,), width=int(6 * k))
        lines = ctx["lines"]
        n = int(min(303, 303 * min(1, t / max(1.0, (lines[1] if len(lines) > 1 else 3.0)))))
        x, y = cam.map(540, 300)
        d2.text((x, y), f"{n} NEW", font=ImageFont.truetype(FONT_BOLD, int(96 * k)), fill=AMBER, anchor="mm",
                stroke_width=int(5 * k), stroke_fill=(10, 10, 10))
    return bg, overlay


# ================= Baghdad Battery =================
def _jar(d, cx, top, s=1.0, clay=(150, 96, 60)):
    d.ellipse([cx - 150 * s, top + 60 * s, cx + 150 * s, top + 460 * s], fill=clay)
    d.rectangle([cx - 80 * s, top, cx + 80 * s, top + 120 * s], fill=clay)
    d.ellipse([cx - 90 * s, top - 20 * s, cx + 90 * s, top + 20 * s], fill=tuple(int(c * 0.8) for c in clay))


def clay_jar(rng):
    """Museum cutaway of a small clay jar: a copper tube inside, an iron rod in the middle, sealed with black bitumen."""
    bg = vgrad([(0, (14, 14, 18)), (1, (26, 22, 20))])
    d = ImageDraw.Draw(bg)
    d.rectangle([220, 1060, 860, 1110], fill=(60, 50, 40))  # museum plinth
    _jar(d, 540, 520, 1.1)
    # cutaway window
    d.rounded_rectangle([440, 560, 640, 1010], radius=30, fill=(40, 26, 20))
    d.rectangle([470, 640, 610, 960], fill=(184, 110, 60))  # copper tube
    d.rectangle([490, 660, 590, 950], fill=(90, 54, 34))
    d.rectangle([530, 560, 550, 930], fill=(120, 124, 130))  # iron rod
    d.rectangle([462, 600, 618, 650], fill=(18, 16, 14))  # bitumen plug
    fb = ImageFont.truetype(FONT_BOLD, 34)
    for (tx, ty, txt, x2, y2) in [(820, 520, "IRON ROD", 548, 600), (840, 800, "COPPER TUBE", 610, 800),
                                   (250, 560, "BITUMEN", 470, 625)]:
        d.line([(tx, ty + 20), (x2, y2)], fill=(200, 190, 170), width=3)
        d.text((tx, ty), txt, font=fb, fill=(230, 220, 200), anchor="mm")
    bg = radial(bg, 540, 760, 520, (255, 200, 140), 0.22)

    def overlay(img, draw, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        k = cam.k
        lines = ctx["lines"]
        if len(lines) > 1 and t >= lines[1]:  # the 'battery' idea: a flickering spark
            x, y = cam.map(540, 540)
            if int(t * 8) % 3:
                pts = [(x, y)]
                for i in range(5):
                    pts.append((x + (18 if i % 2 else -18) * k, y - (i + 1) * 22 * k))
                d2.line(pts, fill=(170, 220, 255, 240), width=int(6 * k))
        follow_pill(d2, ctx, t, y0=1150)
    return bg, overlay


def scroll_jar(rng):
    """Lamp-lit shelf: a rolled scroll rises out of the clay jar, hinting at a far older, simpler use."""
    bg = vgrad([(0, (18, 14, 12)), (1, (36, 26, 18))])
    d = ImageDraw.Draw(bg)
    d.rectangle([80, 1060, 1000, 1100], fill=(70, 46, 28))
    _jar(d, 380, 620, 0.9)
    _jar(d, 760, 700, 0.7, clay=(130, 84, 52))
    bg = radial(bg, 540, 700, 560, (255, 190, 110), 0.3)

    def overlay(img, draw, t, u, cam, ctx):
        d2 = ImageDraw.Draw(img)
        k = cam.k
        rise = min(1, t / 2.5)
        top = 600 - 220 * rise
        a, b = cam.map(345, top)
        c, e = cam.map(415, top + 260)
        d2.rounded_rectangle([a, b, c, e], radius=int(30 * k), fill=(232, 216, 176, 255))
        for i in range(4):
            y = cam.map(0, top + 40 + i * 50)[1]
            d2.line([(a + 10 * k, y), (c - 10 * k, y)], fill=(120, 96, 70, 255), width=int(4 * k))
        x, y = cam.map(380, top - 10)
        d2.ellipse([x - 36 * k, y - 16 * k, x + 36 * k, y + 16 * k], fill=(210, 190, 150, 255))
        lines = ctx["lines"]
        if len(lines) >= 2 and t >= lines[-2]:
            stamp(img, cam, ["NO WIRES FOUND"], cx=560, cy=990, t_age=t - lines[-2])
        follow_pill(d2, ctx, t, y0=1150)
    return bg, overlay


SCENES.update({f.__name__: f for f in [big_ear, wow_printout, jatinga_fog, nazca_desert, ai_scan, clay_jar, scroll_jar]})
