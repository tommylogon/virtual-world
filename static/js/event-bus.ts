/**
 * @module event-bus — tiny synchronous pub/sub used across the UI
 * @contributes AppEventBus (`on`/`off`/`once`/`emit`) and the `appEvents` singleton
 * @powers Event stream — the `log` event stream that feeds the turn feed, stream filters, and panels
 * @relates subscribed to by event-stream.js, turn-feed.js, changes-panel, and others
 * @docs docs/design/event-stream-design-recommendation.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
// NOTE: the type alias sits *below* the class on purpose. tsc drops a file's
// leading JSDoc when the first statement is type-only, and js_module_index.py
// reads @module out of the emitted .js. Keep a value declaration first.
class AppEventBus {
    _listeners: Map<string, EventCallback[]>;

    constructor() {
        this._listeners = new Map();
    }
    on(event: string, callback: EventCallback): () => void {
        if (!this._listeners.has(event)) this._listeners.set(event, []);
        this._listeners.get(event)!.push(callback);
        return () => this.off(event, callback);
    }
    off(event: string, callback: EventCallback): void {
        const list = this._listeners.get(event);
        if (!list) return;
        const idx = list.indexOf(callback);
        if (idx >= 0) list.splice(idx, 1);
    }
    emit(event: string, data?: unknown): void {
        const list = this._listeners.get(event);
        if (!list) return;
        for (const cb of list) {
            try { cb(data); } catch (e) { console.error(`[EventBus:${event}]`, e); }
        }
    }
}
const appEventsInstance = new AppEventBus();
(window as unknown as { appEvents: AppEventBus }).appEvents = appEventsInstance;

type EventCallback = (data?: unknown) => void;
