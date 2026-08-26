"""Vital effect handlers (damage, heal, adjust_vital, save)."""


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


def handle_heal(self, params, context, item_node=None, game_state=None):
    """Restore a vital stat (HP by default) on the active player.

    game_state must provide: game_state.player
    """
    amount = int(params.get("amount", 10))
    stat = params.get("stat", "HP")
    outputs = []
    if game_state and game_state.player:
        if stat in game_state.player.vitals:
            game_state.player.vitals[stat] = min(
                100, game_state.player.vitals.get(stat, 100) + amount
            )
            msg = params.get("message", f"You restore {amount} {stat}.")
            outputs.append(msg)
        else:
            game_state.player.vitals["HP"] = min(
                100, game_state.player.vitals.get("HP", 100) + amount
            )
            outputs.append(f"You heal {amount} HP.")
    return outputs


def handle_adjust_vital(self, params, context, item_node=None, game_state=None):
    """Adjust a vital stat (HP, Energy, Sanity, etc.) on a player.

    game_state must provide:
      game_state.player
      game_state.players
    """
    stat = params.get("stat", "HP")
    amount = int(params.get("amount", 0))
    target = params.get("target", "self")
    outputs = []
    if target == "self" and game_state and game_state.player:
        if stat in game_state.player.vitals:
            game_state.player.vitals[stat] = max(
                0, min(100, game_state.player.vitals[stat] + amount)
            )
        if stat == "HP":
            max_hp = game_state.player.vitals.get("Max_HP", 100)
            game_state.player.vitals[stat] = max(
                0, min(max_hp, game_state.player.vitals[stat])
            )
    elif target != "self" and game_state:
        target_player = game_state.players.get(target)
        if target_player and stat in target_player.vitals:
            target_player.vitals[stat] = max(
                0, min(100, target_player.vitals[stat] + amount)
            )
            if stat == "HP":
                max_hp = target_player.vitals.get("Max_HP", 100)
                target_player.vitals[stat] = max(
                    0, min(max_hp, target_player.vitals[stat])
                )
    from engine.vitals import format_vital_change
    msg = params.get("message") or format_vital_change(stat, amount)
    msg = self._render_template_fn(msg, context)
    outputs.append(msg)
    return outputs


HANDLERS = {
    "damage": handle_damage,
    "save": handle_save,
    "heal": handle_heal,
    "adjust_vital": handle_adjust_vital,
}
