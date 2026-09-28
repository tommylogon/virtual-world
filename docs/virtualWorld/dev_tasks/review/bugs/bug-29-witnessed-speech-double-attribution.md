# Bug 29 — Same witnessed speech appears twice with different attributions

**Status**: Premise disproven against the artifact. Recommend closing — no
defect to fix and nothing to guard.

## Found

Taco Bell session. Jake's opening compliment was said ONCE (tick 4). In a
later turn's `=== WITNESSED ===` it appears two ways simultaneously:

```
[the man → to you] said: "pleas edont try to be cnormal, i like your whole chaos thing..."
[the man] jake halloway he winks as he answers her.
[Heard → to you] a man's voice said: "so miki, you know you are really fun to hang out with, right?"
```

Line 1 is the NEW unacknowledged line (turn-local), line 3 is the OLDER line
rendered through the stranger/anonymized path ("a man's voice") rather than
"[the man]". Two candidates:

a) Deliberate: an unanswered direct address lingers one extra turn so the ball
   stays visibly in the character's court — but then attribution flipping
   between "[the man]" and "[Heard → to you]" between renders of the SAME
   event is inconsistent.
b) Duplicate posting: the speech got recorded into both this-turn events and a
   "pending conversation" carry-over list.

## Investigation — 2026-09-22 (code trace)

`room-context.js` builds WITNESSED from two separate sources and dedupes them:

- local `turn_events` (same area, other actors) → `witnessedLines`,
- `player.recent_hearing` → `heardSpeech`, filtered by a `seenSpeechKeys` set
  keyed `${speaker}|${text.toLowerCase()}` and a contains-match against local
  narration (`room-context.js:603-693`).

The two lines in the repro have **different text** ("...i like your whole chaos
thing" vs "...you are really fun to hang out with, right?"), so they are two
distinct utterances by the same speaker, not one event rendered twice. Different
attribution per source (local event → `[the man]`; `recent_hearing` → `[Heard
→ to you] a man's voice`) is expected behaviour.

**Verdict:** the "double attribution" premise is unproven. To make this a real
bug we need a repro where the *same* line (ideally same tick) appears under two
attributions; the dedupe already keys on speaker+text, so the gap would be
speaker-label instability (e.g. "the man" vs "jake halloway" vs "a man's voice"
for one speaker), not duplicate posting.

## Also noticed

Line 1 shows the letter-scrambling corruption from bug-28's log
("pleas edont", "cnormal"); same unexplained source, tracked there.

## Why investigate

If (b), every directed-but-unanswered line double-charges prompt attention and
can nudge models into answering stale content. If (a), we should at least keep
attribution stable for the same event across turns.

## Action

Trace how WITNESSED entries are built per turn (room_perception /
scene_snapshot + client context-sections): find where an event can enter twice,
or confirm the carry-over design and document it. Then either dedupe by event
id or pin one attribution form for carried-over balls.

## Verify

Two-agent room: A says X to B; B's next TWO prompts contain exactly one entry
for X each turn, attributed identically both times.

## Re-investigation — 2026-09-28 (WT-C): confirmed false alarm, recommend closing

Read the exact lines the report quotes, in
`data/exports/taco_bell_event_log_2026-08-23T16-19-57.txt:422-425`:

```
=== WITNESSED ===
[the man → to you] said: "pleas edont try to be cnormal, i like your whole chaos thing, its perfect! ..."
[the man] jake halloway he winks as he answers her.
[Heard → to you] a man's voice said: "so miki, you know you are really fun to hang out with, right?"
```

The premise fails on the artifact, not just on inference: line 423 and line 425
are **different utterances by the same speaker** ("...i like your whole chaos
thing" vs "...you are really fun to hang out with, right?"). The 2026-08-22 note
called this correctly; nothing has changed since.

**The predicted alternative — speaker-label instability — is also not live.**
The three labels in that block (`the man`, `jake halloway`, `a man's voice`) are
real, and in current code they cannot disagree, because both the bracket label
and the in-body name are derived from the same value:

- `room-context.js:646` computes `anon = PromptBuilder.anonymousName(...)` once
  and uses it for the bracket.
- `room-context.js:653-656` replaces the raw actor name inside `descText` with
  that *same* `anon`.

So `[the man] jake halloway he winks` — a bracket that anonymises next to a body
that leaks the name — is not reachable today; both would say `the man`. The
bracket/body split in that log is a 2026-08-23 artifact, same vintage as the
apostrophe bug in bug-28. (`voiceLabel` for cross-room lines uses
`isKnownToViewer` too, so it agrees with `anonymousName` rather than competing
with it.)

**One latent inconsistency, deliberately not fixed.** The two sites ask
"do I know this name?" with slightly different predicates:

- `worldState.hasMet` (`static/js/world-state.js:170`) returns false when
  `rel.closeness === undefined`;
- `room-context.js:650` uses `first_sighting === false` and ignores closeness.

A relationship record with `first_sighting: false` and no `closeness` would
therefore anonymise the bracket but keep the name in the body. It is **not
reachable from shipped content** — every `first_sighting` in
`data/library/characters/*.json` and `data/scenarios/*.json` is paired with a
`closeness` (`ensure_relationship` always writes it, and deserialisation at
`player.py:1070` indexes `data["closeness"]` directly, so a save cannot omit it).
It would need a hand-edited or legacy save. Fixing unreachable code on a
disproven bug is inventing a fix, so this is recorded, not patched. If anyone
later adds a relationship path that omits `closeness`, make the two predicates
one function at that point.

**Verdict: close.** No duplicate posting, no attribution instability, no defect.
A dedupe-by-event-id change would be untestable against a bug that does not
exist, and would risk collapsing the legitimate carry-over of an unanswered line
into the next turn's prompt.

