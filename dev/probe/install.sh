#!/usr/bin/env bash
# Copy DZProbe into the WoW Forever AddOns folder (replacing an older copy). Remove it with: install.sh --remove
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
WOW="${WOW_DIR:-$HOME/Games/battlenet/drive_c/Program Files (x86)/World of Warcraft}"
ADDONS="$WOW/_forever_/Interface/AddOns"
[ -d "$ADDONS" ] || { echo "No Forever AddOns folder at: $ADDONS (set WOW_DIR)"; exit 1; }
rm -rf "$ADDONS/DZProbe"
if [ "${1:-}" = "--remove" ]; then echo "removed $ADDONS/DZProbe"; exit 0; fi
python3 "$HERE/gen_apilist.py"
cp -r "$HERE/DZProbe" "$ADDONS/DZProbe"
echo "installed $ADDONS/DZProbe"
