"""Miki — PZ NPC character spawner.

Spawns Miki into Project Zomboid with her full personality, traits,
inventory, and vitals. Requires the PZBridge mod running in-game.

Usage:
    python pz_spawn_miki.py                          # spawn at default coords
    python pz_spawn_miki.py 11000 9000 0             # spawn at specific coords
    python pz_spawn_miki.py --brain                  # also start her LLM brain
    python pz_spawn_miki.py --brain --model claude-opus  # with custom LLM
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pz_client import PZBridgeClient
import json
import time

MIKI_PROFILE = {
    "name": "Miki",
    "personality": "Miki is a scavenger, a survivor, and a chaos magnet. Quick to laugh, faster to bolt, and surprisingly loyal once you've earned it. She grew up in the ruins of Louisville and learned that the dead aren't the worst thing out there — people are. She hoards lighters, smokes when she can find them, and has a nervous habit of touching her bandana whenever she's lying. She's not a hero and she'll be the first to tell you, but she'll also be the last one to leave if you're hers.",
    "traits": ["keen_hearing", "fast_reader", "dextrous", "light_eater", "cat_eyes", "outdoorsy"],
    "vitals": {"hp": 100, "max_hp": 100, "hunger": 50, "thirst": 40, "fatigue": 15, "stress": 45, "morale": 60, "endurance": 0.85},
    "inventory": [
        "Hunting Knife", "Lighter", "Cigarettes (Partial)", "Water Bottle",
        "Can of Beans", "Worn Leather Jacket", "Red Bandana", "Combat Boots", "Backpack"
    ],
    "skin": "Base.SurvivorFemale",
    "npc_state": "idle"
}


def spawn_miki(bridge, x=0, y=0, z=0, with_brain=False, **brain_kwargs):
    print(f"🤖 Spawning Miki @ ({x}, {y}, {z}) ...")

    # 1. Spawn
    resp = bridge.spawn(MIKI_PROFILE["name"], x=x, y=y, z=z,
                        personality=MIKI_PROFILE["personality"],
                        traits=MIKI_PROFILE["traits"])
    print(f"   Spawn result: {json.dumps(resp)}")
    time.sleep(0.5)

    # 2. Set personality explicitly
    resp = bridge.act(MIKI_PROFILE["name"], "set_personality",
                       {"text": MIKI_PROFILE["personality"],
                        "traits": MIKI_PROFILE["traits"]})
    print(f"   Personality set: {json.dumps(resp)}")

    # 3. Set initial state
    resp = bridge.act(MIKI_PROFILE["name"], "set_state", {"state": MIKI_PROFILE["npc_state"]})
    print(f"   State set: {json.dumps(resp)}")

    # 4. Make her say hi
    resp = bridge.act(MIKI_PROFILE["name"], "say",
                       {"text": "... fresh air. okay. i'm up. what've we got?"})
    print(f"   Spawn greeting sent")

    print(f"\n✅ Miki is in the world at ({x}, {y}, {z})")

    if with_brain:
        print(f"\n🧠 Starting LLM brain for Miki...")
        from pz_brain import PZBrain
        brain = PZBrain(
            npc_name=MIKI_PROFILE["name"],
            personality=MIKI_PROFILE["personality"],
            traits=MIKI_PROFILE["traits"],
            bridge=bridge,
            model=brain_kwargs.get("model", "gpt-4o-mini"),
            base_url=brain_kwargs.get("base_url", brain_kwargs.get("local", "https://api.openai.com/v1")),
            think_interval=brain_kwargs.get("interval", 4.0)
        )
        brain.run_loop()

    return resp


def main():
    bridge = PZBridgeClient()
    x = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    y = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    z = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    with_brain = "--brain" in sys.argv

    brain_kwargs = {}
    if "--model" in sys.argv:
        idx = sys.argv.index("--model")
        brain_kwargs["model"] = sys.argv[idx + 1] if len(sys.argv) > idx + 1 else "gpt-4o-mini"
    if "--local" in sys.argv:
        idx = sys.argv.index("--local")
        brain_kwargs["local"] = sys.argv[idx + 1] if len(sys.argv) > idx + 1 else "http://localhost:1234/v1"

    spawn_miki(bridge, x, y, z, with_brain=with_brain, **brain_kwargs)


if __name__ == "__main__":
    main()