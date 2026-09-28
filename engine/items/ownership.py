"""Whose thing is this? Item ownership and personal-item permission (task-515).

A treasured object is not a tool: Gribba's Good Knife is not communal kitchen
equipment, and "nobody else may touch it" should be true in the world rather
than only in the fiction. So an item can say whose it is, and the ordinary
verbs honour that.

Two decisions this module makes, because the task left them open:

**A missing or incapacitated owner lifts the refusal.** A dead goblin's knife
is not a sacred object, and a permission rule that keeps protecting a corpse's
belongings is a worse failure mode than a permissive one. An owner who is not
in the world at all (or is dead, unconscious or bound) is treated as having no
claim. An owner who is merely *elsewhere* keeps it.

**A Social or Intimidation check does NOT lift the refusal.** The contested way
to take someone's personal property is ``steal``, which is already a roll and
already raises the stakes. A second roll hidden inside ``take`` would make an
ordinary verb unpredictable, which is worse than a clear "no". So: the normal
verbs say no plainly, and ``steal`` is the way through.

The marker is a node property, not an edge: ``owner`` (a character name or id)
plus the informational ``personal`` tag. An item with no ``owner`` is nobody's
in particular and behaves exactly as before.
"""

from typing import Optional

#: Owner states that mean the owner has no live claim on their things. Keeps a
#: dead or unconscious character's property from staying sacred forever.
INCAPACITATED_OWNER_STATES = {"dead", "unconscious", "bound", "asleep", "sleeping"}


def _norm(value) -> str:
    """Comparison form for an owner handle: lowercase, punctuation read as
    spaces, and the node-id prefix dropped so ``player_gribba`` and ``Gribba``
    are the same person (project rule: id/name checks lowercase everything)."""
    text = (str(value or "").strip().lower()
            .replace("_", " ").replace("-", " "))
    if text.startswith("player "):
        text = text[len("player "):]
    return " ".join(text.split())


def owner_of(node) -> str:
    """The normalised owner handle, or "" when the item is unowned."""
    if node is None:
        return ""
    return _norm((getattr(node, "properties", None) or {}).get("owner"))


def is_owned(node) -> bool:
    """True when the item declares an owner at all."""
    return bool(owner_of(node))


def is_personal(node) -> bool:
    """True when the item is flagged ``personal`` — a treasured thing, however
    it stands. Informational: permission follows ``owner``, not this tag, so an
    author can mark a keepsake that is not yet anybody's."""
    tags = ((getattr(node, "properties", None) or {}).get("tags") or [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]
    return "personal" in {str(t).strip().lower() for t in tags}


def owner_player(player_manager, handle: str):
    """The live Player for an owner handle, or None if there isn't one."""
    wanted = _norm(handle)
    if not wanted or player_manager is None:
        return None
    players = getattr(player_manager, "players", None) or {}
    for name, player in players.items():
        if _norm(name) == wanted:
            return player
    return None


def owner_incumbent(owner) -> bool:
    """False when the owner cannot enforce a claim — absent, or dead,
    unconscious or bound.

    Being *elsewhere* is not the same as being unable: an owner in another room
    still owns the knife. Only a claim nobody can enforce fades.
    """
    if owner is None:
        return False
    if getattr(owner, "state", "") in INCAPACITATED_OWNER_STATES:
        return False
    return True


def owner_can_enforce(player_manager, handle: str) -> bool:
    """True when *handle* names an owner whose claim the world still honours.

    An owner we have never heard of is assumed to be somewhere real, so an
    unrecognised handle keeps the refusal — silence is not consent."""
    wanted = _norm(handle)
    if not wanted:
        return True
    if owner_player(player_manager, wanted) is None:
        return True   # unknown to us, presumed alive elsewhere
    return owner_incumbent(owner_player(player_manager, wanted))


def is_owner(node, player_manager, actor_name: str = None) -> bool:
    """True when *actor_name* is the item's owner. The owner is always allowed —
    the refusal exists to stop *other* people, never the owner."""
    handle = owner_of(node)
    if not handle:
        return True
    if actor_name is None:
        actor_name = getattr(player_manager, "active_player", "")
    return _norm(actor_name) == handle


def permission_refusal(node, actor_name: str, verb: str, player_manager=None) -> Optional[str]:
    """Why *actor_name* may not *verb* this item, or None when they may.

    `verb` is a past-tense phrase ("take it", "use it") so the message reads as
    a sentence rather than a rule.
    """
    handle = owner_of(node)
    if not handle:
        return None
    if _norm(actor_name) == handle:
        return None
    if player_manager is not None and not owner_can_enforce(player_manager, handle):
        return None
    name = getattr(node, "name", "") or "that"
    owner_name = owner_display_name(handle, player_manager)
    return (f"The {name} is {owner_name}'s, and not yours to {verb}. "
            f"You would have to take it.")


def owner_display_name(handle: str, player_manager=None) -> str:
    """How to write the owner's name in a refusal: the real name when we know
    the person, otherwise the handle as authored."""
    handle = str(handle or "").strip()
    if not handle:
        return "someone"
    player = owner_player(player_manager, handle)
    if player is not None and getattr(player, "name", ""):
        return str(player.name)
    return _norm(handle).title()


def owner_bonus_to_perception() -> int:
    """How much harder stealing a personal item is (task-515).

    A fixed bonus rather than a second roll: the target is watching their own
    thing more closely, which is a reason, not a random number. Kept as a
    function so the value is one line to tune and one place to test.
    """
    return 3
