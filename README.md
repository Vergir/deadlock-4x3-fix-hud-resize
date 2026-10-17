# Deadlock narrow-display HUD fix

Data-only Panorama addon (CSS + two tiny layouts + one script) that fixes Deadlock's HUD on
displays narrower than 16:10, such as the LG DualUp in landscape (2880x2560, 9:8).
No code injection, no memory patching, nothing the stock UI hides is revealed.

## The problem

On any screen narrower than 16:10 the engine tags the UI root `AspectRatio4x3`, lays the UI
out on a 1440x1080 canvas and stretches that canvas to the screen. On 2880x2560 that is an
X scale of 2.00 and a Y scale of 2.37, so everything is 18% too tall and far too large, and
panels positioned as "centered, then offset by a fixed 1290px" fall off-screen because the
canvas is much narrower than the 1920px the 16:9 layout assumes.

## The fix

`src/panorama/scripts/narrowhud.vts` runs inside both UI trees (in-game HUD and main menu).
It reads the root's real X/Y scale and pixel size, then sets `ui-scale` on the root's
top-level containers so the UI becomes uniform (un-stretched) and as large as a 16:9 screen
of the same width would get, times a `UI_SIZE` factor baked in at build time. The containers
are enlarged by the inverse so they still cover the screen.

On screens the engine does not stretch (16:9, 16:10, 21:9) the script keeps the engine's own
canvas, so size 1.0 changes nothing there and the other sizes simply scale the vanilla HUD
(checked in game on 16:9 and 16:10; 21:9 untested).

`src/panorama/styles/npc_icons.css` carries the one layout fix that is plain CSS: the health
bar, anchored to the left edge at its exact vanilla position (315 on a 1920 canvas, 199.5 on
16:10's 1728 canvas) instead of "centered, then offset by a fixed margin", which drifts onto the
stat circles when the canvas is narrower.

The script is hosted by overriding two small, always-present layouts
(`hud_data_feed.xml`, `citadel_dashboard_footer_bar.xml`), which only add a `<scripts>`
include; small files survive game patches better than the 4000-line `hud.vcss`.

## Build

```bash
pip install vpk
python build.py --ui-size 1.0 --hud-aspect 1:1   # -> build/mod/pak01_dir.vpk
python install.py                                # copy into the game + fix gameinfo.gi
python release.py                                # zips for several sizes in build/dist/
```

`--ui-size` scales the whole HUD (0.8 smaller ... 1.2 larger). `--hud-aspect 1:1` confines the
HUD to the largest centered 1:1 (or any W:H) region of the screen (the Esc menu's dark backdrop
still covers the whole screen; its contents stay in the region). `--test` keeps an on-screen
debug label with the measured scales. Without arguments, build.py reads `local_settings.json`.

No Valve SDK is needed: `build.py` writes the compiled resource containers itself
(stylesheets and layouts in the legacy plain-text form, scripts as plain text).

## Install (end users)

See `INSTALL.txt` (shipped in each zip). In short: vpk into `game/citadel/addons/`,
`Mod citadel` / `Write citadel` / `Game citadel/addons` lines in `gameinfo.gi`, resolution via
Steam launch options (`-w 2880 -h 2560`), restart the game.

## Panorama scripting notes (learned the hard way)

- Containers are sized with absolute `px` in their own scaled units and positioned with symmetric
  margins. Percent widths above 100% and `style.horizontalAlign` are not reliable from script.
- `BIsVisible` does not exist in Deadlock's JS; `actuallayoutwidth/height`, `actualxoffset/yoffset`,
  `actualuiscale_x/y`, `FindChild(Traverse)`, `BHasClass`, `$.CreatePanel`, `$.Schedule` do.
- A runtime-created `CitadelSettingsSlider` never receives its convar value; there is no convar
  or storage API for scripts.

## Known limits

- Resolution and aspect ratio cannot be made selectable in Video settings: the game's aspect
  handler has four buckets (16:9, 16:10, 21:9, and a hidden `CitadelSetAspectRatio(3)` that
  covers 4:3 and 5:4), none of them 9:8, and the engine ignores an unlisted mode saved in
  `video.txt`, so launch options stay the way to set a narrow resolution.
- No in-game UI Size slider. A runtime slider works for live preview (convar-bound
  `CitadelSettingsSlider` with `updateonvaluechange`), but nothing the UI can write survives
  a restart without hijacking a game convar, and convars come and go with patches, so the
  size is a build-time option instead (prebuilt variants in `build/dist/`).
- The game's live config (`machine_convars.vcfg`, `video.txt`) lives under
  `Steam/userdata/<id>/1422450/local/cfg/`, not in the game folder.
- Game updates overwrite `gameinfo.gi`; re-run `install.py` (or re-add the lines).

## Repository layout

- `src/panorama/` – mod sources (templates; `{{UI_SIZE}}`, `{{DEBUG}}` etc. filled by build.py)
- `build.py`, `xml2laco.py`, `install.py`, `release.py` – tooling
- `extracted/` – decompiled vanilla UI for reference (not shipped)
- `tools/vrf-cli/` – Source 2 Viewer CLI used for extraction
- `ref/` – other open-source Deadlock HUD mods, for reference
- `gameinfo.gi.backup-original`, `video.txt.backup-original` – untouched copies of game configs
