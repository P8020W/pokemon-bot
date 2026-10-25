"""Suchliste und Telegram-Befehle.

Die Suchliste liegt in watchlist.json im Repo. GitHub speichert sie nach jedem Lauf
(Schritt „Suchliste speichern" in check.yml), damit sie nicht verloren geht.

Befehle (im Chat mit dem Bot):
  /hilfe                    – Übersicht
  /liste                    – was der Bot gerade sucht
  /suche <text> [preis]     – eigenes Produkt suchen, optional mit Höchstpreis in €
  /stopp <text oder nr>     – eigene Suche löschen
  /preis <typ oder nr> <€>  – Höchstpreis ändern (z. B. /preis ttb 60 oder /preis 2 130)
  /an <typ>  /aus <typ>     – Produkttyp melden / nicht mehr melden
"""

import html
import json
import os
import re

from catalog import DEFAULT_TYPES, NAMES, PRODUCTS, resolve_type
import tg

WATCHLIST_FILE = os.environ.get("WATCHLIST_FILE", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                               "watchlist.json"))
MAX_SEARCHES = 15  # mehr Suchen = mehr Abfragen pro Shop = Sperrgefahr


def default_watchlist():
    return {"types": list(DEFAULT_TYPES), "type_max": {}, "searches": [], "update_offset": 0}


def load():
    try:
        with open(WATCHLIST_FILE, encoding="utf-8") as f:
            wl = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        wl = {}
    base = default_watchlist()
    base.update({k: v for k, v in wl.items() if k in base})
    return base


def save(wl):
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(wl, f, ensure_ascii=False, indent=1)
        f.write("\n")


def _price(s):
    try:
        v = float(s.replace("€", "").replace(",", "."))
        return v if 0 < v < 10000 else None
    except (ValueError, AttributeError):
        return None


SET_NUMBERS = {"151"}  # Zahlen, die Teil eines Setnamens sind, nicht der Preis


def _split_price(arg):
    """'mega glurak upc 160' → (['mega','glurak','upc'], 160.0). Auch '160€' und 'bis 160'.
    Eine Zahl ohne € gilt nur ab 5 € als Preis und nicht, wenn sie ein Setname ist (151)."""
    parts = arg.split()
    if len(parts) < 2:
        return parts, None
    last = parts[-1]
    explicit = last.endswith("€") or parts[-2].lower() in ("bis", "max")
    value = _price(last)
    if value and (explicit or (value >= 5 and last not in SET_NUMBERS)):
        parts = parts[:-1]
        if parts and parts[-1].lower() in ("bis", "max"):
            parts = parts[:-1]
        return parts, value
    return parts, None


def _find_search(wl, arg):
    arg = arg.strip()
    if arg.isdigit() and 1 <= int(arg) <= len(wl["searches"]):
        return int(arg) - 1
    for i, s in enumerate(wl["searches"]):
        if s["text"].lower() == arg.lower():
            return i
    return None


def help_text():
    typen = ", ".join(k for k, *_ in PRODUCTS)
    return ("🤖 <b>Befehle</b>\n\n"
            "/liste – was ich gerade suche\n"
            "/suche <i>text</i> [<i>preis</i>] – eigenes Produkt suchen\n"
            "   z. B. <code>/suche mega glurak upc bis 160</code>\n"
            "/stopp <i>nr</i> – eigene Suche löschen (Nr. aus /liste)\n"
            "/preis <i>typ oder nr</i> <i>€</i> – Höchstpreis ändern\n"
            "   z. B. <code>/preis ttb 60</code>\n"
            "/an <i>typ</i> · /aus <i>typ</i> – Produkttyp melden oder nicht\n\n"
            f"Typen: {typen}\n\n"
            "⏱ Ich lese Befehle alle paar Minuten, nicht sofort.")


def list_text(wl, aufschlag):
    lines = ["📋 <b>Ich suche gerade:</b>", "", "<b>Produkttypen</b> (UVP + " f"{aufschlag * 100:.0f} %, außer eigener Preis):"]
    for key, name, uvp, _ in PRODUCTS:
        on = key in wl["types"]
        own = wl["type_max"].get(key)
        grenze = f"bis {own:.2f} €" if own else f"UVP {uvp:.2f} €"
        lines.append(f"{'✅' if on else '⬜'} {html.escape(name)} <code>{key}</code> – {grenze}")
    lines += ["", "<b>Eigene Suchen:</b>"]
    if wl["searches"]:
        for i, s in enumerate(wl["searches"], 1):
            grenze = f"bis {s['max']:.2f} €" if s.get("max") else "Preis: UVP falls bekannt, sonst jeder"
            lines.append(f"{i}. {html.escape(s['text'])} – {grenze}")
    else:
        lines.append("– keine – (mit /suche hinzufügen)")
    return "\n".join(lines)


def handle(text: str, wl, aufschlag=0.10) -> str:
    """Einen Befehl ausführen, Antworttext zurückgeben (oder None, wenn kein Befehl)."""
    text = text.strip()
    if not text.startswith("/"):
        return None
    cmd, _, arg = text.partition(" ")
    cmd = cmd.lower().split("@")[0]
    arg = arg.strip()

    if cmd in ("/start", "/hilfe", "/help"):
        return help_text()
    if cmd == "/liste":
        return list_text(wl, aufschlag)

    if cmd == "/suche":
        if not arg:
            return "Was soll ich suchen? Beispiel: <code>/suche mega glurak upc 160</code>"
        parts, max_price = _split_price(arg)
        query = re.sub(r"\s+", " ", " ".join(parts)).strip()[:60]
        if len(query) < 3:
            return "Der Suchtext ist zu kurz."
        i = _find_search(wl, query)
        if i is not None:
            wl["searches"][i]["max"] = max_price
            return f"✏️ Suche „{html.escape(query)}“ aktualisiert."
        if len(wl["searches"]) >= MAX_SEARCHES:
            return f"Maximal {MAX_SEARCHES} eigene Suchen – bitte erst eine mit /stopp löschen."
        wl["searches"].append({"text": query, "max": max_price})
        hint = f" bis {max_price:.2f} €" if max_price else (
            "\n⚠️ Ohne Preis melde ich jedes lieferbare Angebot, wenn ich die UVP nicht kenne – "
            "auch Scalper-Preise. Mit Preis: <code>/suche " + html.escape(query) + " bis 160</code>")
        return f"✅ Suche „{html.escape(query)}“ gespeichert{hint}"

    if cmd == "/stopp":
        i = _find_search(wl, arg)
        if i is None:
            return "Nicht gefunden. Schau mit /liste nach der Nummer."
        removed = wl["searches"].pop(i)
        return f"🗑 Suche „{html.escape(removed['text'])}“ gelöscht."

    if cmd in ("/an", "/aus"):
        key = resolve_type(arg)
        if not key:
            return "Unbekannter Typ. Mögliche: " + ", ".join(k for k, *_ in PRODUCTS)
        if cmd == "/an" and key not in wl["types"]:
            wl["types"].append(key)
        if cmd == "/aus" and key in wl["types"]:
            wl["types"].remove(key)
        return f"{'✅' if cmd == '/an' else '⬜'} {NAMES[key]}: {'wird gemeldet' if cmd == '/an' else 'wird nicht mehr gemeldet'}."

    if cmd == "/preis":
        parts = arg.split()
        if len(parts) != 2 or _price(parts[1]) is None:
            return "So geht's: <code>/preis ttb 60</code> oder <code>/preis 2 130</code> (Nr. aus /liste)"
        target, value = parts[0], _price(parts[1])
        key = resolve_type(target)
        if key:
            wl["type_max"][key] = value
            return f"💶 {NAMES[key]}: melde ich ab jetzt bis {value:.2f} €."
        i = _find_search(wl, target)
        if i is not None:
            wl["searches"][i]["max"] = value
            return f"💶 „{html.escape(wl['searches'][i]['text'])}“: melde ich ab jetzt bis {value:.2f} €."
        return "Typ oder Suche nicht gefunden. Schau mit /liste nach."

    return "Den Befehl kenne ich nicht. /hilfe zeigt alle."


def process_commands(wl, aufschlag=0.10) -> bool:
    """Neue Telegram-Befehle abholen und beantworten. True, wenn sich die Suchliste geändert hat."""
    def content(d):
        return json.dumps({k: v for k, v in d.items() if k != "update_offset"}, sort_keys=True)

    before, old_offset = content(wl), wl.get("update_offset", 0)
    messages, offset = tg.fetch_updates(old_offset)
    wl["update_offset"] = offset
    for text in messages:
        reply = handle(text, wl, aufschlag)
        if reply:
            tg.send(reply)
    changed = content(wl) != before
    if changed or offset != old_offset:
        save(wl)  # Offset immer speichern, sonst würde z. B. /liste bei jedem Lauf neu beantwortet
    return changed
