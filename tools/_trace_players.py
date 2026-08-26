"""Trace where VirtualWorld.players comes from."""
from virtual_world_engine import VirtualWorld
w = VirtualWorld()

# Check where players comes from
print("In __dict__:", 'players' in w.__dict__)

# Find it in the MRO
for cls in type(w).__mro__:
    if 'players' in cls.__dict__:
        obj = cls.__dict__['players']
        print(f"Found in {cls.__name__}: type={type(obj).__name__}")

# Check what it is
players = w.players
print(f"players type: {type(players).__name__}")
print(f"players len: {len(players)}")
print(f"pm players len: {len(w.player_manager.players)}")

# Check if add_player puts it in the right place
w.player_manager.add_player(type('P', (), {'name':'Test'})())
print(f"After add - players len: {len(w.players)}")
print(f"After add - pm players len: {len(w.player_manager.players)}")
