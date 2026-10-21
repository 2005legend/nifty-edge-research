"""SP4 phase 0 pilot (spec §7A.3): one TradingAgents run on ^NSEI via Groq's free tier, measured.

Runs in the separate .venv-desk (TradingAgents pins its own langchain/pandas):

    .venv-desk\\Scripts\\python desk\\run_pilot.py            # today's run (skipped if already done)
    .venv-desk\\Scripts\\python desk\\run_pilot.py --decide   # print the Path A/B decision so far

Each run appends one line to data/desk_pilot/runs.jsonl and saves the brief under data/desk_pilot/briefs/.
After 10 runs it stops running and only prints the decision. The pilot's briefs are logged, never scored.
Only public market data goes to Groq: no credentials, account data or positions.
"""

import argparse
import json
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from quantdesk.desk.pilot import CLIENT_TPM, PilotMeter, TokenBucket, decide  # noqa: E402

IST = ZoneInfo("Asia/Kolkata")
PILOT_DIR = ROOT / "data" / "desk_pilot"
RUNS = PILOT_DIR / "runs.jsonl"
PILOT_RUNS = 10
QUICK_MODEL = "qwen/qwen3.8-27b"
DEEP_MODEL = "openai/gpt-oss-120b"
MAX_TOKENS = 1500
# The measured settings. Only runs made with exactly these count toward the decision; run 1 (21 Oct 2026,
# TradingAgents defaults of 20 + 10 news articles) stays in the log as evidence that the defaults do not fit:
# one News Analyst request was 8,810 tokens, over Groq's 7,000 input-tokens-per-minute limit (HTTP 413).
PILOT_KNOBS = {"max_debate_rounds": 1, "max_risk_discuss_rounds": 1, "max_tool_rounds": 4,
               "max_tokens": MAX_TOKENS, "news_article_limit": 5, "global_news_article_limit": 5}
INDIA_NEWS_QUERIES = [
    "India stock market Nifty Sensex",
    "RBI monetary policy repo rate India inflation",
    "FII DII flows Indian equities",
    "rupee crude oil India economy",
    "US Federal Reserve Asian markets global risk",
]


class SystemClock:
    def now(self):
        return datetime.now(IST)


def load_runs() -> list[dict]:
    if not RUNS.exists():
        return []
    return [json.loads(line) for line in RUNS.read_text(encoding="utf-8").splitlines() if line.strip()]


def pilot_config() -> dict:
    from tradingagents.default_config import DEFAULT_CONFIG

    config = dict(DEFAULT_CONFIG)
    config.update({
        "llm_provider": "groq",
        "quick_think_llm": QUICK_MODEL,   # analysts, researchers, trader
        "deep_think_llm": DEEP_MODEL,     # managers and judge: a separate Groq limit pool
        **PILOT_KNOBS,
        "llm_max_retries": 4,
        "global_news_queries": INDIA_NEWS_QUERIES,
        "results_dir": str(PILOT_DIR / "ta_results"),
        "data_cache_dir": str(PILOT_DIR / "cache"),
        "memory_log_path": str(PILOT_DIR / "memory" / "trading_memory.md"),
        "checkpoint_enabled": False,
    })
    return config


def make_callbacks(meter: PilotMeter):
    """LangChain adapter: rate-limit every Groq request per model, and measure it."""
    import tiktoken
    from langchain_core.callbacks import BaseCallbackHandler

    encoder = tiktoken.get_encoding("cl100k_base")  # an estimate; Groq's tokenizers differ by ~10-20%
    buckets: dict[str, TokenBucket] = {}
    pending: dict = {}
    waited = {"seconds": 0.0}

    def model_of(serialized, kwargs) -> str:
        params = kwargs.get("invocation_params") or {}
        return (params.get("model") or params.get("model_name")
                or (serialized or {}).get("kwargs", {}).get("model_name") or "unknown")

    def text_of(messages) -> str:
        parts = []
        for batch in messages:
            for message in batch:
                content = getattr(message, "content", "")
                parts.append(content if isinstance(content, str) else json.dumps(content, default=str))
        return "\n".join(parts)

    class PilotCallbacks(BaseCallbackHandler):
        run_inline = True  # block in this thread so the bucket really delays the request
        raise_error = False

        def on_chat_model_start(self, serialized, messages, *, run_id, **kwargs):
            model = model_of(serialized, kwargs)
            estimate = int(len(encoder.encode(text_of(messages))) * 1.1) + MAX_TOKENS
            bucket = buckets.setdefault(model, TokenBucket(CLIENT_TPM, 60, clock=SystemClock(), sleep=time.sleep))
            waited["seconds"] += bucket.acquire(estimate)
            pending[run_id] = (model, estimate)
            meter.started(model)

        def on_llm_end(self, response, *, run_id, **kwargs):
            model, estimate = pending.pop(run_id, ("unknown", 0))
            usage = {}
            try:
                usage = response.generations[0][0].message.usage_metadata or {}
            except (AttributeError, IndexError, TypeError):
                pass
            tokens_in, tokens_out = usage.get("input_tokens", 0), usage.get("output_tokens", 0)
            meter.finished(model, tokens_in, tokens_out)
            if model in buckets:
                buckets[model].adjust(tokens_in + tokens_out - estimate)

        def on_llm_error(self, error, *, run_id, **kwargs):
            pending.pop(run_id, None)
            meter.failed(error)

    return PilotCallbacks(), buckets, waited


def run_once(today: str) -> dict:
    import importlib.metadata

    from cli.stats_handler import StatsCallbackHandler
    from tradingagents.graph.trading_graph import TradingAgentsGraph

    meter = PilotMeter()
    pilot_callbacks, buckets, waited = make_callbacks(meter)
    stats = StatsCallbackHandler()
    graph = TradingAgentsGraph(selected_analysts=["market", "news"], config=pilot_config(),
                               callbacks=[pilot_callbacks, stats])
    started = time.time()
    record = {"date": today, "started_at": datetime.now(IST).isoformat(timespec="seconds"),
              "tradingagents": importlib.metadata.version("tradingagents"),
              "quick_model": QUICK_MODEL, "deep_model": DEEP_MODEL,
              "config": PILOT_KNOBS}
    try:
        state, rating = graph.propagate("^NSEI", today)
        record.update(completed=True, rating=str(rating))
        brief = PILOT_DIR / "briefs" / f"{today}.md"
        brief.parent.mkdir(parents=True, exist_ok=True)
        sections = [("Final decision", state.get("final_trade_decision")),
                    ("Market report", state.get("market_report")), ("News report", state.get("news_report"))]
        brief.write_text("\n\n".join(f"## {title}\n\n{text}" for title, text in sections if text),
                         encoding="utf-8")
    except Exception as exc:  # noqa: BLE001 - a failed run is a pilot result, recorded like any other
        record.update(completed=False, error=f"{type(exc).__name__}: {exc}"[:500],
                      traceback=traceback.format_exc()[-2000:])
    record.update(wall_s=round(time.time() - started, 1), waited_s=round(waited["seconds"], 1),
                  oversize_requests=sum(b.oversize for b in buckets.values()),
                  ta_stats=stats.get_stats(), **meter.summary())
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--decide", action="store_true", help="only print the decision so far")
    args = parser.parse_args()
    runs = [r for r in load_runs() if r.get("config") == PILOT_KNOBS]
    if args.decide or len(runs) >= PILOT_RUNS:
        print(json.dumps(decide(runs), indent=2))
        return 0
    today = datetime.now(IST).date().isoformat()
    if any(r["date"] == today and r.get("completed") for r in runs):
        print(f"pilot run for {today} already done")
        return 0
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
    record = run_once(today)
    RUNS.parent.mkdir(parents=True, exist_ok=True)
    with open(RUNS, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")
    print(json.dumps({k: record.get(k) for k in ("date", "completed", "rating", "wall_s", "waited_s", "calls",
                                                   "tokens", "largest_request_tokens", "errors", "error")},
                     indent=2, default=str))
    print(json.dumps(decide([r for r in load_runs() if r.get("config") == PILOT_KNOBS]), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
