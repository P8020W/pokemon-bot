"""Pokémon-30-Jahre-Restock-Bot.

Prüft alle Shops aus shops.py, ordnet die Treffer dem Katalog zu und schickt einen
Telegram-Ping, sobald ein Produkt lieferbar ist UND höchstens UVP + Aufschlag kostet.
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

from catalog import NAMES, UVP, classify
from shops import FLAGS, select_shops

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0 Safari/537.36")
AUFSCHLAG = float(os.environ.get("MAX_AUFSCHLAG_PROZENT", "10")) / 100
STATE_FILE = os.environ.get("STATE_FILE", os.path.join(os.path.dirname(__file__), "state.json"))
DRY_RUN = os.environ.get("DRY_RUN") == "1"
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


def price_limit(key: str) -> float:
    return round(UVP[key] * (1 + AUFSCHLAG) + 0.01, 2)


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

def offer(shop, title, url, price, available, preorder=False):
    currency = shop.get("currency", "EUR")
    return {"shop": shop["name"], "land": shop.get("land", "DE"), "title": title,
            "url": urllib.parse.urljoin(shop["base"], url), "price": price, "currency": currency,
            "available": available, "preorder": preorder, "key": classify(title)}


def eur_price(o):
    """Preis auf die €-UVP-Skala umgerechnet (CHF-Shops), sonst unverändert."""
    if o["price"] is None:
        return None
    return o["price"] * CHF_FAKTOR if o.get("currency") == "CHF" else o["price"]


def check_shopify(shop):
    seen, out = set(), []
    for q in shop["queries"]:
        url = (f"{shop['base']}/search/suggest.json?q={urllib.parse.quote(q)}"
               "&resources[type]=product&resources[limit]=10")
        data = json.loads(fetch(url, "application/json"))
        for p in data["resources"]["results"]["products"]:
            if p["url"] in seen:
                continue
            seen.add(p["url"])
            out.append(offer(shop, p["title"], p["url"].split("?")[0], to_price(p.get("price")), bool(p.get("available"))))
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
    out = []
    for p in jsonld_products(fetch(shop["url"])):
        title = p.get("name") or ""
        price, av = offer_of(p)
        ok, pre = availability_of(av)
        out.append(offer(shop, html.unescape(title), p.get("url") or "", price, ok, pre))
    # Unbekannte Verfügbarkeit nur bei preislich interessanten Treffern auf der Produktseite nachprüfen
    todo = [o for o in out if o["available"] is None and o["key"] and o["price"] and eur_price(o) <= price_limit(o["key"])]
    for o in todo:
        try:
            _, pr, ok, pre = parse_detail(fetch(o["url"]), shop.get("text_check", True))
            o["available"], o["preorder"] = ok, pre
            o["price"] = pr or o["price"]
        except Exception as e:  # noqa: BLE001
            print(f"  Detail {o['url']}: {e}", file=sys.stderr)
    return out


def check_lidl(shop):
    out, seen = [], set()
    for q in shop["queries"]:
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


# ---------- Bewertung, Zustand, Telegram ----------

def is_buyable(o) -> bool:
    if not o["key"] or not o["available"] or o["price"] is None:
        return False
    # Viel zu billig = falsch zugeordnet (z. B. Einzelkarte statt Box)
    return UVP[o["key"]] * 0.4 <= eur_price(o) <= price_limit(o["key"])


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"offers": {}, "errors": {}, "summary_date": None}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)


def telegram(text: str):
    token, chat = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if DRY_RUN or not token or not chat:
        print("---- (nicht gesendet) ----\n" + text + "\n")
        return
    body = urllib.parse.urlencode({"chat_id": chat, "text": text, "parse_mode": "HTML",
                                   "disable_web_page_preview": "true"}).encode()
    urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", body, timeout=20).read()


def fmt_offer(o) -> str:
    uvp = UVP[o["key"]]
    tag = " · Vorbestellung" if o["preorder"] else ""
    flag = FLAGS.get(o.get("land", "DE"), "")
    if o.get("currency") == "CHF":
        preis = f"CHF {o['price']:.2f}"
        rel = f"≈ {eur_price(o):.2f} € auf €-UVP-Skala"
    else:
        diff = o["price"] - uvp
        preis = f"{o['price']:.2f} €"
        rel = "zur UVP" if abs(diff) < 0.5 else f"{diff:+.2f} € ggü. UVP"
    return (f"<b>{html.escape(NAMES[o['key']])}</b>\n"
            f"🛒 {flag} {html.escape(o['shop'])}: <b>{preis}</b> ({rel}, UVP {uvp:.2f} €){tag}\n"
            f"{html.escape(o['title'])}\n"
            f"👉 {html.escape(o['url'])}")


def shop_interval(shop) -> float:
    # Shops, bei denen jede Produktseite einzeln abgerufen wird, seltener fragen (sonst droht Sperre)
    return shop.get("every", 540 if shop["type"] == "links" else 0)


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
            hits = sum(1 for o in res if o["key"])
            print(f"{shop['name']:20} {len(res):3} Treffer, {hits:2} zugeordnet")
        except Exception as e:  # noqa: BLE001
            errors[shop["name"]] = str(e)[:200]
            print(f"{shop['name']:20} FEHLER: {e}", file=sys.stderr)
        time.sleep(0.2)
    # Übersprungene Shops behalten ihren bisherigen Fehlerstatus
    for name in skipped:
        if name in state.get("errors", {}):
            errors[name] = state["errors"][name]["msg"]

    new_alerts, current = [], {}
    # Angebote von Shops, die gerade nicht antworten oder diesmal übersprungen wurden, behalten –
    # sonst gäbe es beim nächsten Abruf einen doppelten Ping
    for url, v in state["offers"].items():
        if v["shop"] in errors or v["shop"] in skipped:
            current[url] = v
    for o in found:
        if not is_buyable(o):
            continue
        current[o["url"]] = {"price": o["price"], "key": o["key"], "shop": o["shop"], "title": o["title"],
                             "currency": o.get("currency", "EUR")}
        before = state["offers"].get(o["url"])
        if before is None or o["price"] < before["price"] - 0.5:
            new_alerts.append(o)

    for o in new_alerts:
        telegram("🚨 <b>Jetzt bestellbar!</b>\n\n" + fmt_offer(o))

    # Shop dauerhaft kaputt? Einmal Bescheid geben, wenn er seit 1 Stunde am Stück nicht antwortet
    prev_err = state.get("errors", {})
    for name, msg in list(errors.items()):
        prev = prev_err.get(name) or {}
        since = prev.get("since") or now.isoformat()
        warned = prev.get("warned", False)
        if not warned and (now - datetime.fromisoformat(since)).total_seconds() >= 3600:
            telegram(f"⚠️ {html.escape(name)} lässt sich seit ca. 1 Stunde nicht abfragen:\n{html.escape(msg)}")
            warned = True
        errors[name] = {"since": since, "warned": warned, "msg": msg}

    # Tägliches Lebenszeichen um 9 Uhr
    today = now.strftime("%Y-%m-%d")
    if now.hour == 9 and state.get("summary_date") != today:
        lines = [f"☀️ Restock-Bot ({REGION}) läuft. {len(SHOPS) - len(errors)}/{len(SHOPS)} Shops erreichbar."]
        if current:
            lines.append("\nAktuell zu UVP lieferbar:")
            lines += [f"• {NAMES[v['key']]} – {v['shop']} {v['price']:.2f} {'CHF' if v.get('currency') == 'CHF' else '€'}"
                      for v in current.values()]
        else:
            lines.append("Gerade nichts zu fairen Preisen lieferbar.")
        telegram("\n".join(lines))
        state["summary_date"] = today

    state["offers"], state["errors"], state["last_run"] = current, errors, now.isoformat()
    save_state(state)
    print(f"\n{now:%H:%M} – {len(SHOPS) - len(skipped)} Shops, {len(found)} Angebote geprüft, {len(current)} kaufbar zu UVP, {len(new_alerts)} neue Pings.\n")


def shop_test():
    """Jeden Shop einmal abfragen und zeigen, ob er antwortet und 30-Jahre-Produkte findet."""
    ok, leer, kaputt = [], [], []
    for shop in SHOPS:
        try:
            res = CHECKERS[shop["type"]](shop)
            hits = [o for o in res if o["key"]]
            (ok if hits else leer).append(f"{shop['name']} ({len(hits)})")
            print(f"OK    {shop['name']:24} {len(res):3} Treffer, {len(hits):2} zugeordnet")
        except Exception as e:  # noqa: BLE001
            kaputt.append(f"{shop['name']}: {str(e)[:60]}")
            print(f"FEHLER {shop['name']:24} {e}", file=sys.stderr)
        time.sleep(0.2)
    text = (f"🧪 <b>Shop-Test Region {html.escape(REGION)}</b> – {len(SHOPS)} Shops\n\n"
            f"✅ Funktioniert ({len(ok)}): {html.escape(', '.join(ok)) or '–'}\n\n"
            f"🟡 Antwortet, aber nichts gefunden ({len(leer)}): {html.escape(', '.join(leer)) or '–'}\n\n"
            f"❌ Nicht erreichbar ({len(kaputt)}):\n" + html.escape("\n".join(kaputt) or "–"))
    if len(text) > 4000:  # Telegram-Limit 4096 Zeichen; kein halbes &amp; stehen lassen
        text = text[:4000]
        if text.rfind("&") > text.rfind(";"):
            text = text[:text.rfind("&")]
        text += " …"
    telegram(text)


def main():
    """LOOP_MINUTES>0: so lange wiederholt prüfen (alle INTERVAL_SECONDS), sonst genau einmal."""
    print(f"Region {REGION}: {len(SHOPS)} Shops")
    if SHOP_TEST:
        shop_test()
        return
    loop_until = time.time() + float(os.environ.get("LOOP_MINUTES", "0")) * 60
    interval = float(os.environ.get("INTERVAL_SECONDS", "180"))
    state = load_state()
    while True:
        started = time.time()
        run_once(state)
        if time.time() + interval > loop_until:
            break
        time.sleep(max(0, interval - (time.time() - started)))


if __name__ == "__main__":
    main()
