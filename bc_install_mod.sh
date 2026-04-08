#!/bin/bash
# bc_install_mod.sh — Install a Star Trek: Bridge Commander ship/mod archive on Linux.
#
# Handles .zip, .rar, .bcmod, and .exe (NSIS/self-extracting) archives.
# Automatically detects KM vs Remastered version subdirectories.
# Takes a Timeshift btrfs snapshot before touching the game (requires sudo).
# Runs fix_bc_case.sh afterwards to resolve Linux case-sensitivity conflicts.
#
# Usage: ./bc_install_mod.sh [--no-snapshot] <archive>
#
# Environment:
#   STBC_DIR        Path to Bridge Commander install (auto-detected if unset)
#   STBC_STAGING    Directory for extracted mod staging (default: ~/BCMods)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STAGING_ROOT="${STBC_STAGING:-$HOME/BCMods}"
SKIP_SNAPSHOT=0

# ── helpers ────────────────────────────────────────────────────────────────────

die()   { echo "ERROR: $*" >&2; exit 1; }

usage() {
    echo "Usage: $0 [--no-snapshot] <archive.zip|.rar|.bcmod|.exe>"
    echo ""
    echo "  --no-snapshot   Skip the Timeshift snapshot (useful when running"
    echo "                  non-interactively or sudo is unavailable)"
    echo ""
    echo "  Environment variables:"
    echo "    STBC_DIR      Path to Bridge Commander install directory"
    echo "    STBC_STAGING  Directory for mod staging (default: ~/BCMods)"
    exit 1
}

find_game_dir() {
    local candidates=(
        "$HOME/Games/Heroic/Star Trek Bridge Commander"
        "$HOME/.steam/steam/steamapps/common/Star Trek Bridge Commander"
        "$HOME/.local/share/Steam/steamapps/common/Star Trek Bridge Commander"
    )
    for d in "${candidates[@]}"; do
        [ -f "$d/stbc.exe" ] && echo "$d" && return
    done
}

copy_dir() {
    local src="$1" dest_name="$2" dest
    dest="$GAME/$dest_name"
    echo "  Copying $(basename "$src") -> $dest_name/"
    mkdir -p "$dest"
    cp -rf "$src/." "$dest/"
}

# ── arguments ─────────────────────────────────────────────────────────────────

[ $# -ge 1 ] || usage

if [ "$1" = "--no-snapshot" ]; then
    SKIP_SNAPSHOT=1
    shift
fi

[ $# -eq 1 ] || usage
ARCHIVE="$1"
[ -f "$ARCHIVE" ] || die "File not found: $ARCHIVE"

# ── locate game ────────────────────────────────────────────────────────────────

if [ -n "${STBC_DIR:-}" ]; then
    GAME="$STBC_DIR"
else
    GAME=$(find_game_dir)
fi
[ -n "$GAME" ] && [ -f "$GAME/stbc.exe" ] || \
    die "Could not find Bridge Commander install. Set STBC_DIR or pass STBC_DIR=<path> before the command."

# ── derive staging dir ─────────────────────────────────────────────────────────

BASENAME=$(basename "$ARCHIVE")
MOD_NAME="${BASENAME%.*}"
MOD_NAME="${MOD_NAME// /_}"
STAGING="$STAGING_ROOT/$MOD_NAME"

echo "=== BC Mod Installer ==="
echo "Archive : $BASENAME"
echo "Game    : $GAME"
echo "Staging : $STAGING"
echo ""

# ── extract ────────────────────────────────────────────────────────────────────

if [ -d "$STAGING" ] && [ "$(ls -A "$STAGING" 2>/dev/null)" ]; then
    echo "Staging directory already exists — skipping extraction."
else
    mkdir -p "$STAGING"
    EXT="${BASENAME##*.}"
    EXT_LOWER="${EXT,,}"
    echo "Extracting..."
    case "$EXT_LOWER" in
        zip)   unzip -o "$ARCHIVE" -d "$STAGING" ;;
        rar)   unrar x -o+ "$ARCHIVE" "$STAGING/" ;;
        bcmod) python3 "$SCRIPT_DIR/bcmod_extract.py" "$ARCHIVE" "$STAGING/extracted" ;;
        exe)   7z x "$ARCHIVE" -o"$STAGING" ;;         # NSIS / self-extracting
        *)     bsdtar -xf "$ARCHIVE" -C "$STAGING" ;;  # fallback (tar.gz, 7z, etc.)
    esac
    echo "Extraction complete."
fi
echo ""

# ── find content root (handles KM / Remastered subdirs) ───────────────────────

mapfile -t KM_DIRS < <(find "$STAGING" -maxdepth 4 -type d -iname "km version"        2>/dev/null)
mapfile -t RM_DIRS < <(find "$STAGING" -maxdepth 4 -type d -iname "remastered version" 2>/dev/null)

if [ ${#KM_DIRS[@]} -gt 0 ] && [ ${#RM_DIRS[@]} -gt 0 ]; then
    echo "Multiple versions detected:"
    echo "  1) KM Version         (${KM_DIRS[0]})"
    echo "  2) Remastered Version (${RM_DIRS[0]})"
    read -rp "Which version to install? [1/2]: " VER_CHOICE
    case "$VER_CHOICE" in
        1) CONTENT_ROOT="${KM_DIRS[0]}" ;;
        2) CONTENT_ROOT="${RM_DIRS[0]}" ;;
        *) die "Invalid choice." ;;
    esac
elif [ ${#RM_DIRS[@]} -gt 0 ]; then
    echo "Remastered Version detected — using it."
    CONTENT_ROOT="${RM_DIRS[0]}"
elif [ ${#KM_DIRS[@]} -gt 0 ]; then
    echo "KM Version detected — using it."
    CONTENT_ROOT="${KM_DIRS[0]}"
else
    FIRST_HIT=$(find "$STAGING" -maxdepth 4 -type d \
        \( -iname "data" -o -iname "scripts" -o -iname "sfx" \) | head -1)
    [ -n "$FIRST_HIT" ] || die "Could not find data/scripts/sfx inside the archive."
    CONTENT_ROOT=$(dirname "$FIRST_HIT")
    echo "Content root: $CONTENT_ROOT"
fi
echo ""

# ── timeshift snapshot ─────────────────────────────────────────────────────────

if [ "$SKIP_SNAPSHOT" -eq 1 ]; then
    echo "=== Skipping Timeshift snapshot ==="
else
    echo "=== Creating Timeshift snapshot ==="
    sudo timeshift --create --comments "BC mod install: $MOD_NAME" --tags O
fi
echo ""

# ── copy mod files into game ───────────────────────────────────────────────────

echo "=== Copying mod files to game ==="

INSTALLED_ANY=0
for dir_name in data Data scripts Scripts sfx SFX py; do
    candidate="$CONTENT_ROOT/$dir_name"
    if [ -d "$candidate" ]; then
        copy_dir "$candidate" "${dir_name,,}"
        INSTALLED_ANY=1
    fi
done

[ "$INSTALLED_ANY" -eq 1 ] || die "No data/scripts/sfx/py directories found under $CONTENT_ROOT"
echo ""

# ── case fix ──────────────────────────────────────────────────────────────────

echo "=== Running case fix ==="
bash "$SCRIPT_DIR/fix_bc_case.sh" "$GAME"

echo ""
echo "Done! '$MOD_NAME' installed."
