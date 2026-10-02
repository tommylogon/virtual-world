/**
 * stream-filters.js — filtering, actor/area scoping, search (task-340)
 *
 * Extracted from event-stream.js; adds stream search and area-filter
 * persistence across reloads. Loaded BEFORE event-stream.js.
 *
 * @module stream/stream-filters — filtering, scoping, and search
 * @contributes StreamFilters: kind filters, actor/area scoping, stream search, persisted area filter
 * @powers Event stream — narrowing the event stream to one character, one area, or a text query
 * @relates loaded before event-stream.js; driven by the stream toolbar
 * @docs docs/virtualWorld/UI & Settings/Event Log Export.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
class StreamFilters {
    /**
     * The owning stream bus (it holds the known-actor roster) and the area name
     * the stream is scoped to, or null. Declared as `declare`d fields so the
     * emit stays exactly the original constructor assignments — a plain class
     * field would emit an extra `_bus;` line that did not exist before.
     */
    declare _bus: StreamBusLike;
    declare areaFilter: string | null;

    constructor(bus: StreamBusLike) {
        this._bus = bus;
        this.areaFilter = null;
    }

    /** Re-filter the event stream — hide/show existing bubbles. */
    applyFilters(): void {
        const streamEl = document.getElementById('event-stream');
        if (!streamEl) return;
        const filters = {
            thought: config.filterThoughts,
            speech: config.filterSpeech,
            action: config.filterActions,
            emote: config.filterActions,
            result: config.filterActions,
            whisper: config.filterSpeech,
            reflection: config.filterThoughts,
            recall: config.filterRecalls,
            npc: config.filterNpc,
            narrated: config.filterSystem,
            crisis: config.filterSystem,
            prune: config.filterSystem,
            system: config.filterSystem,
            error: config.filterSystem,
            rawllm: config.filterRawLLM
        };
        const agentFilter = (document.getElementById('stream-agent-filter') as HTMLInputElement | null)?.value || '';
        const showTick = (document.getElementById('filter-tick') as HTMLInputElement | null)?.checked ?? true;
        const searchEl = document.getElementById('stream-search') as HTMLInputElement | null;
        const query = (searchEl?.value || '').trim().toLowerCase();
        for (const child of streamEl.children as HTMLCollectionOf<HTMLElement>) {
            if (child.classList.contains('stream-scope-banner')) continue;
            if (child.classList.contains('timeline-scrubber') || child.classList.contains('turn-queue-strip')) continue;
            if (child.classList.contains('turn-card')) {
                const actor = child.getAttribute('data-actor');
                let visible = !agentFilter || actor === agentFilter;
                if (visible && query) visible = (child.textContent || '').toLowerCase().includes(query);
                child.style.display = visible ? '' : 'none';
                const body = child.querySelector('.turn-card-body');
                if (body && visible && !query) {
                    let cardHasVisible = false;
                    for (const bubble of body.children as HTMLCollectionOf<HTMLElement>) {
                        if (bubble.classList.contains('stream-scope-banner')) continue;
                        const show = this._shouldShowBubble(bubble, filters, agentFilter, this.areaFilter);
                        bubble.style.display = show ? '' : 'none';
                        if (show) cardHasVisible = true;
                        const tickEl = bubble.querySelector<HTMLElement>('.bubble-tick');
                        if (tickEl) tickEl.style.display = showTick ? '' : 'none';
                    }
                    if (!cardHasVisible) child.style.display = 'none';
                }
                continue;
            }
            if (child.classList.contains('tick-divider')) {
                child.style.display = this.areaFilter ? 'none' : '';
                continue;
            }
            let show = this._shouldShowBubble(child, filters, agentFilter, this.areaFilter);
            if (show && query) show = (child.textContent || '').toLowerCase().includes(query);
            child.style.display = show ? '' : 'none';
            const tickEl = child.querySelector<HTMLElement>('.bubble-tick');
            if (tickEl) tickEl.style.display = showTick ? '' : 'none';
        }
        if (query) {
            const visibleCards = [...streamEl.querySelectorAll<HTMLElement>('.turn-card')]
                .filter(c => c.style.display !== 'none').length;
            const countEl = document.getElementById('stream-search-count');
            if (countEl) countEl.textContent = `${visibleCards} match${visibleCards === 1 ? '' : 'es'}`;
        } else {
            const countEl = document.getElementById('stream-search-count');
            if (countEl) countEl.textContent = '';
        }
    }

    _shouldShowBubble(bubble: HTMLElement, filters: Record<string, unknown>, agentFilter: string, areaFilter: string | null): boolean {
        for (const [type, enabled] of Object.entries(filters)) {
            if (bubble.classList.contains(`msg-bubble-${type}`)) {
                if (type === 'thought') { if (!config.filterThoughts) return false; break; }
                if (!enabled) return false;
                break;
            }
        }
        if (agentFilter) {
            const bubbleActor = bubble.getAttribute('data-actor');
            if (bubbleActor !== agentFilter) return false;
        }
        if (areaFilter) {
            const bubbleArea = bubble.getAttribute('data-stream-area');
            if ((bubbleArea || '') !== areaFilter) return false;
        }
        return true;
    }

    setAgentFilter(): void { this.applyFilters(); }

    noteActor(name: string): void {
        if (!this._bus._knownActors.has(name)) {
            this._bus._knownActors.add(name);
            this.updateAgentFilterDropdown();
        }
    }

    updateAgentFilterDropdown(): void {
        const select = document.getElementById('stream-agent-filter') as HTMLSelectElement | null;
        if (!select) return;
        const current = select.value;
        const sorted = [...this._bus._knownActors].sort();
        window.Lit.render(window.Lit.html`
            <option value="">All actors</option>
            ${sorted.map(a => window.Lit.html`<option value=${a} ?selected=${a === current}>${a}</option>`)}`,
            select);
    }

    toggleTickDisplay(show: boolean): void {
        const streamEl = document.getElementById('event-stream');
        if (!streamEl) return;
        for (const child of streamEl.children as HTMLCollectionOf<HTMLElement>) {
            const tickEl = child.querySelector<HTMLElement>('.bubble-tick');
            if (tickEl) tickEl.style.display = show ? '' : 'none';
        }
    }

    setAreaFilter(areaName: string | null): void {
        this.areaFilter = areaName || null;
        try { localStorage.setItem('vw_area_filter', this.areaFilter || ''); } catch (e) {}
        this._renderScopeBanner();
        this.applyFilters();
    }

    clearAreaFilter(): void { this.setAreaFilter(null); }

    getAreaFilter(): string | null { return this.areaFilter; }

    /** Restore the persisted area filter after a reload (called post-restore). */
    restoreSaved(): void {
        let saved = '';
        try { saved = localStorage.getItem('vw_area_filter') || ''; } catch (e) {}
        if (saved) this.setAreaFilter(saved);
    }

    _renderScopeBanner(): void {
        const streamEl = document.getElementById('event-stream');
        if (!streamEl) return;
        const existing = streamEl.querySelector('.stream-scope-banner');
        if (existing) existing.remove();
        const emptyEl = streamEl.querySelector('.stream-scope-empty');
        if (emptyEl) emptyEl.remove();
        if (!this.areaFilter) return;
        const banner = document.createElement('div');
        banner.className = 'stream-scope-banner';
        const label = document.createElement('span');
        label.textContent = `📌 Scoped to: ${this.areaFilter}`;
        const clearBtn = document.createElement('button');
        clearBtn.textContent = '×';
        clearBtn.title = 'Clear area filter';
        clearBtn.addEventListener('click', () => this.clearAreaFilter());
        banner.append(label, clearBtn);
        streamEl.insertBefore(banner, streamEl.firstChild);

        let anyVisible = false;
        for (const child of streamEl.children as HTMLCollectionOf<HTMLElement>) {
            if (child.classList.contains('stream-scope-banner')) continue;
            if (child.classList.contains('stream-scope-empty')) continue;
            if (child.classList.contains('timeline-scrubber') || child.classList.contains('turn-queue-strip')) continue;
            if (child.style.display === 'none') continue;
            anyVisible = true;
            break;
        }
        if (!anyVisible) {
            const note = document.createElement('div');
            note.className = 'stream-scope-empty';
            note.textContent = `No events recorded in "${this.areaFilter}" yet. Check the 📜 Area Event Log in the inspector.`;
            streamEl.insertBefore(note, banner.nextSibling);
        }
    }
}

/*
 * Type declarations live below the first value statement on purpose: TypeScript
 * drops a file's leading JSDoc block when the first statement is type-only, and
 * `tools/js_module_index.py` reads `@module` out of the emitted `.js`.
 */

/** The slice of the stream bus StreamFilters reads: the known-actor roster. */
interface StreamBusLike {
    _knownActors: Set<string>;
}
