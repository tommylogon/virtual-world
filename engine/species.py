"""Species: an identity the need layer can read (task-549).

Before this, an animal, a goblin and a human were the same kind of thing to the
simulation. Need servicing was a **pure tag intersection**
(`BackgroundSimulation._has_tag`), so the question *"would this creature use a
latrine?"* could not be answered in either direction: the engine had no idea what
kind of creature it was looking at, only what the room was tagged. That
distinction was authored by hand in the room's tags and was invisible to the
simulation.

The world already models the split — but only for narration. 31 of 272 areas in
the Kraktooth scenario carry `goblin_description`, `human_description` and
`goblin_knowledge`. This module is the same distinction in the layer that
*decides*, not the layer that *describes*.

Three decisions, all of them load-bearing:

1. **A species, not a faction, and not a general tag vocabulary.** There is one
   primary species on the character (`Player.species`). Granularity is the
   author's: `goblin` / `human` / `animal` is too coarse to be useful on its own
   (the camp has a chief, a shaman, prisoners and a farmhand), but the *kind*
   matters, and role is what `tags` are already for. The species answers
   "what kind of creature is this"; tags answer everything else.
2. **An unspecified species must change nothing.** Every one of the 70 library
   characters predates this, and so does every scenario. `Player.species`
   defaults to `None`, and `None` means *no profile applies* — every service is
   permitted, exactly as before. This is what makes the field safe to add, and
   it is the reason the whole mechanism is opt-in.
3. **Exclusion is authored, not guessed.** There is no hardcoded
   "animals don't use latrines". A species profile lists the services it
   *cannot* use; a species with no profile, or an empty exclusion list, can use
   everything. If the answer should differ it is written down where the author
   can see it, which is the acceptance criterion — the answer is a property of
   the data, not of which tags somebody happened to put on a room.

On task-551: relief is **permitted anywhere** and this module does not undo
that. An animal that cannot use a latrine does not thereby become unable to
relieve itself; what species changes is whether the latrine *helps*, which is a
comfort question, and the same dignity model already in `engine.relief` still
applies to whatever they do instead.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

#: The services a species profile can say something about. These are the
#: need-layer vocabularies that already existed (`DRINK_TAGS`,
#: `RELIEF_TAGS`) plus the food one, named as *services* rather than as tag
#: tuples so a profile reads as intent.
SERVICES = ("food", "drink", "relief", "wash", "rest")

#: Species that differ from the default. Everything absent from this table can
#: do everything, which is the whole backward-compatibility story.
#:
#: Only exclusions are listed. "Can use" would have to enumerate every service
#: for every species to stay honest, and the day someone adds a service the
#: positive list silently starts lying.
SPECIES_PROFILES: dict[str, dict] = {
    # Animals: no fixture-based relief, no goblin-style pump. They relieve where
    # they stand — which task-551 already permits — they just do not prefer a
    # built fixture and are not served by one.
    "animal": {"cannot_use": ("relief",), "tags": ("animal",)},
    "beast": {"cannot_use": ("relief",), "tags": ("animal",)},
    "quadruped": {"cannot_use": ("relief",), "tags": ("animal",)},
    # Canids and similar go where they can; nothing to exclude.
    "bird": {"cannot_use": (), "tags": ("animal", "flying")},
    "fish": {"cannot_use": ("drink",), "tags": ("animal")},
    # Undead and constructs: no eating, no drinking.
    "undead": {"cannot_use": ("food", "drink"), "tags": ("undead",)},
    "construct": {"cannot_use": ("food", "drink"), "tags": ("construct",)},
    "plant": {"cannot_use": ("food", "drink"), "tags": ("plant",)},
    # The two the Kraktooth scenario actually needs to tell apart. Both can do
    # everything; they are here so an author can start from a named row, and so
    # the narration side has one place to read species from.
    "goblin": {"cannot_use": (), "tags": ()},
    "human": {"cannot_use": (), "tags": ()},
    "elf": {"cannot_use": (), "tags": ()},
    # A ghost takes no space (task-653) and is intangible, so it needs no relief
    # fixture at all — the one case where the exclusion is anatomical.
    "ghost": {"cannot_use": ("food", "drink", "relief"), "tags": ("ghost",)},
}


def species_of(entity) -> str:
    """The primary species of a character, normalised to lowercase.

    Reads ``Player.species``. A node is accepted but, as everywhere in this
    engine, a **bare graph character node carries no such field** — the data
    lives on the ``Player`` — so a node only answers when it was built with its
    properties (a library load, or an explicitly authored node).
    """
    if entity is None:
        return ""
    value = getattr(entity, "species", None)
    if value is None:
        props = getattr(entity, "properties", None)
        if isinstance(props, dict):
            value = props.get("species")
    if isinstance(value, str):
        return value.strip().lower()
    if isinstance(value, (list, tuple)) and value:
        return str(value[0]).strip().lower()
    return ""


def profile_for(species) -> dict | None:
    """The profile for *species*, or ``None`` when it has none.

    ``None`` is the load-bearing return: it means "no opinion", which permits
    every service. Returning an empty-but-present profile would read as "can do
    nothing" and would be a very different mistake.
    """
    name = str(species or "").strip().lower()
    if not name:
        return None
    if name in SPECIES_PROFILES:
        return dict(SPECIES_PROFILES[name])
    # A compound species ("forest goblin", "deep elf") inherits from its last
    # word, so an author gets sensible behaviour from a descriptive name without
    # registering a profile for every one of them.
    tail = name.replace("_", " ").split()[-1] if name.strip() else ""
    if tail and tail in SPECIES_PROFILES:
        return dict(SPECIES_PROFILES[tail])
    return None


def can_use_service(entity, service) -> bool:
    """May *entity* use *service*?

    True unless this character's own species profile says otherwise. An unknown
    species, and an unknown service, both answer True — the module never
    invents a restriction that nobody authored.
    """
    profile = profile_for(species_of(entity))
    if not profile:
        return True
    return str(service).strip().lower() not in profile.get("cannot_use", ())


def excluded_services(entity) -> list:
    """The services this character's species rules out. Empty for most."""
    profile = profile_for(species_of(entity))
    if not profile:
        return []
    return sorted(profile.get("cannot_use", ()))


def describe_species(entity) -> str:
    """A short prose handle for a character's species, for prompts.

    Empty when unspecified, so an un-authored character adds no words to its own
    description and no prompt.
    """
    return species_of(entity)
