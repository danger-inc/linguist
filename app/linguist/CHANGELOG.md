# linguist – Änderungen

## 1.2.1 (2026-10-25)
- **Update-Knopf**: Neben der Versionsnummer steht „󰑐“ – Klick sucht sofort nach einem Update. Gibt es eine neuere
  Version, wird daraus „󰚰 update“; ein Klick lädt und installiert sie (Linux und Windows), danach heißt er „󰑓 neu starten“.
- **Rückmeldung bei Umschalt-Knöpfen**: „An“ (z. B. „Ton behalten“) ist jetzt auch unter dem Mauszeiger zu sehen,
  Drücken färbt sofort – man muss die Maus nicht mehr wegbewegen, um zu sehen, ob der Klick angekommen ist.
- **Windows: echte Titelleiste** – das Fenster lässt sich verschieben, in der Größe ändern, minimieren und
  maximieren.

## 1.2.0 (2026-10-24)
- **Wort direkt einfügen**: In der Hover-Karte setzt **Enter** das beste Wort und ein **Klick** auf ein Wort oder eine
  Wendung die Übersetzung an die Cursorstelle der App darunter (z. B. notist) – per Strg+V an das
  Fenster, das vorher den Fokus hatte (Terminals: Strg+Umschalt+V). Braucht Hyprland oder wtype; abschaltbar in den
  Einstellungen („klick / enter fügt … ein“), dann wird wie bisher kopiert.
- **Kopier-Knopf rechts**: Fährst du über einen Treffer, erscheint rechts daneben 󰆏 – kopiert nur.
- Die Hover-Karte geht noch schneller zu, sobald die Maus weg ist.

## 1.1.0 (2026-10-24)
- **Einstellungen oben rechts**: Das Zahnrad 󰒓 neben dem Versionsknopf öffnet sie (Strg+Komma, Esc geht zurück) –
  wie in den anderen Apps der Suite, nicht mehr als eigener Tab.
- **Hover-Karte größer** (breiter, mehr Ergebnisse sichtbar) und **verschwindet schneller**, sobald die Maus weg ist.
- Erscheint im Starter (Super+R).

## 1.0.0 (2026-10-24)
- **Der Übersetzer der Suite als eigene App**: Wörterbuch Deutsch ⇄ Englisch offline (TU Chemnitz, mit notist
  geteilt), weitere Sprachen aus Wiktionary zum Nachladen, ganze Sätze auf Klick/Enter online (MyMemory).
- **Hover-Übersetzer**: Maus in die untere rechte Bildschirmecke schieben, kurz warten – die Karte taucht auf, du
  tippst oder fügst ein, ein Klick kopiert. Maus weg oder Esc schließt, 󰐃 pinnt sie fest. Ecke, Verweilzeit und
  „nach dem Kopieren zugehen“ stellst du in den Einstellungen ein (Standard: aus).
- **Knopf „übersetzer“ in notist und mailist**: Ist der Hover-Übersetzer eingestellt, zeigt der Knopf, ob er an ist
  (Klick = an/aus, Rechtsklick = Einstellungen, Strg+Umschalt+T = Karte mit dem markierten Text). Sonst öffnet er
  wie bisher den Übersetzer in der App.
- Einzeln benutzbar: `linguist` (Fenster, Super+T), `linguist --selection` (markierten Text übersetzen),
  `linguist --popup wort`, `linguist --hover on|off|toggle`.
