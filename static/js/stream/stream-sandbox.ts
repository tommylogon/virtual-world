/**
 * stream-sandbox.js - Play Mode sandbox boundary for the event stream
 *
 * task-885: Play Mode is a transient simulation. Its rows describe a world that
 * Stop throws away, so entering parks the authored log and starts a clean one,
 * and stopping discards the run and puts the authored log back exactly as it
 * was. Extracted from event-stream.js; loaded BEFORE it.
 *
 * @module stream/stream-sandbox - Play Mode sandbox boundary for the stream
 * @contributes StreamSandbox: park/restore the authored stream across a Play Mode run
 * @powers Play Mode - a transient run cannot leave rows in the authored log
 * @relates loaded before event-stream.js; driven by ui/play-mode
 * @docs docs/virtualWorld/UI & Settings/Event Log Export.md
 */

/** What the authored stream looked like at the moment Play Mode started. */
interface StreamSandboxSnapshot {
    fragment: DocumentFragment;
    card: HTMLDivElement | null;
    cardActor: string | null;
    areaEventLog: Record<string, *FIX*[]>;
    characterState: Record<string, *FIX*>;
    knownActors: Set<string>;
    lineSeq: number;
    tickCounter: number;
    lastGap: { minutes: number; day: number } | null;
    rawResponses: *FIX*[];
    rawStreak: *FIX*;
    scrollTop: number;
}

class StreamSandbox {
    _bus: SandboxBus;
    _snap: StreamSandboxSnapshot | null;

    constructor(bus: SandboxBus) {
        this._bus = bus;
        this._snap = null;
    }

    isActive(): boolean {
        return this._snap !== null;
    }

    /** Forget a parked stream without restoring it (the world was replaced). */
    discard(): void {
        this._snap = null;
    }

    /**
     * Park the authored stream and start a clean one for the run.
     *
     * The live nodes are detached into a fragment instead of being re-rendered
     * from HTML, which keeps their listeners (turn-card collapse, raw-LLM
     * chips, choice buttons) and the identity of the open turn card. Chrome
     * rows are dropped rather than parked because they regenerate themselves
     * (the scrubber re-inserts on rebuild), and a half-written streaming chip
     * is transient by nature.
     */
    enter(): void {
        if (this._snap) return;
        const bus = this._bus;
        const streamEl = document.getElementById('event-stream');
        const fragment = document.createDocumentFragment();
        this._snap = {
            fragment,
            card: bus._cards.current,
            cardActor: bus._cards.actor,
            areaEventLog: bus._areaEventLog,
            characterState: bus._characterState,
            knownActors: bus._knownActors,
            lineSeq: bus._lineSeq,
            tickCounter: bus._tickCounter,
            lastGap: bus._lastGap,
            rawResponses: bus._rawllm._rawResponses,
            rawStreak: bus._rawllm._streak,
            scrollTop: streamEl ? streamEl.scrollTop : 0,
        };
        if (streamEl) {
            for (const el of Array.from(streamEl.children)) {
                const cls = el.className || '';
                const chrome = cls.includes('timeline-scrubber')
                    || cls.includes('stream-scope-banner')
                    || cls.includes('turn-queue-strip');
                if (chrome || (el as HTMLElement).dataset.type === 'stream') el.remove();
                else fragment.appendChild(el);
            }
        }
        // Per-world accumulators belong to the authored run; the sandbox gets
        // fresh ones and the originals are handed back on exit.
        bus._areaEventLog = {};
        bus._characterState = {};
        bus._knownActors = new Set<string>();
        bus._rawllm._rawResponses = [];
        bus._rawllm._streak = null;
        bus._streamSpans = {};
        bus._streamLabels = {};
        bus._isStreaming = false;
        bus._cards.close();
        bus._filters.updateAgentFilterDropdown();
        if (bus._scrubber) bus._scrubber.scheduleRebuild();
    }

    /**
     * Throw away the run and put the authored stream back: rows, open turn
     * card, line/tick counters, area log, raw-LLM chips and scroll position.
     * Called after the server has restored its snapshot, so the stream and the
     * world describe the same moment again.
     */
    exit(): void {
        const snap = this._snap;
        if (!snap) return;
        this._snap = null;
        const bus = this._bus;
        const streamEl = document.getElementById('event-stream');
        if (streamEl) {
            while (streamEl.firstChild) streamEl.removeChild(streamEl.firstChild);
            streamEl.appendChild(snap.fragment);
            streamEl.scrollTop = snap.scrollTop;
        }
        bus._areaEventLog = snap.areaEventLog;
        bus._characterState = snap.characterState;
        bus._knownActors = snap.knownActors;
        bus._lineSeq = snap.lineSeq;
        bus._tickCounter = snap.tickCounter;
        bus._lastGap = snap.lastGap;
        bus._rawllm._rawResponses = snap.rawResponses;
        bus._rawllm._streak = snap.rawStreak;
        bus._cards.current = snap.card;
        bus._cards.actor = snap.cardActor;
        bus._filters.updateAgentFilterDropdown();
        if (bus._scrubber) bus._scrubber.scheduleRebuild();
        // The 5 s persist timer has been writing sandbox rows to IndexedDB;
        // rewrite the stored log now so a refresh cannot resurrect them.
        bus._persistLog();
    }
}

interface SandboxBus {
    _cards: { current: HTMLDivElement | null; actor: string | null; close(): void };
    _filters: { updateAgentFilterDropdown(): void };
    _scrubber?: { scheduleRebuild(): void } | null;
    _rawllm: { _rawResponses: *FIX*[]; _streak?: *FIX* };
    _areaEventLog: Record<string, *FIX*[]>;
    _characterState: Record<string, *FIX*>;
    _knownActors: Set<string>;
    _lineSeq: number;
    _tickCounter: number;
    _lastGap: { minutes: number; day: number } | null;
    _streamSpans: Record<string, HTMLElement>;
    _streamLabels: Record<string, string>;
    _isStreaming: boolean;
    _persistLog(): Promise<void> | void;
}
