"""PZAdapter: lets viwo's character brain control NPCs in Project Zomboid.

It bridges viwo's world model (Player / PlayerManager / NPCBehaviorSystem /
MemoryStore / Traits) onto a Project Zomboid server running the `pz_bridge`
Lua mod.  The game is the source of truth; viwo supplies cognition: memories,
personality, traits, decisions, and scripted/intent-based actions.

Usage:
    adapter = PZAdapter('http://localhost:8742')
    snap = adapter.snapshot()              # read world state
    adapter.act('survivor_1', 'move_to', {'x': 1200, 'y': 950})  # send command

The adapter is intentionally thin so it can be swapped into the existing viwo
`Engine` without rewriting the brain layer:
    - `get_zone()` replaces the room-graph area query.
    - `act(...)` is what NPCBehaviorSystem / the agent engine call instead of
      the local `movement.move_to_room()`.
    - `observe(...)` writes a memory entry for the character, so the brain
      layer stays identical whether the world is text or Zomboid.
"""
import json
import time
from typing import Any, Dict, List, Optional


class PZAdapter:
    """Thin REST client over the PZ Bridge mod."""

    def __init__(self, base_url: str = "http://127.0.0.1:8742", tick_seconds: float = 3.0):
        self.base_url = base_url.rstrip("/")
        # Use urllib only (no external deps) so this runs anywhere
        import urllib.request, urllib.error
        self._urllib = urllib.request
        self._urllib_error = urllib.error
        self.last_snapshot: Optional[Dict[str, Any]] = None
        self.tick_seconds = tick_seconds

    # ── HTTP helper ────────────────────────────────────────────────────
    def _request(self, path: str, body: Optional[dict] = None) -> Any:
        data = None
        headers = {}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = self._urllib.Request(f"{self.base_url}/{path}", data=data, headers=headers, method="GET" if body is None else "POST")
        try:
            with self._urllib.urlopen(req, timeout=5) as resp:
                raw = resp.read().decode("utf-8")
        except self._urllib_error.URLError as e:
            # Bridge unreachable -> caller decides; return a safe stub so viwo brains
            # can keep running (memory updates simply become no-ops until game reconnects).
            print(f"[PZAdapter] bridge unreachable: {e}")
            return {"status": "offline", "error": str(e)}
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"status": "error", "raw": raw}

    # ── World sensing ──────────────────────────────────────────────────
    def snapshot(self) -> Dict[str, Any]:
        """Fetch current world snapshot -> {'zone','player','x','y','z','items','zombieCount'}."""
        snap = self._request("snapshot")
        if isinstance(snap, dict) and snap.get("status") != "offline":
            self.last_snapshot = snap
        return snap or {}

    def zone_name(self) -> str:
        snap = self.last_snapshot or self.snapshot()
        return snap.get("zone") or snap.get("player", "unknown") or "unknown"

    def nearby_items(self) -> List[Dict[str, Any]]:
        snap = self.last_snapshot or self.snapshot()
        return snap.get("items", []) or []

    def nearby_zombies(self) -> int:
        snap = self.last_snapshot or self.snapshot()
        return int(snap.get("zombieCount", 0) or 0)

    # ── Acting (driving the NPC) ───────────────────────────────────────
    def act(self, npc_name: str, action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send an intent to the game for `npc_name`.

        action in {'move_to','say','attack','loot'}; params is the action payload.
        Mirrors what viwo's trigger `act` / `say` / `move` effects would normally do,
        but routed to Zomboid's actual NPC entities.
        """
        resp = self._request("act", {"npc": npc_name, "action": action, "params": params or {}})
        return resp or {"status": "offline"}

    # ── Memory integration ─────────────────────────────────────────────
    def observe(self, character_memory_store, npc_name: str, text: str,
                memory_type: str = "action", importance: int = 3) -> None:
        """Push a world observation into viwo's memory store.

        `character_memory_store` is the viwo MemoryStore for the NPC (or a
        wrapper exposing `add_memory(name, text, ...)`).  This keeps memory
        decay/personality filtering identical to the text-world behaviour.
        """
        # Snapshot first, so importance can be weighted on live data.
        snap = self.last_snapshot or self.snapshot()
        zcount = self.nearby_zombies()
        enriched = text
        if zcount > 0:
            enriched = f"{text} [zombies_nearby={zcount}]"
        try:
            character_memory_store.add_memory(npc_name, enriched, memory_type=memory_type, importance=importance)
        except Exception as e:
            print(f"[PZAdapter] could not write memory: {e}")

    # ── Tick loop integration ──────────────────────────────────────────
    def poll_and_update(self, character_memory_store, npc_name: str) -> Dict[str, Any]:
        """One tick of the bridge: refresh, log an observation, return the snapshot.

        Intended to be called from the viwo tick loop in place of (or alongside)
        `process_simple_npcs` — it lets a simple NPC react to real zombie presence.
        """
        snap = self.snapshot()
        zcount = self.nearby_zombies()
        if zcount > 0:
            self.observe(character_memory_store, npc_name, f"hostile presence felt ({zcount} zombies nearby)", importance=5)
        return snap


# Tiny demo harness ------------------------------------------------------
if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8742"
    br = PZAdapter(url)
    print("snapshot:", br.snapshot())
    print("zone:", br.zone_name())
    print("items:", br.nearby_items())
    print("zombies:", br.nearby_zombies())
    print("act move_to:", br.act("demo_npc", "move_to", {"x": 0, "y": 0}))
    print("act say:", br.act("demo_npc", "say", {"text": "hello from viwo"}))
    print("act attack:", br.act("demo_npc", "attack", {"target_type": "zombie", "target_name": ""}))
