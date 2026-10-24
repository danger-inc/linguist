# linguist

Der Übersetzer der -ist-Suite (GTK4): Wörterbuch Deutsch ⇄ Englisch offline, weitere Sprachen zum Nachladen, ganze
Sätze auf Klick online. Einzeln als Fenster benutzbar – vor allem aber als **Hover-Übersetzer**: Maus in die untere
rechte Bildschirmecke ziehen, und die Übersetzer-Karte taucht auf.

## Installieren – Linux

```bash
gh auth login                                   # einmalig (Repo ist privat, Einladung nötig)
gh repo clone danger-inc/linguist ~/linguist-src
cd ~/linguist-src && ./install.sh
```

Der Installer fragt nach den Systempaketen (GTK4, PyGObject, gtk4-layer-shell, wl-clipboard – einmal Passwort),
kopiert linguist nach `~/.local/share/linguist` und legt den Befehl `linguist` und einen Menüeintrag an. Zum Schluss:
Autostart im Hintergrund (nötig für die Bildschirmecke).

## Bedienung

- **Fenster** (`linguist`, am besten Super+T): Wort oder Satz tippen, ein Klick auf eine Übersetzung kopiert sie,
  Enter kopiert die erste (oder übersetzt online). Sprache und Richtung oben; weitere Sprachen (WikDict) per Klick laden.
- **Hover-Übersetzer** (Einstellungen → *hover-übersetzer*, standardmäßig aus): Maus in die Ecke schieben und kurz
  warten. Tippen, Enter/Klick setzt das Wort an die Cursorstelle der App darunter (󰆏 rechts kopiert nur). Maus weg oder Esc schließt, 󰐃 pinnt die Karte fest. Ecke, Verweilzeit und
  „nach dem Kopieren zugehen“ sind einstellbar.
- **In den anderen Apps** (notist, mailist): Ist der Hover-Übersetzer aktiviert, zeigt der Knopf „übersetzer“, ob er an
  ist (Klick = an/aus, Rechtsklick = Einstellungen, Strg+Umschalt+T = markierten Text in der Karte übersetzen). Ist er
  aus, öffnet der Knopf wie gewohnt den Übersetzer in der App.
- Befehle: `linguist --toggle` (Fenster ein/aus), `linguist --selection` (markierten Text übersetzen),
  `linguist --popup wort`, `linguist --hover on|off|toggle`, `linguist --settings`, `linguist --daemon`, `linguist --quit`.

## Läuft auf

| System | Status |
|---|---|
| Arch (Hyprland) | getestet |
| Sway/KDE (layer-shell), Ubuntu 24.04+, Fedora 40+, openSUSE | sollte gehen |
| GNOME | Fenster und `--popup` gehen, die Bildschirmecke nicht (kein layer-shell) |

Wörterbücher: TU Chemnitz „ding“ (Deutsch ⇄ Englisch, GPL), WikDict/Wiktionary (CC BY-SA); Online-Sätze über MyMemory,
nur auf Klick.

## Aktualisieren / Entfernen

```bash
cd ~/linguist-src && ./update.sh
./uninstall.sh
```
