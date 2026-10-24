# Platzhalter für translate.py: linguist ist deutsch, tr() füllt nur die {}.
def tr(s, *args):
    return s.format(*args) if args and isinstance(s, str) else s
