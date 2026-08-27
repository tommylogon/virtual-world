# Bug 29 — Same witnessed speech appears twice with different attributions

**Status**: Todo — verify first; may be intentional lingering-ball behavior.

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
