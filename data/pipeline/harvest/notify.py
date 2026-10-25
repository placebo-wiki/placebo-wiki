"""Failure alerts: Telegram when PLACEBO_TG_TOKEN and PLACEBO_TG_CHAT are set, otherwise a log next to the base."""
import json
import os
import urllib.request

from base import DB, now


def alert(text: str) -> None:
    token, chat = os.environ.get("PLACEBO_TG_TOKEN"), os.environ.get("PLACEBO_TG_CHAT")
    if token and chat:
        body = json.dumps({"chat_id": chat, "text": text}).encode()
        urllib.request.urlopen(urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=body,
                                                      headers={"Content-Type": "application/json"}), timeout=30)
        return
    with open(DB.parent / "alerts.log", "a", encoding="utf-8") as f:
        f.write(f"{now()} {text}\n")
