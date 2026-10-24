# Pfade für translate.py. Das Wörterbuch wird mit notist geteilt, wenn es dort schon geladen wurde.
import os

_OWN = os.path.expanduser("~/.local/share/linguist")
_NOTES = os.path.expanduser("~/.local/share/notes")
HOME = _NOTES if (not os.path.isdir(os.path.join(_OWN, "dict")) and os.path.isdir(os.path.join(_NOTES, "dict"))) else _OWN
