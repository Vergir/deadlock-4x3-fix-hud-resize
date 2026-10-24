"""Build the HUD Resize & 4:3 / 5:4 Fix addon.

Usage:  python build.py [--ui-size 1.0] [--hud-aspect W:H] [--fov-aspect R] [--test]
  --ui-size     HUD size, 1.0 = vanilla size on 16:9 (0.5 ... 1.5 are shipped)
  --hud-aspect  confine the HUD to the largest centered W:H region (personal builds)
  --fov-aspect  your r_aspectratio, only used to size the crosshair (personal builds)
  --test        keep the on-screen debug label
Without arguments the defaults come from local_settings.json when it exists.

Every file under src/panorama is a template: {{UI_SIZE}}, {{HUD_ASPECT}}, {{FOV_ASPECT}},
{{DEBUG}}, {{BUILD_ID}} are filled in, then the file is compiled into a Source 2 Panorama resource and packed
into build/mod/pak01_dir.vpk. The script measures the screen itself, so the same build works on
any screen shape.

Compiled resource layout (as read by ValveResourceFormat). Valve ships layouts as a KV3 "LaCo"
block; the engine also accepts the legacy plain-text form used here.
  header: u32 file_size, u16 header_version(12), u16 resource_version,
          u32 block_table_offset (relative to this field), u32 block_count
  table:  per block: 4-char type, u32 data_offset (relative to this field), u32 size
  .vcss_c (v3): DATA = u32 crc32(text), u16 0, text
  .vxml_c (v3): DATA = u32 crc32(text), u16 0, text
  .vts_c  (v2): DATA = raw script text
"""
import argparse, pathlib, re, shutil, struct, zlib
import vpk

ROOT = pathlib.Path(__file__).resolve().parent
SRC = ROOT / "src"
DEFAULT_OUT = ROOT / "build" / "mod"


def template_values(test: bool, ui_size: float = 1.0, hud_aspect: str = "", fov_aspect: float = 0.0) -> dict:
    """hud_aspect "W:H" confines the HUD to the largest centered W:H region; "" = whole screen.
    fov_aspect: the personal r_aspectratio (0 = default FOV), only used to size the crosshair so its
    pips match the real bullet spread; never set for shared builds."""
    hud_r = 0.0
    if hud_aspect:
        hw, hh = (float(x) for x in hud_aspect.split(":"))
        hud_r = hw / hh
    import datetime
    return {
        "DEBUG": "true" if test else "false",
        # test builds carry their build time (shows whether a hot reload picked up the new script)
        "BUILD_ID": datetime.datetime.now().strftime("%H:%M:%S") if test else "release",
        "UI_SIZE": f"{ui_size:.4f}",
        "HUD_ASPECT": f"{hud_r:.6f}",
        "FOV_ASPECT": f"{fov_aspect:.6f}",
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
        return rel[:-4] + ".vxml_c", pack_resource(3, [(b"DATA", data_block(raw))])
    if ext == ".vts":
        syntax_check(rel, raw)
        return rel + "_c", pack_resource(2, [(b"DATA", raw)])
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


def render(text: str, values: dict) -> str:
    return re.sub(r"\{\{([A-Z_]+)\}\}", lambda m: values[m.group(1)], text)


def build(test: bool, ui_size: float = 1.0, hud_aspect: str = "", out_dir: pathlib.Path = DEFAULT_OUT,
          fov_aspect: float = 0.0) -> pathlib.Path:
    values = template_values(test, ui_size, hud_aspect, fov_aspect)
    stage = out_dir / "stage"
    if stage.exists():
        shutil.rmtree(stage)
    print(f"ui size {ui_size}, hud region {hud_aspect or 'full screen'}, "
          f"crosshair fov {fov_aspect or 'default'}, debug={values['DEBUG']}")
    for path in sorted(SRC.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(SRC).as_posix()
        if path.suffix.lower() in (".css", ".xml", ".vts"):
            out_rel, data = compile_file(rel, render(path.read_text(encoding="utf-8"), values))
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
    """Personal defaults from local_settings.json (ui_size, hud_aspect, gameinfo_convars)."""
    import json
    p = ROOT / "local_settings.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


if __name__ == "__main__":
    ls = local_settings()
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--ui-size", type=float, default=float(ls.get("ui_size", 1.0)),
                    help="HUD size multiplier; 1.0 = same size as a 16:9 screen of the same width")
    ap.add_argument("--hud-aspect", default=ls.get("hud_aspect", ""),
                    help="constrain the HUD to the largest centered W:H region of the screen, e.g. 1:1")
    ap.add_argument("--fov-aspect", type=float,
                    default=float(ls.get("gameinfo_convars", {}).get("r_aspectratio", 0) or 0),
                    help="your r_aspectratio (default: from local_settings.json), sizes the crosshair; 0 = default FOV")
    a = ap.parse_args()
    build(a.test, a.ui_size, a.hud_aspect, fov_aspect=a.fov_aspect)
