/**
 * @module event-bus — tiny synchronous pub/sub used across the UI
 * @contributes AppEventBus (`on`/`off`/`once`/`emit`) and the `appEvents` singleton
 * @powers the `log` event stream that feeds the turn feed, stream filters, and panels
 * @relates subscribed to by event-stream.js, turn-feed.js, changes-panel, and others
 * @docs docs/design/event-stream-design-recommendation.md
 */
class AppEventBus {
    constructor() {
        this._listeners = new Map();
    }
    on(event, callback) {
        if (!this._listeners.has(event)) this._listeners.set(event, []);
        this._listeners.get(event).push(callback);
        return () => this.off(event, callback);
    }
    off(event, callback) {
        const list = this._listeners.get(event);
        if (!list) return;
        const idx = list.indexOf(callback);
        if (idx >= 0) list.splice(idx, 1);
    }
    emit(event, data) {
        const list = this._listeners.get(event);
        if (!list) return;
        for (const cb of list) {
            try { cb(data); } catch (e) { console.error(`[EventBus:${event}]`, e); }
        }
    }
}
window.appEvents = new AppEventBus();
