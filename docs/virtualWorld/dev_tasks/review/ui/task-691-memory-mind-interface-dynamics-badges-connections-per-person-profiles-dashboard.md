---
type: task
status: review
area: ui
priority: medium
parent: task-685
---

# task-691: Memory Mind interface: dynamics badges, connections, per-person profiles, dashboard

**Filed:** 2026-10-04
**Related:** task-685
**Mockup:** `docs/design/memory-mockup.html` (static, not wired)

## Goal

Grow the inspector's Memories tab (`static/js/inspector/memory-view.ts`) from a
flat list into the memory mind, in four stages — engine fields from task-686
are the prerequisite:

> **Progress 2026-10-04:** stages 1–4 all landed and verified live in the
> browser against a seeded scenario (stats header + filters, dynamics badges,
> editor Category/Confidence/Connections with symmetric link sync, the
> per-person panel over a new `GET /memories/people` endpoint, and the full
> **Memory Mind** dashboard as `static/js/inspector/mind-view.ts` — timeline
> ribbon, category filters, detail pane with contradicts / derived-from /
> same-entity connections, accessibility panel, people panel). Live check
> also caught and fixed two wiring gaps: contradiction detection now runs on
> the HTTP write path, and attitude statements ("I do not trust Anna…") no
> longer link as factual contradictions. `tools/ts_convert.py check` green.
> Dashboard entry: the 🧠 Mind button in the Memories section header.

1. **Stats header** — count by category, average confidence, total
   reinforcements, faded count; **category filters** beside the existing
   search (All / Episodic / Beliefs / Semantic / Social / Contradicted / Faded).
2. **Dynamics on every card** — category chip, confidence %, `↻ ×N`
   reinforced, `⚡ contradicts N` (clicking jumps to the paired memory), faded
   styling under activation < 0.5, consolidated/trace badge; editor gains
   Category select + Confidence slider + contradicts link list (removable).
3. **Per-person panel** — derived profile from `engine/derive.py`
   (trust/fear/attraction/disgust/respect, band label, contributing memory
   count) rendered beside the memory list; clicking a person filters memories
   to their `rel:` tag.
4. **The full dashboard** (timeline ribbon, decay chart, memory graph,
   standalone surface) — the mockup is the design target; only start this
   after stages 1–3 are live in the inspector.

House rules: `.ts` source only (never hand-edit emitted `.js`), run
`python tools/ts_convert.py check` before commit, keep the existing editor
sections working (types, emotions, entity references, negative-tick seeds,
embedding status).

## Acceptance

- [ ] Stage gate each: 1 and 2 land together with task-686/689 wiring proof; 3 renders real derived data for a character with rel-tagged memories (measured, not assumed).
- [ ] Every badge value shown is a field the backend actually wrote — no decorative numbers.
- [ ] `tools/ts_convert.py check` and `node tools/unit/run.cjs` pass.
- [ ] Editor round-trips category/confidence/contradicts through the entry update endpoint.

## Open questions

- Does the dashboard need to exist inside the inspector at all, or is it a
  separate "mind view" route (there is precedent: the graph view)? Decide
  after stages 1–3 — the inspector panel may be enough.
- The mockup shows an emotional-encoding panel with named affect rows; the
  memory editor already edits `memory_emotions` — reuse that vocabulary, do
  not invent a second one.
