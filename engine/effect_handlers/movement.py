"""Movement effect handlers for the virtual world trigger system.

@module effect_handlers/movement
@contributes the ``push_actor`` and ``hazard`` trigger effects
@docs docs/virtualWorld/Rules Engine/Triggers & Effects.md
"""


def handle_push_actor(self, params, context, item_node=None, game_state=None):
    """Push an actor along a connected downstream way using normal movement.

    params: {"direction": "south"}  OR  {"way_id": "way_river_01"}
    """
    if game_state is None:
        return []
    target = params.get("target", "self")
    if target == "target":
        target = context.get("target_name") or (
            game_state.active_player if game_state else ""
        )
    pname = self._resolve_player_name(game_state, target)
    player = getattr(game_state, "players", {}).get(pname)
    if player is None:
        return []
    direction = params.get("direction") or ""
    way_id = params.get("way_id") or ""
    area_id = player.current_area
    if not area_id:
        return []
    try:
        exits = game_state.build_exits_for_area(area_id, include_hidden=True) or {}
    except Exception:
        exits = {}
    dest = ""
    actual_direction = direction
    if way_id:
        for d, data in exits.items():
            if data.get("way_id") == way_id:
                dest = data.get("target") or ""
                actual_direction = d
                break
    else:
        data = exits.get(direction) or {}
        dest = data.get("target") or ""
    if not dest:
        return []
    old_active = getattr(game_state, "active_player", None)
    game_state.active_player = pname
    try:
        game_state.movement.move_to_area(actual_direction, kind="go")
        return []
    except Exception as exc:
        return [str(exc) or "the way is blocked"]
    finally:
        game_state.active_player = old_active


def handle_hazard(self, params, context, item_node=None, game_state=None):
    """Execute a single-roll terrain/current hazard effect (task-746).

    params:
      hazard_id (str): optional hazard from hazards.json (e.g. 'river', 'rapids', 'cliff')
      skill (str): skill or ability to roll (default 'Athletics' or from hazard)
      ability (str): ability fallback
      dc (int): DC for check, or derived via hazard strength
      strength (int): encounter strength for hazard DC lookup (default 5)
      direction (str): downstream direction to push actor on failure
      way_id (str): downstream way_id to push actor on failure
      target (str): 'self' or 'target'
      sweep_guard_minutes (float): minutes to suppress re-triggering during sweep (default 2.0)
      avoid_minutes (float): minutes to route around on failure / refusal (default 30.0)
      damage (str|int): optional damage on failure
      conditions (list): optional condition tags to apply on failure
      tags (list): optional event/status tags
      message_success (str): custom narrative on success
      message_fail (str): custom narrative on failure
      on_success (list|dict): optional nested effect(s) on success
      on_fail (list|dict): optional nested effect(s) on failure
    """
    if game_state is None:
        return []

    from engine import hazards
    from engine import checks
    from engine import traversal

    target = params.get("target", "self")
    if target == "target":
        target = context.get("target_name") or (
            game_state.active_player if game_state else ""
        )
    pname = self._resolve_player_name(game_state, target)
    player = getattr(game_state, "players", {}).get(pname)
    if player is None:
        return []

    hazard_id = params.get("hazard_id") or ""
    hazard_data = hazards.hazard(hazard_id) or {} if hazard_id else {}

    guard_id = params.get("guard_id") or hazard_id or (item_node.id if item_node else "hazard_sweep")
    try:
        now_minutes = float(game_state.total_game_minutes())
    except Exception:
        now_minutes = 0.0

    sweep_guards = getattr(player, "_hazard_sweep_guards", None)
    if sweep_guards is None:
        sweep_guards = {}
        try:
            player._hazard_sweep_guards = sweep_guards
        except Exception:
            pass

    until = sweep_guards.get(guard_id, 0.0)
    if until > now_minutes:
        # Sweep guard active: suppress re-roll and cascade
        return []

    guard_duration = float(params.get("sweep_guard_minutes", 2.0))
    sweep_guards[guard_id] = now_minutes + guard_duration

    # Resolve check kind and DC
    skill = params.get("skill") or hazard_data.get("ability") or "Athletics"
    strength = int(params.get("strength", 5))
    dc = params.get("dc")
    if dc is None:
        if hazard_id:
            dc = hazards.dc_for(hazard_id, strength)
        if dc is None:
            dc = 12
    else:
        dc = int(dc)

    roll_fn = context.get("roll_fn")
    check_result = checks.resolve(player, kind=skill, dc=dc, roll_fn=roll_fn)

    out = []
    if check_result.message:
        out.append(check_result.message)

    area_id = getattr(player, "current_area", "")

    if check_result.success:
        succ_msg = params.get("message_success") or hazard_data.get("message_success")
        if succ_msg:
            out.append(succ_msg)
        on_success = params.get("on_success")
        if on_success:
            if isinstance(on_success, dict):
                on_success = [on_success]
            for eff in on_success:
                etype = eff.get("type")
                eparams = eff.get("params", {})
                if etype:
                    out.extend(self.execute(etype, eparams, context, item_node=item_node, game_state=game_state))
    else:
        fail_msg = params.get("message_fail") or hazard_data.get("message_fail")
        if fail_msg:
            out.append(fail_msg)

        # On-fail hazard registry definitions
        on_fail_spec = hazard_data.get("on_fail") or {}
        conditions_to_apply = list(params.get("conditions") or on_fail_spec.get("conditions") or [])
        damage_expr = params.get("damage") or on_fail_spec.get("damage")

        for cond in conditions_to_apply:
            self.execute("apply_condition", {"condition": cond, "target": pname}, context, item_node=item_node, game_state=game_state)

        if damage_expr:
            try:
                from engine.checks import roll
                dmg_val = roll(str(damage_expr)) if any(c in str(damage_expr) for c in "dD+-") else int(damage_expr)
            except Exception:
                dmg_val = 1
            if dmg_val > 0:
                self.execute("damage", {"amount": dmg_val, "target": pname}, context, item_node=item_node, game_state=game_state)

        # Forced push movement
        push_direction = params.get("direction") or ""
        push_way_id = params.get("way_id") or ""

        # Record traversal refusal so soak routes around it
        avoid_label = push_direction or push_way_id or "hazard"
        avoid_mins = float(params.get("avoid_minutes", traversal.AVOID_MINUTES))
        if area_id:
            traversal.note_refusal(game_state, player, area_id, avoid_label, minutes=avoid_mins)

        if push_direction or push_way_id:
            push_res = handle_push_actor(self, {"direction": push_direction, "way_id": push_way_id, "target": pname}, context, item_node=item_node, game_state=game_state)
            if push_res:
                out.extend(push_res)

        on_fail = params.get("on_fail")
        if on_fail:
            if isinstance(on_fail, dict):
                on_fail = [on_fail]
            for eff in on_fail:
                etype = eff.get("type")
                eparams = eff.get("params", {})
                if etype:
                    out.extend(self.execute(etype, eparams, context, item_node=item_node, game_state=game_state))

    return out


HANDLERS = {
    "push_actor": handle_push_actor,
    "hazard": handle_hazard,
    "current_push": handle_hazard,
}
