# Lived Log Format (objective, code-written history)

The **lived log** is a compact, append-only, per-character record of what actually
happened, written by code — never by the LLM. It is the substrate for:

- first-person **memory** (the LLM summarizes a lived-log window into memory),
- **"what have you been up to?"** when you click a background character,
- **reversibility** on promote/demote (see [[reversibility-contract]]),
- and debugging a character's recent history *within its retention window*.

It is deliberately *not* the memory store. Memories are subjective, sparse, and
LLM-authored. The lived log is objective, mechanical, and free.

> **Renamed from `trace` in task-542.** The old name was the problem, not a
> detail. "Trace" reads as instrumentation — an auditable objective record you
> would debug a long run with — and that reading invites merging this store with
> soak telemetry. They are not the same system. See
> [Not the same system as telemetry](#not-the-same-system-as-telemetry) below.

## Entry schema

Each entry is a plain dict (JSON-friendly) on `player.lived_log`:

```json
{
  "tick": 4120,           // world tick
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

- `tick` — required, integer world tick (`world.time_ticks`). Was `t` before
  task-542; the rename is deliberate, because this was the only cryptic key in an
  otherwise readable format and the cost of a longer name is not measurable.
- `kind` — required, one of the enumerated kinds below.
- `what` — required, short third-person objective phrase ("took 2 rations").
- `why` — a reason tag naming *why this happened* (see reason tags). Optional
  but strongly preferred; this is what makes background activity explainable.
- `area` — the area name at the time, when relevant.
- `tags` — 0–3 single-word labels (`need`, `combat`, `trade`, `travel`).
- `salient` — set true for things worth remembering (deaths, discoveries,
  conflict, relationship change, first encounters, completed plans).
- `delta` — optional; only for things a reader may want numerically (HP loss).

**Back-compat is load-bearing.** `engine/lived_log.py` `load()` accepts both
`tick` and the legacy `t`, and `engine/serialization.py` accepts both the
`lived_log` save key and the legacy `trace` key. This is not polish. `load()`
copies entries verbatim, so without the rewrite every legacy entry keeps `t` and
every reader falls back to tick 0 — which scrambles `rollup()`'s sort and makes
`since()` find nothing. That is **silent data corruption, not a load error**:
nothing raises, a promotion quietly writes no memory, and the only symptom is a
character who cannot remember their own life. It is one line in `load()` and must
not be dropped when the code around it changes.

## Kinds

The `KINDS` tuple in `engine/lived_log.py` is the declared vocabulary. The table
below lists **every kind a live call site actually writes**, with the writing
module, because the declared set and the written set have drifted apart.

| kind | meaning | typical `why` | written by |
|---|---|---|---|
| `move` | changed area / arrived | `goal:travel`, `need:shelter` | `engine/background_simulation.py` |
| `act` | performed an action verb | `goal:*`, `plan:*` | `engine/background_simulation.py`, `engine/tick_manager.py`, `engine/foraging.py`, `engine/background_social.py` |
| `need` | a vital crossed a tier | `needs:hunger` | `engine/tick_manager.py` |
| `plan` | plan/sequence started, completed, or failed | `plan:*` | `engine/background_plans.py`, `engine/timeskip.py` |
| `pursuit` | pursuit assigned or completed | `sim:*` | `engine/background_plans.py` |
| `traversal` | a crossing check result | `traversal:*` | `engine/background_simulation.py` |
| `death` | character died (salient) | `cause:*` | `virtual_world_engine.py` (`kill_player`) |
| `promote` / `demote` | fidelity boundary crossed | `sim:fidelity` | `engine/promotion.py` |
| `relationship` | closeness toward someone moved | `social:*` | `engine/relationships.py` |
| `social` | a social action at a tier | `social:*` | `engine/background_social.py` |
| `threat` | a threat reaction | `threat:*` | `engine/background_social.py` |

**Declared but with no writer found (2026-10-06):** `condition`, `encounter`,
`observe`. `condition` and `observe` *do* exist as method names, but on **soak
telemetry** (`engine/soak_telemetry.py`), which is the deliberately separate
system below — not on `lived_log`. Treat these three as aspirational until a
call site appears, or remove them from `KINDS`.

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

The lived log is not an action log for its own sake. Write at the level a person
would actually remember or a reader would care about:

- Routine mechanical steps are **collapsed** ("crossed the camp to the store",
  not every way-node traversed).
- Needs are recorded only on **tier crossings** (e.g. crossed into "very
  hungry"), not every tick.
- Salient events are recorded **individually** and marked `salient`.

## Retention and rollup

`player.lived_log` is capped (default 200 entries, mirroring the memory store).
`engine.lived_log.rollup()` runs periodically and:

1. Drops the oldest non-salient entries first.
2. Compresses long runs of the same `(kind, why, area)` into one summary entry
   ("spent the day working in the Workshop", `kind: "plan"`).
3. Always keeps `salient` entries (bounded separately).

## Lived log → memory

Code writes the lived log; code also writes the memory that summarizes it. The
bridge is `engine/promotion.py` (task-399, v1): on **promotion** (background →
attended) `promote()` reads the span since the last consolidation and writes
**one bounded memory** (`source="background"`, tag `background`) via
`player.add_memory(...)`. It is **deterministic and templated — no LLM call is
made** (task-412 non-goals); a later LLM pass may only *read* the trace. The
idempotence rule matters: the span is `tick > max(last_offload_tick,
background_consolidated_through)`, so a second promotion of the same span writes
nothing.

`engine.lived_log.summarize_window(player, since_tick)` is the window reader;
`engine/timeskip.py` uses it to seed a resume memory across a skip.

This is why objective history must come first: LLM memory alone drifts (a
recorded run had a character "remember" a waxwork man who was never there).

> **This bridge only fires on a fidelity change.** It does not run for a
> character whose tier does not change, so events that happen while a character
> stays attended or stays background are not promoted into memory by it. See
> [Known gaps](#known-gaps-2026-10-06).

## Known gaps (2026-10-06)

Measured against the live Kraktooth goblin camp. These are open; task-725 owns
the fix.

- **Interaction events are not written to the lived log at all.** `grab` /
  `escape` (`engine/grapple.py`) and attack damage (`engine/combat.py`) write no
  `lived_log` entry and no memory. A traversal or a fight therefore leaves no
  account a character can reflect on, and no entry for the memory bridge to
  promote. (Attack *does* move closeness −30 in `engine/relationships.py`; the
  event itself is still unrecorded.)
- **The memory bridge only fires on a fidelity change.** A character who stays
  attended (or stays background) does not get the span promoted, so a salient
  event — e.g. `kind: "death"` — can sit in `lived_log` and never reach
  `memories`, which is what the character Mind panel reads. Repro: a character
  died and their Mind showed no reason, no travel, no feelings, no vitals slide,
  and no reaction to resurrection.
- **Consequence for affect and relationships.** Because the events are not in
  memory, the character cannot reflect on them, their emotion/relationship state
  is not driven by them, and later conversation cannot reference them ("you
  tried to grab me last night").

The fix reuses the existing bridge (extend `engine/promotion.py` to salient life
events) or has Mind read salient `lived_log` entries — it does **not** merge the
stores.

## Serialization

`player.lived_log` is a list of plain dicts, written by both `Player.to_dict()`
(API responses) and `SerializationManager._serialize_player` (saves), and
restored in `_deserialize_player`. Bounded at 200 entries, so it does not blow
up save size.

> **Fixed in task-542:** the save path had a *reader* for a `trace` key and **no
> writer at all**, so the whole store was silently discarded on every reload —
> the module docstring's claim that entries "serialize with the save" was false.
> Scenario payloads (`to_scenario_dict`) drop `lived_log` for the same reason
> they drop `recent_hearing` and observation-sourced memories: a character does
> not *author* their own history, and keeping it would add 200 entries per
> character to every scenario file on the first save.

## Not the same system as telemetry

There are **two** record systems in this codebase. They look alike and are
deliberately incompatible.

| | `lived_log` | soak telemetry |
|---|---|---|
| scope | per **character** | per **run** |
| stored | **in the save**, on the player | **out of the save**, on the run |
| grain | salience-filtered, runs collapsed | complete, every move |
| test applied | "a person would remember this" | "measure exactly this" |
| lifetime | ~200 entries, rolled up | the whole run, then archived |
| consumer | LLM summarisation on promote/demote | dashboard, export, benchmark |
| if it leaks | an LLM "remembers" a life it never lived | the benchmark becomes fiction |

The rollup that makes the lived log *good* for memory is precisely what destroys
it for measurement. That is not a tuning difference — the two requirements are
incompatible, which is why they cannot be one store. Telemetry is built in
`engine/soak_runner.py` (task-543) and is owned by the run, not the player.

**The rule, stated once so it cannot be "optimised" away:**

> **Telemetry is never written to a `lived_log`, and the `lived_log` is never
> the dashboard's data source.** If you want "what happened" in a soak, derive it
> from telemetry.

Rules without reasons get optimised away, which is the whole reason this section
exists. The reason is in the table above: the two stores ask opposite questions
of the same data, and a merged store necessarily answers one of them wrongly —
either it forgets too much to be a benchmark, or it remembers too much to be a
memory.

The other side of the boundary — what telemetry records, how the space-time view
draws it, and the `why` vocabulary that keeps the two from drifting — is in
[Soak Lab telemetry and the space-time view](soak-lab-telemetry.md).
