"""Phone messages through the owner's Telegram bot (SP3 design S6; owner decision 22 Oct 2026).

A failed send is retried 3 times and logged, and never stops the engine. Messages carry public market levels
and the system's own suggestions only: never credentials, account data or broker positions.
"""

import logging
import time

import requests

from quantdesk.config import MissingSecretError, get_secret

log = logging.getLogger(__name__)
API = "https://api.telegram.org/bot{token}/{method}"
ATTEMPTS = 3


class NullNotifier:
    """Used when no bot is configured: the dashboard still shows everything."""

    def send(self, text: str) -> bool:
        return False


class Telegram:
    def __init__(self, token: str, chat_id: str, http_post=None, sleep=time.sleep):
        self.token, self.chat_id = token, chat_id
        self.post = http_post or requests.post
        self.sleep = sleep

    def send(self, text: str) -> bool:
        url = API.format(token=self.token, method="sendMessage")
        for attempt in range(ATTEMPTS):
            try:
                response = self.post(url, json={"chat_id": self.chat_id, "text": text}, timeout=10)
                if response.status_code == 200:
                    return True
                log.warning("telegram send failed: HTTP %s", response.status_code)
            except (requests.RequestException, ConnectionError, TimeoutError, OSError) as exc:
                log.warning("telegram send failed: %s", exc)
            self.sleep(2 ** attempt)
        return False


def notifier_from_env():
    try:
        return Telegram(get_secret("TELEGRAM_BOT_TOKEN"), get_secret("TELEGRAM_CHAT_ID"))
    except MissingSecretError:
        return NullNotifier()


def find_chat_id(token: str, http_get=None) -> str | None:
    """The chat of the latest message the bot received: the owner sends it one message first."""
    get = http_get or requests.get
    response = get(API.format(token=token, method="getUpdates"), timeout=10)
    updates = response.json().get("result", [])
    chats = [u["message"]["chat"]["id"] for u in updates if "message" in u]
    return str(chats[-1]) if chats else None


def _hhmm(at) -> str:
    return at.strftime("%H:%M") if hasattr(at, "strftime") else str(at)[11:16]


def format_kill(reasons: str, at) -> str:
    return (f"KILL SWITCH {_hhmm(at)}: {reasons}\n"
            "New alerts are shadow only from now (do not trade them).\n"
            "Open trades keep their exit messages. Lift it on the dashboard with a typed reason.")


def format_alert(a: dict) -> str:
    shadow = " (SHADOW - do not trade)" if a.get("mode") == "shadow" else ""
    return (f"ALERT{shadow} {_hhmm(a['at'])}\n"
            f"BUY {a['index']} {a['strike']:.0f} {a['kind']} exp {a['expiry']}, {a['lot']} qty\n"
            f"Limit up to Rs {a['entry_limit']:.2f} (lapses in 5 min)\n"
            f"Index stop {a['index_stop']:.1f}, plan target {a['index_target']:.1f}\n"
            f"Backstop SL-limit: trigger {a['backstop_trigger']:.2f}, limit {a['backstop_limit']:.2f}\n"
            f"p {a['p']:.2f}, EV Rs {a['ev']:.0f}\n"
            f"For: {a.get('reasons_for') or '-'}\nAgainst: {a.get('reasons_against') or '-'}")


def format_prealert(index: str, side: str, at) -> str:
    return f"Setup forming {_hhmm(at)}: {index} {side} near its band. An alert may follow at the next check."


def format_ratchet(index: str, index_stop: float, trigger: float, at) -> str:
    return (f"MOVE STOP {_hhmm(at)}: {index} index stop to {index_stop:.1f}; "
            f"move your SL-limit trigger to Rs {trigger:.2f}")


def format_exit(index: str, reason: str, at) -> str:
    return f"EXIT NOW {_hhmm(at)}: {index} position ({reason}). Sell at the bid."


def format_summary(day, alerts: int, paper_r: float, mode: str) -> str:
    return f"{day}: {alerts} alert(s), paper result {paper_r:+.2f}R. Mode: {mode}."
