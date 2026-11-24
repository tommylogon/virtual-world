"""Turn-level prompt assembly (think-decide & result-reaction) (task-1002)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from engine.agent.prompt_builder.character_state import build_character_state
from engine.agent.prompt_builder.room_context import build_room_context, build_room_events_block
from engine.agent.prompt_builder.system_prompt import build_json_example, build_system_prompt


def _resolve_ap(player: Any, action_points: Optional[Dict[str, int]]) -> Dict[str, int]:
    from engine import action_tiers

    if isinstance(action_points, dict) and action_points:
        return action_points
    live = getattr(player, "action_points", None)
    if isinstance(live, dict) and live:
        return live
    return dict(action_tiers.DEFAULT_BUDGET)


def _build_available_actions_block(action_points: Optional[Dict[str, int]] = None) -> str:
    """Budget-aware available actions summary."""
    major = int((action_points or {}).get("major", 0))
    minor = int((action_points or {}).get("minor", 0))
    lines = ["=== AVAILABLE ACTIONS ==="]
    if major > 0:
        lines.append("Major: go, dash, approach, examine, search, take, use, use_on, eat, drink, open, close, put, give, steal, attack, grab")
    if minor > 0:
        lines.append("Minor: wear, remove, stow, drop, stand, sit, lie")
    lines.append("Free: look, inventory, stats, plan <intent>, wait (plus speech/emote)")
    if major <= 0 and minor <= 0:
        lines.append("(Major and minor action points exhausted this turn. Only free actions, speech, or wait remain.)")
    elif major <= 0:
        lines.append("(Major action points exhausted this turn - do NOT use examine, go, use, use_on, take, eat, or drink. Choose a minor/free action, speak, or wait.)")
    return "\n".join(lines)


def _build_plan_block(player: Any, plan_steps: Optional[List[str]] = None) -> str:
    steps = list(plan_steps or [])
    if not steps:
        pursuit = getattr(player, "active_pursuit", None)
        if isinstance(pursuit, dict) and pursuit.get("steps"):
            steps = [str(s) for s in pursuit["steps"] if s]
        elif isinstance(pursuit, list):
            steps = [str(s) for s in pursuit if s]
    if steps:
        numbered = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps))
        return f"=== YOUR PLAN ===\n{numbered}"
    return "=== YOUR PLAN ===\n(No active plan - use free action `plan <intent>` to form a grounded multi-step plan, or act directly.)"


_INTERNAL_MEM_PREFIXES = ("Observed ", "Secret fact:", "Deepest secret:", "Current situation:", "You have seen ")


def _build_memory_block(player: Any, memory_thought: str) -> str:
    mem_clean = (memory_thought or "").strip()
    if mem_clean and "You don't remember anything relevant right now." not in mem_clean:
        if mem_clean.startswith("=== I REMEMBER") or "=== I REMEMBER" in mem_clean:
            return mem_clean
        return f"=== I REMEMBER (CONSCIOUS THOUGHT) ===\n{mem_clean}"
    # Fallback: pull up to 2 distinct, non-internal recent memories from Player
    # (skipping snake_case metadata and near-duplicate inner_monologue echoes).
    raw_mems = list(getattr(player, "memories", None) or [])
    snippets: List[str] = []
    seen_heads: set = set()
    for m in reversed(raw_mems[-12:]):
        txt = str(getattr(m, "text", None) or (m.get("text") if isinstance(m, dict) else "")).strip()
        if not txt or txt.startswith(_INTERNAL_MEM_PREFIXES):
            continue
        head = txt[:60].lower()
        if head in seen_heads:
            continue
        seen_heads.add(head)
        snippets.append(txt)
        if len(snippets) >= 2:
            break
    if snippets:
        return "=== I REMEMBER (CONSCIOUS THOUGHT) ===\n" + "\n".join(f"- {s}" for s in snippets)
    return "=== I REMEMBER (CONSCIOUS THOUGHT) ===\nNothing specific comes to mind right now."


_DRINK_WORDS = ("water", "bottle", "drink", "flask", "tea", "coffee", "juice", "soda", "canteen", "wine", "ale", "beer", "milk", "monster", "potion")
_EAT_WORDS = ("bar", "food", "bread", "apple", "ration", "snack", "jerky", "sandwich", "meat", "fruit", "cake", "cookie", "soup", "stew", "cheese", "meal", "granola", "protein")


def _carried_names(world: Any, player: Any) -> List[str]:
    graph = getattr(world, "graph", None)
    if graph is None:
        return []
    pname = str(getattr(player, "name", "") or "").lower()
    pid_us = f"player_{pname.replace(' ', '_')}"
    pid_sp = f"player_{pname}"
    p_ids = {pname, pid_us, pid_sp}
    nodes = getattr(graph, "nodes", None) or {}
    get_node = graph.get_node if hasattr(graph, "get_node") else nodes.get
    out: List[str] = []
    for edge in list(getattr(graph, "edges", None) or []):
        rel = str(getattr(edge, "relation", None) or getattr(edge, "type", None) or "").lower()
        if rel != "carrying":
            continue
        src = str(getattr(edge, "source", "") or "")
        tgt = str(getattr(edge, "target", "") or "")
        item_id = tgt if src.lower() in p_ids else (src if tgt.lower() in p_ids else None)
        if not item_id:
            continue
        inode = get_node(item_id)
        if inode is not None:
            out.append(str(getattr(inode, "name", None) or item_id))
    return out


def _build_smart_action_snippet(
    world: Any,
    player: Any,
    ap: Dict[str, int],
    *,
    plan_steps: Optional[List[str]] = None,
) -> str:
    """Pick an affordable, highest-priority example action based on live state + AP."""
    major = int(ap.get("major", 0))
    minor = int(ap.get("minor", 0))
    if major <= 0:
        if not plan_steps:
            return '"action":"plan","item":null,"target":null'
        if minor > 0:
            return '"action":"wait","item":null,"target":null'
        return '"action":"wait","item":null,"target":null'

    thirst = float(getattr(player, "thirst", 0) or 0)
    hunger = float(getattr(player, "hunger", 0) or 0)
    energy = float(getattr(player, "energy", 100) or 100)
    carried = _carried_names(world, player)

    if thirst >= 70:
        for item in carried:
            if any(w in item.lower() for w in _DRINK_WORDS):
                return f'"action":"drink","item":"{item}","target":null'
    if hunger >= 70:
        for item in carried:
            if any(w in item.lower() for w in _EAT_WORDS):
                return f'"action":"eat","item":"{item}","target":null'
    if energy <= 25:
        return '"action":"rest","item":null,"target":null'
    return '"action":"examine","item":"...","target":null'


def build_think_decide_messages(
    world: Any,
    player_name: str,
    *,
    last_result: str = "",
    memory_thought: str = "",
    action_points: Optional[Dict[str, int]] = None,
    plan_steps: Optional[List[str]] = None,
    recent_speech: Optional[List[str]] = None,
) -> List[Dict[str, str]]:
    """Build [system, user] messages for a character's think-decide turn."""
    player = world.players[player_name]
    tick = int(getattr(world, "time_ticks", 0) or 0)
    persona = getattr(player, "personality", "") or ""
    persona_line = f"You are {player.name}. Personality: {persona}" if persona else f"You are {player.name}."
    appearance = str(getattr(player, "appearance", None) or getattr(player, "description", None) or "").strip()
    if appearance:
        persona_line += f"\nYour appearance: {appearance}"

    ap = _resolve_ap(player, action_points)
    state_block = build_character_state(player, world=world, action_points=ap)
    room_block = build_room_context(world, player, action_points=ap, include_witnessed=False)
    mem_block = _build_memory_block(player, memory_thought)
    events_block = build_room_events_block(world, player, last_result=last_result)
    actions_block = _build_available_actions_block(ap)
    plan_block = _build_plan_block(player, plan_steps=plan_steps)

    conv_block = ""
    if recent_speech:
        quoted = "; ".join(f'"{s}"' for s in recent_speech[-4:] if s)
        if quoted:
            conv_block = f"=== CONVERSATION ===\nYou recently said: {quoted}\nDo not repeat a line you already said."

    action_snippet = _build_smart_action_snippet(world, player, ap, plan_steps=plan_steps)
    schema_example = build_json_example(
        ["inner_monologue", "action_use_on", "speech", "volume", "tone", "emote", "learned_names"]
    ).replace('"action":"use_on","item":"...","target":"..."', action_snippet)
    sections = [
        f"[Tick {tick}]",
        persona_line,
        state_block,
        room_block,
        mem_block,
        events_block,
    ]
    if conv_block:
        sections.append(conv_block)
    sections.append(actions_block)
    sections.append(plan_block)
    sections.append(f"Respond with ONLY a single raw JSON object matching this schema:\n{schema_example}")
    user_msg = "\n\n".join(sections)
    return [
        {"role": "system", "content": build_system_prompt(world, react_mode=False)},
        {"role": "user", "content": user_msg},
    ]


def build_result_reaction_messages(
    world: Any,
    player_name: str,
    *,
    what_happened: str = "",
    memory_thought: str = "",
    action_points: Optional[Dict[str, int]] = None,
    said_this_turn: str = "",
) -> List[Dict[str, str]]:
    """Build [system, user] messages for a character's post-action react phase."""
    player = world.players[player_name]
    persona = getattr(player, "personality", "") or ""
    persona_line = f"You are {player.name}. Personality: {persona}" if persona else f"You are {player.name}."

    ap = _resolve_ap(player, action_points)
    state_block = build_character_state(player, world=world, action_points=ap)
    room_block = build_room_context(world, player, action_points=ap, include_witnessed=False)
    mem_block = _build_memory_block(player, memory_thought)
    events_block = build_room_events_block(world, player, last_result=what_happened)

    schema_example = build_json_example(
        ["inner_monologue", "speech", "volume", "tone", "emote", "learned_names"]
    ).replace('"speech":"..."', '"speech":null')
    parts = [persona_line, state_block, room_block]
    if mem_block:
        parts.append(mem_block)
    parts.append(events_block)
    if said_this_turn and str(said_this_turn).strip():
        parts.append(f'You already said this turn: "{str(said_this_turn).strip()}"')
    parts.append(
        "React to what just happened. Do NOT include action/item fields.\n"
        f"Respond with ONLY a single raw JSON object:\n{schema_example}"
    )
    return [
        {"role": "system", "content": build_system_prompt(world, react_mode=True)},
        {"role": "user", "content": "\n\n".join(parts)},
    ]
