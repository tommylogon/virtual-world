"""PZ Brain — LLM-driven NPC autonomously controlling a Project Zomboid survivor.

This is the "agent brain." It:
  - Polls the PZBridge mod every few seconds for world state + NPC vitals + inventory
  - Maintains per-NPC personality, traits, memories, and goals (in a Python dict)
  - Submits the full scenario to an LLM: "You are [personality]. Your vitals: [...]. Your
    inventory: [...]. Zombies nearby: N. Time: [...]. What do you do?"
  - Sends the LLM's chosen action back to the bridge via /act
  - Stores the action + outcome as a memory for the NPC's next decision

Requires: openai>=1.0 (or any OpenAI-compatible API). Also works with local LLMs
(LM Studio, Ollama, text-gen-webui) by changing the base_url.

Usage:
  python pz_brain.py                          # single NPC with default personality
  python pz_brain.py --npc "Bob"              # control NPC named Bob
  python pz_brain.py --personality "paranoid scavenger"  # set NPC personality
  python pz_brain.py --interval 5              # think every 5 seconds
  python pz_brain.py --model gpt-4o-mini       # use a specific model
  python pz_brain.py --local http://localhost:1234/v1  # use local LLM
  python pz_brain.py --once                    # one decision only, no loop
  python pz_brain.py --spawn "Bob"             # spawn + control
"""
import argparse
import json
import time
import sys
import os
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError

# ─── Bridge client ─────────────────────────────────────────────────────
class BridgeClient:
    def __init__(self, base="http://127.0.0.1:8742"):
        self.base = base.rstrip("/")
    def _req(self, path, body=None):
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
        req = Request(f"{self.base}/{path}", data=data, headers={"Content-Type": "application/json"},
                       method="POST" if body else "GET")
        try:
            with urlopen(req, timeout=5) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            return {"status": "offline", "error": str(e)}
    def snapshot(self): return self._req("snapshot")
    def npc_sheet(self, name): return self._req("npc/" + name)
    def act(self, npc, action, params=None): return self._req("act", {"npc": npc, "action": action, "params": params or {}})
    def spawn(self, name, x=0, y=0, z=0, personality="", traits=None):
        return self._req("npc", {"name": name, "x": x, "y": y, "z": z, "personality": personality, "traits": traits or []})
    def list_npcs(self): return self._req("npc")

# ─── LLM caller (OpenAI API compatible) ────────────────────────────────
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_BASE = "https://api.openai.com/v1"

def call_llm(prompt: str, system: str = "", model: str = DEFAULT_MODEL,
             base_url: str = DEFAULT_BASE, api_key: Optional[str] = None,
             temperature: float = 0.7) -> str:
    """Call an OpenAI-compatible LLM. Returns text completion."""
    import openai  # lazy import
    client = openai.OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY", "sk-none"),
                           base_url=base_url)
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = client.chat.completions.create(model=model, messages=messages,
                                           temperature=temperature)
    return resp.choices[0].message.content or ""

# ─── Memory ────────────────────────────────────────────────────────────
class NPCMemory:
    """Simple episodic memory per NPC. Holds recent events and reflections."""
    def __init__(self, max_entries=20):
        self.max = max_entries
        self.entries = []  # list of (tick, text)
    def add(self, tick, text):
        self.entries.append((tick, text))
        if len(self.entries) > self.max:
            self.entries.pop(0)
    def recent(self, n=5):
        return [e[1] for e in self.entries[-n:]]
    def summarize(self):
        if not self.entries:
            return "No recent memories."
        return "; ".join(self.recent(8))

# ─── System prompt template ────────────────────────────────────────────
SYSTEM_PROMPT = """You are an NPC survivor in Project Zomboid. You have a personality, a body with vitals, an inventory, and a goal: survive.

Rules:
1. Choose ONE action per turn from: move_to (x,y,z), walk_to (x,y,z), say (text), attack (target_type="zombie"), loot (item), set_state (state), follow (target), set_personality (text,traits), stop
2. Always respond in valid JSON: {"action":"...", "params":{...}, "reasoning":"one sentence explaining your choice"}
3. Consider your vitals (hunger, thirst, fatigue, stress) and act urgently when they're critical (over 80)
4. Consider your current inventory and what you need
5. Consider zombies nearby when deciding where to go
6. Stay in character based on your personality and mood
7. You can speak to other characters by saying things
8. When in danger, running away (walk_to away from zombies) or attacking are both valid
9. If you're starving or dying of thirst, prioritize looting nearby buildings for food/water
10. If it's nighttime and you're tired, find a safe place to rest (set_state sleeping)
"""

# ─── Brain class ───────────────────────────────────────────────────────
class PZBrain:
    """Autonomous NPC brain for a Project Zomboid survivor."""

    def __init__(self, npc_name: str, personality: str, traits: list,
                 bridge: BridgeClient, model: str = DEFAULT_MODEL,
                 base_url: str = DEFAULT_BASE, api_key: Optional[str] = None,
                 think_interval: float = 4.0):
        self.name = npc_name
        self.personality = personality
        self.traits = traits
        self.bridge = bridge
        self.model = model
        self.base_url = base_url
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.interval = think_interval
        self.memory = NPCMemory()
        self._tick = 0

    def think(self) -> str:
        """One decision cycle: read state -> LLM -> act. Returns the chosen action."""
        self._tick += 1
        # 1. Read state
        snap = self.bridge.snapshot()
        if snap.get("status") == "offline":
            return "OFFLINE: cannot reach bridge"
        sheet = self.bridge.npc_sheet(self.name)
        if sheet.get("status") == "offline" or sheet.get("status") == "error":
            return f"ERROR: {sheet.get('message', 'NPC sheet unavailable')}"

        # 2. Build prompt
        vit = sheet.get("vitals", {})
        inv = sheet.get("inventory", [])
        inv_str = ", ".join([f"{i.get('name','?')} (x{i.get('count',1)})" for i in inv]) if inv else "nothing"
        memories = self.memory.summarize()
        time_info = snap.get("time", {})
        weather = snap.get("weather", {})
        player_name = snap.get("player", "unknown")
        player_vit = snap.get("playerVitals", {})

        prompt = f"""[CURRENT STATE]
Location: ({sheet.get('x')}, {sheet.get('y')}, {sheet.get('z')})
Zone: {snap.get('zone', 'unknown')}
Time: {time_info.get('hour','?')}:{time_info.get('minute','00'):02d} Day {time_info.get('day','?')}
Weather: {weather.get('temperature','?')}°C {'Raining' if weather.get('raining') else 'Clear'}
Zombies nearby: {snap.get('zombieCount', 0)}
Player nearby: {player_name} @ ({snap.get('x')}, {snap.get('y')}, {snap.get('z')})

[YOUR VITALS]
HP: {vit.get('hp','?')}/{vit.get('max_hp','?')}
Hunger: {vit.get('hunger','?'):.0f}/100 (critical if >80)
Thirst: {vit.get('thirst','?'):.0f}/100 (critical if >80)
Fatigue: {vit.get('fatigue','?'):.0f}/100 (critical if >80)
Stress: {vit.get('stress','?'):.0f}/100
Morale: {vit.get('morale','?'):.0f}/100
Pain: {vit.get('pain',0)}
Bleeding: {'YES' if vit.get('bleeding',0) > 0 else 'No'}

[YOUR INVENTORY]
{inv_str}

[YOUR PERSONALITY]
{self.personality}

[YOUR TRAITS]
{', '.join(self.traits) if self.traits else 'none'}

[RECENT MEMORIES]
{memories}

[YOUR STATE]
Current NPC state: {sheet.get('npc_state', 'idle')}

What do you do? Return valid JSON with action, params, and reasoning."""

        # 3. Call LLM
        try:
            raw = call_llm(prompt, system=SYSTEM_PROMPT, model=self.model,
                          base_url=self.base_url, api_key=self.api_key)
        except Exception as e:
            self.memory.add(self._tick, f"LLM error: {e}")
            return f"LLM_ERROR: {e}"

        # 4. Parse response
        decision = None
        # Try extracting JSON from the response (it might wrap in ```json or just be JSON)
        try:
            # Strip code fences if present
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
                cleaned = cleaned.rsplit("```", 1)[0].strip()
            decision = json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to find {...} block
            import re
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            if m:
                try:
                    decision = json.loads(m.group(0))
                except json.JSONDecodeError:
                    pass

        if not decision or not isinstance(decision, dict):
            self.memory.add(self._tick, f"Bad LLM response: {raw[:200]}")
            return "PARSE_ERROR"

        action = decision.get("action", "set_state")
        params = decision.get("params", {})
        reasoning = decision.get("reasoning", "")

        # 5. Execute via bridge
        result = self.bridge.act(self.name, action, params)
        self.memory.add(self._tick, f"{action}({params}): {result.get('status','?')} — {reasoning}")
        return f"{action} -> {result.get('status','?')} [{reasoning}]"

    def run_loop(self):
        """Run the think-act cycle indefinitely."""
        print(f"🧠 PZ Brain: {self.name} [{self.personality}]")
        print(f"   Model: {self.model} @ {self.base_url}")
        print(f"   Cycle interval: {self.interval}s")
        print(f"   Press Ctrl+C to stop.\n")
        while True:
            result = self.think()
            print(f"[{time.strftime('%H:%M:%S')}] {self.name}: {result}")
            if hasattr(result, 'startswith') and result.startswith("OFFLINE"):
                print("   ⚠ Bridge offline — waiting...")
                time.sleep(5)
                continue
            time.sleep(self.interval)


# ─── Main ──────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="PZ Brain — LLM-driven NPC")
    parser.add_argument("--npc", default="Aria", help="NPC name")
    parser.add_argument("--personality", default="A cautious but resourceful scavenger. Friendly but not naive — she knows the dead are everywhere and trust is earned slowly. She hoards medical supplies and always has an escape route planned.",
                        help="Personality description")
    parser.add_argument("--traits", nargs="*", default=["lucky", "keen_hearing", "organized", "fast_reader"],
                        help="Traits list")
    parser.add_argument("--interval", type=float, default=4.0, help="Think cycle interval (seconds)")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"LLM model ID (default: {DEFAULT_MODEL})")
    parser.add_argument("--base", default=DEFAULT_BASE, help=f"LLM API base URL (default: {DEFAULT_BASE})")
    parser.add_argument("--key", default=None, help="OpenAI API key (defaults to OPENAI_API_KEY env)")
    parser.add_argument("--local", default=None, help="Local LLM base URL (overrides --base)")
    parser.add_argument("--once", action="store_true", help="One decision only, no loop")
    parser.add_argument("--spawn", default=None, help="Spawn NPC with this name first")
    parser.add_argument("--spawn-x", type=int, default=0, help="Spawn x")
    parser.add_argument("--spawn-y", type=int, default=0, help="Spawn y")
    parser.add_argument("--spawn-z", type=int, default=0, help="Spawn z")
    args = parser.parse_args()

    bridge = BridgeClient()
    base_url = args.local or args.base

    # Optionally spawn
    npc_name = args.npc
    if args.spawn:
        npc_name = args.spawn
        print(f"🤖 Spawning '{npc_name}' @ ({args.spawn_x},{args.spawn_y},{args.spawn_z}) ...")
        result = bridge.spawn(npc_name, args.spawn_x, args.spawn_y, args.spawn_z,
                              personality=args.personality, traits=args.traits)
        print(f"   {json.dumps(result)}")
        time.sleep(0.5)

    brain = PZBrain(npc_name, args.personality, args.traits, bridge,
                    model=args.model, base_url=base_url, api_key=args.key,
                    think_interval=args.interval)

    if args.once:
        result = brain.think()
        print(result)
    else:
        brain.run_loop()


if __name__ == "__main__":
    main()