---
id: 321
title: Conversation Response Instinct (salience + inclination + anti-repeat)
status: review
priority: medium
created: 2026-08-21
tags: [prompt-builder, agent, dialogue, prompting]
---

# task-321: Conversation Response Instinct

**Status** — In Review — implemented + verified 2026-08-21 (node --check clean, live browser test against running server using real Lyrie state, pytest baseline unchanged). Moved from todo/ 2026-08-21.

## Summary

Improve how characters respond to spoken dialogue without forcing them to act.
Two separable problems:

1. **Signal (salience)** — a character does not know whether a spoken line was aimed
   at *them* vs just overheard. Today every heard line renders identically as
   `[Heard] a voice said: "..."`, so the model must guess from the words and weak
   models hedge (e.g. Lyrie repeating "Hello? Is someone there?").

2. **Inclination + quality** — the single static line
   (`system-prompt.js` "RESPONSE PRIORITY") says only "usually prioritize a verbal
   response"; it gives no sense of *how directly* a line targets them, no guard
   against talking over a group, and no memory of their own recent lines, so
   repetition gets re-rolled fresh.

Design principle: **weighted emphasis, never a command.** Adding a "to you" marker
raises the salience a character *notices*, but the decision to speak stays the
character's — consistent with the project's "don't force characters to act" stance.

## No-schema-change constraint

No new stored `to:` field on speech (the humans-don't-get-tagged-by-the-universe
finding). Instead the *listener's* attention reads the line's text (name call, "you"
pronoun, group-open wording) at prompt-build time and marks its direction. The
inclination drift reuses existing state (`vitals.social`, emotional conditions) plus
a per-character optional override in the personality or trait text, so nothing
requires a data migration.

## What was implemented

- `static/js/agent/prompt-builder/conversation-context.js` (new):
  - `classifySpeechTarget(text, charName, player)` — heuristic on the spoken text:
    listener name/alias call → `addressed_to_you`; group-open wording
    ("everyone/anybody/anyone/you all" + a question) → `to_group`; clear second-person
    "you" → `to_you`; else `overheard`. Returns a stable tag + short label.
  - `markWitnessedLine(line, text, charName, player)` — renders the leading tag
    (`[Heard] → addressed to you: "..."`) right on the WITNESSED line, so the model
    sees the salience at a glance without a separate index.
  - `buildOwnRecentSpeech(state, charName, player)` — the character's own recent
    quoted lines (from the same source that feeds WITNESSED hears, but only lines
    the character themself spoke), used as a soft anti-repeat guard.
  - `buildTalkinessHint(player, actionState)` — a per-turn inclination line derived
    from existing state (`vitals.social`, key vitals/emotions), phrased as the
    character's *current* disposition toward speaking (e.g. "you are withdrawn
    right now"), not a mandate.
- `system-prompt.js` — replaced the single "RESPONSE PRIORITY" line with a compact
  `CONVERSATION INSTINCT` block explaining: the WITNESSED `→` markers mean *directed
  at you* (respond to the content — their name, their actual question/words) vs
  bare `[Heard]` = overheard (respond, react, or go on as you were — all fine);
  and the anti-repeat rule (do not repeat a line you already said, unless genuinely
  re-asserting). This is emphasis + grammar-free, never a compel.
- `room-context.js` — wires the classification into the WITNESSED assembly so
  called-name / to-you / to-group lines render distinctly.

## Why the wording is loose (and that's on purpose)

The mechanism deliberately "clarifies the option to respond, not morally law" — a
direct "Hey Lyrie, watch out!" *should* feel spurring, but the character can still
choose silence if hiding/sneaking/in danger. The INSTINCT text says so explicitly.

## How verified

- `node --check` on all touched JS files.
- WITNESSED render check: a line containing the character's own name gets the
  `→ addressed to you` tag; a group-open question gets `→ to the group`; unrelated
  chatter stays bare `[Heard]`.
- Anti-repeat: when the character already spoke a line this window, the reaction /
  decide prompt surfaces "you already said: ..." so repetition is aware-not-forced.

## Notes

- Guards against eager-response: the `to_group` and `overheard` classes carry NO
  "must respond" directive — those resolve ie get responded to or not, by the
  moment. Only `addressed_to_you` nudges.
- This is the first pass; the eventual (optional) `to:` field on speech (backend +
  speak UI) remains possible later as a true "said to you" channel (Fork 1B), kept
  out of scope here to honor the no-forcing principle and no-schema-change goal.