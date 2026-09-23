# VirtualWorld Engine

A local, single-player simulation of a persistent world driven by AI agents. Flask and
vanilla JavaScript, no build step required to run, and no cloud dependency: point it at a
local model (LM Studio, Ollama) or any OpenAI-compatible endpoint and play.

The world is a **graph**, not a map. `area` nodes (rooms, clearings, marsh), `way` nodes
(every door, gate and passage, with six states), `item` nodes and `character` nodes,
connected by typed edges. Space is relational rather than metric - there are no distances,
and nothing physically traverses anything. It is theater of the mind by design.

## The rules the engine plays by

- **One entity, four processing levels.** Soak NPCs, simple NPCs, LLM agents and the human
  all exist at the same scale and follow the same rules. They differ only in how much
  cognition they get: thinking can refine what a character does, never grant capability
  they do not have.
- **One decision per turn, per character.** LLM calls never scale with turn length. A
  fifteen-minute turn is still one set of decisions.
- **A turn is a timeframe, not a currency.** One in-game minute by default, filled by an
  action flow rather than spent in unit costs. `minutes_per_turn` is tunable, and the world
  clock may run faster than realtime.
- **Identity is an id, never a display name.** Names are a resolution layer, so two
  characters can share one.
- **Show state as traces and sign, not tooltips.** Plain words for durability, moodlets
  that name the item you are carrying, honest defaults everywhere.
- **Out-of-focus stays cheap.** Background characters are simulated without LLM calls, but
  their fast decisions still respect what they could and want to do.

## Quick start

```bash
pip install -r requirements.txt
python app.py
```

Then open <http://127.0.0.1:4444>. On Windows, `start.bat` does the same thing.

Some features need an LLM provider configured in Settings (local providers work; the app
runs without one, but agents will not think).

## Commands

| Task | Command |
|---|---|
| Run the app | `python app.py` |
| Full test suite | `python -m pytest -q` |
| One test file | `python -m pytest tests/test_<name>.py -q` |
| JS lint | `npm run lint` |
| JS/TS typecheck | `npm run typecheck` |
| Lint an exported play log | `node tools/log_lint.cjs data/exports/<log>.txt` |
| Dev tasks (list, add, move, validate) | `python tools/tasks.py list` |

The suite baseline is roughly **3,239 passing with 60 known pre-existing failures**, all
from one broken MCP test harness. Compare against that baseline rather than expecting green;
details are in [`AGENTS.md`](AGENTS.md).

## Where things live

| Path | What it is |
|---|---|
| `app.py` | Flask app factory (`create_app`) |
| `engine/` | Game systems: time, vitals, conditions, triggers, sound, light, agents, memory |
| `routes/` | HTTP layer; `*_ops.py` holds the logic, the thin `routes/<x>.py` files only register URLs |
| `graph.py`, `virtual_world_engine.py`, `player.py`, `area.py` | World graph, engine facade, player model, area model |
| `static/js/` | Frontend: plain-DOM helpers and lit-html modules |
| `templates/index.html` | Page shell; script tags and modals live here, not in `static/` |
| `data/` | Saves, scenarios, and the content library under `data/library/<type>/` |
| `docs/virtualWorld/` | The design vault: system documentation and the dev-task tree |
| `tools/` | One-off scripts, the dev-task helper, and the log linter |

## Reading more

- **[`AGENTS.md`](AGENTS.md)** - architecture, conventions, testing, and known gotchas.
  The practical entry point for working in this repo.
- **[`CHANGELOG.md`](CHANGELOG.md)** - what shipped, release by release.
- **[`docs/virtualWorld/History.md`](docs/virtualWorld/History.md)** - where this came from.
- **[`docs/virtualWorld/_Index.md`](docs/virtualWorld/_Index.md)** - the wiki index; every
  system has a page.
- **[`docs/virtualWorld/Patch Notes 2026-08-22 to 2026-09-22.md`](docs/virtualWorld/Patch%20Notes%202026-08-22%20to%202026-09-22.md)**
  - a single narrative of one month of work.

## License

MIT. See [`LICENSE`](LICENSE).
