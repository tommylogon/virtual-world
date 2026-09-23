# player.py
import re
import time
import uuid

from vital_rates import BASELINE_DECAY, BLADDER_FILL

MEMORY_LIMIT_KEY = "memory.max_per_character"


def _memory_limit() -> int:
    """Configured per-character memory cap; 0 or unset means keep everything.

    Imported lazily: player.py is reached through ``engine/__init__.py``, so a
    module-level ``from engine.runtime_config import config`` would re-enter the
    package while it is still initialising.
    """
    try:
        from engine.runtime_config import config
        return max(0, int(config.get(MEMORY_LIMIT_KEY, 0) or 0))
    except Exception:
        return 0


class Player:
    def sync_vitals_with_tags(self):
        """Add or remove Mana vital based on 'magic' tag."""
        if "magic" in self.tags:
            if "Mana" not in self.vitals:
                self.vitals["Mana"] = 100
            if "Mana" not in self.decay_rates:
                self.decay_rates["Mana"] = 0
        else:
            self.vitals.pop("Mana", None)
            self.decay_rates.pop("Mana", None)

    def sync_pleasure_vitals(self, enabled: bool):
        """task-206/207: add or strip the pleasure vitals with the toggle.

        Arousal/Stimulation/Pleasure only exist while ``mature_content`` is on,
        so the base game never shows them. Decay rates match the engine
        baseline (slow Arousal, medium Stimulation, fast Pleasure).
        """
        if enabled:
            if "Arousal" not in self.vitals:
                self.vitals["Arousal"] = 0
            if "Stimulation" not in self.vitals:
                self.vitals["Stimulation"] = 0
            if "Pleasure" not in self.vitals:
                self.vitals["Pleasure"] = 0
            self.decay_rates.setdefault("Arousal", 1)
            self.decay_rates.setdefault("Stimulation", 2)
            self.decay_rates.setdefault("Pleasure", 3)
        else:
            self.vitals.pop("Arousal", None)
            self.vitals.pop("Stimulation", None)
            self.vitals.pop("Pleasure", None)
            for vital in ("Arousal", "Stimulation", "Pleasure"):
                self.decay_rates.pop(vital, None)
            # The arousal state conditions are meaningless without the vitals.
            # The id set is data (each condition's `mature` flag), not a list here.
            for cid in MATURE_CONDITIONS:
                self.conditions.pop(cid, None)

    @staticmethod
    def node_id_for(name: str) -> str:
        """The graph node id for a character named ``name``.

        The single definition of the convention — `PlayerManager.get_player_node_id`
        delegates here, and `Player.node_id` is derived from it at construction.
        Observation memories key a subject by node id (task-403) and relationships
        key by *name*, so anything that needs to cross between the two (e.g. the
        meeting novelty grant, task-434) must use this rather than re-deriving
        the string, which is how the two would drift.
        """
        return f"player_{name}".replace(" ", "_")

    def __init__(self, name="Traveler"):
        self.name = name
        # Derived, not persisted: it must follow a rename the same way the graph
        # node does, and the deserializer builds Players without going through
        # PlayerManager.add_player.
        self.node_id = self.node_id_for(name)
        # Game minutes per tick, refreshed by the tick loop. Novelty windows are
        # authored in game minutes but compared against tick deltas, so the
        # conversion has to happen somewhere that knows both.
        self.minutes_per_tick = 1.0
        # Authored daily schedule (task-409): [{start:"HH:MM", activity, area,
        # fallback}]. Empty means "no schedule" — pure need-driven behaviour,
        # which is what every character did before schedules existed.
        self.schedule = []
        # task-316 foundation: stable opaque identity. Display names stay the
        # addressing surface (same-named characters are allowed); the id is the
        # anchor the full id-backed re-key will use. 8 hex chars, survives
        # save/load and library hydration.
        import uuid as _uuid
        self.id = _uuid.uuid4().hex[:8]
        # Free-form description/personality text for this character
        self.personality = ""
        # Base physical description (naked/baseline appearance — what they look like with nothing on)
        self.base_description = ""
        # Current outward-facing description (auto-generated from base + equipment, or manually set)
        self.description = ""
        # Explicit label used until another character meets this one. When empty,
        # a label is derived from `description` (task-154).
        self.unknown_name = ""
        
        # D&D Core Stats
        self.stats = {
            "STR": 10, "DEX": 10, "CON": 10,
            "INT": 10, "WIS": 10, "CHA": 10
        }
        
        # Vitals & Needs (Max 100)
        # Hunger/Thirst are DRIVES (task-337 flip): 0 = fed/hydrated,
        # 100 = starving/dehydrated. Spawn satisfied, they fill over time.
        self.vitals = {
            "HP": 100, "Max_HP": 100,
            "Hunger": 0, "Thirst": 0,
            "Hygiene": 100, "Energy": 100,
            "Social": 100,
            "Bladder": 0, "Sanity": 100,
            "Entertainment": 100, "Temperature": 37.0
        }

        # Per-character decay rate overrides. Defaults mirror
        # vital_rates.BASELINE_DECAY (the single source of truth) — real-world
        # per-minute rates: from a FULL meter a healthy adult reaches the
        # starvation edge at ~3 weeks, the dehydration edge at ~3 days, and
        # Energy empties over a ~16h waking day. Sub-1 rates rely on the
        # fractional accumulator in TickManager.tick_turn(). Bladder has its
        # own thirst-modulated fill in tick_manager. Goblins get the faster
        # `high_metabolism` trait.
        self.decay_rates = {**BASELINE_DECAY, "Bladder": BLADDER_FILL}

        # Per-body-part numeric state (task-253 body-part taxonomy). Flat dict
        # keyed by region id from engine/body_parts.py: each region has a base
        # `sensitivity` and an `injury` slot (None until combat/conditions set
        # one). Erogenous state (hardness, wetness, flush, ...) is modeled as
        # conditions (nipple_hard/blushing/wetness), not numeric fields here
        # (task-207, descoped).
        from engine.body_parts import default_body_state
        self.body_state = default_body_state()
        
        # Basic Skills
        # The full skill vocabulary (task-474). Every skill is on the sheet, so a
        # setting or a character can grant/train any of them; skills a setting
        # does not use simply sit at 0. The six "adventuring basics" start at 1.
        self.skills = {
            "Athletics": 1, "Acrobatics": 1,
            "Stealth": 1, "Perception": 1,
            "Survival": 1, "Persuasion": 1,
            "Animal Handling": 0, "Arcana": 0, "Deception": 0,
            "History": 0, "Insight": 0, "Intimidation": 0,
            "Investigation": 0, "Medicine": 0, "Nature": 0,
            "Performance": 0, "Religion": 0, "Sleight of Hand": 0,
        }
        # Crafting (task-2): recipe names this character has discovered
        # (discoverable recipes after the first successful craft).
        self.crafting_known = []
        # Traits: mapping trait_id -> parameter value.
        # Boolean traits use True. Parameterized traits use a string (e.g. {"allergic": "pollen"}).
        # Example: {"dark_vision": True, "hardy": True, "glutton": True}
        self.traits = {}
        # Tags: identity markers for this character, checked by items/triggers/conditions.
        # Examples: ["vampire", "faction:guard", "synthetic", "nobility"]
        self.tags = []
        # Interest tags: what this character pays attention to in a room.
        # Items matching these tags (or their keywords) surface in the prompt's
        # "Items that catch your attention" list before other items.
        # Examples: ["magic", "food", "weapon", "documents"]
        self.interest_tags = []
        # Things this character is afraid of (task-469). Mirrors interest_tags:
        # meeting a co-located character/item or an area whose tags intersect
        # these applies the source-gated `frightened` condition. Guards vs
        # farmers vs goblins differ purely by these lists, so no group needs a
        # global "hostile" flag that makes it panic at its own kind.
        self.fear_tags = []
        # An active soak order (task-481): declared on this human's turn ("go
        # west for an hour"), it makes the character run on a policy each turn
        # until the span is spent or something promotes them back. None = normal
        # attended play. Transient: deliberately not serialized.
        self.soak_order = None
        # Conditions system: {condition_id: [instance, instance, ...]} — MULTIPLE
        # concurrent instances per condition (5 vials of poison = 5 `poisoned`
        # instances). Each instance: {duration, source, level, periodic, ends_on,
        # symptoms, known} where the optional fields override the catalog default.
        # duration = game minutes remaining (None = until countered/removed).
        # Scaled to the tick length by engine/conditions.py:process_tick.
        self.conditions = {"awake": [{"duration": None, "source": None, "level": 0}]}
        # Track discovered exits: set of (area_name, direction) tuples
        self.discovered_exits = set()
        # Way knowledge learned the hard way (task-333): {(area_name, direction):
        # set of aspect strings} — 'locked', 'blocked', 'needs_force'. The turn
        # panel only reveals these once discovered (examine or a failed go).
        self.known_way_aspects = {}
        # Track areas the character has visited (for Entertainment novelty bonus)
        self.visited_areas = set()
        # Track items the character has discovered (for Entertainment novelty bonus)
        self.discovered_items = set()
        # AUTHORED knowledge (not runtime discovery): entity ids this character
        # knows from the start — way ids ("way_secret_passage"), item ids
        # ("item_old_key"), player names ("miki doki"), area names or ids.
        # Seeded from the character data's `known` list; the inspector's
        # "Known by" control edits it. Runtime discovery still works on top.
        self.known = []
        # Current area location (for multi-player support)
        self.current_area = None
        # Recent speech heard: list of dicts {speaker, text, tick, timestamp}
        self.recent_hearing = []
        # === SIMPLE NPC (no LLM) ===
        self.simple_npc = False
        # Human-driven flag: autonomy False = a human player drives this
        # character (the browser agent engine skips it and surfaces the human
        # turn composer). Persisted so it survives reloads/saves.
        self.autonomy = True
        self.npc_behavior = "wander"  # wander, flee, stationary
        self.npc_action_interval = 3  # act every N ticks
        self.npc_state = "idle"        # behavior state machine
        self.state_enter_tick = 0       # tick when npc_state was entered
        self.behaviors = []             # list of behavior definitions
        self.patrol_route = []          # ordered area names for patrol mode
        self.patrol_index = 0           # current index in patrol_route

        # === ACTIVITY SYSTEM (task-131) ===
        # What the character is *doing* across turns. Purely descriptive —
        # mechanical gating comes from player.state + conditions.
        #   None | {"type": str, "started_at_tick": int, "target_item": str|None,
        #           "duration_ticks": int|None, "elapsed_ticks": int, "visible": bool}
        # Types: sleeping, resting, waiting, meditating, bathing, sitting, lying down
        self.activity = None

        # === EMOTION SYSTEM ===
        # Current emotional state from the allowed set:
        # neutral, happy, sad, angry, afraid, surprised, disgusted
        self.emotion = "neutral"
        # How strongly the current emotion is felt (0.0 to 1.0)
        # Higher = more influence on behavior
        self.emotion_intensity = 0.0
        # Multi-dimensional affect map (task-96): {dim: 0-100}, lazily
        # initialized to baselines via emotions_map(). None = untouched.
        self._emotions = None

        # === HIDE / SEEK SYSTEM (Phase 1 edge-based hiding) ===
        # Fast lookup flag: True when this character is hidden in/behind/under
        # something. The edge (hidden/relation) is the source of truth; this
        # boolean mirrors it for quick condition checks.
        self.hidden = False
        # Arbitrary flags set by trigger effects (set_flag action).
        # Examples: "alert", "fleeing", "guarding", "distracted".
        # Dict of flag_name -> value (usually True). Checked by character_has_flag
        # condition (if added later) or simple `if "alert" in player.flags`.
        self.flags = {}

        # === SOCIAL RELATIONSHIPS ===
        # Dict of {other_player_name: {"closeness": -100-100, "last_interaction_tick": int, "interaction_count": int}}
        # closeness: -100 = sworn enemy, -50 = rival, 0 = neutral, 50 = friend, 100 = inseparable
        self.relationships = {}

        # === EQUIPMENT ===
        # Slots mapped to lists of item node IDs. Stack order = wear order.
        # Index 0 = innermost (closest to skin), last index = outermost.
        self.equipped = {
            "head": [], "neck": [], "torso": [], "arms": [],
            "hands": [], "legs": [], "feet": [], "back": [],
            "waist": [], "accessory": [],
            "hand_left": [], "hand_right": []
        }

        # === MEMORY STORE ===
        # List of {text, tick, timestamp, importance (1-10), type, embedding (optional)}
        self.memories = []
        # subject graph id -> id of the live observation memory about it
        # (engine/observation.py). Takes "which memory is about this subject?"
        # out of the memory list, so a subject does not have to be found by
        # scanning for it, and it is how a character knows what it has and has
        # not seen.
        self.memory_index = {}

        # === TRACE (objective history) ===
        # Bounded list of plain dicts written by engine.trace — the mechanical
        # "what happened and why" record. Distinct from subjective memories;
        # see docs/design/trace-format.md.
        self.trace_log = []

        # === SIMULATION FIDELITY (task-399) ===
        # simulation_mode is a runtime fidelity, orthogonal to
        # controller/autonomy/simple_npc: "active" runs the normal LLM/simple
        # loop, "background" runs the deterministic survival runner instead.
        # next_due_tick is when the background runner should next consider
        # them, so background work is event-scheduled, not a per-tick scan.
        self.simulation_mode = "active"
        self.next_due_tick = 0

        self.sync_vitals_with_tags()

    # ── Backward-compatible state property ──────────────────────────
    @property
    def state(self):
        """Return the most significant condition for backward compat."""
        return get_state(self)

    @state.setter
    def state(self, value):
        """Set a state — ADDS the condition without wiping others."""
        set_state(self, value)

    def has_condition(self, condition: str) -> bool:
        return condition_has_condition(self, condition)

    def add_condition(self, condition: str, duration=None, source=None, level=None,
                      periodic=None, extra_conditions=None, ends_on=None,
                      symptoms=None, known=None, source_type=None, overrides=None):
        """Apply a condition instance (or bundle)."""
        return condition_add_condition(self, condition, duration=duration, source=source,
                                       level=level, periodic=periodic,
                                       extra_conditions=extra_conditions, ends_on=ends_on,
                                       symptoms=symptoms, known=known,
                                       source_type=source_type, overrides=overrides)

    def remove_condition(self, condition: str):
        condition_remove_condition(self, condition)

    def end_instances(self, action: str):
        """Remove every instance whose effective ends_on includes *action*.

        Returns the removed ``(condition_id, source)`` pairs.
        """
        return condition_end_instances(self, action)

    @property
    def state_timer(self) -> int:
        """Backward-compat: ticks remaining on the current state condition."""
        return get_state_timer(self)

    @state_timer.setter
    def state_timer(self, value):
        """Backward-compat: set the current state condition's countdown duration."""
        set_state_timer(self, value)

    def load_conditions(self, payload):
        """Replace conditions from serialized data."""
        condition_load_conditions(self, payload)

    def set_emotion(self, new_emotion: str, intensity: float = 0.3):
        """Set the character's emotion with the given intensity."""
        allowed = ["neutral", "happy", "sad", "angry", "afraid", "surprised", "disgusted"]
        if new_emotion not in allowed:
            raise ValueError(f"Invalid emotion '{new_emotion}'. Must be one of {allowed}")
        self.emotion = new_emotion
        self.emotion_intensity = max(0.0, min(1.0, intensity))

    # === Multi-dimensional affect (task-96) ===

    def emotions_map(self) -> dict:
        """The full affect map, lazily initialized to baselines."""
        from engine import emotion as _emotion
        if self._emotions is None:
            self._emotions = _emotion.baseline()
        return self._emotions

    def spike_emotion(self, emotion: str, delta: float) -> None:
        """Nudge one affect dimension (clamped 0-100). Unknown dims ignored."""
        from engine import emotion as _emotion
        _emotion.spike(self.emotions_map(), emotion, delta)

    #: Emotion-label -> (derived dimension, sign factor). The recipient decides
    #: how a line landed (label + intensity 1-10); we map it to a dimension
    #: delta and record it as an experience (task-350).
    _FELT_TO_DIM = {
        "affectionate": ("trust", +1.0),
        "happy": ("trust", +0.5),
        "grateful": ("trust", +0.7),
        "afraid": ("fear", +1.0),
        "frightened": ("fear", +1.0),
        "disgusted": ("disgust", +1.0),
        "repulsed": ("disgust", +1.0),
        "angry": ("trust", -0.8),
        "envious": ("disgust", -0.6),
        "distrustful": ("trust", -1.0),
        "uneasy": ("fear", +0.5),
    }

    def felt_toward(self, other_name: str, label: str, intensity: float, tick: int) -> bool:
        """Record a recipient-decided feeling *toward* another character.

        This is the single LLM to experience bridge. The recipient (the person
        the line landed on) names how they feel about other_name (label + 1-10),
        the ENGINE maps it to a dimension delta and writes a tagged memory, and
        engine.derive later folds it into the derived profile (consent/trust/
        fear) so mechanics can gate on it. Returns True when a memory was written.
        """
        key = str(label or "").strip().lower()
        if key not in self._FELT_TO_DIM:
            return False
        try:
            intensity = max(1.0, min(10.0, float(intensity)))
        except (TypeError, ValueError):
            return False
        # Ensure a relationship record exists so this person shows up in
        # derived profiles and later name-learning can clear the stranger flag.
        from engine.relationships import ensure_relationship
        rel, created = ensure_relationship(self, other_name, tick)
        if created:
            rel["first_sighting"] = True
        dim, factor = self._FELT_TO_DIM[key]
        # Per-point magnitude: a 10/10 feeling lands a tag of ~2.5, which the
        # reducer multiplies by importance, leaving a real mark on the profile.
        mag = intensity / 4.0
        importance = max(3, round(intensity))
        rel_key = self._rel_key(other_name)
        from engine.relationships import display_name as _rel_display
        tags = ["rel:" + rel_key, dim + ":" + str(round(factor * mag, 2))]
        self.add_memory(
            "I felt " + label + " toward " + _rel_display(self, other_name, rel_key) + ".", tick=tick,
            importance=importance, memory_type="emotion", tags=tags, source="felt",
        )
        # Also nudge the live affect map so the mood reads this turn.
        if label in self.emotions_map():
            self.spike_emotion(label, intensity)
        return True

    def decay_emotions(self) -> None:
        """Per-tick drift of all dimensions toward baseline (tick_manager hook)."""
        from engine import emotion as _emotion
        if self._emotions is not None:
            _emotion.decay(self._emotions)

    def emotions_description(self) -> str:
        """First-person mood paragraph for prompts ('' when near-neutral).

        task-142: when no explicit emotion has been set recently (the affect
        map is untouched, or every dimension has decayed back to baseline),
        derive a coherent mood from the character's actual vitals/state instead
        of narrating "relieved but vigilant" while shivering and starving.
        """
        from engine import emotion as _emotion
        if self._emotions is not None:
            explicit = _emotion.describe(self._emotions)
            if explicit:
                return explicit
            # Near-neutral explicit map — fall through to vitals-derived mood.
        derived = _emotion.derive_from_vitals(self.vitals, self.state)
        if derived is None:
            return ""
        return _emotion.describe(derived)

    def load_emotions(self, data) -> None:
        """Restore a stored emotion map from a scenario/save dict."""
        from engine import emotion as _emotion
        self._emotions = _emotion.normalize(data)

    def get_emotion_nl(self) -> str:
        """Return a natural language description of the current emotion state."""
        if self.emotion == "neutral" or self.emotion_intensity < 0.1:
            return ""
        WORD_MAP = [
            (0.9, "extremely "),
            (0.7, "very "),
            (0.5, "quite "),
            (0.3, "slightly "),
        ]
        word = ""
        for threshold, w in WORD_MAP:
            if self.emotion_intensity >= threshold:
                word = w
                break
        return f"{self.name} is {word}{self.emotion}."

    def update_emotion_from_outcome(self, outcome: str, tick: int):
        """Update emotion based on action outcome text heuristics."""
        lower = outcome.lower()
        
        # Success patterns
        if any(word in lower for word in ["success", "succeed", "you open", "you take", "you pick up", "works", "unlock", "reveal", "find", "you pick"]):
            self.set_emotion("happy", min(1.0, self.emotion_intensity + 0.2))
        # Damage / threat patterns
        elif any(word in lower for word in ["damage", "hit you", "strike", "slash", "hurt", "injure", "pain"]):
            if self.vitals["HP"] < 30:
                self.set_emotion("afraid", 0.7)
            else:
                self.set_emotion("angry", 0.5)
        # Fear / danger patterns
        elif any(word in lower for word in ["creepy", "scary", "frighten", "terrify", "horror", "scream", "shriek", "shadow", "ghost"]):
            self.set_emotion("afraid", 0.6)
        # Sad / loss patterns
        elif any(word in lower for word in ["sad", "loss", "dead", "kill", "die", "death", "grave"]):
            self.set_emotion("sad", 0.5)
        # Surprise patterns
        elif any(word in lower for word in ["sudden", "unexpected", "surprise", "startle", "shock", "appear", "appears"]):
            self.set_emotion("surprised", 0.4)
        # Disgust patterns
        elif any(word in lower for word in ["rotten", "decay", "smell", "stench", "disgust", "mold", "filth"]):
            self.set_emotion("disgusted", 0.4)
        # Frustration / failure patterns
        elif any(word in lower for word in ["fail", "can't", "cannot", "blocked", "locked", "stop", "refuse", "error"]):
            self.set_emotion("angry", 0.3)
        # Decay towards neutral over time
        else:
            if self.emotion_intensity > 0.1:
                self.emotion_intensity = max(0.0, self.emotion_intensity - 0.1)
            if self.emotion_intensity <= 0.1 and self.emotion != "neutral":
                self.emotion = "neutral"

    def register_first_meeting(self, other_name: str, tick: int) -> bool:
        """Register that this character has met *other_name* for the first time.

        Creates the relationship entry (closeness 0, no interaction bump) and
        grants an Entertainment novelty boost. Returns True only on first meet;
        no-op afterwards, so it is safe to call on every shared-area observation.

        The new record is stamped ``first_sighting: True`` so the character's
        identity stays hidden from prompt renderers for the rest of this turn
        (the first sighting is anonymized); the flag is cleared on the next
        shared-area encounter, which is when the name is revealed.
        """
        if self._rel_key(other_name) in self.relationships:
            return False
        from engine.relationships import ensure_relationship
        ensure_relationship(self, other_name, tick, label="")
        self.relationships[self._rel_key(other_name)]["first_sighting"] = True
        self._grant_meeting_entertainment(other_name, tick)
        return True

    def _rel_key(self, other) -> str:
        """Identity key a relationship with ``other`` is stored under (task-446)."""
        manager = getattr(self, "player_manager", None)
        if manager is not None and hasattr(manager, "relationship_key"):
            return manager.relationship_key(other)
        return str(getattr(other, "name", other) or "")

    def has_met(self, other_name: str) -> bool:
        """True when this character has met *other_name* (a relationship exists)."""
        return self._rel_key(other_name) in self.relationships

    def knows_name(self, other_name: str) -> bool:
        """True when this character has actually learned *other_name*'s name
        (heard it spoken, or read their name tag) — task-339. Recognition
        (having seen them) is NOT name knowledge."""
        rel = self.relationships.get(self._rel_key(other_name))
        return rel is not None and not rel.get("first_sighting")

    def learn_name(self, other_name: str, tick: int) -> bool:
        """Learn another character's NAME (heard it spoken / read their name
        tag) — task-339. Registers the relationship if new and clears the
        name-unknown flag. Returns True only when this was new knowledge."""
        self.register_first_meeting(other_name, tick)
        rel = self.relationships.get(self._rel_key(other_name))
        if rel is None:
            return False
        was_unknown = bool(rel.get("first_sighting"))
        if was_unknown:
            rel["first_sighting"] = False
        return was_unknown

    def learn_way_aspect(self, area_name: str, direction: str, aspect: str) -> None:
        """Record that this character discovered a way's hidden aspect
        ('locked', 'blocked', 'needs_force') — task-333 scene discovery."""
        key = (str(area_name), str(direction))
        self.known_way_aspects.setdefault(key, set()).add(str(aspect))

    def knows_way_aspect(self, area_name: str, direction: str, aspect: str) -> bool:
        """True when this character has discovered the given way aspect."""
        return str(aspect) in self.known_way_aspects.get(
            (str(area_name), str(direction)), ()
        )

    def unknown_display_name(self) -> str:
        """The label others see for this character before meeting them.

        Uses the explicit `unknown_name` when set, otherwise derives a
        description-based label (first sentence, leading article stripped).
        If the character has no usable description, falls back to a label
        derived from their tags (male/female/man/woman/girl/boy/animal),
        then to a generic "the stranger".
        """
        if getattr(self, "unknown_name", "").strip():
            return self.unknown_name.strip()
        tag_label = self._tag_unknown_name()
        if tag_label != "the stranger":
            return tag_label
        desc = (self.description or self.base_description or "").strip()
        if not desc:
            return self._tag_unknown_name()
        first_sentence = re.split(r"[.!?]", desc)[0].strip()
        first_sentence = re.sub(r"^(?:a|an|the)\s+", "", first_sentence, flags=re.IGNORECASE)
        if not first_sentence:
            return self._tag_unknown_name()
        # Pronoun-starting descriptions ("She stands bare and unadorned...") —
        # map to a person label instead of producing "the she stands...".
        m = re.match(r"^(she|he|they)\b", first_sentence, flags=re.IGNORECASE)
        if m:
            person = {"she": "woman", "he": "man", "they": "person"}[m.group(1).lower()]
            rest = first_sentence[m.end():].strip()
            if rest:
                return f"the {person} who {rest}".lower()
        return f"the {first_sentence.lower()}"

    def _tag_unknown_name(self) -> str:
        """Derive a stranger label from character tags when there's no
        description to build one from. e.g. `male` → "the man", `female` →
        "the woman", `girl` → "a girl", `boy` → "a boy", `animal` → "an
        animal". Falls back to "the stranger" when no tag matches."""
        tag_map = {
            "male": "the man",
            "man": "the man",
            "female": "the woman",
            "woman": "the woman",
            "girl": "a girl",
            "boy": "a boy",
            "child": "a child",
            "animal": "an animal",
        }
        tags = getattr(self, "tags", []) or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
        for tag in tags:
            label = tag_map.get(str(tag).strip().lower())
            if label:
                return label
        return "the stranger"

    def _grant_meeting_entertainment(self, other_name: str = "", tick: int = 0) -> int:
        """Entertainment the first time this character meets someone new.

        Routed through the shared novelty curve (task-425) keyed on the other
        character's *node id*, so meeting somebody is the **person** subject of
        the same mechanic that covers places and things.

        It both **reads and records** the observation, which is what makes it
        idempotent with perception in either order (task-434): perception records
        the character on arrival and pays, so a later meeting reads a fresh tick
        and pays nothing — and a meeting that happens first records, so a later
        perception pays nothing. This used to be a separate flat +10 that
        double-paid with the perception grant.

        Note the ordering inside: the grant reads the tick *before* the record
        refreshes it, exactly as `observe_area` computes freshness before
        refreshing.
        """
        if "Entertainment" not in self.vitals or not other_name:
            return 0
        from engine.novelty import grant
        subject = self.node_id_for(other_name)
        gained = grant(self, subject, tick)
        self.record_observation(
            subject, f"You have met {other_name}.", tick, kind="character",
            tags=["met"], importance=5,
            location=getattr(self, "current_area", "") or "",
        )
        return gained

    def update_relationship(self, other_name: str, tick: int, sentiment_change: int = 0):
        """Update relationship closeness with another character.
        sentiment_change: -20 to +20 per interaction. Range: -100 to +100.

        First meeting with a character grants an Entertainment novelty boost
        (mirrors the area-visit/item-discovery boosts in task-136).

        Goes through `engine/relationships.py` — the one writer of closeness
        (task-420), so the change carries a cause and clamps in one place.
        """
        from engine.relationships import apply_relationship_delta, ensure_relationship
        _, created = ensure_relationship(self, other_name, tick)
        if created:
            self._grant_meeting_entertainment(other_name, tick)
        apply_relationship_delta(
            self, other_name, sentiment_change, "dialogue",
            tick=tick, area_id=getattr(self, "current_area", "") or "",
        )

    #: Familiarity's damping on relationship decay. 0.15 means six prior
    #: interactions halve the rate — shared history should not evaporate.
    RELATIONSHIP_DECAY_FAMILIARITY = 0.15

    def decay_relationships(self, elapsed_days: float, per_day: float) -> int:
        """Drift closeness toward 0 for relationships left unmaintained.

        Deliberately safe on authored data: the step can never cross zero
        (strength protects itself), shared history damps the rate through
        `interaction_count`, and an authored `label` ("my brother") is a
        declaration rather than a measurement, so it is never touched — only the
        computed closeness moves.

        Sub-1 daily steps accumulate per relationship the way vitals do, or a
        0.5/day rate would round to nothing every day.

        Returns the number of relationships that moved.
        """
        if elapsed_days <= 0 or per_day <= 0:
            return 0
        accum = getattr(self, "_rel_decay_accum", None)
        if accum is None:
            accum = self._rel_decay_accum = {}
        changed = 0
        for name, rel in self.relationships.items():
            closeness = rel.get("closeness", 0)
            if not isinstance(closeness, (int, float)) or not closeness:
                accum.pop(name, None)
                continue
            damping = 1.0 / (
                1.0 + self.RELATIONSHIP_DECAY_FAMILIARITY
                * float(rel.get("interaction_count", 0) or 0)
            )
            accum[name] = accum.get(name, 0.0) + per_day * elapsed_days * damping
            step = int(accum[name])
            if not step:
                continue
            accum[name] -= step
            step = min(abs(closeness), step)
            rel["closeness"] = closeness - step if closeness > 0 else closeness + step
            changed += 1
        return changed

    def get_relationship_nl(self, other_name: str) -> str:
        """Return a natural language description of the relationship.

        The band ladder lives in engine/relationships.py so band-gated game
        rules (task-423's flirt/confide gates) cannot disagree with this prose
        about where the boundaries are.
        """
        from engine.relationships import describe
        return describe(self, other_name)

    def add_memory(self, text: str, tick: int, importance: int = 5, memory_type: str = "observation", tags=None, source: str = "auto", entity_ids=None, location: str = "", salience: int = 0):
        """Add a memory entry. Importance 1-10, higher = more significant.

        tags: list[str] — optional keyword labels for targeting via trigger effects.
        entity_ids: list[str] — graph node ids this memory is about (a subject),
            used by the observation index and the retrieval entity boost.
        location: str — the area the memory happened in.
        source: str — provenance label (auto/manual/trigger/...).
        Returns the stored entry so callers can index it.
        """
        entry = {
            "id": str(uuid.uuid4())[:8],
            "text": text,
            "tick": tick,
            "timestamp": time.time(),
            "importance": max(1, min(10, importance)),
            "type": memory_type,
            "tags": list(tags) if tags else [],
            "source": source,
            "entity_ids": [str(e) for e in (entity_ids or []) if e],
            "location": location or "",
            "salience_override": salience,
            "suppressions": [],
        }
        self.memories.append(entry)
        limit = _memory_limit()
        if limit and len(self.memories) > limit:
            self._trim_memories(limit)
        return entry

    def record_observation(self, subject_id: str, text: str, tick: int, kind: str = "",
                           tags=None, importance: int = 4, location: str = "",
                           source: str = "observation") -> dict:
        """Record seeing ``subject_id`` now, refreshing its live observation.

        ONE live observation per subject, updated in place: re-seeing the pantry
        updates the memory that already describes it rather than appending a
        second one. That is what keeps the store bounded by *subjects* instead
        of by visits — a week of wandering does not become thousands of
        observations — and it makes "when did I last see this?" a single lookup.

        The trace is the history; this holds the current belief.
        """
        existing = self.observation_memory(subject_id)
        if existing is not None:
            existing["text"] = text
            existing["tick"] = tick
            existing["timestamp"] = time.time()
            existing["location"] = location or existing.get("location", "")
            existing["visits"] = int(existing.get("visits", 1)) + 1
            if tags:
                existing["tags"] = sorted(set(existing.get("tags", [])) | set(tags))
            self.memory_index[str(subject_id)] = existing["id"]
            return existing

        entry = self.add_memory(
            text, tick, importance=importance, memory_type="observation",
            tags=(["observed"] + ([kind] if kind else []) + list(tags or [])),
            source=source, entity_ids=[subject_id], location=location,
        )
        entry["kind"] = kind
        entry["visits"] = 1
        self.memory_index[str(subject_id)] = entry["id"]
        return entry

    def observation_memory(self, subject_id: str):
        """The live observation memory about ``subject_id``, or None.

        Falls back to a scan when the index has no entry (an old save, or a
        memory written outside ``record_observation``) so the index can never
        silently disagree with the store; the scan repairs it.
        """
        key = str(subject_id)
        if not key:
            return None
        entry_id = self.memory_index.get(key)
        if entry_id:
            for m in self.memories:
                if m.get("id") == entry_id and not m.get("superseded_by"):
                    return m
        found = None
        for m in self.memories:
            if m.get("superseded_by"):
                continue
            if key in (m.get("entity_ids") or []):
                found = m
        if found is not None:
            self.memory_index[key] = found["id"]
        return found

    def observation_tick(self, subject_id: str):
        """Game tick this subject was last seen (None = never)."""
        entry = self.observation_memory(subject_id)
        return entry.get("tick") if entry else None

    def has_seen(self, subject_id: str) -> bool:
        """True when the character has a live observation of ``subject_id``.

        The novelty test (task-425): absence means "never been", because every
        sighting refreshes or creates the observation.
        """
        return self.observation_memory(subject_id) is not None

    def supersede_observation(self, subject_id: str, reason: str = "") -> bool:
        """Retire the observation of a subject that no longer exists as seen.

        The belief was replaced (the bread was eaten, the door was unlocked) and
        nothing new took its place, so recall must stop surfacing it. This is
        the only path that adds to the supersede chain — sightings refresh in
        place, they do not chain.
        """
        entry = self.observation_memory(str(subject_id))
        if entry is None:
            return False
        entry["superseded_by"] = reason or "gone"
        self.memory_index.pop(str(subject_id), None)
        return True

    def _trim_memories(self, limit: int):
        """Drop the least worth keeping when a retention cap is configured.

        Authored memories (``source == "manual"``) are the character's backstory,
        so they go last — a busy week of generated social chatter must not push
        the hand-written past out of the character.

        An evicted subject also leaves the observation index, so the character
        genuinely no longer knows it. Forgetting therefore re-enchants the world
        (task-425): a place it can no longer remember is novel again.
        """
        while len(self.memories) > limit:
            victim = 0
            for index, memory in enumerate(self.memories):
                if memory.get("source") != "manual":
                    victim = index
                    break
            gone = self.memories.pop(victim)
            for subject in (gone.get("entity_ids") or []):
                if self.memory_index.get(str(subject)) == gone.get("id"):
                    self.memory_index.pop(str(subject), None)

    def suppress_memory(self, tags=None, keywords: str = "", duration: int = 1, scope: str = "self") -> list:
        """Mark matching memories as inaccessible for `duration` turns.

        Returns list of suppressed memory ids.
        duration=0 means permanent until explicitly unblocked.
        """
        tags = [t.lower() for t in (tags or []) if t]
        keywords_lower = keywords.lower().strip()
        suppressed_ids = []
        for m in self.memories:
            if m.get("suppressions"):
                continue
            mem_tags = [t.lower() for t in (m.get("tags") or [])]
            tag_match = bool(tags) and all(t in mem_tags for t in tags)
            kw_match = bool(keywords_lower) and keywords_lower in m.get("text", "").lower()
            if (tags and tag_match) or (keywords_lower and kw_match) or (not tags and not keywords_lower):
                m.setdefault("suppressions", [])
                m["suppressions"].append({"until_tick": duration if duration > 0 else None, "source": scope})
                suppressed_ids.append(m.get("id"))
        return suppressed_ids

    def unblock_memory(self, tags=None, keywords: str = "", scope: str = "self") -> list:
        """Remove active suppressions from matching memories.

        Returns list of unblocked memory ids.
        """
        tags = [t.lower() for t in (tags or []) if t]
        keywords_lower = keywords.lower().strip()
        unblocked_ids = []
        for m in self.memories:
            suppressions = m.get("suppressions", [])
            if not suppressions:
                continue
            mem_tags = [t.lower() for t in (m.get("tags") or [])]
            tag_match = bool(tags) and all(t in mem_tags for t in tags)
            kw_match = bool(keywords_lower) and keywords_lower in m.get("text", "").lower()
            if (tags and tag_match) or (keywords_lower and kw_match) or (not tags and not keywords_lower):
                m["suppressions"] = [s for s in suppressions if s.get("source") != scope]
                if not m["suppressions"]:
                    unblocked_ids.append(m.get("id"))
        return unblocked_ids

    def clear_expired_suppressions(self, current_tick: int) -> None:
        """Drop suppressions whose `until_tick` has passed."""
        for m in self.memories:
            suppressions = m.get("suppressions", [])
            m["suppressions"] = [
                s for s in suppressions
                if s.get("until_tick") is None or s["until_tick"] > current_tick
            ]

    def reset_turn_state(self, current_tick: int) -> None:
        """Call at the start of each turn: reset salience overrides and clear expired suppressions."""
        for m in self.memories:
            m["salience_override"] = 0
        self.clear_expired_suppressions(current_tick)

    def get_relevant_memories(self, query: str, max_results: int = 5) -> list:
        """Keyword-based memory retrieval respecting suppressions and salience.

        Memories with an active suppression are excluded, and so are superseded
        observations — a belief that was replaced by a later one must not still
        be recallable (task-403).
        Recalled memories get a reinforce bump (+1 importance, cap 10).
        """
        if not self.memories:
            return []

        import re
        query_lower = query.lower()
        query_words = set(re.sub(r'[^\w\s]', '', query_lower).split())

        scored = []
        for m in self.memories:
            if m.get("suppressions") or m.get("superseded_by"):
                continue
            text_clean = re.sub(r'[^\w\s]', '', m.get("text", "").lower())
            text_words = set(text_clean.split())
            word_overlap = len(query_words & text_words)
            recency_boost = max(0, 1.0 - (m.get("tick", 0) / 100))
            salience = m.get("salience_override", 0)
            score = (word_overlap * 2) + (m.get("importance", 5) * 0.5) + (recency_boost * 3) + (salience * 2)
            if word_overlap > 0 or m.get("importance", 5) >= 7 or salience > 0:
                if m.get("importance", 5) < 10:
                    m["importance"] = m["importance"] + 1
                scored.append((score, m))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:max_results]]

    def get_memory_context_nl(self, query: str, max_results: int = 3) -> str:
        """Build a natural language context string from relevant memories."""
        mems = self.get_relevant_memories(query, max_results)
        if not mems:
            return ""
        lines = [f"=== {self.name}'s relevant memories ==="]
        for m in mems:
            lines.append(f"[Tick {m.get('tick', '?')}] {m['text']}")
        return "\n".join(lines)

    def to_dict(self):
        """Serialize player state including emotion and relationships for API responses."""
        return {
            "name": self.name,
            "exhaustion_count": getattr(self, 'exhaustion_count', 0),
            "current_area": self.current_area,
            "state": self.state,
            "conditions": list(self.conditions),
            "condition_instances": {
                cid: [dict(inst) for inst in instances]
                for cid, instances in self.conditions.items()
            },
            "vitals": dict(self.vitals),
            "decay_rates": dict(self.decay_rates),
            "stats": dict(self.stats),
            "skills": dict(self.skills),
            "inventory": [],
            "personality": self.personality,
            "description": getattr(self, 'description', ''),
            "base_description": getattr(self, 'base_description', ''),
            "unknown_name": getattr(self, 'unknown_name', ''),
            "simple_npc": self.simple_npc,
            "autonomy": self.autonomy,
            "npc_behavior": self.npc_behavior,
            "npc_action_interval": self.npc_action_interval,
            "emotion": {
                "current": self.emotion,
                "intensity": round(self.emotion_intensity, 2),
                "description": self.get_emotion_nl()
            },
            "emotions": dict(self.emotions_map()),
            "equipped": dict(self.equipped),
            "activity": self.activity,
            "relationships": self._relationships_to_dict(),
            "traits": dict(self.traits),
            "tags": list(self.tags),
            "interest_tags": list(self.interest_tags),
            "fear_tags": list(self.fear_tags),
            "flags": dict(getattr(self, "flags", {})),
            "hidden": bool(getattr(self, "hidden", False)),
            "visited_areas": list(self.visited_areas),
            "discovered_items": list(self.discovered_items),
            "memory_index": dict(self.memory_index),
            "patrol_route": list(getattr(self, "patrol_route", [])),
            "patrol_index": getattr(self, "patrol_index", 0),
            "trace": [dict(e) for e in getattr(self, "trace_log", [])],
            "simulation_mode": getattr(self, "simulation_mode", "active"),
            "next_due_tick": int(getattr(self, "next_due_tick", 0)),
        }

    def _relationships_to_dict(self):
        """Serialize relationships, attaching the derived per-person read.

        task-350: the derived (trust/fear/consent) profile is computed from the
        experience store and included so the prompt builder can render a
        truthful read synchronously (no extra fetch).
        """
        out = {}
        for key, data in (self.relationships or {}).items():
            display = data.get("name") or key
            entry = {
                "closeness": data["closeness"],
                "interaction_count": data.get("interaction_count", 0),
                "last_interaction_tick": data.get("last_interaction_tick", 0),
                "first_sighting": data.get("first_sighting", False),
                "label": data.get("label", ""),
            }
            try:
                from engine.derive import derive_person_profile
                prof = derive_person_profile(self, key)
                entry["role"] = prof.get("role")
                entry["consent"] = round(prof.get("consent", 0.0), 3)
                entry["trust"] = round(prof.get("trust", 0.0), 1)
                entry["fear"] = round(prof.get("fear", 0.0), 1)
                entry["summary"] = prof.get("summary")
                entry["has_signal"] = bool(prof.get("_has_signal"))
            except Exception:
                pass
            out[display] = entry
        return out
from engine.player_conditions import (
    CONDITION_DEFINITIONS,
    CONDITION_HIERARCHY,
    BLOCKING_CONDITIONS,
    PERIODIC_CONDITIONS,
    CONDITION_EXCLUSIONS,
    CONDITION_DEFAULT_TIMERS,
    PERCEPTION_SKIP,
    MATURE_CONDITIONS,
    _CONDITION_BASE,
    _condition_library_dir,
    _load_condition_library,
    seed_condition_library,
    reload_condition_library,
    _normalize_instance,
    condition_has_condition,
    condition_add_condition,
    condition_remove_condition,
    condition_end_instances,
    condition_load_conditions,
    get_state,
    set_state,
    get_state_timer,
    set_state_timer,
)