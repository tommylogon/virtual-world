"""Per-agent pronoun resolution from identity tags.

Narrator stamps and system copy name characters; the pronoun axis comes
from the character's identity tags (female / male / …), so "Lyrie hugs
her arms" instead of the forced-neutral "their arms" (or the old mixed
voice "hugs yourself"). Characters without a gender tag fall back to
neutral they/them - never a hardcoded guess.
"""

PRONOUN_SETS: dict[str, dict[str, str]] = {
    "female": {
        "subject": "she",
        "object": "her",
        "possessive": "her",
        "possessive_pronoun": "hers",
        "reflexive": "herself",
    },
    "male": {
        "subject": "he",
        "object": "him",
        "possessive": "his",
        "possessive_pronoun": "his",
        "reflexive": "himself",
    },
    "neutral": {
        "subject": "they",
        "object": "them",
        "possessive": "their",
        "possessive_pronoun": "theirs",
        "reflexive": "themselves",
    },
}

#: Identity tags that imply a pronoun set. Matched case-insensitively.
_GENDER_TAGS: dict[str, set[str]] = {
    "female": {"female", "woman", "girl"},
    "male": {"male", "man", "boy"},
}

#: First tokens of an explicit pronouns field, mapped to a set. "xe/xim"
#: and anything unrecognised fall through to the tag lookup (then neutral):
#: an explicit field nobody can act on is worse than no field.
_EXPLICIT: dict[str, str] = {
    "she": "female", "her": "female", "hers": "female", "herself": "female",
    "he": "male", "him": "male", "his": "male", "himself": "male",
    "they": "neutral", "them": "neutral", "their": "neutral",
    "theirs": "neutral", "themselves": "neutral",
}


def _explicit_pronouns(record) -> dict[str, str] | None:
    try:
        block = record.get("identity") if isinstance(record, dict) else None
        raw = (block or {}).get("pronouns", "")
        first = str(raw).strip().split("/")[0].strip().lower()
    except Exception:
        return None
    if not first:
        return None
    set_name = _EXPLICIT.get(first)
    if set_name is None:
        return None
    return PRONOUN_SETS[set_name]


def pronouns_for(player, record=None) -> dict[str, str]:
    """Return the pronoun set for a player object (or None).

    An explicit ``identity.pronouns`` on the structured record wins over
    tags: ``record`` is the ``character_appearance.get_record`` block (or
    anything with an ``identity`` mapping). Reads ``player.tags`` (identity
    markers, same list the trigger system uses) as the fallback;
    anything unreadable/untagged falls back to neutral.
    """
    explicit = _explicit_pronouns(record)
    if explicit is not None:
        return dict(explicit)
    tags: set[str] = set()
    try:
        raw = getattr(player, "tags", None)
        if raw is None:
            raw = []
        if isinstance(raw, (list, tuple, set)):
            for t in raw:
                if isinstance(t, str):
                    tags.add(t.lower())
    except TypeError:
        tags = set()
    if tags & _GENDER_TAGS["female"]:
        return dict(PRONOUN_SETS["female"])
    if tags & _GENDER_TAGS["male"]:
        return dict(PRONOUN_SETS["male"])
    return dict(PRONOUN_SETS["neutral"])
