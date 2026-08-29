"""Per-agent pronoun resolution from identity tags.

Narrator stamps and system copy name characters; the pronoun axis comes
from the character's identity tags (female / male / …), so "Lyrie hugs
her arms" instead of the forced-neutral "their arms" (or the old mixed
voice "hugs yourself"). Characters without a gender tag fall back to
neutral they/them — never a hardcoded guess.
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


def pronouns_for(player) -> dict[str, str]:
    """Return the pronoun set for a player object (or None).

    Reads ``player.tags`` (identity markers, same list the trigger system
    uses); anything unreadable/untagged falls back to neutral.
    """
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
