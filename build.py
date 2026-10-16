"""Build the Deadlock narrow-display HUD addon.

Usage:  python build.py [--aspect W:H] [--ui-size 1.0] [--hud-aspect W:H] [--no-fallback] [--test]
  --aspect   screen aspect ratio the CSS fallback is built for (default 9:8). Any ratio the
             engine treats as "4x3" (narrower than 16:10) should work: 9:8, 5:4, 4:3, 1:1 ...
  --test     keep debug tints / on-screen debug label

Every file under src/panorama is a template: {{SCALE_X}}, {{SCALE_Y}}, {{WIDTH}}, {{HEIGHT}},
{{ASPECT}}, {{DEBUG}} are filled in, then the file is compiled into a Source 2 Panorama
resource and packed into build/<aspect>/pak01_dir.vpk.

Compiled resource layout (as read by ValveResourceFormat):
  header: u32 file_size, u16 header_version(12), u16 resource_version,
          u32 block_table_offset (relative to this field), u32 block_count
  table:  per block: 4-char type, u32 data_offset (relative to this field), u32 size
  .vcss_c (v3): DATA = u32 crc32(text), u16 0, text
  .vxml_c (v3): DATA = u32 crc32(text), u16 0, text          ("text" mode, legacy)
                DATA = u32 0, u16 0 ; LaCo = text KV3 layout AST ("laco" mode, what Valve ships)
  .vts_c  (v2): DATA = raw script text
"""
import argparse, pathlib, re, shutil, struct, zlib
import vpk
from xml2laco import xml_to_laco

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / "src"

# Which encoding to use for each layout override. Valve ships "laco"; "text" is the legacy
# plain-XML form. Both are being evaluated.
LAYOUT_MODE = {
    "panorama/layout/hud_data_feed.xml": "text",
    "panorama/layout/citadel_dashboard_footer_bar.xml": "text",
}
DEFAULT_LAYOUT_MODE = "laco"

# The engine lays "4x3-class" screens out on a 1440x1080 canvas stretched to the screen.
ENGINE_W, ENGINE_H = 1440.0, 1080.0
TARGET_W = 1920.0  # make the virtual canvas as wide as the 16:9 layout expects


def scale_values(aspect: str, test: bool, ui_size: float = 1.0, hud_aspect: str = "") -> dict:
    """CSS-fallback numbers for a given screen aspect (the script computes the same at runtime).
    hud_aspect constrains the HUD to the largest centered W:H region of the screen."""
    w, h = (float(x) for x in aspect.split(":"))
    W, H = 2880.0, 2880.0 * h / w                       # any width works, only ratios matter
    sx, sy = W / ENGINE_W, H / ENGINE_H                 # engine px-per-canvas-px (stretched)
    rw, rh = W, H
    hud_r = 0.0
    if hud_aspect:
        hw, hh = (float(x) for x in hud_aspect.split(":"))
        hud_r = hw / hh
        if hud_r <= W / H:
            rw, rh = H * hud_r, H
        else:
            rw, rh = W, W / hud_r
    t = min(sx, sy, rw / TARGET_W) * ui_size            # uniform px per virtual px
    ux, uy = t / sx, t / sy
    return {
        "SCALE_X": f"{ux*100:.4f}%",
        "SCALE_Y": f"{uy*100:.4f}%",
        "WIDTH": f"{(rw/W)/ux*100:.4f}%",
        "HEIGHT": f"{(rh/H)/uy*100:.4f}%",
        "ASPECT": aspect,
        "DEBUG": "true" if test else "false",
        "UI_SIZE": f"{ui_size:.4f}",
        "HUD_ASPECT": f"{hud_r:.6f}",
    }


def pack_resource(version: int, blocks: list[tuple[bytes, bytes]]) -> bytes:
    """blocks: list of (4-byte type, payload). Payloads are 16-byte aligned like Valve's files."""
    header = struct.pack("<IHHII", 0, 12, version, 8, len(blocks))
    table_size = 12 * len(blocks)
    pos = len(header) + table_size
    offsets = []
    body = bytearray()
    for i, (_, payload) in enumerate(blocks):
        pad = (-pos) % 16
        body += b"\0" * pad
        pos += pad
        offsets.append(pos)
        body += payload
        pos += len(payload)
    table = bytearray()
    for i, (btype, payload) in enumerate(blocks):
        field_pos = len(header) + 12 * i + 4
        table += btype + struct.pack("<II", offsets[i] - field_pos, len(payload))
    out = bytearray(header) + table + body
    struct.pack_into("<I", out, 0, len(out))
    return bytes(out)


def data_block(text: bytes) -> bytes:
    return struct.pack("<IH", zlib.crc32(text) & 0xFFFFFFFF, 0) + text


def compile_file(rel: str, text: str) -> tuple[str, bytes]:
    ext = pathlib.Path(rel).suffix.lower()
    raw = text.encode("utf-8")
    if ext == ".css":
        return rel[:-4] + ".vcss_c", pack_resource(3, [(b"DATA", data_block(raw))])
    if ext == ".xml":
        mode = LAYOUT_MODE.get(rel, DEFAULT_LAYOUT_MODE)
        if mode == "text":
            return rel[:-4] + ".vxml_c", pack_resource(3, [(b"DATA", data_block(raw))])
        laco = xml_to_laco(text).encode("utf-8")
        return rel[:-4] + ".vxml_c", pack_resource(3, [(b"DATA", data_block(b"")), (b"LaCo", laco)])
    if ext == ".vts":
        syntax_check(rel, raw)
        return rel + "_c", pack_resource(2, [(b"DATA", raw)])
    if ext == ".js":
        return rel[:-3] + ".vjs_c", pack_resource(4, [(b"DATA", raw)])
    raise ValueError(rel)


def syntax_check(rel: str, raw: bytes) -> None:
    """Fail the build if node is available and reports a JS syntax error."""
    import shutil as _sh, subprocess, tempfile
    node = _sh.which("node")
    if not node:
        return
    with tempfile.NamedTemporaryFile("wb", suffix=".js", delete=False) as f:
        f.write(raw)
    r = subprocess.run([node, "--check", f.name], capture_output=True, text=True)
    pathlib.Path(f.name).unlink(missing_ok=True)
    if r.returncode != 0:
        raise SystemExit(f"JS syntax error in {rel}: {r.stderr}")


def render(text: str, values: dict, test: bool, fallback: bool = True) -> str:
    if not fallback:
        text = re.sub(r"/\* FALLBACK:BEGIN.*?FALLBACK:END \*/\n?", "", text, flags=re.S)
    if not test:
        text = re.sub(r"/\* TEST BUILD:.*?\*/\s*[^{}]+\{[^}]*\}\s*", "", text, flags=re.S)
    return re.sub(r"\{\{([A-Z_]+)\}\}", lambda m: values[m.group(1)], text)


def build(aspect: str, test: bool, ui_size: float = 1.0, hud_aspect: str = "", fallback: bool = True) -> pathlib.Path:
    values = scale_values(aspect, test, ui_size, hud_aspect)
    out_dir = ROOT / "build" / aspect.replace(":", "x")
    stage = out_dir / "stage"
    if stage.exists():
        shutil.rmtree(stage)
    print(f"aspect {aspect}, ui size {ui_size}, hud region {hud_aspect or 'full screen'}, "
          f"css fallback {'on' if fallback else 'off'} ({values['SCALE_X']} {values['SCALE_Y']}, "
          f"{values['WIDTH']} x {values['HEIGHT']}), debug={values['DEBUG']}")
    for path in sorted(SRC.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(SRC).as_posix()
        if path.name == "base.css" and not fallback:
            continue        # base.css only carries aspect-specific fallback rules
        if path.suffix.lower() in (".css", ".xml", ".vts", ".js"):
            out_rel, data = compile_file(rel, render(path.read_text(encoding="utf-8"), values, test, fallback))
        else:
            out_rel, data = rel, path.read_bytes()
        dest = stage / out_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        print(f"  {rel} -> {out_rel} ({len(data)} bytes)")
    out_vpk = out_dir / "pak01_dir.vpk"
    vpk.new(str(stage)).save(str(out_vpk))
    print(f"packed -> {out_vpk} ({out_vpk.stat().st_size} bytes)")
    return out_vpk


def local_settings() -> dict:
    """Personal defaults from local_settings.json (aspect, ui_size, hud_aspect, gameinfo_convars)."""
    import json
    p = ROOT / "local_settings.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


if __name__ == "__main__":
    ls = local_settings()
    ap = argparse.ArgumentParser()
    ap.add_argument("--aspect", default=ls.get("aspect", "9:8"))
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--ui-size", type=float, default=float(ls.get("ui_size", 1.0)),
                    help="HUD size multiplier; 1.0 = same size as a 16:9 screen of the same width")
    ap.add_argument("--hud-aspect", default=ls.get("hud_aspect", ""),
                    help="constrain the HUD to the largest centered W:H region of the screen, e.g. 1:1")
    ap.add_argument("--no-fallback", action="store_true",
                    help="script only; do not ship the aspect-specific CSS fallback (for shared builds)")
    a = ap.parse_args()
    build(a.aspect, a.test, a.ui_size, a.hud_aspect, not a.no_fallback)
