#!/usr/bin/env bash
# Starter für linguist. Läuft es schon im Hintergrund, geht der Aufruf direkt per D-Bus hin.
#   linguist [wort]  ·  --toggle (Super+T)  ·  --popup [text]  ·  --selection  ·  --settings
#   linguist --hover on|off|toggle  ·  --daemon (Autostart)  ·  --quit
APP=de.invincible.Linguist
OBJ=/de/invincible/Linguist
D="$HOME/.local/share/linguist"
PY=python3
LOG="${XDG_RUNTIME_DIR:-/tmp}/linguist.log"

running() { gdbus call --session --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus \
    --method org.freedesktop.DBus.NameHasOwner "$APP" 2>/dev/null | grep -q true; }
action() { gdbus call --session --timeout 3 --dest "$APP" --object-path "$OBJ" \
    --method org.gtk.Actions.Activate "$1" "${2:-[]}" '{}' >/dev/null 2>&1; }
str() { local t=${1//\\/\\\\}; t=${t//\'/\\\'}; echo "[<'$t'>]"; }   # Text als D-Bus-Variante

# gtk4-layer-shell (für die Hover-Ecke) – liegt je nach Distribution woanders; fehlt sie, geht linguist ohne Hover
layer_shell() {
    local p
    for p in /usr/lib/libgtk4-layer-shell.so.0 /usr/lib64/libgtk4-layer-shell.so.0 \
             /usr/lib/*-linux-gnu/libgtk4-layer-shell.so.0 /usr/local/lib/libgtk4-layer-shell.so.0 \
             /usr/local/lib/*-linux-gnu/libgtk4-layer-shell.so.0 /usr/local/lib64/libgtk4-layer-shell.so.0 \
             /usr/lib/libgtk4-layer-shell.so; do
        [[ -e $p ]] && { echo "$p"; return; }
    done
}
start() {
    local pre; pre=$(layer_shell)
    [[ -n ${WAYLAND_DISPLAY:-} && -n $pre ]] && export LD_PRELOAD=$pre${LD_PRELOAD:+:$LD_PRELOAD}
    if [[ $pre == /usr/local/* ]]; then
        local d=${pre%/*}/girepository-1.0
        [[ -d $d ]] && export GI_TYPELIB_PATH=$d${GI_TYPELIB_PATH:+:$GI_TYPELIB_PATH}
    fi
    setsid -f "$PY" "$D/linguist.py" "$@" >>"$LOG" 2>&1 </dev/null
}

case "${1:-}" in
    --hover)     exec "$PY" "$D/linguist.py" "$@" ;;       # nur Zustand schreiben (kein GTK nötig)
    --daemon)    running || start --daemon; exit 0 ;;
    --quit)      running && action quit; exit 0 ;;
    --toggle)    running && action toggle && exit 0; start; exit 0 ;;
    --selection) running && action selection && exit 0; start --selection; exit 0 ;;
    --settings)  running && action settings && exit 0; start --settings; exit 0 ;;
    --popup)     if running; then
                     if [ -n "${2:-}" ]; then action popup "$(str "$2")"; else action popup "$(str "")"; fi
                     exit 0
                 fi
                 start "$@"; exit 0 ;;
    "")          running && action show && exit 0; start; exit 0 ;;
    *)           t="$*"
                 running && action translate "$(str "$t")" && exit 0
                 start "$@"; exit 0 ;;
esac
