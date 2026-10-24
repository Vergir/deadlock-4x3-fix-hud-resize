"""Produce shareable packages: build/dist/<name>/pak01_dir.vpk + INSTALL.txt for several UI sizes,
zipped as deadlock-4x3-fix-hud-resize-v<version>-size<size>.zip (the version is in the name because
GameBanana mangles re-uploads of a file with an unchanged name).
The script inside the mod measures the screen itself, so one package works for any narrow
display; the size variants only change how large the HUD is (1.0 = same as a 16:9 screen of
the same width).

    python release.py 1.0.2
"""
import argparse, pathlib, re, shutil, zipfile
from build import build, ROOT

SIZES = [f"{s / 10:.1f}" for s in range(5, 16)]   # 0.5 ... 1.5

ap = argparse.ArgumentParser(description="build the release zips for every HUD size")
ap.add_argument("version", help="release version, e.g. 1.0.2 (goes into the zip names)")
args = ap.parse_args()
version = args.version.lstrip("v")
if not re.fullmatch(r"\d+\.\d+\.\d+", version):
    ap.error(f"version must look like 1.0.2, got {args.version!r}")

dist = ROOT / "build" / "dist"
if dist.exists():
    shutil.rmtree(dist)
dist.mkdir(parents=True)
for size in SIZES:
    name = f"deadlock-4x3-fix-hud-resize-v{version}-size{size}"
    d = dist / name
    vpk = build(False, float(size), "", out_dir=d)
    shutil.rmtree(d / "stage")
    shutil.copy2(ROOT / "INSTALL.txt", d / "INSTALL.txt")
    with zipfile.ZipFile(dist / f"{name}.zip", "w", zipfile.ZIP_DEFLATED) as z:
        z.write(vpk, "pak01_dir.vpk")
        z.write(d / "INSTALL.txt", "INSTALL.txt")
    print("->", dist / f"{name}.zip")
