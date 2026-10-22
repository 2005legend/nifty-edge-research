"""The objects the pipeline passes between its steps (design §10). Frozen where nothing should change them."""

from dataclasses import dataclass, field
from datetime import date, datetime, time

import numpy as np


@dataclass(frozen=True)
class ZRef:
    """A feature's mean, sd and count at one check time over earlier sessions: the causal z reference (R10)."""
    mean: float
    sd: float
    n: int


@dataclass(frozen=True, eq=False)   # eq=False: band_sigma is an array
class DayContext:
    """Everything known about one index's day by 09:16 (design §4, §10 step 1)."""
    index: str
    day: date
    session_kind: str
    open: float
    prev_close: float
    prev_day: tuple          # (high, low, close)
    prev_week: tuple         # (high, low, close) of the previous Monday-Friday week
    is_expiry_day: bool
    expiry_1: date
    expiry_2: date | None
    lot_1: int
    lot_2: int | None
    dte_1: int
    sigma_day: float         # HAR forecast, fraction of the index for one session
    sigma_gap: float
    har_pct: float | None
    vix_prev_close: float
    band_sigma: np.ndarray   # 375 slots, NaN where fewer than 14 same-type sessions exist
    events: tuple
    delta_parts: dict        # "shock", "stress", "stress_full", "event", "slow_trend", "gamma"
    options_raw: dict | None
    macro_raw: float
    vol_rich_threshold: float | None
    z_refs: dict             # (feature, "HH:MM") -> ZRef
    hard_exit: time
    spike_ref: np.ndarray | None = None   # per-slot median |1-min ATM premium change| over the previous 14 sessions


@dataclass(frozen=True)
class Signal:
    index: str
    at: datetime
    side: str                # "long" or "short"
    ref_close: float
    upper: float
    lower: float
    vwap: float
    stop_level: float
    b: float
    target_level: float


@dataclass(frozen=True)
class StrikeChoice:
    index: str
    expiry: date
    strike: float
    kind: str                # "CE" or "PE"
    lot: int
    ask: float
    delta: float
    gain: float
    loss: float
    p_be: float
    ev: float
    kelly: float


@dataclass(frozen=True)
class Alert:
    choice: StrikeChoice
    side: str
    at: datetime
    entry_limit: float
    index_stop: float
    index_target: float
    backstop_trigger: float
    backstop_limit: float
    p: float
    delta: float
    delta_parts: dict
    reasons_for: tuple
    reasons_against: tuple


@dataclass
class Decision:
    index: str
    at: datetime
    signal: Signal | None
    failed: str | None
    p: float | None = None
    delta: float = 0.0
    scores: dict = field(default_factory=dict)
    choice: StrikeChoice | None = None
    alert: Alert | None = None


@dataclass(frozen=True)
class TrialConfig:
    trial_id: str
    exit_policy: str                 # "X0", "X1" or "X2"
    probability: str                 # "consensus", "meta" or "meta_ctx"
    hurdles: frozenset = frozenset() # subset of {"shock", "stress", "slow_trend", "gamma"}
    trigger: str = "h1"              # "h1", or "rod" for the 14:45 research trial
