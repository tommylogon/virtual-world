# Trace Format (objective, code-written history)

The **trace** is a compact, append-only, per-character record of what actually
happened, written by code — never by the LLM. It is the substrate for:

- first-person **memory** (the LLM summarizes a trace window into memory),
- **"what have you been up to?"** when you click a background character,
- **reversibility** on promote/demote (see [[reversibility-contract]]),
- and debugging long runs (an auditable objective record).

It is deliberately *not* the memory store. Memories are subjective, sparse, and
LLM-authored. The trace is objective, mechanical, and free.

## Entry schema

Each entry is a plain dict (JSON-friendly) on `player.trace_log`:

```json
{
  "t": 4120,              // world tick
  "kind": "need",         // see kinds below
  "what": "became very hungry",
  "why": "needs:hunger",  // reason tag, from the deciding layer
  "area": "Food Storage",
  "tags": ["need"],       // short labels for filtering
  "salient": false,       // survives rollup when true
  "delta": null           // optional small numeric payload, e.g. {"HP": -1}
}
```

Field rules:

- `t` — required, integer world tick (`world.time_ticks`).
- `kind` — required, one of the enumerated kinds below.
- `what` — required, short third-person objective phrase ("took 2 rations").
- `why` — a reason tag naming *why this happened* (see reason tags). Optional
  but strongly preferred; this is what makes background activity explainable.
- `area` — the area name at the time, when relevant.
- `tags` — 0–3 single-word labels (`need`, `combat`, `trade`, `travel`).
- `salient` — set true for things worth remembering (deaths, discoveries,
  conflict, relationship change, first encounters, completed plans).
- `delta` — optional; only for things a reader may want numerically (HP loss).

## Kinds

| kind | meaning | typical `why` |
|---|---|---|
| `move` | changed area / arrived | `goal:travel`, `need:shelter` |
| `act` | performed an action verb | `goal:*`, `plan:*` |
| `need` | a vital crossed a tier | `needs:hunger` |
| `condition` | condition gained/lost | `react:*`, `env:*` |
| `encounter` | another character involved | `social:*`, `threat:*` |
| `observe` | notable percept | `sense:*` |
| `plan` | plan/sequence started or completed | `plan:*` |
| `death` | character died (salient) | `cause:*` |
| `promote` / `demote` | fidelity boundary crossed | `sim:fidelity` |

## Reason tags

`why` names the layer that decided the action, so the reason survives even when
the LLM that chose it is long gone:

- `needs:<vital>` — driven by a pressing need (hunger, thirst, rest).
- `goal:<name>` — serving a chosen goal/plan.
- `plan:<name>` — executing a standing plan (background rule tier or LLM).
- `social:<name>` — prompted by another character.
- `threat:<source>` — reactive to danger.
- `order:<character>` — following someone's instruction.
- `env:<factor>` — forced by environment/weather/area status.
- `llm:<reason>` — an LLM deliberation chose this (foreground only).

## Granularity

The trace is not an action log for its own sake. Write at the level a person
would actually remember or a reader would care about:

- Routine mechanical steps are **collapsed** ("crossed the camp to the store",
  not every way-node traversed).
- Needs are recorded only on **tier crossings** (e.g. crossed into "very
  hungry"), not every tick.
- Salient events are recorded **individually** and marked `salient`.

## Retention and rollup

`player.trace_log` is capped (default 200 entries, mirroring the memory store).
`engine.trace.rollup()` runs periodically and:

1. Drops the oldest non-salient entries first.
2. Compresses long runs of the same `(kind, why, area)` into one summary entry
   ("spent the day working in the Workshop", `kind: "plan"`).
3. Always keeps `salient` entries (bounded separately).

## Trace → memory

Code writes the trace; the LLM writes memory. The bridge is a window:

```
engine.trace.summarize_window(player, since_tick)  ->  text lines
```

Used at natural boundaries (plan/sequence completion, promotion, end of day),
the LLM turns that window into 1–3 first-person memories in the existing memory
store. This is why objective trace must come first: LLM memory alone drifts
(a recorded run had a character "remember" a waxwork man who was never there).

## Serialization

`player.trace_log` is a list of plain dicts, written by `Player.to_dict()` and
restored in `engine.serialization._deserialize_player`. Bounded, so it does not
blow up save size.
