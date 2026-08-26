# UI & Display

## Vital Bar

- Range 25–45°C mapped to 0–100%: `((value − 25) / 20) × 100`
- °C suffix on numeric display
- Color-coded bar:

| Core Temp | Color | Hex |
|-----------|-------|-----|
| < 33°C (danger) | Red | `#f85149` |
| 33–34°C (cold) | Blue | `#58a6ff` |
| 35–39°C (safe) | Green | `#3fb950` |
| 40°C (warm) | Yellow | `#e3b341` |
| > 40°C (danger) | Red | `#f85149` |

## Narrative Tiers

| Core Temp | Description |
|-----------|-------------|
| < 33°C | "shivering uncontrollably — hypothermia setting in" |
| 33–34°C | "shivering violently from the cold" |
| 35°C | "cold and shivering" |
| 38–39°C | "feeling very hot" |
| 40–41°C | "dangerously overheated" |
| > 42°C | "heat is overwhelming — about to collapse" |

## Environment Description

Area descriptions and temperature warnings use **effective temperature** (feels-like after insulation), not raw ambient. From `area_description.py` using the authoritative `temperature_description()` and `temperature_warning()` functions:

| Feels Like | env_summary text | Warning text |
|------------|-----------------|--------------|
| ≥60°C | "The heat is infernal — you can't breathe." | "You are burning! Seek shelter or die!" |
| ≥50°C | "Blazing heat — the air shimmers." | "The heat is cooking you alive!" |
| ≥40°C | "Scorching hot." | "The intense heat is draining your energy!" |
| ≥35°C | "Very hot." | "You're overheating — find shade or water." |
| ≥30°C | "Hot." | "It's quite hot; you're feeling thirsty." |
| ≥25°C | "Warm." | (none) |
| ≥18°C | "Pleasant." | (none) |
| ≥12°C | "Cool." | (none) |
| ≥5°C | "Chilly." | (none) |
| ≥0°C | "Cold." | "The cold is biting." |
| ≥-10°C | "Freezing." | "It's freezing! You need to warm up." |
| ≥-25°C | "Bitterly cold." | "The cold is sapping your strength." |
| ≥-50°C | "Arctic — the cold is lethal." | "Hypothermia is imminent — find warmth now!" |
| < -50°C | "Deadly cold — nothing survives." | "You are freezing to death!" |

## Graph Overlay

Rooms colored by environment temperature in the graph heat overlay:
- ≤ -20°C: dark blue
- -5–5°C: blue
- 15°C: lighter blue
- 25°C: neutral
- 35°C: orange
- 45°C: dark orange
- > 45°C: red

## UI Panels

- Area temperature is displayed in the room info panel
- Body temperature is visible in the player stats panel
- Temperature-related effects (thirst, energy, HP changes) are logged as game messages
- Environment inspector shows temperature with the other environment properties

## Key Code Locations

| Concern | File | Lines |
|---------|------|-------|
| Temperature description (14 bands) | `area_description.py` | `temperature_description()`, `temperature_warning()` |
| Area descriptions | `area_description.py` | 141-230 |
| Feels-like serialization | `serialization.py` | `_compute_feels_like()` |
| Vital detail API | `routes/players.py` | 361-432 |
| Frontend vital bar | `agent-view.js` | 233-275 |
| Frontend narrative | `agent-engine.js` | 180-184 |
| Frontend alerts | `ui-controller.js` | 118-119 |
| Graph heat overlay | `network-manager.js` | 375-386 |
