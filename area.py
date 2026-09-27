# area.py — Fixed by Yuki
class Area:
    def __init__(self, name, description, items, exits=None, environment=None):
        self.name = name
        self.description = description
        self.items = list(items) if items else []  # COPY, not reference
        self.exits = dict(exits) if exits else {}  # COPY, not reference
        self.environment = dict(environment) if environment else {
            "light": 80,
            # `temperature` is the **simulated** value: the engine rewrites it
            # every tick from the forecast, the propagation model and any heat
            # source, and a hand-set value cannot survive a tick. `base_temperature`
            # is the **authored** baseline — the world's own climate, in °C — and
            # the forecast adds its curve and its delta on top of it (task-553).
            # Two keys because they are two different facts: "this is a mountain
            # range" and "right now it is 6°C" are not the same statement, and a
            # save that carried only the second would lose the first.
            "base_temperature": 21.0,
            "temperature": 21,
            "air": "fresh",
            "smell": "neutral",
            "noise": "quiet"
        }