"""Phase 0 desk pilot (spec §7A.3): measure TradingAgents on Groq's free tier, then pick Path A or B.

Standard library only, so the separate .venv-desk (which runs TradingAgents) can import it too.
"""

import re
from collections import defaultdict, deque

GROQ_TPM = 7000          # Groq free tier: input tokens per minute for qwen3.8-27b (seen in a 413, 21 Oct 2026)
CLIENT_TPM = 6500        # our client-side ceiling, below Groq's
DAILY_TOKEN_LIMIT = 150_000
MIN_RUNS = 5
COMPLETION_NEEDED = 0.9


class TokenBucket:
    """Sliding 60 s window of tokens sent to one model. acquire() blocks until the request fits.
    A request larger than the whole limit waits for an empty window, goes alone, and is counted."""

    def __init__(self, limit: int = CLIENT_TPM, window_s: float = 60, *, clock, sleep):
        self.limit = limit
        self.window_s = window_s
        self.clock = clock
        self.sleep = sleep
        self.sent: deque = deque()  # (time, tokens)
        self.oversize = 0

    def _drop_old(self, now) -> None:
        while self.sent and (now - self.sent[0][0]).total_seconds() >= self.window_s:
            self.sent.popleft()

    def acquire(self, tokens: int) -> float:
        waited = 0.0
        if tokens > self.limit:
            self.oversize += 1
        while True:
            now = self.clock.now()
            self._drop_old(now)
            used = sum(t for _, t in self.sent)
            if used + tokens <= self.limit or not self.sent:
                self.sent.append((now, tokens))
                return waited
            wait = self.window_s - (now - self.sent[0][0]).total_seconds()
            self.sleep(wait)
            waited += wait

    def adjust(self, delta: int) -> None:
        """Replace an estimate with the real usage once the response arrives."""
        if delta:
            self.sent.append((self.clock.now(), delta))


class PilotMeter:
    """Per-run counts the pilot needs beyond TradingAgents' own StatsCallbackHandler."""

    def __init__(self):
        self.calls: dict[str, int] = defaultdict(int)
        self.tokens: dict[str, int] = defaultdict(int)
        self.largest_request_tokens = 0
        self.errors = {"413": 0, "429": 0, "other": 0}

    def started(self, model: str) -> None:
        self.calls[model] += 1

    def finished(self, model: str, tokens_in: int, tokens_out: int) -> None:
        total = int(tokens_in) + int(tokens_out)
        self.tokens[model] += total
        self.largest_request_tokens = max(self.largest_request_tokens, total)

    def failed(self, error: BaseException) -> None:
        text = str(error).lower()
        if "413" in text or "too large" in text:
            self.errors["413"] += 1
            requested = re.search(r"requested (\d+)", text)  # Groq states the rejected request's size
            if requested:
                self.largest_request_tokens = max(self.largest_request_tokens, int(requested.group(1)))
        elif "429" in text or "rate_limit" in text or "rate limit" in text:
            self.errors["429"] += 1
        else:
            self.errors["other"] += 1

    def summary(self) -> dict:
        return {"calls": dict(self.calls), "tokens": dict(self.tokens),
                "largest_request_tokens": self.largest_request_tokens, "errors": dict(self.errors)}


def decide(runs: list[dict]) -> dict:
    """Spec §7A.3: Path A if >= 90% of runs complete, no single request exceeds Groq's per-minute limit,
    and no model uses more than 150K tokens in a day (one run per day). Otherwise Path B."""
    if len(runs) < MIN_RUNS:
        # A request over the per-minute limit, or a 413, is a reason no later run can undo: Path B is already certain.
        largest = max((r.get("largest_request_tokens", 0) for r in runs), default=0)
        too_large = sum(r.get("errors", {}).get("413", 0) for r in runs)
        if largest > GROQ_TPM or too_large:
            return {"path": "B", "runs": len(runs), "largest_request_tokens": largest,
                    "reasons": [f"decided early after {len(runs)} runs: {too_large} request(s) rejected as too large "
                                f"(HTTP 413), largest {largest} tokens against the per-minute limit of {GROQ_TPM}"]}
        return {"path": "undecided", "reasons": [f"{len(runs)} of {MIN_RUNS} runs so far"], "runs": len(runs)}
    reasons = []
    completed = sum(1 for r in runs if r.get("completed"))
    if completed / len(runs) < COMPLETION_NEEDED:
        reasons.append(f"only {completed}/{len(runs)} runs completed (need {COMPLETION_NEEDED:.0%})")
    too_large = sum(r.get("errors", {}).get("413", 0) for r in runs)
    if too_large:
        reasons.append(f"{too_large} request(s) were too large for Groq's per-minute input limit (HTTP 413)")
    largest = max(r.get("largest_request_tokens", 0) for r in runs)
    if largest > GROQ_TPM:
        reasons.append(f"a single request used {largest} tokens, over the per-minute limit of {GROQ_TPM}")
    daily = max((t for r in runs for t in r.get("tokens", {}).values()), default=0)
    if daily > DAILY_TOKEN_LIMIT:
        reasons.append(f"a model used {daily} tokens in one day, over {DAILY_TOKEN_LIMIT}")
    return {"path": "B" if reasons else "A", "reasons": reasons or ["all three conditions held"],
            "runs": len(runs), "completed": completed, "largest_request_tokens": largest,
            "max_daily_tokens_per_model": daily}
