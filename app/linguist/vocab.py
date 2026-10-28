# linguist – Verlauf, Vokabeln (Karteikarten) und Zwischenspeicher für Online-Übersetzungen.
# Alles liegt als kleine JSON-Dateien in ~/.config/linguist; nichts davon verlässt den Rechner.
import json, os, time

from gi.repository import GLib

DIR = os.path.join(GLib.get_user_config_dir(), "linguist")
HIST = os.path.join(DIR, "history.json")
VOCAB = os.path.join(DIR, "vocab.json")
CACHE = os.path.join(DIR, "online-cache.json")
HIST_MAX = 300
CACHE_MAX = 400
LEITNER = [0, 1, 3, 7, 14, 30]          # Tage bis zur nächsten Abfrage je Fach


def _load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, type(default)) else default
    except (OSError, ValueError):
        return default


def _save(path, data):
    try:
        os.makedirs(DIR, exist_ok=True)
        with open(path + ".tmp", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(path + ".tmp", path)
    except OSError:
        pass


# ---------------------------------------------------------------- Verlauf
def hist_add(q, first, lang):
    q = q.strip()
    if len(q) < 2 or not first:
        return
    d = [h for h in _load(HIST, []) if h.get("q", "").lower() != q.lower()]
    d.insert(0, {"q": q, "a": first, "lang": lang, "t": time.time()})
    _save(HIST, d[:HIST_MAX])


def hist_list(n=12):
    return _load(HIST, [])[:n]


def hist_del(q):
    _save(HIST, [h for h in _load(HIST, []) if h.get("q") != q])


def hist_clear():
    _save(HIST, [])


# ---------------------------------------------------------------- Vokabeln
def _key(c):
    return (c.get("q", "").lower(), c.get("a", "").lower(), c.get("lang", ""))


def vocab_list():
    return _load(VOCAB, [])


def vocab_has(q, a, lang):
    k = (q.lower(), a.lower(), lang)
    return any(_key(c) == k for c in vocab_list())


def vocab_toggle(q, a, lang, direction=""):
    """Wort merken bzw. wieder entfernen → True, wenn es jetzt gemerkt ist."""
    cards = vocab_list()
    k = (q.lower(), a.lower(), lang)
    if any(_key(c) == k for c in cards):
        _save(VOCAB, [c for c in cards if _key(c) != k])
        return False
    cards.insert(0, {"q": q, "a": a, "lang": lang, "dir": direction, "t": time.time(), "box": 0, "due": 0})
    _save(VOCAB, cards)
    return True


def vocab_remove(q, a, lang):
    k = (q.lower(), a.lower(), lang)
    _save(VOCAB, [c for c in vocab_list() if _key(c) != k])


def vocab_due(limit=20):
    now = time.time()
    due = [c for c in vocab_list() if c.get("due", 0) <= now]
    due.sort(key=lambda c: (c.get("box", 0), c.get("due", 0)))
    return due[:limit]


def vocab_grade(card, known):
    """Karte bewertet: gewusst → nächstes Fach (länger warten), sonst zurück ins erste."""
    cards = vocab_list()
    k = _key(card)
    for c in cards:
        if _key(c) == k:
            if known:
                c["box"] = min(len(LEITNER) - 1, c.get("box", 0) + 1)
                c["due"] = time.time() + LEITNER[c["box"]] * 86400
            else:
                c["box"], c["due"] = 0, time.time() + 120
            break
    _save(VOCAB, cards)


def vocab_tsv():
    """Vorderseite⇥Rückseite je Zeile – lässt sich so in Anki/Quizlet einfügen."""
    return "\n".join(f"{c['q']}\t{c['a']}" for c in vocab_list())


# ---------------------------------------------------------------- Online-Zwischenspeicher
def cache_get(src, lang, q):
    return _load(CACHE, {}).get(f"{src}|{lang}|{q}")


def cache_put(src, lang, q, texts):
    d = _load(CACHE, {})
    d[f"{src}|{lang}|{q}"] = texts
    while len(d) > CACHE_MAX:
        d.pop(next(iter(d)))
    _save(CACHE, d)
