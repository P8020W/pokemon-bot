"""Produktkatalog: erkennt Pokémon-Produkttypen in Shop-Titeln und kennt ihre UVP.

Ein Titel wird über Schlüsselwörter einem Produkttyp zugeordnet. Die Reihenfolge zählt:
spezifische Typen zuerst (z. B. „Mini-Tin-Display" vor „Display", „Boosterbundle" vor „Booster").

UVP-Stand Oktober 2026 (deutsche Ausgabe):
  Top-Trainer-Box 52,99 € (Dunkelnacht; Spezialsets etwas mehr → 54,99 € als Basis),
  Boosterbundle 29,99 €, 3er-Blister 15,99 €, Einzelbooster 4,99 €,
  Display = Anzahl Booster × 4,99 € (18er ≈ 89,82 €, 36er ≈ 179,64 €).
  UPC schwankt je nach Ausgabe stark → 149,99 € als Basis, Sonderausgaben über SET_UVP.
Wer eine andere Grenze will, setzt sie per Telegram: /preis ttb 60

Welche Sprachausgaben zählen, steuert die Umgebungsvariable SPRACHEN:
  "de" (Standard) · "de,en" · "en"
"""

import os
import re
import unicodedata

CATALOG_VERSION = 2  # erhöhen, wenn sich die Erkennung stark ändert → ein stiller Durchlauf ohne Pings

BOOSTER_UVP = 4.99

# (key, Anzeigename, UVP in €, Schlüsselwörter – eins davon muss im Titel vorkommen)
PRODUCTS = [
    ("upc", "Ultra-Premium-Kollektion", 149.99, ["ultra premium", "ultrapremium", "upc"]),
    ("ttb", "Top-Trainer-Box", 54.99, ["top trainer", "toptrainer", "elite trainer", "etb", "ttb"]),
    ("minitin_display", "Mini-Tin-Display", 139.90, ["mini tin display", "minitin display"]),
    ("display", "Booster-Display", 179.64, ["display", "booster box", "boosterbox"]),
    ("bundle", "Boosterbundle", 29.99, ["bundle"]),
    ("blister3", "3er-Blister", 15.99, ["3er blister", "3 pack blister", "3 booster blister", "3er pack",
                                         "3 pack", "3er booster"]),
    ("premium", "Premium-Kollektion", 46.99, ["premium kollektion", "premium collection"]),
    ("minitin", "Mini-Tin", 13.99, ["mini tin", "minitin"]),
    ("tin", "Tin-Box", 24.99, ["tin box", "tinbox", " tin "]),
    ("kollektion", "Kollektion", 24.99, ["kollektion", "collection"]),
    ("booster", "Einzelbooster", BOOSTER_UVP, ["booster"]),
]

# Typen, die der Bot ohne eigene Einstellung meldet. Rest per /an <typ> zuschaltbar.
DEFAULT_TYPES = ["ttb", "upc", "bundle", "display"]

# Abweichende UVP für bestimmte Sets: (Wort im Titel, Typ) → UVP
SET_UVP = {
    ("30 jahre", "upc"): 199.99, ("30th", "upc"): 199.99,
    ("30 jahre", "ttb"): 55.00, ("30th", "ttb"): 55.00,
    ("30 jahre", "premium"): 46.99, ("30th", "premium"): 46.99,
}

UVP = {k: uvp for k, _, uvp, _ in PRODUCTS}
NAMES = {k: name for k, name, _, _ in PRODUCTS}
TYPE_ALIASES = {  # was man bei /an, /aus, /preis eintippen darf
    "ttb": "ttb", "etb": "ttb", "toptrainer": "ttb", "top-trainer-box": "ttb",
    "upc": "upc", "ultra": "upc",
    "display": "display", "box": "display",
    "bundle": "bundle", "boosterbundle": "bundle",
    "blister": "blister3", "blister3": "blister3",
    "premium": "premium", "minitin": "minitin", "mini-tin": "minitin",
    "minitin_display": "minitin_display", "tin": "tin", "kollektion": "kollektion", "booster": "booster",
}

# Suchbegriffe, mit denen die Shops abgefragt werden (je Sprache)
SEARCH_QUERIES = {
    "de": ["pokemon top trainer box", "pokemon booster bundle", "pokemon ultra premium kollektion",
           "pokemon display deutsch"],
    "en": ["pokemon elite trainer box", "pokemon ultra premium collection", "pokemon booster box"],
}

# Erkennt „Pokémon" auch ohne das Wort selbst – über bekannte Setnamen
POKEMON_WORDS = [
    "pokemon", "mega entwicklung", "fatale flammen", "erhabene helden", "optimale ordnung", "wachsendes chaos",
    "dunkelnacht", "30 jahre", "prismatische entwicklungen", "reisegefahrten", "ewige rivalen", "weisse flammen",
    "schwarze blitze", "stellarkrone", "nebel der sagen", "mega evolution", "phantasmal flames", "ascended heroes",
    "perfect order", "chaos rising", "pitch black", "30th celebration", "prismatic evolutions", "journey together",
    "destined rivals", "black bolt", "white flare",
]
OTHER_TCG = ["one piece", "lorcana", "magic the gathering", "mtg", "yu gi oh", "yugioh", "dragon ball", "digimon",
             "flesh and blood", "star wars", "riftbound", "union arena", "weiss schwarz", "gundam", "disney",
             "sorcery", "altered", "metazoo", "final fantasy", "naruto", "vanguard"]

# Immer raus: andere Sprachen, Einzelkarten, Leerboxen, Pokémon-Center-Ware, Zubehör usw.
EXCLUDE = [
    "japan", " jp ", "(jp)", "chinesisch", "chinese", "koreanisch", "korean", "thai", "indonesisch",
    "franzosisch", "francais", "french", "(fr)", " fr ", "italienisch", "italiano", "italian", "(it)",
    "spanisch", "espanol", "spanish", "(es)", "portugues", "nederlands", "(nl)", "polski",
    "pokemon center", "einzelkarte", "single card", "graded", "psa ", "cgc ", "leer ", "empty", "ohne booster",
    "kartenhullen", "sleeves", "kuscheltier", "plusch", "plush", "puzzle", "multipack", "sortiert",
    "acryl", " case", "schutzhulle", "schutzbox", "protector", "magnetic", "toploader", "aufbewahrung",
    "lot ", "replica", "sammelalbum", "portfolio", "ordner", "binder", "playmat", "spielmatte",
]
EXCLUDE_EN = ["englisch", "english", "(en)", " en ", " en,", " eng ", "(eng)"]
EXCLUDE_DE = ["deutsch", "(de)", " de "]


def languages():
    return {s.strip().lower() for s in os.environ.get("SPRACHEN", "de").split(",") if s.strip()}


def normalize(text: str) -> str:
    """Kleinbuchstaben, ohne Akzente, Bindestriche/Satzzeichen → Leerzeichen, mit Rand-Leerzeichen."""
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode().lower()
    text = re.sub(r"[-_/:|,;!+]", " ", text)
    return " " + re.sub(r"\s+", " ", text).strip() + " "


def is_relevant(title: str, langs=None) -> bool:
    """Pokémon-Produkt in einer erlaubten Sprache und kein Zubehör/Einzelkarte?"""
    langs = langs or languages()
    t = normalize(title)
    if any(x in t for x in OTHER_TCG) or any(x in t for x in EXCLUDE):
        return False
    if "en" not in langs and any(x in t for x in EXCLUDE_EN):
        return False
    if "de" not in langs and any(x in t for x in EXCLUDE_DE):
        return False
    return True


def is_pokemon(title: str) -> bool:
    t = normalize(title)
    return any(w in t for w in POKEMON_WORDS)


def _has(t: str, word: str) -> bool:
    """Kurze Kürzel (ttb, etb, upc …) nur als ganzes Wort, sonst wäre „Bettbezug" eine Top-Trainer-Box."""
    w = word.strip()
    return f" {w} " in t if len(w) <= 4 else word in t


def classify(title: str, langs=None):
    """Produkttyp-Key oder None. „Top-Trainer-Box"/„UPC" gelten auch ohne das Wort Pokémon."""
    if not title or not is_relevant(title, langs):
        return None
    t = normalize(title)
    for key, _, _, words in PRODUCTS:
        if any(_has(t, w) for w in words):
            if key in ("ttb", "upc") or is_pokemon(title):
                return key
            return None
    return None


def uvp_for(key: str, title: str) -> float:
    """UVP für diesen Titel (Display nach Booster-Anzahl, Sonder-UVP für bestimmte Sets)."""
    t = normalize(title)
    if key == "display":
        m = re.search(r"\b(18|24|36)\s?(er|x|booster|packs?)\b", t)
        return round(int(m.group(1)) * BOOSTER_UVP, 2) if m else UVP["display"]
    for (word, k), uvp in SET_UVP.items():
        if k == key and word in t:
            return uvp
    return UVP[key]


def matches_search(title: str, text: str) -> bool:
    """Eigene Suche (/suche): alle Wörter des Suchtexts müssen im Titel vorkommen."""
    t = normalize(title)
    words = [w for w in normalize(text).split() if len(w) > 1 and w != "pokemon"]
    joined = t.replace(" ", "")
    # Wortanfang muss passen („glurak" in „Mega-Glurak"); zusammengeschrieben nur bei längeren Wörtern
    return bool(words) and all(f" {w}" in t or (len(w) >= 5 and w in joined) for w in words)


def resolve_type(word: str):
    return TYPE_ALIASES.get((word or "").strip().lower())
