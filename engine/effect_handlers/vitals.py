"""Vital effect handlers (damage, heal, adjust_vital, set_vital, save).

Every write in this module goes through :func:`engine.vitals.ceiling`, the one
answer to "what is the top of this vital on this character" (task-538). Before
that resolver existed these handlers carried their own copies of the rule, and
`heal` had the wrong one — it clamped to a literal 100, so healing a 7-HP
goblin by 5 produced 12 HP. That was invisible only because `Max_HP` was itself
always 100; the moment a stat block declared a real maximum, the bug surfaced.
"""

from engine.vitals import ceiling, clamp_to_ceiling


def handle_damage(self, params, context, item_node=None, game_state=None):
    """Deal damage to the active player or another character.

    params:
      amount (int) — raw damage dealt on a failed (or absent) save.
      target — ``"self"``, ``"other"`` (first character in the area /
               the one named by ``character_name``), or an explicit
               character name.
      character_name (str) — which character for ``target="other"``.
      save (dict) — optional save to resist the damage (task-159):
          ``{"stat": "DEX", "dc": 12, "on_success": "half"|"none"}``
        ``stat`` may be an ability (STR/DEX/...) or a skill (Athletics...).
        On success the damage is halved (default) or avoided entirely; the
        ``[Save] ...`` roll is emitted alongside the damage message.

    game_state must provide:
      game_state.player        -- the active Player (or None)
      game_state.players       -- dict of all Player objects
      game_state.get_players_in_area(area_name, exclude_self) -> list
      game_state.saving_throw(player, stat, dc) -> (success, total, msg)
    """
    amount = int(params.get("amount", 5))
    target = params.get("target", "self")
    outputs = []

    target_player = None
    label = ""
    if target == "self" and game_state:
        target_player = game_state.player
        label = "You"
    elif target == "other":
        others = game_state.get_players_in_area() if game_state else []
        if others:
            character_name = params.get("character_name", others[0]["name"])
            target_player = game_state.players.get(character_name) if game_state else None
            label = character_name
    elif game_state:
        target_player = (getattr(game_state, "players", None) or {}).get(target)
        label = target

    if target_player is None:
        return outputs

    applied = amount
    save_cfg = params.get("save") or {}
    if save_cfg:
        check = save_cfg.get("stat") or save_cfg.get("skill") or "DEX"
        dc = int(save_cfg.get("dc", 12))
        success, total, msg = game_state.saving_throw(target_player, check, dc)
        outputs.append(msg)
        if success:
            on_success = save_cfg.get("on_success", "half")
            applied = 0 if on_success == "none" else amount // 2
        else:
            outputs.append(f"{label} fails to resist!")

    target_player.vitals["HP"] = max(
        0, target_player.vitals.get("HP", 100) - applied
    )
    if applied == 0:
        outputs.append(f"{label} avoids the damage entirely!")
    elif applied < amount:
        outputs.append(f"{label} takes {applied} damage (was {amount})!")
    else:
        outputs.append(f"{label} takes {applied} damage!")
    # Damage interrupts activities / wakes sleepers (task-131)
    if game_state is not None and hasattr(game_state, "activities"):
        wake_msg = game_state.activities.wake_on_damage(target_player.name)
        if wake_msg:
            outputs.append(wake_msg)
    return outputs


def handle_save(self, params, context, item_node=None, game_state=None):
    """Roll a saving throw, then run the matching effect branch.

    params:
      stat (str) — ability (WIS...) or skill (Athletics...) to roll.
      dc (int) — difficulty class of the save.
      on_fail (list) — effects to run when the save fails.
      on_success (list) — effects to run when the save succeeds.

    This is the world-authoring gate for fears and hazards: a way or item
    trigger can force a fear save and apply ``frightened`` on failure.
    ``source`` defaults to the triggering node's name for any
    ``apply_condition`` sub-effect, so authors only set ``source_type``.

    game_state must provide ``saving_throw(player, stat, dc)`` and the
    active player.
    """
    if game_state is None:
        return []
    player = getattr(game_state, "player", None)
    if player is None:
        return []
    check = params.get("stat") or params.get("skill") or "WIS"
    dc = int(params.get("dc", 12))
    success, total, msg = game_state.saving_throw(player, check, dc)
    outputs = [msg]
    branch = "on_success" if success else "on_fail"
    sub_context = dict(context)
    for effect in params.get(branch) or []:
        etype = effect.get("type", "message")
        eparams = dict(effect.get("params", {}))
        if etype == "apply_condition" and "source" not in eparams and item_node is not None:
            eparams["source"] = item_node.name
        outputs.extend(
            self.execute(
                etype, eparams, sub_context,
                item_node=item_node, game_state=game_state,
            )
        )
    return outputs


def _vital_ceiling(vitals: dict, stat: str) -> float:
    """The ceiling for *stat* on a vitals dict.

    Thin alias kept because several callers inside this module predate the
    resolver; it delegates so the rule exists in exactly one place
    (``engine.vitals.ceiling``). HP resolves to an authored ``Max_HP`` and never
    silently to 100; Temperature is anatomical (~37) and unbounded above, since
    its own band model in ``tick_manager`` decides what is lethal.
    """
    return ceiling(vitals, stat)


def handle_heal(self, params, context, item_node=None, game_state=None):
    """Restore a vital stat (HP by default).

    params:
      amount (int) — how much to restore.
      stat (str)   — which vital. Canonical spelling ("HP", "Energy"), resolved
                     case-insensitively against the target's vitals.
      target (str) — "self" (default) or a character name. Mirrors
                     ``apply_condition`` and ``adjust_vital``, which both accept a
                     target; this used to always act on ``game_state.player``.
      message      — narration.

    The result is clamped to the target's own ceiling — ``Max_HP`` for HP — rather
    than a hardcoded 100. The old literal was harmless only because ``Max_HP`` was
    itself always 100; the moment a stat block declared a real maximum, healing a
    7-HP goblin by 5 produced 12 HP. See task-538.
    """
    amount = int(params.get("amount", 10))
    stat = params.get("stat", "HP")
    target = params.get("target", "self")
    outputs = []
    if not game_state:
        return outputs

    subject = None
    if target == "self":
        subject = getattr(game_state, "player", None)
    else:
        players = getattr(game_state, "players", {}) or {}
        subject = players.get(self._resolve_player_name(game_state, target))
    if subject is None:
        return outputs

    vitals = subject.vitals
    key = _resolve_vital_key(vitals, stat)
    if key is None:
        # Unknown vital name: fall back to HP rather than inventing a new key.
        key = "HP"
    before = vitals.get(key, 0)
    try:
        before = float(before)
    except (TypeError, ValueError):
        before = 0.0
    vitals[key] = clamp_to_ceiling(vitals, key, before + amount)
    restored = vitals[key] - before

    if restored <= 0:
        return [params.get(
            "message",
            f"{getattr(subject, 'name', 'You')} cannot be restored further.",
        )]

    return [params.get("message", f"You restore {restored:g} {key}.")]


#: Vitals are keyed canonically ("Thirst"); authored data spells them loosely
#: ("thirst"). Exact match wins, then a case-insensitive lookup, so a lowercase
#: stat in a trigger adjusts the right vital instead of silently doing nothing.
def _resolve_vital_key(vitals, stat):
    if not isinstance(vitals, dict):
        return None
    if stat in vitals:
        return stat
    low = str(stat or "").lower()
    for key in vitals:
        if str(key).lower() == low:
            return key
    return None


def _effect_subject(params, game_state):
    """Resolve ``target`` to a Player: ``self`` (default) or a named character.

    Shared by every vital effect so they all accept the same ``target``
    vocabulary, and — the reason it exists — so none of them silently acts on
    ``game_state.player`` when the author named someone else.
    """
    if game_state is None:
        return None
    target = params.get("target", "self")
    if target in (None, "self"):
        return getattr(game_state, "player", None)
    players = getattr(game_state, "players", {}) or {}
    if not isinstance(players, dict):
        return None
    resolved = players.get(str(target))
    if resolved is not None:
        return resolved
    # Case-insensitive second pass, so a name spelled in the wrong case lands on
    # the right character instead of doing nothing.
    low = str(target).strip().lower()
    for name, player in players.items():
        if str(name).strip().lower() == low:
            return player
    return None


def handle_adjust_vital(self, params, context, item_node=None, game_state=None):
    """Adjust a vital stat (HP, Energy, Sanity, etc.) on a player.

    params:
      stat (str)    — which vital. Canonical spelling ("HP", "Energy"), resolved
                      case-insensitively against the target's vitals.
      amount (int)  — signed delta.
      target (str)  — ``"self"`` (default) or a character name.

    Clamped against **this character's own ceiling** (``engine.vitals.ceiling``),
    which for HP means an authored ``Max_HP``. The old code clamped to a literal
    100 and then re-clamped HP to ``Max_HP``, so a character with a real maximum
    and a large negative amount behaved fine but the two clamps could disagree
    for any other vital that later grows a ``Max_`` companion.

    game_state must provide:
      game_state.player
      game_state.players
    """
    stat = params.get("stat", "HP")
    amount = int(params.get("amount", 0))
    outputs = []

    subject = _effect_subject(params, game_state)
    if subject is None:
        return outputs
    key = _resolve_vital_key(subject.vitals, stat)
    if key is not None:
        subject.vitals[key] = clamp_to_ceiling(
            subject.vitals, key, subject.vitals[key] + amount)

    from engine.vitals import format_vital_change
    msg = params.get("message") or format_vital_change(stat, amount)
    msg = self._render_template_fn(msg, context)
    outputs.append(msg)
    return outputs


def handle_set_vital(self, params, context, item_node=None, game_state=None):
    """Set a vital to an exact value (``task-538``, task-537 §M).

    params:
      stat (str)    — which vital (canonical spelling preferred).
      value (num)   — the absolute value to set. Clamped to the vital's ceiling.
      target (str)  — ``"self"`` (default) or a character name.

    This is the "set the meter" counterpart to ``adjust_vital``'s "move the
    meter", and it is what a resurrection or a scripted scene needs. It is
    clamped, not free: a ``set_vital`` that could push Energy past its maximum
    would break every later clamp that trusts the ceiling.
    """
    stat = params.get("stat", "HP")
    outputs = []
    subject = _effect_subject(params, game_state)
    if subject is None:
        return outputs
    key = _resolve_vital_key(subject.vitals, stat)
    if key is None:
        outputs.append(params.get("message")
                       or f"{subject.name} has no {stat} to set.")
        return outputs
    try:
        value = float(params.get("value", 0))
    except (TypeError, ValueError):
        value = 0.0
    subject.vitals[key] = clamp_to_ceiling(subject.vitals, key, value)
    msg = params.get("message") or f"{key} set to {subject.vitals[key]:g}."
    outputs.append(self._render_template_fn(msg, context))
    return outputs


def handle_modify_vital_max(self, params, context, item_node=None, game_state=None):
    """Raise (or lower) a vital's **maximum** (``task-538``, task-537 §M).

    params:
      stat (str)    — which vital.
      amount (num)  — signed delta to ``Max_{stat}`` (or, for HP, to a
                      ``max_hp`` alias). A positive amount raises the ceiling.
      target (str)  — ``"self"`` (default) or a character name.
      scale_current (bool) — when true (default false), also raise the *current*
                      value by the same amount, so a character that gains max HP
                      gains the vitality with it. By default the current value
                      is **unchanged**: a spell that lifts your maximum should
                      not silently heal you, and the existing behaviour callers
                      rely on is "ceiling moved, meter stayed".

    This is the reason a maximum wants to be data rather than a constant: a
    trait, a spell or a level-up effect can raise it at runtime, and the whole
    clamp chain follows automatically because every reader asks
    ``engine.vitals.ceiling``.
    """
    stat = params.get("stat", "HP")
    outputs = []
    subject = _effect_subject(params, game_state)
    if subject is None:
        return outputs
    key = _resolve_vital_key(subject.vitals, stat)
    if key is None:
        outputs.append(params.get("message")
                       or f"{subject.name} has no {stat} maximum to modify.")
        return outputs
    try:
        amount = float(params.get("amount", 0))
    except (TypeError, ValueError):
        amount = 0.0
    max_key = f"Max_{key}"
    try:
        current_max = float(subject.vitals.get(max_key,
                                               ceiling(subject.vitals, key)))
    except (TypeError, ValueError):
        current_max = 0.0
    new_max = max(0.0, current_max + amount)
    subject.vitals[max_key] = new_max

    if params.get("scale_current"):
        subject.vitals[key] = clamp_to_ceiling(
            subject.vitals, key, subject.vitals.get(key, 0) + amount)
    else:
        # A ceiling that dropped below the current value would leave the vital
        # above its own maximum, which every later clamp would silently fix and
        # every reader would find surprising. Bring the value back under it.
        subject.vitals[key] = clamp_to_ceiling(
            subject.vitals, key, subject.vitals.get(key, 0))

    msg = params.get("message") or f"{max_key} is now {new_max:g}."
    outputs.append(self._render_template_fn(msg, context))
    return outputs


STAT_NAMES = ("STR", "DEX", "CON", "INT", "WIS", "CHA")
#: 5e's ability range. A trigger may train or drain an ability but not make it
#: nonsense, so the result is clamped rather than left to the author.
STAT_MIN, STAT_MAX = 1, 30


def handle_adjust_stat(self, params, context, item_node=None, game_state=None):
    """Adjust an ability score on a player (task-480).

    The sheet counterpart to ``adjust_vital``: abilities are mutable stats
    changed by play, so an item or trigger can train or drain one. ``stat`` is a
    core ability (STR/DEX/CON/INT/WIS/CHA, case-insensitive); the existing key
    casing on the player is reused so both ``STR`` and ``str`` spells work.
    Clamped to [1, 30]. Targets ``self`` or a named character.
    """
    stat = str(params.get("stat", "")).upper()
    if stat not in STAT_NAMES:
        return []
    try:
        amount = int(params.get("amount", 0))
    except (TypeError, ValueError):
        return []
    target = params.get("target", "self")

    outputs = []
    player = None
    if game_state is not None:
        if target == "self":
            player = getattr(game_state, "player", None)
        else:
            player = (getattr(game_state, "players", None) or {}).get(target)
    if player is None:
        return outputs

    stats = getattr(player, "stats", None)
    if not isinstance(stats, dict):
        return outputs
    key = stat if stat in stats else stat.lower()
    try:
        current = int(stats.get(key, 10) or 10)
    except (TypeError, ValueError):
        current = 10
    stats[key] = max(STAT_MIN, min(STAT_MAX, current + amount))
    outputs.append(params.get("message")
                   or f"{key} {stats[key]} ({amount:+d}).")
    return outputs


HANDLERS = {
    "damage": handle_damage,
    "save": handle_save,
    "heal": handle_heal,
    "adjust_vital": handle_adjust_vital,
    "set_vital": handle_set_vital,
    "modify_vital_max": handle_modify_vital_max,
    "adjust_stat": handle_adjust_stat,
}
