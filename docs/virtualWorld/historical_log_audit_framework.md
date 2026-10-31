---
type: doc
tags: [analysis, history, logs, audit]
---

# Historical Log Audit: Framework and Hypotheses

## Purpose

A systematic, evidence-based audit of the 20 historical execution logs and run exports stored in `data/exports/`, spanning from August 8, 2026 to October 25, 2026.

The goal is to trace the architectural and behavioral evolution of the simulation, identify historical failure modes (stagnation loops, prompt telemetry leakage, conversational deadlocks, action hallucinations), and extract direct lessons to ensure the Millwood scenario succeeds.

---

## The 5 Core Hypotheses to Prove or Disprove

### 1. The Stagnation Loop Hypothesis (The 6,834-Tick Question)
- **Question**: What actually happens when an autonomous agent is left in a closed simulation loop across thousands of ticks without human intervention?
- **Hypothesis**: Without long-horizon pursuits or stateful goal achievement gates, an LLM agent in an isolated environment collapses into an action-oscillation loop (e.g. examine desk -> look -> search -> examine door -> repeat) or ping-pongs between two connected areas once immediate physiological needs are met.
- **Verification Metric**: Unique areas visited, unique actions taken per 100 ticks, action n-gram repetition frequency, and stagnation onset tick in `mansion_tick_6834_event_log_2026-09-07T23-26-55.md`.

### 2. The Telemetry Leak Timeline (The Task-905 Origin)
- **Question**: When and why did the prompt builder begin injecting raw engine numbers, and how did LLM reasoning models react?
- **Hypothesis**: In early August, prompts were short and parser-like. In early September, as vitals and MOSIAC letters were wired in, prompts began dumping raw integer telemetry (e.g. `thirst: 80`, `Choices: activity 12`). Models immediately began reciting these numbers in their `inner_monologue` because LLMs treat prompt keys as literal reality. Clean subjective narrative sensations only emerged in late October with task-905.
- **Verification Metric**: Character length of prompts, presence of raw integer stats in prompt payloads, and word-for-word telemetry quoting in `inner_monologue` across chronological logs.

### 3. The Multi-Agent Social Void (Kraktooth vs. Taco Bell)
- **Question**: How did character density affect social dynamics and emergent dialogue?
- **Hypothesis**: High agent density (27 goblins in Kraktooth) produced near-zero meaningful social interaction, resulting in ambient wandering where speech was restricted to broadcast barks. Staged two-character rooms (Taco Bell) produced dialogue only because of manual turn passing, but suffered from rigid ping-pong pacing until desynchronized cadence shipped in late October.
- **Verification Metric**: Dialogue frequency (% of turns containing speech), addressed speech ratio, and conversational burstiness in Kraktooth vs. Taco Bell.

### 4. The Action Economy and Hallucination Curve
- **Question**: How frequently did models hallucinate non-existent items, exits, or verbs, and how did the engine resolve invalid actions?
- **Hypothesis**: Early logs suffered high rejection and error rates due to models hallucinating room contents or inventing unsupported verbs. As `=== AVAILABLE ACTIONS ===`, plan grounding, and action tiers were introduced, structural errors dropped, but agent plans became more conservative and repetitive.
- **Verification Metric**: Parser rejection rate, invalid target errors, plan length, and action diversity across August vs. October (`the valerious case_tick_84_with_action_Economy`).

### 5. The Fatal Millwood Trap
- **Question**: What recurring systemic failure across the historical scenarios poses the greatest threat to Millwood?
- **Hypothesis**: Previous scenarios died of either terminal isolation (a single character trapped alone in a house) or aimless crowd drift (unanchored NPCs wandering across open maps). Millwood will suffer the same fate unless the 60 GIMP goals, The Commons communication channels, and strict calendar schedules actively force characters into shared physical spaces with conflicting stakes.
- **Verification Metric**: Analysis of failure causes across all 20 logs correlated with Millwood's scenario structure.

---

## Log Inventory (Chronological Order)

| # | Filename | Date | Size | Scenario / Focus |
|---|---|---|---|---|
| 01 | `event_log_2026-08-08T09-45-29.txt` | 2026-08-08 | 17.3 KB | Early engine baseline / movement |
| 02 | `event_log_2026-08-10T21-45-19.txt` | 2026-08-10 | 4.38 MB | Massive early world run |
| 03 | `event_log_2026-08-13T17-46-38.txt` | 2026-08-13 | 222.7 KB | Mid-August engine mechanics |
| 04 | `mansion_event_log_2026-08-23T15-04-54.txt` | 2026-08-23 | 586.0 KB | Mansion v1: early Elena Vance exploration |
| 05 | `taco_bell_event_log_2026-08-23T16-19-57.txt` | 2026-08-23 | 370.4 KB | Taco Bell v1: early social date prototype |
| 06 | `event_log_2026-08-27T11-59-17.txt` | 2026-08-27 | 1.53 MB | Late August engine run |
| 07 | `event_log_2026-08-27T13-46-49.txt` | 2026-08-27 | 110.7 KB | Late August targeted mechanics |
| 08 | `taco_bell_date_tick_87_event_log_2026-08-27T20-54-43.md` | 2026-08-27 | 250.9 KB | Taco Bell v2: tick 87 date progression |
| 09 | `lyrie 28082026.txt` | 2026-08-28 | 326.6 KB | Lyrie the elf in Frozen Thicket |
| 10 | `taco_bell_date_tick_179_event_log_2026-09-04T10-24-48.md` | 2026-09-04 | 752.4 KB | Taco Bell v3: tick 179 Miki Doki and Jake |
| 11 | `world_template_tick_613_event_log_2026-09-05T02-35-04.md` | 2026-09-05 | 235.1 KB | World template baseline run |
| 12 | `mansion_tick_135_event_log_2026-09-06T21-06-40.md` | 2026-09-06 | 310.4 KB | Mansion v2: tick 135 progression |
| 13 | `mansion_tick_6834_event_log_2026-09-07T23-26-55.md` | 2026-09-07 | 16.8 MB | Mansion v3: 6,834-tick endurance run |
| 14 | `kraktooth_goblin_camp_tick_739_event_log_2026-09-20T10-05-04.md` | 2026-09-20 | 1.40 MB | Kraktooth v1: 739-tick 27-goblin run |
| 15 | `kraktooth_goblin_camp_tick_414_event_log_2026-09-21T22-02-58.md` | 2026-09-21 | 774.9 KB | Kraktooth v2: 414-tick goblin run |
| 16 | `soak-e31a7b0521c4.json` | 2026-09-29 | 2.19 MB | Overnight headless soak run |
| 17 | `export of diffrent local models responses` | 2026-09-xx | 137.8 KB | Multi-model local prompt benchmark |
| 18 | `Untitled-1.txt` | 2026-09-xx | 34.4 KB | Task 17: Jane Doe conditions lab test |
| 19 | `the valerious case_tick_84_with_action_Economy_event_log_2026-10-11T13-02-17.md` | 2026-10-11 | 366.0 KB | Action economy system verification |
| 20 | `benchmark_elena_vance_2026-10-25T17-20-33.json` | 2026-10-25 | 32.9 KB | The Proving Ground (/bench) 11-model test |
