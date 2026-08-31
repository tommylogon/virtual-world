# PZBridge — NPC Control for Project Zomboid

A two-part system that lets you control NPCs in Project Zomboid from an external Python script (or an LLM agent).

## What it does

- **PZBridge Mod** (Lua): runs inside PZ, opens a localhost HTTP server on port 8742
- **PZBridge Client** (Python): connects to the bridge to spawn, move, and command NPCs

## How to install

### 1. Install the mod

Copy the `pz_bridge/` folder into your Project Zomboid mods directory:

**Single-player:**
```
%USERPROFILE%\Zomboid\mods\PZBridge\
```

**Dedicated server:**
```
%USERPROFILE%\Zomboid\Server\mods\PZBridge\
```
Then add `PZBridge` to your `Mods=` line in `servertest.ini`.

The folder structure should be:
```
PZBridge/
├── mod.info
└── media/
    └── lua/
        └── server/
            └── BridgeMod.lua
```

### 2. Enable the mod in-game

- Launch PZ, go to **Mods**, find **PZBridge**, enable it
- Load a save (or start a new one)
- The bridge starts automatically when the world loads

### 3. Run the Python client

```bash
python pz_client.py
```

If PZ is running with the mod, you'll see a world snapshot. If not, you'll get a "Connection refused" warning — this is expected, the bridge needs the game world to be loaded.

## API Endpoints

All endpoints are served on `http://127.0.0.1:8742`.

### `GET /snapshot` — World state

Returns JSON with player position, zone, items, zombie count, time, weather, and spawned NPCs.

### `POST /npc` — Spawn an NPC

```json
{ "name": "Bob", "skin": "Base.SurvivorMale", "x": 11000, "y": 9000, "z": 0 }
```

Returns `{"status": "ok", "action": "spawn", "name": "Bob"}`

### `GET /npc` — List NPCs

Returns all spawned NPCs with their positions and states.

### `POST /act` — Control an NPC

```json
{ "npc": "Bob", "action": "say", "params": { "text": "Hello!" } }
```

Supported actions:

| Action | Params | Description |
|--------|--------|-------------|
| `move_to` | `x`, `y`, `z` | Teleport NPC to coordinates |
| `walk_to` | `x`, `y`, `z` | Pathfind NPC to coordinates |
| `say` | `text` | Speak out loud |
| `attack` | `target_type` ("zombie") | Attack nearest zombie |
| `loot` | `item` | Pick up item from ground |
| `follow` | `target` (player name) | Follow the target |
| `set_state` | `state` ("idle"/"fleeing"/"moving") | Set NPC state |
| `stop` | — | Stop following, go idle |

### `GET /zone` — Current zone info

Returns room/zone metadata for the player's current location.

## Example: Spawn and command an NPC

```bash
# Spawn Bob at the current player location
python pz_client.py spawn Bob 0 0 0

# Make Bob speak
python pz_client.py act Bob say "Hey, need any help?"

# Bob follows you
python pz_client.py act Bob follow

# Bob attacks nearby zombies
python pz_client.py act Bob attack

# Bob stops following
python pz_client.py act Bob stop
```

## Running headless (LLM agent)

The `pz_client.py` client is designed to be called from any Python agent or script. Every command returns JSON, so you can integrate it with any workflow:

```python
from pz_client import PZBridgeClient

bridge = PZBridgeClient()
snap = bridge.snapshot()
if snap.get("zombieCount", 0) > 5:
    bridge.act("Bob", "set_state", {"state": "fleeing"})
    bridge.act("Bob", "walk_to", {"x": snap["x"] + 20, "y": snap["y"] + 20, "z": 0})
```

## Troubleshooting

- **"Connection refused"** — PZ isn't running, or the mod isn't loaded, or the world hasn't started yet
- **Port 8742 already in use** — kill the old process or change the port in `BridgeMod.lua` (line: `PZBridge.port = 8742`)
- **NPC spawn fails** — try a different location; the coordinates must be within a loaded chunk
- **"Invalid JSON"** — make sure you're sending valid JSON with proper escaping