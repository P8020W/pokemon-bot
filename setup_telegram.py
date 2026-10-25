"""Einmalig: Chat-ID für den Telegram-Bot herausfinden und eine Testnachricht schicken.

1. In Telegram @BotFather öffnen → /newbot → Namen vergeben → Token kopieren
2. Den neuen Bot öffnen und ihm „/start" schreiben
3. python3 setup_telegram.py <TOKEN>
"""

import json
import sys
import urllib.parse
import urllib.request

token = sys.argv[1] if len(sys.argv) > 1 else input("Bot-Token: ").strip()
updates = json.load(urllib.request.urlopen(f"https://api.telegram.org/bot{token}/getUpdates", timeout=20))
chats = {u["message"]["chat"]["id"]: u["message"]["chat"].get("first_name", "")
         for u in updates.get("result", []) if "message" in u}
if not chats:
    sys.exit("Keine Nachricht gefunden – schreib dem Bot zuerst „/start“ und starte das Skript erneut.")

chat_id = list(chats)[-1]
body = urllib.parse.urlencode({"chat_id": chat_id, "text": "✅ Pokémon-Restock-Bot ist verbunden. Ab jetzt kommt hier ein Ping, sobald etwas zur UVP lieferbar ist."}).encode()
urllib.request.urlopen(f"https://api.telegram.org/bot{token}/sendMessage", body, timeout=20).read()
print(f"Chat-ID: {chat_id}  (Testnachricht gesendet)")
