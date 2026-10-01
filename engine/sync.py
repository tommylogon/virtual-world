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

#: The richer link introduced by task-290: the same ``library_id`` plus what a
#: flat string cannot say — which variant, which fields are linked at all, and
#: which the author has taken over. It is **additive**: a node may carry only the
#: flat field, only this block, or both, and :func:`template_ref` folds the
#: shapes together so no other call site has to care.
REF_FIELD = "template_ref"

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


def link(node, template_id: str, *, variant: Optional[str] = None,
         overrides: Optional[dict] = None) -> None:
    """Bind a node to a template, clearing any previous break marker.

    Writes the **flat** ``library_id`` even when a variant is given, and records
    the rest in ``template_ref``. That asymmetry is deliberate: ~150 call sites
    in 33 files read ``library_id`` directly (26 of them in ``population.py``),
    and a variant is a *subset* of a template, not a different one — so the flat
    field stays the single answer to "which template is this", and ``template_ref``
    only carries what the flat field cannot express.
    """
    props = getattr(node, "properties", None)
    if props is None:
        return
    props[LINK_FIELD] = str(template_id or "").strip()
    props.pop(BROKEN_FIELD, None)

    ref = {}
    if variant:
        ref["variant"] = str(variant)
    if overrides:
        ref["overrides"] = dict(overrides)
    if ref:
        props[REF_FIELD] = ref
    elif REF_FIELD in props:
        props.pop(REF_FIELD, None)


def template_ref(node) -> dict:
    """The node's link as one normalised dict — the only reader of both shapes.

    This is the "wrap ``library_id`` on first read" migration, done in the one
    place that reads links. A node written before task-290 has a bare
    ``library_id`` and no ``template_ref``; a node written after may have both.
    Rather than rewrite every one of those call sites, the two shapes are folded
    together here and everything downstream sees one dict.

    Returns ``{"library_id", "variant", "linked_fields", "overrides"}`` with
    absent keys as empty values, so a caller never has to test for them.
    """
    props = getattr(node, "properties", None) or {}
    stored = props.get(REF_FIELD) or {}
    if not isinstance(stored, dict):
        stored = {}
    return {
        "library_id": linked_template_id(node),
        "variant": str(stored.get("variant") or "").strip(),
        "linked_fields": [str(f) for f in (stored.get("linked_fields") or [])],
        "overrides": dict(stored.get("overrides") or {}),
    }


def override_fields(node) -> frozenset:
    """Fields the author has taken ownership of on this node.

    The union of the two ways of saying so: the pre-290 ``locked_fields`` list,
    and the post-290 ``template_ref.overrides`` map. Both exist, both mean the
    same thing, and a sync has to honour both — otherwise upgrading the authoring
    format would quietly unprotect every field a previous author had locked.
    """
    return frozenset(locked_fields(node)) | frozenset(template_ref(node)["overrides"])


def syncable_fields(node) -> frozenset:
    """The fields a sync may write for this node: whitelist minus what is owned.

    ``linked_fields`` narrows further when present — it is the author saying
    "only these come from the template" — and overrides remove individual fields
    from whatever is left.
    """
    ref = template_ref(node)
    fields = set(_mutable_names(node))
    if ref["linked_fields"]:
        fields &= set(ref["linked_fields"])
    fields -= set(override_fields(node))
    return frozenset(f for f in fields if f not in NEVER_SYNCED)


def _merge_definition(base: dict, overlay: dict) -> dict:
    """Deep-merge ``overlay`` onto ``base``; overlay wins (task-290 design 5).

    Dicts merge key by key so a variant can adjust one setting of a trigger
    without restating the rest. Lists **replace** rather than concatenate:
    appending a variant's tags to the base's would be a surprise, and a variant
    saying ``tags: ["outdoor"]`` means exactly that.
    """
    out = dict(base or {})
    for key, value in (overlay or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge_definition(out[key], value)
        else:
            out[key] = value
    return out


def resolve_template(registry: dict, library_id: str,
                     variant: Optional[str] = None) -> Optional[dict]:
    """The effective definition for a template + optional variant.

    Resolution is a chain, applied base-first:

    1. ``parent_template``, if the entry declares one — the base space. The
       parent's own ``parent_template`` is followed too, so a chain is allowed,
       with a depth cap so a cycle in authored data cannot hang a save.
    2. the entry itself, on top of that base.
    3. ``entry["variants"][variant]``, on top of *that*, when a variant is named.

    The card puts conflict resolution out of scope with "variant wins by design",
    and that is what the layering does: the most specific definition is applied
    last, so it wins every field it mentions and inherits the rest.
    """
    if not library_id or library_id not in (registry or {}):
        return None

    chain: list = []
    current_id = library_id
    seen: set = set()
    while current_id and current_id in registry and current_id not in seen:
        seen.add(current_id)
        chain.append(registry[current_id] or {})
        if len(chain) > 8:                      # authored cycle guard
            break
        current_id = (registry[current_id] or {}).get("parent_template") or ""

    definition: dict = {}
    for entry in reversed(chain):               # base first
        definition = _merge_definition(definition, entry)

    if variant:
        variants = (registry.get(library_id) or {}).get("variants") or {}
        chosen = variants.get(str(variant))
        if chosen is None:
            return None
        definition = _merge_definition(definition, chosen)

    # A variants map and a parent pointer are authoring metadata, not content:
    # they must not land on the node as if they were fields of the template.
    definition.pop("variants", None)
    definition.pop("parent_template", None)
    return definition


def break_template_link(node) -> dict:
    """Unbind a node from its template **without touching its data**.

    The point of breaking a link is to keep what the node currently is. So this
    only ever removes the link marker; every field the template last wrote stays
    exactly as it is, which is what makes "I fixed this one by hand" a durable
    decision rather than something the next accidental refresh undoes.

    An ``overrides`` map is *flattened into the node* on the way out (task-290
    design 3): those values were the reason the link existed, and dropping them
    with the block would silently lose an author's work.

    Returns a small report the inspector can show: what it was linked to, whether
    anything changed, and whether there was even a link to break.
    """
    was = linked_template_id(node)
    ref = template_ref(node)
    props = getattr(node, "properties", None) or {}

    if not was:
        return {
            "node_id": getattr(node, "id", None),
            "was_linked": False,
            "template_id": None,
            "changed": False,
            "note": "Node is not linked to a template; nothing to break.",
        }

    flattened = []
    for key, value in (ref["overrides"] or {}).items():
        if key in NEVER_SYNCED:
            continue
        if props.get(key) != value:
            props[key] = value
            flattened.append(key)

    props.pop(LINK_FIELD, None)
    props.pop(REF_FIELD, None)
    # Provenance only, so "was linked to X" is still answerable after the break.
    # Deliberately NOT auto-locking every mutable field: that would alter the
    # node (the card says a break changes no data) and would make a later
    # deliberate re-link + sync silently apply nothing, which reads as a broken
    # button rather than as a decision. Re-linking is an explicit choice to sync
    # again; an author who wants fields spared names them in
    # `locked_fields` themselves.
    props[BROKEN_FIELD] = was
    if hasattr(node, "properties"):
        node.properties = props

    return {
        "node_id": getattr(node, "id", None),
        "was_linked": True,
        "template_id": was,
        "variant": ref["variant"] or None,
        "flattened_overrides": flattened,
        "changed": True,
        "note": "Link removed. Node data untouched and still protected by any "
                "locked_fields it already had."
                + (f" Overrides flattened onto the node: {', '.join(flattened)}."
                   if flattened else ""),
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
