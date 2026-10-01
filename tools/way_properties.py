#!/usr/bin/env python3
"""The canonical way-property declaration.

Four axes of behaviour live on a `way` node, and they are independent — a way can be
passable and opaque, or solid and glazed, or open and climb-gated, or narrow and
see-through. Any of them can be set from three unrelated directions (a trigger, the
library, a hand-authored save), and the three directions historically copied the
property list by hand and drifted apart.

This module is the one place the set is written down. `tools/way_property_index.py`
generates the documentation page from it and fails when any hand-maintained list in the
engine stops matching, so the page cannot quietly become a lie.

Adding a property here is the whole task: declare it, regenerate, and the checker tells
you which call sites still need to learn about it.

Fields per property:
    name       the property key as stored on the node
    axis       which of the four independent axes it belongs to, or "identity"/"authoring"
    values     the closed set, where one exists. ``None`` means free-form.
    reads      engine code that consumes it, as (file, line, what it decides)
    notes      the rule that is not obvious from the name
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence, Tuple

Read = Tuple[str, int, str]

#: The four independent behaviour axes. A way's *meaning* is the tuple of these, which is
#: why no single "kind" can describe a way and why a new kind of door is usually just a
#: new combination of existing values.
AXES = {
    "passage": "Whether you can get through, and what stops you",
    "transparency": "Whether you can see or hear through",
    "verb": "Which movement verb the passage demands",
    "size": "Who physically fits",
    "identity": "Naming, layout and rendering — no traversal effect",
    "authoring": "Editor-facing metadata that changes how something is authored",
}

#: The lists a library-synced property must appear in. The trigger spawn path is NOT
#: among them: it is a narrower surface by design (see TRIGGER_OMISSIONS), and holding
#: it to the same set would report 19 "omissions" that are mostly properties its own
#: props dict assigns two lines above the tuple.
TEMPLATE_LISTS = (
    "engine/sync.py (mutable)",
    "routes/library_ops.py (library spawn)",
    "routes/library_ops.py (refresh)",
)

#: Properties the engine reads, the library paths now carry, and the trigger spawn path
#: still does not. Recorded rather than enforced, because widening the trigger surface is
#: a feature decision and not a drift fix.
TRIGGER_OMISSIONS = (
    "blocked_description", "climb_dc", "jump_dc", "refusal_message",
    "sound_barrier",
)


@dataclass(frozen=True)
class WayProperty:
    name: str
    axis: str
    values: Optional[Sequence[str]] = None
    reads: Sequence[Read] = field(default_factory=tuple)
    notes: str = ""
    #: Set when the property is authored in the inspector but has no engine consumer, or
    #: is consumed but not honoured on some path. Surfaced loudly by the generator.
    caveat: str = ""
    #: The guarded lists this property is *required* to appear in. Empty means the
    #: checker stays silent about it, which is the honest answer for a view-layer
    #: property, an edge property, or one a handler assigns in its own props dict
    #: rather than through a copy tuple. Leaving the default while the property
    #: belongs to none of those lists produces a permanent false positive, and a gate
    #: that always cries wolf is a gate nobody runs.
    expect: Sequence[str] = field(default_factory=lambda: TEMPLATE_LISTS)


PROPERTIES: Tuple[WayProperty, ...] = (
    # ── identity ────────────────────────────────────────────────────────────────
    WayProperty(
        name="name",
        axis="identity",
        reads=(("player.py", 0, "what the player calls it"),),
        notes="Display only. Node identity is `id`, never the name.",
        expect=(),  # the spawn paths assign it from the template's own name field
    ),
    WayProperty(
        name="description",
        axis="identity",
        notes="Shown on examine and in look output while the way is solid.",
    ),
    WayProperty(
        name="pass_message",
        axis="identity",
        reads=(("movement.py", 0, "narration line on a successful traverse"),),
        notes="Overrides the generated KIND_MOVE_LINE when present.",
    ),
    WayProperty(
        name="refusal_message",
        axis="passage",
        reads=(("movement.py", 572, "what a closed way says instead of letting you through"),),
        notes="Holds until the way is actually `open`.",
    ),
    WayProperty(
        name="blocked_description",
        axis="passage",
        reads=(("movement.py", 1015, "why a blocked way is blocked"),),
        notes="Falls back to `refusal_message`.",
    ),
    WayProperty(
        name="edge_length",
        axis="identity",
        values=("20", "500"),
        notes="Graph spring length override. Not a traversal property.",
    ),
    WayProperty(
        name="cardinal",
        axis="identity",
        values=("north", "northeast", "east", "southeast", "south",
                "southwest", "west", "northwest"),
        notes="Per-side, on the connection edge. Decides map layout, not movement.",
        expect=(),  # connection-edge property, not a way-node property
    ),
    WayProperty(
        name="physics_enabled",
        axis="identity",
        notes="Turn off to freeze the node while the rest of the graph settles.",
        expect=(),  # view-layer; never library-synced
    ),
    WayProperty(
        name="distance_from_parent",
        axis="identity",
        notes="Per-node graph physics distance.",
        expect=(),  # view-layer; never library-synced
    ),
    WayProperty(
        name="image",
        axis="identity",
        notes="Thumbnail on the graph when the Images toggle is on.",
        expect=(),  # view-layer; never library-synced
    ),

    # ── passage ────────────────────────────────────────────────────────────────
    WayProperty(
        name="current_state",
        axis="passage",
        values=("open", "see_through", "closed", "locked", "blocked", "broken"),
        reads=(
            ("engine/barriers.py", 135, "declared_state, normalised"),
            ("engine/movement.py", 564, "whether a traverse is refused"),
            ("engine/barriers.py", 148, "outranked by see_through for light and sound"),
        ),
        notes="The passage ladder. Movement gates on THIS, never on see_through.",
        caveat="`broken` is offered by the inspector's State dropdown but is NOT in "
               "engine/barriers.py WAY_STATES, and an unrecognised state resolves to "
               "UNKNOWN_STATE_FALLBACK = 'open'. If that holds, a broken door is more "
               "open than an open door. Verify, then either add it to both barrier "
               "tables in ladder order or remove it from the dropdown.",
    ),
    WayProperty(
        name="one_way",
        axis="passage",
        reads=(("engine/movement.py", 558, "refuses the reverse traverse"),),
        notes="Incorporeal characters phase through it (task-309).",
    ),
    WayProperty(
        name="auto_close",
        axis="passage",
        notes="Closes behind a character who has gone through.",
    ),
    WayProperty(
        name="prevent_close",
        axis="passage",
        reads=(
            ("engine/movement.py", 1026, "character close is refused"),
            ("engine/world_compile.py", 411, "set on compiled outdoor ways"),
        ),
        notes="Author's call, not the compiler's default. The state can then only be "
              "changed by triggers. An outdoor way carries it because you cannot close "
              "a road into a forest by hand. `requires: crawl/climb/jump` is always "
              "uncloseable independently of this.",
    ),
    WayProperty(
        name="needs_open",
        axis="passage",
        notes="{enabled, skill, dc}. On a successful roll the way auto-sets "
              "current_state to 'open' and fires on_open triggers "
              "(engine/movement.py:582-600). This is how a closed, see-through wall "
              "becomes walkable — the 'break the glass' case.",
    ),
    WayProperty(
        name="requires",
        axis="verb",
        values=("", "crawl", "climb", "jump"),
        reads=(
            ("engine/movement.py", 462, "verb gate; 'go' auto-converts to crawl"),
            ("engine/movement.py", 542, "Athletics roll against <requires>_dc"),
            ("engine/movement.py", 1021, "open/close refused — an open passage"),
        ),
        notes="crawl/climb/jump ways are always uncloseable. Failed climb and jump "
              "rolls fire on_fail_climb / on_fail_jump triggers.",
    ),
    WayProperty(
        name="climb_dc",
        axis="verb",
        notes="Athletics DC when requires='climb'. Read as f'{requires}_dc', default 12.",
    ),
    WayProperty(
        name="jump_dc",
        axis="verb",
        notes="Athletics DC when requires='jump'. Read as f'{requires}_dc', default 12.",
    ),
    WayProperty(
        name="cost",
        axis="passage",
        notes="{time, energy}. 'time' is a DURATION HINT for a future stateful-action "
              "system, not per-action clock advancement — crawl/climb/jump do NOT "
              "scale costs today (task-187).",
    ),

    # ── transparency ───────────────────────────────────────────────────────────
    WayProperty(
        name="see_through",
        axis="transparency",
        reads=(
            ("engine/barriers.py", 148, "way_state returns see_through, outranking state"),
            ("engine/barriers.py", 44, "sound barrier 0.75 vs open 0.5"),
            ("engine/barriers.py", 62, "light transmission 0.75 vs open 1.0"),
            ("engine/beyond_visibility.py", 54, "line of sight continues through"),
            ("engine/area_description.py", 647, "peek-through text on examine"),
            ("engine/awareness.py", 159, "a quieter channel than open, louder than solid"),
            ("static/js/agent/turn-feed.js", 88, "a distinct sound cue"),
        ),
        notes="The single transparency axis. Independent of current_state, which is why "
              "all four combinations of walkable/see-through are expressible: "
              "`closed` + see_through is a window, `open` + see_through is a glass "
              "door, `open` + prevent_close + see_through is an archway or trail.",
        caveat="engine/world_compile.py _mint_way hardcodes see_through=True on EVERY "
               "way it mints, so every painted door is currently glazed. Separate task.",
    ),
    WayProperty(
        name="visible_in_direction",
        axis="transparency",
        reads=(("engine/area_description.py", 723, "the 'what you see beyond' text"),),
        notes="Per-side, on the connection edge. Requires see_through to be seen. "
              "The auto-generated peek-through is NOT shown for see_through ways.",
        expect=(),  # connection-edge property, not a way-node property
    ),
    WayProperty(
        name="sound_barrier",
        axis="transparency",
        notes="Per-door override, applied while the way is solid "
              "(closed/locked/blocked only). Blank = the engine-config default.",
    ),
    WayProperty(
        name="insulation",
        axis="transparency",
        reads=(("engine/environment_propagation.py", 78,
                "multiplies the heat rate through this way"),),
        notes="A float multiplier on heat transfer across the way, default 1.0. A "
              "thick curtain or a shut door is how a cold room stays cold.",
        caveat="Was honored by engine/effect_handlers/ways.py alone; the library "
               "spawn, the refresh map and engine/sync.py omitted it, so a "
               "library-spawned way silently lost it. Fixed by task-659.",
    ),

    # ── size ───────────────────────────────────────────────────────────────────
    WayProperty(
        name="max_size",
        axis="size",
        values=("tiny", "small", "normal", "huge", "giant", "titanic"),
        reads=(("engine/movement.py", 469, "two tiers over is blocked; one over crawls"),),
        notes="SIZE_TIERS is the whole model — engine/size.py:10 states there is no "
              "height or girth property. Carrying at >= 50% capacity adds one tier "
              "before the comparison (task-202), so a loaded character can be locked "
              "out of a gap they walked through unloaded.",
    ),
    WayProperty(
        name="size",
        axis="size",
        expect=(),  # read off the character, never synced onto a way
        notes="On the CHARACTER, not the way (task-605). Read by way max_size gating "
              "and by per-area occupancy (task-653). Falls back to a `size_*` trait "
              "for hand-authored characters; the property must not default to 'normal' "
              "or it would silently outrank every trait and break the gate.",
    ),

    # ── authoring ──────────────────────────────────────────────────────────────
    WayProperty(
        name="tags",
        axis="authoring",
        notes="Identity matching; does not affect traversal.",
    ),
    WayProperty(
        name="parameters",
        axis="authoring",
        notes="{param:<key>} substitution in descriptions and trigger messages.",
    ),
    WayProperty(
        name="aliases",
        axis="authoring",
        notes="Other names that target this in commands.",
    ),
    WayProperty(
        name="triggers",
        axis="authoring",
        notes="on_open, on_fail_climb, on_fail_jump, requires_open, and the rest.",
        expect=(),  # refresh handles triggers on its own rebuild path, not via prop_map
    ),
)


# ── the hand-maintained lists this guards ──────────────────────────────────────
# Each is (label, path, start marker, end marker). The keys are the snake_case string
# literals between the markers, which is deliberately crude: it must keep working when
# the surrounding code is refactored, and the whole point is to notice the list changed.
SPAWN_LISTS = (
    ("engine/sync.py (mutable)",
     "engine/sync.py", 'registry="ways.json",', 'guess="name"', None),
    ("routes/library_ops.py (library spawn)",
     "routes/library_ops.py", 'for k in ("current_state", "description"',
     'props["area_from"]', None),
    ("engine/effect_handlers/ways.py (trigger spawn)",
     "engine/effect_handlers/ways.py", 'for key in ("see_through", "tags"',
     "if one_way:", None),
    # `prop_map = {` occurs twice — items (line ~808, carrying `uses`/`weight`/`equip_slots`)
    # and ways (line ~911). The start marker includes the map's own first line so the
    # way one is selected deterministically rather than by whichever comes first.
    ("routes/library_ops.py (refresh)",
     "routes/library_ops.py",
     "prop_map = {\n            'description': 'description', 'current_state': 'current_state',",
     "if section_key in sections and prop_key not in locked:", None),
)


def by_name():
    return {p.name: p for p in PROPERTIES}