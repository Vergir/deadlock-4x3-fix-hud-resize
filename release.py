"""Produce shareable packages: build/dist/<name>/pak01_dir.vpk + README for several UI sizes.
The script inside the mod measures the screen itself, so one package works for any narrow
display; the size variants only change how large the HUD is (1.0 = same as a 16:9 screen of
the same width)."""
import pathlib, shutil, zipfile
from build import build, ROOT

SIZES = ["0.8", "0.9", "1.0", "1.1", "1.2"]
dist = ROOT / "build" / "dist"
if dist.exists():
    shutil.rmtree(dist)
dist.mkdir(parents=True)
for size in SIZES:
    vpk = build("9:8", False, float(size), "", fallback=False)
    name = f"deadlock-narrow-hud-size{size}"
    d = dist / name
    d.mkdir()
    shutil.copy2(vpk, d / "pak01_dir.vpk")
    shutil.copy2(ROOT / "INSTALL.txt", d / "INSTALL.txt")
    with zipfile.ZipFile(dist / f"{name}.zip", "w", zipfile.ZIP_DEFLATED) as z:
        z.write(d / "pak01_dir.vpk", "pak01_dir.vpk")
        z.write(d / "INSTALL.txt", "INSTALL.txt")
    print("->", dist / f"{name}.zip")
