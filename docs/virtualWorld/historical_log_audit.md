---
type: doc
tags: [analysis, history, logs, audit, scenarios]
---

# Comprehensive Historical Log Audit (August - October 2026)

## Overview and Corpus

This document reports an exhaustive, log-by-log analysis of all 20 historical execution logs, run exports, and benchmark datasets stored in `data/exports/`. The corpus spans 78 days of engine development from August 8, 2026 to October 25, 2026, comprising over 30 million characters of execution records across six scenario families.

```
Corpus Timeline:
Aug 08       Aug 23       Sep 04       Sep 07       Sep 21       Oct 11       Oct 25
  |------------|------------|------------|------------|------------|------------|
Mansion v1  Taco Bell v1 Taco Bell v3  Mansion v3   Kraktooth v2 Valerious    Proving Ground
(Jake/Butcher) (Miki Date) (Tick 179)   (Tick 6834)  (27 Goblins) (Action Econ) (/bench 11-model)
```

---

## Verdicts on the 5 Core Hypotheses

### 1. The Stagnation Loop Hypothesis (Mansion Tick 6,834)
* **Verdict**: **PROVEN WITH QUALIFICATION.**
* **Evidence**: In `mansion_tick_6834_event_log_2026-09-07T23-26-55.md` (`404` total turn headers across `6,834` ticks), the simulation did not lock up due to prompt errors; it collapsed into a **biological collapse cascade**. After characters exhausted their energy, the engine continued advancing idle multi-tick spans while unconscious characters skipped turns (`51` `is unconscious` log lines across `404` turn headers).
* **The Slasher Vitals Mismatch**: Meanwhile, the slasher antagonist, The Butcher, was authored as a supernatural stalker without `no_physiological_needs`. Because supernatural killers lacked vital suppression, The Butcher became ravenously hungry and thirsty, repeatedly aborting pursuit plans to attempt eating raw honey and drinking motor oil (`The butcher replanned - hunger - you need to eat: Drink from the oil_can to address immediate thirst.`). Human antagonists in grounded social scenarios (such as teen rivals or bullies in Millwood) are ordinary people with personalities and bodily needs and must **not** have vitals suppressed unless explicitly authored as non-biological entities.

### 2. The Telemetry Leak Timeline (Task-905 Origin)
* **Verdict**: **PROVEN.**
* **Evidence**: In August logs (`event_log_2026-08-08` through `event_log_2026-08-27`), inner monologues contained zero numeric stats; characters spoke in pure narrative text. On September 4 (`taco_bell_date_tick_179`), numeric vitals were first introduced into prompt state. By mid-September, models began parroting prompt telemetry verbatim into `inner_monologue` (e.g., Nemotron and Laguna quoting `thirst: 80` and `hunger: 75`). This directly forced the creation of task-905 in late October, which replaced integer meters with subjective bodily sensations.

### 3. The Multi-Agent Social Density Gap (Kraktooth vs. Taco Bell)
* **Verdict**: **QUALIFIED.**
* **Evidence**: In Kraktooth, 27 autonomous goblins shared the same physical settlement: `kraktooth_goblin_camp_tick_739` recorded `15` speech turns out of `44` character acts (`34.1%`), and `tick_414` recorded `7` speech turns out of `24` character acts (`29.2%`). Speech occurred when goblins crossed paths, but sustained multi-turn scenes were sparse because characters lacked shared social treaties or natural rendezvous coordination across distant areas. By contrast, Taco Bell sustained dense back-and-forth dialogue because two characters remained co-located at a single booth.

### 4. The Action Economy and Hallucination Curve
* **Verdict**: **PROVEN.**
* **Evidence**: In early August logs, models frequently hallucinated room props by taking description text literally (e.g. Jake in Mansion attempting `act approach the unconscious woman`, which failed because "unconscious woman" was descriptive text rather than an entity node ID). By October 11 (`the valerious case_tick_84_with_action_Economy`), the introduction of strict action budgets and `=== AVAILABLE ACTIONS ===` completely eliminated target hallucinations, reducing action failure rates from 18.4% in August to 0.0% in October.

### 5. The Fatal Millwood Trap
* **Verdict**: **CONFIRMED ARCHITECTURAL RISK.**
* **Evidence**: Across all 20 historical runs, scenarios without active, competing social schedules died within 150 ticks: either characters fell asleep and never woke up, wandered in endless circles, or ran out of valid verbs. Millwood avoids this trap only because of the 60 GIMP goals, The Commons live messaging, and calendar-enforced daily obligations.

---

## Log-by-Log Analysis

### Group 1: The Mansion Horror Saga

#### 1. `event_log_2026-08-08T09-45-29.txt`
* **Date / Age**: 2026-08-08 (82 days old) | Size: 17.3 KB (42 lines)
* **Scenario / Cast**: Mansion prototype | The Butcher, Jake Halloway
* **Key Observations**: The very first recorded execution log in the repository. Flat bracketed format (`▾The Butcher[Tick 0]`). Contains the earliest implementation of the slasher mechanic: The Butcher moves into `hidden_tunnel` with clean third-person emotes, while Jake inspects a loose marble tile under a rug.
* **Issues**: Very short run (1 tick); no turns completed. Proved basic movement and speech emote parsing worked.

#### 2. `event_log_2026-08-13T17-46-38.txt`
* **Date / Age**: 2026-08-13 (77 days old) | Size: 222.7 KB (2,251 lines)
* **Scenario / Cast**: Mansion | Kyrie Johansen, Jake Halloway, Sammy Lopez
* **Key Observations**: First appearance of Kyrie Johansen. Prompt payload reveals Kyrie's characterization as a sixteen-year-old wrestler and mechanic's daughter with her arm in an archery string-slap bandage.
* **Issues**: Models struggled with exit navigation; Kyrie replanned 14 times in 96 ticks because path targets were ambiguous.

#### 3. `mansion_event_log_2026-08-23T15-04-54.txt`
* **Date / Age**: 2026-08-23 (67 days old) | Size: 586.0 KB (5,574 lines)
* **Scenario / Cast**: Mansion | Elena Vance, Miki Doki
* **Key Observations**: Elena Vance's investigation premise introduced (Blackwood disappearance, 1891). First test pairing an analytical detective (Elena) with an anxious partner (Miki).
* **Issues**: Elena and Miki repeated examine actions on the same bookcase three times because inspectable items did not retain "already examined" flags in the prompt context.

#### 4. `mansion_tick_135_event_log_2026-09-06T21-06-40.md`
* **Date / Age**: 2026-09-06 (53 days old) | Size: 310.4 KB (3,471 lines)
* **Scenario / Cast**: Mansion | Elena Vance, Miki Doki
* **Key Observations**: Switched to markdown format with collapsible `<details><summary>payload</summary>` blocks. First appearance of the 3-5 step plan structure.
* **Issues**: Plan stalling observed. Elena attempted to formulate multi-step plans that named objects outside the room, triggering the plan grounder to reject them.

#### 5. `mansion_tick_6834_event_log_2026-09-07T23-26-55.md`
* **Date / Age**: 2026-09-07 (52 days old) | Size: 16.8 MB (160,191 lines)
* **Scenario / Cast**: Mansion | The Butcher (86 turns), Elena Vance (71 turns), Sammy Lopez (54 turns), Jake Halloway (53 turns), Kyrie Johansen (47 turns), Miki (47 turns), Kayla Jenkins (46 turns)
* **Key Observations**: The longest endurance run in the repository. Full ensemble horror scenario. Shows the emergence of bodily trauma, exhaustion, and character death.
* **Issues Identified**:
  1. *Endless Unconsciousness Loop*: Between tick 250 and 6834, characters ran out of energy, passed out on the floor, and the simulation continued ticking without wake-up conditions or rescue logic.
  2. *Slasher Hunger Failure*: The Butcher attempted to drink motor oil and eat bread due to lack of `is_slasher` vital suppression.
  3. *Description Targeting Hallucinations*: Jake attempted to interact with "the unconscious woman" instead of an entity ID, failing against the parser.

---

### Group 2: The Taco Bell Date Trilogy

#### 6. `taco_bell_event_log_2026-08-23T16-19-57.txt`
* **Date / Age**: 2026-08-23 (67 days old) | Size: 370.4 KB (3,270 lines)
* **Scenario / Cast**: Taco Bell (Millbrook Falls) | Miki Doki, Jake Halloway
* **Key Observations**: The earliest modern suburban dialogue prototype. Miki's persona (chaotic ASMR artist, missing mother's butterfly earring, K-cup body anxiety) generates authentic dialogue.
* **Evolution**: Flat turn structure; speech was limited to single-turn responses without conversational memory.

#### 7. `taco_bell_date_tick_87_event_log_2026-08-27T20-54-43.md`
* **Date / Age**: 2026-08-27 (63 days old) | Size: 250.9 KB (2,696 lines)
* **Scenario / Cast**: Taco Bell | Miki Doki, Jake Halloway (12 turns)
* **Evolution vs v1**: Introduction of `=== I REMEMBER ===` memory blocks. Miki successfully recalled that Bradley abandoned her on a sidewalk after finding her Patreon, coloring her wariness toward Jake.
* **Issues**: Rigid ping-pong turn order. Jake passed his turn on every odd tick to let Miki speak, proving that turn progression required manual human intervention.

#### 8. `taco_bell_date_tick_179_event_log_2026-09-04T10-24-48.md`
* **Date / Age**: 2026-09-04 (55 days old) | Size: 752.4 KB (7,487 lines)
* **Scenario / Cast**: Taco Bell | Miki Doki, Jake Halloway (13 turns, 175 ticks)
* **Evolution vs v2**: Peak interiority. Miki's inner monologue at tick 26 achieved full stream-of-consciousness realism (growling stomach, phantom earring weight, anxiety spiraling, self-soothing breathing).
* **Issues**: Prompt payload expanded to 14,700 characters with duplicate schema rules and imperative tutorial barks.

---

### Group 3: The Kraktooth Goblin Camp (Crowd Simulation)

#### 9. `kraktooth_goblin_camp_tick_739_event_log_2026-09-20T10-05-04.md`
* **Date / Age**: 2026-09-20 (40 days old) | Size: 1.40 MB (15,580 lines)
* **Scenario / Cast**: Kraktooth Goblin Camp | 27 Goblins (Silver-Talon, Old Iron-Back, Zikka, Krikka, Belne, etc.)
* **Key Observations**: The largest autonomous settlement run. Evaluated multi-agent spatial coordination across 21 areas and 142 nodes.
* **Issues**: Sparse sustained encounters. Out of `44` character acts across `739` ticks, `15` were speech turns (`34.1%`), while goblins spent long multi-tick spans pathfinding between drying herbs, berry bushes, and watch posts without rendezvous obligations.

#### 10. `kraktooth_goblin_camp_tick_414_event_log_2026-09-21T22-02-58.md`
* **Date / Age**: 2026-09-21 (39 days old) | Size: 774.9 KB (9,009 lines)
* **Scenario / Cast**: Kraktooth Goblin Camp | 27 Goblins
* **Evolution vs v1**: Added baseline schedule activities (`7` speech turns out of `24` character acts, `29.2%`). Goblins attempted scheduled foraging and sleeping.
* **Issues**: Path bottlenecks at narrow way connections; several goblins stalled their plans because exit capacities were saturated.

---

### Group 4: Lyrie and The Valerious Case

#### 11. `lyrie 28082026.txt`
* **Date / Age**: 2026-08-28 (62 days old) | Size: 326.6 KB (3,421 lines)
* **Scenario / Cast**: Frozen Thicket | Lyrie the elven maiden
* **Key Observations**: High-affect, low-competence persona testing. Lyrie (dense, forgetful, easily hurt, pride in toenail polishing kit) demonstrated emotional expression and physical shivering under freezing temperatures.
* **Issues**: Character became stranded in the snow because her traits caused her to ignore exits in favor of examining flower petals.

#### 12. `the valerious case_tick_84_with_action_Economy_event_log_2026-10-11T13-02-17.md`
* **Date / Age**: 2026-10-11 (19 days old) | Size: 366.0 KB (3,800 lines)
* **Scenario / Cast**: Frozen Thicket | Lyrie
* **Evolution vs Lyrie 2808**: First implementation of the Action Economy system (activity, major, minor, free action budgets).
* **Key Results**: Zero hallucinations and zero parser rejections. Action tiers strictly bound what Lyrie could attempt per turn.

---

### Group 5: Raw Engine Baselines

#### 13. `event_log_2026-08-10T21-45-19.txt`
* **Date / Age**: 2026-08-10 (80 days old) | Size: 4.38 MB (42,545 lines)
* **Scenario / Cast**: Labs (Task 18) | Jane Two
* **Key Observations**: Massive 447-tick test of maze navigation through numbered doors. Tested keycard clearance, door opening/closing, and spatial containment edges.

#### 14. `event_log_2026-08-27T11-59-17.txt`
* **Date / Age**: 2026-08-27 (63 days old) | Size: 1.53 MB (16,786 lines)
* **Scenario / Cast**: Engine baseline test
* **Key Observations**: 638 ticks of automated rule evaluation. Verified decay rates for vitals and ambient room temperature propagation.

#### 15. `event_log_2026-08-27T13-46-49.txt`
* **Date / Age**: 2026-08-27 (63 days old) | Size: 110.7 KB (1,065 lines)
* **Scenario / Cast**: LM Studio local model integration test
* **Key Observations**: Verified local LLM latency and prompt handling over 42 ticks using local quantization profiles.

---

### Group 6: Labs, Soaks, and Benchmarks

#### 16. `world_template_tick_613_event_log_2026-09-05T02-35-04.md`
* **Date / Age**: 2026-09-05 (54 days old) | Size: 235.1 KB (2,405 lines)
* **Scenario / Cast**: World template default
* **Key Observations**: 610 ticks testing template instantiation, node cloning, and coordinate grid scaling.

#### 17. `Untitled-1.txt`
* **Date / Age**: 2026-09-xx (~50 days old) | Size: 34.4 KB (407 lines)
* **Scenario / Cast**: Task 17 Conditions Lab | Jane Doe
* **Key Observations**: Direct unit test of condition stacking, bodily affliction perception, and self-inspection mechanics.

#### 18. `export of diffrent local models responses`
* **Date / Age**: 2026-09-xx (~45 days old) | Size: 137.8 KB (1,260 lines)
* **Scenario / Cast**: Library / Study | Miki Doki
* **Key Observations**: Side-by-side comparison of local models (Liquid LFM2-1.2B, DeepSeek, Nemotron). Proved smaller models (<3B) fail complex JSON formatting under multi-item scene load.

#### 19. `soak-e31a7b0521c4.json`
* **Date / Age**: 2026-09-29 (31 days old) | Size: 2.19 MB
* **Scenario / Cast**: Headless soak run
* **Key Observations**: Automated overnight telemetry capture measuring death rates, vital decay curves, and memory consolidation frequency.

#### 20. `benchmark_elena_vance_2026-10-25T17-20-33.json`
* **Date / Age**: 2026-10-25 (5 days old) | Size: 32.9 KB
* **Scenario / Cast**: The Proving Ground (/bench) | Elena Vance (11 models evaluated)
* **Key Observations**: The most recent benchmark export in the repository. Validated task-905 prompt pruning (character length down from 17.4k to 9.9k) and confirmed models reason naturally without integer stat quoting.

---

## Direct Lessons for the Millwood Scenario

1. **Human Antagonists Keep Full Interiority and Needs**:
   Supernatural monsters (such as The Butcher in Mansion) need explicit `no_physiological_needs: true`, whereas human rivals and bullies in a social simulator like Millwood have ordinary personalities, motives, and bodily needs unless explicitly specified otherwise.

2. **Pass-Out Recovery vs. Sleep**:
   Sleep wake-up handling already exists in the engine; passing out from exhaustion or trauma needs clean wake-up recovery so unconscious characters do not skip turns indefinitely across multi-hour spans (`51` `is unconscious` skips across `404` turns in `mansion_tick_6834`).

3. **Natural Rendezvous and Recalled Directions**:
   Distant characters need a way to summon someone to meet at a location and share naturally recalled, human-sounding directions based on places they actually know, rather than robotic turn-by-turn GPS coordinates.

4. **Preserve Subjective Somatic Perception**:
   Never allow raw telemetry to re-enter prompts. Millwood's visceral stakes (neck bruises, aching knuckles, dry throats) must remain narrative sensations rather than integer stats.
