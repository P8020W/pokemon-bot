"""Shop-Liste. Drei Abfragearten:

- shopify:  Shopify-Suche (/search/suggest.json), liefert Preis + Verfügbarkeit direkt
- jsonld:   Suchseite mit schema.org-Produktdaten; fehlt die Verfügbarkeit, wird die Produktseite geprüft
- links:    Kategorie-/Suchseite → Produktlinks einsammeln → jede Produktseite prüfen

Regionen (Umgebungsvariable REGION): AT = nur Österreich, DACH = AT + DE + CH,
EU = DACH + Shops aus NL, BE, FR, IT, ES, PT, FI.

Neuen Shop hinzufügen = einen Eintrag ergänzen. Shops, die automatische Abfragen
blocken (Stand 18.10.2026: Thalia, Galeria, Kaufland, Smyths, Rossmann, Pokémon Center, Conrad,
Cyberport, Bücher.de, Netto, Aldi, Rewe, Bol, Euronics, Fantasywelt u. a.), fehlen bewusst.
"""

# ---------------- Deutschland ----------------
SHOPS_DE = [
    # Kleine TCG-Shops (Shopify)
    {"name": "Geeks Heaven", "type": "shopify", "base": "https://geeksheaven.de", "queries": ["30 jahre"]},
    {"name": "Starz Collectibles", "type": "shopify", "base": "https://starzcollectibles.de", "queries": ["30 jahre"]},

    # TCG-Fachhändler mit eigener Shop-Software
    # Card-Corner: Hinweistexte („Benachrichtigung … sobald") stehen auf jeder Seite → stattdessen Warenkorb-Button prüfen
    {"name": "Card-Corner", "type": "links", "text_check": False, "require_text": "In den Warenkorb",
     "base": "https://www.card-corner.de",
     "url": "https://www.card-corner.de/pokemon-30-jahre",
     "link_pattern": r'href="(https://www\.card-corner\.de/Pokemon-30-Jahre-[A-Za-z0-9-]+)"'},
    {"name": "Steinehelden", "type": "links", "base": "https://steinehelden.de",
     "url": "https://www.steinehelden.de/search?sSearch=pokemon+30+jahre",
     "link_pattern": r'href="(https://steinehelden\.de/[^"]*30-Jahre[^"]*/\d+)"'},
    {"name": "Alternate", "type": "links", "base": "https://www.alternate.de",
     "url": "https://www.alternate.de/listing.xhtml?q=pokemon+30+jahre",
     "link_pattern": r'href="(https://www\.alternate\.de/[^"]*30-Jahre[^"]*/html/product/\d+)"'},

    # Große Händler
    # MediaMarkt/Saturn funktionieren lokal, blocken aber GitHub-Server (403) – daher aus.
    # {"name": "MediaMarkt", "type": "jsonld", "base": "https://www.mediamarkt.de",
    #  "url": "https://www.mediamarkt.de/de/search.html?query=pokemon%2030%20jahre"},
    # {"name": "Saturn", "type": "jsonld", "base": "https://www.saturn.de",
    #  "url": "https://www.saturn.de/de/search.html?query=pokemon%2030%20jahre"},
    {"name": "Müller", "type": "jsonld", "base": "https://www.mueller.de",
     "url": "https://www.mueller.de/search/?q=pokemon+30+jahre+sammelkarten"},
    {"name": "Otto", "type": "jsonld", "base": "https://www.otto.de",
     "url": "https://www.otto.de/suche/pokemon%2030%20jahre/"},
    {"name": "Lidl", "type": "lidl", "base": "https://www.lidl.de",
     "queries": ["pokemon 30 jahre", "pokemon sammelkarten"]},
    {"name": "EDEKA24", "type": "links", "base": "https://www.edeka24.de",
     "url": "https://www.edeka24.de/index.php?lang=0&cl=search&searchparam=pokemon+30+jahre",
     "link_pattern": r'href="(https://www\.edeka24\.de/Pokemon-[^"?]*30-Jahre[^"?]*\.html)',
     "price_regex": r'<div class="price">\s*([\d.,]+)\s*€',
     "avail_regex": r'<li class="delivery-text product-note ([a-z-]*)"', "avail_ok": ["available"]},

    # Spielwaren
    {"name": "Toys-for-Fun", "type": "links", "base": "https://www.toys-for-fun.com",
     "url": "https://www.toys-for-fun.com/de/catalogsearch/result/?q=pokemon+30+jahre",
     "link_pattern": r'href="(https://www\.toys-for-fun\.com/de/pokemon-[a-z0-9-]*30-jahre[a-z0-9-]*\.html)"'},
    {"name": "Rofu", "type": "links", "base": "https://www.rofu.de",
     "url": "https://www.rofu.de/suche?searchPhrase=pokemon+30+jahre",
     "link_pattern": r'"url":"(https://www\.rofu\.de/[a-z0-9-]*\.html)"'},

    # Weitere TCG-Shops (Shopify)
    {"name": "Cardcosmos", "type": "shopify", "base": "https://cardcosmos.de", "queries": ["30 jahre", "30 jahre top trainer", "30 jahre mini tin"]},
    {"name": "Packhunter", "type": "shopify", "base": "https://packhunter.de", "queries": ["30 jahre"]},
    {"name": "Toy Treasure", "type": "shopify", "base": "https://toy-treasure.com", "queries": ["30 jahre", "30 jahre mini tin"]},
    {"name": "Racoon Rises", "type": "shopify", "base": "https://racoon-rises.com", "queries": ["30 jahre", "30 jahre kollektion"]},
    {"name": "CardBuddys", "type": "shopify", "base": "https://cardbuddys.de", "queries": ["30 jahre"]},
    {"name": "CrispyCards", "type": "shopify", "base": "https://crispycards.de", "queries": ["30 jahre", "30 jahre kollektion"]},
    {"name": "Card-Knights", "type": "shopify", "base": "https://www.card-knights.de", "queries": ["30 jahre deutsch", "30 jahre kollektion", "30 jahre mini tin"]},
    {"name": "JustNerds TCG", "type": "shopify", "base": "https://justnerdstcg.de", "queries": ["30 jahre deutsch", "30 jahre"]},
    {"name": "Trinket Mage", "type": "shopify", "base": "https://trinket-mage.eu", "queries": ["30 jahre", "30 jahre mini tin", "30 jahre top trainer box"]},
    {"name": "KARDS Greifswald", "type": "shopify", "base": "https://kardsgreifswald.de", "queries": ["pokemon 30 jahre", "30 jahre top trainer"]},
    {"name": "Pushdich-TCG", "type": "shopify", "base": "https://www.pushdich-tcg.de", "queries": ["30 jahre", "30 jahre kollektion"]},
    {"name": "Feenturm", "type": "shopify", "base": "https://feenturm.de", "queries": ["30th celebration deutsch"]},
    {"name": "Steelduck", "type": "shopify", "base": "https://www.steelduck.de", "queries": ["30 jahre deutsch", "30 jahre top trainer box", "30 jahre mini tin"]},
    {"name": "Peer-Online", "type": "shopify", "base": "https://www.peer-online.de", "queries": ["30 jahre", "30 jahre mini tin"]},
    {"name": "TradingToys", "type": "shopify", "base": "https://www.tradingtoys.de", "queries": ["30 jahre top trainer box", "30 jahre booster bundle"]},
    {"name": "Prückis Cards", "type": "shopify", "base": "https://pruckis.de", "queries": ["30 jahre", "30 jahre kollektion"]},
    {"name": "Underpaid Collectibles", "type": "shopify", "base": "https://underpaidcollectibles.com", "queries": ["30 jahre", "30 jahre deutsch"]},
    {"name": "Major Cards TCG", "type": "shopify", "base": "https://majorcardstcg.com", "queries": ["30 jahre", "30 jahre kollektion"]},
    {"name": "RocketCardStore", "type": "shopify", "base": "https://rocketcardstore.de", "queries": ["30 jahre"]},
    {"name": "Dirricards", "type": "shopify", "base": "https://dirricards.de", "queries": ["30 jahre top trainer box", "30 jahre kollektion"]},
    {"name": "Brofessor Eich", "type": "shopify", "base": "https://brofessoreich.de", "queries": ["30 jahre", "30 jahre kollektion"]},

    # TCG-/Spieleläden mit eigener Shop-Software
    {"name": "Gate to the Games", "type": "links", "every": 540, "base": "https://www.gate-to-the-games.de",
     "url": "https://www.gate-to-the-games.de/?qs=Pokemon-30-Jahre+deutsch&af=100",
     "link_pattern": r'href="(https://www\.gate-to-the-games\.de/Pokemon-30-Jahre-[^"#]+)"'},
    {"name": "Comic Planet", "type": "links", "every": 540, "base": "https://www.comicplanet.de",
     "url": "https://www.comicplanet.de/search?search=pokemon+30+jahre",
     "link_pattern": r'href="(https://www\.comicplanet\.de/sammelkarten/pokemon/deutsch/[^"]*pokemon-30-jahre-[^"]+)"'},
    {"name": "Spielgetuschel", "type": "links", "every": 540, "base": "https://spielgetuschel.de",
     "url": "https://spielgetuschel.de/?qs=pokemon+30+jahre",
     "link_pattern": r'href="(https://spielgetuschel\.de/Pokemon-30-Jahre-[^"#]+)"'},
    {"name": "TcG Love", "type": "links", "every": 540, "base": "https://tcg-love.de",
     "url": "https://tcg-love.de/?s=%2230+Jahre%22&post_type=product",
     "link_pattern": r'href="(https://tcg-love\.de/pokemon-30-jahre-[^"]+)"'},
    {"name": "Zambomba", "type": "links", "every": 540, "base": "https://www.zambomba.de",
     "url": "https://www.zambomba.de/?s=pokemon+30+jahre&post_type=product",
     "link_pattern": r'href="(https://www\.zambomba\.de/shop/pokemon-30-jahre-[^"]+)"'},
    {"name": "Sonnenstil", "type": "links", "every": 540, "base": "https://sonnenstil.shop",
     "url": "https://sonnenstil.shop/?s=pokemon+30+jahre&post_type=product",
     "link_pattern": r'href="(https://sonnenstil\.shop/products/[^"]*30-jahre[^"]*)"'},
]


# ---------------- Österreich ----------------
# Recherche 25.10.2026. Shopify-Shops sind am zuverlässigsten. MediaMarkt.at und Smyths AT
# blocken laut Original-Autor GitHub-Server – darum hier nicht drin (von Hand beobachten).
SHOPS_AT = [
    {"name": "Prime Protector", "type": "shopify", "base": "https://primeprotector.at", "queries": ["30 jahre"]},
    {"name": "Kamikura TCG", "type": "shopify", "base": "https://kamikuratcg.com", "queries": ["30th celebration de", "30th celebration"]},
    {"name": "MerchFox", "type": "shopify", "base": "https://www.merchfox.at", "queries": ["30 jahre", "30 jahre kollektion"]},
    {"name": "Comic Galerie Wien", "type": "shopify", "base": "https://shop.comic-galerie.at", "queries": ["30 jahre", "30 jahre tin"]},
    {"name": "Cardcorner Krems", "type": "shopify", "base": "https://cardcorner.at", "queries": ["30 jahre deutsch", "30 jahre"]},
    {"name": "Collector's Society 5", "type": "shopify", "base": "https://www.coso5.at", "queries": ["30 jahre"]},
    {"name": "Cardhome", "type": "shopify", "base": "https://cardhome.at", "queries": ["30 jahre"]},
    {"name": "Mikiscardshop", "type": "shopify", "base": "https://www.mikiscardshop.at", "queries": ["30 jahre"]},
    {"name": "S-Games", "type": "shopify", "base": "https://s-games.at", "queries": ["30 jahre"]},
    {"name": "Videogamepalace", "type": "shopify", "base": "https://www.videogamepalace.at", "queries": ["30th celebration", "30 jahre"]},
    {"name": "Pokechest", "type": "shopify", "base": "https://pokechest.at", "queries": ["30 jahre"]},
    {"name": "Lairos", "type": "shopify", "base": "https://lairos.shop", "queries": ["30 jahre"]},
    {"name": "Pokevend", "type": "shopify", "base": "https://pokevend.at", "queries": ["30 jahre"]},
    {"name": "MistiCards", "type": "shopify", "base": "https://misticards.com", "queries": ["30 jahre"]},
    {"name": "Müller AT", "type": "jsonld", "base": "https://www.mueller.at",
     "url": "https://www.mueller.at/search/?q=pokemon+30+jahre+sammelkarten"},
    {"name": "Lidl AT", "type": "lidl", "base": "https://www.lidl.at", "assortment": "AT", "locale": "de_AT",
     "queries": ["pokemon 30 jahre", "pokemon sammelkarten"]},
    {"name": "Grubi & Co", "type": "links", "every": 540, "base": "https://www.grubi-co.at",
     "url": "https://www.grubi-co.at/de/sammelkarten/pokemon/",
     "link_pattern": r'href="((?:https://www\.grubi-co\.at)?/de/sammelkarten/pokemon/[^"]*30-[Jj]ahre[^"]*\.html)"'},
    {"name": "Butticards", "type": "links", "every": 540, "base": "https://www.butticards.at",
     "url": "https://www.butticards.at/Shop/Pokemon-c72181358",
     "link_pattern": r'href="((?:https://www\.butticards\.at)?/Shop/[^"]*30[^"]*-p\d+)"'},
    {"name": "Spielbrett", "type": "links", "every": 540, "base": "https://spielbrett.co.at",
     "url": "https://spielbrett.co.at/search?search=pokemon+30+jahre",
     "link_pattern": r'href="((?:https://spielbrett\.co\.at)?/[^"]*30-Jahre[^"]*)"'},
]

# ---------------- Schweiz (Preise in CHF) ----------------
# Achtung: Fast kein Schweizer Shop liefert nach Österreich (pokecado, zadoys: nur CH/LI).
SHOPS_CH = [
    {"name": "Pokecado", "type": "shopify", "base": "https://www.pokecado.ch", "queries": ["30th celebration", "30 jahre"]},
    {"name": "cardmaniac", "type": "shopify", "base": "https://cardmaniac.ch", "queries": ["30 jahre", "30th celebration"]},
    {"name": "Game Galaxy", "type": "shopify", "base": "https://gamegalaxy.ch", "queries": ["30 jahre", "30th celebration"]},
    {"name": "Pikaversum", "type": "shopify", "base": "https://pikaversum.ch", "queries": ["30th celebration"]},
    {"name": "Lascho Cards", "type": "shopify", "base": "https://laschocards.ch", "queries": ["30th celebration"]},
    {"name": "SparkLeaf TCG", "type": "shopify", "base": "https://sparkleaf.ch", "queries": ["30th celebration"]},
    {"name": "Amazingtoys", "type": "links", "every": 540, "base": "https://amazingtoys.ch",
     "url": "https://amazingtoys.ch/search?search=pokemon+30+jahre",
     "link_pattern": r'href="((?:https://amazingtoys\.ch)?/(?:en/)?[^"]*30-Jahre[^"]*)"'},
    {"name": "Two Moons", "type": "links", "every": 540, "base": "https://www.twomoons.ch",
     "url": "https://www.twomoons.ch/search?search=30th+celebration",
     "link_pattern": r'href="((?:https://www\.twomoons\.ch)?/(?:en/)?30th-celebration[^"]*)"'},
    {"name": "The Uncommon Shop", "type": "links", "every": 540, "text_check": False, "base": "https://theuncommonshop.ch",
     "url": "https://theuncommonshop.ch/?s=pokemon+30th&post_type=product",
     "link_pattern": r'href="(https://theuncommonshop\.ch/(?:en/)?product/[^"]*30th[^"]*/)"'},
    {"name": "TCG Treasure", "type": "links", "every": 540, "text_check": False, "base": "https://tcg-treasure.com",
     "url": "https://tcg-treasure.com/?s=30th+celebration&post_type=product",
     "link_pattern": r'href="(https://tcg-treasure\.com/product/[^"]*30th[^"]*/)"'},
]

# ---------------- Restliches Europa (Euro-Länder) ----------------
# Fast nur englische Ausgabe → Region EU nutzt standardmäßig SPRACHEN=de,en.
# Versand nach Österreich: bestätigt nur bei Senpai Manga Shop (IT); bei den anderen vorher prüfen.
# text_check aus: Die Prüfung auf „nicht vorrätig" kennt nur deutsche Texte.
SHOPS_EU = [
    # Niederlande
    {"name": "Card-Binder", "land": "NL", "type": "shopify", "base": "https://card-binder.com", "queries": ["30 jahre", "30th celebration"]},
    {"name": "PKM Winkel", "land": "NL", "type": "shopify", "base": "https://www.pkmwinkel.nl", "queries": ["30th celebration"]},
    {"name": "Rarecards", "land": "NL", "type": "shopify", "base": "https://rarecards.nl", "queries": ["30th celebration"]},
    {"name": "Dracoon", "land": "NL", "type": "links", "every": 540, "text_check": False, "base": "https://dracoon.nl",
     "url": "https://dracoon.nl/?s=30th+celebration&post_type=product",
     "link_pattern": r'href="(https://dracoon\.nl/product/[^"]*30th[^"]*/)"'},
    {"name": "TCG Company", "land": "NL", "type": "links", "every": 540, "text_check": False, "base": "https://tcgcompany.nl",
     "url": "https://tcgcompany.nl/?s=30th+celebration&post_type=product",
     "link_pattern": r'href="(https://tcgcompany\.nl/[^"]*30th-celebration[^"]*/)"'},
    {"name": "Playingcardshop.eu", "land": "NL", "type": "links", "every": 540, "text_check": False,
     "base": "https://www.playingcardshop.eu",
     "url": "https://www.playingcardshop.eu/catalogsearch/result/?q=30th+celebration",
     "link_pattern": r'href="(https://www\.playingcardshop\.eu/[^"]*30th-celebration[^"]*\.html)"'},
    {"name": "Spellenrijk", "land": "NL", "type": "links", "every": 540, "text_check": False,
     "base": "https://www.spellenrijk.nl",
     "url": "https://www.spellenrijk.nl/zoeken.html?s=30th+celebration",
     "link_pattern": r'href="((?:https://www\.spellenrijk\.nl)?/artikel/\d+/[^"]*30th-celebration[^"]*\.html)"'},
    # Belgien
    {"name": "Outpost Brussels", "land": "BE", "type": "shopify", "base": "https://outpostbrussels.be", "queries": ["30th celebration"]},
    {"name": "Maximus", "land": "BE", "type": "links", "every": 540, "text_check": False, "base": "https://maximus.be",
     "url": "https://maximus.be/?s=30th+celebration&post_type=product",
     "link_pattern": r'href="(https://maximus\.be/product/[^"]*30th[^"]*/)"'},
    {"name": "Panini Belgium", "land": "BE", "type": "links", "every": 540, "text_check": False,
     "base": "https://www.paninibelgium.com",
     "url": "https://www.paninibelgium.com/shp_bel_nl/catalogsearch/result/?q=30th+celebration",
     "link_pattern": r'href="(https://www\.paninibelgium\.com/shp_bel_nl/[^"]*30th-celebration[^"]*\.html)"'},
    # Frankreich
    {"name": "PixelHeart", "land": "FR", "type": "links", "every": 540, "text_check": False, "base": "https://www.pixelheart.eu",
     "url": "https://www.pixelheart.eu/en/?s=30th+celebration&post_type=product",
     "link_pattern": r'href="(https://www\.pixelheart\.eu/(?:en/)?produit/[^"]*30th[^"]*/)"'},
    # Italien
    {"name": "Senpai Manga Shop", "land": "IT", "type": "shopify", "base": "https://senpaimangashop.com", "queries": ["30th celebration"]},
    {"name": "Otakura", "land": "IT", "type": "shopify", "base": "https://otakura.com", "queries": ["30th celebration"]},
    {"name": "Scimmia", "land": "IT", "type": "links", "every": 540, "text_check": False, "base": "https://scimmia.it",
     "url": "https://scimmia.it/?s=30th+celebration&post_type=product",
     "link_pattern": r'href="(https://scimmia\.it/prodotto/[^"]*30th[^"]*/)"'},
    # Spanien
    {"name": "Pokemillon", "land": "ES", "type": "shopify", "base": "https://www.pokemillon.com", "queries": ["30th", "etb 30th"]},
    {"name": "Flash Store", "land": "ES", "type": "links", "every": 540, "text_check": False, "base": "https://flashstore.es",
     "url": "https://flashstore.es/?s=30th&post_type=product",
     "link_pattern": r'href="(https://flashstore\.es/producto/[^"]*30th[^"]*/)"'},
    # Portugal
    {"name": "A Jogar", "land": "PT", "type": "shopify", "base": "https://www.ajogar.com", "queries": ["30th", "30th celebration"]},
    {"name": "Geek Haven", "land": "PT", "type": "shopify", "base": "https://geekhaven.pt", "queries": ["30th celebration"]},
    {"name": "Hypegod", "land": "PT", "type": "shopify", "base": "https://hypegod.pt", "queries": ["30th celebration"]},
    {"name": "Lotus Valley", "land": "PT", "type": "links", "every": 540, "text_check": False, "base": "https://lotusvalley.pt",
     "url": "https://lotusvalley.pt/?s=30th+celebration&post_type=product",
     "link_pattern": r'href="(https://lotusvalley\.pt/produto/[^"]*30th[^"]*/)"'},
    {"name": "TT Modelismo", "land": "PT", "type": "links", "every": 540, "text_check": False, "base": "https://ttmodelismo.com",
     "url": "https://ttmodelismo.com/?s=30th+celebration&post_type=product",
     "link_pattern": r'href="(https://ttmodelismo\.com/shop/[^"]*30th[^"]*/)"'},
    {"name": "Centro Xogo", "land": "PT", "type": "links", "every": 540, "text_check": False,
     "base": "https://www.centroxogo.pt",
     "url": "https://www.centroxogo.pt/catalogsearch/result/?q=30th+celebration",
     "link_pattern": r'href="(https://www\.centroxogo\.pt/[^"]*30th-celebration[^"]*\.html)"'},
    # Finnland
    {"name": "TCG-kauppa", "land": "FI", "type": "links", "every": 540, "text_check": False, "base": "https://www.tcgkauppa.fi",
     "url": "https://www.tcgkauppa.fi/?s=30th+celebration&post_type=product",
     "link_pattern": r'href="(https://www\.tcgkauppa\.fi/tuote/[^"]*30th[^"]*/)"'},
    {"name": "Kauppakeidas", "land": "FI", "type": "links", "every": 540, "text_check": False, "base": "https://www.kauppakeidas.fi",
     "url": "https://www.kauppakeidas.fi/?s=30th+celebration&post_type=product",
     "link_pattern": r'href="(https://www\.kauppakeidas\.fi/tuote/[^"]*30th[^"]*/)"'},
]

for _s in SHOPS_DE:
    _s.setdefault("land", "DE")
for _s in SHOPS_AT:
    _s.setdefault("land", "AT")
for _s in SHOPS_CH:
    _s.setdefault("land", "CH")
    _s.setdefault("currency", "CHF")

FLAGS = {"DE": "🇩🇪", "AT": "🇦🇹", "CH": "🇨🇭", "NL": "🇳🇱", "BE": "🇧🇪", "FR": "🇫🇷", "IT": "🇮🇹",
         "ES": "🇪🇸", "PT": "🇵🇹", "FI": "🇫🇮"}

REGIONEN = {
    "AT": SHOPS_AT,
    "DACH": SHOPS_AT + SHOPS_DE + SHOPS_CH,
    "EU": SHOPS_AT + SHOPS_DE + SHOPS_CH + SHOPS_EU,
}


def select_shops(region: str):
    """Shop-Liste für AT, DACH oder EU (unbekannte Werte → AT)."""
    return REGIONEN.get(region.upper(), SHOPS_AT)


# Alter Name, damit nichts bricht
SHOPS = REGIONEN["DACH"]
