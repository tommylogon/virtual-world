---
id: 327
title: Context-Aware Vitals Threshold Messages
status: todo
priority: medium
created: 2026-08-23
tags: [prompting, agent-engine, vitals, ux]
---

# Context-Aware Vitals Threshold Messages

## Summary

Vitals threshold lines (`static/js/agent/prompt-builder/character-state.js`) are absolute —
they fire purely from a numeric vital crossing a threshold and describe one fixed situation.
Make them context-aware: the same low Social value must produce different text depending on
whether the character is alone, in company, or mid-conversation.

## Motivation

Observed contradiction (taco_bell_date run, 2026-08-23): Miki has Social 40, is seated
next to Jake, actively talking with him — and her prompt reads:

> You feel isolated. The silence presses in around you.

That is flatly wrong at the moment it matters most (a conversation). Threshold messages
that contradict the visible scene damage trust in the whole simulation layer, because the
LLM reads them as ground truth about its own state.

Other known-shaky cases:

- "The silence presses in around you" in a noisy area (taco bell hum, drive-thru speaker).
- Hunger/thirst lines that ignore whether food/drink is literally on the table in front of
  the character (CRITICAL NEEDS already handles urgency separately).
- Sanity-tier dread text applied identically in a bright fast-food restaurant and a
  haunted cellar (genre mismatch tracked separately in task-328).

## Implementation

### 1. Build a lightweight scene context object

Assemble where vitals lines are currently generated, from data already available in
`worldState`:

```js
{
  alone: bool,                    // no other characters in area
  companyCount: int,
  wasAddressedThisTurn: bool,     // witnessed block contains [Heard → addressed to you]
  inConversation: bool,           // recent exchanged lines with someone present
  areaNoise: 'quiet'|'noisy',     // from area environment.noise heuristics
  areaTags: [...],                // exterior, restroom, kitchen...
  timeOfDay: 'day'|'night'        // from game clock
}
```

### 2. Gate and branch line families instead of single strings

Each threshold line becomes a small selector keyed by context. Sketch for low Social:

| Context | Line |
|---|---|
| alone | "You feel isolated. The silence presses in around you." |
| company, not engaged | "Being around people feels harder than it should today." |
| company, addressed/in conversation | "You hang on their words a little too much." |

Hunger/thirst: mention available food only as a hint when items are actually visible in
the area item list ("Your stomach growls — the smell of the burrito isn't helping."),
otherwise keep current generic line.

### 3. Keep CRITICAL NEEDS untouched

The urgent-need plan-forcing block works well (proven in taco run) and stays as-is.

## Acceptance Criteria

- [ ] No threshold line can contradict an observable fact of the current scene
      (people present, noise level, visible relevant items).
- [ ] Low-Social-during-conversation produces connection-seeking wording, never
      isolation wording.
- [ ] All new lines are genre-neutral (see task-328) and second-person safe.
- [ ] Re-run taco_bell_date scenario: Miki turn-0 prompt no longer says "isolated"
      while Jake stands beside her.
