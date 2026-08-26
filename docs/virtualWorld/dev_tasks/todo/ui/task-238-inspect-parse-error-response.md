# Task-238: Click a Parse Error to Inspect the Raw Response

**Status:** In backlog — filed 2026-08-16 from developer ideas backlog.
**Source:** `dev_tasks/developer ideas.md` (click on parse error to see responses?)

## Goal

When an LLM response fails to parse (JSON extraction fails, or a state/action parse error),
surface the raw response text in a clickable way so the bad output can be inspected for the
cause. Currently parse failures likely just log an error with no easy way to see the raw
payload in the UI.

## Notes / open questions

- Which surfaces hit parse errors: agent `_parseReaction`/`_normalizeStructuredAction`,
  AI generators (`AIGenerator`), emote parsing, skill-check parsing?
- Where to attach the click: an error bubble in the event stream, or a toast that expands
  to show the raw text.
- Store the last N raw responses (browser-side ring buffer) and link a parse-failure click
  to the matching raw payload.