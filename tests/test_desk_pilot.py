from quantdesk.desk.pilot import PilotMeter, TokenBucket, decide
from tests.fakes import FakeClock, FakeSleep
from datetime import datetime
from quantdesk.clock import IST

T0 = datetime(2026, 10, 21, 19, 30, tzinfo=IST)


def test_bucket_admits_within_limit_and_waits_when_full():
    clock = FakeClock(T0)
    sleep = FakeSleep(clock)
    bucket = TokenBucket(limit=7000, window_s=60, clock=clock, sleep=sleep)
    assert bucket.acquire(4000) == 0
    assert bucket.acquire(2500) == 0
    waited = bucket.acquire(2000)  # 8500 > 7000: wait for the first 4000 to leave the window
    assert waited == 60
    assert sleep.calls == [60]


def test_bucket_lets_an_oversize_request_through_alone_and_flags_it():
    clock = FakeClock(T0)
    bucket = TokenBucket(limit=7000, window_s=60, clock=clock, sleep=FakeSleep(clock))
    bucket.acquire(1000)
    bucket.acquire(9000)  # bigger than the whole limit: waits for an empty window, then goes
    assert bucket.oversize == 1


def test_meter_tracks_models_largest_request_and_errors():
    meter = PilotMeter()
    meter.started("qwen/qwen3.8-27b")
    meter.finished("qwen/qwen3.8-27b", tokens_in=5200, tokens_out=800)
    meter.started("openai/gpt-oss-120b")
    meter.finished("openai/gpt-oss-120b", tokens_in=3000, tokens_out=1200)
    meter.failed(RuntimeError("Error code: 413 - Request too large for model"))
    meter.failed(RuntimeError("Error code: 429 - rate_limit_exceeded"))
    meter.failed(RuntimeError("connection reset"))
    stats = meter.summary()
    assert stats["calls"] == {"qwen/qwen3.8-27b": 1, "openai/gpt-oss-120b": 1}
    assert stats["tokens"] == {"qwen/qwen3.8-27b": 6000, "openai/gpt-oss-120b": 4200}
    assert stats["largest_request_tokens"] == 6000
    assert stats["errors"] == {"413": 1, "429": 1, "other": 1}


def run(completed=True, largest=6000, quick=60_000, deep=40_000):
    return {"completed": completed, "largest_request_tokens": largest,
            "tokens": {"qwen/qwen3.8-27b": quick, "openai/gpt-oss-120b": deep}}


def test_decision_path_a_when_every_condition_holds():
    result = decide([run() for _ in range(9)] + [run(completed=False)])
    assert result["path"] == "A"


def test_decision_path_b_when_a_request_exceeds_the_per_minute_limit():
    result = decide([run() for _ in range(9)] + [run(largest=8600)])
    assert result["path"] == "B" and "per-minute" in " ".join(result["reasons"])


def test_decision_path_b_on_too_many_failures_or_daily_tokens():
    assert decide([run() for _ in range(8)] + [run(completed=False)] * 2)["path"] == "B"
    assert decide([run() for _ in range(9)] + [run(quick=151_000)])["path"] == "B"


def test_decision_waits_for_five_runs():
    assert decide([run() for _ in range(4)])["path"] == "undecided"


def test_a_reason_more_runs_cannot_undo_decides_path_b_early():
    """22 Oct 2026: 3 of 3 measured runs failed, with requests up to 20,515 tokens against a 7,000 limit."""
    too_big = dict(run(completed=False, largest=20_515), errors={"413": 2, "429": 0, "other": 0})
    result = decide([too_big] * 3)
    assert result["path"] == "B" and any("early" in r for r in result["reasons"])
    assert decide([run(completed=False)] * 2)["path"] == "undecided"      # failures alone may still recover


def test_a_rejected_413_request_counts_toward_the_largest_request():
    """Live 21 Oct 2026: Groq rejected an 8810-token request (ITPM limit 7000); the meter must see its size."""
    meter = PilotMeter()
    meter.failed(RuntimeError("Error code: 413 - {'error': {'message': 'Request too large for model "
                              "`qwen/qwen3.8-27b` ... on input tokens per minute (ITPM): Limit 7000, "
                              "Requested 8810, please reduce your message size'}}"))
    stats = meter.summary()
    assert stats["largest_request_tokens"] == 8810
    assert stats["errors"]["413"] == 1


def test_any_413_rules_out_path_a():
    runs = [run() for _ in range(9)] + [dict(run(), errors={"413": 1, "429": 0, "other": 0})]
    result = decide(runs)
    assert result["path"] == "B" and any("too large" in r for r in result["reasons"])
