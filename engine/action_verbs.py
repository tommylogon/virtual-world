"""Scoped registry and single source of truth for action verbs (task-491).

Every verb accepted by the game command line, agent action normalizer,
prompt builder, Human Turn buttons, or autocomplete is declared here once.
`tools/action_verbs_index.py` emits the client-side mirror
(`static/js/agent/action-verbs.generated.js`).

@module action_verbs
@contributes VerbSpec, VERBS, all_verbs, mature_verbs, verbs_for_scope, bracket_order, llm_manifest
@powers Use / use on - single source of truth for action verbs across client and engine
@relates engine/action_tiers.py, routes/action_handlers.py, static/js/agent/action-verbs.generated.js
@docs docs/virtualWorld/AI & Narration/Agent Engine.md
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from engine.pleasure_actions import INTIMACY_VERBS


@dataclass(frozen=True)
class VerbSpec:
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
BRACKET_ORDER_VERBS: Tuple[str, ...] = (
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


VERBS: Tuple[VerbSpec, ...] = (
    # === MOVEMENT & PASSAGE ===
    VerbSpec("go", aliases=("walk", "move", "enter"), scope="way", target_schema="target", cost_key="major"),
    VerbSpec("dash", aliases=(), scope="way", target_schema="target", cost_key="major"),
    VerbSpec("crawl", aliases=(), scope="way", target_schema="target", cost_key="major"),
    VerbSpec("climb", aliases=(), scope="way", target_schema="target", cost_key="major"),
    VerbSpec("jump", aliases=(), scope="way", target_schema="target", cost_key="major"),
    VerbSpec("approach", aliases=(), scope="way", target_schema="target", cost_key="minor"),
    VerbSpec("escape", aliases=(), scope="movement", target_schema="none", cost_key="major"),
    VerbSpec("struggle", aliases=(), scope="movement", target_schema="none", cost_key="major"),
    VerbSpec("flee", aliases=("disengage", "withdraw"), scope="movement", target_schema="none", cost_key="minor"),
    VerbSpec("stop", aliases=(), scope="movement", target_schema="none", cost_key="free"),

    # === ITEMS & CONTAINMENT ===
    VerbSpec("take", aliases=("get", "pickup", "pick", "snatch", "collect"), scope="item", target_schema="item", cost_key="major", bracket_order=0),
    VerbSpec("use", aliases=("use_on",), scope="item", target_schema="item_target", cost_key="major", bracket_order=1),
    VerbSpec("open", aliases=("unlock",), scope="item,way", target_schema="target", cost_key="free", bracket_order=3),
    VerbSpec("close", aliases=("lock",), scope="item,way", target_schema="target", cost_key="free", bracket_order=4),
    VerbSpec("eat", aliases=("consume",), scope="item", target_schema="item", cost_key="major", bracket_order=5),
    VerbSpec("drink", aliases=("quaff",), scope="item", target_schema="item", cost_key="major", bracket_order=6),
    VerbSpec("read", aliases=(), scope="item", target_schema="target", cost_key="major", bracket_order=7),
    VerbSpec("wear", aliases=("equip", "dress"), scope="item", target_schema="item", cost_key="minor", bracket_order=8),
    VerbSpec("remove", aliases=("unequip", "undress", "strip"), scope="item", target_schema="item", cost_key="minor", bracket_order=9),
    VerbSpec("toggle", aliases=("light", "ignite"), scope="item", target_schema="item", cost_key="minor", bracket_order=10),
    VerbSpec("drop", aliases=(), scope="item", target_schema="item", cost_key="free", bracket_order=11),
    VerbSpec("put", aliases=("place", "stow"), scope="item", target_schema="item_target", cost_key="minor"),
    VerbSpec("combine", aliases=(), scope="item", target_schema="item", cost_key="major"),
    VerbSpec("split", aliases=(), scope="item", target_schema="item", cost_key="major"),
    VerbSpec("write", aliases=("inscribe",), scope="item", target_schema="item_target", cost_key="major"),
    VerbSpec("bind", aliases=("enchant",), scope="item", target_schema="trigger_bind", cost_key="major"),
    VerbSpec("fix", aliases=("treat",), scope="item", target_schema="item", cost_key="major"),

    # === PERCEPTION & INSPECTION ===
    VerbSpec("examine", aliases=("search", "inspect", "check", "x"), scope="perception,item", target_schema="target", cost_key="major", bracket_order=12),
    VerbSpec("look", aliases=("l",), scope="perception", target_schema="none", cost_key="free"),
    VerbSpec("listen", aliases=(), scope="perception", target_schema="none", cost_key="free"),
    VerbSpec("frisk", aliases=(), scope="perception", target_schema="target", cost_key="major"),

    # === SOCIAL & INTERACTION ===
    VerbSpec("speak", aliases=("say", "talk"), scope="social", target_schema="target", cost_key="free"),
    VerbSpec("whisper", aliases=(), scope="social", target_schema="target", cost_key="free"),
    VerbSpec("shout", aliases=("yell", "scream"), scope="social", target_schema="none", cost_key="free"),
    VerbSpec("sing", aliases=(), scope="social", target_schema="none", cost_key="free"),
    VerbSpec("give", aliases=("hand",), scope="social", target_schema="item_target", cost_key="major"),
    VerbSpec("steal", aliases=(), scope="social", target_schema="item_target", cost_key="major"),
    VerbSpec("lead", aliases=(), scope="social", target_schema="target", cost_key="minor"),
    VerbSpec("teach", aliases=(), scope="social", target_schema="item_target", cost_key="major"),
    VerbSpec("wake", aliases=(), scope="social", target_schema="target", cost_key="minor"),
    VerbSpec("name", aliases=("label",), scope="social", target_schema="target", cost_key="free"),

    # === COMBAT ===
    VerbSpec("attack", aliases=("kill", "hit", "strike", "punch"), scope="combat", target_schema="target", cost_key="major"),
    VerbSpec("grab", aliases=(), scope="combat", target_schema="target", cost_key="minor"),
    VerbSpec("release", aliases=(), scope="combat", target_schema="target", cost_key="minor"),

    # === INTIMACY (MATURE GATE) ===
    VerbSpec("kiss", aliases=(), scope="intimacy", target_schema="intimacy", cost_key="major", mature_gate=True),
    VerbSpec("caress", aliases=(), scope="intimacy", target_schema="intimacy", cost_key="major", mature_gate=True),
    VerbSpec("lick", aliases=(), scope="intimacy", target_schema="intimacy", cost_key="major", mature_gate=True),
    VerbSpec("suck", aliases=(), scope="intimacy", target_schema="intimacy", cost_key="major", mature_gate=True),
    VerbSpec("bite", aliases=(), scope="intimacy", target_schema="intimacy", cost_key="major", mature_gate=True),
    VerbSpec("pinch", aliases=(), scope="intimacy", target_schema="intimacy", cost_key="major", mature_gate=True),
    VerbSpec("blow", aliases=(), scope="intimacy", target_schema="intimacy", cost_key="major", mature_gate=True),
    VerbSpec("tickle", aliases=(), scope="intimacy", target_schema="intimacy", cost_key="major", mature_gate=True),

    # === CRAFTING & FORAGING ===
    VerbSpec("craft", aliases=("make",), scope="crafting", target_schema="target", cost_key="major"),
    VerbSpec("find", aliases=("forage",), scope="foraging", target_schema="target", cost_key="major"),

    # === BODILY & REST ===
    VerbSpec("rest", aliases=(), scope="self", target_schema="duration", cost_key="activity"),
    VerbSpec("sleep", aliases=(), scope="self", target_schema="duration", cost_key="activity"),
    VerbSpec("wait", aliases=("nothing", "pause", "stay"), scope="self", target_schema="none", cost_key="activity"),
    VerbSpec("stand", aliases=(), scope="self", target_schema="none", cost_key="minor"),
    VerbSpec("sit", aliases=(), scope="self", target_schema="none", cost_key="activity"),
    VerbSpec("lie", aliases=("lay",), scope="self", target_schema="none", cost_key="activity"),
    VerbSpec("meditate", aliases=(), scope="self", target_schema="none", cost_key="activity"),
    VerbSpec("bathe", aliases=("bath",), scope="self", target_schema="none", cost_key="activity"),
    VerbSpec("relieve", aliases=(), scope="self", target_schema="none", cost_key="major"),
    VerbSpec("fumble", aliases=("grope", "feel"), scope="self", target_schema="none", cost_key="major"),
    VerbSpec("manifest", aliases=(), scope="self", target_schema="none", cost_key="minor"),
    VerbSpec("vanish", aliases=(), scope="self", target_schema="none", cost_key="minor"),

    # === INTERNAL & MIND ===
    VerbSpec("recall", aliases=(), scope="internal", target_schema="none", cost_key="free"),
    VerbSpec("goal", aliases=(), scope="internal", target_schema="target", cost_key="free"),
    VerbSpec("obligation", aliases=(), scope="internal", target_schema="target", cost_key="free"),
    VerbSpec("schedule", aliases=(), scope="internal", target_schema="target", cost_key="free"),
    VerbSpec("fear", aliases=(), scope="internal", target_schema="target", cost_key="free"),
    VerbSpec("interest", aliases=(), scope="internal", target_schema="target", cost_key="free"),
    VerbSpec("guess", aliases=(), scope="internal", target_schema="none", cost_key="free"),

    # === SYSTEM & META ===
    VerbSpec("inventory", aliases=("i", "inv"), scope="meta", target_schema="none", cost_key="free"),
    VerbSpec("stats", aliases=("status",), scope="meta", target_schema="none", cost_key="free"),
    VerbSpec("do", aliases=(), scope="meta", target_schema="target", cost_key="free"),
)


_BY_ID: Dict[str, VerbSpec] = {s.id: s for s in VERBS}
_BY_NAME: Dict[str, VerbSpec] = {}
for _s in VERBS:
    for _name in _s.all_names:
        _BY_NAME[_name.lower()] = _s


def get_verb(name: str) -> Optional[VerbSpec]:
    """Look up a verb spec by canonical id or alias."""
    if not name:
        return None
    return _BY_NAME.get(name.lower().strip())


def is_valid_verb(name: str, mature: bool = False) -> bool:
    """True if *name* resolves to a recognized verb (respecting mature gate)."""
    spec = get_verb(name)
    if not spec:
        return False
    if spec.mature_gate and not mature:
        return False
    return True


def all_verbs(include_aliases: bool = True, mature: bool = True) -> List[str]:
    """Every registered verb name, sorted."""
    out: Set[str] = set()
    for s in VERBS:
        if s.mature_gate and not mature:
            continue
        out.add(s.id)
        if include_aliases:
            out.update(s.aliases)
    return sorted(out)


def mature_verbs() -> List[str]:
    """Verbs that require the mature content toggle."""
    out: Set[str] = set()
    for s in VERBS:
        if s.mature_gate:
            out.add(s.id)
            out.update(s.aliases)
    return sorted(out)


def verbs_for_scope(scope_name: str) -> List[VerbSpec]:
    """All VerbSpecs matching *scope_name* (case-insensitive)."""
    return [s for s in VERBS if s.has_scope(scope_name)]


def bracket_order() -> List[str]:
    """Canonical verb display order for item action brackets."""
    return list(BRACKET_ORDER_VERBS)


def llm_manifest(mature: bool = False) -> List[Dict[str, Any]]:
    """Structured list of verbs for LLM prompt generation."""
    out = []
    for s in VERBS:
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


# Autocomplete verb groupings - each group represents a completion domain.
AUTOCOMPLETE_GROUPS: Dict[str, Tuple[str, ...]] = {
    "take": _BY_ID["take"].all_names,
    "examine": _BY_ID["examine"].all_names + ("read",),
    "use": _BY_ID["use"].all_names,
    "door": _BY_ID["open"].all_names + _BY_ID["close"].all_names,
    "drop": _BY_ID["drop"].all_names + ("stow", "put"),
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
