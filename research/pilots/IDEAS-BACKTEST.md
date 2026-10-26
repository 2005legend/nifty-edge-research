# Idea feed on history (one untuned look; not a registry trial)

- data_hash `1aeb87aad8ecd6aa`, written 2026-10-26T12:39:38+05:30
- Settings: `IDEAS_RELAXED`, exits of the live configuration, fill at delay 1, one idea per index at a time
- Option prices are modelled (early pricing check: 0.22 median error vs 0.15 target)

| period | ideas | filled | win rate | mean R | median R | t | mean return on premium % | mean Rs per lot |
|---|---|---|---|---|---|---|---|---|
| all | 1609 | 1330 | 0.31 | -0.06 | -0.31 | -2.04 | -0.1 | -37 |
| 2019-2025 | 1343 | 1106 | 0.32 | -0.06 | -0.31 | -1.83 | -0.2 | -24 |
| 2026 | 266 | 224 | 0.27 | -0.07 | -0.42 | -0.91 | 0.9 | -103 |
| 2019 | 111 | 85 | 0.34 | -0.12 | -0.41 | -1.06 | -3.5 | -63 |
| 2020 | 120 | 94 | 0.28 | -0.06 | -0.29 | -0.53 | -0.6 | 36 |
| 2021 | 147 | 114 | 0.33 | 0.06 | -0.28 | 0.54 | 4.7 | 104 |
| 2022 | 139 | 115 | 0.36 | -0.03 | -0.30 | -0.34 | -0.8 | 44 |
| 2023 | 170 | 145 | 0.25 | -0.22 | -0.38 | -2.87 | -5.7 | -128 |
| 2024 | 236 | 205 | 0.32 | 0.06 | -0.28 | 0.73 | 6.8 | 46 |
| 2025 | 420 | 348 | 0.32 | -0.10 | -0.29 | -1.77 | -2.6 | -93 |
| NIFTY | 1145 | 942 | 0.31 | -0.06 | -0.31 | -1.78 | -0.3 | -19 |
| SENSEX | 464 | 388 | 0.31 | -0.06 | -0.32 | -1.01 | 0.5 | -83 |

## Exits

| reason | count | mean R |
|---|---|---|
| deadline | 19 | 0.22 |
| hard_exit | 69 | 0.35 |
| stall | 383 | -0.16 |
| stop | 467 | -0.85 |
| target | 244 | 1.87 |
| vwap_cross | 148 | -0.73 |

R = result / the strike's planned loss at the index stop (after charges). A mean R above 0 with t above 2 in both periods would be worth confirming on the forward scorecards; anything else says the ideas do not pay as built.
