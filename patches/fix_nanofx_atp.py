#!/usr/bin/env python3
"""
fix_nanofx_atp.py — Fixes NanoFX 2.0 + Advanced Technologies Plugin crashes on BC Remastered.

Two bugs fixed:

  1. ATP_Wrapper.py — Missing Redirect function
     ATP_Wrapper.AddHandler() registers "...ATP_Wrapper.Redirect" as a global broadcast
     event handler so that per-instance Python method handlers fire correctly. But the
     Redirect function was never written, causing:

       AttributeError: Redirect          (console interrupt on every WC ship)
       TypeError: call of non-function    (BC's fallback resolution calling the module)

     Fix: adds the Redirect function and guards the Node.SetDeleteMe call in delete()
     against use-after-free.

  2. BlinkerFX.py — Hard crash on ship explosion (use-after-free)
     BlinkerContainer.Swap() ran on a timer every 0.15–2.0s and called
     self.Node.IsHidden(). When a ship exploded, BC freed the C++ node but the timer
     kept firing — accessing freed memory causes a hard crash that Python cannot catch.
     Also, ET_OBJECT_DESTROYED was registered globally so DeleteContainer fired on ALL
     BlinkerContainers when ANY ship died, and DeleteContainer had AddHandler instead of
     RemoveHandler (re-registered the handler instead of cleaning it up).

     Fix: store ShipID, re-validate ship is alive via GetObjectByID in Swap before
     touching the node, remove ET_OBJECT_DESTROYED handler (Swap handles cleanup
     naturally), fix DeleteContainer to properly clean up.

Run once after installing NanoFX 2.0 beta + any mod using the Advanced Technologies Plugin
(e.g. Wiley Coyote Fleet Megapack).

Usage: python3 fix_nanofx_atp.py [game_dir]
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


def backup_and_write(path, data):
    backup = path + '.bak'
    if not os.path.isfile(backup):
        shutil.copy2(path, backup)
        print(f"  Backup saved: {os.path.basename(backup)}")
    open(path, 'wb').write(data.encode('latin-1'))
    pyc = path + 'c'
    if os.path.isfile(pyc):
        os.remove(pyc)
        print(f"  Removed stale {os.path.basename(pyc)}")


def patch_atp_wrapper(game_dir):
    path = os.path.join(game_dir, 'scripts', 'Custom', 'AdvancedTechnologies',
                        'Data', 'ATP_Wrapper.py')
    if not os.path.isfile(path):
        print("  SKIP: ATP_Wrapper.py not found (ATP not installed).")
        return

    data = open(path, 'rb').read().decode('latin-1').replace('\r\n', '\n').replace('\r', '\n')
    changed = False

    # ── Fix 1: add missing Redirect function ──────────────────────────────────
    REDIRECT_MARKER = 'def Redirect(pObject, pEvent):'
    REDIRECT_FUNC = (
        'def Redirect(pObject, pEvent):\n'
        '\t# Routes global broadcast events to each registered ATP_Wrapper instance.\n'
        '\t# Registered as the broadcast handler by AddHandler() so that per-instance\n'
        '\t# Python method handlers (registered on self.Wrapper) actually fire.\n'
        '\teventType = pEvent.GetEventType()\n'
        '\tEventDict = ATP_Wrapper.EventDict\n'
        '\tif not EventDict.has_key(eventType):\n'
        '\t\treturn\n'
        '\tfor Wrapper in EventDict[eventType][:]:\n'
        '\t\tpNewEvent = App.TGEvent_Create()\n'
        '\t\tpNewEvent.SetEventType(eventType)\n'
        '\t\tpNewEvent.SetDestination(Wrapper)\n'
        '\t\tApp.g_kEventManager.AddEvent(pNewEvent)\n'
        '\n'
    )

    if REDIRECT_MARKER in data:
        print("  Redirect function already present — skipping.")
    else:
        # Insert Redirect before the class definition
        CLASS_MARKER = 'class ATP_Wrapper:'
        if CLASS_MARKER in data:
            data = data.replace(CLASS_MARKER, REDIRECT_FUNC + CLASS_MARKER, 1)
            print("  Added missing Redirect function.")
            changed = True
        else:
            print("  WARNING: Could not find ATP_Wrapper class to insert Redirect before.")

    # ── Fix 2: guard Node.SetDeleteMe in delete() against use-after-free ──────
    OLD_DELETE_NODE = (
        '\t\tif self.Node:\n'
        '\t\t\tif self.Node.IsTypeOf(App.CT_BASE_OBJECT):\n'
        '\t\t\t\tself.Node.SetDeleteMe(TRUE)\n'
    )
    NEW_DELETE_NODE = (
        '\t\tif self.Node:\n'
        '\t\t\ttry:\n'
        '\t\t\t\tif self.Node.IsTypeOf(App.CT_BASE_OBJECT):\n'
        '\t\t\t\t\tself.Node.SetDeleteMe(TRUE)\n'
        '\t\t\texcept:\n'
        '\t\t\t\tpass\n'
    )

    if NEW_DELETE_NODE in data:
        print("  Node.SetDeleteMe guard already applied — skipping.")
    elif OLD_DELETE_NODE in data:
        data = data.replace(OLD_DELETE_NODE, NEW_DELETE_NODE, 1)
        print("  Guarded Node.SetDeleteMe against use-after-free.")
        changed = True
    else:
        print("  WARNING: Could not find Node.SetDeleteMe block to patch.")

    if changed:
        backup_and_write(path, data)
        print("  Wrote patched ATP_Wrapper.py")
    else:
        print("  No changes made to ATP_Wrapper.py.")


def patch_blinkerfx(game_dir):
    path = os.path.join(game_dir, 'scripts', 'Custom', 'NanoFXv2',
                        'SpecialFX', 'BlinkerFX.py')
    if not os.path.isfile(path):
        print("  SKIP: BlinkerFX.py not found (NanoFX not installed).")
        return

    data = open(path, 'rb').read().decode('latin-1').replace('\r\n', '\n').replace('\r', '\n')
    changed = False

    # ── Fix: replace BlinkerContainer with safe version ───────────────────────
    # Match the original class (handles both pre-fix and post-fix states).
    OLD_SETNODE_CALL = '\tpContainer.SetNode(kBlinkers)\n'
    NEW_SETNODE_CALL = '\tpContainer.SetNode(kBlinkers, pShip)\n'

    OLD_CLASS = (
        'from Custom.AdvancedTechnologies.Data.ATP_Wrapper import *\n'
        'class BlinkerContainer(ATP_Wrapper):\n'
        '\tdef __init__(self):\n'
        '\t\tATP_Wrapper.__init__(self)\n'
        '\t\tself.Node = None\n'
        '\n'
        '\tdef SetNode(self,Node):\n'
        '\t\tself.Node = Node\n'
        '\t\tself.RemoveClock("Swap")\n'
        '\t\tself.AddClock("Swap", 0.15)\n'
        '\t\t\n'
        '\t\tself.AddHandler(App.ET_EXIT_GAME, "DeleteContainer")\n'
        '\t\tself.AddHandler(App.ET_OBJECT_DESTROYED, "DeleteContainer")\n'
        '\t\t\n'
        '\tdef Swap(self, pEvent):\n'
        '\t\tif self.Node:\n'
        '\t\t\tif self.Node.IsHidden():\n'
        '\t\t\t\tself.Node.SetHidden(FALSE)\n'
        '\t\t\t\tself.RemoveClock("Swap")\n'
        '\t\t\t\tself.AddClock("Swap", 0.20)\n'
        '\t\t\telse:\n'
        '\t\t\t\tself.Node.SetHidden(TRUE)\n'
        '\t\t\t\tself.RemoveClock("Swap")\n'
        '\t\t\t\tself.AddClock("Swap", 2.0)\t\n'
        '\t\t\t\t\n'
        '\tdef DeleteContainer(self, pEvent):\n'
        '\t\t#self.AddHandler(App.ET_EXIT_GAME, "DeleteContainer")\n'
        '\t\tself.AddHandler(App.ET_OBJECT_DESTROYED, "DeleteContainer")\n'
        '\t\tself.Node.SetDeleteMe(1)\n'
        '\t\tself.delete()\n'
    )

    NEW_CLASS = (
        'from Custom.AdvancedTechnologies.Data.ATP_Wrapper import *\n'
        'class BlinkerContainer(ATP_Wrapper):\n'
        '\tdef __init__(self):\n'
        '\t\tATP_Wrapper.__init__(self)\n'
        '\t\tself.Node = None\n'
        '\t\tself.ShipID = None\n'
        '\n'
        '\tdef SetNode(self, Node, pShip):\n'
        '\t\tself.Node = Node\n'
        '\t\tself.ShipID = pShip.GetObjID()\n'
        '\t\tself.RemoveClock("Swap")\n'
        '\t\tself.AddClock("Swap", 0.15)\n'
        '\t\tself.AddHandler(App.ET_EXIT_GAME, "DeleteContainer")\n'
        '\n'
        '\tdef Swap(self, pEvent):\n'
        '\t\tif self.ShipID is None:\n'
        '\t\t\treturn\n'
        '\t\t# Re-validate the ship is still alive before touching the node.\n'
        '\t\t# Accessing a freed C++ node directly causes a hard crash.\n'
        '\t\tpShip = App.ShipClass_GetObjectByID(App.SetClass_GetNull(), self.ShipID)\n'
        '\t\tif not pShip or pShip.IsDead():\n'
        '\t\t\tself.Node = None\n'
        '\t\t\tself.ShipID = None\n'
        '\t\t\tself.delete()\n'
        '\t\t\treturn\n'
        '\t\tif self.Node.IsHidden():\n'
        '\t\t\tself.Node.SetHidden(FALSE)\n'
        '\t\t\tself.RemoveClock("Swap")\n'
        '\t\t\tself.AddClock("Swap", 0.20)\n'
        '\t\telse:\n'
        '\t\t\tself.Node.SetHidden(TRUE)\n'
        '\t\t\tself.RemoveClock("Swap")\n'
        '\t\t\tself.AddClock("Swap", 2.0)\n'
        '\n'
        '\tdef DeleteContainer(self, pEvent):\n'
        '\t\tself.RemoveHandler(App.ET_EXIT_GAME, "DeleteContainer")\n'
        '\t\tself.Node = None\n'
        '\t\tself.ShipID = None\n'
        '\t\tself.delete()\n'
    )

    ALREADY_PATCHED = 'self.ShipID = None'

    if ALREADY_PATCHED in data:
        print("  BlinkerContainer already patched — skipping.")
    elif OLD_CLASS in data:
        data = data.replace(OLD_SETNODE_CALL, NEW_SETNODE_CALL, 1)
        data = data.replace(OLD_CLASS, NEW_CLASS, 1)
        print("  Patched BlinkerContainer (use-after-free fix).")
        changed = True
    else:
        print("  WARNING: Could not match BlinkerContainer class (line endings may differ).")

    if changed:
        backup_and_write(path, data)
        print("  Wrote patched BlinkerFX.py")
    else:
        print("  No changes made to BlinkerFX.py.")


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
    print()
    print("Patching ATP_Wrapper.py...")
    patch_atp_wrapper(game_dir)
    print()
    print("Patching BlinkerFX.py...")
    patch_blinkerfx(game_dir)
