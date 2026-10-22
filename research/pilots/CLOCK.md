# CLOCK: business-time weights fitted on 2019-01-01..2022-12-31

- data_hash `fc2edfa556eeb474`, fitted 2026-10-22T08:10:56+05:30, 985 regular sessions
- theta_night 0.5340 (overnight share 0.348; research measured 0.38-0.43)
- theta_weekend_day 0.1858 ± 0.0509
- theta_holiday 0.2808 ± 0.1840 (805 implied-variance pairs)

| 15 minutes from | share of a session's variance |
|---|---|
| 09:15 | 0.1812 |
| 09:30 | 0.0626 |
| 09:45 | 0.0459 |
| 10:00 | 0.0389 |
| 10:15 | 0.0326 |
| 10:30 | 0.0310 |
| 10:45 | 0.0281 |
| 11:00 | 0.0272 |
| 11:15 | 0.0261 |
| 11:30 | 0.0253 |
| 11:45 | 0.0239 |
| 12:00 | 0.0235 |
| 12:15 | 0.0239 |
| 12:30 | 0.0240 |
| 12:45 | 0.0256 |
| 13:00 | 0.0295 |
| 13:15 | 0.0297 |
| 13:30 | 0.0353 |
| 13:45 | 0.0354 |
| 14:00 | 0.0407 |
| 14:15 | 0.0418 |
| 14:30 | 0.0459 |
| 14:45 | 0.0399 |
| 15:00 | 0.0507 |
| 15:15 | 0.0311 |

## Surface

| dte | R(dte) | ATM pairs |
|---|---|---|
| 0 | 0.8315 | 0 |
| 1 | 0.8315 | 203 |
| 2 | 0.8419 | 202 |
| 3 | 0.8529 | 203 |
| 4 | 0.8371 | 201 |
| 5 | 0.8565 | 203 |
| 6 | 0.8747 | 202 |

- skew b1 -0.0590, b2 0.0482 (38939 strikes, |z| <= 3)
- spot-vol beta: gamma_dn -2.481 (10992 windows), gamma_up -1.665 (11493 windows)

## Shock CUSUM

- h = 14.9244 (seed 20261021, 992 daily returns, target 1 alarm per 250 sessions)
