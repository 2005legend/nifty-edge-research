# Early pricing pre-check (not R17)

- data_hash `7f63e17c99325e63`; option candles 2026-09-29 to 2026-10-21
- 132 contracts, 15 sessions, 28958 measured moves

| measure | median error |
|---|---|
| all | 0.220 |
| horizon 15 | 0.263 |
| horizon 30 | 0.227 |
| horizon 60 | 0.200 |
| horizon exit | 0.195 |
| NIFTY | 0.216 |
| SENSEX | 0.230 |

R17's pass mark is 0.15. This early read is **OUTSIDE** it.

Not a substitute for R17. There are no expiry days (listed contracts have not expired), and the prices are last trades, not quotes. The trials still wait for the recorded check.
