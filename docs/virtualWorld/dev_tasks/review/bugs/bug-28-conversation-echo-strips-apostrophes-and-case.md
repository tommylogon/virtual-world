# Bug 28 — === CONVERSATION === echoes characters' own speech mangled (apostrophes stripped, lowercased)

**Status**: Resolved as historical — the corruption was real, the transform is
gone. Regression guards added (see bottom). Recommended: close.

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

## Re-investigation — 2026-09-28 (WT-C): the corruption was real, the transform is gone

**The transform is exactly `'` -> space, plus a full lowercase.** Nothing else.
`—`, `?`, `!`, `...`, `*burp*` and every other character survived untouched, which
is what makes this identifiable: `that's` -> `that s`, `I'm` -> `i m`, `you're` ->
`you re`, `haven't` -> `haven t`, `I'll` -> `i ll`, `I've` -> `i ve`, `it's` ->
`it s`, `nobody's` -> `nobody s`, `my name's` -> `my name s`. Every mangled
example in both bug files, across all three Taco Bell exports, is that one rule.

**The filed "letter scrambling" oddity is not a second bug.** In
`taco_bell_event_log_2026-08-23T16-19-57.txt:288` the *event log* itself already
reads `"Pleas edont try to be cnormal, i like your whole chaos thing, its
perfect! ... wnat me to lick it away"`. That text was stored mangled and
lowercased (bar the leading `P`) **before** any prompt was built, so it is not a
prompt-builder artefact at all — it is the NPC agent's own generated line for
that tick. `wnat` is `won't` with the apostrophe gone. The corruption the two bug
files could not place in code was upstream of the engine the whole time.

**Direct evidence that the transform used to exist and no longer does.** Same
export file, same turn, same utterance, two renderings:

| line | block | text |
|---|---|---|
| 640 | `You said:` | `NO. no licking. absolutely not, that's— that's advanced DLC content, you haven't even unlocked the first date yet!! i'll handle the cheese situation MYSELF...` |
| 719 | `You recently said:` | `...absolutely not, that s— that s advanced dlc content, you haven t even unlocked the first date yet!! i ll handle the cheese situation myself...` |

The verbatim form and the mangled form of one utterance sit in the same file. The
`=== WITNESSED ===` block at line 423 was mangled the same way while the event
log at line 288 kept its `P` — so the pass sat between the stored event and the
prompt, exactly as originally suspected, and applied to more than one block.

**Current code is clean, verified by test, not by reading.** Added
`tests/test_speech_verbatim.py` (6 tests, all passing) pinning verbatim
preservation across every hop: `recent_hearing` for speaker and listener, the
directed-whisper copy, `speech_log`, the `speak` turn event, and
`NarrationSystem.listen()`. Added 4 tests to
`tools/unit/test_conversation_context.js` pinning `ownRecentSpeech`,
`buildConversationInstinct` and `markSpeechLine` against apostrophe-stripping,
lowercasing, and a dedupe that overwrites the first spelling with the second.
All 18 conversation-context tests pass.

**Verdict: no live repro, and none is possible without reintroducing the bug.**
The pass no longer exists in `engine/speech.py` or in
`static/js/agent/prompt-builder/`. This is hypothesis (a) from the 2026-09-22
note — the conversation-context refactor removed the old builder — confirmed
against the artifacts rather than against the source. No code fix was made
because there is nothing to fix; the guards are the deliverable.

**Verify (unchanged, still the right manual check)**: new play session, speak a
line containing apostrophes + capitals, next decide-phase `CONVERSATION` block
matches the spoken text verbatim.

