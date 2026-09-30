---
type: task
status: cancelled
area: gameplay
priority: high
---

# task-634: Vital decay of ~0.0034/turn makes hunger a permanent alarm

**Filed:** 2026-09-30
**Related:** 

## Goal

0 to 100 takes ~26,500 turns (about 2,700 in-game days), yet the engine shouts urgency at 90. Hunger can only be relieved by eating, so every character is permanently 'very hungry' from tick one. The vital modal compounds it by labelling the quantity 'decay' and 'TIME TO EMPTY' when hunger fills.

## Acceptance

- TODO

## Cancellation

Cancelled 2026-09-30. The rate is **deliberate and documented**, and every
documented figure matches the value. `vital_rates.py` lines 29-32:

    From a FULL meter: Hunger reaches the starvation edge at ~3 weeks,
    Thirst the dehydration edge at ~3 days, Energy empties over a ~16h
    waking day. Social/Hygiene/Entertainment run on a ~1-2 day cycle;
    Sanity is deliberately slow (~14 days) and mostly condition-driven.

Checked against 100/rate in in-game minutes:

    Hunger  100/0.0034 = 29,412 min = 20.4 days   (documented ~3 weeks)
    Thirst  100/0.0250 =  4,000 min =  2.8 days   (documented ~3 days)
    Energy  100/0.1040 =    961 min = 16.0 hours  (documented ~16h)
    Sanity  100/0.0050 = 20,000 min = 13.9 days   (documented ~14 days)

All four match. The original finding read a long timescale as an accident
without reading the source of truth, and `vital_rates.BASELINE_DECAY` is
deliberately the single source (a migration script, `migrate_decay_rates.py`,
and a guard test, `test_decay_rate_bake.py`, both exist to keep scenarios
baked to it).

The genuine residue is a copy observation, not a defect: the tier messages in
`tick_manager.get_need_message` are rate-agnostic, so a 3-week hunger drive and
a 16-hour energy draw are announced in identical urgency language. That belongs
with the audit's notes, not the backlog.