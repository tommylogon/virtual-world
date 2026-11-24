"""System prompt and JSON example builder for Python agent turns (task-1002)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

JSON_FIELDS: Dict[str, str] = {
    "inner_monologue": '"inner_monologue":"..."',
    "action_use_on": '"action":"use_on","item":"...","target":"..."',
    "speech": '"speech":"..."',
    "volume": '"volume":"say"',
    "tone": '"tone":"normal"',
    "emote": '"emote":"..."',
    "learned_names": '"learned_names":[]',
}

EMOTE_RULES = (
    'Write emotes as bare THIRD-person action phrases (e.g. "leans in close", '
    '"bites their lip", "glances at the door") - the narrator adds the character\'s name; '
    'never "you"/"your"/"I"/"my" and never your own character name. '
    'Use singular -s actions ("hugs", "leans", "sinks") and neutral pronouns (their/them/themselves).'
)

SPEECH_RULES = (
    "=== SPEECH, VOLUME & TONE ===\n"
    'Put speech in the "speech" field and volume in the "volume" field - '
    "whisper | say | sing | shout | scream (default say). The volume word is the KEY name, never part of the speech text.\n"
    'DELIVERY TONE: use "tone": "normal" for ordinary speech, or '
    '"warm|teasing|sarcastic|cold|hostile|serious|apologetic|guarded" when not plain. '
    "Tone is how you TRY to deliver the line; "
    "listeners perceive it subjectively through their own mood and your body language.\n"
    'DIRECTED WHISPER: add "target":"<character name>" for a private aside - only that character hears it.\n'
    'For a speech-only turn, omit "action". If you say nothing, set "speech": null. '
    'To do nothing, respond {"action":"wait"}.'
)

JSON_RULES = (
    "=== JSON RULES ===\n"
    '- One comma between every field: {"inner_monologue":"...","action":"wait"}\n'
    '- Never repeat keys; use null or "" for unused fields ("speech": null, "emote": null)\n'
    '- Never add fields that are not in the schema (no "stats", no "inventory", no "memory", no "emotion")'
)


def build_json_example(field_keys: List[str]) -> str:
    pairs = [JSON_FIELDS[k] for k in field_keys if k in JSON_FIELDS]
    lines = [f"    {p}{',' if i < len(pairs) - 1 else ''}" for i, p in enumerate(pairs)]
    return "{\n" + "\n".join(lines) + "\n}"


def build_system_prompt(world: Any = None, *, react_mode: bool = False) -> str:
    """Build the standing system prompt for think-decide or react phase."""
    blocks: List[str] = []

    # Optional world lore
    lore_lines: List[str] = []
    if world is not None:
        lore = getattr(world, "lore", None) or getattr(world, "world_lore", None)
        if isinstance(lore, list):
            for entry in lore[:12]:
                if isinstance(entry, dict) and entry.get("content"):
                    cat = entry.get("category") or "general"
                    title = entry.get("title") or entry.get("key") or ""
                    lore_lines.append(f"[{cat}] {title}: {entry['content']}")
    if lore_lines:
        blocks.append("=== WORLD LORE ===\n" + "\n".join(lore_lines))

    if react_mode:
        blocks.append(
            "=== REACT MODE ===\n"
            "This is the instant after your own action resolved. You cannot take new actions in this phase - "
            "respond only with inner_monologue, speech (rarely), volume, tone, emote, and learned_names.\n"
            "React only to what just changed or surprised you. Leave \"speech\": null unless the result "
            "gives you something genuinely new to say - never repeat or paraphrase a line you already spoke.\n"
            + EMOTE_RULES
        )
    else:
        blocks.append(
            "=== ACTIONS ===\n"
            "Emit ONE action per response as a structured JSON object:\n"
            '- "action": a single action word (go, dash, approach, crawl, climb, take, drop, use, use_on, '
            "eat, drink, examine, open, close, attack, grab, wait, rest, put, give, search, look, inventory, stats, ...).\n"
            '- "item" and "target": the full multi-word name of what you act on, never truncated.\n'
            '- If you wait, listen, or hold still, use "action": "wait".\n'
            + EMOTE_RULES
        )

    blocks.append(SPEECH_RULES)
    blocks.append(JSON_RULES)
    blocks.append(
        "=== RESPONSE LENGTH ===\n"
        "Keep your response under 1000 tokens. Be concise - inner monologue, speech, and action should be brief and natural."
    )
    return "\n\n".join(blocks)
