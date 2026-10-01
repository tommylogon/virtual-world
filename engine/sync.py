"""Template links: one place that knows what a link is and who can have one.

A **template link** binds a placed node to a library entry, so editing the
template can be pushed down into every copy instead of into each copy by hand.
`library_id` on the node's properties is the link; absent or empty means the
node is standalone and owns its data.

This module is the *contract*. The four ``_refresh_*`` handlers in
``routes/library_ops.py`` keep their per-type apply bodies — they genuinely
differ, because a character's fields live on the ``Player`` and a way's are
coerced booleans — but they all read their field list, their template-id
resolution and their lock rule from here, because that is the part that had
drifted into four different answers.

What was wrong before this module existed, concretely:

- **Four different ways to guess a template id.** An item only accepted an
  explicit one. A way slugified its name. An area stripped an ``area_`` node-id
  prefix and only then fell back to the name. A character fell back to its
  display name. So the same operation on four node types could resolve to three
  different templates, or none.
- **No way to unlink.** ``refresh-to-world`` existed for all four types and
  nothing could break the link, so "this copy is now mine" was unexpressible and
  an author had to stop syncing by forgetting to press the button.
- **No statement of what may sync.** The field lists lived inline in four
  handlers, so "never sync an id" was a convention in somebody's head rather
  than a property this module could expose.

The World -> Library direction is a different concern and lives in the frontend
(``world-sync.js`` ``_mergeEntry`` plus the diff modal's clobber guard). The two
directions share one idea and must not share one file: the Library -> World
half is a field whitelist, the World -> Library half is a "never let a bare
instance erase curated data" rule. task-290 will add ``template_ref`` variants
and override tracking on top of :func:`locked_fields`; it is deliberately not
implemented here, because a whitelist is not a variant system.
"""

import re
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Optional, Tuple

#: The property that carries the link. Absent, empty or ``None`` = standalone.
LINK_FIELD = "library_id"

#: The property that names fields the author has taken ownership of. A locked
#: field survives every sync, which is the Library -> World half of the
#: "don't clobber" rule; the World -> Library half is the frontend merge guard.
LOCKED_FIELD = "locked_fields"

#: Set on a node that was once linked and has since been broken, so the
#: inspector can say "was linked to X" instead of pretending it never was.
BROKEN_FIELD = "template_broken_from"

#: Node properties that are identity or runtime state, never template content.
#: Listed so the intent is a property of this module rather than a habit: a
#: spatial edge, a node id, or where a character happens to be standing is not
#: something a library entry gets to overwrite.
#:
#: ``current_state`` is deliberately **not** here, and that is an open question
#: rather than a settled one. task-289's design says never sync it, and for a
#: way it is right — ``open``/``closed``/``locked`` is runtime, so a sync would
#: re-open a door an NPC had closed. But on an item ``current_state`` carries
#: authored content (``"hidden"`` vs ``"normal"``), and both have shipped that
#: way since the item sync was written. Unifying them changes what an existing
#: refresh does, so it is a decision to make deliberately rather than a cleanup
#: to slip in here. Until then the whitelist follows the code, and this comment
#: is where the disagreement is recorded.
NEVER_SYNCED: FrozenSet[str] = frozenset({
    "id", "type", "position", "spatial_position",
    LINK_FIELD, LOCKED_FIELD, BROKEN_FIELD,
})


@dataclass(frozen=True)
class TemplateSpec:
    """How one node type links to the library.

    ``registry`` is the library file stem under ``data/library/``.
    ``mutable`` is the whitelist: the only fields a sync may write. Anything not
    named here is left alone, which is what keeps ``NEVER_SYNCED`` true by
    construction rather than by remembering to check.
    """

    registry: str
    mutable: Tuple[str, ...]
    #: How to guess a template id when the caller did not name one. ``"none"``
    #: means "do not guess" — an item's id is an opaque library key, so a
    #: name-derived guess would silently attach it to the wrong template.
    guess: str = "none"
    #: A character syncs onto its ``Player``, not onto node properties.
    target: str = "node"


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", str(value or "").lower())


SPECS: Dict[str, TemplateSpec] = {
    "item": TemplateSpec(
        registry="items.json",
        mutable=(
            "name", "description", "actions", "uses", "weight", "equip_slots",
            "current_state", "light_level", "target_temperature", "heating_rate",
            "sound_level", "sound_pattern", "stun_chance", "stun_duration",
            "defense", "damage", "insulation", "resistances", "action_costs",
            "skill_check", "contents", "aliases", "tags", "image", "triggers",
        ),
        guess="none",
    ),
    "way": TemplateSpec(
        registry="ways.json",
        mutable=(
            "name", "description", "current_state", "pass_message", "edge_length",
            "needs_open", "auto_close", "see_through", "one_way", "requires",
            "max_size", "sound_barrier", "prevent_close", "tags", "parameters",
            "triggers", "insulation", "climb_dc", "jump_dc",
            "refusal_message", "blocked_description", "cost", "aliases",
        ),
        guess="name",
    ),
    "area": TemplateSpec(
        registry="areas.json",
        mutable=("name", "description", "tags", "environment", "triggers"),
        guess="node_id_prefix:area_",
    ),
    "character": TemplateSpec(
        registry="characters.json",
        mutable=(
            "name", "description", "base_description", "unknown_name",
            "personality", "stats", "skills", "traits", "tags", "interest_tags",
            "behaviors", "npc_behavior", "npc_action_interval", "npc_state",
            "simple_npc", "memories", "relationships", "vitals", "decay_rates",
            "conditions", "equipped", "recent_hearing", "activity", "current_area",
            "emotion", "image", "profile_image", "expressions", "triggers",
        ),
        guess="node_name",
        target="player",
    ),
}


def spec_for(node_type: str) -> Optional[TemplateSpec]:
    """The link contract for a node type, or ``None`` if it has no library."""
    return SPECS.get(str(node_type or "").lower())


def linked_template_id(node) -> str:
    """The template id this node is bound to, or ``""`` when standalone."""
    props = getattr(node, "properties", None) or {}
    return str(props.get(LINK_FIELD) or "").strip()


def is_linked(node) -> bool:
    return bool(linked_template_id(node))


def locked_fields(node) -> set:
    """Field names the author has taken ownership of on this node."""
    props = getattr(node, "properties", None) or {}
    return {str(f) for f in (props.get(LOCKED_FIELD) or [])}


def resolve_template_id(node, explicit: Optional[str] = None) -> str:
    """The template id to sync from: explicit, then the link, then the type's guess.

    This is the function that used to exist four times with three different
    fallbacks. The per-type behaviour is declared in :data:`SPECS` instead, so
    "which node types guess, and at what" is one table a reader can check
    rather than four branches to compare.
    """
    if explicit:
        return str(explicit).strip()
    existing = linked_template_id(node)
    if existing:
        return existing

    spec = spec_for(getattr(node, "type", ""))
    if spec is None:
        return ""
    node_type = str(node.type).lower()
    props = getattr(node, "properties", None) or {}
    name = props.get("name") or getattr(node, "name", "") or ""

    if spec.guess == "none":
        return ""
    if spec.guess == "name":
        return _slug(name) if name else ""
    if spec.guess == "node_name":
        return str(name)
    if spec.guess.startswith("node_id_prefix:"):
        prefix = spec.guess.split(":", 1)[1]
        node_id = str(getattr(node, "id", "") or "")
        if node_id.startswith(prefix):
            stripped = node_id[len(prefix):]
            if stripped:
                return stripped
        return _slug(name) if name else ""
    return ""


def link(node, template_id: str) -> None:
    """Bind a node to a template, clearing any previous break marker."""
    props = getattr(node, "properties", None)
    if props is None:
        return
    props[LINK_FIELD] = str(template_id or "").strip()
    props.pop(BROKEN_FIELD, None)


def break_template_link(node) -> dict:
    """Unbind a node from its template **without touching its data**.

    The point of breaking a link is to keep what the node currently is. So this
    only ever removes the link marker; every field the template last wrote stays
    exactly as it is, which is what makes "I fixed this one by hand" a durable
    decision rather than something the next accidental refresh undoes.

    Returns a small report the inspector can show: what it was linked to, whether
    anything changed, and whether there was even a link to break.
    """
    was = linked_template_id(node)
    props = getattr(node, "properties", None) or {}

    if not was:
        return {
            "node_id": getattr(node, "id", None),
            "was_linked": False,
            "template_id": None,
            "changed": False,
            "note": "Node is not linked to a template; nothing to break.",
        }

    props.pop(LINK_FIELD, None)
    # Provenance only, so "was linked to X" is still answerable after the break.
    # Deliberately NOT auto-locking every mutable field: that would alter the
    # node (the card says a break changes no data) and would make a later
    # deliberate re-link + sync silently apply nothing, which reads as a broken
    # button rather than as a decision. Re-linking is an explicit choice to sync
    # again; an author who wants some fields spared names them in
    # `locked_fields` themselves.
    props[BROKEN_FIELD] = was
    if hasattr(node, "properties"):
        node.properties = props

    return {
        "node_id": getattr(node, "id", None),
        "was_linked": True,
        "template_id": was,
        "changed": True,
        "note": "Link removed. Node data untouched and still protected by any "
                "locked_fields it already had.",
    }


def _mutable_names(node) -> set:
    spec = spec_for(getattr(node, "type", ""))
    if spec is None:
        return set()
    return {f for f in spec.mutable if f not in NEVER_SYNCED}


def changed_fields(before: dict, after: dict) -> Dict[str, dict]:
    """Fields whose value actually moved, as ``{field: {"from", "to"}}``.

    A sync that rewrites identical values is not a sync an author should be
    told about, and "Updated N fields" is only honest if N counts real changes.
    """
    out: Dict[str, dict] = {}
    for key in sorted(set(before) | set(after)):
        old, new = before.get(key), after.get(key)
        if old != new:
            out[key] = {"from": old, "to": new}
    return out
