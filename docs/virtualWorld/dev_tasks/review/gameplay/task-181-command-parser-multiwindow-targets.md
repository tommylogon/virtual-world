# Task: Command Parser — Multi-Word `use X on Y` Targets

**Status**: In Review — implemented (verified 2026-08-08 code audit; moved from todo). `routes/action.py:290` joins the full remainder after `on` as the target (`target_name = ' '.join(tokens[on_idx + 1:])`), and quoted tokens become an explicit target+params pair for the inscribe path — multi-word targets like `dried flower crown` no longer truncate. Pending: dedicated backend test from the task's §3.

## Goal

Fix the parser so `use [item] on [target]` works with multi-word targets. Today
`routes/action.py:180-181` takes only the **single token** after `on` as the
target and dumps the rest into `params`:

```python
target_name = tokens[on_idx + 1] if on_idx + 1 < len(tokens) else ""
params = ' '.join(tokens[on_idx + 2:]) if on_idx + 2 < len(tokens) else None
```

Evidence from `event_log_2026-08-02T12-00-06.txt`:
- `use create flame on dry leaves` → target `"dry"` → `"You try to use the create flame on dry, but there's no purchase on it — it's purely decorative."`
- `use create flame on dried flower crown` → target `"dried"`, params `"flower crown"` → **`"You use the create flame on the dried, inscribing: "flower crown"."`** — it *inscribed* text onto her crown via the `params` path (`engine/item_actions.py:862-870`) instead of trying to ignite it.

Multi-word item/target names are everywhere in this world (`Short Forest Cape`,
`Dried Flower Crown (Crushed)`, `Stovepipe Leather Boots (Pair)`), so this
breaks real interactions.

## Changes

### 1. `routes/action.py` — `use` handler (lines 172-188)
- Resolve the target as the **full remainder** after `on` when the rest is
  unquoted: `target_name = ' '.join(tokens[on_idx + 1:])`.
- Only populate `params` when the tokenizer returned explicit **quoted tokens**
  (check `tokenize_command` in `routes/helpers.py` — confirm quotes merge into a
  single token). Rule:
  - If there are quoted tokens after `on` → first quoted token(s) = target,
    remaining quoted tokens = `params` (inscribing, etc.).
  - Otherwise → target = `' '.join(tokens[on_idx+1:])`, `params = None`.
- Never let `params` take precedence over a real target. Guard `on_idx + 1 >=
  len(tokens)` → "Use <item> on what?".

### 2. Audit other "on"/"with" parsers for the same truncation
- `rest ... on ...` (line 327-341): already joins the full remainder — verify,
  leave as-is.
- `attack ... with ...` (line 380-391): `weapon_name` already joins remainder —
  verify, leave as-is.
- `put X in Y` / `steal X from Y` (lines 238-255): `cmd.find` slicing — already
  full remainder — verify.
- `wear X under Y` (line 277-282): already splits on `" under "` — verify.

### 3. Tests
- Add cases to an existing test (`tools/test_all.cjs` or backend tests) covering:
  - `use create flame on dry leaves` → target = `dry leaves`
  - `use create flame on dried flower crown` → target = `dried flower crown` (no inscribe)
  - `use key on cellar_way` still resolves
  - quoted multi-word target still works if that path is kept

## Files Modified
- `routes/action.py`
- `routes/helpers.py` (only if `tokenize_command` needs quoted-token awareness)
- `tools/test_all.cjs` (or backend test file)
