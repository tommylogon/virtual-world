/**
 * stream-filters.js — filtering, actor/area scoping, search (task-340)
 *
 * Extracted from event-stream.js; adds stream search and area-filter
 * persistence across reloads. Loaded BEFORE event-stream.js.
 */
class StreamFilters {
    constructor(bus) {
        this._bus = bus;
        this.areaFilter = null;
    }

    /** Re-filter the event stream — hide/show existing bubbles. */
    applyFilters() {
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
            narrated: config.filterSystem,
            crisis: config.filterSystem,
            prune: config.filterSystem,
            system: config.filterSystem,
            error: config.filterSystem,
            rawllm: config.filterRawLLM
        };
        const agentFilter = document.getElementById('stream-agent-filter')?.value || '';
        const showTick = document.getElementById('filter-tick')?.checked ?? true;
        const searchEl = document.getElementById('stream-search');
        const query = (searchEl?.value || '').trim().toLowerCase();
        for (const child of streamEl.children) {
            if (child.classList.contains('stream-scope-banner')) continue;
            if (child.classList.contains('timeline-scrubber') || child.classList.contains('turn-queue-strip')) continue;
            if (child.classList.contains('turn-card')) {
                const actor = child.getAttribute('data-actor');
                let visible = !agentFilter || actor === agentFilter;
                if (visible && query) visible = child.textContent.toLowerCase().includes(query);
                child.style.display = visible ? '' : 'none';
                const body = child.querySelector('.turn-card-body');
                if (body && visible && !query) {
                    let cardHasVisible = false;
                    for (const bubble of body.children) {
                        if (bubble.classList.contains('stream-scope-banner')) continue;
                        const show = this._shouldShowBubble(bubble, filters, agentFilter, this.areaFilter);
                        bubble.style.display = show ? '' : 'none';
                        if (show) cardHasVisible = true;
                        const tickEl = bubble.querySelector('.bubble-tick');
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
            if (show && query) show = child.textContent.toLowerCase().includes(query);
            child.style.display = show ? '' : 'none';
            const tickEl = child.querySelector('.bubble-tick');
            if (tickEl) tickEl.style.display = showTick ? '' : 'none';
        }
        if (query) {
            const visibleCards = [...streamEl.querySelectorAll('.turn-card')]
                .filter(c => c.style.display !== 'none').length;
            const countEl = document.getElementById('stream-search-count');
            if (countEl) countEl.textContent = `${visibleCards} match${visibleCards === 1 ? '' : 'es'}`;
        } else {
            const countEl = document.getElementById('stream-search-count');
            if (countEl) countEl.textContent = '';
        }
    }

    _shouldShowBubble(bubble, filters, agentFilter, areaFilter) {
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

    setAgentFilter() { this.applyFilters(); }

    noteActor(name) {
        if (!this._bus._knownActors.has(name)) {
            this._bus._knownActors.add(name);
            this.updateAgentFilterDropdown();
        }
    }

    updateAgentFilterDropdown() {
        const select = document.getElementById('stream-agent-filter');
        if (!select) return;
        const current = select.value;
        const sorted = [...this._bus._knownActors].sort();
        window.Lit.render(window.Lit.html`
            <option value="">All actors</option>
            ${sorted.map(a => window.Lit.html`<option value=${a} ?selected=${a === current}>${a}</option>`)}`,
            select);
    }

    toggleTickDisplay(show) {
        const streamEl = document.getElementById('event-stream');
        if (!streamEl) return;
        for (const child of streamEl.children) {
            const tickEl = child.querySelector('.bubble-tick');
            if (tickEl) tickEl.style.display = show ? '' : 'none';
        }
    }

    setAreaFilter(areaName) {
        this.areaFilter = areaName || null;
        try { localStorage.setItem('vw_area_filter', this.areaFilter || ''); } catch (e) {}
        this._renderScopeBanner();
        this.applyFilters();
    }

    clearAreaFilter() { this.setAreaFilter(null); }

    getAreaFilter() { return this.areaFilter; }

    /** Restore the persisted area filter after a reload (called post-restore). */
    restoreSaved() {
        let saved = '';
        try { saved = localStorage.getItem('vw_area_filter') || ''; } catch (e) {}
        if (saved) this.setAreaFilter(saved);
    }

    _renderScopeBanner() {
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
        for (const child of streamEl.children) {
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
