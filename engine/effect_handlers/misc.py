"""Miscellaneous effect handlers (message, scenario control, scheduling)."""


def handle_message(self, params, context, item_node=None, game_state=None):
    """Output a narrative message.

    game_state: unused.
    """
    msg = params.get("message", "")
    if not msg.strip():
        return []
    msg = self._render_template_fn(msg, context)
    return [msg]


def handle_end_scenario(self, params, context, item_node=None, game_state=None):
    """Set the scenario-ended flag.

    game_state must provide: game_state.scenario_ended (writable attribute)
    """
    if game_state is not None:
        game_state.scenario_ended = True
    return [params.get("message", "The scenario has ended.")]


def handle_restart_scenario(self, params, context, item_node=None, game_state=None):
    """Set both the scenario-ended and restart-requested flags.

    game_state must provide:
      game_state.scenario_ended (writable)
      game_state._restart_requested (writable)
    """
    if game_state is not None:
        game_state.scenario_ended = True
        game_state._restart_requested = True
    return [params.get("message", "The scenario will restart.")]


def handle_schedule_trigger(self, params, context, item_node=None, game_state=None):
    """Queue a trigger fire N ticks in the future (task-90).

    Pure scheduling: this effect only records when *and on which node* the
    delayed fire happens. What actually occurs is defined by the target
    node's ``on_delayed`` trigger, reusing all normal effect types.

    params:
      delay_ticks (int) — ticks from now until the fire.
      target (str, optional) — item/node name **or** graph node ID whose
          ``on_delayed`` triggers should run. Defaults to the node the
          scheduling trigger sits on (``item_node``).

    game_state must provide:
      game_state.time_ticks          -- current tick count
      game_state.schedule_delayed(fire_tick, target_node_id,
                                  trigger_type, label) -- queue hook
    """
    if game_state is None:
        return []
    try:
        delay = max(1, int(params.get("delay_ticks", 1)))
    except (ValueError, TypeError):
        delay = 1

    # Resolve the target node: explicit name/ID, else the trigger's parent.
    target = params.get("target", "")
    target_node = None
    if target:
        needle = str(target).lower()
        for node in self.graph.nodes.values():
            if node.id.lower() == needle or (node.name or "").lower() == needle:
                target_node = node
                break
    if target_node is None:
        target_node = item_node
    if target_node is None:
        return []

    fire_tick = game_state.time_ticks + delay
    label = f"{target_node.name} in {delay} tick(s)"
    game_state.schedule_delayed(fire_tick, target_node.id, "on_delayed", label)
    return []


HANDLERS = {
    "message": handle_message,
    "end_scenario": handle_end_scenario,
    "restart_scenario": handle_restart_scenario,
    "schedule_trigger": handle_schedule_trigger,
}
