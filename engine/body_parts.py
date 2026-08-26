"""Body-part taxonomy — single fixed catalog (task-253, Flat + zoned).

The engine's body-part system is ONE flat list of region IDs. Coarse injury
regions (head, torso, arms, ...) also act as parents for nested erogenous
zones (face, lips, nipple_left, genitals, ...). Every region carries
metadata consumed by both pipelines:

- ``zone`` — ``"injury"``, ``"erogenous"`` or ``"both"`` (a region that
  matters for combat AND intimacy).
- ``parent`` — the enclosing coarse region (``nipple_left`` → ``breast_left``
  → ``torso``). Injury targeting on a zone resolves up to the nearest
  injury-capable ancestor.
- ``slots`` — the paperdoll equipment slots whose outer layers cover this
  region. Accessibility/coverage checks read these.
- ``base_sensitivity`` — default erogenous sensitivity (0-1+), the value
  ``body_state[region]["sensitivity"]`` starts from.

Body parts are NOT graph nodes: ``Player.body_state`` (a flat dict keyed by
region id) holds quick numeric lookups, and region-scoped state that needs
durations/stacking lives as condition instances with a ``body_part`` field
(see ``data/library/conditions/injured.json`` / ``bleeding.json``).
"""

#: Coverage value at/above which an outer clothing layer blocks direct skin
#: contact (injury applied to the region, direct erogenous touch, etc.).
COVERAGE_EXPOSED_THRESHOLD = 0.8

#: Damage needed before a hit to a region starts causing injury.
INJURY_DAMAGE_THRESHOLD = 5

#: Damage needed before a hit risks starting bleeding as well.
BLEEDING_DAMAGE_THRESHOLD = 10

BODY_REGIONS = {
    # --- Coarse injury regions -------------------------------------------------
    "head": {
        "name": "Head", "zone": "both", "parent": None,
        "slots": ["head"], "base_sensitivity": 0.2,
        "aliases": ["skull", "cranium", "forehead", "temple"],
    },
    "neck": {
        "name": "Neck", "zone": "both", "parent": None,
        "slots": ["neck"], "base_sensitivity": 0.4,
        "aliases": ["throat", "nape", "collarbone"],
    },
    "torso": {
        "name": "Torso", "zone": "both", "parent": None,
        "slots": ["torso"], "base_sensitivity": 0.3,
        "aliases": ["chest", "belly", "stomach", "abdomen", "ribs", "waist",
                    "pelvis", "hip", "hips", "side"],
    },
    "back": {
        "name": "Back", "zone": "injury", "parent": None,
        "slots": ["back"], "base_sensitivity": 0.2,
        "aliases": ["spine", "shoulders", "shoulder blades"],
    },
    "arm_left": {
        "name": "Left Arm", "zone": "injury", "parent": None,
        "slots": ["arms"], "base_sensitivity": 0.3,
        "aliases": ["left arm", "left upper arm", "left forearm"],
    },
    "arm_right": {
        "name": "Right Arm", "zone": "injury", "parent": None,
        "slots": ["arms"], "base_sensitivity": 0.3,
        "aliases": ["right arm", "right upper arm", "right forearm"],
    },
    "hand_left": {
        "name": "Left Hand", "zone": "injury", "parent": "arm_left",
        "slots": ["hands"], "base_sensitivity": 0.4,
        "aliases": ["left hand", "left palm", "left wrist", "left fingers"],
    },
    "hand_right": {
        "name": "Right Hand", "zone": "injury", "parent": "arm_right",
        "slots": ["hands"], "base_sensitivity": 0.4,
        "aliases": ["right hand", "right palm", "right wrist", "right fingers"],
    },
    "leg_left": {
        "name": "Left Leg", "zone": "injury", "parent": None,
        "slots": ["waist", "feet"], "base_sensitivity": 0.3,
        "aliases": ["left leg", "left thigh", "left knee", "left shin",
                    "left calf"],
    },
    "leg_right": {
        "name": "Right Leg", "zone": "injury", "parent": None,
        "slots": ["waist", "feet"], "base_sensitivity": 0.3,
        "aliases": ["right leg", "right thigh", "right knee", "right shin",
                    "right calf"],
    },
    "foot_left": {
        "name": "Left Foot", "zone": "injury", "parent": "leg_left",
        "slots": ["feet"], "base_sensitivity": 0.2,
        "aliases": ["left foot", "left ankle", "left toes", "left sole"],
    },
    "foot_right": {
        "name": "Right Foot", "zone": "injury", "parent": "leg_right",
        "slots": ["feet"], "base_sensitivity": 0.2,
        "aliases": ["right foot", "right ankle", "right toes", "right sole"],
    },
    # --- Erogenous zones (nested under coarse regions) -------------------------
    "face": {
        "name": "Face", "zone": "erogenous", "parent": "head",
        "slots": ["head"], "base_sensitivity": 0.5,
        "aliases": ["facial", "jaw", "chin", "ears"],
    },
    "cheeks": {
        "name": "Cheeks", "zone": "erogenous", "parent": "face",
        "slots": ["head"], "base_sensitivity": 0.6,
        "aliases": ["cheek"],
    },
    "lips": {
        "name": "Lips", "zone": "erogenous", "parent": "face",
        "slots": ["head"], "base_sensitivity": 0.8,
        "aliases": ["lip", "mouth", "kiss"],
    },
    "breast_left": {
        "name": "Left Breast", "zone": "erogenous", "parent": "torso",
        "slots": ["torso"], "base_sensitivity": 0.6,
        "aliases": ["left breast", "left chest", "left boob"],
    },
    "breast_right": {
        "name": "Right Breast", "zone": "erogenous", "parent": "torso",
        "slots": ["torso"], "base_sensitivity": 0.6,
        "aliases": ["right breast", "right chest", "right boob"],
    },
    "nipple_left": {
        "name": "Left Nipple", "zone": "erogenous", "parent": "breast_left",
        "slots": ["torso"], "base_sensitivity": 0.9,
        "aliases": ["left nipple"],
    },
    "nipple_right": {
        "name": "Right Nipple", "zone": "erogenous", "parent": "breast_right",
        "slots": ["torso"], "base_sensitivity": 0.7,
        "aliases": ["right nipple"],
    },
    "genitals": {
        "name": "Genitals", "zone": "erogenous", "parent": "torso",
        "slots": ["waist"], "base_sensitivity": 0.8,
        "aliases": ["groin", "crotch", "penis", "cock", "vagina", "pussy",
                    "vulva", "clit", "clitoris", "cunt", "dick"],
    },
    "balls": {
        "name": "Balls", "zone": "erogenous", "parent": "genitals",
        "slots": ["waist"], "base_sensitivity": 0.7,
        "aliases": ["testicles", "testes", "scrotum", "nuts", "balls"],
    },
}

#: Region ids that resolve a ``where`` targeting an erogenous zone down to an
#: injury-capable ancestor (a hit on the nipple injures the torso).
INJURY_CAPABLE = {r for r, d in BODY_REGIONS.items() if d["zone"] != "erogenous"}


def region_definition(region_id):
    """Return the metadata dict for a region id (empty dict if unknown)."""
    return BODY_REGIONS.get(region_id, {})


def resolve_region(where):
    """Resolve a free-text ``where`` string to a canonical region id.

    Matches region ids, aliases, and ``left/right`` prefixed forms
    (``"left arm"`` → ``arm_left``, ``"nipple"`` → ``nipple_left``).
    Returns ``None`` when nothing matches.
    """
    if not where:
        return None
    text = str(where).strip().lower()
    if not text:
        return None

    # Exact canonical id.
    if text in BODY_REGIONS:
        return text

    # Alias lookup.
    for region_id, meta in BODY_REGIONS.items():
        if text in meta.get("aliases", []):
            return region_id

    # Left/right prefix — "left arm" → arm_left, "right nipple" → nipple_right.
    for side, suffix in (("left ", "_left"), ("right ", "_right")):
        if text.startswith(side):
            base = text[len(side):]
            candidate = base + suffix
            if candidate in BODY_REGIONS:
                return candidate
            # "left nipple" where only "nipple" is an alias → apply side to the
            # resolved base region.
            base_id = resolve_region(base)
            if base_id and base_id in BODY_REGIONS:
                side_id = base_id + suffix
                if side_id in BODY_REGIONS:
                    return side_id
    return None


def injury_region(region_id):
    """Nearest injury-capable region for a targeting resolution.

    An erogenous zone resolves up through its parent chain to the enclosing
    coarse region (``nipple_left`` → ``torso``). Injury regions return
    themselves. Unknown ids return ``None``.
    """
    current = region_id
    seen = set()
    while current and current not in seen:
        seen.add(current)
        if current in INJURY_CAPABLE:
            return current
        current = BODY_REGIONS.get(current, {}).get("parent")
    return None


def region_chain(region_id):
    """Region id + every enclosing ancestor, outermost first.

    ``nipple_left`` → ``["torso", "nipple_left"]``.
    """
    chain = []
    current = region_id
    seen = set()
    while current and current not in seen:
        seen.add(current)
        chain.append(current)
        current = BODY_REGIONS.get(current, {}).get("parent")
    chain.reverse()
    return chain


def coverage_slots(region_id):
    """All equipment slots whose outer layer covers a region (incl. parents)."""
    slots = []
    for r in region_chain(region_id):
        for slot in BODY_REGIONS.get(r, {}).get("slots", []):
            if slot not in slots:
                slots.append(slot)
    return slots


def is_exposed(player, region_id, graph, threshold=COVERAGE_EXPOSED_THRESHOLD):
    """True if a region is NOT covered by high-coverage clothing/armor.

    Reads the OUTER layer of each covering equip slot: an item whose
    ``coverage`` property is at/above *threshold* counts as covering the
    region (blocks direct skin contact → no injury applied, no direct touch).
    Outer layer = last item in ``player.equipped[slot]`` (stack order is
    innermost → outermost). An unknown region or empty slots = exposed.
    """
    slots = coverage_slots(region_id)
    for slot in slots:
        stack = (player.equipped or {}).get(slot) or []
        outer_ids = [i for i in stack if i and not str(i).startswith("__multi_slot")]
        if not outer_ids:
            continue
        outer_id = outer_ids[-1]
        node = graph.get_node(outer_id) if graph else None
        if node is None:
            continue
        coverage = float(node.properties.get("coverage", 0.0) or 0.0)
        if coverage >= threshold:
            return False
    return True


def default_body_state():
    """Per-region numeric lookup dict for a fresh Player.

    Every region gets a ``sensitivity`` seeded from the catalog. Injury state
    is NOT stored here — it lives as ``body_part``-tagged condition instances
    (``injured``/``bleeding``), the single source of truth. Erogenous-only
    numeric fields (hardness, wetness, flush, ...) land here in task-207.
    """
    return {
        region_id: {
            "sensitivity": float(meta.get("base_sensitivity", 0.5)),
        }
        for region_id, meta in BODY_REGIONS.items()
    }


def region_injury_level(damage):
    """Map incoming damage to an ``injured`` level (1 light, 2 moderate, 3 severe)."""
    if damage < INJURY_DAMAGE_THRESHOLD:
        return 0
    if damage >= 12:
        return 3
    if damage >= 8:
        return 2
    return 1


#: d20 hit-location table for un-aimed attacks (task-253). Bigger targets get
#: more faces: torso (5 faces), legs (3), arms (2), head (2), then the small
#: extremities. Each (low, high) pair maps a contiguous d20 range to a region.
HIT_LOCATION_TABLE = [
    ((1, 2), "head"),
    ((3, 3), "neck"),
    ((4, 5), "arm_left"),
    ((6, 7), "arm_right"),
    ((8, 12), "torso"),
    ((13, 13), "back"),
    ((14, 14), "hand_left"),
    ((15, 15), "hand_right"),
    ((16, 17), "leg_left"),
    ((18, 18), "leg_right"),
    ((19, 19), "foot_left"),
    ((20, 20), "foot_right"),
]


def roll_hit_location(d20_roll=None):
    """Pick a region for an un-aimed attack hit.

    Pass the attacker's d20 roll (1-20) to use a deterministic table lookup,
    or omit it to roll fresh. Returns a region id (always valid).
    """
    import random
    if d20_roll is None:
        d20_roll = random.randint(1, 20)
    for (low, high), region_id in HIT_LOCATION_TABLE:
        if low <= d20_roll <= high:
            return region_id
    return "torso"