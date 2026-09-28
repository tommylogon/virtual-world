"""Structured appearance and personality (task-507), one slice.

The task asks for optional structured fields alongside the existing prose, in
two authoring modes — prose-only, or fully structured — with the structured
block as the source of truth and the prose as the narrative layer rendered *once*
from it. It is also explicit that this grows per feature and must not become the
whole graph-editor catalog, so this module carries a **curated, mechanic-backed
set only**: every field here has something that can read it.

    appearance   height_cm, weight_kg, build,
                 hair{color, length, style}, eyes{color}, skin{tone}
    personality  likes, dislikes, fears, kinks, turn_offs   (lists of ids)

``media`` / ``mbti`` / ``alignment`` are deliberately absent: nothing in the
engine can act on them, and a field nobody reads is a field that rots.

**Where it lives: the character graph node**, not the ``Player``. Adding an
attribute to :class:`Player` means ``player.py``, which is a hub file. The node
is also where task-457 wants the character definition to end up, so the two
tasks point the same way: put the structured block on the node and task-457's
migration picks it up for free instead of it becoming a third place to look.

**References are ids, never display names.** ``kinks``, ``likes`` and the rest
are lists of ids because a display name is a presentation choice: a rename would
silently orphan every reference, and two characters may share a name. Ids are
resolved to names only for display, at the edge.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

#: Node property holding the structured block. One key, not two, so "is this
#: character structured?" is a single membership test.
RECORD_KEY = "appearance"

#: The curated appearance schema: field -> (kind, subfields).
#: ``kind`` is "number" | "text" | "enum", and ``subfields`` only for groups.
APPEARANCE_FIELDS: Dict[str, Any] = {
    "height_cm": ("number", None),
    "weight_kg": ("number", None),
    "build": ("text", None),
    "hair": ("group", ("color", "length", "style")),
    "eyes": ("group", ("color",)),
    "skin": ("group", ("tone",)),
}

#: Personality fields, all lists of **ids**. The mechanic each one feeds is
#: named here so a field cannot be added without saying what reads it.
PERSONALITY_FIELDS: Dict[str, str] = {
    "likes": "gifts and dialogue targeting",
    "dislikes": "gifts and dialogue targeting",
    "fears": "engine.fear fear_tags; the same id vocabulary",
    "kinks": "affect_for_stimulus -> arousal",
    "turn_offs": "affect_for_stimulus -> disgust and negative arousal",
}

#: An id is a slug: lowercase, digits, underscore or dash. Deliberately strict,
#: because the alternative is a display name sneaking in and becoming a
#: reference that breaks on rename.
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")

#: Plausible human ranges, used to reject a typo rather than to police a design.
HEIGHT_CM_RANGE = (40, 260)
WEIGHT_KG_RANGE = (10, 400)


class StructuredError(ValueError):
    """A structured block that cannot be accepted. Carries per-field detail."""


# ── reading ──

def get_record(node) -> Dict[str, Any]:
    """The structured block on *node*, or ``{}``.

    Prose-only characters simply have no block, and that is the normal case, not
    a missing feature — hence the empty default rather than a fill-in template.
    """
    if node is None:
        return {}
    props = getattr(node, "properties", None) or {}
    record = props.get(RECORD_KEY)
    return dict(record) if isinstance(record, dict) else {}


def is_structured(node) -> bool:
    """True when this character has a structured block at all."""
    return bool(get_record(node))


def appearance(node) -> Dict[str, Any]:
    return dict(get_record(node).get("appearance") or {})


def personality(node) -> Dict[str, List[str]]:
    return {k: list(v) for k, v in (get_record(node).get("personality") or {}).items()}


# ── writing ──

def _clean_appearance(raw: Any) -> Dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise StructuredError("appearance must be an object")
    out: Dict[str, Any] = {}
    for field, (kind, subfields) in APPEARANCE_FIELDS.items():
        if field not in raw:
            continue
        value = raw[field]
        if kind == "group":
            if not isinstance(value, dict):
                raise StructuredError(f"appearance.{field} must be an object")
            group = {k: str(v).strip() for k, v in value.items()
                     if k in subfields and str(v).strip()}
            if group:
                out[field] = group
            continue
        if value is None or (isinstance(value, str) and not value.strip()):
            continue
        if kind == "number":
            try:
                out[field] = float(value)
            except (TypeError, ValueError):
                raise StructuredError(
                    f"appearance.{field} must be a number, got {value!r}")
            continue
        out[field] = str(value).strip()
    for field, bounds, label in (
            ("height_cm", HEIGHT_CM_RANGE, "height"),
            ("weight_kg", WEIGHT_KG_RANGE, "weight")):
        if field in out and not (bounds[0] <= out[field] <= bounds[1]):
            raise StructuredError(
                f"appearance.{field} of {out[field]:g}{label} is not plausible")
    return out


def _clean_personality(raw: Any) -> Dict[str, List[str]]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise StructuredError("personality must be an object")
    out: Dict[str, List[str]] = {}
    for field in PERSONALITY_FIELDS:
        if field not in raw:
            continue
        value = raw[field]
        if isinstance(value, str):
            value = [value]
        if not isinstance(value, (list, tuple, set)):
            raise StructuredError(
                f"personality.{field} must be a list of ids")
        ids, bad = [], []
        for entry in value:
            entry = str(entry).strip()
            if not entry:
                continue
            if not _ID_RE.match(entry):
                bad.append(entry)
                continue
            if entry not in ids:
                ids.append(entry)
        if bad:
            raise StructuredError(
                f"personality.{field} must hold ids, not display names; "
                f"rejected {bad}")
        if ids:
            out[field] = ids
    return out


def validate(record: Any) -> Dict[str, Any]:
    """Validate and normalise a structured block.

    Raises :class:`StructuredError` naming the offending field. Rejecting is the
    right behaviour: a silently dropped kink is a character who mysteriously does
    not respond, which is far harder to notice than a 400.
    """
    if record is None:
        return {}
    if not isinstance(record, dict):
        raise StructuredError("the structured block must be an object")
    unknown = sorted(set(record) - {"appearance", "personality"})
    if unknown:
        raise StructuredError(f"unknown top-level keys: {unknown}")
    out: Dict[str, Any] = {}
    appearance_block = _clean_appearance(record.get("appearance"))
    personality_block = _clean_personality(record.get("personality"))
    if appearance_block:
        out["appearance"] = appearance_block
    if personality_block:
        out["personality"] = personality_block
    return out


def set_record(node, record: Any) -> Dict[str, Any]:
    """Validate and store a structured block on *node*; returns what was stored.

    An empty block removes the key, so a character can go back to prose-only.
    """
    cleaned = validate(record)
    props = getattr(node, "properties", None)
    if props is None:
        raise StructuredError("node has no properties")
    if cleaned:
        props[RECORD_KEY] = cleaned
    else:
        props.pop(RECORD_KEY, None)
    return cleaned


def clear_record(node) -> None:
    """Drop the structured block. Prose-only authoring, restored."""
    if node is not None and getattr(node, "properties", None) is not None:
        node.properties.pop(RECORD_KEY, None)


# ── ids → prose ──

def resolve_ids(ids, lookup) -> List[str]:
    """Map ids to display names via *lookup*, leaving unknown ids visible.

    An id with no resolvable name is kept as itself rather than dropped: a kink
    that quietly vanishes from a description is a bug report with no cause.
    """
    out = []
    for entry in ids or ():
        entry = str(entry)
        try:
            out.append(str(lookup(entry) or entry))
        except Exception:
            out.append(entry)
    return out


_HAIR_LENGTHS = {
    "bald": "", "shaved": "", "cropped": "cropped",
    "short": "short", "medium": "shoulder-length", "long": "long",
    "very long": "waist-length", "floor length": "floor-length",
}


def render_prose(node, resolve=None) -> str:
    """Render the structured appearance as a third-person description.

    This is the *narrative* layer: written once, into ``base_description``,
    where the existing equipment/LLM description pipeline picks it up. It is
    deliberately plain and factual — the LLM's voice owns the prose, this only
    has to get the facts onto the page in a readable order.
    """
    looks = appearance(node)
    if not looks:
        return ""
    looks = dict(looks)
    if resolve:
        for group in ("hair", "eyes", "skin"):
            block = looks.get(group)
            if isinstance(block, dict):
                looks[group] = {k: resolve(v) for k, v in block.items()}

    clauses: List[str] = []
    if "height_cm" in looks:
        clauses.append(f"{_ft_in(looks['height_cm'])} tall")
    if "build" in looks:
        clauses.append(str(looks["build"]))
    if "weight_kg" in looks:
        clauses.append(f"weighing about {looks['weight_kg']:g} kg")

    hair = looks.get("hair") or {}
    hair_bits = [hair[k] for k in ("length", "style", "color") if hair.get(k)]
    if hair_bits:
        clauses.append(_join(hair_bits))
    elif "color" in hair:
        clauses.append(str(hair["color"]))

    eyes = looks.get("eyes") or {}
    if eyes.get("color"):
        clauses.append(f"{eyes['color']} eyes")

    skin = looks.get("skin") or {}
    if skin.get("tone"):
        clauses.append(f"{skin['tone']} skin")

    if not clauses:
        return ""
    return _join(clauses).capitalize() + "."


def _ft_in(centimetres: float) -> str:
    total_inches = centimetres / 2.54
    feet = int(total_inches // 12)
    inches = int(round(total_inches - feet * 12))
    if inches == 12:
        feet, inches = feet + 1, 0
    return f"{feet} foot {inches} inch" if inches else f"{feet} feet"


def _join(parts: List[str]) -> str:
    parts = [str(p) for p in parts if str(p).strip()]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + " and " + parts[-1]


# ── the mechanic ──

#: Kink id -> the affect axes a match moves. All positive: a kink pulls toward
#: arousal and, usually, toward liking whoever triggered it.
KINK_AXES: Dict[str, Dict[str, float]] = {
    "affectionate": {"aroused": 6.0, "happy": 2.0},
    "teasing": {"aroused": 8.0, "happy": 3.0},
    "boldness": {"aroused": 5.0},
    "dominance": {"aroused": 7.0},
    "submission": {"aroused": 7.0, "grateful": 2.0},
    "exhibitionism": {"aroused": 9.0},
    "voyeurism": {"aroused": 8.0},
}

#: Turn-off id -> the affect axes a match moves. Disgust, anger or fear *up*,
#: arousal *down*.
#:
#: Kept as a separate table rather than one table with a sign flipped. Negating a
#: shared table turns "disgust up, arousal down" into "disgust down, arousal up"
#: — the exact opposite of a turn-off — because the sign of an axis is semantic
#: here, not an arithmetic consequence of which list it came from.
TURN_OFF_AXES: Dict[str, Dict[str, float]] = {
    "cruelty": {"disgusted": 9.0, "angry": 4.0, "aroused": -6.0},
    "deception": {"disgusted": 7.0, "angry": 3.0, "aroused": -4.0},
    "coercion": {"disgusted": 10.0, "afraid": 5.0, "aroused": -8.0},
    "incompetence": {"disgusted": 4.0, "irritated": 5.0},
    "abuse": {"disgusted": 10.0, "sad": 5.0, "aroused": -7.0},
}

#: Every stimulus id the mechanic knows, for the schema and the tests.
AFFECT_AXES: Dict[str, Dict[str, float]] = {**KINK_AXES, **TURN_OFF_AXES}

#: What a kink or turn-off the tables do not cover still does. A kink nobody
#: wrote axes for is still a kink; a turn-off nobody wrote axes for still turns
#: something off.
KINK_FALLBACK: Dict[str, float] = {"aroused": 5.0}
TURN_OFF_FALLBACK: Dict[str, float] = {"disgusted": 5.0, "aroused": -3.0}


def affect_for_stimulus(node, stimulus_id: str) -> Dict[str, float]:
    """Affect deltas for *stimulus_id* against this character's record.

    The mechanic task-507 asks for: a kink raises arousal, a turn-off raises
    disgust and pushes arousal down. Returns ``{}`` for an unknown stimulus, a
    character with no structured record, or a character who is simply neutral
    about it — never a guess, so an unrelated stimulus cannot nudge a character.
    """
    record = get_record(node)
    if not record:
        return {}
    key = str(stimulus_id or "").strip()
    if not key:
        return {}
    listed = record.get("personality") or {}
    wants = set(listed.get("kinks") or ())
    refuses = set(listed.get("turn_offs") or ())
    deltas: Dict[str, float] = {}

    def _apply(axes: Dict[str, float]) -> None:
        for axis, magnitude in axes.items():
            deltas[axis] = deltas.get(axis, 0.0) + magnitude

    if key in wants:
        _apply(KINK_AXES.get(key, KINK_FALLBACK))
    if key in refuses:
        # A turn-off is defined against the same vocabulary, so an id that is
        # both is contradictory: refuse wins, because a character cannot be
        # simultaneously drawn to and repelled by the same thing in a way that
        # is worth modelling here.
        _apply(TURN_OFF_AXES.get(key, TURN_OFF_FALLBACK))
    return {axis: round(value, 2) for axis, value in deltas.items() if value}


def knows_personality_id(node, field: str, value: str) -> bool:
    """Whether *value* is in this character's *field* list (``likes`` etc)."""
    listed = (get_record(node).get("personality") or {}).get(str(field)) or ()
    return str(value) in set(listed)


def schema_for_llm() -> Dict[str, Any]:
    """The JSON schema of the whole structured block, for the LLM-fill flow.

    Task-507 wants the model handed the schema of all fields plus the character
    card. Returning it from one place means the prompt and the validator cannot
    disagree about what exists.
    """
    appearance_block: Dict[str, Any] = {}
    for field, (kind, subfields) in APPEARANCE_FIELDS.items():
        if kind == "group":
            appearance_block[field] = {
                sub: {"type": "string",
                      "description": f"{field} {sub}"}
                for sub in subfields
            }
        elif kind == "number":
            appearance_block[field] = {"type": "number"}
        else:
            appearance_block[field] = {"type": "string"}

    personality_block = {
        field: {
            "type": "array",
            "items": {"type": "string", "pattern": _ID_RE.pattern},
            "description": f"ids of {mechanic}",
        }
        for field, mechanic in PERSONALITY_FIELDS.items()
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "appearance": {
                "type": "object",
                "additionalProperties": False,
                "properties": appearance_block,
            },
            "personality": {
                "type": "object",
                "additionalProperties": False,
                "properties": personality_block,
            },
        },
    }
