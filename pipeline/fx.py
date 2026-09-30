"""Shared helpers that make every video livelier and prove it is a true story.

- Wikimedia Commons photo resolver (license-checked at render time, credit built automatically)
- "Real photo" opener for Shorts (vertical) and documentaries (landscape)
- Shot planner: a new camera shot on every narration line (snap zooms to points of interest, drift, shake)
- Transitions (zoom-through, flash, whip-pan), floating dust, light leaks, flicker
- UI words in English or Hindi
"""
import hashlib
import json
import math
import os
import re
import time
import urllib.parse
import urllib.request

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "..", "assets", "fonts")
BOLD = os.path.join(FONTS, "Poppins-Bold.ttf")
MED = os.path.join(FONTS, "Poppins-Medium.ttf")
AMBER = (255, 184, 82)
RED = (214, 52, 44)
BONE = (240, 232, 214)
UA = {"User-Agent": "UntoldMysteriesDaily/1.0 (https://github.com/pramodhnd/untold-mysteries-daily; video renderer)"}

_FONTS = {}


def font(path, size):
    key = (path, int(size))
    if key not in _FONTS:
        _FONTS[key] = ImageFont.truetype(path, max(8, int(size)))
    return _FONTS[key]


# ---------------------------------------------------------------- language
WORDS = {
    "en": {"true": "TRUE STORY", "real": "REAL PHOTO", "chapter": "CHAPTER", "recon": "RECONSTRUCTION",
           "follow": "FOLLOW FOR DAILY MYSTERIES"},
    "hi": {"true": "सच्ची कहानी", "real": "असली तस्वीर", "chapter": "अध्याय", "recon": "पुनर्निर्माण",
           "follow": "रोज़ एक रहस्य के लिए फ़ॉलो करें"},
}


def lang_of(story):
    return "hi" if str(story.get("lang", "en")).lower().startswith("hi") else "en"


def word(lang, key):
    return WORDS.get(lang, WORDS["en"])[key]


# ---------------------------------------------------------------- Wikimedia Commons
def _allowed(short):
    s = (short or "").strip().lower()
    if not s or re.search(r"\b(nc|nd)\b|non-?commercial|no ?deriv|fair use|non-free", s):
        return False
    return s.startswith(("cc0", "cc by", "cc-by", "public domain", "pd", "no restrictions"))


def _api(params, tries=3):
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({**params, "format": "json"})
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            print(f"   commons api retry {i + 1}: {e}", flush=True)
            time.sleep(2 + 3 * i)
    return {}


def _clean(html):
    txt = re.sub(r"<[^>]+>", "", html or "")
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt[:70] or "Unknown author"


def _norm(t):
    t = t.strip().replace("_", " ")
    return t if t.lower().startswith("file:") else "File:" + t


def _infos(titles, width):
    out = {}
    for i in range(0, len(titles), 20):
        d = _api({"action": "query", "titles": "|".join(titles[i:i + 20]), "prop": "imageinfo",
                  "iiprop": "url|extmetadata|mime|size", "iiurlwidth": width})
        q = d.get("query", {})
        alias = {n["to"]: n["from"] for n in q.get("normalized", [])}
        for p in q.get("pages", {}).values():
            if "imageinfo" in p:
                out[p["title"]] = p["imageinfo"][0]
                if p["title"] in alias:
                    out[alias[p["title"]]] = p["imageinfo"][0]
    return out


def _search(term, n=15):
    d = _api({"action": "query", "list": "search", "srsearch": f"{term} filetype:bitmap", "srnamespace": 6,
              "srlimit": n})
    return [x["title"] for x in d.get("query", {}).get("search", [])]


def _category(cat, n=30):
    cat = cat if cat.lower().startswith("category:") else "Category:" + cat
    d = _api({"action": "query", "list": "categorymembers", "cmtitle": cat, "cmtype": "file", "cmlimit": n})
    return [x["title"] for x in d.get("query", {}).get("categorymembers", [])]


def _download(url, out_dir):
    os.makedirs(os.path.join(out_dir, "photos"), exist_ok=True)
    path = os.path.join(out_dir, "photos", hashlib.md5(url.encode()).hexdigest()[:12] + ".jpg")
    if os.path.exists(path):
        return path
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                data = r.read()
            with open(path, "wb") as fh:
                fh.write(data)
            Image.open(path).verify()
            return path
        except Exception as e:  # noqa: BLE001
            print(f"   photo download retry {i + 1}: {e}", flush=True)
            time.sleep(3 + 3 * i)
    return None


def resolve_photo(spec, out_dir, width=1920, min_width=900):
    """spec: {"photo_url", "credit"} or {"file": str|[str], "search": str, "category": str}.

    Returns {"path", "credit", "page"} for the first Commons file whose license is CC0 / CC BY / CC BY-SA /
    public domain, or None. The license is checked here, at render time, so a wrong guess is never used.
    """
    if not spec:
        return None
    if spec.get("photo_url"):
        p = _download(spec["photo_url"], out_dir)
        return {"path": p, "credit": spec.get("credit"), "page": spec.get("photo_url")} if p else None
    files = spec.get("file") or spec.get("files") or []
    titles = [_norm(t) for t in ([files] if isinstance(files, str) else files)]
    if spec.get("category"):
        titles += _category(spec["category"])
    if spec.get("search"):
        titles += _search(spec["search"])
    seen, order = set(), []
    for t in titles:
        if t not in seen and not t.lower().endswith((".svg", ".pdf", ".gif", ".tif", ".tiff", ".djvu", ".ogg", ".webm")):
            seen.add(t)
            order.append(t)
    if not order:
        return None
    infos = _infos(order, width)
    for t in order:
        ii = infos.get(t)
        if not ii:
            continue
        m = ii.get("extmetadata", {})
        lic = _clean(m.get("LicenseShortName", {}).get("value", ""))
        if not _allowed(lic):
            print(f"   skip {t}: license {lic!r}", flush=True)
            continue
        if ii.get("width", 0) < min_width:
            continue
        url = ii.get("thumburl") or ii.get("url")
        path = _download(url, out_dir)
        if not path:
            continue
        artist = _clean(m.get("Artist", {}).get("value", ""))
        credit = f"Photo: {artist}, {lic}, Wikimedia Commons"
        print(f"   photo: {t} ({lic})", flush=True)
        return {"path": path, "credit": credit, "page": ii.get("descriptionurl", ""), "title": t}
    print("   no usable open-license photo found", flush=True)
    return None


def record_credit(out_dir, sid, credit, page):
    if not credit:
        return
    with open(os.path.join(out_dir, f"{sid}_credits.txt"), "a") as fh:
        fh.write(f"{credit}{' - ' + page if page else ''}\n")


# ---------------------------------------------------------------- easing / noise
def smooth(u):
    u = min(1.0, max(0.0, u))
    return u * u * (3 - 2 * u)


def ease_out(u):
    u = min(1.0, max(0.0, u))
    return 1 - (1 - u) ** 3


def wobble(t, seed, amp):
    """Smooth pseudo-random 2D shake."""
    x = sum(math.sin(t * f + seed * p) / f for f, p in [(3.1, 1.3), (5.7, 2.1), (9.3, 0.7)])
    y = sum(math.sin(t * f + seed * p) / f for f, p in [(2.7, 0.9), (6.1, 1.7), (8.9, 2.9)])
    return x * amp, y * amp


# ---------------------------------------------------------------- points of interest
def focal_points(img, band=(0.0, 1.0), k=3):
    """Find up to k busy/bright spots (normalized x, y) in an image, to aim close-ups at."""
    small = img.convert("L").resize((96, int(96 * img.height / img.width)), Image.BILINEAR)
    a = np.asarray(small, np.float32)
    gy, gx = np.gradient(a)
    e = np.hypot(gx, gy) + 0.15 * a
    e = np.asarray(Image.fromarray(np.clip(e * 2, 0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(4)), np.float32)
    h, w = e.shape
    y0, y1 = int(band[0] * h), int(band[1] * h)
    mask = np.zeros_like(e)
    mask[y0:y1, int(w * 0.12):int(w * 0.88)] = 1
    e = e * mask
    pts = []
    for _ in range(k):
        if e.max() <= 1:
            break
        yy, xx = np.unravel_index(np.argmax(e), e.shape)
        pts.append(((xx + 0.5) / w, (yy + 0.5) / h))
        r = int(w * 0.18)
        e[max(0, yy - r):yy + r, max(0, xx - r):xx + r] = 0
    if not pts:
        pts = [(0.5, (band[0] + band[1]) / 2)]
    return pts


class ShotPlan:
    """A new shot on every narration line (long lines are split), with a quick snap move between shots.

    state(lt) -> (zoom, cx, cy, shake_x, shake_y); zoom 1 = the default framing, cx/cy normalized centre.
    """

    SNAP = 0.3

    def __init__(self, line_starts, dur, focal, seed, home=(0.5, 0.5), zmax=1.42, max_shot=3.6):
        cuts = sorted(set([0.0] + [max(0.0, s) for s in line_starts]))
        cuts = [c for c in cuts if c < dur - 0.5] or [0.0]
        bounds = cuts + [dur]
        starts = []
        for a, b in zip(bounds[:-1], bounds[1:]):
            n = max(1, int(math.ceil((b - a) / max_shot)))
            starts += [a + (b - a) * j / n for j in range(n)]
        self.starts = starts + [dur]
        rng = np.random.default_rng(seed)
        self.shots = []
        pattern = ["wide", "close", "medium", "close", "wide", "medium"]
        off = int(rng.integers(0, 2))
        for j in range(len(starts)):
            kind = pattern[(j + off) % len(pattern)] if j else ("wide" if seed % 2 else "medium")
            fx, fy = focal[(j + seed) % len(focal)] if kind != "wide" else home
            z = {"wide": 1.0, "medium": 1.18, "close": zmax}[kind] * float(rng.uniform(0.97, 1.03))
            zin = bool(rng.integers(0, 2)) if kind == "wide" else (j % 2 == 0)
            drift = (float(rng.uniform(-0.035, 0.035)), float(rng.uniform(-0.02, 0.02)))
            self.shots.append({"z": z, "cx": fx, "cy": fy, "zin": zin, "drift": drift})
        self.seed = seed

    def _at(self, j, v):
        s = self.shots[j]
        z = s["z"] * (1 + (0.07 * v if s["zin"] else 0.07 * (1 - v)))
        return z, s["cx"] + s["drift"][0] * v, s["cy"] + s["drift"][1] * v

    def state(self, lt):
        j = max(0, min(len(self.shots) - 1, int(np.searchsorted(self.starts, lt, side="right") - 1)))
        a, b = self.starts[j], self.starts[j + 1]
        v = smooth((lt - a) / max(0.01, b - a))
        z, cx, cy = self._at(j, v)
        age = lt - a
        if j > 0 and age < self.SNAP:  # fast eased move from where the previous shot ended
            pz, pcx, pcy = self._at(j - 1, 1.0)
            e = ease_out(age / self.SNAP)
            z, cx, cy = pz + (z - pz) * e, pcx + (cx - pcx) * e, pcy + (cy - pcy) * e
        kick = 1.0 + 2.5 * max(0.0, 1 - age / 0.35) if j > 0 else 1.0
        sx, sy = wobble(lt, self.seed + j, 2.2 * kick)
        return z, cx, cy, sx, sy


# ---------------------------------------------------------------- transitions
KINDS = ["zoom", "flash", "whip", "zoom", "fade", "whip"]


def _zoom_img(img, z):
    if abs(z - 1) < 1e-3:
        return img
    w, h = img.size
    if z > 1:
        cw, ch = w / z, h / z
        return img.crop((int((w - cw) / 2), int((h - ch) / 2), int((w + cw) / 2), int((h + ch) / 2))).resize((w, h), Image.BILINEAR)
    small = img.resize((int(w * z), int(h * z)), Image.BILINEAR)
    out = Image.new(img.mode, img.size, (0, 0, 0, 255))
    out.paste(small, ((w - small.width) // 2, (h - small.height) // 2))
    return out


def transition(kind, prev, nxt, a):
    """Blend two RGBA frames; a goes 0 -> 1."""
    a = min(1.0, max(0.0, a))
    if kind == "zoom":
        e = smooth(a)
        return Image.blend(_zoom_img(prev, 1 + 0.35 * e), _zoom_img(nxt, 1.18 - 0.18 * e), e)
    if kind == "whip":
        e = smooth(a)
        w = prev.width
        dx = int(e * w)
        frame = Image.new("RGBA", prev.size, (0, 0, 0, 255))
        frame.paste(prev, (-dx, 0))
        frame.paste(nxt, (w - dx, 0))
        if 0.08 < e < 0.92:  # motion blur during the whip
            arr = np.asarray(frame, np.float32)
            acc = arr.copy()
            for s in (12, 24, 36, 48):
                acc[:, s:] += arr[:, :-s]
                acc[:, :s] += arr[:, :s]
            frame = Image.fromarray((acc / 5).astype(np.uint8), "RGBA")
        return frame
    img = Image.blend(prev, nxt, smooth(a))
    if kind == "flash":
        f = max(0.0, 1 - abs(a - 0.5) * 2.2)
        white = Image.new("RGBA", img.size, (255, 244, 225, 255))
        img = Image.blend(img, white, 0.8 * f)
    return img


# ---------------------------------------------------------------- post effects (numpy, float32 HxWx3)
class Atmosphere:
    """Floating dust motes, a drifting warm light leak and gentle flicker, added to every frame."""

    def __init__(self, w, h, seed=3, n=46, leak=0.13):
        self.w, self.h = w, h
        rng = np.random.default_rng(seed)
        self.p = rng.uniform(0, 1, (n, 2)) * [w, h]
        self.v = np.stack([rng.uniform(-14, 14, n), rng.uniform(-38, -8, n)], 1) * (w / 1080)
        self.size = rng.integers(0, 3, n)
        self.ph = rng.uniform(0, 6.28, n)
        self.sprites = []
        for r in (4, 7, 11):
            r = int(r * w / 1080) + 2
            yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
            g = np.exp(-(xx ** 2 + yy ** 2) / (0.3 * r * r)).astype(np.float32)
            self.sprites.append(g[..., None] * np.array([255, 226, 180], np.float32)[None, None])
        # light leak field at quarter resolution, 2x wider so it can drift
        qh, qw = h // 4, w // 4
        yy, xx = np.mgrid[0:qh, 0:2 * qw].astype(np.float32)
        f = np.zeros((qh, 2 * qw), np.float32)
        for cx, cy, r in [(0.25, 0.2, 0.55), (1.2, 0.8, 0.6), (1.75, 0.3, 0.5)]:
            f += np.exp(-(((xx - cx * qw) / (r * qw)) ** 2 + ((yy - cy * qh) / (r * qh)) ** 2))
        self.leak = (f / f.max() * 255).astype(np.uint8)
        self.leak_gain = leak
        self.tint = np.array([1.0, 0.72, 0.42], np.float32)

    def apply(self, arr, t):
        h, w = self.h, self.w
        qw = w // 4
        off = int((math.sin(t * 0.13) * 0.5 + 0.5) * qw)
        leak = Image.fromarray(self.leak[:, off:off + qw]).resize((w, h), Image.BILINEAR)
        g = self.leak_gain * (0.7 + 0.3 * math.sin(t * 0.7))
        arr += np.asarray(leak, np.float32)[..., None] * (g * self.tint)
        arr *= 1.0 + 0.022 * math.sin(t * 13.7) * math.sin(t * 3.1)
        pos = self.p + self.v * t
        pos[:, 0] %= w
        pos[:, 1] %= h
        for (x, y), s, ph in zip(pos, self.size, self.ph):
            spr = self.sprites[s] * (0.25 + 0.2 * math.sin(t * 1.3 + ph))
            r = spr.shape[0] // 2
            x0, y0 = int(x) - r, int(y) - r
            x1, y1 = x0 + spr.shape[1], y0 + spr.shape[0]
            if x0 < 0 or y0 < 0 or x1 > w or y1 > h:
                continue
            arr[y0:y1, x0:x1] += spr
        return arr


# ---------------------------------------------------------------- "true story" stamp
def _stamp_img(text, size):
    f = font(BOLD, size)
    tw = f.getlength(text)
    pad = size * 0.45
    img = Image.new("RGBA", (int(tw + pad * 2 + 20), int(size * 2.1)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([6, 6, img.width - 6, img.height - 6], radius=int(size * 0.3), outline=RED + (255,),
                        width=max(4, size // 9), fill=(0, 0, 0, 110))
    d.text((img.width / 2, img.height / 2), text, font=f, fill=RED + (255,), anchor="mm")
    return img.rotate(8, resample=Image.BICUBIC, expand=True)


def paste_stamp(frame, stamp, cx, cy, age):
    """Stamp slams in (scale 2 -> 1) and settles."""
    if age < 0:
        return
    e = ease_out(age / 0.18)
    s = 2.0 - e
    a = min(1.0, age / 0.08)
    im = stamp.resize((max(1, int(stamp.width * s)), max(1, int(stamp.height * s))), Image.BILINEAR)
    if a < 1:
        im.putalpha(im.getchannel("A").point(lambda v: int(v * a)))
    frame.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


def _pill(frame, x, y, text, size, fg, bg, anchor="l"):
    f = font(BOLD, size)
    tw = f.getlength(text)
    h = size + 26
    if anchor == "c":
        x -= (tw + 44) / 2
    d = ImageDraw.Draw(frame, "RGBA")
    d.rounded_rectangle([x, y, x + tw + 44, y + h], radius=h // 2, fill=bg)
    d.text((x + 22, y + h / 2), text, font=f, fill=fg, anchor="lm")


def _grade(im):
    a = np.asarray(im.convert("RGB")).astype(np.float32)
    lum = a.mean(axis=2, keepdims=True)
    a = (lum + (a - lum) * 0.9 - 128) * 1.06 + 122
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def _cover(im, w, h):
    r = max(w / im.width, h / im.height)
    im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1), Image.LANCZOS)
    x0, y0 = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x0, y0, x0 + w, y0 + h))


class Opener:
    """The first seconds of every video: a real, open-license photo with a TRUE STORY stamp."""

    def __init__(self, path, caption, credit, w, h, lang="en", vertical=True):
        self.w, self.h, self.vertical = w, h, vertical
        self.caption, self.credit, self.lang = caption or "", credit or "", lang
        im = _grade(Image.open(path))
        self.stamp = _stamp_img(word(lang, "true"), 64 if vertical else 58)
        if vertical:
            bg = _cover(im, int(w * 1.1), int(h * 1.1)).filter(ImageFilter.GaussianBlur(28))
            self.bg = Image.eval(bg, lambda v: int(v * 0.45)).convert("RGBA")
            fw, fh = 980, 760
            r = min(fw / im.width, fh / im.height)
            ph = im.resize((int(im.width * r), int(im.height * r)), Image.LANCZOS)
            card = Image.new("RGBA", (ph.width + 24, ph.height + 24), BONE + (255,))
            card.paste(ph, (12, 12))
            shadow = Image.new("RGBA", (card.width + 80, card.height + 80), (0, 0, 0, 0))
            ImageDraw.Draw(shadow).rectangle([40, 52, 40 + card.width, 52 + card.height], fill=(0, 0, 0, 170))
            shadow = shadow.filter(ImageFilter.GaussianBlur(18))
            shadow.alpha_composite(card, (40, 40))
            self.card = shadow.rotate(-2, resample=Image.BICUBIC, expand=True)
        else:
            self.bg = _cover(im, int(w * 1.12), int(h * 1.12)).convert("RGBA")
            grad = np.zeros((h, w, 4), np.uint8)
            grad[..., 3] = (np.clip(np.linspace(-0.2, 1, h), 0, 1) ** 1.6 * 190).astype(np.uint8)[:, None]
            self.shade = Image.fromarray(grad, "RGBA")

    def frame(self, t, dur):
        w, h = self.w, self.h
        u = min(1.0, t / max(0.1, dur))
        z = 1.0 + 0.09 * smooth(u)
        bw, bh = self.bg.size
        cw, ch = bw / z, bh / z
        x0 = (bw - cw) / 2 + (u - 0.5) * (bw - cw) * 0.6
        y0 = (bh - ch) / 2
        img = self.bg.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((w, h), Image.BILINEAR)
        tr = word(self.lang, "real")
        if self.vertical:
            e = ease_out(t / 0.45)
            s = (1.22 - 0.22 * e) * (1 + 0.04 * u)
            c = self.card.resize((int(self.card.width * s), int(self.card.height * s)), Image.BILINEAR)
            if e < 1:
                c.putalpha(c.getchannel("A").point(lambda v: int(v * e)))
            cy = 770
            img.alpha_composite(c, (int(w / 2 - c.width / 2), int(cy - c.height / 2)))
            top = cy - self.card.height / 2 * s
            bot = cy + self.card.height / 2 * s
            if t > 0.25:
                _pill(img, 70, int(top + 34), tr, 34, (20, 16, 10, 255), AMBER + (235,))
            paste_stamp(img, self.stamp, w - 240, int(top + 70), t - 0.55)
            d = ImageDraw.Draw(img, "RGBA")
            if self.credit:
                d.text((w - 78, bot - 42), self.credit[:80], font=font(MED, 21), fill=(235, 235, 235, 230),
                       anchor="rs", stroke_width=2, stroke_fill=(0, 0, 0, 220))
            if self.caption and t > 0.4:
                d.text((w / 2, min(bot + 40, 1175)), self.caption, font=font(BOLD, 42), fill=BONE + (255,),
                       anchor="mm", stroke_width=4, stroke_fill=(0, 0, 0, 255))
        else:
            img.alpha_composite(self.shade)
            paste_stamp(img, self.stamp, w - 260, 130, t - 0.5)
            d = ImageDraw.Draw(img, "RGBA")
            if t > 0.3:
                _pill(img, 70, h - 400, tr, 30, (20, 16, 10, 255), AMBER + (235,))
            if self.caption and t > 0.45:
                d.text((70, h - 300), self.caption, font=font(BOLD, 62), fill=BONE + (255,), anchor="lm",
                       stroke_width=4, stroke_fill=(0, 0, 0, 220))
            if self.credit:
                d.text((w - 36, h - 230), self.credit[:110], font=font(MED, 22), fill=(225, 225, 225, 210),
                       anchor="rs", stroke_width=2, stroke_fill=(0, 0, 0, 200))
        return img


def build_opener(story, out_dir, w, h, vertical):
    """Resolve story["opener"] (or the thumbnail photo for documentaries) into an Opener, or None."""
    spec = dict(story.get("opener") or {})
    if not spec and story.get("thumbnail", {}).get("photo_url"):
        th = story["thumbnail"]
        spec = {"photo_url": th["photo_url"], "credit": th.get("credit"), "caption": th.get("caption", "")}
    if not spec:
        return None
    ph = resolve_photo(spec, out_dir)
    if not ph:
        return None
    credit = spec.get("credit") or ph["credit"]
    record_credit(out_dir, story["id"], credit, ph.get("page"))
    caps = {_norm(k): v for k, v in (spec.get("captions") or {}).items()}
    caption = caps.get(ph.get("title", ""), spec.get("caption", ""))
    return Opener(ph["path"], caption, credit, w, h, lang_of(story), vertical)
