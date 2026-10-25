"""Pokémon-Restock-Bot.

Prüft alle Shops aus shops.py, ordnet die Treffer dem Katalog zu und schickt einen
Telegram-Ping, sobald ein gesuchtes Produkt lieferbar ist UND höchstens die Preisgrenze kostet.
Was gesucht wird, steht in watchlist.json und lässt sich per Telegram-Befehl ändern (watchlist.py).
Gepingt wird nur beim Wechsel „nicht kaufbar → kaufbar", nicht bei jedem Lauf.

Umgebungsvariablen:
  TELEGRAM_TOKEN, TELEGRAM_CHAT_ID   – ohne die wird nur in die Konsole geschrieben
  MAX_AUFSCHLAG_PROZENT              – erlaubter Aufschlag auf die UVP (Standard 10)
  STATE_FILE                         – Pfad zur Zustandsdatei (Standard state.json)
  DRY_RUN=1                          – nichts senden, nur anzeigen
  LOOP_MINUTES, INTERVAL_SECONDS     – Dauerschleife (GitHub: 30 Min. lang alle 3 Min.)
  REGION                             – AT (Standard), DACH oder EU
  SPRACHEN                           – de (Standard) oder de,en (siehe catalog.py)
  CHF_FAKTOR                         – rechnet Schweizer Preise auf € um (siehe unten)
  SHOP_TEST=1                        – jeden Shop einmal abfragen und Bericht schicken
"""

import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from zoneinfo import ZoneInfo

import tg
import watchlist
from catalog import CATALOG_VERSION, NAMES, SEARCH_QUERIES, classify, is_pokemon, is_relevant, languages, \
    matches_search, uvp_for
from shops import FLAGS, select_shops

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0 Safari/537.36")
AUFSCHLAG = float(os.environ.get("MAX_AUFSCHLAG_PROZENT", "10")) / 100
STATE_FILE = os.environ.get("STATE_FILE", os.path.join(os.path.dirname(__file__), "state.json"))
TZ = ZoneInfo("Europe/Vienna")
REGION = os.environ.get("REGION", "AT").strip().upper() or "AT"
SHOPS = select_shops(REGION)
SHOP_TEST = os.environ.get("SHOP_TEST") == "1"
# Schweizer Shops rechnen in CHF. Der günstigste Schweizer Preis (Smyths CH, CHF 54.95)
# entspricht fast genau der €-UVP (54.99 €), darum Standard 1.0. Höher = strenger, niedriger = großzügiger.
CHF_FAKTOR = float(os.environ.get("CHF_FAKTOR", "1.0"))

AVAILABLE = ("instock", "preorder", "presale", "limitedavailability", "onlineonly")

# Viele Shops lassen „PreOrder"/„InStock" in den Seitendaten stehen, obwohl das Kontingent weg ist.
# Steht so etwas im sichtbaren Seitentext, gilt der Artikel als NICHT bestellbar.
NOT_ORDERABLE = re.compile(
    r"benachrichtig\w*[^.<\"“”„]{0,25}(sobald|wenn)[^.<\"“”„]{0,30}(verfügbar|lieferbar|wieder|erhältlich)"
    r"|nicht mehr (verfügbar|lieferbar|bestellbar|erhältlich)|nicht vorrätig|vergriffen", re.I)


def visible_text(page: str) -> str:
    page = re.sub(r"<script.*?</script>|<style.*?</style>|<noscript.*?</noscript>", " ", page, flags=re.S | re.I)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", page)))


def fetch(url: str, accept: str = "text/html") -> str:
    url = urllib.parse.quote(url, safe=":/?&=%#+,;@[]")  # Umlaute in Pfaden (z. B. Alternate)
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": accept, "Accept-Language": "de-DE,de;q=0.9"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", errors="ignore")


def price_limit(uvp: float) -> float:
    return round(uvp * (1 + AUFSCHLAG) + 0.01, 2)


def to_price(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace("€", "").replace("\xa0", "").strip()
    if "," in s:  # deutsches Format 1.234,56
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def availability_of(value):
    """schema.org-Availability → True / False / None (unbekannt) + Vorbestellung?"""
    if not value:
        return None, False
    v = str(value).lower().rsplit("/", 1)[-1]
    return v in AVAILABLE, v in ("preorder", "presale")


# ---------- JSON-LD / Microdata ----------

def jsonld_products(page: str):
    out = []

    def walk(o):
        if isinstance(o, dict):
            t = o.get("@type")
            if t == "Product" or (isinstance(t, list) and "Product" in t):
                out.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    for block in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', page, re.S):
        try:
            walk(json.loads(block.strip()))
        except json.JSONDecodeError:
            continue
    return out


def offer_of(product: dict):
    offers = product.get("offers")
    if isinstance(offers, list):
        offers = offers[0] if offers else None
    if isinstance(offers, dict) and offers.get("@type") == "AggregateOffer":
        return to_price(offers.get("lowPrice") or offers.get("price")), offers.get("availability")
    if isinstance(offers, dict):
        return to_price(offers.get("price")), offers.get("availability")
    return None, None


def parse_detail(page: str, text_check: bool = True):
    """Titel, Preis, Verfügbarkeit, Vorbestellung aus einer Produktseite."""
    title = price = avail = None
    for p in jsonld_products(page):
        title = title or p.get("name")
        pr, av = offer_of(p)
        price = price if price is not None else pr
        avail = avail or av
    if not title:
        m = re.search(r'property="og:title"\s+content="([^"]*)"', page)
        title = m.group(1) if m else None
    if avail is None:  # Microdata (z. B. JTL-Shops)
        m = re.search(r'itemprop="availability"\s+(?:href|content)="([^"]*)"', page)
        avail = m.group(1) if m else None
    if price is None:
        m = re.search(r'itemprop="price"\s+content="([^"]*)"', page)
        price = to_price(m.group(1)) if m else None
    ok, pre = availability_of(avail)
    if ok and text_check and NOT_ORDERABLE.search(visible_text(page)):
        ok = False
    return (html.unescape(title).strip() if title else None), price, ok, pre


# ---------- Shop-Abfragen ----------

WATCH = watchlist.default_watchlist()  # wird in main() aus watchlist.json geladen


def queries_for(shop):
    """Suchbegriffe für einen Shop: eigene aus shops.py + Standard-Suchen + eigene Telegram-Suchen."""
    qs = list(shop.get("queries", []))
    if shop.get("generic", True):
        for lang in sorted(languages()):
            qs += SEARCH_QUERIES.get(lang, [])
        qs += [s["text"] for s in WATCH["searches"]]
    return list(dict.fromkeys(q.strip().lower() for q in qs if q.strip()))


def offer(shop, title, url, price, available, preorder=False):
    currency = shop.get("currency", "EUR")
    title = title or ""
    key = classify(title)
    return {"shop": shop["name"], "land": shop.get("land", "DE"), "title": title,
            "url": urllib.parse.urljoin(shop["base"], url), "price": price, "currency": currency,
            "available": available, "preorder": preorder, "key": key,
            "uvp": uvp_for(key, title) if key else None}


def eur_price(o):
    """Preis auf die €-UVP-Skala umgerechnet (CHF-Shops), sonst unverändert."""
    if o["price"] is None:
        return None
    return o["price"] * CHF_FAKTOR if o.get("currency") == "CHF" else o["price"]


def check_shopify(shop):
    seen, out = set(), []
    for q in queries_for(shop):
        url = (f"{shop['base']}/search/suggest.json?q={urllib.parse.quote(q)}"
               "&resources[type]=product&resources[limit]=10")
        data = json.loads(fetch(url, "application/json"))
        for p in data["resources"]["results"]["products"]:
            u = p["url"].split("?")[0]  # Shopify hängt den Suchbegriff an den Link → sonst Doppel-Pings
            if u in seen:
                continue
            seen.add(u)
            out.append(offer(shop, p["title"], u, to_price(p.get("price")), bool(p.get("available"))))
        time.sleep(0.3)
    return out


def check_detail(shop, url):
    page = fetch(url)
    title, price, ok, pre = parse_detail(page, shop.get("text_check", True))
    # Shops ohne strukturierte Daten: eigene Regexe aus shops.py
    if shop.get("price_regex") and price is None:
        m = re.search(shop["price_regex"], page)
        price = to_price(m.group(1)) if m else None
    # Optional: Text, der nur auf wirklich bestellbaren Seiten steht (z. B. Warenkorb-Button)
    if ok and shop.get("require_text") and not re.search(shop["require_text"], visible_text(page)):
        ok = False
    if shop.get("avail_regex") and ok is None:
        m = re.search(shop["avail_regex"], page)
        ok = bool(m) and m.group(1) in shop.get("avail_ok", ["available"])
    if not title:
        return None
    return offer(shop, title, url, price, ok, pre)


def check_links(shop):
    page = fetch(shop["url"])
    links = list(dict.fromkeys(re.findall(shop["link_pattern"], page)))[:30]
    with ThreadPoolExecutor(6) as ex:
        return [o for o in ex.map(lambda u: check_detail(shop, urllib.parse.urljoin(shop["base"], html.unescape(u))), links) if o]


def check_jsonld(shop):
    out, seen = [], set()
    urls = ([shop["search_url"].format(q=urllib.parse.quote_plus(q)) for q in queries_for(shop)]
            if shop.get("search_url") else [shop["url"]])
    for page_url in urls:
        for p in jsonld_products(fetch(page_url)):
            title = html.unescape(p.get("name") or "")
            link = p.get("url") or ""
            if (link or title) in seen:
                continue
            seen.add(link or title)
            price, av = offer_of(p)
            ok, pre = availability_of(av)
            out.append(offer(shop, title, link, price, ok, pre))
    # Unbekannte Verfügbarkeit nur bei preislich interessanten Treffern auf der Produktseite nachprüfen
    todo = [o for o in out if o["available"] is None and target(o) and o["price"] and within_limit(o)]
    for o in todo[:10]:
        try:
            _, pr, ok, pre = parse_detail(fetch(o["url"]), shop.get("text_check", True))
            o["available"], o["preorder"] = ok, pre
            o["price"] = pr or o["price"]
        except Exception as e:  # noqa: BLE001
            print(f"  Detail {o['url']}: {e}", file=sys.stderr)
    return out


def check_lidl(shop):
    out, seen = [], set()
    for q in queries_for(shop):
        url = (f"{shop['base']}/q/api/search?assortment={shop.get('assortment', 'DE')}"
               f"&locale={shop.get('locale', 'de_DE')}&version=v2.0.0&fetchsize=48&q=" + urllib.parse.quote(q))
        for item in json.loads(fetch(url, "*/*")).get("items", []):  # Lidl antwortet auf application/json mit 401
            if item.get("resultClass") != "product":
                continue
            d = item.get("gridbox", {}).get("data", {})
            link = d.get("canonicalUrl") or ""
            if not link or link in seen:
                continue
            seen.add(link)
            badges = [b.get("type") for b in (d.get("stockAvailability", {}).get("badgeInfo", {}) or {}).get("badges", [])]
            out.append(offer(shop, d.get("fullTitle") or "", link, to_price((d.get("price") or {}).get("price")),
                             "AVAILABLE_ONLINE" in badges))
    return out


CHECKERS = {"shopify": check_shopify, "links": check_links, "jsonld": check_jsonld, "lidl": check_lidl}


# ---------- Was wird gesucht, was ist kaufbar ----------

def target(o):
    """Passt das Angebot zu etwas, das gesucht wird? → (Bezeichnung, Preisgrenze oder None) bzw. None.

    Eigene Suchen (/suche) haben Vorrang vor den Produkttypen.
    """
    if not is_relevant(o["title"]):
        return None
    for s in WATCH["searches"]:
        if matches_search(o["title"], s["text"]) and (o["key"] or is_pokemon(o["title"])):
            limit = s.get("max") or (price_limit(o["uvp"]) if o["uvp"] else None)
            return "🔎 " + s["text"], limit
    if o["key"] and o["key"] in WATCH["types"]:
        own = WATCH["type_max"].get(o["key"])
        return NAMES[o["key"]], own or price_limit(o["uvp"])
    return None


def within_limit(o) -> bool:
    t = target(o)
    if not t or o["price"] is None:
        return False
    limit = t[1]
    price = eur_price(o)
    # Viel zu billig = falsch zugeordnet (z. B. Einzelkarte statt Box)
    if o["uvp"] and price < o["uvp"] * 0.4:
        return False
    return limit is None or price <= limit


def is_buyable(o) -> bool:
    return bool(o["available"]) and within_limit(o)


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"offers": {}, "errors": {}, "summary_date": None}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)


def fmt_offer(o) -> str:
    label = target(o)[0]
    tag = " · Vorbestellung" if o["preorder"] else ""
    flag = FLAGS.get(o.get("land", "DE"), "")
    if o.get("currency") == "CHF":
        preis = f"CHF {o['price']:.2f}"
        rel = f"≈ {eur_price(o):.2f} € auf €-Skala"
    elif o["uvp"]:
        diff = o["price"] - o["uvp"]
        preis = f"{o['price']:.2f} €"
        rel = "zur UVP" if abs(diff) < 0.5 else f"{diff:+.2f} € ggü. UVP {o['uvp']:.2f} €"
    else:
        preis, rel = f"{o['price']:.2f} €", "UVP unbekannt"
    return (f"<b>{html.escape(label)}</b>\n"
            f"🛒 {flag} {html.escape(o['shop'])}: <b>{preis}</b> ({rel}){tag}\n"
            f"{html.escape(o['title'])}\n"
            f"👉 {html.escape(o['url'])}")


SEND_FAILURES = []  # Telegram-Fehler sammeln; am Ende wird der Lauf rot, statt mittendrin abzubrechen


def safe_send(text: str) -> bool:
    try:
        tg.send(text)
        return True
    except SystemExit:
        raise  # Token/Chat-ID fehlen ganz → sofort rot
    except Exception as e:  # noqa: BLE001
        SEND_FAILURES.append(str(e)[:200])
        print(f"Telegram-Fehler: {e}", file=sys.stderr)
        return False


def send_alerts(alerts):
    """Bis zu 5 Treffer einzeln, mehr als Sammelnachricht. Gibt die Links zurück, die NICHT ankamen."""
    failed = set()
    if len(alerts) <= 5:
        for o in alerts:
            if not safe_send("🚨 <b>Jetzt bestellbar!</b>\n\n" + fmt_offer(o)):
                failed.add(o["url"])
        return failed
    chunk, members = f"🚨 <b>{len(alerts)} Angebote jetzt bestellbar</b>\n", []
    for o in alerts:
        part = "\n\n" + fmt_offer(o)
        if len(chunk) + len(part) > 3900:
            if not safe_send(chunk):
                failed.update(members)
            chunk, members = "🚨 <b>Fortsetzung</b>", []
        chunk += part
        members.append(o["url"])
    if not safe_send(chunk):
        failed.update(members)
    return failed


def shop_interval(shop) -> float:
    # Seltener fragen, wo viele Abrufe nötig sind (sonst droht Sperre):
    # Produktseiten einzeln (links) und Shopify mit mehreren Suchbegriffen alle 9 Min.
    return shop.get("every", 540 if shop["type"] in ("links", "shopify") else 0)


def run_once(state):
    now = datetime.now(TZ)
    found, errors, skipped = [], {}, set()
    last = state.setdefault("last_checked", {})

    for shop in SHOPS:
        if time.time() - last.get(shop["name"], 0) < shop_interval(shop) - 30:
            skipped.add(shop["name"])
            continue
        last[shop["name"]] = time.time()
        try:
            res = CHECKERS[shop["type"]](shop)
            found += res
            hits = sum(1 for o in res if target(o))
            print(f"{shop['name']:20} {len(res):3} Treffer, {hits:2} gesucht")
        except Exception as e:  # noqa: BLE001
            errors[shop["name"]] = str(e)[:200]
            print(f"{shop['name']:20} FEHLER: {e}", file=sys.stderr)
        time.sleep(0.2)
    # Übersprungene Shops behalten ihren bisherigen Fehlerstatus
    for name in skipped:
        if name in state.get("errors", {}):
            errors[name] = state["errors"][name]["msg"]

    # Neue Katalogversion: einmal still durchlaufen, damit nicht alles Lieferbare auf einmal gemeldet wird
    silent = state.get("catalog_version") != CATALOG_VERSION

    new_alerts, current = [], {}
    # Angebote von Shops, die gerade nicht antworten oder diesmal übersprungen wurden, behalten –
    # sonst gäbe es beim nächsten Abruf einen doppelten Ping
    seen_urls = {o["url"] for o in found}
    for url, v in state["offers"].items():
        if v["shop"] in errors or v["shop"] in skipped:
            current[url] = v
        elif url not in seen_urls and v.get("miss", 0) < 2:
            # Kurz verschwunden (Ladefehler, Captcha)? Noch 2 Durchgänge merken, sonst Doppel-Ping
            current[url] = dict(v, miss=v.get("miss", 0) + 1)
    for o in found:
        if not is_buyable(o) or o["url"] in current:  # gleicher Link doppelt im Ergebnis
            continue
        label = target(o)[0]
        current[o["url"]] = {"price": o["price"], "label": label, "shop": o["shop"], "title": o["title"],
                             "currency": o.get("currency", "EUR")}
        before = state["offers"].get(o["url"])
        if before is None or o["price"] < before["price"] - 0.5 or before.get("label") != label:
            new_alerts.append(o)

    if silent:
        if new_alerts:
            safe_send(f"ℹ️ Erkennung aktualisiert: {len(new_alerts)} Angebote sind gerade schon lieferbar. "
                      "Die melde ich nicht einzeln – ab jetzt kommen nur neue. Übersicht morgen um 9 Uhr.")
        state["catalog_version"] = CATALOG_VERSION
    else:
        for url in send_alerts(new_alerts):
            # Nicht angekommen → beim nächsten Durchgang nochmal versuchen
            if state["offers"].get(url):
                current[url] = state["offers"][url]
            else:
                current.pop(url, None)

    # Shop dauerhaft kaputt? Einmal Bescheid geben, wenn er seit 1 Stunde am Stück nicht antwortet
    prev_err = state.get("errors", {})
    for name, msg in list(errors.items()):
        prev = prev_err.get(name) or {}
        since = prev.get("since") or now.isoformat()
        warned = prev.get("warned", False)
        if not warned and (now - datetime.fromisoformat(since)).total_seconds() >= 3600:
            warned = safe_send(f"⚠️ {html.escape(name)} lässt sich seit ca. 1 Stunde nicht abfragen:\n{html.escape(msg)}")
        errors[name] = {"since": since, "warned": warned, "msg": msg}

    # Tägliches Lebenszeichen um 9 Uhr
    today = now.strftime("%Y-%m-%d")
    if now.hour == 9 and state.get("summary_date") != today:
        lines = [f"☀️ Restock-Bot ({REGION}) läuft. {len(SHOPS) - len(errors)}/{len(SHOPS)} Shops erreichbar."]
        if current:
            lines.append(f"\nAktuell zu fairen Preisen lieferbar ({len(current)}):")
            for v in sorted(current.values(), key=lambda v: v.get("label", ""))[:20]:
                cur = "CHF" if v.get("currency") == "CHF" else "€"
                lines.append(f"• {html.escape(v.get('label', ''))} – {html.escape(v['shop'])} {v['price']:.2f} {cur}")
            if len(current) > 20:
                lines.append(f"… und {len(current) - 20} weitere")
        else:
            lines.append("Gerade nichts Gesuchtes zu fairen Preisen lieferbar.")
        lines.append("\n/liste zeigt, was ich suche · /hilfe alle Befehle")
        if safe_send("\n".join(lines)):
            state["summary_date"] = today

    state["offers"], state["errors"], state["last_run"] = current, errors, now.isoformat()
    save_state(state)
    print(f"\n{now:%H:%M} – {len(SHOPS) - len(skipped)} Shops, {len(found)} Angebote geprüft, "
          f"{len(current)} kaufbar, {len(new_alerts)} neu{' (still)' if silent else ''}.\n")


def shop_test():
    """Jeden Shop einmal abfragen und zeigen, ob er antwortet und Gesuchtes findet."""
    ok, leer, kaputt = [], [], []
    for shop in SHOPS:
        try:
            res = CHECKERS[shop["type"]](shop)
            hits = [o for o in res if target(o)]
            (ok if hits else leer).append(f"{shop['name']} ({len(hits)})")
            print(f"OK    {shop['name']:24} {len(res):3} Treffer, {len(hits):2} gesucht")
        except Exception as e:  # noqa: BLE001
            kaputt.append(f"{shop['name']}: {str(e)[:60]}")
            print(f"FEHLER {shop['name']:24} {e}", file=sys.stderr)
        time.sleep(0.2)
    text = (f"🧪 <b>Shop-Test Region {html.escape(REGION)}</b> – {len(SHOPS)} Shops\n\n"
            f"✅ Findet Gesuchtes ({len(ok)}): {html.escape(', '.join(ok)) or '–'}\n\n"
            f"🟡 Antwortet, aber nichts Gesuchtes ({len(leer)}): {html.escape(', '.join(leer)) or '–'}\n\n"
            f"❌ Nicht erreichbar ({len(kaputt)}):\n" + html.escape("\n".join(kaputt) or "–"))
    if len(text) > 4000:  # Telegram-Limit 4096 Zeichen; kein halbes &amp; stehen lassen
        text = text[:4000]
        if text.rfind("&") > text.rfind(";"):
            text = text[:text.rfind("&")]
        text += " …"
    tg.send(text)  # Shop-Test: Fehler hier sollen den Lauf rot machen


def main():
    """LOOP_MINUTES>0: so lange wiederholt prüfen (alle INTERVAL_SECONDS), sonst genau einmal."""
    global WATCH
    WATCH = watchlist.load()
    print(f"Region {REGION}: {len(SHOPS)} Shops · Typen {WATCH['types']} · {len(WATCH['searches'])} eigene Suchen")
    if SHOP_TEST:
        shop_test()
        return
    loop_until = time.time() + float(os.environ.get("LOOP_MINUTES", "0")) * 60
    interval = float(os.environ.get("INTERVAL_SECONDS", "180"))
    state = load_state()
    while True:
        started = time.time()
        if commands(WATCH):
            # Geänderte Suche sofort überall prüfen, nicht erst nach 9 Minuten
            state["last_checked"] = {}
        run_once(state)
        if time.time() + interval > loop_until:
            break
        time.sleep(max(0, interval - (time.time() - started)))
    commands(WATCH)
    if SEND_FAILURES:
        sys.exit(f"Telegram hat {len(SEND_FAILURES)} Nachricht(en) abgelehnt, zuletzt: {SEND_FAILURES[-1]}")


def commands(wl) -> bool:
    try:
        return watchlist.process_commands(wl, AUFSCHLAG)
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001
        SEND_FAILURES.append(f"Befehle: {e}"[:200])
        print(f"Telegram-Befehle nicht abrufbar: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    main()
