# Bug 28 — === CONVERSATION === echoes characters' own speech mangled (apostrophes stripped, lowercased)

**Status**: Todo — filed 2026-08-27 from export-log review.

## Found

Taco Bell session, decide-phase prompt (`=== CONVERSATION ===` block):

```
You recently said: "fun?? me?? that s— okay that s so nice of you to say
and i m going to be normal about it, watch me be normal..."
```

The original speech event (same log, tick 19) was:

```
"fun?? me?? that's— okay that's so nice of you to say and I'm going to be
normal about it..."
```

So somewhere between the speech event store and prompt-building, `'` is
removed as whitespace ("that's" → "that s", "I'm" → "i m") and the line is
lowercased.

Suspect: the anti-repeat conversation-history builder in the JS agent side
(`static/js/agent/` — likely context-sections / memory-context area) or a tag/
sanitizer applied to stored turn_events server-side. Trace where the
conversation section text is sourced.

## Impact

- ANTI-REPEAT instruction tells the model not to repeat lines it already
  said — but the reference lines are corrupted versions of its own words.
- Voice degradation leaks back: models sometimes mirror the corrupted forms.
- Same sanitizer probably touches other logged text (check WITNESSED rendering
  for identical mangling).

## Fix sketch

Locate the strip/lowercase pass; keep lowercasing decisions only where they're
intentional (speaker-name prefixing), preserve apostrophes in quoted speech.
Add a unit test: store `I'm — that's`, build conversation section, assert
apostrophes survive.

## Verify

New play session, speak a line containing apostrophes + capitals → next
decide-phase CONVERSATION block matches the spoken text verbatim.
