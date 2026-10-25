# Pokémon 30 Jahre – Restock-Bot (AT / DACH / EU)

Prüft Shops auf Produkte von „Pokémon 30 Jahre" / „30th Celebration" und schickt einen
Telegram-Ping, sobald etwas **lieferbar** ist und **höchstens UVP + 10 %** kostet.
Scalper-Preise werden ignoriert. Läuft gratis auf GitHub Actions, nicht auf deinem Gerät.

Basiert auf luneeo-de/pokemon-restock-bot (Code geprüft am 25.10.2026), erweitert um Regionen.

## Die drei Varianten

Umgeschaltet wird mit **einer** Variable `REGION` (GitHub → Settings → Secrets and variables →
Actions → Tab *Variables*):

| REGION | Shops | Sprache | Hinweis |
|---|---|---|---|
| `AT` (Standard) | 19 österreichische | Deutsch | liefern alle nach AT |
| `DACH` | 67 (AT + DE + CH) | Deutsch | viele DE-Shops liefern nach AT, CH-Shops fast nie |
| `EU` | 91 (DACH + NL, BE, FR, IT, ES, PT, FI) | Deutsch + Englisch | Versand nach AT vor dem Kauf prüfen |

Weitere Variablen (optional):
- `MAX_AUFSCHLAG_PROZENT` – erlaubter Aufschlag auf die UVP, Standard `10`
- `SPRACHEN` – `de`, `en` oder `de,en` (bei EU automatisch `de,en`)
- `CHF_FAKTOR` – Umrechnung Schweizer Preise, Standard `1.0` (CHF 54.95 ≈ UVP 55 €)

## Einrichtung (ca. 20 Minuten, am Laptop)

1. **Telegram-Bot anlegen:** In Telegram `@BotFather` öffnen → `/newbot` → Namen vergeben →
   Token kopieren. Dann deinem neuen Bot `/start` schreiben.
2. **Chat-ID holen:** `python3 setup_telegram.py <TOKEN>` – du bekommst eine Testnachricht
   und die Chat-ID wird angezeigt.
3. **GitHub:** Neues Repository anlegen (**öffentlich**, sonst reichen die Gratis-Minuten nicht),
   diesen Ordner hochladen.
4. **Secrets eintragen:** Settings → Secrets and variables → Actions → *New repository secret*:
   `TELEGRAM_TOKEN` und `TELEGRAM_CHAT_ID`. Secrets bleiben auch bei öffentlichem Repo geheim.
5. **Variable `REGION`** auf `AT`, `DACH` oder `EU` setzen (Tab *Variables*).
6. **Shop-Test:** Tab *Actions* → *Restock-Check* → *Run workflow* → Haken bei „Nur Shop-Test" →
   Telegram zeigt, welche Shops funktionieren.
7. Fertig – ab jetzt prüft der Bot automatisch rund um die Uhr.

## Lokal testen

```
DRY_RUN=1 REGION=AT python3 bot.py
DRY_RUN=1 REGION=EU SHOP_TEST=1 python3 bot.py
```

## Was der Bot NICHT kann

- Große Ketten (MediaMarkt, Smyths, Kaufland, Amazon, Pokémon Center) blocken automatische
  Abfragen von GitHub-Servern – die musst du selbst im Auge behalten.
- Er kauft nichts und braucht keine Zugangsdaten zu Shops. Gib ihm auch nie welche.
- Jeden Tag um 9 Uhr kommt ein Lebenszeichen. Ist ein Shop ~1 Stunde nicht erreichbar, kommt
  eine Warnung.
- GitHub pausiert geplante Abläufe nach 60 Tagen ohne Commit – dann im Tab *Actions* wieder
  aktivieren.
