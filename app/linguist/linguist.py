#!/usr/bin/env python3
# linguist: der Übersetzer der Suite (Deutsch ⇄ Englisch u. a., Wörterbuch offline, Sätze auf Klick online).
# Einzeln als Fenster benutzbar (Super+T), vor allem aber als Hover-Übersetzer: Maus in die Bildschirmecke
# (Standard unten rechts) → die Karte taucht auf. Läuft dafür unsichtbar im Hintergrund (--daemon).
#   linguist [wort]        Fenster       linguist --toggle      Fenster ein/aus
#   linguist --popup [t]   Karte unten rechts (angepinnt) – mit Text gleich übersetzen
#   linguist --selection   Karte mit dem markierten Text (Primärauswahl, sonst Zwischenablage)
#   linguist --hover on|off|toggle   Hover ein-/ausschalten (wie der Knopf „übersetzer“ in den Apps)
#   linguist --settings    Einstellungen     linguist --daemon / --quit
import json, os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(1, os.path.expanduser("~/.local/share/rice-apps"))
import linguist_link as link  # noqa: E402


def cli_hover(arg):
    """--hover braucht kein GTK: Zustand schreiben, der laufende linguist (und die Apps) merken es per Dateiüberwachung."""
    state = link._load(link.STATE_FILE)
    cur = bool(state.get("hover_on", True))
    new = {"on": True, "an": True, "off": False, "aus": False}.get(arg, not cur)
    link.set_hover_active(new)
    print("hover:", "an" if new else "aus")


if "--hover" in sys.argv:
    i = sys.argv.index("--hover")
    cli_hover(sys.argv[i + 1] if i + 1 < len(sys.argv) else "toggle")
    sys.exit(0)

PRELOADED = "gtk4-layer-shell" in os.environ.get("LD_PRELOAD", "")
os.environ.setdefault("GSK_RENDERER", "cairo")      # gleiche Optik, halber Speicher

import gi  # noqa: E402
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, Gio, GLib, Gtk  # noqa: E402

for _var in ("LD_PRELOAD", "GSK_RENDERER"):       # nicht an gestartete Programme (wl-paste …) vererben
    os.environ.pop(_var, None)

import glass  # noqa: E402
import tui  # noqa: E402
import hotcorner  # noqa: E402
import translate  # noqa: E402

hotcorner.PRELOADED = PRELOADED
APP_ID = "de.invincible.Linguist"
DEFAULTS = {"hover": False, "corner": "bottom-right", "delay": 160, "close_on_copy": True, "translator": {}}
DELAYS = [(0, "sofort"), (160, "kurz"), (350, "mittel"), (600, "lang")]

CSS = """
window.ling-trigger { background-color: rgba(0, 0, 0, 0.01); }       /* ganz durchsichtig würde nicht angezeigt */
window.ling-popup { background: none; background-color: transparent; box-shadow: none; color: @foreground; }
window.ling-popup * { font-family: "JetBrainsMono Nerd Font", "JetBrains Mono", "Notes Icons", monospace; font-weight: bold; }
window.ling-popup label { font-size: 13px; }
.trx entry { background-color: alpha(@foreground, 0.07); background-image: none; color: @foreground; box-shadow: none;
    border: 1px solid alpha(@primary, 0.45); border-radius: 4px; min-height: 26px; padding: 0 6px; }
.trx entry:focus-within { border-color: @primary; }
.trx entry image { color: alpha(@foreground, 0.55); }
.trx button.trx-dir { background-color: alpha(@foreground, 0.07); color: @foreground; border: none; }
.trx button.trx-dir:hover { background-color: alpha(@primary, 0.2); }
.trx button.trx-phrase { color: @foreground; }
.trx-plain .trx-foot { margin-top: 6px; }
window.tui .hintline { color: alpha(@foreground, 0.6); }
"""


class LinguistWindow(tui.TuiWindow):
    APP_ID = APP_ID
    ESC_CLOSES = False          # Esc gehört dem Übersetzer (Eingabe leeren/schließen)

    def on_show(self):
        self.get_application().refresh_window()

    def on_hide(self):
        self.get_application().maybe_quit()


class Linguist(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.HANDLES_OPEN)
        self.cfg = {**DEFAULTS, **link._load(link.CFG_FILE)}
        self.win = None
        self.pop = None
        self.daemon = False
        self.held = False
        self.corners = []
        self.start_text = None
        self.start_mode = None        # "popup" | "selection" | "settings"
        self.mon = None
        self.displays_id = None

    # ================= Einstellungen =================
    def save_cfg(self):
        try:
            os.makedirs(link.CFG_DIR, exist_ok=True)
            tmp = link.CFG_FILE + ".tmp"
            with open(tmp, "w") as f:
                json.dump(self.cfg, f, ensure_ascii=False, indent=1)
            os.replace(tmp, link.CFG_FILE)
        except OSError as e:
            print("linguist: Einstellungen nicht gespeichert:", e, file=sys.stderr)

    def set_cfg(self, key, value):
        self.cfg[key] = value
        self.save_cfg()
        self.apply_hover()

    def hover_on(self):
        return bool(link._load(link.STATE_FILE).get("hover_on", True))

    def hover_wanted(self):
        return bool(self.cfg.get("hover")) and self.hover_on()

    def corner(self):
        c = self.cfg.get("corner")
        return c if c in dict(hotcorner.CORNERS) else "bottom-right"

    # ================= Start =================
    def do_startup(self):
        Gtk.Application.do_startup(self)
        if CSS not in tui.CSS:
            tui.CSS += CSS + translate.CSS
        tui.Theme.get().load()
        for name, cb, ptype in (("show", lambda *_: self.show_window(), None), ("toggle", lambda *_: self.toggle(), None),
                                ("quit", lambda *_: self.quit(), None),
                                ("popup", lambda a, v: self.show_popup(v.get_string() if v else None), "s"),
                                ("selection", lambda *_: self.show_selection(), None),
                                ("settings", lambda *_: self.show_window("set"), None),
                                ("translate", lambda a, v: self.show_window(text=v.get_string()), "s"),
                                ("hover", lambda a, v: cli_hover(v.get_string()), "s")):
            act = Gio.SimpleAction.new(name, GLib.VariantType.new(ptype) if ptype else None)
            act.connect("activate", cb)
            self.add_action(act)
        self.mon = link.watch(self.files_changed)
        if self.mon is None:                         # Ordner gibt es noch nicht → anlegen und neu versuchen
            os.makedirs(link.CFG_DIR, exist_ok=True)
            self.mon = link.watch(self.files_changed)
        disp = Gdk.Display.get_default()
        if disp:
            self.displays_id = disp.get_monitors().connect("items-changed", lambda *_: self.rebuild_corners())
        GLib.idle_add(lambda: (self.apply_hover(), False)[1])       # erst wenn die Hauptschleife läuft

    def do_activate(self):
        mode, text = self.start_mode, self.start_text
        self.start_mode = self.start_text = None
        if self.daemon:                   # Hintergrundstart: nur da sein
            self.daemon = False
            self.update_hold(force=True)
            return
        if mode == "popup":
            self.show_popup(text)
        elif mode == "selection":
            self.show_selection()
        elif mode == "settings":
            self.show_window("set")
        else:
            self.show_window(text=text)

    def files_changed(self):
        new = {**DEFAULTS, **link._load(link.CFG_FILE), "translator": self.cfg.get("translator", {})}
        self.cfg.clear()                         # an Ort und Stelle: Fenster und Karte halten dasselbe Dict
        self.cfg.update(new)
        self.apply_hover()
        if self.win:
            self.refresh_settings()

    # ================= Hover =================
    def apply_hover(self):
        want = self.hover_wanted() and hotcorner.layer_ok()
        if want:
            self.rebuild_corners()
        else:
            for c in self.corners:
                c.set_active(False)
            if self.pop and self.pop.is_open() and not self.pop.pinned:
                self.pop.hide()
        self.update_hold()

    def rebuild_corners(self):
        """Eine Ecke je Monitor. Nur neu bauen, wenn sich Monitore oder Ecke geändert haben (Neubauen zerstört
        gerade eingeblendete layer-shell-Flächen)."""
        if not (self.hover_wanted() and hotcorner.layer_ok()):
            return
        mons = Gdk.Display.get_default().get_monitors()
        wanted = [(mons.get_item(i), self.corner()) for i in range(mons.get_n_items())]
        if [(c.monitor, c.corner) for c in self.corners] != wanted:
            for c in self.corners:
                c.destroy()
            self.corners = [hotcorner.Corner(self, m, corner, self.on_corner_hit, lambda: None) for m, corner in wanted]
        for c in self.corners:
            c.delay = int(self.cfg.get("delay", 160))
            c.set_active(True)

    def on_corner_hit(self, monitor):
        self.show_popup(None, sticky=False, monitor=monitor)

    def update_hold(self, force=False):
        keep = self.hover_wanted() or force or self.held_daemon
        if keep and not self.held:
            self.hold()
            self.held = True
        elif not keep and self.held:
            self.release()
            self.held = False

    held_daemon = False

    def keep_running(self):
        return self.held and (self.held_daemon or self.hover_wanted())

    def maybe_quit(self):
        """Ohne Hintergrunddienst und ohne offenes Fenster/Karte beendet sich linguist."""
        def check():
            visible = (self.win and self.win.get_visible()) or (self.pop and self.pop.is_open())
            if not visible and not self.keep_running():
                self.quit()
            return False
        GLib.idle_add(check)

    # ================= Karte (Popup) =================
    def popup(self):
        if self.pop is None:
            self.pop = hotcorner.Popup(self, self.cfg, self.save_cfg, self.corner,
                                       lambda: bool(self.cfg.get("close_on_copy", True)))
            self.pop.on_hidden = self.maybe_quit
        return self.pop

    def show_popup(self, text=None, sticky=True, monitor=None):
        self.popup().show((text or "").strip() or None, sticky=sticky, monitor=monitor)

    def show_selection(self):
        text = None
        if shutil.which("wl-paste"):
            for args in (["wl-paste", "-p", "-n"], ["wl-paste", "-n"]):
                try:
                    out = subprocess.run(args, capture_output=True, text=True, timeout=1).stdout.strip()
                except (OSError, subprocess.SubprocessError):
                    out = ""
                if out:
                    text = out
                    break
        self.show_popup(text)

    # ================= Fenster =================
    def toggle(self):
        if self.win and self.win.get_visible() and self.win.is_active():
            self.win.close()
        else:
            self.show_window()

    def show_window(self, tab="trans", text=None):
        if not self.win:
            self.build()
        getattr(glass, "bring_here", lambda w: None)(self.win)
        self.win.present()
        self.win.show_tab(tab)
        if text:
            self.tr.entry.set_text(text.strip()[:500])

    def refresh_window(self):
        self.tr.reload_prefs()
        self.refresh_settings()
        GLib.idle_add(lambda: (self.win.current_tab() == "trans" and self.tr.toggle(True), False)[1])

    def build(self):
        win = LinguistWindow(self, "linguist", [("trans", "übersetzer", "󰗊"), ("set", "einstellungen", "󰒓")],
                             size=(560, 640), hints=(("esc", "leeren/zu"), ("enter", "kopieren")))
        self.win = win
        win.add_changelog("linguist", HERE)
        self.tr = translate.Translator(self.cfg, self.save_cfg, mode="window")
        self.tr.on_toggled = lambda on: None if on else win.close()
        win.add_page("trans", self.tr, scroll=False)
        win.add_page("set", self.build_settings())
        win.on_tab = lambda tid: tid == "trans" and GLib.idle_add(lambda: (self.tr.entry.grab_focus(), False)[1])
        for name, cb, keys in (("close", lambda *_: win.close(), ["<Control>w"]),):
            act = Gio.SimpleAction.new(name, None)
            act.connect("activate", cb)
            win.add_action(act)
            self.set_accels_for_action(f"win.{name}", keys)

    def build_settings(self):
        page = tui.vbox(spacing=8)
        page.set_margin_top(6)
        page.set_margin_bottom(10)
        p = tui.Panel("hover-übersetzer")
        self.hover_check = tui.Check("maus in die ecke → linguist taucht auf", self.cfg["hover"],
                                     lambda on: self.set_cfg("hover", on))
        self.on_check = tui.Check("zurzeit eingeschaltet", self.hover_on(), self.set_hover_on,
                                  tooltip="Derselbe Schalter wie der Knopf „übersetzer“ in notist, mailist …")
        p.body.append(self.hover_check)
        p.body.append(self.on_check)
        self.corner_sel = tui.Select(lambda v: self.set_cfg("corner", v))
        self.delay_sel = tui.Select(lambda v: self.set_cfg("delay", v))
        p.body.append(tui.hbox(tui.label("ecke", "dim"), self.corner_sel, tui.label("", hexpand=True),
                               tui.label("verweilen", "dim"), self.delay_sel, spacing=8))
        self.close_check = tui.Check("nach dem kopieren wieder zugehen", self.cfg["close_on_copy"],
                                     lambda on: self.set_cfg("close_on_copy", on))
        p.body.append(self.close_check)
        self.support_lbl = tui.label("", "dim", wrap=True)
        p.body.append(self.support_lbl)
        page.append(p)
        a = tui.Panel("in den anderen apps")
        a.body.append(tui.label("Ist der Hover-Übersetzer hier aktiviert, zeigt der Knopf „übersetzer“ in notist, "
                                "mailist und Co., ob er an ist – ein Klick schaltet ihn ein/aus. Ist er hier aus "
                                "(Standard), öffnet der Knopf wie gewohnt den Übersetzer in der App.", "dim", wrap=True))
        page.append(a)
        k = tui.Panel("kürzel & befehle")
        for cmd, what in (("linguist --toggle", "Fenster ein/aus (Super+T)"),
                          ("linguist --selection", "markierten Text übersetzen (Karte unten rechts)"),
                          ("linguist --popup wort", "Karte mit Wort öffnen"),
                          ("linguist --hover toggle", "Hover an/aus")):
            k.body.append(tui.hbox(tui.label(cmd, "accent"), tui.label(what, "dim"), spacing=10))
        page.append(k)
        self.refresh_settings()
        return page

    def set_hover_on(self, on):
        link.set_hover_active(on)

    def refresh_settings(self):
        if not self.win:
            return
        self.hover_check.set_active(bool(self.cfg.get("hover")))
        self.on_check.set_active(self.hover_on())
        self.close_check.set_active(bool(self.cfg.get("close_on_copy", True)))
        self.corner_sel.set_options(hotcorner.CORNERS, self.corner())
        d = int(self.cfg.get("delay", 160))
        self.delay_sel.set_options(DELAYS, d if d in dict(DELAYS) else 160)
        if hotcorner.layer_ok():
            self.support_lbl.set_label("Die Ecke ist bereit – Maus hineinschieben, kurz warten. "
                                       "Esc oder Maus weg schließt, 󰐃 pinnt die Karte fest.")
        else:
            self.support_lbl.set_label("Dieser Desktop bietet keine Bildschirm-Ecke (layer-shell) – "
                                       "Hover geht hier nicht. Fenster (Super+T) und `linguist --popup` gehen trotzdem.")


def main(argv):
    app = Linguist()
    args = argv[1:]
    rest = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--daemon":
            app.daemon = True
            app.held_daemon = True
        elif a == "--toggle":
            app.register(None)
            if app.get_is_remote():
                app.activate_action("toggle", None)
                return 0
        elif a == "--popup":
            app.start_mode = "popup"
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                app.start_text = args[i + 1]
                i += 1
        elif a == "--selection":
            app.start_mode = "selection"
        elif a == "--settings":
            app.start_mode = "settings"
        elif a == "--quit":
            return 0
        else:
            rest.append(a)
        i += 1
    if rest and not app.start_mode:
        app.start_text = " ".join(rest)
    return app.run([argv[0]])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
