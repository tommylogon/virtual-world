"""World decomposition: the global index and chunk load/unload (tasks 401/583).

`engine.world` holds the scale layer over the authoritative flat graph: a small
index that stays resident while individual scopes may be loaded or evicted.

@module __init__
@contributes module initialization and namespace exports
@docs none - package initialization
"""
