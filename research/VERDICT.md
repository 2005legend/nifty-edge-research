# SP2 verdict: **alert-off**

- Configuration: none (shadow runs B0, the pre-registered baseline)
- Accepted trials: none. No trial was run, and none is needed to reach this verdict.
- Decided: 22 Oct 2026, by the owner at the D2 checkpoint (spec §6.3)

## Reasons

- **Too few setups to test.** The H1 noise-band trigger with the pre-registered gates and strike picker gives 0.67 eligible setups a year at ₹10k / ₹400 (P1: 4 in 2019-2025). D2 option 1 (₹15k / ₹600) gives 1.7 a year (16). The validation needs about 60 a year. P10 puts the chance that every gate could ever pass at 0% and 2%.
- **The cause is structural.** Signals that clear every gate have a median structural stop of 6 index points, so the planning target is about 14 points. On a weekly option, a 14-point move doesn't pay for the spread, about ₹57 of charges and an hour of theta. The best strike per signal plans a median ₹0.74 gain per ₹1 at risk, so breakeven needs about a 57% hit rate, while the index target is reached about 38% of the time.
- **No profit was looked at.** Every number above comes from zero-trial pilots and planning maths. The 13 trial slots are unspent.

## What runs instead

- Recording, the derived tables, the journal and the dashboard, as before.
- The live engine in shadow mode. Its calls reach Telegram marked "SHADOW - do not trade", and its paper trades build a forward record.
- The analyst desk (SP4) once its pilot is done.
- Any new trading idea (for example, wider stops or longer holds) is a separate, newly pre-registered project. It does not reuse these slots.
