"""Scoped registry and single source of truth for character actions (task-491, task-988).

Every action accepted by the game action API, agent action normalizer,
prompt builder, Human Turn buttons, or autocomplete is declared here once.
`tools/actions_index.py` emits the client-side mirror
(`static/js/agent/actions.generated.js`).

@module actions
@contributes ActionSpec, ACTIONS, all_actions, mature_actions, actions_for_scope, bracket_order, llm_manifest
@powers Use / use on - single source of truth for actions across client and engine
@relates engine/action_tiers.py, routes/action_handlers.py, static/js/agent/actions.generated.js
@docs docs/virtualWorld/AI & Narration/Agent Engine.md
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from engine.pleasure_actions import INTIMACY_ACTIONS


@dataclass(frozen=True)
class ActionSpec:
    id: str
    aliases: Tuple[str, ...] = ()
    scope: str = "general"
    target_schema: str = "none"
    cost_key: str = "major"
    mature_gate: bool = False
    bracket_order: Optional[int] = None

    @property
    def all_names(self) -> Tuple[str, ...]:
        return (self.id,) + self.aliases

    @property
    def scopes(self) -> Tuple[str, ...]:
        return tuple(s.strip() for s in self.scope.split(","))

    def has_scope(self, scope_name: str) -> bool:
        s = scope_name.lower().strip()
        return s in (x.lower() for x in self.scopes)


# Canonical display order for item action brackets in the prompt and UI.
BRACKET_ORDER_ACTIONS: Tuple[str, ...] = (
    "take",
    "use",
    "use_on",
    "open",
    "close",
    "eat",
    "drink",
    "read",
    "wear",
    "remove",
    "toggle",
    "drop",
    "examine",
)


ACTIONS: Tuple[ActionSpec, ...] = (
    # === MOVEMENT & PASSAGE ===
    ActionSpec("go", aliases=("walk", "move", "enter", "move_to", "moveto"), scope="way", target_schema="target", cost_key="major"),
    ActionSpec("dash", aliases=(), scope="way", target_schema="target", cost_key="major"),
    ActionSpec("crawl", aliases=(), scope="way", target_schema="target", cost_key="major"),
    ActionSpec("climb", aliases=(), scope="way", target_schema="target", cost_key="major"),
    ActionSpec("jump", aliases=(), scope="way", target_schema="target", cost_key="major"),
    ActionSpec("swim", aliases=(), scope="way", target_schema="target", cost_key="major"),
    ActionSpec("dive", aliases=(), scope="way", target_schema="target", cost_key="major"),
    ActionSpec("approach", aliases=(), scope="way", target_schema="target", cost_key="minor"),
    ActionSpec("mount", aliases=("ride",), scope="movement", target_schema="target", cost_key="minor"),
    ActionSpec("dismount", aliases=(), scope="movement", target_schema="none", cost_key="free"),
    ActionSpec("saddle", aliases=(), scope="movement,item", target_schema="target", cost_key="minor"),
    ActionSpec("escape", aliases=(), scope="movement", target_schema="none", cost_key="major"),
    ActionSpec("struggle", aliases=(), scope="movement", target_schema="none", cost_key="major"),
    ActionSpec("flee", aliases=("disengage", "withdraw"), scope="movement", target_schema="none", cost_key="minor"),
    ActionSpec("hide", aliases=("sneak", "conceal"), scope="movement,self", target_schema="target", cost_key="minor"),
    ActionSpec("unhide", aliases=("reveal",), scope="movement,self", target_schema="none", cost_key="free"),
    ActionSpec("stop", aliases=(), scope="movement", target_schema="none", cost_key="free"),

    # === ITEMS & CONTAINMENT ===
    ActionSpec("take", aliases=("get", "pickup", "pick", "snatch", "collect"), scope="item", target_schema="item", cost_key="major", bracket_order=0),
    ActionSpec("use", aliases=("use_on",), scope="item", target_schema="item_target", cost_key="major", bracket_order=1),
    ActionSpec("open", aliases=("unlock",), scope="item,way", target_schema="target", cost_key="free", bracket_order=3),
    ActionSpec("close", aliases=("lock",), scope="item,way", target_schema="target", cost_key="free", bracket_order=4),
    ActionSpec("eat", aliases=("consume",), scope="item", target_schema="item", cost_key="major", bracket_order=5),
    ActionSpec("drink", aliases=("quaff",), scope="item", target_schema="item", cost_key="major", bracket_order=6),
    ActionSpec("read", aliases=(), scope="item", target_schema="target", cost_key="major", bracket_order=7),
    ActionSpec("wear", aliases=("equip", "dress"), scope="item", target_schema="item", cost_key="minor", bracket_order=8),
    ActionSpec("remove", aliases=("unequip", "undress", "strip"), scope="item", target_schema="item", cost_key="minor", bracket_order=9),
    ActionSpec("toggle", aliases=("light", "ignite"), scope="item", target_schema="item", cost_key="minor", bracket_order=10),
    ActionSpec("drop", aliases=(), scope="item", target_schema="item", cost_key="free", bracket_order=11),
    ActionSpec("throw", aliases=("toss",), scope="item", target_schema="item_target", cost_key="major"),
    ActionSpec("put", aliases=("place", "stow"), scope="item", target_schema="item_target", cost_key="minor"),
    ActionSpec("combine", aliases=(), scope="item", target_schema="item", cost_key="major"),
    ActionSpec("split", aliases=(), scope="item", target_schema="item", cost_key="major"),
    ActionSpec("write", aliases=("inscribe",), scope="item", target_schema="item_target", cost_key="major"),
    ActionSpec("bind", aliases=("enchant",), scope="item", target_schema="trigger_bind", cost_key="major"),
    ActionSpec("fix", aliases=("treat",), scope="item", target_schema="item", cost_key="major"),

    # === PERCEPTION & INSPECTION ===
    ActionSpec("examine", aliases=("search", "inspect", "check", "x"), scope="perception,item", target_schema="target", cost_key="major", bracket_order=12),
    ActionSpec("look", aliases=("l",), scope="perception", target_schema="none", cost_key="free"),
    ActionSpec("listen", aliases=(), scope="perception", target_schema="none", cost_key="free"),
    ActionSpec("frisk", aliases=(), scope="perception", target_schema="target", cost_key="major"),

    # === SOCIAL & INTERACTION ===
    ActionSpec("speak", aliases=("say", "talk"), scope="social", target_schema="target", cost_key="free"),
    ActionSpec("whisper", aliases=(), scope="social", target_schema="target", cost_key="free"),
    ActionSpec("shout", aliases=("yell", "scream"), scope="social", target_schema="none", cost_key="free"),
    ActionSpec("sing", aliases=(), scope="social", target_schema="none", cost_key="free"),
    ActionSpec("call", aliases=(), scope="social", target_schema="target", cost_key="free"),
    ActionSpec("answer", aliases=(), scope="social", target_schema="none", cost_key="free"),
    ActionSpec("hangup", aliases=(), scope="social", target_schema="none", cost_key="free"),
    ActionSpec("text", aliases=("message",), scope="social", target_schema="target", cost_key="free"),
    ActionSpec("give", aliases=("hand",), scope="social", target_schema="item_target", cost_key="major"),
    ActionSpec("steal", aliases=(), scope="social", target_schema="item_target", cost_key="major"),
    ActionSpec("lead", aliases=(), scope="social", target_schema="target", cost_key="minor"),
    ActionSpec("teach", aliases=(), scope="social", target_schema="item_target", cost_key="major"),
    ActionSpec("wake", aliases=(), scope="social", target_schema="target", cost_key="minor"),
    ActionSpec("name", aliases=("label",), scope="social", target_schema="target", cost_key="free"),

    # === COMBAT ===
    ActionSpec("attack", aliases=("kill", "hit", "strike", "punch"), scope="combat", target_schema="target", cost_key="major"),
    ActionSpec("disarm", aliases=(), scope="combat", target_schema="target", cost_key="major"),
    ActionSpec("grab", aliases=(), scope="combat", target_schema="target", cost_key="minor"),
    ActionSpec("release", aliases=(), scope="combat", target_schema="target", cost_key="minor"),

    # === INTIMACY (MATURE GATE) ===
    ActionSpec("kiss", aliases=(), scope="intimacy", target_schema="intimacy", cost_key="major", mature_gate=True),
    ActionSpec("caress", aliases=(), scope="intimacy", target_schema="intimacy", cost_key="major", mature_gate=True),
    ActionSpec("lick", aliases=(), scope="intimacy", target_schema="intimacy", cost_key="major", mature_gate=True),
    ActionSpec("suck", aliases=(), scope="intimacy", target_schema="intimacy", cost_key="major", mature_gate=True),
    ActionSpec("bite", aliases=(), scope="intimacy", target_schema="intimacy", cost_key="major", mature_gate=True),
    ActionSpec("pinch", aliases=(), scope="intimacy", target_schema="intimacy", cost_key="major", mature_gate=True),
    ActionSpec("blow", aliases=(), scope="intimacy", target_schema="intimacy", cost_key="major", mature_gate=True),
    ActionSpec("tickle", aliases=(), scope="intimacy", target_schema="intimacy", cost_key="major", mature_gate=True),

    # === CRAFTING & FORAGING ===
    ActionSpec("craft", aliases=("make",), scope="crafting", target_schema="target", cost_key="major"),
    ActionSpec("find", aliases=("forage",), scope="foraging", target_schema="target", cost_key="major"),

    # === BODILY & REST ===
    ActionSpec("rest", aliases=(), scope="self", target_schema="duration", cost_key="activity"),
    ActionSpec("sleep", aliases=(), scope="self", target_schema="duration", cost_key="activity"),
    ActionSpec("wait", aliases=("nothing", "pause", "stay"), scope="self", target_schema="none", cost_key="activity"),
    ActionSpec("stand", aliases=(), scope="self", target_schema="none", cost_key="minor"),
    ActionSpec("sit", aliases=(), scope="self", target_schema="none", cost_key="activity"),
    ActionSpec("lie", aliases=("lay",), scope="self", target_schema="none", cost_key="activity"),
    ActionSpec("meditate", aliases=(), scope="self", target_schema="none", cost_key="activity"),
    ActionSpec("bathe", aliases=("bath",), scope="self", target_schema="none", cost_key="activity"),
    ActionSpec("relieve", aliases=(), scope="self", target_schema="none", cost_key="major"),
    ActionSpec("fumble", aliases=("grope", "feel"), scope="self", target_schema="none", cost_key="major"),
    ActionSpec("manifest", aliases=(), scope="self", target_schema="none", cost_key="minor"),
    ActionSpec("vanish", aliases=(), scope="self", target_schema="none", cost_key="minor"),

    # === INTERNAL & MIND ===
    ActionSpec("recall", aliases=(), scope="internal", target_schema="none", cost_key="free"),
    ActionSpec("goal", aliases=(), scope="internal", target_schema="target", cost_key="free"),
    ActionSpec("obligation", aliases=(), scope="internal", target_schema="target", cost_key="free"),
    ActionSpec("offer", aliases=(), scope="social", target_schema="target", cost_key="free"),
    ActionSpec("schedule", aliases=(), scope="internal", target_schema="target", cost_key="free"),
    ActionSpec("plan", aliases=("replan",), scope="internal", target_schema="target", cost_key="free"),
    ActionSpec("fear", aliases=(), scope="internal", target_schema="target", cost_key="free"),
    ActionSpec("interest", aliases=(), scope="internal", target_schema="target", cost_key="free"),
    ActionSpec("guess", aliases=(), scope="internal", target_schema="none", cost_key="free"),

    # === SYSTEM & META ===
    ActionSpec("inventory", aliases=("i", "inv"), scope="meta", target_schema="none", cost_key="free"),
    ActionSpec("stats", aliases=("status",), scope="meta", target_schema="none", cost_key="free"),
    ActionSpec("do", aliases=(), scope="meta", target_schema="target", cost_key="free"),
)


_BY_ID: Dict[str, ActionSpec] = {s.id: s for s in ACTIONS}
_BY_NAME: Dict[str, ActionSpec] = {}
for _s in ACTIONS:
    for _name in _s.all_names:
        _BY_NAME[_name.lower()] = _s


def get_action(name: str) -> Optional[ActionSpec]:
    """Look up an action spec by canonical id or alias."""
    if not name:
        return None
    return _BY_NAME.get(name.lower().strip())


def is_valid_action(name: str, mature: bool = False) -> bool:
    """True if *name* resolves to a recognized action (respecting mature gate)."""
    spec = get_action(name)
    if not spec:
        return False
    if spec.mature_gate and not mature:
        return False
    return True


def all_actions(include_aliases: bool = True, mature: bool = True) -> List[str]:
    """Every registered action name, sorted."""
    out: Set[str] = set()
    for s in ACTIONS:
        if s.mature_gate and not mature:
            continue
        out.add(s.id)
        if include_aliases:
            out.update(s.aliases)
    return sorted(out)


def mature_actions() -> List[str]:
    """Actions that require the mature content toggle."""
    out: Set[str] = set()
    for s in ACTIONS:
        if s.mature_gate:
            out.add(s.id)
            out.update(s.aliases)
    return sorted(out)


def actions_for_scope(scope_name: str) -> List[ActionSpec]:
    """All ActionSpecs matching *scope_name* (case-insensitive)."""
    return [s for s in ACTIONS if s.has_scope(scope_name)]


def bracket_order() -> List[str]:
    """Canonical action display order for item action brackets."""
    return list(BRACKET_ORDER_ACTIONS)


def llm_manifest(mature: bool = False) -> List[Dict[str, Any]]:
    """Structured list of actions for LLM prompt generation."""
    out = []
    for s in ACTIONS:
        if s.mature_gate and not mature:
            continue
        out.append({
            "id": s.id,
            "aliases": list(s.aliases),
            "scope": s.scope,
            "target_schema": s.target_schema,
            "cost_key": s.cost_key,
            "mature_gate": s.mature_gate,
        })
    return out


# Autocomplete action groupings - each group represents a completion domain.
AUTOCOMPLETE_GROUPS: Dict[str, Tuple[str, ...]] = {
    "take": _BY_ID["take"].all_names,
    "examine": _BY_ID["examine"].all_names + ("read",),
    "use": _BY_ID["use"].all_names,
    "door": _BY_ID["open"].all_names + _BY_ID["close"].all_names,
    "drop": _BY_ID["drop"].all_names + ("stow", "put"),
    "throw": _BY_ID["throw"].all_names,
    "combine": _BY_ID["combine"].all_names,
    "split": _BY_ID["split"].all_names,
    "craft": _BY_ID["craft"].all_names,
    "consume": _BY_ID["eat"].all_names + _BY_ID["drink"].all_names,
    "toggle": _BY_ID["toggle"].all_names,
    "char_target": _BY_ID["attack"].all_names + _BY_ID["speak"].all_names + _BY_ID["whisper"].all_names + _BY_ID["shout"].all_names,
    "name": _BY_ID["name"].all_names,
    "go": _BY_ID["go"].all_names,
    "find": _BY_ID["find"].all_names,
}
