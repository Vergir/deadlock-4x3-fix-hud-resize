"""Builds the GameBanana / README images in docs/pics/gamebanana/ from the raw screenshots in docs/pics/
(shot list: docs/SHOTLIST.md, kept locally). File names are numbered in gallery order; 01_main.jpg is the
main image / tile; header.jpg (also copied to docs/images/) is the README header.

Needs Pillow, numpy and OpenCV (pip install pillow numpy opencv-python-headless).
Usage: python docs/make_images.py [--thumbs]
Raw screenshots (git-ignored) are snips of the game window on a 2878x2559 (9:8) monitor; FRAMES holds the game frame
inside each snip. Style follows the author's page rules: captions on dark pills and one rounded gold box are the only
highlighting; the main image is 16:9 with the mod name as the biggest text; labels read Vanilla / With mod.
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "pics")
OUT = os.path.join(RAW, "gamebanana")
FONT = "C:/Windows/Fonts/segoeuib.ttf"
W, H = 1920, 1080
TITLE = "4:3 / 5:4 Fix & HUD Resize"

# The game frame inside each snip (left, top, right, bottom), found from the window edges.
FRAMES = {
    "v_43_hud": (0, 44, 2878, 2204), "m_43_hud": (0, 56, 2878, 2216),
    "v_43_shop": (0, 41, 2878, 2201), "m_43_shop": (0, 53, 2878, 2213),
    "v_54_hud": (0, 29, 2878, 2333), "m_54_hud": (0, 50, 2878, 2354),
    "v_98_hud": (0, 0, 2878, 2559), "m_98_hud": (0, 0, 2878, 2559),
    "v_98_menu": (0, 0, 2878, 2559), "m_98_menu": (0, 0, 2878, 2559),
    "v_169_hud": (0, 41, 2878, 1661), "m_169_hud": (0, 89, 2878, 1709),
    "s07_169_hud": (0, 51, 2878, 1671), "s13_169_hud": (0, 51, 2878, 1671),
}
# 1.1.0 shots (5:4): the 2880x2304 game frame, top edge found from the Steam window around it
for _k, _t in {"v_54_shop": 40, "v_54_catalog": 40, "v_54_roster": 34, "v_54_graphs": 47, "v_54_profile": 50,
               "v_54_hud": 34, "m_54_shop": 44, "m_54_catalog": 49, "m_54_roster": 43, "m_54_graphs": 37,
               "m_54_profile": 43, "m_54_hud": 46, "m_54_dialogue": 37, "v_54_dialogue": 44,
               "v_54_editbuild": 49, "m_54_editbuild": 70, "v_54_watch": 37, "m_54_watch": 26,
               "v_54_scoreboard": 59, "m_54_scoreboard": 24}.items():
    FRAMES[_k] = (0, _t, 2878, _t + 2304)

# Areas blurred before cropping (raw snip pixels): the author's friend code on the player page.
BLUR = {"v_54_profile": [(640, 300, 768, 338)], "m_54_profile": [(464, 214, 558, 246)]}

_cache = {}


def hide_fps(im):
    """Paint out the game's FPS counter in the bottom-right corner (bright text pixels, inpainted)."""
    a = np.asarray(im).copy()
    h, w = a.shape[:2]
    l, t, r, b = w - 420, h - 75, w - 5, h - 5
    reg = a[t:b, l:r].astype(int)
    g = reg.mean(axis=2)
    m = (g > 120) | ((reg[:, :, 0] - reg[:, :, 1]) > 50)
    mask = np.zeros((h, w), np.uint8)
    mask[t:b, l:r] = m.astype(np.uint8) * 255
    mask = cv2.dilate(mask, np.ones((7, 7), np.uint8))
    return Image.fromarray(cv2.inpaint(a[:, :, ::-1], mask, 7, cv2.INPAINT_TELEA)[:, :, ::-1])


def shot(key):
    if key not in _cache:
        im = Image.open(os.path.join(RAW, key + ".png")).convert("RGB")
        for b in BLUR.get(key, ()):
            im.paste(im.crop(b).filter(ImageFilter.GaussianBlur(9)), b[:2])
        im = im.crop(FRAMES[key])
        _cache[key] = hide_fps(im)
    return _cache[key]


def font(size):
    return ImageFont.truetype(FONT, size)


HILITE = (255, 64, 170)   # hot pink: a colour the HUD does not use, so a highlight never reads as part of the game


def box(img, b, k=1.0):
    """The highlight: a rounded pink outline, 10 px wide at a 1080 px tall image (k = image height / 1080), on a dark
    outline so it reads on light and dark backgrounds alike."""
    w = max(5, round(10 * k))
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle(b, round(16 * k), outline=(0, 0, 0, 170), width=w + 6)
    d.rounded_rectangle(tuple(v + o for v, o in zip(b, (3, 3, -3, -3))), round(16 * k), outline=HILITE, width=w)


def ring(img, b, k=1.0):
    """The same highlight as an ellipse (b is its bounding box), for round things like the minimap."""
    w = max(5, round(10 * k))
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse(b, outline=(0, 0, 0, 170), width=w + 6)
    d.ellipse(tuple(v + o for v, o in zip(b, (3, 3, -3, -3))), outline=HILITE, width=w)


def label(img, text, xy, size, anchor="la"):
    """White text on a dark pill."""
    d = ImageDraw.Draw(img, "RGBA")
    f = font(size)
    l, t, r, b = d.textbbox(xy, text, font=f, anchor=anchor)
    p = size // 4
    d.rounded_rectangle((l - p, t - p, r + p, b + p), p, fill=(0, 0, 0, 190))
    d.text(xy, text, font=f, fill="white", anchor=anchor)


def outlined(img, text, xy, size, anchor="mm"):
    """The title: white with a dark outline and a soft shadow, straight on the scene."""
    f = font(size)
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).text((xy[0] + 6, xy[1] + 8), text, font=f, fill=(0, 0, 0, 200), anchor=anchor)
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10)))
    ImageDraw.Draw(img).text(xy, text, font=f, fill="white", anchor=anchor, stroke_width=4, stroke_fill=(20, 20, 20))


def shadowed_paste(dst, src, xy, edge=False):
    x, y = xy
    sh = Image.new("RGBA", dst.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle((x + 6, y + 10, x + src.width + 6, y + src.height + 10), fill=(0, 0, 0, 210))
    dst.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    dst.paste(src, (x, y))
    if edge:   # a thin light frame so the shot's border reads against a dark background
        ImageDraw.Draw(dst, "RGBA").rectangle((x - 1, y - 1, x + src.width, y + src.height),
                                              outline=(255, 255, 255, 70), width=2)


def neutral_backdrop(w=W, h=H):
    """A plain dark backdrop: charcoal, a little lighter at the top, soft vignette and fine grain."""
    y = np.linspace(0, 1, h)[:, None, None]
    x = np.linspace(-1, 1, w)[None, :, None]
    base = np.array([38, 41, 47]) * (1 - y) + np.array([15, 16, 19]) * y
    r = np.sqrt(x ** 2 + ((y - 0.45) * 1.7) ** 2)
    base = base * (1 - 0.35 * np.clip(r - 0.35, 0, 1))
    base = base + np.random.default_rng(1).normal(0, 2.0, (h, w, 1))
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8)).convert("RGBA")


STYLE = "neutral"   # "blur": a blurred copy of the shot behind the pair; "neutral": the plain dark backdrop


def backdrop(key, dim=0.7, blur=10):
    """A blurred, dimmed copy of a shot filling the 16:9 frame (cover crop), so composites have no black bars."""
    im = shot(key)
    s = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 2
    im = im.crop((x, y, x + W, y + H)).filter(ImageFilter.GaussianBlur(blur))
    return ImageEnhance.Brightness(im).enhance(dim).convert("RGBA")


def save(img, name):
    os.makedirs(OUT, exist_ok=True)
    img.convert("RGB").save(os.path.join(OUT, name), quality=92)
    print(f"{name:22} {img.width}x{img.height} {os.path.getsize(os.path.join(OUT, name)) // 1024:5} KB")


def pair(keys, labels, out, title, crop=None, boxes=(), top=150, gap=40, margin=40, bright=1.0, marks=((), ())):
    """Two shots side by side on a backdrop (STYLE), labelled; crop, boxes (on both panels) and marks (per panel:
    ("box" | "ring", bounds)) are in raw frame pixels."""
    neutral = STYLE == "neutral"
    img = neutral_backdrop() if neutral else backdrop(keys[1])
    ims = [shot(k).crop(crop) if crop else shot(k) for k in keys]
    s = min((W - 2 * margin - gap) / (2 * ims[0].width), (H - top - margin) / ims[0].height)
    pw, ph = round(ims[0].width * s), round(ims[0].height * s)
    x = (W - 2 * pw - gap) // 2
    y = top + (H - top - margin - ph) // 2
    ox, oy = (crop[0], crop[1]) if crop else (0, 0)
    for im, lbl, own in zip(ims, labels, marks):
        p = ImageEnhance.Brightness(im.resize((pw, ph), Image.LANCZOS)).enhance(bright).convert("RGBA")
        for kind, b in [("box", b) for b in boxes] + list(own):
            (ring if kind == "ring" else box)(p, tuple(round((v - o) * s) for v, o in zip(b, (ox, oy, ox, oy))),
                                              ph / 1080)
        shadowed_paste(img, p, (x, y), edge=neutral)
        label(img, lbl, (x + 18, y + 18), 44)
        x += pw + gap
    if title.startswith("#"):
        outlined(img, title[1:], (W // 2, top // 2 + 6), 104)
    else:
        label(img, title, (W // 2, top // 2), 56, anchor="mm")
    save(img, out)
    return img


def overview(cols, out, title, crop):
    """Several screens at once: vanilla on the top row, the mod on the bottom row, one column per screen with its name
    above; every shot cropped to the same frame area (crop, raw frame pixels)."""
    img = neutral_backdrop()
    top, margin, gap, name_h = 140, 30, 24, 46
    n = len(cols)
    cw, ch = crop[2] - crop[0], crop[3] - crop[1]
    s = min((W - 2 * margin - (n - 1) * gap) / (n * cw), (H - top - margin - name_h - gap) / (2 * ch))
    pw, ph = round(cw * s), round(ch * s)
    x0 = (W - n * pw - (n - 1) * gap) // 2
    y0 = top + name_h + (H - top - margin - name_h - gap - 2 * ph) // 2
    for i, (v, m, name) in enumerate(cols):
        x = x0 + i * (pw + gap)
        label(img, name, (x + pw // 2, y0 - name_h // 2 - 4), 32, anchor="mm")
        for row, (key, lbl) in enumerate(((v, "Vanilla"), (m, "With mod"))):
            y = y0 + row * (ph + gap)
            shadowed_paste(img, shot(key).crop(crop).resize((pw, ph), Image.LANCZOS).convert("RGBA"), (x, y), edge=True)
            label(img, lbl, (x + 12, y + 12), 26)
    label(img, title, (W // 2, top // 2), 52, anchor="mm")
    save(img, out)


def main_image():
    """Main image = listing tile: the 5:4 shop, vanilla (stretched, cut off on the right) vs with the mod (full)."""
    return pair(("v_54_shop", "m_54_shop"), ("Vanilla", "With mod"), "01_main.jpg", "#" + TITLE, top=190)


def header():
    """README header, 1300x372: the main image's comparison, smaller, under the title. Also copied to docs/images/,
    the only image that is committed."""
    hw, hh = 1300, 372
    im = shot("m_54_shop")
    img = neutral_backdrop(hw, hh)
    outlined(img, TITLE, (hw // 2, 54), 58)
    ph, gap = 250, 28
    pw = round(ph * im.width / im.height)
    x = (hw - 2 * pw - gap) // 2
    for k, lbl in (("v_54_shop", "Vanilla"), ("m_54_shop", "With mod")):
        p = shot(k).resize((pw, ph), Image.LANCZOS).convert("RGBA")
        shadowed_paste(img, p, (x, 100), edge=True)
        label(img, lbl, (x + 10, 110), 24)
        x += pw + gap
    save(img, "header.jpg")
    os.makedirs(os.path.join(HERE, "images"), exist_ok=True)
    img.convert("RGB").save(os.path.join(HERE, "images", "header.jpg"), quality=90)


# The bottom-left of each 2880x1620 (16:9) frame: the whole lower-left HUD, the health bar and ability 1, ending in the
# gap before ability 2 (which sits further left the larger the HUD), so nothing is cut. Same top and height for all,
# so the panels share one scale and the sizes compare directly.
CORNERS_169 = {"s07_169_hud": (0, 600, 1346, 1620), "m_169_hud": (0, 600, 1306, 1620),
               "s13_169_hud": (0, 600, 1266, 1620)}


def sizes():
    """16:9 at size 0.7 / 1.0 / 1.3: the bottom-left corner of each frame as separate panels on a blurred backdrop."""
    img = neutral_backdrop()
    top, margin, gap = 150, 30, 30
    items = (("s07_169_hud", "Size 0.7"), ("m_169_hud", "Size 1.0 = vanilla"), ("s13_169_hud", "Size 1.3"))
    widths = [CORNERS_169[k][2] - CORNERS_169[k][0] for k, _ in items]
    ch = CORNERS_169["m_169_hud"][3] - CORNERS_169["m_169_hud"][1]
    s = min((W - 2 * margin - 2 * gap) / sum(widths), (H - top - margin) / ch)
    ph = round(ch * s)
    x = (W - round(sum(widths) * s) - 2 * gap) // 2
    y = top + (H - top - margin - ph) // 2
    for (k, lbl), cw in zip(items, widths):
        pw = round(cw * s)
        p = shot(k).crop(CORNERS_169[k]).resize((pw, ph), Image.LANCZOS).convert("RGBA")
        shadowed_paste(img, p, (x, y), edge=True)
        label(img, lbl, (x + 16, y + 16), 40)
        x += pw + gap
    label(img, "16:9: pick your HUD size (0.5 to 1.5)", (W // 2, top // 2), 56, anchor="mm")
    save(img, "08_sizes.jpg")


def thumbs(img):
    """The listing-tile test: 300 and 170 px renders next to the outputs."""
    for w, h in ((300, 169), (170, 96)):
        img.convert("RGB").resize((w, h), Image.LANCZOS).save(os.path.join(OUT, f"_tile_{w}.png"))
    g = np.asarray(img.convert("L"), dtype=np.float32) / 255
    print(f"tile brightness {g.mean():.3f} (reference tiles 0.24), contrast {g.std():.3f}")


# 5:4 HUD shots (frame pixels): the minimap is a tall oval in vanilla and a smaller circle with the mod; the health
# bar only exists with the mod (vanilla pushes it off screen)
MAP_V54 = (2005, 1300, 2870, 2300)
MAP_M54 = (2195, 1610, 2875, 2300)
HEALTH_M54 = (570, 1625, 935, 2135)

if __name__ == "__main__":
    for stale in ("02_43_hud.jpg", "03_43_shop.jpg", "04_54_hud.jpg", "05_sizes.jpg", "04_54_roster.jpg",
                  "05_54_graphs.jpg", "06_54_profile.jpg", "07_sizes.jpg", "04_54_dialogue.jpg",
                  "05_54_profile.jpg", "06_sizes.jpg", "04_54_profile.jpg", "05_54_other.jpg"):   # earlier galleries
        if os.path.exists(os.path.join(OUT, stale)):
            os.remove(os.path.join(OUT, stale))
    tile = main_image()
    header()
    v_m = ("Vanilla", "With mod")
    pair(("v_54_hud", "m_54_hud"), v_m, "02_54_hud.jpg", "5:4: health bar back, HUD no longer stretched",
         marks=((("ring", MAP_V54),), (("box", HEALTH_M54), ("ring", MAP_M54))))
    pair(("v_54_catalog", "m_54_catalog"), v_m, "03_54_items.jpg", "5:4 shop: your hero in view, nothing overlaps")
    pair(("v_54_editbuild", "m_54_editbuild"), v_m, "04_54_editbuild.jpg", "Edit Build: the panel no longer covers the items")
    pair(("v_54_watch", "m_54_watch"), v_m, "05_54_watch.jpg", "Watch Matches: the 2 x 2 grid fits")
    pair(("v_54_scoreboard", "m_54_scoreboard"), v_m, "06_54_scoreboard.jpg", "Post-match scoreboard: every column fits")
    pair(("v_54_profile", "m_54_profile"), v_m, "07_54_profile.jpg", "Player page: nothing cut off")
    sizes()
    if "--thumbs" in sys.argv:
        thumbs(tile)
