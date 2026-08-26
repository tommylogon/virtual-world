---
group: Prompt & Narrative Quality
---
# Richer Vital Descriptions for "HOW YOU ARE"

**Filed**: 2026-07-29  
**Priority**: Medium  
**Status**: Done

---

## Summary

Replace flat vital statements like `"You are hungry."` with narrative descriptions that convey intensity and physical sensation.

### Current
```
=== HOW YOU ARE ===
You are hungry. You are thirsty.
```

### Target examples
- Hunger: *"Your stomach growls emptily."* / *"A dull ache of hunger gnaws at you."* / *"You feel faint from lack of food."*
- Thirst: *"Your throat is dry and sticky."* / *"Your lips are cracked from thirst."* / *"You desperately need water."*
- Bladder: Already updated with tiered thresholds — keep but make more sensory
- Energy: *"Your legs tremble with exhaustion."* / *"You feel alert and rested."*
- Temperature: *"The cold seeps into your bones."* / *"Sweat beads on your forehead."*

### Scope
- `static/js/agent/prompt-builder.js` — `describeVitals()` function
- Multiple narrative tiers per vital (matched to current threshold system)
- Keep + add to existing threshold logic, don't replace
