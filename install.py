"""Install the mod: copy the built VPK to the addons folder and make sure gameinfo.gi mounts
citadel/addons. Safe to re-run after every game update (Steam verifies/overwrites gameinfo.gi,
which drops the addons line).

    python install.py [ASPECT] [--aspect-convar VALUE]

ASPECT selects build/<aspect>/pak01_dir.vpk (default 9:8).
--aspect-convar sets r_aspectratio in gameinfo.gi's ConVars block (the mechanism performance
configs use); pass "" to remove it again. This is NOT part of the HUD mod, it changes the
game's field of view.
"""
import pathlib
import re
import shutil
import sys

GAME = pathlib.Path(r"C:/Games/Steam/steamapps/common/Deadlock/game/citadel")
ROOT = pathlib.Path(__file__).resolve().parent
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
ASPECT = ARGS[0] if ARGS else "9:8"
VPK = ROOT / "build" / ASPECT.replace(":", "x") / "pak01_dir.vpk"


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
    s = p.read_text(encoding="utf-8")
    s = re.sub(r'\n\t\t"' + re.escape(name) + r'"\t+"[^"]*"[^\n]*', "", s)
    if value:
        anchor = "\tConVars\n\t{\t \n"
        if anchor not in s:
            sys.exit("gameinfo.gi: ConVars block not found in the expected form")
        line = '\t\t"' + name + '"\t\t"' + value + '"\t\t// added by install.py\n'
        s = s.replace(anchor, anchor + line, 1)
        print(f"gameinfo.gi: {name} = {value}")
    else:
        print(f"gameinfo.gi: {name} removed")
    p.write_text(s, encoding="utf-8", newline="")


def install_vpk():
    addons = GAME / "addons"
    addons.mkdir(exist_ok=True)
    if VPK.exists():
        shutil.copy2(VPK, addons / VPK.name)
        print(f"copied {VPK.name} -> {addons}")
    else:
        print(f"no {VPK} yet, run build.py first")


if __name__ == "__main__":
    patch_gameinfo()
    install_vpk()
    if "--aspect-convar" in sys.argv:
        set_convar("r_aspectratio", sys.argv[sys.argv.index("--aspect-convar") + 1])
