# engine/save_on.py
"""Trait × world-event consequences (Phase 3, task-trait-condition-system-v2).

The engine emits named events at natural moments (``crawl_tight_way``,
``enter_area``, ``loud_noise``, ...). Traits with a matching ``save_on`` entry
fire a saving throw; failures apply the listed ``on_fail`` effects (conditions +
vital deltas). Fully data-driven — no trait-specific code in the movement,
combat, or narration modules.

Event catalog (v1):

| Event           | Fires when                                             |
|-----------------|--------------------------------------------------------|
| crawl_tight_way | crawling through a tight/small passage (task-187)      |
| climb_way       | attempting a climb (success)                           |
| jump_way        | attempting a jump (success)                            |
| enter_area      | entering an area (tags via ``area_tags`` filter)       |
| see_item        | an item with matching ``item_tags`` becomes visible    |
| loud_noise      | loud noise in the current area                         |
| takes_damage    | character takes damage (extends wake-on-damage hook)   |
| alone_in_dark   | ambient light low AND no other character in area       |
"""

from typing import Optional


class SaveOnResolver:
    """Resolves ``save_on`` trait entries against emitted world events."""

    def __init__(self, game_state):
        self.gs = game_state

    def emit(self, player_name: str, event: str, context: Optional[dict] = None) -> list:
        """Emit a world event for one player.

        Returns narration lines from FAILED saves (successes are flavor-only —
        no mechanical effect). Context may carry ``source`` (used as the
        condition source, e.g. the area name a frightened character fears),
        ``area_tags``/``item_tags`` filters, and a ``fail_message``.
        """
        context = context or {}
        player = self.gs.players.get(player_name)
        if not player or not getattr(player, "traits", None):
            return []
        from engine.traits import TraitSystem
        entries = TraitSystem.get_save_on_entries(player, event, context)
        if not entries:
            return []
        lines = []
        for entry in entries:
            stat = entry.get("stat", "WIS")
            dc = int(entry.get("dc", 12))
            success, total, msg = self.gs.saving_throw(player, stat, dc)
            if success:
                continue
            for effect in entry.get("on_fail", []):
                if "condition" in effect:
                    source = effect.get("source") or context.get("source")
                    source_type = effect.get("source_type") or context.get("source_type")
                    player.add_condition(
                        effect["condition"],
                        duration=effect.get("duration"),
                        source=source,
                        source_type=source_type,
                        periodic=effect.get("periodic"),
                        ends_on=effect.get("ends_on"),
                    )
                elif "vital" in effect:
                    vital = effect["vital"]
                    if vital in player.vitals:
                        player.vitals[vital] = max(
                            0, min(100, player.vitals[vital] + int(effect.get("amount", 0)))
                        )
            lines.append(
                entry.get("fail_message") or context.get("fail_message")
                or f"{player.name} loses their nerve."
            )
        return lines
