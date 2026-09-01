# player.py
import re
import time
import uuid

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
            for cid in ("warming_up", "aroused", "highly_aroused", "frantic",
                        "overstimulated", "nipple_hard", "blushing", "wetness",
                        "sensitized", "satisfied"):
                self.conditions.pop(cid, None)

    def __init__(self, name="Traveler"):
        self.name = name
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

        # Per-character decay rate overrides (defaults match engine baseline)
        self.decay_rates = {
            "Hunger": 1, "Thirst": 1, "Energy": 1, "Social": 1,
            "Hygiene": 1, "Bladder": 1, "Sanity": 1, "Entertainment": 1
        }

        # Per-body-part numeric state (task-253 body-part taxonomy). Flat dict
        # keyed by region id from engine/body_parts.py: each region has a base
        # `sensitivity` and an `injury` slot (None until combat/conditions set
        # one). Erogenous numeric fields (hardness, wetness, flush, ...) extend
        # this per-region dict in task-207.
        from engine.body_parts import default_body_state
        self.body_state = default_body_state()
        
        # Basic Skills
        self.skills = {
            "Athletics": 1, "Acrobatics": 1,
            "Stealth": 1, "Perception": 1,
            "Survival": 1, "Persuasion": 1
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
        # Conditions system: {condition_id: [instance, instance, ...]} — MULTIPLE
        # concurrent instances per condition (5 vials of poison = 5 `poisoned`
        # instances). Each instance: {duration, source, level, periodic, ends_on,
        # symptoms, known} where the optional fields override the catalog default.
        # duration = ticks remaining (None = until countered/removed).
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
        if other_name not in self.relationships:
            self.relationships[other_name] = {
                "closeness": 0, "last_interaction_tick": tick,
                "interaction_count": 0, "first_sighting": True,
            }
        dim, factor = self._FELT_TO_DIM[key]
        # Per-point magnitude: a 10/10 feeling lands a tag of ~2.5, which the
        # reducer multiplies by importance, leaving a real mark on the profile.
        mag = intensity / 4.0
        importance = max(3, round(intensity))
        tags = ["rel:" + other_name, dim + ":" + str(round(factor * mag, 2))]
        self.add_memory(
            "I felt " + label + " toward " + other_name + ".", tick=tick,
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
        if other_name in self.relationships:
            return False
        self.relationships[other_name] = {
            "closeness": 0,
            "last_interaction_tick": tick,
            "interaction_count": 0,
            "first_sighting": True
        }
        self._grant_meeting_entertainment()
        return True

    def has_met(self, other_name: str) -> bool:
        """True when this character has met *other_name* (a relationship exists)."""
        return other_name in self.relationships

    def knows_name(self, other_name: str) -> bool:
        """True when this character has actually learned *other_name*'s name
        (heard it spoken, or read their name tag) — task-339. Recognition
        (having seen them) is NOT name knowledge."""
        rel = self.relationships.get(other_name)
        return rel is not None and not rel.get("first_sighting")

    def learn_name(self, other_name: str, tick: int) -> bool:
        """Learn another character's NAME (heard it spoken / read their name
        tag) — task-339. Registers the relationship if new and clears the
        name-unknown flag. Returns True only when this was new knowledge."""
        self.register_first_meeting(other_name, tick)
        rel = self.relationships.get(other_name)
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

    def _grant_meeting_entertainment(self):
        """Entertainment boost the first time a character meets someone new."""
        if "Entertainment" not in self.vitals:
            return
        try:
            from engine.traits import TraitSystem
        except ImportError:
            base_boost = 10
        else:
            base_boost = 10
            if TraitSystem.has_effect(self, "curious"):
                base_boost = int(base_boost * 1.5)
            if TraitSystem.has_effect(self, "homebody"):
                base_boost = 0
        self.vitals["Entertainment"] = min(100, self.vitals.get("Entertainment", 50) + base_boost)

    def update_relationship(self, other_name: str, tick: int, sentiment_change: int = 0):
        """Update relationship closeness with another character.
        sentiment_change: -20 to +20 per interaction. Range: -100 to +100.

        First meeting with a character grants an Entertainment novelty boost
        (mirrors the area-visit/item-discovery boosts in task-136).
        """
        if other_name not in self.relationships:
            self.relationships[other_name] = {
                "closeness": 0,
                "last_interaction_tick": tick,
                "interaction_count": 0
            }
            self._grant_meeting_entertainment()
        rel = self.relationships[other_name]
        rel["closeness"] = max(-100, min(100, rel["closeness"] + sentiment_change))
        rel["last_interaction_tick"] = tick
        rel["interaction_count"] += 1

    def get_relationship_nl(self, other_name: str) -> str:
        """Return a natural language description of the relationship."""
        rel = self.relationships.get(other_name)
        if not rel:
            return f"{self.name} has never met {other_name}."
        closeness = rel["closeness"]
        if closeness <= -75:
            desc = "mortal enemy"
        elif closeness <= -50:
            desc = "enemy"
        elif closeness <= -25:
            desc = "rival"
        elif closeness < 0:
            desc = "unfriendly"
        elif closeness == 0:
            desc = "neutral"
        elif closeness <= 25:
            desc = "acquaintance"
        elif closeness <= 50:
            desc = "friend"
        elif closeness <= 75:
            desc = "close friend"
        else:
            desc = "inseparable"
        return f"{self.name} considers {other_name} a {desc} (closeness: {closeness}/100)."

    def add_memory(self, text: str, tick: int, importance: int = 5, memory_type: str = "observation", tags=None, source: str = "auto"):
        """Add a memory entry. Importance 1-10, higher = more significant.

        tags: list[str] — optional keyword labels for targeting via trigger effects.
        source: str — provenance label (auto/manual/trigger/...).
        """
        self.memories.append({
            "id": str(uuid.uuid4())[:8],
            "text": text,
            "tick": tick,
            "timestamp": time.time(),
            "importance": max(1, min(10, importance)),
            "type": memory_type,
            "tags": list(tags) if tags else [],
            "source": source,
            "salience_override": 0,
            "suppressions": [],
        })
        if len(self.memories) > 200:
            self.memories.pop(0)

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

        Memories with an active suppression are excluded.
        Recalled memories get a reinforce bump (+1 importance, cap 10).
        """
        if not self.memories:
            return []

        import re
        query_lower = query.lower()
        query_words = set(re.sub(r'[^\w\s]', '', query_lower).split())

        scored = []
        for m in self.memories:
            if m.get("suppressions"):
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
            "visited_areas": list(self.visited_areas),
            "discovered_items": list(self.discovered_items),
            "patrol_route": list(getattr(self, "patrol_route", [])),
            "patrol_index": getattr(self, "patrol_index", 0),
        }

    def _relationships_to_dict(self):
        """Serialize relationships, attaching the derived per-person read.

        task-350: the derived (trust/fear/consent) profile is computed from the
        experience store and included so the prompt builder can render a
        truthful read synchronously (no extra fetch).
        """
        out = {}
        for name, data in (self.relationships or {}).items():
            entry = {
                "closeness": data["closeness"],
                "interaction_count": data.get("interaction_count", 0),
                "last_interaction_tick": data.get("last_interaction_tick", 0),
                "first_sighting": data.get("first_sighting", False),
            }
            try:
                from engine.derive import derive_person_profile
                prof = derive_person_profile(self, name)
                entry["role"] = prof.get("role")
                entry["consent"] = round(prof.get("consent", 0.0), 3)
                entry["trust"] = round(prof.get("trust", 0.0), 1)
                entry["fear"] = round(prof.get("fear", 0.0), 1)
                entry["summary"] = prof.get("summary")
                entry["has_signal"] = bool(prof.get("_has_signal"))
            except Exception:
                pass
            out[name] = entry
        return out
from engine.player_conditions import (
    CONDITION_DEFINITIONS,
    CONDITION_HIERARCHY,
    BLOCKING_CONDITIONS,
    PERIODIC_CONDITIONS,
    CONDITION_EXCLUSIONS,
    CONDITION_DEFAULT_TIMERS,
    _CONDITION_BASE,
    _condition_library_dir,
    _load_condition_library,
    seed_condition_library,
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