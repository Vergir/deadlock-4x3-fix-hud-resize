"""Internal comparison sheets (not for the mod page): for each screen, vanilla 16:9 on top, vanilla 5:4 bottom
left, the mod at 5:4 bottom right, so we can see where the mod fixes something, where it falls short and which
screens make good page shots. A screen missing from a set gets a black "MISSING" panel.

Usage: python docs/make_compare.py  (reads Steam/Snipping Tool screenshots, writes docs/pics/compare/, git-ignored)
The snips include the Steam window around the game; the game frame (2880x1620 or 2880x2304) is found from the
strongest row changes at its top and bottom edges.
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SRC = os.path.expanduser("~/Pictures/Screenshots")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pics", "compare")
FONT = "C:/Windows/Fonts/segoeuib.ttf"
SHOT = "Screenshot 2026-10-24 {}.png"

# screen: (vanilla 16:9, vanilla 5:4, mod 5:4) snip times (2026-10-24 unless dated), None = not taken;
# mod 5:4: the 2026-10-25 set (menus at vanilla size), game build 6819
SCREENS = [
    ("01 play mode select", "215025", "214548", "2026-10-25 013228"),
    ("02 create roster (hero select)", "215036", "214609", "2026-10-25 013233"),
    ("03 ranked", "215113", "214623", "2026-10-25 013243"),
    ("04 leaderboards", "215121", "214630", "2026-10-25 015214"),
    ("05 player page", "215220", "214713", "2026-10-25 013322"),
    ("06 post-match team", "215234", "214720", "2026-10-25 013331"),
    ("07 post-match scoreboard", "215246", "214726", "2026-10-25 013338"),
    ("08 post-match MVP", "215238", "214731", "2026-10-25 013346"),
    ("09 post-match graphs", "215257", "214743", "2026-10-25 013355"),
    ("10 watch matches", "215059", "214805", "2026-10-25 013406"),
    ("11 recent updates", "215105", "214814", "2026-10-25 013421"),
    ("12 dialogue player", "215050", "214822", "2026-10-25 013434"),
    ("13 shop item page (Weapon)", "233557", "214839", "2026-10-25 013444"),
    ("14 shop edit build", "215147", "214900", "2026-10-25 013452"),
    ("15 shop build browser", "215154", "214915", "2026-10-25 013503"),
    ("16 shop build page, quick buy closed", "215129", "214925", "2026-10-25 013517"),
    ("17 shop build page, quick buy open", "215139", "233527", "2026-10-25 013523"),
    ("18 esc menu", "233608", "214943", "2026-10-25 013529"),
    ("19 match history", "215227", "215005", "2026-10-25 015221"),
]


# frame tops checked by hand where the edge search picks the wrong row
TOPS = {"215220": 43, "215535": 21}


def frame(stamp, fh):
    """The game frame inside a snip: the top row t (0..250) whose edges t and t+fh change the most."""
    name = "Screenshot {}.png".format(stamp) if " " in stamp else SHOT.format(stamp)   # "date time" or time
    im = Image.open(os.path.join(SRC, name)).convert("RGB")
    if stamp in TOPS:
        return im.crop((0, TOPS[stamp], im.width, min(im.height, TOPS[stamp] + fh)))
    a = np.asarray(im.convert("L"), dtype=float)
    diff = np.abs(np.diff(a, axis=0)).mean(axis=1)
    h = a.shape[0]

    def score(t):
        return (diff[t - 1] if t > 0 else 0) + (diff[t + fh - 1] if t + fh - 1 < h - 1 else 0)
    t = max(range(0, min(250, h - 100)), key=score)
    return im.crop((0, t, im.width, min(h, t + fh)))


def panel(stamp, fh, w, h, name):
    if stamp is None:
        p = Image.new("RGB", (w, h), (0, 0, 0))
        d = ImageDraw.Draw(p)
        d.text((w // 2, h // 2), "MISSING", font=ImageFont.truetype(FONT, h // 6), fill=(230, 60, 60), anchor="mm")
        d.text((w // 2, h // 2 + h // 7), name, font=ImageFont.truetype(FONT, 34), fill=(200, 200, 200), anchor="mm")
        return p
    im = frame(stamp, fh)
    s = min(w / im.width, h / im.height)
    p = Image.new("RGB", (w, h), (0, 0, 0))
    r = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    p.paste(r, (0, 0))
    return p


def tag(img, text, xy):
    d = ImageDraw.Draw(img, "RGBA")
    f = ImageFont.truetype(FONT, 34)
    l, t, r, b = d.textbbox(xy, text, font=f)
    d.rounded_rectangle((l - 8, t - 6, r + 8, b + 6), 8, fill=(0, 0, 0, 200))
    d.text(xy, text, font=f, fill="white")


def sheet(name, wide, v54, m54):
    W, gap = 2000, 20
    bw = (W - 3 * gap) // 2
    bh = round(bw * 2304 / 2880)
    tw = 1400
    th = round(tw * 1620 / 2880)
    title_h = 70
    H = title_h + th + gap + bh + gap
    img = Image.new("RGB", (W, H), (40, 42, 48))
    d = ImageDraw.Draw(img)
    d.text((W // 2, title_h // 2), name, font=ImageFont.truetype(FONT, 44), fill="white", anchor="mm")
    tx = (W - tw) // 2
    img.paste(panel(wide, 1620, tw, th, "vanilla 16:9"), (tx, title_h))
    tag(img, "16:9 vanilla", (tx + 14, title_h + 12))
    y = title_h + th + gap
    img.paste(panel(v54, 2304, bw, bh, "vanilla 5:4"), (gap, y))
    tag(img, "5:4 vanilla", (gap + 14, y + 12))
    img.paste(panel(m54, 2304, bw, bh, "mod 5:4"), (2 * gap + bw, y))
    tag(img, "5:4 with mod (size 1.0)", (2 * gap + bw + 14, y + 12))
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name.replace(" ", "_").replace(",", "").replace("(", "").replace(")", "") + ".jpg")
    img.save(path, quality=88)
    print(os.path.basename(path))


# 16:9 check (2026-10-25): the mod at size 1.0 on 2880x1620, same order as SCREENS; should match vanilla 16:9
MOD_169 = ["2026-10-25 " + t for t in "015932 015939 015948 015954 020008 020019 020027 020038 020045 020055 020104 "
           "020117 020132 020140 020148 020155 020159 020206 020218".split()]


def sheet169(name, wide, mod):
    """vanilla 16:9 left, mod 16:9 right"""
    W, gap, title_h = 2000, 20, 70
    pw = (W - 3 * gap) // 2
    ph = round(pw * 1620 / 2880)
    img = Image.new("RGB", (W, title_h + ph + gap), (40, 42, 48))
    ImageDraw.Draw(img).text((W // 2, title_h // 2), name + " (16:9 check)", font=ImageFont.truetype(FONT, 44),
                             fill="white", anchor="mm")
    img.paste(panel(wide, 1620, pw, ph, "vanilla 16:9"), (gap, title_h))
    tag(img, "16:9 vanilla", (gap + 14, title_h + 12))
    img.paste(panel(mod, 1620, pw, ph, "mod 16:9"), (2 * gap + pw, title_h))
    tag(img, "16:9 with mod (size 1.0)", (2 * gap + pw + 14, title_h + 12))
    out = os.path.join(OUT, "169")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, name.replace(" ", "_").replace(",", "").replace("(", "").replace(")", "") + ".jpg")
    img.save(path, quality=88)
    print("169/" + os.path.basename(path))


if __name__ == "__main__":
    only = [a for a in sys.argv[1:] if a != "--169"]
    for i, s in enumerate(SCREENS):
        if only and s[0][:2] not in only:
            continue
        if "--169" in sys.argv:
            sheet169(s[0], s[1], MOD_169[i])
        else:
            sheet(*s)
