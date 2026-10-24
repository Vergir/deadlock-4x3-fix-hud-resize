"""Undo install.py to compare with vanilla: remove addons/pak99_dir.vpk (or the --loose files), remove
the personal gameinfo.gi convars listed in local_settings.json (e.g. r_aspectratio) and set the "vanilla" Steam
launch options (e.g. -w 2880 -h 1620; Steam is restarted if needed).
`python install.py` puts everything back.

    python uninstall.py [--launch NAME]

The citadel/addons search path stays in gameinfo.gi: Deadlock Mod Manager uses it too, and with no
VPKs in the folder it changes nothing.
"""
import sys

from install import GAME, SETTINGS, TARGET, check_target, remove_loose, set_convar, set_launch_options


def remove_vpk():
    addons = GAME / "addons"
    vpk = addons / TARGET
    if not vpk.exists():
        print(f"{TARGET}: not installed")
        return
    check_target(addons)
    try:
        vpk.unlink()
    except PermissionError:
        sys.exit(f"{TARGET} is locked (Deadlock running?); not removed")
    print(f"removed {vpk}")


if __name__ == "__main__":
    remove_vpk()
    remove_loose()
    for name in SETTINGS.get("gameinfo_convars", {}):
        set_convar(name, "")
    set_launch_options(sys.argv[sys.argv.index("--launch") + 1] if "--launch" in sys.argv else "vanilla")
