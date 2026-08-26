# item.py
class Item:
    def __init__(self, name, description, actions, uses=-1, effect_target=None, effect_stat=None, effect_amount=0, action_costs=None):
        self.name = name
        self.description = description
        self.actions = actions

        # Optional per-action cost definitions. Example: {"use": {"time": 2, "energy": 5}}
        self.action_costs = action_costs or {}

        self.uses = uses                 # -1 for infinite, > 0 for consumable
        self.effect_target = effect_target # 'player' or 'area'
        self.effect_stat = effect_stat     # e.g., 'HP', 'light', 'smell'
        self.effect_amount = effect_amount # e.g., 20, -10, or "lavender"