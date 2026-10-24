"""Install the mod: copy the built VPK to the addons folder and make sure gameinfo.gi mounts
citadel/addons. Safe to re-run after every game update (Steam verifies/overwrites gameinfo.gi,
which drops the addons line).

    python install.py [--loose] [--launch NAME] [--aspect-convar VALUE]

--loose (development) installs the script as a loose file under addons/ and only layouts and styles
in the VPK, so script changes can be installed while the game runs. A normal install removes it again.

Installs build/mod/pak01_dir.vpk (what build.py produces) as addons/pak99_dir.vpk: Deadlock Mod
Manager names the mods it manages pak01, pak02, ... (lowest free number), so a high number keeps
the two from overwriting each other.
--aspect-convar sets r_aspectratio in gameinfo.gi's ConVars block (the mechanism performance
configs use); pass "" to remove it again. This is NOT part of the HUD mod, it changes the
game's field of view.

With a "launch_options" entry in local_settings.json ({"modded": "-w 2880 -h 2560", "vanilla": ""})
it also sets Deadlock's Steam launch options (install.py: modded, uninstall.py: vanilla). Without
-w/-h the game uses the resolution saved in video.txt. Steam keeps launch options in
userdata/<id>/config/localconfig.vdf and rewrites that file on exit, so when they need to change and
Steam is running, the script shuts Steam down, edits the file and starts Steam again.
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys
import time

GAME = pathlib.Path(r"C:/Games/Steam/steamapps/common/Deadlock/game/citadel")
STEAM = pathlib.Path(r"C:/Program Files (x86)/Steam")
STEAM_USER = "62013903"
APP_ID = "1422450"
ROOT = pathlib.Path(__file__).resolve().parent
LOCAL = ROOT / "local_settings.json"
SETTINGS = json.loads(LOCAL.read_text(encoding="utf-8")) if LOCAL.exists() else {}
VPK = ROOT / "build" / "mod" / "pak01_dir.vpk"
TARGET = "pak99_dir.vpk"


def patch_gameinfo():
    p = GAME / "gameinfo.gi"
    s = p.read_text(encoding="utf-8")
    if "citadel/addons" in s:
        print("gameinfo.gi: addons path already present")
        return
    old = "\t\t\tGame\t\t\t\tcitadel\n\t\t\tGame\t\t\t\tcore\n"
    if s.count(old) != 1:
        sys.exit("gameinfo.gi: SearchPaths block not in the expected form, patch by hand")
    new = ("\t\t\tMod\t\t\t\tcitadel\n"
           "\t\t\tWrite\t\t\t\tcitadel\n"
           "\t\t\tGame\t\t\t\tcitadel/addons\n"
           "\t\t\tGame\t\t\t\tcitadel\n"
           "\t\t\tGame\t\t\t\tcore\n")
    p.write_text(s.replace(old, new), encoding="utf-8", newline="")
    print("gameinfo.gi: added Mod/Write/addons search paths")


def set_convar(name: str, value: str):
    """Add, update or remove (value "") a convar line in gameinfo.gi's ConVars block."""
    p = GAME / "gameinfo.gi"
    original = p.read_text(encoding="utf-8")
    s = re.sub(r'\n\t\t"' + re.escape(name) + r'"\t+"[^"]*"[^\n]*', "", original)
    if value:
        anchor = "\tConVars\n\t{\t \n"
        if anchor not in s:
            sys.exit("gameinfo.gi: ConVars block not found in the expected form")
        line = '\t\t"' + name + '"\t\t"' + value + '"\t\t// added by install.py\n'
        s = s.replace(anchor, anchor + line, 1)
    if s == original:
        print(f"gameinfo.gi: {name} already {'= ' + value if value else 'absent'}")
        return
    try:
        p.write_text(s, encoding="utf-8", newline="")
    except PermissionError:
        sys.exit(f"gameinfo.gi is locked (Deadlock running?); {name} not changed")
    print(f"gameinfo.gi: {name} = {value}" if value else f"gameinfo.gi: {name} removed")


def check_target(addons: pathlib.Path):
    dmm = addons / ".dmm.json"
    if dmm.exists():
        managed = {v for m in json.loads(dmm.read_text(encoding="utf-8")).get("mods", {}).values()
                   for v in m.get("currentVpks", [])}
        if TARGET in managed:
            sys.exit(f"{TARGET} belongs to a Deadlock Mod Manager mod; pick another TARGET in install.py")


def install_vpk():
    addons = GAME / "addons"
    addons.mkdir(exist_ok=True)
    if not VPK.exists():
        print(f"no {VPK} yet, run build.py first")
        return
    check_target(addons)
    remove_loose()
    try:
        shutil.copy2(VPK, addons / TARGET)
    except PermissionError:
        sys.exit(f"{TARGET} is locked (Deadlock running?); not installed")
    print(f"copied {VPK.name} -> {addons / TARGET}")


# Development: the script as a loose file in addons/, the rest (layouts, CSS) in pak99 as usual. The game
# searches its own citadel/pak01.vpk before loose files in addons/ (but addons VPKs before both), so loose
# copies of vanilla files are ignored (tested 2026-10-24); our script has no vanilla twin, so the layouts in
# pak99 find it loose. Loose files are not locked by the game, so the script can be replaced while it runs.
LOOSE_LIST = GAME / "addons" / "hud_resize_loose_files.txt"
LOOSE_DIRS = ("panorama/scripts/",)


def remove_loose():
    if not LOOSE_LIST.exists():
        return
    addons = GAME / "addons"
    for rel in LOOSE_LIST.read_text(encoding="utf-8").split():
        (addons / rel).unlink(missing_ok=True)
        for parent in (addons / rel).parents:   # prune now-empty folders, never addons itself
            if parent == addons or any(parent.iterdir()):
                break
            parent.rmdir()
    LOOSE_LIST.unlink()
    print("removed the loose files")


def install_loose():
    import vpk
    stage = VPK.parent / "stage"
    addons = GAME / "addons"
    files = sorted(p.relative_to(stage).as_posix() for p in stage.rglob("*") if p.is_file())
    if not files:
        sys.exit("no build/mod/stage yet, run build.py first")
    loose = [f for f in files if f.startswith(LOOSE_DIRS)]
    # the VPK part: everything else; replaced only when it changed (the game locks it while running)
    dev_stage = VPK.parent / "dev" / "stage"
    if dev_stage.exists():
        shutil.rmtree(dev_stage)
    for rel in files:
        if rel not in loose:
            (dev_stage / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(stage / rel, dev_stage / rel)
    dev_vpk = VPK.parent / "dev" / "pak01_dir.vpk"
    vpk.new(str(dev_stage)).save(str(dev_vpk))
    check_target(addons)
    target = addons / TARGET
    if target.exists() and target.read_bytes() == dev_vpk.read_bytes():
        print(f"{TARGET} (layouts, styles) unchanged")
    else:
        try:
            shutil.copy2(dev_vpk, target)
        except PermissionError:
            sys.exit(f"{TARGET} is locked and layouts or styles changed; close the game and run again")
        print(f"copied layouts and styles -> {target}")
    # hot reload: number this install (written into the script's DEV_SEQ literal, same width so the compiled
    # file needs no repacking) and add layout/narrowhud_dev_<n>.xml + scripts/narrowhud_dev_<n>.vts, which a
    # running script with number n-1 picks up (see probeReload in the script)
    seq_file = VPK.parent / "dev" / "seq.txt"
    seq = (int(seq_file.read_text()) if seq_file.exists() else 0) + 1
    seq_file.write_text(str(seq))
    from build import compile_file
    out = {}
    for rel in loose:
        data = (stage / rel).read_bytes()
        if rel == "panorama/scripts/narrowhud.vts_c":
            old, new = b'parseInt("000000"', b'parseInt("%06d"' % seq
            if data.count(old) != 1:
                sys.exit("script has no DEV_SEQ literal; rebuild")
            data = data.replace(old, new)
            out[f"panorama/scripts/narrowhud_dev_{seq}.vts_c"] = data
        out[rel] = data
    layout_rel, layout = compile_file(
        f"panorama/layout/narrowhud_dev_{seq}.xml",
        "<root>\n\t<scripts>\n\t\t<include src=\"s2r://panorama/scripts/narrowhud_dev_%d.vts\" />\n"
        "\t</scripts>\n\t<Panel hittest=\"false\" />\n</root>\n" % seq)
    out[layout_rel] = layout
    remove_loose()
    for rel, data in out.items():
        (addons / rel).parent.mkdir(parents=True, exist_ok=True)
        (addons / rel).write_bytes(data)
    LOOSE_LIST.write_text("\n".join(sorted(out)) + "\n", encoding="utf-8")
    print(f"copied the script (loose) as hot-reload #{seq} -> {addons}")


def running(exe: str) -> bool:
    out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {exe}", "/NH"], capture_output=True, text=True).stdout
    return exe.lower() in out.lower()


def set_launch_options(which: str):
    """Set Deadlock's Steam launch options to local_settings.json launch_options[which]."""
    opts = SETTINGS.get("launch_options", {})
    if which not in opts:
        return
    value = opts[which]
    cfg = STEAM / "userdata" / STEAM_USER / "config" / "localconfig.vdf"
    # the app's block in Software/Valve/Steam/apps: the one with LastPlayed, closed at its own indent
    block = re.compile(r'\n(\t+)"' + APP_ID + r'"\n\1\{\n(.*?)\n\1\}', re.S)

    def edit(text: str) -> str:
        for m in block.finditer(text):
            body = m.group(2)
            if '"LastPlayed"' not in body:
                continue
            indent = m.group(1) + "\t"
            line = f'{indent}"LaunchOptions"\t\t"{value}"'
            new, n = re.subn(r'(?m)^' + indent + r'"LaunchOptions"\t\t"(?:[^"\\]|\\.)*"$', lambda _: line, body)
            if n == 0:
                new = line + "\n" + body
            return text[:m.start(2)] + new + text[m.end(2):]
        sys.exit(f"localconfig.vdf: no app block for {APP_ID}; set the launch options by hand: {value!r}")

    text = cfg.read_text(encoding="utf-8")
    if edit(text) == text:
        print(f"Steam launch options already {value!r}")
        return
    if running("deadlock.exe"):
        sys.exit("Deadlock is running; close it to change the launch options")
    restart = running("steam.exe")
    if restart:
        print("shutting Steam down to change the launch options ...")
        subprocess.run([str(STEAM / "steam.exe"), "-shutdown"])
        for _ in range(120):
            if not running("steam.exe"):
                break
            time.sleep(0.5)
        else:
            sys.exit("Steam did not exit; launch options not changed")
        time.sleep(1)
        text = cfg.read_text(encoding="utf-8")   # Steam wrote it on exit
    backup = cfg.with_name("localconfig.vdf.hud-resize-backup")
    if not backup.exists():
        shutil.copy2(cfg, backup)
    cfg.write_text(edit(text), encoding="utf-8", newline="")
    print(f"Steam launch options: {value!r} ({which})")
    if restart:
        subprocess.Popen([str(STEAM / "steam.exe"), "-silent"],
                         creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
        print("Steam restarted")


if __name__ == "__main__":
    patch_gameinfo()
    if "--loose" in sys.argv:
        install_loose()
    else:
        install_vpk()
    # personal gameinfo.gi convars from local_settings.json (e.g. r_aspectratio); re-applied every run
    for name, value in SETTINGS.get("gameinfo_convars", {}).items():
        set_convar(name, str(value))
    if "--aspect-convar" in sys.argv:
        set_convar("r_aspectratio", sys.argv[sys.argv.index("--aspect-convar") + 1])
    # --launch NAME picks another local_settings.json launch_options entry (e.g. "vanilla" for 16:9 tests)
    set_launch_options(sys.argv[sys.argv.index("--launch") + 1] if "--launch" in sys.argv else "modded")
