"""Name masking for stranger descriptions (task-339 companion).

Design contract: a stranger's first sentence is an *appearance* handle —
but character descriptions routinely BEGIN with the character's name
("miki doki, mid-twenties american..."), so slicing the first sentence
still leaks the name. When the viewer doesn't know the name, scrub the
real name (and aliases) out of the prose and replace with the stranger
label before rendering.
"""

import re as _re


def mask_name_in_text(text: str, char_name: str, label: str, aliases=()) -> str:
    """Replace *char_name* (and *aliases*) in *text* with *label*.

    No-op when text is empty or the name is empty. Longest pattern first so
    multi-word aliases win over single-word ones.
    """
    if not text or not char_name:
        return text
    patterns = {char_name.lower()}
    for alias in aliases or ():
        if alias:
            patterns.add(str(alias).lower())
    for pattern in sorted(patterns, key=len, reverse=True):
        text = _re.sub(
            r"(?<!\w)" + _re.escape(pattern) + r"(?!\w)",
            label or "the stranger",
            text,
            flags=_re.IGNORECASE,
        )
    return text
