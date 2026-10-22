from datetime import datetime

from quantdesk.clock import IST
from quantdesk.live.notify import NullNotifier, Telegram, find_chat_id, format_alert, format_exit, format_ratchet
from tests.fakes import FakeResponse

AT = datetime(2026, 10, 22, 10, 0, tzinfo=IST)


class Post:
    def __init__(self, fail_first=0):
        self.calls, self.fail_first = [], fail_first

    def __call__(self, url, json, timeout):
        self.calls.append((url, json))
        if len(self.calls) <= self.fail_first:
            raise ConnectionError("down")
        return FakeResponse(200, b'{"ok": true}')


def test_send_posts_to_the_bot_api_and_retries():
    post = Post(fail_first=2)
    bot = Telegram("TOKEN", "42", http_post=post, sleep=lambda s: None)
    assert bot.send("hello") is True
    url, body = post.calls[-1]
    assert url == "https://api.telegram.org/botTOKEN/sendMessage" and body["chat_id"] == "42" and len(post.calls) == 3


def test_a_dead_channel_never_raises():
    bot = Telegram("TOKEN", "42", http_post=Post(fail_first=99), sleep=lambda s: None)
    assert bot.send("hello") is False
    assert NullNotifier().send("x") is False


def test_messages_carry_what_the_owner_needs():
    text = format_alert({"at": AT, "index": "NIFTY", "side": "long", "strike": 22000.0, "kind": "CE",
                         "expiry": "2026-10-27", "lot": 65, "entry_limit": 60.1, "index_stop": 21980.0,
                         "index_target": 22046.0, "backstop_trigger": 53.9, "backstop_limit": 48.5, "p": 0.45,
                         "ev": 120.0, "reasons_for": "technical +1.20", "reasons_against": "", "mode": "live"})
    for piece in ("NIFTY", "22000", "CE", "60.1", "21980", "53.9", "48.5", "10:00"):
        assert piece in text
    assert "21995" in format_ratchet("NIFTY", 21995.0, 55.2, AT)
    assert "exit" in format_exit("NIFTY", "stop", AT).lower()


def test_find_chat_id_reads_the_latest_message():
    body = b'{"ok": true, "result": [{"message": {"chat": {"id": 7}}}, {"message": {"chat": {"id": 99}}}]}'
    assert find_chat_id("T", lambda url, timeout: FakeResponse(200, body)) == "99"
