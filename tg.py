"""Telegram: Nachrichten senden und Befehle abholen."""

import json
import os
import urllib.parse
import urllib.request

DRY_RUN = os.environ.get("DRY_RUN") == "1"
_sent_in_dry_run = []  # für Tests


def _creds():
    return os.environ.get("TELEGRAM_TOKEN", "").strip(), os.environ.get("TELEGRAM_CHAT_ID", "").strip()


def _api(method: str, params: dict) -> dict:
    token, _ = _creds()
    body = urllib.parse.urlencode(params).encode()
    with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/{method}", body, timeout=25) as r:
        return json.loads(r.read().decode())


def configured() -> bool:
    token, chat = _creds()
    return bool(token and chat)


def send(text: str):
    """Schickt eine Nachricht. Fehlen Token/Chat-ID, bricht der Lauf ab (roter Haken statt stillem Grün)."""
    if DRY_RUN:
        _sent_in_dry_run.append(text)
        print("---- (DRY_RUN, nicht gesendet) ----\n" + text + "\n")
        return
    if not configured():
        raise SystemExit("TELEGRAM_TOKEN oder TELEGRAM_CHAT_ID fehlt – bitte die GitHub-Secrets prüfen.")
    _, chat = _creds()
    _api("sendMessage", {"chat_id": chat, "text": text, "parse_mode": "HTML", "disable_web_page_preview": "true"})


def fetch_updates(offset: int):
    """Neue Nachrichten an den Bot (nur aus dem eigenen Chat). Gibt (nachrichten, neuer_offset) zurück."""
    if DRY_RUN or not configured():
        return [], offset
    _, chat = _creds()
    data = _api("getUpdates", {"offset": offset, "timeout": 0, "allowed_updates": '["message"]'})
    messages, new_offset = [], offset
    for upd in data.get("result", []):
        new_offset = max(new_offset, upd["update_id"] + 1)
        msg = upd.get("message") or {}
        # Nur Befehle aus deinem eigenen Chat annehmen – fremde Leute könnten den Bot sonst steuern
        if str((msg.get("chat") or {}).get("id")) == chat and msg.get("text"):
            messages.append(msg["text"])
    return messages, new_offset
