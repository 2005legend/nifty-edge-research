# Earlier looks at outcomes, before the registry existed

The design research measured how several trading rules would have paid before SP2 fixed its parameters. Those looks count against the deflated Sharpe ratio, exactly like registry trials (R33): N = N_prior + trials run.

**Counting rule:**
- One count per distinct rule variant whose mean outcome was printed. A rule variant is a trigger, a filter on a trigger, an entry technique or a regime switch.
- Subsets of the same rule count once: periods, long/short, expiry/non-expiry, the two indices.
- Purely descriptive statistics (ranges, base rates, volatility paths) and simulations on synthetic paths (`exit_rules_mc.py`) don't count.

**N_prior = 46** (`gate.n_prior` in `hypotheses.yaml`).

| Source | Section | Rule variants | Count |
|---|---|---|---|
| `entry_timing_measurements_output.txt` | A5 | hourly noise band, V = 1.0 and V = 1.25 | 2 |
| | A6 | limit 0.25σ, limit 0.50σ, limit at band edge, one-hour confirmation | 4 |
| | A7 | aligned with 20-day and 50-day trend | 2 |
| | A10 | after NR4, NR7 or inside day; RSI5 split | 4 |
| | A3, A3b, A4, A8 | move-so-far continuation, rest-of-day form, first hour vs rest, first-hour direction by trend | 4 |
| | B2, B3 | 5-minute band; 15-minute continuation | 2 |
| | D2 | daily trend filter on open-to-close | 1 |
| `regime_timing_measure_output.txt` | A1–A13 | H1 daily proxy by 13 regime variables | 13 |
| | B | switch-off and raise-the-hurdle variants | 2 |
| | C, D | strategy momentum; jump-model good/bad state | 2 |
| `macro_crossasset_checks_output.txt` | 1, 2, 3, 5b, 6, 8, 9 | day of week, turn of month, pre/post-holiday, fade/follow big US moves, Budget/election days, expiry weekday, RBI/FOMC days | 7 |
| `nifty_daily_facts_output.txt` | 4, 5, 6 | gap follow/fade, US session to Nifty, 50-day trend filter | 3 |
| **Total** | | | **46** |

**Not counted:**
- The alert-delay costs (C1). They measure execution on the same rule, and the spec's delay test repeats them.
- The contraction/expansion range statistics (D1).
- The volatility, VIX and volume profiles.
- `exit_rules_mc.py`, which uses synthetic paths only.

**Parameters chosen after these looks** are marked `after_full_sample_look` in `hypotheses.yaml`:
- the shock thresholds and their Δ and duration
- the slow-trend jump model's λ and Δ

Any regime add-on built on them must also pass the clean forward holdout before it goes live.

**Consequence, stated up front.** With N = 46 + trials, the DSR ≥ 0.95 gate needs a much larger out-of-sample Sharpe than at N = 10. Pilot P10 computes the chance of passing before any trial is spent.

## Look 47 (26 Oct 2026): the idea feed on history, owner-approved

- **What:** `python -m quantdesk ideas-backtest`. The idea feed exactly as it runs live (`IDEAS_RELAXED`, the live exits, fill at delay 1, one idea per index at a time), over 2019 to the last derived session. Nothing tuned.
- **Why:** the owner asked whether the ideas would have made money, before relying on the forward scorecards (D2 found the pre-registered rules untestable).
- **Consequence:**
  - N_prior becomes 47 for any later deflated Sharpe (`gate.n_prior` stays 46 until a new pre-registration is written, which must use 47 or more).
  - No setting of the feed may be tuned on this result. A change needs its own pre-registration and the forward record.
- **Result (26 Oct, after the z-reference fix):** 1,330 filled ideas from 2019 to 2026.
  - Win rate 31%; mean −0.06 R (t −2.04); about −₹37 per lot on average after charges.
  - 2026 alone: −0.07 R. Only 2021 and 2024 were positive, and neither significantly.
  - Targets hit 18% of the time (+1.87 R); stops 35% (−0.85 R).
  - Option prices are modelled.
  - **Verdict:** the idea feed as built does not pay. No setting is tuned on this.
