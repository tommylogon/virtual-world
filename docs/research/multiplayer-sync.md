# Multiplayer & State Synchronization — Research

## The Problem
Virtual World supports multiple human players via the turn queue, but this is not true multiplayer. Each human acts in sequence, and there's no real-time state synchronization, conflict resolution, or shared experience.

**Current state:**
- Turn-based: humans take turns, same as NPCs
- No real-time updates across clients
- No conflict resolution (what if two humans try to take the same item?)
- No spectator mode or shared viewing

**Target state:**
- Multiple humans can be in the same world simultaneously
- State changes broadcast to all relevant clients
- Conflicts resolved deterministically
- LLM NPCs interact with all players consistently

## Architecture Options

### 1. Authoritative Server (Current Direction)
**How it works:** Backend is the single source of truth. All state changes go through the server. Clients send intents, server broadcasts state.

**Pros:**
- Prevents cheating
- Consistent state for all players
- LLM NPCs see the same world regardless of which player interacts

**Cons:**
- Higher latency (client → server → client)
- More complex backend
- Server becomes bottleneck at scale

**VW fit:** VW already has a Flask backend. This is the natural evolution.

### 2. Peer-to-Peer (Not Recommended for VW)
**How it works:** Clients sync state directly. One client is "host."

**Pros:**
- No server infrastructure
- Low latency for local players

**Cons:**
- Cheating (host can modify state)
- Desync risk
- Host leaving = game over

**VW fit:** Not suitable. VW needs authoritative state for LLM NPCs.

### 3. Hybrid (Best for VW)
**How it works:**
- Backend authoritative for world state and LLM NPCs
- Client-side prediction for own player's actions
- Server reconciliation when state diverges

**Pros:**
- Responsive feel for local player
- Consistent world state
- LLM NPCs work naturally

**Cons:**
- Complex reconciliation logic
- Requires careful state design

## Key Technical Challenges

### 1. LLM NPC Consistency
**Problem:** If two players talk to the same NPC simultaneously, what happens?

**Options:**
- **Queue NPC interactions:** NPC processes one at a time, others wait
- **Parallel with locking:** NPC can handle one interaction per "thread," others queue
- **Instance splitting:** Create temporary NPC copies for each player (dangerous — inconsistent state)

**Recommended:** Queue with priority. Human players get priority over NPC autonomous actions.

### 2. State Broadcast Granularity
**Problem:** Broadcasting full state every tick is wasteful. Broadcasting too little causes stale UIs.

**Solution:** Event-sourced state updates
```json
{
  "type": "npc_spoke",
  "character": "Lyrie",
  "speech": "The door is locked.",
  "timestamp": 12345
}
```

Clients apply events to their local state. Missing events are fetched on reconnect.

### 3. Conflict Resolution
**Problem:** Two players try to take the same item, open the same door, etc.

**Solution:** First-intent-wins with server arbitration
```python
@app.route('/api/action', methods=['POST'])
def handle_action():
    player = get_player(request)
    action = parse_action(request)
    
    # Check if action is still valid
    if not world.can_perform(action, player):
        return {"success": False, "message": "Too late — someone else got there first."}
    
    # Apply action
    world.apply(action, player)
    broadcast_state_change(action, player)
```

### 4. LLM Context Consistency
**Problem:** NPCs in multiplayer need to know about all players, not just one.

**Solution:** NPC context includes all visible players
```
=== PEOPLE HERE ===
- Lyrie (awake) — a close friend
- The stranger (awake) — unknown
- Miki (awake) — suspicious
```

NPCs address all players in their responses, not just the one who triggered the turn.

## State Synchronization Design

### Event Stream (Existing)
VW already has an event stream. This is the natural backbone for multiplayer sync.

**Event types:**
- `player_action` — human or NPC took an action
- `state_change` — world state updated
- `npc_turn` — NPC took a turn
- `chat` — player/NPC speech
- `system` — game events (turn advance, decay)

### Delta Compression
Instead of broadcasting full world state, broadcast diffs:
```json
{
  "type": "delta",
  "changes": [
    {"node": "item_rusty_key", "property": "current_state", "from": "normal", "to": "taken"},
    {"node": "player_alice", "property": "carrying", "add": "rusty_key"}
  ]
}
```

### Client Reconciliation
```javascript
class GameClient {
    constructor() {
        this.localState = {};
        this.pendingActions = [];
    }
    
    sendAction(action) {
        // Optimistic update
        this.applyLocal(action);
        this.pendingActions.push(action);
        
        // Send to server
        fetch('/api/action', {action}).then(response => {
            if (response.success) {
                this.pendingActions.shift();
            } else {
                // Rollback
                this.rollback(action);
            }
        });
    }
}
```

## Recommended VW Multiplayer Architecture

### Phase 1: Room-Based Sync (1-2 weeks)
- Players in the same area share a SocketIO room
- State changes broadcast to room only
- Other areas don't receive updates (bandwidth + privacy)

### Phase 2: Conflict Resolution (2-3 weeks)
- Server validates all actions before applying
- First-intent-wins for contested resources
- Clear feedback when action fails due to conflict

### Phase 3: Spectator Mode (1 week)
- Observers can watch a game session
- Read-only access to event stream
- Useful for streaming, debugging, tutorials

### Phase 4: Persistent Multiplayer (4-6 weeks)
- World state persists across sessions
- Multiple sessions can run simultaneously
- NPCs remember all players, not just one

## Key Insight
**Multiplayer for LLM-driven games is fundamentally different from traditional multiplayer.** In a traditional game, you sync player positions and actions. In an LLM game, you also need to sync:
- NPC conversation state (who said what to whom)
- NPC memories (what does this NPC know about each player?)
- Relationship state (how does each NPC feel about each player?)

The state is richer, the sync requirements are stricter, and the cost (LLM calls per player) is higher. Design for this from the start.
