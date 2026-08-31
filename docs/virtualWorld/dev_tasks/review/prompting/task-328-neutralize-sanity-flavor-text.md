---
id: 328
title: Neutralize Sanity Flavor Text (De-Horror, De-Madness)
status: todo
priority: high
created: 2026-08-23
tags: [prompting, vitals, sanity, copy]
---

# Neutralize Sanity Flavor Text (De-Horror, De-Madness)

**Status**: In Review — implemented 2026-08-31, code-verified + live browser check. Neutral stress wording applied to BOTH sanity surfaces (the design noted "four tier strings + stray line": the strings now live in `buildInsanityContext` tiers AND `describeVital('Sanity')` tiers — both fire in the same prompt, so both were neutralized per Tommy's confirmation). `rg "shadow|dark corner|madness|reality bends"` over the prompt-builder now hits only doc comments, no runtime prompt strings.

## Summary

The Sanity tier strings in `static/js/agent/prompt-builder/character-state.js`
(lines ~100–103 and the "shadows seem to watch you" line at ~208) are horror-generic:
"The dark corners of every area feel threatening", "The shadows seem to watch you",
"Reality bends and fractures around you". Replace with neutral, composure-based wording.
Madness/hallucination-style text belongs to actual conditions, traits and intoxication —
which are separate systems — not to the base sanity vital.

## Motivation

Observed in taco_bell_date run (2026-08-23): Miki (Sanity 70) sits in a bright Taco Bell
and her prompt tells her "the shadows seem to watch you." Wrong genre, wrong scene.

Design rule (Tommy, 2026-08-23): low *sanity* means stress, frayed nerves, poor composure —
NOT madness. Madness/delusion/disorientation effects must come from named conditions
(poisoned, drunk, drugged, cursed, panicking) which already have their own symptom text
and known/unknown gating. The vital's baseline text should read plausibly for any setting:
fantasy tavern, horror mansion, modern fast food.

## Implementation

Rewrite the four tier strings + stray line as scene-neutral escalation of stress:

| Tier | Replacement direction |
|---|---|
| ≤75 | "A low hum of unease you can't quite shake. You keep double-checking things." |
| ≤50 | "You feel strained and irritable. Patience is thin and everything grates." |
| ≤25 | "Nerves frayed raw. You flinch at small sounds and snap at small annoyances." |
| ≤10 | "Barely holding it together. Every decision feels heavier than it should." |
| line 208 | "A creeping sense that something is off, even if you can't name it." |

Rules:

- No genre nouns (shadows, dark corners, whispers of madness, reality bending).
- No medical/insanity framing — that vocabulary is reserved for condition symptoms
  (`apply_condition` sources: poison/drugs/alcohol/curses).
- Escalation should read as *stress curve*, usable by an LLM to color behavior
  (jumpiness, irritability, indecision) rather than hallucinated content.
- Keep second-person voice; no pronoun+verb constructions (converter-safe per G1).

## Acceptance Criteria

- [ ] `rg "shadow|dark corner|madness|reality bends"` over prompt-builder returns no
      vitals-threshold hits.
- [ ] taco_bell_date re-run: Miki's prompt shows stress wording that fits a lit restaurant.
- [ ] Horror mansion run: low-sanity characters still feel appropriately tense via the
      neutral wording + area/environment dread lines, not hardcoded gothic imagery.
