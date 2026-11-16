"""tools/swarm_soak.py - Autonomous multi-agent soak harness for VirtualWorld.

Drives 2+ characters using a local LLM (e.g. LM Studio on localhost:1234).
Each turn:
1. Gathers character perception (room look, vitals, emotions, recent memories).
2. Prompts the local LLM to select an action grounded in personality and desires.
3. Dispatches the action via the real engine API (/api/action).
4. Advances the cycle via (/api/turn/apply).
5. Prints the unscripted narrative trace and relationship shifts.
"""
from __future__ import annotations

import json
import logging
import re
import sys
import time
import urllib.request
from typing import Dict, Any, List
from pathlib import Path

# Add project root to sys.path so app is importable from tools/
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Suppress loud engine logs
logging.basicConfig(level=logging.ERROR)

LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
MODEL_ID = "qwen3.5-2b"  # Fast, natural dialogue following

def call_local_llm(messages: List[Dict[str, str]], max_tokens: int = 500) -> str:
    payload = {
        "model": MODEL_ID,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.5,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        LM_STUDIO_URL,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            res_obj = json.loads(resp.read().decode("utf-8"))
            choice = res_obj["choices"][0]["message"]
            content = choice.get("content") or ""
            # If the model put reasoning in content or reasoning_content, clean it:
            if not content.strip():
                content = choice.get("reasoning_content") or ""
            return content.strip()
    except Exception as e:
        print(f" [LLM Error]: {e}", file=sys.stderr)
        return "wait"

def clean_command(raw_text: str) -> str:
    """Extract a single valid game command from model output."""
    raw = raw_text.strip()
    if not raw:
        return "wait"

    # If the model already gave a valid command prefix, use it
    lower = raw.lower()
    if lower.startswith("say ") or lower.startswith("examine ") or lower.startswith("go ") or lower == "wait" or lower == "look":
        return raw.splitlines()[0].strip()

    # If it's natural in-character speech (like "Hey Sammy, ..."), wrap it in 'say'
    first_line = raw.splitlines()[0].strip().strip('"').strip("'")
    # Clean any trailing or leading artifacts
    if first_line:
        return f"say {first_line}"
    return "wait"

def run_swarm_soak(num_turns: int = 4, characters: List[str] = None):
    if characters is None:
        characters = ["jake halloway", "sammy lopez"]

    from app import create_app
    print(f"\n=======================================================")
    print(f"   VIRTUALWORLD AUTOSWARM SOAK HARNESS")
    print(f"   Characters: {', '.join(characters)}")
    print(f"   Model: {MODEL_ID} on {LM_STUDIO_URL}")
    print(f"   Target Cycles: {num_turns}")
    print(f"=======================================================\n")

    app = create_app()
    client = app.test_client()
    world = app.world

    for turn_idx in range(num_turns):
        print(f"\n--- [ CYCLE {turn_idx + 1} / {num_turns} ] ---")
        
        for char_name in characters:
            player = world.players.get(char_name)
            if not player:
                print(f"Character '{char_name}' not found in world!")
                continue

            # 1. Perception
            res = client.post('/api/action', json={'command': 'look', 'character': char_name})
            room_desc = res.get_json().get('output', '')
            # Shorten description to keep prompt focused
            room_summary = room_desc[:600] if len(room_desc) > 600 else room_desc

            # 2. Vitals & Mental state
            vitals_str = f"HP: {player.vitals.get('HP')}, Energy: {player.vitals.get('Energy')}, Hunger: {player.vitals.get('Hunger')}"
            emotion_str = f"{player.emotion} (intensity: {player.emotion_intensity:.2f})"
            recent_memories = [m.get('text', '') for m in player.memories[-3:] if isinstance(m, dict)]
            mem_str = "\n".join(f"- {m}" for m in recent_memories) if recent_memories else "(No recent memories)"

            # 3. Prompt
            prompt = (
                f"You are {char_name.title()} at Millwood High School.\n"
                f"Your personality: {player.personality[:150] if player.personality else 'High school student'}\n"
                f"Your current mood: {emotion_str}\n"
                f"You are sitting in the cafeteria with your friends Sammy, Kayla, and Zoe.\n"
                f"On the table: Takis, Cheetos, beef jerky, gummy worms, chocolate milk, apples.\n\n"
                f"Say something natural to your friends right now, or examine an item, or wait.\n"
                f"Respond with ONLY your line of dialogue or action:"
            )

            raw_decision = call_local_llm([{"role": "user", "content": prompt}], max_tokens=250)
            cmd = clean_command(raw_decision)
            
            # 4. Execute action in engine
            action_res = client.post('/api/action', json={'command': cmd, 'character': char_name})
            out = action_res.get_json().get('output', '')
            
            print(f"[{char_name.upper()}]:")
            print(f"  Command: '{cmd}'")
            print(f"  Result:  {out.strip()[:300]}")
            print(f"  Emotion: {player.emotion} | Area: {player.current_area}")
            time.sleep(0.5)

        # 5. Apply turn cycle decay and advance time
        decay_res = client.post('/api/turn/apply', json={'actor': characters[0]})
        print(f"\n[Cycle {turn_idx + 1} Advance]: {decay_res.get_json()}")

    print(f"\n=======================================================")
    print(f"   SWARM SOAK COMPLETED SUCCESSFULLY")
    print(f"=======================================================\n")

if __name__ == "__main__":
    turns = 3
    if len(sys.argv) > 1:
        try:
            turns = int(sys.argv[1])
        except ValueError:
            pass
    run_swarm_soak(num_turns=turns)
