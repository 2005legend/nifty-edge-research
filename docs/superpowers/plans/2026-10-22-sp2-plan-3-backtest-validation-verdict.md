# SP2 Plan 3: Signal Dataset, Backtester, Registry, Statistics and Verdict — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the pre-registered trials behind a registry guard and turn them into a verdict, alert-on or alert-off.

**Architecture:** The work runs in two stages.
- **Stage A (`backtest/dataset.py`):** walk every regular session once and store each H1 signal with:
  - its gate outcome
  - its family scores
  - its index-outcome label
  - its strike candidates

  No P&L.
- **Stage B (`backtest/engine.py`):** for one trial and one CV split:
  - give each test-day signal its probability from the split's model
  - apply the EV gate and the caps
  - fill with a delay
  - simulate the exit

  P&L exists only inside Stage B, and Stage B refuses to run without a registry ticket (R32).

`validation/` holds:
- CPCV (`cv.py`)
- the statistics (`stats.py`)
- the trial runner (`trial.py`)
- the registry (`registry.py`)
- the verdict (`verdict.py`)

**Tech Stack:** Python 3.11, pandas, numpy, scipy, pytest. It reuses plans 1 and 2.

**Spec:** `docs/superpowers/specs/2026-10-21-sp2-detailed-design.md` §12–§15; spec §6.2–§6.4; `research/hypotheses.yaml`.

## Global Constraints

- As in plans 1 and 2: `param()` only, offline tests, IST timestamps, branch `sp2/plan-3`.
- **No P&L outside a ticket.**
  - `engine.run_trial_split` raises `NoTicketError` without a valid `TrialTicket`.
  - Placebo mode (random entries) is the only unticketed run, and it is for controls.
- **Labels are never summarised before a ticket.** Stage A stores them; nothing prints their means.
- Registry refusals:
  - the cap of 13 trials
  - an unfrozen or changed `hypotheses.yaml`
  - a dirty git tree
  - unmet prerequisites (pilots, pricing check)
  - a repeated trial id

## Review Focus

1. **Both indices signalling at the same check time**: caps allow one trade a day. The higher EV wins, ties go to NIFTY. Pinned in Task 3.
2. **A delay that runs past the alert lapse (5 minutes) or the hard exit**: the signal lapses with R = 0 and still counts as a signal. Pinned in Task 2.
3. **A CPCV training set left empty by the embargo** (early groups): the split is skipped and reported, never crashes. Pinned in Task 5.
4. **PBO with a single trial run**: reported as "n/a" and passes, as the spec intends. Pinned in Task 6.
5. **Changing `hypotheses.yaml` after the `prereg-v1` tag**: the registry refuses every ticket. Pinned in Task 1.

---

### Task 1: Registry and trial tickets
**Files:** create `quantdesk/validation/registry.py`; test `tests/test_registry.py`.

**Produces:**
- `TrialTicket(trial_id, slot, issued_at, commit, hypotheses_hash, data_hash, cumulative_trials)`
- `Registry(research_dir, repo_dir)`
- `issue_ticket(trial_id, data_hash, prerequisites: dict[str, bool], accepted: dict) -> TrialTicket`
- `record(ticket, metrics: dict, trades, daily_r, models: dict) -> Path`
- `trials_run() -> list[str]`
- `hypotheses_hash() -> str`

**Tests:**
- refuses at 13 trials
- refuses an id not in the YAML
- refuses a repeat
- refuses `frozen: false`
- refuses a hash change after the tag (the tag hash is read from `research/prereg.json`)
- refuses a dirty tree (git is injected)
- refuses unmet prerequisites
- `record` appends exactly one CSV row and writes `research/trials/<id>/`

### Task 2: Fills
**Files:** create `quantdesk/backtest/fills.py`; test `tests/test_fills.py`.

**Produces:** `fill(signal, choice, frame, quotes, delay_min, h) -> FillResult(status: "filled"|"lapsed"|"rejected_flip", at, premium)`
- **Entry:** ask + 1 tick at bar T + k − 1.
- **Lapse:** if the delay is 5 minutes or more (beyond `time.alert_lapse_min`), or past the hard exit.
- **Chase cap:** |S_fill − ref| > min(0.15·σ(τ)·O, 0.3·b) gives `lapsed`.
- **Sign flip:** the close at T + 2 back across the band or VWAP gives `rejected_flip`, applied for delays ≥ 3.

### Task 3: Stage A signal dataset
**Files:** create `quantdesk/backtest/dataset.py`; test `tests/test_dataset.py`.

**Produces:** `build_dataset(loader, h, start, end, today) -> SignalDataset`
- **signals table:** day, index, at, side, ref_close, stop_level, b, target_level, failed, technical, options, macro, har_pct, dte, label, delta_event, delta_shock, delta_stress, lot, vix_tercile, weekday, expiry_day
- **candidates table:** signal_id plus `Candidate` fields
- saved under `data/derived/signals/`

Labels come from `meta.label`. Candidates exist only for signals that passed every gate.

### Task 4: Stage B engine and caps
**Files:** create `quantdesk/backtest/engine.py`; test `tests/test_engine.py`.

**Produces:** `run_trial_split(dataset, test_days, cfg, model, loader, h, today, delay, ticket) -> pd.DataFrame` (trades)
- Signals are walked in time order across indices.
- Caps: 1 a day, 3 a week, the monthly pro-rata share of 100.
- Model gives p; `pick` applies p and Δ; then `fill` and `simulate_exit`.
- Skipped and lapsed signals are kept with R = 0.

Also `placebo_run(dataset, days, loader, h, today, seed)` with random side and check time, no ticket needed.

### Task 5: CPCV and walk-forward
**Files:** create `quantdesk/validation/cv.py`; test `tests/test_cv.py`.

**Produces:**
- `half_year_groups(days) -> list[list[date]]`
- `cpcv_splits(groups, k=2, embargo=20) -> list[Split(train, test, test_groups)]` (45 for 10 groups)
- `paths(splits, n_groups) -> list[list[(group, split_index)]]` (9)
- `walk_forward(days, train_end, test_start, test_end, embargo)`

**Tests:** split count; embargo on both sides; path coverage (each group once per path).

### Task 6: Statistics
**Files:** modify `quantdesk/validation/stats.py`; test `tests/test_stats.py`.

**Produces:**
- `pbo(matrix: np.ndarray, S=10) -> float | None`: about 0.5 on noise, about 0 for one dominant trial, None if fewer than 2 trials
- `permutation_p(actual, mirror, buckets, rounds, seed)`
- `years_positive(daily_r_by_year)`
- `post_publication_ratio(...)`
- `addon_gate(new_trades, old_trades, days, years)`

### Task 7: Training inside folds
**Files:** create `quantdesk/backtest/training.py`; test `tests/test_training.py`.

**Produces:** `train(dataset, train_days, cfg, h) -> model`
- **Consensus (B0/X1):** `fit_consensus` on mean scores.
- **Meta:** `fit_meta` on `columns()`.

It uses training-day signals only, skipped setups included, and saves the model JSON.

### Task 8: Trial runner and verdict
**Files:** create `quantdesk/validation/trial.py` and `quantdesk/validation/verdict.py`; modify `quantdesk/cli.py` (`dataset`, `trial <ID>`, `verdict`, `preflight`, `pricecheck`); test `tests/test_trial.py`.

**Produces:**
- `run_trial(trial_id, registry, dataset, loader, h, today) -> dict`. For each split: train, then run the test days; assemble the 9 paths; take the median path; run the walk-forward; run delay 3; compute every gate; record.
- `evaluate(registry, h) -> Verdict(status: "alert-on"|"alert-off", config, reasons)`

### Task 9: Pre-flight
**Files:** create `quantdesk/validation/preflight.py`; test `tests/test_preflight.py`.

**Produces:** `preflight(...) -> dict[str, bool]`
- negative control: placebo |t| < 2
- positive control: a planted drift is recovered with t > 3
- the truncation test file passes
- the delay test runs
- pricing check passed
- frozen files present
- tree clean
- `prereg-v1` tag exists

## Plan 3 is done when
The suite passes, `preflight` reports every item green except the time-gated pricing check, and `trial` refuses to run until it is green.
