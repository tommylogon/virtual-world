"""Integration module: viwo brain + Project Zomboid bridge.

This hooks the existing `NPCBehaviorSystem` and `memory`/`traits` layer
into `PZAdapter` so viwo characters can live inside PZ.
"""
from pz_adapters.adapter import PZAdapter
from engine.player_manager import PlayerManager
from engine.npc_behaviors import NPCBehaviorSystem

class PZNPCAdapterEngine:
    """Wraps PZAdapter around viwo's engine objects."""
    def __init__(self, pz_adapter: PZAdapter, player_manager: PlayerManager):
        self.adapter = pz_adapter
        self.pm = player_manager
        # The hook point: when viwo's tick loop calls process_simple_npcs,
        # a PZ-backed character overrides that call with adapter.poll_and_update.
    def observe_npc(self, npc_name: str, memory_store, text: str, importance: int = 3):
        self.adapter.observe(memory_store, npc_name, text, importance=importance)
    def tick_pz_npc(self, npc_name, memory_store):
        return self.adapter.poll_and_update(memory_store, npc_name)
