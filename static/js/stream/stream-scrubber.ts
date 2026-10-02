/**
 * stream-scrubber.js — timeline minimap for the event stream (task-340)
 *
 * A sticky strip showing the shape of the session: one segment per top-level
 * entry, colored by dominant kind (teal=speech/thought, red=error/crisis,
 * blue=action). Click anywhere to jump; a purple head tracks scroll position.
 *
 * @module stream/stream-scrubber — timeline minimap
 * @contributes StreamScrubber: per-entry colour segments, click-to-jump, scroll head
 * @powers Event stream — navigating a long session's stream at a glance
 * @relates loaded before event-stream.js
 * @docs docs/virtualWorld/UI & Settings/Event Log Export.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
class StreamScrubber {
    _bus: unknown;
    MAX_SEGS: number;
    _rebuildTimer: ReturnType<typeof setTimeout> | null;

    constructor(bus: unknown) {
        this._bus = bus;
        this.MAX_SEGS = 120;
        this._rebuildTimer = null;
    }

    el(): HTMLDivElement | null {
        const streamEl = document.getElementById('event-stream');
        if (!streamEl) return null;
        let bar = streamEl.querySelector<HTMLDivElement>('.timeline-scrubber');
        if (!bar) {
            // A local, so the click/scroll closures below do not re-read the
            // `let` that is still null until the assignment at the end.
            const created = document.createElement('div');
            created.className = 'timeline-scrubber';
            created.title = 'Session timeline — click to jump';
            const head = document.createElement('div');
            head.className = 'scrub-head';
            created.appendChild(head);
            created.addEventListener('click', (e) => {
                const rect = created.getBoundingClientRect();
                const ratio = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width));
                streamEl.scrollTop = ratio * streamEl.scrollHeight - 40;
            });
            streamEl.addEventListener('scroll', () => this._syncHead(created), { passive: true });
            streamEl.insertBefore(created, streamEl.firstChild);
            bar = created;
        }
        return bar;
    }

    /** Debounced rebuild — called from log paths. */
    scheduleRebuild(): void {
        if (this._rebuildTimer) return;
        this._rebuildTimer = setTimeout(() => { this._rebuildTimer = null; this.rebuild(); }, 800);
    }

    rebuild(): void {
        const streamEl = document.getElementById('event-stream');
        if (!streamEl) return;
        const bar = this.el();
        if (!bar) return;
        const entries: Element[] = [];
        for (const child of streamEl.children) {
            const cls = child.className || '';
            if (cls.includes('timeline-scrubber') || cls.includes('stream-scope-banner') || cls.includes('turn-queue-strip')) continue;
            entries.push(child);
        }
        // Rebuild segment row (keep the head element at index 0)
        const head = bar.querySelector('.scrub-head');
        while (bar.childNodes.length > 1) bar.removeChild(bar.lastChild!);
        const bucketCount = Math.min(this.MAX_SEGS, Math.max(entries.length, 1));
        const perBucket = entries.length / bucketCount;
        for (let i = 0; i < bucketCount; i++) {
            const start = Math.floor(i * perBucket);
            const end = Math.max(start + 1, Math.floor((i + 1) * perBucket));
            let kind = '';
            for (let j = start; j < end && j < entries.length; j++) {
                kind = this._classify(entries[j], kind);
            }
            const seg = document.createElement('div');
            seg.className = `seg${kind ? ' ' + kind : ''}`;
            bar.appendChild(seg);
        }
        bar.appendChild(head!);
        this._syncHead(bar);
    }

    _classify(node: Element, current: string): string {
        const cls = node.className || '';
        const text = cls.includes('turn-card') ? (node.querySelector('.turn-card-body')?.textContent || '') : (node.textContent || '');
        if (/parse error|⚠|crisis|❌|failed/i.test(text) && current !== 'crisis') return 'crisis';
        if (cls.includes('msg-bubble-error')) return 'crisis';
        if (/💬|"|\bsay|\bwhisper/i.test(text) && current === '') return 'speech';
        if (cls.includes('msg-bubble-action')) return current === '' ? 'hot' : current;
        return current;
    }

    _syncHead(bar: HTMLElement): void {
        const streamEl = document.getElementById('event-stream');
        if (!streamEl || !bar) return;
        const head = bar.querySelector<HTMLElement>('.scrub-head');
        if (!head) return;
        const range = streamEl.scrollHeight - streamEl.clientHeight;
        const ratio = range > 0 ? streamEl.scrollTop / range : 0;
        head.style.left = `${(ratio * 100).toFixed(2)}%`;
    }
}
