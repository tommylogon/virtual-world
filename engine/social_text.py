"""Templated prose for background social interactions (task-423).

The background tier never calls an LLM, so a memory has to be written from a
template. Keeping the templates here rather than inline in
`engine/background_social.py` means the same phrasing serves both participants
without the resolution logic growing a pile of strings — and when the LLM
enriches a background span on promotion (the trace -> memory direction), these
are the lines it is enriching.

Every phrase takes an ``{other}`` placeholder holding the *other* participant:
the actor's memory reads "I teased Vekka", the target's reads "Rikka teased me",
and both come from one template per (action, landed).
"""

from __future__ import annotations

#: action -> (landed, did-not-land). `{other}` is the other participant.
PHRASES = {
    "chat": ("chatted with {other}", "ran out of things to say to {other}"),
    "joke": ("made {other} laugh", "told {other} a joke that fell flat"),
    "compliment": ("said something kind to {other}",
                   "fumbled a compliment at {other}"),
    "tease": ("teased {other}", "needled {other} a little too hard"),
    "confide": ("confided in {other}", "started to confide in {other} and stopped"),
    "flirt": ("flirted with {other}", "flirted with {other} and misjudged it"),
    "apologise": ("made it up with {other}", "tried to apologise to {other} badly"),
    "bully": ("leaned on {other}", "tried to lean on {other} and came off worse"),
}

#: Fallback for an action added without a template.
DEFAULT_PHRASES = ("spent time with {other}", "failed to reach {other}")

#: Tier -> whether the event reads as having landed. `minor_failure` is a
#: failure; the tier scale in background_social is the authority and this is
#: derived from it by the caller, so the two cannot disagree.
def phrase(action: str, tier: str, other: str, landed: bool) -> str:
    """The phrase for ``action``, from the ``other`` participant's view.

    ``other`` is whatever the memory needs in that slot — the actor passes the
    target's name, the target passes "me".
    """
    landed_text, failed_text = PHRASES.get(action, DEFAULT_PHRASES)
    template = landed_text if landed else failed_text
    return template.format(other=other)
