"""PZ Bridge Client — standalone NPC driver for Project Zomboid

Connects to PZBridge mod running at http://127.0.0.1:8742
and lets you spawn, control, and query NPCs in real-time.

Usage:
  python pz_client.py                           # interactive shell
  python pz_client.py snapshot                  # one-shot snapshot
  python pz_client.py spawn Bob 11000 9000 0    # spawn NPC at coords
  python pz_client.py act Bob say "hello"       # make NPC speak
  python pz_client.py act Bob follow            # follow player
  python pz_client.py act Bob move_to 11050 9050 0  # teleport NPC
  python pz_client.py act Bob walk_to 11050 9050 0  # pathfind NPC
  python pz_client.py act Bob attack            # attack nearest zombie
  python pz_client.py act Bob set_state fleeing # change NPC state
  python pz_client.py act Bob stop              # stop following
  python pz_client.py act Bob set_personality "friendly doc"  # set personality
  python pz_client.py npcs                      # list all NPCs
  python pz_client.py npc-sheet Bob             # full character sheet (vitals+inventory+personality)
  python pz_client.py zone                      # get current zone info
"""
import json
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import URLError


class PZBridgeClient:
    def __init__(self, base_url="http://127.0.0.1:8742"):
        self.base_url = base_url.rstrip("/")

    def _request(self, path, body=None, method="GET"):
        data = None
        headers = {"Content-Type": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            method = "POST"
        req = Request(f"{self.base_url}/{path}", data=data, headers=headers, method=method)
        try:
            with urlopen(req, timeout=5) as resp:
                raw = resp.read().decode("utf-8")
        except URLError as e:
            return {"status": "offline", "error": str(e)}
        except ConnectionRefusedError:
            return {"status": "offline", "error": "Connection refused — is PZ running with PZBridge mod?"}
        if not raw:
            return {"status": "error", "message": "Empty response"}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"status": "error", "raw": raw}

    def snapshot(self):
        return self._request("snapshot")

    def spawn_npc(self, name, x=0, y=0, z=0, skin="Base.SurvivorMale", personality="", traits=None):
        body = {"name": name, "skin": skin, "x": x, "y": y, "z": z}
        if personality:
            body["personality"] = personality
        if traits:
            body["traits"] = traits
        return self._request("npc", body)

    def npc_sheet(self, name):
        return self._request("npc/" + name)

    def list_npcs(self):
        return self._request("npc")

    def act(self, npc_name, action, params=None):
        return self._request("act", {"npc": npc_name, "action": action, "params": params or {}})

    def zone(self):
        return self._request("zone")

    def pretty_print(self, data, indent=2):
        print(json.dumps(data, indent=indent, default=str))


def demo_snapshot(client):
    """Fetch and display a world snapshot."""
    snap = client.snapshot()
    if snap.get("status") == "offline":
        print(f"❌ Bridge offline: {snap.get('error')}")
        return False
    player = snap.get("player", "?")
    x, y, z = snap.get("x"), snap.get("y"), snap.get("z")
    zone = snap.get("zone", "?")
    zombies = snap.get("zombieCount", 0)
    npcs = snap.get("npcs", [])
    time_info = snap.get("time", {})
    weather = snap.get("weather", {})
    print(f"📍 Player: {player}")
    print(f"   Position: ({x}, {y}, {z})")
    print(f"   Zone: {zone}")
    print(f"   Zombies nearby: {zombies}")
    print(f"   Time: {time_info.get('hour')}:{time_info.get('minute'):02d} Day {time_info.get('day')}")
    print(f"   Weather: {weather.get('temperature')}°C {'☔' if weather.get('raining') else '☀️'}")
    if npcs:
        print(f"   NPCs ({len(npcs)}):")
        for n in npcs:
            print(f"     - {n['name']} @ ({n['x']},{n['y']},{n['z']}) [{n.get('npc_state','?')}]")
    items = snap.get("items", [])
    if items:
        print(f"   Items nearby ({len(items)}):")
        for item in items[:5]:
            print(f"     - {item.get('name')}")
        if len(items) > 5:
            print(f"     ... and {len(items) - 5} more")
    return True


def demo_spawn_and_control(client):
    """Spawn an NPC, move it, talk, then list it."""
    name = "TestBot"
    print(f"\n🤖 Spawning NPC '{name}'...")
    resp = client.spawn_npc(name, x=0, y=0, z=0)
    print(f"   {json.dumps(resp)}")
    if resp.get("status") != "ok":
        print(f"   (may already exist — continuing)")
    print(f"🗣️  Making '{name}' speak...")
    resp = client.act(name, "say", {"text": "Hello from the PZ Bridge! I am alive."})
    print(f"   {json.dumps(resp)}")
    print(f"📍 Moving '{name}'...")
    resp = client.act(name, "move_to", {"x": 5, "y": 5, "z": 0})
    print(f"   {json.dumps(resp)}")
    print(f"📋 Listing NPCs...")
    resp = client.list_npcs()
    print(f"   {json.dumps(resp, indent=2, default=str)}")


def main():
    url = "http://127.0.0.1:8742"
    client = PZBridgeClient(url)

    if len(sys.argv) < 2:
        print("PZBridge Client — interactive demo")
        print("=" * 50)
        print(f"Connecting to {url} ...")
        # Try snapshot first
        if not demo_snapshot(client):
            print("\n⚠️  Bridge is not reachable. Make sure PZ is running with PZBridge mod enabled.")
            print("   The mod starts automatically when the game world loads.\n")
        else:
            demo_spawn_and_control(client)
        print("\nDone. Run with commands: python pz_client.py <command> [args]")
        print("  snapshot  — world state")
        print("  spawn     — spawn NPC: python pz_client.py spawn Name x y z")
        print("  act       — act: python pz_client.py act Name action [params...]")
        print("  npcs      — list NPCs")
        print("  npc-sheet — full character sheet: python pz_client.py npc-sheet Name")
        print("  zone      — zone info")
        return

    cmd = sys.argv[1]
    if cmd == "snapshot":
        snap = client.snapshot()
        client.pretty_print(snap)
    elif cmd == "spawn":
        name = sys.argv[2] if len(sys.argv) > 2 else "Survivor"
        x = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        y = int(sys.argv[4]) if len(sys.argv) > 4 else 0
        z = int(sys.argv[5]) if len(sys.argv) > 5 else 0
        skin = sys.argv[6] if len(sys.argv) > 6 else "Base.SurvivorMale"
        personality = sys.argv[7] if len(sys.argv) > 7 else ""
        traits = None
        if len(sys.argv) > 8:
            traits = sys.argv[8].split(",")
        resp = client.spawn_npc(name, x, y, z, skin, personality, traits)
        client.pretty_print(resp)
    elif cmd == "act":
        name = sys.argv[2] if len(sys.argv) > 2 else "Survivor"
        action = sys.argv[3] if len(sys.argv) > 3 else "say"
        params = {}
        if action == "move_to" or action == "walk_to":
            params = {"x": int(sys.argv[4]) if len(sys.argv) > 4 else 0,
                      "y": int(sys.argv[5]) if len(sys.argv) > 5 else 0,
                      "z": int(sys.argv[6]) if len(sys.argv) > 6 else 0}
        elif action == "say":
            params = {"text": " ".join(sys.argv[4:]) if len(sys.argv) > 4 else "Hello!"}
        elif action == "set_state":
            params = {"state": sys.argv[4] if len(sys.argv) > 4 else "idle"}
        elif action == "follow":
            params = {"target": sys.argv[4] if len(sys.argv) > 4 else ""}
        elif action == "attack":
            params = {"target_type": sys.argv[4] if len(sys.argv) > 4 else "zombie"}
        elif action == "loot":
            params = {"item": sys.argv[4] if len(sys.argv) > 4 else ""}
        elif action == "set_personality":
            params = {"text": " ".join(sys.argv[4:]) if len(sys.argv) > 4 else ""}
        resp = client.act(name, action, params)
        client.pretty_print(resp)
    elif cmd == "npcs":
        resp = client.list_npcs()
        client.pretty_print(resp)
    elif cmd == "zone":
        resp = client.zone()
        client.pretty_print(resp)
    elif cmd == "npc-sheet" or cmd == "npc_sheet":
        name = sys.argv[2] if len(sys.argv) > 2 else "Survivor"
        resp = client.npc_sheet(name)
        client.pretty_print(resp)
    else:
        print(f"Unknown command: {cmd}")
        print("Commands: snapshot, spawn, act, npcs, zone")


if __name__ == "__main__":
    main()