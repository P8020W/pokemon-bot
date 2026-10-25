"""Produktkatalog „Pokémon 30 Jahre" / „30th Celebration" mit UVP.

Ein Shop-Titel wird über Schlüsselwörter einem Produkt zugeordnet.
Reihenfolge zählt: spezifische Produkte zuerst, der Einzelbooster ganz zum Schluss.
UVP-Quellen: Gameshop Marli / Monsterdealz / TCGcheck (Stand Oktober 2026).

Welche Sprachausgaben zählen, steuert die Umgebungsvariable SPRACHEN:
  "de"     – nur deutsche Edition (Standard)
  "de,en"  – deutsche und englische Edition (sinnvoll für die Europa-Variante)
  "en"     – nur englische Edition
"""

import os
import re
import unicodedata

# (key, Anzeigename, UVP in €, Pflicht-Schlüsselwörter DE + EN (eins davon muss vorkommen))
PRODUCTS = [
    ("upc", "Ultra-Premium-Kollektion (Tag/Nacht)", 199.99, ["ultra-premium", "ultra premium", "upc"]),
    ("ditto", "Premium-Kollektion Ditto", 46.99, ["ditto"]),
    ("figur", "Figuren-Kollektion Mew/Mewtu", 35.99, ["figuren-kollektion", "figuren kollektion", "figure collection"]),
    ("ttb", "Top-Trainer-Box", 55.00, ["top-trainer", "top trainer", "elite trainer", "ttb", "etb"]),
    ("minitin_display", "Mini-Tin Display (10 Tins)", 139.90, ["mini-tin display", "mini tin display", "mini-tin-display"]),
    ("bundle", "Boosterbundle (6 Booster)", 29.99, ["bundle"]),
    ("minitin", "Mini-Tin-Box", 13.99, ["mini-tin", "mini tin", "minitin"]),
    ("tin", "Tin-Box Feelinara-ex / Quajutsu-ex", 24.99,
     ["tin-box", "tin box", "tin #", "tin 1", "tin 2", "tin -", "tin tag", "tin nacht", " tin "]),
    ("deck", "Kampfdeck Psiana-ex / Nachtara-ex", 25.99, ["kampfdeck", "battle deck"]),
    ("ordner", "Ordner-Kollektion", 46.99, ["ordner", "binder"]),
    ("poster", "Poster-Kollektion", 23.99, ["poster"]),
    ("sticker", "Tech-Sticker-Kollektion", 19.99, ["sticker"]),
    ("knockout", "Knock-out-Kollektion", 12.99, ["knock-out", "knock out", "knockout"]),
    ("blister", "2er-Pack-Blister", 12.99, ["2er", "blister", "2-pack"]),
    ("ex", "Kollektion Feelinara-ex / Quajutsu-ex", 24.99,
     ["feelinara", "quajutsu", "ex-kollektion", "ex kollektion", "sylveon", "greninja", "ex box"]),
    ("booster", "Einzelbooster", 4.99, ["booster"]),
]

UVP = {k: uvp for k, _, uvp, _ in PRODUCTS}
NAMES = {k: name for k, name, _, _ in PRODUCTS}

# Immer raus: andere Sprachen, Einzelkarten, Leerboxen, Pokémon-Center-Exklusivware, Zubehör usw.
EXCLUDE = [
    "japan", " jp", "(jp)", "chinesisch", "chinese", "t-chinese", "s-chinese", "koreanisch", "korean",
    "thai", "indonesisch", "franzosisch", "francais", "french", "(fr)", " fr ", "italienisch", "italiano",
    "italian", "(it)", "spanisch", "espanol", "spanish", "(es)", "portugues", "nederlands", "(nl)", "polski",
    "pokemon center", "einzelkarte", "single card", "graded", "psa ", "cgc ", "leer", "empty", "ohne booster",
    "kartenhullen", "sleeves", "kuscheltier", "plusch", "plush", "puzzle", "select-serie", "first partner",
    "multipack", "sortiert", "wizard", "acryl", " case", "schutzhulle", "schutzbox", "protector",
    "magnetic", "toploader", "aufbewahrung", "x booster", "x30", "lot ",
]
# Raus, wenn Englisch NICHT erlaubt ist
EXCLUDE_EN = ["englisch", "english", "(en)", " en ", " en,", " eng ", "(eng)"]
# Raus, wenn Deutsch NICHT erlaubt ist
EXCLUDE_DE = ["deutsch", "(de)", " de ", "30 jahre", "30-jahre"]


def languages():
    return {s.strip().lower() for s in os.environ.get("SPRACHEN", "de").split(",") if s.strip()}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return " " + re.sub(r"\s+", " ", text) + " "


def is_30_jahre(title: str, langs=None) -> bool:
    langs = langs or languages()
    t = normalize(title)
    if any(x in t for x in EXCLUDE):
        return False
    if "en" not in langs and any(x in t for x in EXCLUDE_EN):
        return False
    if "de" not in langs and any(x in t for x in EXCLUDE_DE):
        return False
    if "de" in langs:
        if "30 jahre" in t or "30-jahre" in t:
            return True
        # Manche Shops schreiben „30th … (Deutsch)"
        if ("30th" in t or "jubilaum" in t) and ("deutsch" in t or "(de)" in t or " de " in t):
            return True
    if "en" in langs:
        if "30th celebration" in t or "30th anniversary" in t:
            return True
    return False


# Alter Name, falls jemand ihn noch benutzt
def is_german_30_jahre(title: str) -> bool:
    return is_30_jahre(title, {"de"})


def classify(title: str, langs=None):
    """Gibt den Produkt-Key zurück oder None, wenn kein passendes 30-Jahre-Produkt."""
    if not is_30_jahre(title, langs):
        return None
    t = normalize(title)
    # Displays/Kisten mit mehreren Einheiten nur, wenn ausdrücklich im Katalog
    if "display" in t and "mini" not in t:
        return None
    for key, _, _, words in PRODUCTS:
        if any(w in t for w in words):
            return key
    return None
