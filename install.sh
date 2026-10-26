#!/usr/bin/env bash
# linguist installieren (ins eigene Benutzerverzeichnis, root nur für Systempakete).
#   ./install.sh            normal (fragt nach Systempaketen und Autostart)
#   ./install.sh --update   ohne Rückfragen (von update.sh)
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SRC/pkg.sh"
DIR="$HOME/.local/share/linguist"
RICE="$HOME/.local/share/rice-apps"
BIN="$HOME/.local/bin"
APPS="$HOME/.local/share/applications"
ICONS="$HOME/.local/share/icons/hicolor/scalable/apps"
UPDATE=0; [[ "${1:-}" == "--update" ]] && UPDATE=1

say "== linguist installieren =="
basics_missing() {
    python3 -c 'import gi, cairo; gi.require_version("Gtk", "4.0")' 2>/dev/null && return 1
    return 0
}
if { (( UPDATE )) && basics_missing && say "Es fehlen Systempakete – werden nachinstalliert …"; } \
   || ask "Systempakete installieren (GTK4, PyGObject, gtk4-layer-shell für die Bildschirmecke, wl-clipboard)?"; then
    pkg_install \
        "gtk4 gtk4-layer-shell python python-gobject python-cairo adwaita-icon-theme xdg-utils wl-clipboard" \
        "python3 python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-gtk4layershell-1.0 libgtk4-layer-shell0 adwaita-icon-theme xdg-utils libglib2.0-bin wl-clipboard" \
        "python3 python3-gobject python3-cairo gtk4 gtk4-layer-shell adwaita-icon-theme xdg-utils glib2 wl-clipboard" \
        "python3 python3-gobject python3-gobject-cairo python3-gobject-Gdk typelib-1_0-Gtk-4_0 typelib-1_0-Gtk4LayerShell-1_0 adwaita-icon-theme xdg-utils glib2-tools wl-clipboard" \
        || warn "Paketinstallation nicht vollständig – weiter."
fi
echo

say "Kopiere linguist nach $DIR …"
mkdir -p "$DIR" "$RICE/fonts" "$BIN" "$APPS" "$ICONS"
cp -f "$SRC"/app/linguist/*.py "$SRC"/app/linguist/VERSION "$SRC"/app/linguist/CHANGELOG.md "$DIR/"
install -m 755 "$SRC/linguist.sh" "$DIR/linguist.sh"
chmod +x "$DIR/linguist.py"
cp -f "$SRC/app/tui.py" "$SRC/app/glass.py" "$SRC/app/istheme.py" "$SRC/app/changelog.py" "$SRC/app/swipe.py" "$RICE/"   # gemeinsame Bausteine
cp -f "$SRC"/app/fonts/* "$RICE/fonts/"                           # Symbolschrift (Icons ohne Nerd Font)
ln -sf "$DIR/linguist.sh" "$BIN/linguist"
sed "s|@EXEC@|$BIN/linguist|g" "$SRC/linguist.desktop.in" > "$APPS/linguist.desktop"
cp -f "$SRC/linguist.svg" "$ICONS/linguist.svg"
refresh_desktop

if (( ! UPDATE )); then
    echo
    if ask "linguist beim Anmelden unsichtbar starten? (nötig für den Hover-Übersetzer in der Bildschirmecke)"; then
        mkdir -p "$HOME/.config/autostart"
        sed -e "s|@EXEC@ %F|$BIN/linguist --daemon|" -e "s|^Name=linguist|Name=linguist (Hintergrund)|" \
            "$SRC/linguist.desktop.in" > "$HOME/.config/autostart/linguist.desktop"
        echo "  Autostart: ~/.config/autostart/linguist.desktop"
        echo "  (Hyprland/Sway lesen den Ordner nicht – dort selbst eintragen:  exec-once = linguist --daemon)"
    fi
fi
# läuft linguist schon im Hintergrund? → neu starten, damit der neue Code gilt
if gdbus call --session --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus \
     --method org.freedesktop.DBus.NameHasOwner de.invincible.Linguist 2>/dev/null | grep -q true; then
    "$BIN/linguist" --quit; sleep 1.5; "$BIN/linguist" --daemon
fi

echo
say "Prüfe …"
check_gtk || warn "Ohne passendes GTK startet linguist nicht – siehe README."
python3 -c 'import gi, cairo; gi.require_version("Gtk", "4.0")' 2>/dev/null && echo "  PyGObject/cairo: ok" \
    || warn "  PyGObject oder pycairo fehlt"
python3 - <<'PY'
try:
    import gi
    gi.require_version("Gtk4LayerShell", "1.0")
    print("  Hover-Ecke (gtk4-layer-shell): möglich – in den Einstellungen einschaltbar")
except (ImportError, ValueError):
    print("  Hover-Ecke: nicht verfügbar (gtk4-layer-shell fehlt) – Fenster und Karte per Befehl gehen trotzdem")
PY
command -v wl-paste >/dev/null && echo "  wl-clipboard: vorhanden (linguist --selection)" \
    || echo "  wl-clipboard: fehlt – optional, nur für  linguist --selection"
echo
path_hint
say "Fertig!  Starten mit:  linguist   (oder über das Anwendungsmenü)"
echo "Tipp: Tastenkürzel auf  linguist --toggle  (Fenster) und  linguist --selection  (markierten Text) legen."
echo "Aktualisieren: ./update.sh   Entfernen: ./uninstall.sh"
