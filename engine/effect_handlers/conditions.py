"""Condition and trait effect handlers (apply/remove condition, apply/remove trait)."""


def handle_apply_condition(self, params, context, item_node=None, game_state=None):
    """Apply a condition to a character.
    params: {"condition": "poisoned", "target": "self", "duration": 10,
             "source": "viper", "source_type": "item", "level": 0,
             "periodic": {"HP": -7},              // per-instance drain override
             "extra_conditions": [{"condition": "blind", "duration": 3}],
             "ends_on": ["fix"], "symptoms": {...}, "known": false}
    """
    condition = params.get("condition", "")
    if not condition:
        return []
    target = params.get("target", "self")
    if target == "target":
        # Ally-administered cure: "use X on <name>" resolves to the target.
        target = context.get("target_name") or (game_state.active_player if game_state else "")
    if game_state is not None:
        pname = self._resolve_player_name(game_state, target)
        game_state.conditions.apply_condition(
            pname, condition,
            duration=params.get("duration"),
            source=params.get("source"),
            level=params.get("level"),
            periodic=params.get("periodic"),
            extra_conditions=params.get("extra_conditions"),
            ends_on=params.get("ends_on"),
            symptoms=params.get("symptoms"),
            known=params.get("known"),
            source_type=params.get("source_type"),
        )
    return [params.get("message", f"{condition} applied.")]


def handle_remove_condition(self, params, context, item_node=None, game_state=None):
    """Remove a condition from a character.
    params: {"condition": "poisoned", "target": "self"}
    """
    condition = params.get("condition", "")
    if not condition:
        return []
    target = params.get("target", "self")
    if target == "target":
        # Ally-administered cure: "use X on <name>" resolves to the target.
        target = context.get("target_name") or (game_state.active_player if game_state else "")
    if game_state is not None:
        pname = self._resolve_player_name(game_state, target)
        game_state.conditions.remove_condition(pname, condition)
    msg = params.get("message", f"{condition} cured.")
    return [self._render_template_fn(msg, context)]


def handle_apply_trait(self, params, context, item_node=None, game_state=None):
    """Apply a trait to a character.
    params: {"trait": "dark_vision", "target": "self", "param": true}

    SILENT by default — no announcement is emitted unless the trigger
    author explicitly sets ``message``. A cursed object can curse you
    without your knowledge; a button can flag someone else without telling
    the presser.
    """
    trait_id = params.get("trait", "")
    if not trait_id:
        return []
    target = params.get("target", "self")
    param_value = params.get("param", True)
    from engine.traits import TraitSystem
    trait_def = TraitSystem.get_definition(trait_id)
    label = trait_def["name"] if trait_def else trait_id
    if game_state is not None:
        pname = game_state.active_player if target == "self" else target
        player = game_state.players.get(pname)
        if player:
            conflicts = TraitSystem.conflicting_traits(player, trait_id)
            if conflicts:
                # Conflict = a failed grant. Surface it to the SYSTEM log
                # (event stream / UI) but never to the agent's action
                # result — the character shouldn't meta-know their trait
                # grants failed unless the author wrote a message for it.
                if params.get("message"):
                    return [params["message"]]
                if hasattr(game_state, "add_log_entry"):
                    conflict_names = ", ".join(
                        TraitSystem.get_definition(c).get("name", c) for c in conflicts
                    )
                    game_state.add_log_entry(
                        f"Trait conflict: {pname} couldn't gain {label} "
                        f"(conflicts with {conflict_names})."
                    )
                return []
            player.traits[trait_id] = param_value
            # grants_conditions: trait-sourced conditions stay in sync
            TraitSystem.sync_granted_conditions(player)
            # Only surface an announcement when the author wrote one.
            if params.get("message"):
                return [params["message"]]
            return []
    return [params["message"]] if params.get("message") else []


def handle_remove_trait(self, params, context, item_node=None, game_state=None):
    """Remove a trait from a character.
    params: {"trait": "dark_vision", "target": "self"}

    SILENT by default — only announces when ``message`` is explicitly set.
    """
    trait_id = params.get("trait", "")
    if not trait_id:
        return []
    target = params.get("target", "self")
    from engine.traits import TraitSystem
    trait_def = TraitSystem.get_definition(trait_id)
    label = trait_def["name"] if trait_def else trait_id
    if game_state is not None:
        pname = game_state.active_player if target == "self" else target
        player = game_state.players.get(pname)
        if player:
            if trait_id in player.traits:
                del player.traits[trait_id]
                TraitSystem.sync_granted_conditions(player)
                # Only surface an announcement when the author wrote one.
                if params.get("message"):
                    return [params["message"]]
                return []
    return [params["message"]] if params.get("message") else []


HANDLERS = {
    "apply_condition": handle_apply_condition,
    "remove_condition": handle_remove_condition,
    "apply_trait": handle_apply_trait,
    "remove_trait": handle_remove_trait,
}
