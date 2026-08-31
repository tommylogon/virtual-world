# Task-242: Allow Agents to Create Triggers on Items

**Status**: Todo — not started. Scope lock 2026-08-30: new agent action via normalizeStructuredAction + /api/action, schema {item, when, effect}, reuse TriggerEditor internals (edge props + logic_trigger nodes) so human editors see them; limit to supported effects/conditions; ensure graph serialization round-trips.
**Source:** `dev_tasks/developer ideas.md` (allow agents to create their own triggers on items)

## Goal

Let AI agents add triggers to items at runtime â€” e.g. an agent crafts or enchants an item
and binds a behaviour (`on_use`, `on_take`, `on_examine`, timing) to it â€” moving trigger
authoring beyond the human designer.

## Notes / open questions

- New agent action + schema field (e.g. `create_trigger`: `{item, when, effect}`), routed
  through the existing `normalizeStructuredAction` and `/api/action` path.
- Security/sanity: scope what agents can express (supported effect/condition sets), and
  whether agent-created triggers persist (graph) and serialize.
- Interaction with the shared TriggerEditor data model (edge properties vs
  `logic_trigger` nodes) â€” reuse the same internals so human editors can see/edit them.
