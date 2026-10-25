# Pokémon Restock-Bot (AT / DACH / EU)

Prüft Shops auf Pokémon-Produkte und schickt einen Telegram-Ping, sobald etwas **lieferbar** ist
und **höchstens die Preisgrenze** kostet (Standard: UVP + 10 %). Scalper-Preise werden ignoriert.
Läuft gratis auf GitHub Actions, nicht auf deinem Gerät.

Basiert auf luneeo-de/pokemon-restock-bot (Code geprüft am 25.10.2026), erweitert um Regionen,
alle Produkttypen und Telegram-Befehle.

## Was gemeldet wird

**Produkttypen** (Standard an: Top-Trainer-Box, UPC, Boosterbundle, Display):

| Typ | Schlüssel | UVP-Basis |
|---|---|---|
| Ultra-Premium-Kollektion | `upc` | 149,99 € (30 Jahre: 199,99 €) |
| Top-Trainer-Box | `ttb` | 54,99 € |
| Booster-Display | `display` | Anzahl Booster × 4,99 € |
| Boosterbundle | `bundle` | 29,99 € |
| 3er-Blister | `blister3` | 15,99 € |
| Premium-Kollektion | `premium` | 46,99 € |
| Mini-Tin-Display | `minitin_display` | 139,90 € |
| Tin-Box / Mini-Tin | `tin` / `minitin` | 24,99 € / 13,99 € |
| Kollektion | `kollektion` | 24,99 € |
| Einzelbooster | `booster` | 4,99 € |

Plus **eigene Suchen** per Telegram (siehe unten).

## Telegram-Befehle

Im Chat mit deinem Bot:

| Befehl | Wirkung |
|---|---|
| `/liste` | zeigt, was gerade gesucht wird |
| `/suche mega glurak upc bis 160` | eigenes Produkt suchen, bis 160 € |
| `/stopp 1` | eigene Suche Nr. 1 löschen |
| `/preis ttb 60` | Top-Trainer-Boxen bis 60 € melden |
| `/an tin` · `/aus display` | Typ melden / nicht mehr melden |
| `/hilfe` | alle Befehle |

Der Bot liest Befehle **alle paar Minuten**, nicht sofort. Die Suchliste steht in `watchlist.json`
und wird nach jedem Lauf automatisch im Repo gespeichert.

## Einrichtung

1. Telegram: bei `@BotFather` mit `/newbot` einen Bot anlegen, Token sichern, dem Bot `/start` schreiben.
2. Chat-ID von `@userinfobot` holen.
3. GitHub: öffentliches Repo, alle Dateien hochladen (inkl. Ordner `.github`).
4. Settings → Secrets and variables → Actions:
   - Secrets: `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID`
   - Variable: `REGION` = `AT`, `DACH` oder `EU`
5. Actions → Restock-Check → Run workflow → Haken „Nur Shop-Test" → Bericht kommt per Telegram.

Weitere Variablen (optional): `MAX_AUFSCHLAG_PROZENT` (Standard 10), `SPRACHEN` (`de`, `en`, `de,en`),
`CHF_FAKTOR` (Standard 1.0).

## Gut zu wissen

- **Nach einem Update** läuft der Bot einmal „still": Was schon lieferbar ist, wird nicht einzeln
  gemeldet (sonst kämen auf einen Schlag dutzende Nachrichten). Danach nur noch Neues.
- **Täglich um 9 Uhr** kommt ein Lebenszeichen mit allem, was gerade zu fairen Preisen lieferbar ist.
- Fehlen Token oder Chat-ID, wird der Lauf **rot** (früher blieb er still grün).
- **Shopify-Shops, Müller und Lidl** suchen alle Produkttypen. Shops vom Typ „links" (z. B. Card-Corner,
  Gate to the Games) finden weiterhin **nur „30 Jahre"**, weil ihre Suchmuster fest eingestellt sind.
- Große Ketten (MediaMarkt, Smyths, Kaufland, Amazon, Pokémon Center, Otto) blocken automatische Abfragen.
- Müller/Lidl zeigen im Shop-Test oft „0" – evtl. lädt die Suche per JavaScript. Nicht darauf verlassen.
- Der Bot kauft nichts und braucht keine Shop-Zugangsdaten. Gib ihm nie welche.
- GitHub pausiert geplante Abläufe nach 60 Tagen ohne Commit – dann im Tab *Actions* wieder aktivieren.

## Lokal testen

```
DRY_RUN=1 REGION=AT python3 bot.py
DRY_RUN=1 REGION=DACH SHOP_TEST=1 python3 bot.py
```
