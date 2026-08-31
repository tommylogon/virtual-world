"""Scry / far-sight view (task-320).

Builds a natural-language view of a DISTANT area without touching the shared
observer pipeline: no walk/meeting registration, no agent-prompt drift — the
scry output is a frozen narrative glance assembled from the target area's own
rendered description + ambient light + exit summary.
"""


def scry_view(gs, target_name: str) -> str:
    """Render a distant area as seen through a scrying effect.

    ``gs`` is the VirtualWorld (game_state) — must expose ``graph``,
    ``lighting`` and ``area_description``.
    """
    target_node = None
    needle = str(target_name).lower().strip()
    for node in gs.graph.nodes.values():
        if node.type == "area" and (needle in node.name.lower() or needle in node.id.lower()):
            target_node = node
            break
    if target_node is None:
        raise ValueError(f"No area called '{target_name}'.")

    env = target_node.properties.get("environment", {}) or {}
    ambient = 80
    try:
        ambient = gs.lighting.get_ambient_light(target_node.id, env)
    except Exception:
        pass
    level = gs.lighting.light_to_level(ambient)

    desc = ""
    try:
        desc = gs.area_description._render_node(target_node) or ""
    except Exception:
        desc = str(target_node.properties.get("description", "") or "")

    lines = [f"You catch sight of {target_node.name}."]
    if level == "pitch_black":
        lines.append("It is pitch black there — nothing can be made out.")
    elif level == "dim":
        lines.append("The light there is dim — shapes only, no detail.")
    else:
        lines.append(desc if desc else "It looks empty.")

    try:
        exits = gs.area_description.build_exits_for_area(target_node.name)
        if exits:
            parts = []
            for handle, data in list(exits.items())[:8]:
                parts.append(f"{handle} ({data.get('target', 'floor')})")
            lines.append("Paths: " + ", ".join(parts) + ".")
    except Exception:
        pass
    return "\n".join(l for l in lines if l)
