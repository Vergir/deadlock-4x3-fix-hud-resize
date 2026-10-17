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
GOLD = (216, 201, 163)
W, H = 1920, 1080
TITLE = "HUD Resize & 4:3 / 5:4 Fix"

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

_cache = {}


def hide_fps(im):
    """Paint out the game's FPS counter in the bottom-right corner (bright text pixels, inpainted)."""
    a = np.asarray(im).copy()
    h, w = a.shape[:2]
    l, t, r, b = w - 340, h - 75, w - 5, h - 5
    reg = a[t:b, l:r].astype(int)
    g = reg.mean(axis=2)
    m = (g > 120) | ((reg[:, :, 0] - reg[:, :, 1]) > 50)
    mask = np.zeros((h, w), np.uint8)
    mask[t:b, l:r] = m.astype(np.uint8) * 255
    mask = cv2.dilate(mask, np.ones((7, 7), np.uint8))
    return Image.fromarray(cv2.inpaint(a[:, :, ::-1], mask, 7, cv2.INPAINT_TELEA)[:, :, ::-1])


def shot(key):
    if key not in _cache:
        im = Image.open(os.path.join(RAW, key + ".png")).convert("RGB").crop(FRAMES[key])
        _cache[key] = hide_fps(im)
    return _cache[key]


def font(size):
    return ImageFont.truetype(FONT, size)


def box(img, b, k=1.0):
    """The highlight: a rounded gold outline, 5 px wide, radius 14 at a 1080 px tall image (k = image height / 1080)."""
    ImageDraw.Draw(img).rounded_rectangle(b, round(14 * k), outline=GOLD, width=max(3, round(5 * k)))


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


def shadowed_paste(dst, src, xy):
    x, y = xy
    sh = Image.new("RGBA", dst.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle((x + 6, y + 10, x + src.width + 6, y + src.height + 10), fill=(0, 0, 0, 210))
    dst.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14)))
    dst.paste(src, (x, y))


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


def pair(keys, labels, out, title, crop=None, boxes=(), top=150, gap=40, margin=40, bright=1.0):
    """Two shots side by side on a blurred backdrop, labelled; crop and boxes are in raw frame pixels."""
    img = backdrop(keys[1])
    ims = [shot(k).crop(crop) if crop else shot(k) for k in keys]
    s = min((W - 2 * margin - gap) / (2 * ims[0].width), (H - top - margin) / ims[0].height)
    pw, ph = round(ims[0].width * s), round(ims[0].height * s)
    x = (W - 2 * pw - gap) // 2
    y = top + (H - top - margin - ph) // 2
    for im, lbl in zip(ims, labels):
        p = ImageEnhance.Brightness(im.resize((pw, ph), Image.LANCZOS)).enhance(bright).convert("RGBA")
        for b in boxes:
            ox, oy = (crop[0], crop[1]) if crop else (0, 0)
            box(p, tuple(round((v - o) * s) for v, o in zip(b, (ox, oy, ox, oy))), ph / 1080)
        shadowed_paste(img, p, (x, y))
        label(img, lbl, (x + 18, y + 18), 44)
        x += pw + gap
    if title.startswith("#"):
        outlined(img, title[1:], (W // 2, top // 2 + 6), 104)
    else:
        label(img, title, (W // 2, top // 2), 56, anchor="mm")
    save(img, out)
    return img


# Health bar on a 2880x2160 (4:3) frame at size 1.0: 1.5 px per HUD unit, container at x 315, 300 wide, 456 tall,
# 20 above the bottom of the 1440-unit-tall canvas.
HEALTH_43 = (440, 1430, 960, 2150)


def main_image():
    """Main image = listing tile: the bottom-left of a 4:3 screen, vanilla (no health bar) vs with the mod."""
    return pair(("v_43_hud", "m_43_hud"), ("Vanilla", "With mod"), "01_main.jpg", "#" + TITLE,
                crop=(0, 900, 1680, 2160), boxes=[HEALTH_43], top=190)


def header():
    """README header, 1300x372: the main image's comparison, smaller, under the title. Also copied to docs/images/,
    the only image that is committed."""
    hw, hh = 1300, 372
    im = shot("m_43_hud")
    s = max(hw / im.width, hh / im.height)
    bg = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    y0 = (bg.height - hh) // 2
    img = ImageEnhance.Brightness(bg.crop((0, y0, hw, y0 + hh)).filter(ImageFilter.GaussianBlur(10))).enhance(0.7)
    img = img.convert("RGBA")
    outlined(img, TITLE, (hw // 2, 54), 58)
    crop = (0, 900, 1680, 2160)
    ph, gap = 250, 28
    pw = round(ph * (crop[2] - crop[0]) / (crop[3] - crop[1]))
    x = (hw - 2 * pw - gap) // 2
    for k, lbl in (("v_43_hud", "Vanilla"), ("m_43_hud", "With mod")):
        p = shot(k).crop(crop).resize((pw, ph), Image.LANCZOS).convert("RGBA")
        sc = ph / (crop[3] - crop[1])
        box(p, tuple(round((v - o) * sc) for v, o in zip(HEALTH_43, (0, 900, 0, 900))), ph / 1080 * 2)
        shadowed_paste(img, p, (x, 100))
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
    img = backdrop("m_169_hud")
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
        shadowed_paste(img, p, (x, y))
        label(img, lbl, (x + 16, y + 16), 40)
        x += pw + gap
    label(img, "16:9: pick your HUD size (0.5 to 1.5)", (W // 2, top // 2), 56, anchor="mm")
    save(img, "05_sizes.jpg")


def thumbs(img):
    """The listing-tile test: 300 and 170 px renders next to the outputs."""
    for w, h in ((300, 169), (170, 96)):
        img.convert("RGB").resize((w, h), Image.LANCZOS).save(os.path.join(OUT, f"_tile_{w}.png"))
    g = np.asarray(img.convert("L"), dtype=np.float32) / 255
    print(f"tile brightness {g.mean():.3f} (reference tiles 0.24), contrast {g.std():.3f}")


if __name__ == "__main__":
    tile = main_image()
    header()
    pair(("v_43_hud", "m_43_hud"), ("Vanilla", "With mod"), "02_43_hud.jpg", "4:3: the health bar is back",
         boxes=[HEALTH_43])
    pair(("v_43_shop", "m_43_shop"), ("Vanilla", "With mod"), "03_43_shop.jpg",
         "4:3 shop: Quick Buy no longer covers the items")
    pair(("v_54_hud", "m_54_hud"), ("Vanilla", "With mod"), "04_54_hud.jpg",
         "5:4: health bar back, HUD no longer stretched")
    sizes()
    if "--thumbs" in sys.argv:
        thumbs(tile)
