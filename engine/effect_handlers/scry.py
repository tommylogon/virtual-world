"""Scry effect handler (task-320): far-sight vision of a distant area.

params:
  target (str) — area name to view.
  message (str) — narrative lead-in (default "You peer into the distance...").
  fail_message (str) — used when the target can't be resolved.

game_state (the world) must provide: graph, lighting, area_description.
"""


def handle_scry(self, params, context, item_node=None, game_state=None):
    try:
        from engine.scry import scry_view
    except Exception:
        return [params.get("fail_message", "The vision shimmers and fades.")]
    target = (params.get("target") or "").strip()
    if not target or game_state is None:
        return [params.get("fail_message", "The vision shows nothing.")]
    try:
        view = scry_view(game_state, target)
        lead = params.get("message") or "You peer into the distance..."
        return [f"{lead}\n{view}"]
    except Exception:
        return [params.get("fail_message", "The vision shimmers and fades.")]


HANDLERS = {
    "scry": handle_scry,
}
