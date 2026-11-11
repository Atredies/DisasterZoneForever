#!/usr/bin/env bash
# Dev install of DisasterZone into the WoW Forever client, straight from this checkout (a "dev" build: in-game
# updates never apply to it). Game packs are big and optional: name them to include them.
#   dev/install_forever.sh                      # the main addon only
#   dev/install_forever.sh Bingo Chess          # plus DisasterZone_Bingo and DisasterZone_Chess
#   dev/install_forever.sh --remove             # take every DisasterZone folder out again
# Saved data (WTF/.../SavedVariables/DisasterZone*.lua) is never touched. WOW_DIR overrides the client folder.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$HERE/../addon"
WOW="${WOW_DIR:-$HOME/Games/battlenet/drive_c/Program Files (x86)/World of Warcraft}"
ADDONS="$WOW/_forever_/Interface/AddOns"
[ -d "$ADDONS" ] || { echo "No Forever AddOns folder at: $ADDONS (set WOW_DIR)"; exit 1; }
if [ "${1:-}" = "--remove" ]; then
    for d in "$ADDONS"/DisasterZone "$ADDONS"/DisasterZone_*; do [ -e "$d" ] && rm -rf "$d" && echo "removed $d"; done
    exit 0
fi
folders=(DisasterZone)
for p in "$@"; do folders+=("DisasterZone_$p"); done
for f in "${folders[@]}"; do
    [ -d "$SRC/$f" ] || { echo "no such addon folder: $SRC/$f"; exit 1; }
    rsync -a --delete "$SRC/$f/" "$ADDONS/$f/"
    echo "installed $ADDONS/$f"
done
