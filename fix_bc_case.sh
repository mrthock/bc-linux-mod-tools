#!/bin/bash
# fix_bc_case.sh — Merges duplicate case-variant directories in Star Trek: Bridge Commander.
#
# Linux filesystems are case-sensitive; Windows mods assume case-insensitive NTFS.
# This causes broken references when folders like "Ships" and "ships" both exist.
# Run this after installing any mod to merge duplicates into the canonical name.
#
# Usage: ./fix_bc_case.sh [game_dir]
#   game_dir defaults to the STBC_DIR environment variable, then auto-detects
#   common Heroic/Steam install locations.

set -euo pipefail

# ── locate game dir ────────────────────────────────────────────────────────────

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

if [ $# -ge 1 ]; then
    GAME="$1"
elif [ -n "${STBC_DIR:-}" ]; then
    GAME="$STBC_DIR"
else
    GAME=$(find_game_dir)
fi

[ -n "$GAME" ] && [ -f "$GAME/stbc.exe" ] || {
    echo "ERROR: Could not find Bridge Commander install. Set STBC_DIR or pass the path as an argument." >&2
    exit 1
}

echo "Game dir: $GAME"

# ── fix_case <parent> <lower_name> <upper_name> <target_name> ─────────────────
# Merges the smaller directory into the larger one, then renames to target_name.

fix_case() {
    local parent="$1"
    local name_lower="$2"
    local name_upper="$3"
    local target="$4"
    local lower="$parent/$name_lower"
    local upper="$parent/$name_upper"

    if [ -d "$lower" ] && [ -d "$upper" ]; then
        local count_lower count_upper
        count_lower=$(ls "$lower" | wc -l)
        count_upper=$(ls "$upper" | wc -l)
        echo "Found duplicate: $name_lower ($count_lower files) vs $name_upper ($count_upper files)"

        if [ "$count_lower" -ge "$count_upper" ]; then
            echo "  Merging $name_upper -> $name_lower"
            chmod -R u+w "$lower"
            cp -rv "$upper/." "$lower/"
            rm -rf "$upper"
            if [ "$name_lower" != "$target" ]; then
                mv "$lower" "$parent/$target"
                echo "  Renamed to $target"
            fi
        else
            echo "  Merging $name_lower -> $name_upper"
            chmod -R u+w "$upper"
            cp -rv "$lower/." "$upper/"
            rm -rf "$lower"
            if [ "$name_upper" != "$target" ]; then
                mv "$upper" "$parent/$target"
                echo "  Renamed to $target"
            fi
        fi
    fi
}

# ── known case conflict pairs ──────────────────────────────────────────────────

fix_case "$GAME/scripts"              "ships"      "Ships"      "ships"
fix_case "$GAME/scripts"              "custom"     "Custom"     "Custom"
fix_case "$GAME/scripts/ships"        "hardpoints" "Hardpoints" "hardpoints"
fix_case "$GAME/scripts/Custom"       "ships"      "Ships"      "Ships"
fix_case "$GAME/scripts/Custom"       "autoload"   "Autoload"   "Autoload"
fix_case "$GAME/scripts/Custom"       "carriers"   "Carriers"   "Carriers"
fix_case "$GAME/data/Icons"           "ships"      "Ships"      "ships"
fix_case "$GAME/data/Models"          "ships"      "Ships"      "Ships"
fix_case "$GAME/data"                 "models"     "Models"     "Models"
fix_case "$GAME/data"                 "animations" "Animations" "animations"
fix_case "$GAME/data"                 "textures"   "Textures"   "Textures"

echo "All done!"
