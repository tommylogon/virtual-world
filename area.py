# area.py — Fixed by Yuki
class Area:
    def __init__(self, name, description, items, exits=None, environment=None):
        self.name = name
        self.description = description
        self.items = list(items) if items else []  # COPY, not reference
        self.exits = dict(exits) if exits else {}  # COPY, not reference
        self.environment = dict(environment) if environment else {
            "light": 80,
            "temperature": 21,
            "air": "fresh",
            "smell": "neutral",
            "noise": "quiet"
        }