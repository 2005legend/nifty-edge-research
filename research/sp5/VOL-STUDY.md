# SP5 result (look 48): buy the ATM straddle only when implied < forecast

- Rule and gates: `research/sp5/PREREG.md`. Days with a trade signal: 37%
- Market vs reality (2019-2025): implied variance averaged 1.06x the variance that followed

| 11 Feb 2019 - 31 Dec 2025 | trades | mean return on premium | t | win rate |
|---|---|---|---|---|
| filtered (rho < 1) | 628 | -3.20% | -3.43 | 31% |
| baseline (every day) | 1694 | -3.39% | -5.57 | 30% |

Filtered minus baseline: Welch t = 0.18

## By year (filtered)

| year | trades | mean | t |
|---|---|---|---|
| 2019 | 100 | -4.96% | -2.29 |
| 2020 | 80 | -3.43% | -1.52 |
| 2021 | 104 | -2.42% | -0.94 |
| 2022 | 45 | -1.99% | -0.63 |
| 2023 | 110 | -3.43% | -1.82 |
| 2024 | 85 | -4.97% | -2.19 |
| 2025 | 104 | -0.95% | -0.32 |

2026 (touched, not a gate): filtered 46 trades, mean +6.17%; baseline 198, mean -0.79%

## Gates

- mean_positive_t2: fail
- years_positive_4_of_6: fail
- beats_baseline: fail

**Verdict: FAILED - no buying edge by this rule**
