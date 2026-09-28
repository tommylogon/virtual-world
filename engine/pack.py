"""Pack logic for simple NPCs (task-354), MVP scope.

The filed idea: several rats, or several wolves, coordinate through code. They
hear or smell each other over a wider distance than sight, warn each other, and
attack the same target.

Three pieces, matching the MVP the task file itself specifies:

* **Pack identity** — a ``pack:<name>`` entry in the character's existing
  ``tags``. No new field: ``player.tags`` is where the shipped data already puts
  the things a character *is* (``"goblin"``, ``"rat"``), and adding a
  ``pack`` attribute to :class:`Player` would be ``player.py``, a hub file. A
  tag also means a pack is visible to everything else that reads tags.
* **Packmate awareness** — who shares a pack and where, plus a *call* that
  reaches one room further than sight, which is the "hear or smell over larger
  areas" half of the idea.
* **A coordinated target** — the nearest packmate's target, so a pack converges
  on one enemy instead of splitting.

Deliberately **not** here: formation, flanking, role assignment. The task file
puts those out of scope, and they are the part that turns a mechanic into a
project.

Scope note: this only does anything for characters a scenario has actually
tagged. Like task-552, the mechanic is inert until the data exists — a `pack:`
tag with no packmate is just a character, and that is the correct answer.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set

#: Tag prefix that marks pack membership.
PACK_PREFIX = "pack:"

#: How many areas away a pack *call* carries. One room: enough that a rat in the
#: next doorway knows the one in this room is being chased, which is the MVP's
#: "hear or smell over larger areas" and not enough to coordinate a whole
#: dungeon. Beyond sight but not beyond hearing.
PACK_CALL_RANGE = 1

#: Pack calls are throttled per pack so a cornered rat does not have the whole
#: sewer howling every tick.
PACK_CALL_COOLDOWN = 10


def pack_of(player) -> Optional[str]:
    """This character's pack name, or None.

    Lowercased so ``pack:Sewer`` and ``pack:sewer`` are the same pack — the same
    reasoning as ``player_manager.relationship_key``.
    """
    for tag in (getattr(player, "tags", None) or []):
        text = str(tag).strip()
        if text.lower().startswith(PACK_PREFIX):
            name = text[len(PACK_PREFIX):].strip().lower()
            if name:
                return name
    return None


def packmates_in(gs, player, areas: int = 0) -> List[str]:
    """Names of packmates, nearest first.

    ``areas`` widens the search: 0 is same area only, and a positive value walks
    that many areas away through the area graph. Living packmates only — a dead
    packmate is not calling for help.
    """
    pack = pack_of(player)
    if not pack:
        return []
    here = getattr(player, "current_area", None)
    if not here:
        return []

    reachable = {here} if areas <= 0 else _areas_within(gs, here, areas)
    out = []
    for name, other in (getattr(gs, "players", None) or {}).items():
        if other is player or name == getattr(player, "name", None):
            continue
        if getattr(other, "state", "") == "dead":
            continue
        if pack_of(other) != pack:
            continue
        if getattr(other, "current_area", None) in reachable:
            out.append(name)
    return out


def _areas_within(gs, area_name: str, hops: int) -> Set[str]:
    """Area names reachable from *area_name* within *hops* steps."""
    seen = {area_name}
    frontier = [area_name]
    for _ in range(max(0, hops)):
        nxt = []
        for name in frontier:
            try:
                exits = gs._build_exits_for_area(name) or {}
            except Exception:
                continue
            for direction, ex in exits.items():
                target = (ex or {}).get("area") or (ex or {}).get("target_area")
                if target and target not in seen:
                    seen.add(target)
                    nxt.append(target)
        frontier = nxt
        if not frontier:
            break
    return seen


def coordinated_target(gs, player, threats: Optional[List[str]] = None) -> Optional[str]:
    """A target a packmate is already dealing with, or None.

    The MVP's "attack the same target as the nearest packmate". Deliberately a
    *nearest-packmate* rule rather than a majority vote: a pack that has to
    agree before it acts is not a pack, it is a committee.

    *threats* restricts the answer to characters actually worth converging on,
    so a pack does not inherit a packmate's grudge against another rat.
    """
    packmates = packmates_in(gs, player)
    if not packmates:
        return None
    allowed = set(threats) if threats is not None else None
    for name in packmates:
        other = (getattr(gs, "players", None) or {}).get(name)
        target = getattr(other, "pack_target", None)
        if not target or target == getattr(player, "name", None):
            continue
        if allowed is not None and target not in allowed:
            continue
        return target
    return None


def call_for_help(gs, player, cause: str, tick: int) -> List[str]:
    """Sound a pack call, reaching one room further than sight.

    Returns the packmates that heard it. The caller stamps
    ``pack_target`` on each listener so :func:`coordinated_target` has something
    to converge on — the call is what carries the information, and without that
    stamp a "pack" is just a crowd standing near each other.
    """
    pack = pack_of(player)
    if not pack:
        return []
    heard = packmates_in(gs, player, areas=PACK_CALL_RANGE)
    if not heard:
        return []
    _mark_call(gs, pack, tick)
    heard.sort()
    target = getattr(player, "name", None)
    for name in heard:
        other = (getattr(gs, "players", None) or {}).get(name)
        if other is not None:
            other.pack_target = target
    return heard


def _mark_call(gs, pack: str, tick: int) -> None:
    calls = getattr(gs, "_pack_last_call", None)
    if calls is None:
        calls = gs._pack_last_call = {}
    calls[pack] = int(tick or 0)


def on_call_cooldown(gs, player, tick: int) -> bool:
    """True when this pack called recently, so it should not call again."""
    pack = pack_of(player)
    if not pack:
        return False
    calls = getattr(gs, "_pack_last_call", None) or {}
    last = calls.get(pack)
    if last is None:
        return False
    return (int(tick or 0) - int(last)) < PACK_CALL_COOLDOWN


def pack_summary(player) -> Dict[str, object]:
    """The pack view of a character, for a prompt or a debug endpoint."""
    pack = pack_of(player)
    return {
        "pack": pack,
        "tag": f"{PACK_PREFIX}{pack}" if pack else "",
        "in_pack": pack is not None,
    }
