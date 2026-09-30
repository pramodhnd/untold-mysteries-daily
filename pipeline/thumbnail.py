"""1280x720 YouTube thumbnail from a story's "thumbnail" block.

story["thumbnail"] = {"line1": "LAKE OF", "line2": "SKELETONS", "badge": "DNA: 1,000 YEARS APART",
                      "sub": "300+ bodies. Who were they?", "scene": "ranger_1942", "photo": "optional/path.jpg",
                      "credit": "Photo: Name, CC BY-SA 4.0"}
Usage: python3 pipeline/thumbnail.py <story.json> <out.jpg>
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
import scenes_long as SL  # noqa: E402

W, H = 1280, 720


def background(spec):
    photo = spec.get("photo")
    if spec.get("photo_url"):
        from render_long import fetch_photo
        photo = fetch_photo(spec["photo_url"], os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out"))
    if photo and os.path.exists(photo):
        im = Image.open(photo).convert("RGB")
        r = max(W / im.width, H / im.height)
        im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1), Image.LANCZOS)
        x0, y0 = (im.width - W) // 2, (im.height - H) // 2
        return im.crop((x0, y0, x0 + W, y0 + H)).convert("RGBA")
    name = spec.get("scene", "ranger_1942")
    if name in SL.PARAM_SCENES:  # reusable scenes (night_sea, forest_night, ...) take the spec as their fields
        scene = SL.PARAM_SCENES[name](np.random.default_rng(5), spec)
    else:
        scene = SL.SCENES.get(name, SL.ranger_1942)(np.random.default_rng(5))
    im = None
    for layer, _ in scene["layers"]:
        c = layer.crop((200, 180, 200 + 1920, 180 + 1080))
        if im is None:
            im = c.copy()
        else:
            im.alpha_composite(c)
    scene["overlay"](im, 3.0, 0.8, _Cam(), {"lines": [0, 0.5, 1, 1.5, 2], "dur": 6, "chapter_n": 1})
    return im.resize((W, H))


class _Cam:
    z = 1.0

    def map(self, x, y, d=1.0):
        return (x - 200, y - 180)

    def k(self, d=1.0):
        return 1.0


def make(story, out):
    spec = dict(story.get("thumbnail", {}))
    if not (spec.get("photo") or spec.get("photo_url")) and story.get("opener"):
        # use the video's real opener photo: a true photo on the thumbnail tells viewers this really happened
        import fx
        ph = fx.resolve_photo(story["opener"], os.path.dirname(os.path.abspath(out)) or ".")
        if ph:
            spec["photo"], spec["credit"] = ph["path"], story["opener"].get("credit") or ph["credit"]
            spec.setdefault("skull", False)
    im = background(spec)
    a = np.asarray(im).astype(np.float32)
    a[..., :3] *= np.clip(np.linspace(0.3, 1.0, W) ** 0.8, 0, 1)[None, :, None]  # darker left side for text
    im = Image.fromarray(a.astype(np.uint8), "RGBA")
    d = ImageDraw.Draw(im)
    if spec.get("skull", True):
        SL.skull(d, 1060, 430, 115)
    f1 = ImageFont.truetype(SL.BOLD, 116)
    d.text((50, 60), spec.get("line1", ""), font=f1, fill=(255, 255, 255), stroke_width=8, stroke_fill=(0, 0, 0))
    d.text((50, 180), spec.get("line2", story.get("title", "")[:14]), font=f1, fill=SL.AMBER, stroke_width=8, stroke_fill=(0, 0, 0))
    if spec.get("badge"):
        fb = ImageFont.truetype(SL.BOLD, 46)
        tw = fb.getlength(spec["badge"])
        d.rounded_rectangle([50, 350, 50 + tw + 60, 450], radius=18, fill=(200, 36, 36))
        d.text((80 + tw / 2, 400), spec["badge"], font=fb, fill=(255, 255, 255), anchor="mm")
    if spec.get("sub"):
        d.text((50, 510), spec["sub"], font=ImageFont.truetype(SL.MED, 44), fill=(235, 235, 235), stroke_width=4, stroke_fill=(0, 0, 0))
    if spec.get("credit"):
        d.text((W - 16, H - 14), spec["credit"], font=ImageFont.truetype(SL.MED, 16), fill=(230, 230, 230), anchor="rs")
    im.convert("RGB").save(out, quality=92)


if __name__ == "__main__":
    make(json.load(open(sys.argv[1])), sys.argv[2])
