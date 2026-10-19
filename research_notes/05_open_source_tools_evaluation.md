# 05. Open-source tools evaluation: TradingAgents, OpenBB, Fincept Terminal

Checked 19 Oct 2026, at the owner's request. None of these tools has been installed yet.

## Facts checked

| | TradingAgents | OpenBB (ODP) | Fincept Terminal |
|---|---|---|---|
| Repo | [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) | [openbq-org/OpenBB](https://github.com/openbq-org/OpenBB) | [Fincept-Corporation/FinceptTerminal](https://github.com/Fincept-Corporation/FinceptTerminal) |
| Stars, last push | ~112k, 16 Oct 2026 | ~74k, 18 Oct 2026 | ~33k, 13 Oct 2026 |
| Version | v0.7.0 (Oct 2026) | PyPI `openbb` 5.0.0 | v4.5.1 |
| License | Apache-2.0 | Apache-2.0 (README) | AGPL-3.0 open build; Enterprise is closed source |
| What it is | LangGraph multi-agent LLM "trading firm": analysts → bull/bear debate → trader → risk team → portfolio manager | Python data platform unifying many providers; REST API; MCP server (`openbb-mcp-server`) | C++20/Qt6 desktop "Bloomberg-like" terminal: analytics, 37 AI agents, 100+ data connectors, paper trading, broker links |
| LLMs | OpenAI, Anthropic, Gemini, Ollama (local) and many others | n/a (serves data to agents) | Bring-your-own key, incl. Anthropic and Ollama |
| India | Any Yahoo ticker (`^NSEI`, `RELIANCE.NS`); fundamentals tool is SEC EDGAR (US only) | Via the yfinance provider (prices only); macro via FRED/IMF/OECD etc. | Secondary sources claim 13 Indian brokers incl. Angel One and Zerodha (**not verified** in official docs) |
| Indian options | **No.** Yahoo returns no option chains for `^NSEI` or `RELIANCE.NS` (tested 19 Oct 2026). | **No** NSE option data | Unclear. Would come only through broker links. |
| Decision cadence | Daily (one decision per ticker per date) | n/a | Interactive |
| Backtest | Daily, scored from the next close; non-deterministic | n/a | Backtesting is Enterprise-only |

**Repository identity check.** The owner was given an `openbq-org` link. `OpenBB-finance/OpenBB` redirects to `openbq-org/OpenBB`: same GitHub repo ID 323048702, created 2020-12-20. This is the official repository after an org rename, not a copy.

## Evidence caveats (from earlier rounds)

- TradingAgents' published Sharpe (5.6–8.2) comes from one 3-month bullish window (Jan–Mar 2024) on 5 US tech stocks. Slippage is not modelled.
- LLM look-ahead and memorisation bias are not yet tested for TradingAgents ([Look-Ahead-Bench](https://arxiv.org/pdf/2601.13770)). Most LLM agents failed to beat buy-and-hold in a 2025 benchmark ([survey](https://arxiv.org/html/2605.19337v1)).
- So an honest evaluation must be **forward-only** (decisions logged before the open), never a historical replay.

## Fit with our system

- **TradingAgents → "Analyst desk" (proposed SP4).**
  - A daily pre-market Nifty/Sensex brief with a bull/bear/risk debate.
  - Its tools are rewired to our own data: technical engine, macro engine, Angel One option-chain stats, Indian news RSS. The US fundamentals analyst is disabled.
  - Explanation and caution flags only. It has no vote in the trade until a forward shadow test supports one.
  - Its daily call (direction + confidence) is logged every day from the start, because the forward-test clock is the binding constraint.
- **OpenBB → global and macro data layer in SP1 (section 5.7a), plus an MCP server for research sessions.** All Indian market and option data stays with Angel One.
- **Fincept Terminal → a standalone research terminal the owner can install and use alongside our dashboard.** It is not wired into the engine (C++ desktop app, AGPL). Broker credentials entered there are the owner's choice and responsibility.

## Forward-test power (daily directional call)

- Distinguishing 58% from 50% daily accuracy needs about 250 trading days for roughly 2.5 standard errors.
- About 100 days gives only about 1.6 SE.
- So expect a usable verdict on the analyst desk after about 1 year of daily shadow logging.
