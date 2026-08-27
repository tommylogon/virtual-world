# task-345 — Grammar guardrail for LLM-generated appearance text

**Status**: Todo — filed 2026-08-27 from export-log review.

## Found

Mansion session (mansion_event_log_2026-08-23T15-04-54.txt), sammy lopez's
`Your appearance:` block, which is RE-SENT on every prompt:

> "your body is who lean and completely flat-chested, a fact **you is**
> deeply self-conscious about... **you is** tall and coltish at 171cm"

The appearance-generation call produced broken second-person grammar
("you is", "body is who"), and generated text is stored once and echoed into
every system/user prompt forever — errors become permanent, load-bearing
context that models also mirror in prose.

## Fix options

(a) Prompt-side: appearance generation already gets voice rules; add explicit
"always second-person singular ('you are/your'), never verb-agreement slips"
+ 2 few-shot lines of correct output.
(b) Validation-side: after generation, cheap check for known slip patterns
(`\byou is\b`, `\byou was\b`, `\bbody is who\b`) → one silent repair pass or
regen before persisting.
(c) Editor-side: task-42 memory editor / inspector could flag suspect grammar
for human touch-up.

Recommend (a)+(b): instruction plus automated catch. (c) optional.

## Verify

Generate appearances across several providers/models (incl. small local ones
— the repro came from stealth/ox-alpha) → zero `\byou is\b|\byou was\b` hits;
regression: pre-existing broken text can be repaired via a regenerate action.
