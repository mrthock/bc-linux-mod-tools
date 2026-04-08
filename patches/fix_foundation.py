#!/usr/bin/env python3
"""
fix_foundation.py — Patches Foundation.py in BC Remastered for NanoFX 2.0 compatibility.

BC Remastered ships Foundation.py version '20020525'. NanoFX 2.0 beta's autoload
scripts only apply their compatibility patches when Foundation version > '20030221',
so on a stock Remastered install they silently do nothing — causing:

  KeyError: GalaxyBridge       (bridge lookup by string fails)
  AttributeError: BridgeSetLocation  (function never installed)

This script applies two fixes directly to Foundation.py:

  1. Bumps the version string to '20030222' so NanoFX's autoload patches fire.
  2. Adds bridgeList._keyList[bridgeString] registration to BridgeDef.__init__
     so bridges can be looked up by their bridge string as well as their name.

Run once after installing NanoFX 2.0 (or any mod that ships with NanoFX scripts).

Usage: python3 fix_foundation.py [game_dir]
"""

import sys
import os
import shutil

def find_game_dir():
    home = os.path.expanduser('~')
    candidates = [
        os.path.join(home, 'Games', 'Heroic', 'Star Trek Bridge Commander'),
        os.path.join(home, '.steam', 'steam', 'steamapps', 'common', 'Star Trek Bridge Commander'),
        os.path.join(home, '.local', 'share', 'Steam', 'steamapps', 'common', 'Star Trek Bridge Commander'),
    ]
    for d in candidates:
        if os.path.isfile(os.path.join(d, 'stbc.exe')):
            return d
    return None


def patch_foundation(game_dir):
    foundation = os.path.join(game_dir, 'scripts', 'Foundation.py')
    foundation_pyc = foundation + 'c'

    if not os.path.isfile(foundation):
        print(f"ERROR: Foundation.py not found at {foundation}")
        sys.exit(1)

    data = open(foundation, 'rb').read().decode('latin-1')
    changed = False

    # ── Fix 1: bump version so NanoFX autoload patches fire ───────────────────
    OLD_VERSION = "version = '20020525'"
    NEW_VERSION = "version = '20030222'"
    if OLD_VERSION in data:
        data = data.replace(OLD_VERSION, NEW_VERSION, 1)
        print(f"  Bumped Foundation version: 20020525 -> 20030222")
        changed = True
    elif NEW_VERSION in data:
        print(f"  Foundation version already at 20030222 — skipping.")
    else:
        print(f"  WARNING: Could not find version string to patch.")

    # ── Fix 2: register bridge by bridgeString as well as name ────────────────
    # BridgeDef.__init__ only registers by name ('Galaxy'), but NanoFX's
    # Fixes20030217.py looks bridges up by bridgeString ('GalaxyBridge').
    # The double \r is how BC Remastered Foundation.py stores line endings.
    OLD_BRIDGEDEF = (
        '\t\tself.num = bridgeList.Register(self, name)\r\r\n'
        '\t\tMutatorElementDef.__init__(self, name, dict)'
    )
    NEW_BRIDGEDEF = (
        '\t\tself.num = bridgeList.Register(self, name)\r\r\n'
        '\t\tbridgeList._keyList[bridgeString] = self\r\r\n'
        '\t\tMutatorElementDef.__init__(self, name, dict)'
    )
    if OLD_BRIDGEDEF in data:
        data = data.replace(OLD_BRIDGEDEF, NEW_BRIDGEDEF, 1)
        print(f"  Patched BridgeDef to register by bridgeString.")
        changed = True
    elif NEW_BRIDGEDEF in data:
        print(f"  BridgeDef bridgeString patch already applied — skipping.")
    else:
        print(f"  WARNING: Could not find BridgeDef.__init__ to patch (line endings may differ).")

    if changed:
        # Back up original
        backup = foundation + '.bak'
        if not os.path.isfile(backup):
            shutil.copy2(foundation, backup)
            print(f"  Backup saved: Foundation.py.bak")

        open(foundation, 'wb').write(data.encode('latin-1'))
        print(f"  Wrote patched Foundation.py")

        # Remove stale bytecode so Python recompiles from the patched source
        if os.path.isfile(foundation_pyc):
            os.remove(foundation_pyc)
            print(f"  Removed stale Foundation.pyc")
    else:
        print("  No changes made.")


if __name__ == '__main__':
    if len(sys.argv) >= 2:
        game_dir = sys.argv[1]
    elif 'STBC_DIR' in os.environ:
        game_dir = os.environ['STBC_DIR']
    else:
        game_dir = find_game_dir()

    if not game_dir or not os.path.isfile(os.path.join(game_dir, 'stbc.exe')):
        print("ERROR: Could not find Bridge Commander install.")
        print("Set STBC_DIR or pass the path as an argument.")
        sys.exit(1)

    print(f"Game dir: {game_dir}")
    patch_foundation(game_dir)
