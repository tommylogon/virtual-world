# Bug 28 — === CONVERSATION === echoes characters' own speech mangled (apostrophes stripped, lowercased)

**Status**: Todo — investigated 2026-09-22, not reproducible from current code.
Needs a live repro before any fix; likely obsolete after the conversation-context
refactor.

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

## Investigation — 2026-09-22 (code trace, no repro)

Traced the whole path and found **no transform that strips apostrophes or
lowercases**:

- `engine/speech.py:207-215` builds the hearing event with `"text": speech_text`
  verbatim; `:272` copies `dict(event)` into each listener's `recent_hearing`.
- `static/js/agent/prompt-builder/conversation-context.js:117-131`
  (`ownRecentSpeech`) only trims + dedupes (`toLowerCase` is used solely as the
  dedupe key, never written back).
- Involuntary speech (`static/js/agent/involuntary.js`) only stutters the first
  letter or splices `*hic*` fragments — it does not lowercase or strip `'`.

So the mangled text in the report must have been the text actually broadcast at
that tick, not a corruption introduced while building the prompt. Two candidate
explanations: (a) the refactor since 2026-08-27 removed the old builder that did
this, making the bug obsolete; (b) the model emitted the mangled line itself and
the "original" quoted in the report came from a different source.

**Related oddity:** the same taco_bell log shows a *different* corruption shape —
`please don't` → `pleas edont`, `normal` → `cnormal` (bug-29's local line). That
is letter scrambling, not apostrophe/lowercase normalisation, and no such pass
exists in the code either. If either corruption is still live, capture the raw
`/api/action` request body and the `recent_hearing` entry side by side — that
separates an upstream text bug from a prompt-builder bug.

