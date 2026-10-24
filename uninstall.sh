#!/usr/bin/env bash
# linguist entfernen. Geladene Wörterbücher (~/.local/share/linguist/dict) gehen mit – notist hat eigene.
set -euo pipefail
RICE="$HOME/.local/share/rice-apps"
"$HOME/.local/bin/linguist" --quit 2>/dev/null || true
pkill -u "$(id -u)" -f "share/linguist/linguist.py" 2>/dev/null || true
rm -rf "$HOME/.local/share/linguist"
rm -f "$HOME/.local/bin/linguist" "$HOME/.local/share/applications/linguist.desktop" \
      "$HOME/.local/share/icons/hicolor/scalable/apps/linguist.svg" "$HOME/.config/autostart/linguist.desktop"
# gemeinsame Bausteine nur entfernen, wenn keine andere Suite-App sie noch braucht
if [ ! -d "$RICE/calendar" ] && [ ! -d "$RICE/music" ] && [ ! -d "$HOME/.local/share/mailist" ] \
   && [ ! -d "$HOME/.local/share/wallist" ] && [ ! -d "$HOME/.local/share/sharist" ]; then
    rm -rf "$RICE/fonts" "$RICE/tui.py" "$RICE/glass.py" "$RICE/changelog.py" "$RICE/swipe.py" "$RICE/__pycache__"
    rmdir "$RICE" 2>/dev/null || true
fi
echo "linguist entfernt (Einstellungen: ~/.config/linguist)."
