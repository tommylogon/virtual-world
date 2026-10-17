"""Template-context construction for trigger rendering.

Single owner of the template context block shared by execution and the
editor test-run path. Previously duplicated between ``execution.py`` and
``testing.py``; consolidated here so both paths read the same defaults.
"""

from typing import Any, Optional

from graph import Node


def build_template_context(
    item_node: Optional[Node] = None,
    game_state: Any = None,
    *,
    area_node: Optional[Node] = None,
    area_name: str = "",
    area_env: Optional[dict] = None,
    target_name: Optional[str] = None,
    context: Optional[dict] = None,
) -> dict:
    """Populate and return the trigger template context.

    Applies every default via ``setdefault`` so caller-provided values are
    preserved. Area resolution is the caller's responsibility when it needs
    item-based lookup; otherwise falls back to ``game_state.current_area``.
    """
    if context is None:
        context = {}
    context = dict(context)

    if area_env is None:
        area_env = {}

    if area_node is not None and not area_name:
        try:
            area_name = area_node.name
        except Exception:
            area_name = area_name or ""

    if area_node is None and not area_name and not area_env and game_state is not None:
        legacy_area = getattr(game_state, "current_area", None)
        if legacy_area is not None:
            area_name = getattr(legacy_area, "name", "") or ""
            area_env = getattr(legacy_area, "environment", {}) or {}

    context["item_node"] = item_node
    if game_state is not None:
        context["game_state"] = game_state

    context.setdefault(
        "game_time", game_state.get_current_time() if game_state else ""
    )
    context.setdefault(
        "time_ticks", str(game_state.time_ticks) if game_state else ""
    )
    context.setdefault(
        "turn_number", str(game_state.turn_number) if game_state else ""
    )
    context.setdefault(
        "player_name", game_state.active_player if game_state else ""
    )
    context.setdefault(
        "area_name",
        area_node.name if area_node is not None else (area_name or ""),
    )
    context.setdefault("item_name", item_node.name if item_node else "")
    context.setdefault(
        "item_state",
        item_node.properties.get("current_state", "") if item_node else "",
    )
    context.setdefault(
        "item_description",
        item_node.properties.get("description", "") if item_node else "",
    )
    context.setdefault("item_properties", item_node.properties if item_node else {})
    if item_node:
        context.setdefault(
            "item_params", item_node.properties.get("parameters", {})
        )
    if target_name is not None:
        context.setdefault("target_name", target_name)
    if game_state and getattr(game_state, "player", None):
        context.setdefault(
            "player_hp", str(game_state.player.vitals.get("HP", 0))
        )
        context.setdefault(
            "player_energy",
            str(game_state.player.vitals.get("Energy", 0)),
        )
        context.setdefault(
            "player_sanity",
            str(game_state.player.vitals.get("Sanity", 0)),
        )
    if area_env:
        context.setdefault("area_light", str(area_env.get("light", "")))
        context.setdefault("area_temp", str(area_env.get("temperature", "")))
        context.setdefault("area_smell", area_env.get("smell", ""))

    return context