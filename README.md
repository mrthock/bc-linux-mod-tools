# BC Linux Mod Tools

Tools for installing and fixing mods for **Star Trek: Bridge Commander** on Linux (via Heroic Games Launcher or Steam/Proton).

Linux filesystems are case-sensitive; Windows mods assume they are not. These scripts handle the resulting conflicts automatically and fix several known compatibility issues between KM-era mods and BC Remastered.

---

## Requirements

| Tool | Purpose |
|------|---------|
| `unzip` | Extract `.zip` archives |
| `unrar` | Extract `.rar` archives |
| `bsdtar` | Fallback extractor (tar, gz, etc.) |
| `7zip` | Extract `.exe` self-installing mods |
| `python3` | Run the BCMod extractor and Foundation patcher |
| `timeshift` | btrfs snapshot before each install (optional) |

Install on Arch/Manjaro:
```bash
sudo pacman -S unzip unrar bsdtar 7zip python timeshift
```

Install on Ubuntu/Debian:
```bash
sudo apt install unzip unrar libarchive-tools 7zip python3 timeshift
```

---

## Setup

Clone the repo and make the scripts executable:

```bash
git clone https://github.com/mrthock/bc-linux-mod-tools.git
cd bc-linux-mod-tools
chmod +x bc_install_mod.sh fix_bc_case.sh
```

The scripts auto-detect Bridge Commander at these locations:
- `~/Games/Heroic/Star Trek Bridge Commander` (Heroic)
- `~/.steam/steam/steamapps/common/Star Trek Bridge Commander` (Steam)

If your install is elsewhere, set `STBC_DIR`:
```bash
export STBC_DIR="/path/to/Star Trek Bridge Commander"
```

---

## Usage

### Install a mod

```bash
./bc_install_mod.sh ~/Downloads/somemod.zip
./bc_install_mod.sh ~/Downloads/somemod.rar
./bc_install_mod.sh ~/Downloads/somemod.BCMod
./bc_install_mod.sh ~/Downloads/somemod.exe
```

What it does:
1. Extracts the archive to `~/BCMods/<mod-name>/` (skips if already extracted)
2. Detects KM vs Remastered version subdirs — prompts if both are present
3. Creates a **Timeshift btrfs snapshot** before touching the game, if Timeshift is installed (requires sudo)
4. Copies `data/`, `scripts/`, `sfx/`, `py/` into the game directory (lowercased)
5. Runs `fix_bc_case.sh` to merge any duplicate case-variant folders

Timeshift snapshots are skipped automatically if Timeshift isn't installed. To force-skip even when it is installed:
```bash
./bc_install_mod.sh --no-snapshot ~/Downloads/somemod.zip
```

To roll back a bad mod install:
```bash
sudo timeshift --restore
```

### Fix case conflicts only

```bash
./fix_bc_case.sh
# or with explicit path:
./fix_bc_case.sh "/path/to/Star Trek Bridge Commander"
```

Run this any time after manually copying mod files.

---

## Known Issues & Fixes

### NanoFX 2.0 + BC Remastered: Foundation version conflict

**Symptom:** After installing NanoFX 2.0, Quick Battle fails with:
```
KeyError: GalaxyBridge
AttributeError: BridgeSetLocation
```

**Cause:** BC Remastered ships `Foundation.py` version `20020525`. NanoFX's autoload
scripts only apply their compatibility patches when Foundation version > `20030221`,
so on a stock Remastered install they silently skip — leaving bridge lookups broken.

**Fix:** Run the included patcher once after installing NanoFX:
```bash
python3 patches/fix_foundation.py
```

This bumps Foundation's version string to `20030222` and patches `BridgeDef` to
register bridges by their bridge string (e.g. `GalaxyBridge`) in addition to their
short name (`Galaxy`), which is what `Fixes20030217.py` expects.

---

### KM mod scripts: bare `DISRUPTOR` / `PHOTON` constants

**Symptom:** Python debug console shows:
```
AttributeError: DISRUPTOR
AttributeError: PHOTON
```

**Cause:** KM-era projectile scripts use bare constants (`DISRUPTOR`, `PHOTON`) that
BC Remastered renamed to numbered variants (`DISRUPTOR1`, `PHOTON1`, etc.).

**Fix:** In any affected `.py` file under `scripts/Tactical/Projectiles/`, replace:
```python
Multiplayer.SpeciesToTorp.DISRUPTOR   →   Multiplayer.SpeciesToTorp.DISRUPTOR1
Multiplayer.SpeciesToTorp.PHOTON      →   Multiplayer.SpeciesToTorp.PHOTON1
```

For a whole mod folder at once:
```bash
PROJ="path/to/scripts/Tactical/Projectiles"
sed -i 's/SpeciesToTorp\.DISRUPTOR)/SpeciesToTorp.DISRUPTOR1)/g' "$PROJ"/*.py
sed -i 's/SpeciesToTorp\.PHOTON)/SpeciesToTorp.PHOTON1)/g'      "$PROJ"/*.py
```

---

### KM weapon textures cause white squares in space

**Symptom:** White opaque boxes appear in space during combat, attached to ships.

**Cause 1 — Duplicate texture folders:** KM mods install to `data/textures/` (lowercase)
while BC Remastered uses `data/Textures/` (capital T). On Linux both exist simultaneously;
the game reads one, ignores the other, and KM alpha formats render as white blocks.

`fix_bc_case.sh` handles this automatically by merging the two folders (Remastered
files win on conflicts).

**Cause 2 — Missing NanoFXv2:** Ship mods that use NanoFXv2 for nav light / blinker
effects will show white squares if NanoFXv2 isn't installed. Install NanoFX first:
[NanoFX 2.0 on GameFront](https://www.gamefront.com/games/bridge-commander/file/nanofx)

---

### `.BCMod` format (BC Mod Packager)

Some older mods ship as `.BCMod` files (created by "BC - Mod Packager BETA v4.4").
`bc_install_mod.sh` handles these transparently via `bcmod_extract.py`.

You can also extract a `.BCMod` manually:
```bash
python3 bcmod_extract.py somemod.BCMod output/
```

**Format notes** (for the curious): The file begins with a plain-text header and
table of contents (one Windows path per line, terminated by `;`). Binary file
contents follow, separated by `\r\n===Next File===\r\n`. Foundation files are
automatically skipped during extraction to prevent old 2004 versions from
overwriting BC Remastered's.

---

## File Overview

| File | Description |
|------|-------------|
| `bc_install_mod.sh` | Main mod installer |
| `fix_bc_case.sh` | Merges duplicate case-variant directories |
| `bcmod_extract.py` | Extracts `.BCMod` archives |
| `patches/fix_foundation.py` | Patches Foundation.py for NanoFX compatibility |

---

## Contributing

If you find new case conflicts, broken constants, or other mod compatibility issues,
PRs and issues are welcome.
