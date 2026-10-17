"""Install the mod: copy the built VPK to the addons folder and make sure gameinfo.gi mounts
citadel/addons. Safe to re-run after every game update (Steam verifies/overwrites gameinfo.gi,
which drops the addons line).

    python install.py [--aspect-convar VALUE]

Installs build/mod/pak01_dir.vpk (what build.py produces) as addons/pak99_dir.vpk: Deadlock Mod
Manager names the mods it manages pak01, pak02, ... (lowest free number), so a high number keeps
the two from overwriting each other.
--aspect-convar sets r_aspectratio in gameinfo.gi's ConVars block (the mechanism performance
configs use); pass "" to remove it again. This is NOT part of the HUD mod, it changes the
game's field of view.
"""
import json
import pathlib
import re
import shutil
import sys

GAME = pathlib.Path(r"C:/Games/Steam/steamapps/common/Deadlock/game/citadel")
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


def install_vpk():
    addons = GAME / "addons"
    addons.mkdir(exist_ok=True)
    if not VPK.exists():
        print(f"no {VPK} yet, run build.py first")
        return
    dmm = addons / ".dmm.json"
    if dmm.exists():
        managed = {v for m in json.loads(dmm.read_text(encoding="utf-8")).get("mods", {}).values()
                   for v in m.get("currentVpks", [])}
        if TARGET in managed:
            sys.exit(f"{TARGET} belongs to a Deadlock Mod Manager mod; pick another TARGET in install.py")
    shutil.copy2(VPK, addons / TARGET)
    print(f"copied {VPK.name} -> {addons / TARGET}")


if __name__ == "__main__":
    patch_gameinfo()
    install_vpk()
    # personal gameinfo.gi convars from local_settings.json (e.g. r_aspectratio); re-applied every run
    for name, value in SETTINGS.get("gameinfo_convars", {}).items():
        set_convar(name, str(value))
    if "--aspect-convar" in sys.argv:
        set_convar("r_aspectratio", sys.argv[sys.argv.index("--aspect-convar") + 1])
