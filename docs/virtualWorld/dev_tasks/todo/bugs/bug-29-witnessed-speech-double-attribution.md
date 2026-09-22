# Bug 29 — Same witnessed speech appears twice with different attributions

**Status**: Todo — investigated 2026-09-22. The filed evidence does **not** show
duplication (the two lines are different utterances), so this is most likely a
false alarm. Keep open only pending a repro that pins a single event id twice.

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

