# Memory Deletion — Cannot Delete Individual Memories from Character Inspector

**Filed**: 2026-07-17
**Priority**: High
**Status**: Done — verified 2026-08-03. All four fix items in code: DELETE endpoint `routes/memories.py:66-75`, `api.js:332` `deletePlayerMemory`, guard logs `console.warn` instead of silent exit (`static/js/inspector/memory-view.js:150-158`), ID backfill on restore (`engine/serialization.py:179`, `player.py:352`). File references are stale (app.py:1648 / inspector.js / api.js:240 predate the routes/ + inspector/ split).

---

## Summary

The character inspector in the UI shows a 🗑 delete button for each memory entry, but clicking it fails to delete the memory. The backend DELETE endpoint exists and works, but the frontend call encounters an issue — likely the entry ID being empty or mismatched, or the frontend state not syncing properly after deletion.

## Current State

### Backend endpoint (`app.py:1648`)

```python
@app.route('/api/players/<name>/memories/entry/<entry_id>', methods=['DELETE'])
def delete_player_memory(name, entry_id):
    p = app.world.players.get(name)
    if not p:
        return jsonify({"error": "Player not found"}), 404
    old_len = len(p.memories)
    p.memories = [m for m in p.memories if m.get("id") != entry_id]
    if len(p.memories) == old_len:
        return jsonify({"error": "Entry not found"}), 404
    return jsonify({"status": "success"})
```

### Frontend call (`api.js:240`)

```javascript
static async deletePlayerMemory(name, entryId) {
    const resp = await fetch(`/api/players/${encodeURIComponent(name)}/memories/entry/${encodeURIComponent(entryId)}`, { method: 'DELETE' });
    ...
}
```

### Frontend delete handler (`inspector.js:2732`)

```javascript
_deleteMemory(charName, entryId) {
    if (!entryId) return;         // <-- GUARD: silently exits if no entryId
    ApiClient.deletePlayerMemory(charName, entryId).then(() => {
        worldState.fetch().then(() => this._reRender());
    });
}
```

### Memory entry display (`inspector.js:228`)

```javascript
const id = m.id || `mem_${i}`;
```

The memory ID is displayed using a fallback `mem_${i}` if `m.id` is missing. But the delete button sends `m.id || ''` — so if `m.id` is undefined/null, the entryId is an empty string, and the guard `if (!entryId) return;` silently aborts.

## Root Cause

Memories stored via `player.add_memory()` (called from `app.py:407-408`):

```python
memory_text = f"{cmd}: {final_output[:200]}"
p.add_memory(memory_text, world.time_ticks, importance=importance, memory_type='action')
```

In `player.py:180`, `add_memory()` generates an ID:

```python
self.memories.append({
    "id": str(uuid.uuid4())[:8],
    ...
})
```

However, some memories (especially those loaded from save data or created by the MemoryStore frontend) may lack the `id` field entirely. The frontend display uses a fallback `mem_${i}` for rendering but the delete function passes the actual `m.id` which could be `undefined`.

## Fix

1. **Ensure all memories have IDs**: Backfill missing IDs in `player.py` constructor or `add_memory()`
2. **Fix the frontend guard**: The `if (!entryId) return;` guard should not silently fail — it should log a warning or attempt to match by index
3. **Add migration**: For existing saves, add IDs to any memory entries that lack them on `from_dict()` restore
4. **Verify**: Delete button sends the correct entry ID, and refresh after delete succeeds

## Files Affected

- `player.py` — ensure `id` field on all memories during init/restore
- `virtual_world_engine.py` — memory restore in `from_dict()`, add ID backfill
- `static/js/inspector.js` — `_deleteMemory()`, improve guard and error handling
- `static/js/api.js` — `deletePlayerMemory()`, add error handling
