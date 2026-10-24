# Hover-Übersetzer: unsichtbarer Auslöser in der Bildschirmecke (layer-shell, je Monitor) und die Popup-Karte,
# die auftaucht, wenn die Maus dort ankommt. Verschwindet wieder, wenn die Maus weg ist (außer angepinnt).
import json, os, shutil, socket, subprocess

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GLib, Gtk

try:   # braucht gtk4-layer-shell (vom Starter per LD_PRELOAD geladen) und einen Compositor mit layer-shell
    gi.require_version("Gtk4LayerShell", "1.0")
    from gi.repository import Gtk4LayerShell as Layer
except (ImportError, ValueError):
    Layer = None
try:
    import cairo
except ImportError:
    cairo = None

import translate

RUNTIME = GLib.get_user_runtime_dir()
PRELOADED = False        # setzt linguist.py: Starter hat libgtk4-layer-shell vorgeladen
CORNERS = [("bottom-right", "unten rechts"), ("bottom-left", "unten links"),
           ("top-right", "oben rechts"), ("top-left", "oben links")]


def layer_ok():
    try:
        return Layer is not None and PRELOADED and Layer.is_supported()
    except Exception:  # noqa: BLE001
        return False


def cursor_pos():
    """Zeigerposition (logische Pixel) direkt vom Hyprland-Socket – None, wenn das nicht klappt."""
    sig = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
    if not sig:
        return None
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            s.connect(f"{RUNTIME}/hypr/{sig}/.socket.sock")
            s.sendall(b"j/cursorpos")
            data = b""
            while chunk := s.recv(4096):
                data += chunk
        d = json.loads(data)
        return d["x"], d["y"]
    except (OSError, ValueError, KeyError):
        return None


def hypr_json(cmd):
    """Anfrage an den Hyprland-Socket (z. B. "j/activewindow") → JSON oder None."""
    sig = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
    if not sig:
        return None
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            s.connect(f"{RUNTIME}/hypr/{sig}/.socket.sock")
            s.sendall(cmd.encode())
            data = b""
            while chunk := s.recv(4096):
                data += chunk
        return json.loads(data)
    except (OSError, ValueError):
        return None


def can_insert():
    """Einfügen ins Textfeld der App darunter: per Hyprland (send_shortcut) oder wtype."""
    return bool(os.environ.get("HYPRLAND_INSTANCE_SIGNATURE") and shutil.which("hyprctl")) or \
        bool(shutil.which("wtype"))


TERMINALS = ("kitty", "foot", "alacritty", "wezterm", "konsole", "gnome-terminal", "xterm", "ghostty", "terminator",
             "tilix", "st-256color", "org.wezfurlong.wezterm", "com.mitchellh.ghostty")


def send_paste(target):
    """Strg+V (im Terminal Strg+Umschalt+V) an das Fenster schicken, das vor der Karte den Fokus hatte."""
    cls = ((target or {}).get("class") or "").lower()
    mods = "CTRL SHIFT" if any(t in cls for t in TERMINALS) else "CTRL"
    if os.environ.get("HYPRLAND_INSTANCE_SIGNATURE") and shutil.which("hyprctl"):
        win = f', window = "address:{target["address"]}"' if target and target.get("address") else ""
        subprocess.Popen(["hyprctl", "dispatch", f'hl.dsp.send_shortcut({{ mods = "{mods}", key = "V"{win} }})'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif shutil.which("wtype"):
        args = ["wtype", "-M", "ctrl"] + (["-M", "shift"] if "SHIFT" in mods else []) + ["-k", "v"]
        subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def edges(corner):
    v, h = corner.split("-")
    return (Layer.Edge.BOTTOM if v == "bottom" else Layer.Edge.TOP,
            Layer.Edge.RIGHT if h == "right" else Layer.Edge.LEFT)


class Corner:
    """Unsichtbarer 6×6-Punkt in der Ecke eines Monitors. Maus drauf (kurz verweilen) → on_hit(monitor)."""
    SIZE = 6

    def __init__(self, app, monitor, corner, on_hit, on_leave):
        self.monitor, self.corner, self.on_hit, self.on_leave = monitor, corner, on_hit, on_leave
        self.timer = None
        self.delay = 160
        self.win = Gtk.Window(application=app, resizable=False, decorated=False)
        self.win.add_css_class("ling-trigger")
        Layer.init_for_window(self.win)
        Layer.set_namespace(self.win, "linguist-trigger")
        Layer.set_layer(self.win, Layer.Layer.OVERLAY)       # liegt auch über Vollbild-Fenstern
        Layer.set_monitor(self.win, monitor)
        Layer.set_exclusive_zone(self.win, 0)
        Layer.set_keyboard_mode(self.win, Layer.KeyboardMode.NONE)
        self.place(corner)
        self.win.set_child(Gtk.Box(width_request=self.SIZE, height_request=self.SIZE))
        self.win.set_default_size(self.SIZE, self.SIZE)
        self.win.set_size_request(self.SIZE, self.SIZE)
        m = Gtk.EventControllerMotion()
        m.connect("enter", self.enter)
        m.connect("leave", self.leave)
        self.win.add_controller(m)

    def place(self, corner):
        for e in (Layer.Edge.TOP, Layer.Edge.BOTTOM, Layer.Edge.LEFT, Layer.Edge.RIGHT):
            Layer.set_anchor(self.win, e, False)
        for e in edges(corner):
            Layer.set_anchor(self.win, e, True)

    def enter(self, *_):
        self.cancel()
        self.timer = GLib.timeout_add(max(self.delay, 1), self.fire)    # kurz verweilen: kein Aufpoppen im Vorbeiziehen

    def fire(self):
        self.timer = None
        self.on_hit(self.monitor)
        return False

    def leave(self, *_):
        self.cancel()
        self.on_leave()

    def cancel(self):
        if self.timer is not None:
            GLib.source_remove(self.timer)
            self.timer = None

    def set_active(self, on):
        if on:
            if not self.win.get_visible():
                self.win.present()
        else:
            self.cancel()
            self.win.set_visible(False)

    def destroy(self):
        self.cancel()
        self.win.destroy()


class Popup:
    """Die Karte selbst: layer-shell-Fenster in der Ecke mit der Übersetzer-Karte. Ohne layer-shell ein kleines
    normales Fenster (kein Hover, aber `linguist --popup` geht trotzdem)."""
    GRACE_MS = 180            # so lange darf die Maus weg sein, bevor die Karte verschwindet
    GRACE_TEXT_MS = 600      # … wenn schon etwas getippt wurde
    TRAVEL_MS = 450           # anfangs Zeit, von der Ecke auf die Karte zu fahren

    def __init__(self, app, cfg, save_cfg, get_corner, close_on_copy):
        self.cfg, self.get_corner, self.close_on_copy = cfg, get_corner, close_on_copy
        self.layer = layer_ok()
        self.pinned = False
        self.outside_ms = 0
        self.watch_id = None
        self.hide_id = None
        self.monitor = None
        self.win = Gtk.Window(application=app, resizable=False, decorated=False, title="linguist")
        self.win.add_css_class("ling-popup")
        self.tr = translate.Translator(cfg, save_cfg, mode="popup")
        self.tr.on_toggled = lambda on: None if on else self.hide()
        self.tr.on_copied = self.copied
        self.tr.on_pin = self.set_pinned
        self.target = None                # Fenster, das vor der Karte den Fokus hatte (hier landet „einfügen“)
        self.tr.on_insert = self.insert
        self.tr.insert_enabled = lambda: bool(cfg.get("insert", True)) and can_insert() and bool(self.target)
        if self.layer:
            Layer.init_for_window(self.win)
            Layer.set_namespace(self.win, "linguist-popup")
            Layer.set_layer(self.win, Layer.Layer.OVERLAY)
            Layer.set_exclusive_zone(self.win, 0)
            Layer.set_keyboard_mode(self.win, Layer.KeyboardMode.NONE)    # Tastatur nur, solange die Karte offen ist
        else:
            self.win.set_default_size(600, -1)
        self.win.set_child(self.tr)
        m = Gtk.EventControllerMotion()
        m.connect("enter", lambda *_: self.cancel_hide())
        m.connect("leave", lambda *_: self.leave_soon())
        self.win.add_controller(m)
        self.win.connect("map", lambda *_: GLib.idle_add(self.fit_input))

    # ----- Platz -----
    def place(self):
        if not self.layer:
            return
        corner = self.get_corner()
        for e in (Layer.Edge.TOP, Layer.Edge.BOTTOM, Layer.Edge.LEFT, Layer.Edge.RIGHT):
            Layer.set_anchor(self.win, e, False)
            Layer.set_margin(self.win, e, 0)
        for e in edges(corner):
            Layer.set_anchor(self.win, e, True)
        v, h = corner.split("-")
        self.tr.set_halign(Gtk.Align.END if h == "right" else Gtk.Align.START)
        self.tr.set_valign(Gtk.Align.END if v == "bottom" else Gtk.Align.START)
        if self.monitor is not None:
            Layer.set_monitor(self.win, self.monitor)

    def fit_input(self):
        """Nur die Karte nimmt Mausklicks an – der transparente Schattenrand lässt sie zu den Fenstern darunter durch."""
        if cairo is None or not self.win.get_visible():
            return False
        try:
            ok, b = self.tr.compute_bounds(self.win)
            surf = self.win.get_surface()
            if ok and surf:
                x, y = int(b.get_x()), int(b.get_y())
                w, h = int(b.get_width()), int(b.get_height())
                surf.set_input_region(cairo.Region(cairo.RectangleInt(x + 14, y + 14, max(1, w - 28), max(1, h - 28))))
        except Exception:  # noqa: BLE001
            pass
        return False

    # ----- ein/aus -----
    def is_open(self):
        return self.win.get_visible()

    def show(self, text=None, sticky=False, monitor=None):
        self.cancel_hide()
        self.monitor = monitor or self.monitor
        was_open = self.is_open()
        if not was_open:
            w = hypr_json("j/activewindow")
            self.target = w if isinstance(w, dict) and w.get("address") and w.get("class") != "de.invincible.Linguist" else None
            self.tr.pin_btn.set_active(bool(sticky))
            self.pinned = bool(sticky)
            self.tr.reload_prefs()
            self.place()
        elif sticky:
            self.tr.pin_btn.set_active(True)
        if self.layer:
            Layer.set_keyboard_mode(self.win, Layer.KeyboardMode.EXCLUSIVE)
        self.win.present()
        self.tr.toggle(True, text)
        GLib.timeout_add(120, self.fit_input)
        GLib.timeout_add(500, self.fit_input)
        if not self.pinned and self.watch_id is None:
            self.outside_ms = -self.TRAVEL_MS
            self.watch_id = GLib.timeout_add(150, self.watch)

    def hide(self):
        self.cancel_hide()
        self.watch_id = None
        if self.layer:
            Layer.set_keyboard_mode(self.win, Layer.KeyboardMode.NONE)     # Fokus zurück an das Fenster darunter
        self.win.set_visible(False)
        self.tr.pin_btn.set_active(False)
        self.pinned = False
        self.on_hidden()

    def on_hidden(self):
        """Wird vom Besitzer überschrieben."""

    def set_pinned(self, on):
        self.pinned = bool(on)
        if self.pinned:
            self.cancel_hide()
        elif self.is_open() and self.watch_id is None:
            self.outside_ms = 0
            self.watch_id = GLib.timeout_add(150, self.watch)

    def insert(self, text):
        """Wort an die Cursorstelle des Fensters darunter setzen: Zwischenablage + Strg+V an dieses Fenster."""
        self.tr.get_clipboard().set(text)
        target = self.target
        self.cancel_hide()
        if self.layer:
            Layer.set_keyboard_mode(self.win, Layer.KeyboardMode.NONE)    # Tastatur zurück an das Fenster darunter

        def paste():
            send_paste(target)
            if self.pinned:                                               # angepinnt: Karte bleibt, Tastatur zurück
                if self.layer:
                    GLib.timeout_add(250, lambda: (Layer.set_keyboard_mode(self.win, Layer.KeyboardMode.EXCLUSIVE),
                                                   self.tr.entry.grab_focus(), False)[2])
            else:
                self.hide()
            return False
        GLib.timeout_add(120, paste)

    def copied(self, text):
        if self.close_on_copy() and not self.pinned:
            self.cancel_hide()
            self.hide_id = GLib.timeout_add(500, lambda: (self.hide(), False)[1])

    # ----- Maus weg → zu -----
    def cancel_hide(self):
        if self.hide_id is not None:
            GLib.source_remove(self.hide_id)
            self.hide_id = None

    def leave_soon(self):
        """Rückfall ohne Hyprland-Socket: Enter/Leave des Fensters."""
        if self.pinned or not self.is_open() or cursor_pos() is not None:
            return
        self.cancel_hide()
        self.hide_id = GLib.timeout_add(self.grace(), lambda: (self.hide(), False)[1])

    def grace(self):
        return self.GRACE_TEXT_MS if self.tr.entry.get_text() else self.GRACE_MS

    def pointer_inside(self):
        """Zeiger auf der Karte oder in dem Streifen zwischen Karte und Ecke? (None = unbekannt)"""
        pos = cursor_pos()
        surf = self.win.get_surface()
        if pos is None or surf is None:
            return None
        mon = self.win.get_display().get_monitor_at_surface(surf)
        if not mon:
            return None
        g = mon.get_geometry()
        w, h = self.win.get_width(), self.win.get_height()
        v, hz = self.get_corner().split("-")
        x0, x1 = (g.x + g.width - w, g.x + g.width) if hz == "right" else (g.x, g.x + w)
        y0, y1 = (g.y + g.height - h, g.y + g.height) if v == "bottom" else (g.y, g.y + h)
        pad = 8
        return x0 - pad <= pos[0] <= x1 + pad and y0 - pad <= pos[1] <= y1 + pad

    def watch(self):
        if not self.is_open() or self.pinned:
            self.watch_id = None
            return False
        inside = self.pointer_inside()
        if inside is None:                 # kein Socket → Enter/Leave übernehmen
            self.watch_id = None
            return False
        if inside:
            self.outside_ms = min(self.outside_ms, 0)
        else:
            self.outside_ms += 150
            if self.outside_ms >= self.grace():
                self.watch_id = None
                self.hide()
                return False
        return True
