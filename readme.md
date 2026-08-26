# VirtualWorld

**A game engine and living simulation where AI agents control NPCs in a persistent virtual world.**

VirtualWorld exists to answer a question: what happens when LLM-driven characters don't just chat, but *live* somewhere? A world where an NPC gets cold, hears a fight through a wall, remembers who stole from them, holds a grudge, plans revenge, and acts on it, all simulated down to the smallest details.

![status](https://img.shields.io/badge/status-actively%20developed-green)
![tests](https://img.shields.io/badge/tests-~1%2C090%20automated-blue)

## What it does

- **Graph-based persistent world** - areas connected by ways, filled with items and characters, all defined as editable JSON libraries (data-driven, no code changes needed to author content)
- **AI-agent NPCs** - characters are LLM-driven agents with simulated senses (sight, hearing with sound propagation, touch), spatial memory, relationships, threat awareness, initiative and autonomous replanning
- **Physiological simulation** - body temperature, vitals (hunger, energy, bladder), health conditions with cascading effects (bleeding, intoxication, exhaustion), body parts
- **Environmental simulation** - weather, ambient temperature, lighting and time of day, all feeding agent perception
- **Live world editor** - an interactive graph view of the entire world with inspector panels per entity, a trigger editor, a library browser with template sync, and a schema-driven engine config UI. The world can be built and adjusted while it runs
- **Event stream** - every turn, agent action and system effect rendered as an inspectable, scrubbable feed, including the raw LLM response
- **MCP server** - ~60 tools exposing the engine to coding agents (Claude, Kilo, etc.), so AI agents can *build and operate the world themselves*, not just play in it

## Why

The project is inspired by research on simulated agents, most notably Stanford's
[*Generative Agents*](https://arxiv.org/abs/2304.03442) (the "Smallville" experiment) and the open-source
humanoid-agent community that followed it. Those projects showed LLM characters with memory and reflection.
VirtualWorld takes the next step: a real engine where agents have bodies, environments and consequences,
where the smallest physical detail is available to the agent's context, and where the world keeps existing
when you stop looking.

It is also a playground for agentic AI workflows: the engine is operated and extended by AI agents under
human direction. Architecture, specifications and verification are human work; the agents write code; a
~1,090-test suite decides what ships.

## Architecture in one paragraph

Python/Flask backend (~50 modules, split by concern: sound, lighting, temperature, spatial memory,
speech, conditions, triggers...), exposed as a REST API. A vanilla ES6 + lit-html frontend with no build
step renders the world as an interactive graph (vis.js) with live synchronization. Worlds, characters,
items, traits and conditions are data-driven JSON libraries. An MCP server (FastMCP) wraps ~60 engine
operations as agent-callable tools.

## Quick start

Requires Python 3.10+ and an OpenAI-compatible LLM endpoint (LM Studio, OpenRouter, OpenAI, ...).

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows (source .venv/bin/activate on Linux/Mac)
pip install -r requirements.txt
python app.py
```

Then open the UI, point the LLM settings at your endpoint, and start playing or building.
For agent-driven operation, run `mcp_server.py` and connect your MCP client.

## Documentation (the wiki)

Full design documentation lives in [`docs/virtualWorld/`](docs/virtualWorld/):

- [AI & Narration](docs/virtualWorld/AI%20&%20Narration/) - memory system, agent architecture, prompting
- [Environment](docs/virtualWorld/Environment/) - temperature, sound, weather and lighting systems
- [Library System](docs/virtualWorld/Library%20System/) - the data-driven content model
- [Rules Engine](docs/virtualWorld/Rules%20Engine/) - conditions, triggers and effects
- [Graph & Editor](docs/virtualWorld/Graph%20&%20Editor/) - the live editor internals
- [dev_tasks/](docs/virtualWorld/dev_tasks/) - the full task kanban (todo / in progress / review / done) documenting how the project is actually built

## Testing

```bash
pytest
```

Approximately 1,090 automated tests cover the engine. A Playwright-based E2E suite covers the UI
(`npm install` in the project root, then run the suites under `tools/`).

## Status

Actively developed. Systems marked as planned in the wiki (see `dev_tasks/todo`) are on the roadmap.
