/**
 * timeline-bar.ts - Interactive Scenario Timeline & Branch Switcher Bar (task-980)
 *
 * Mounts a compact, fluid branch-lane bar inside #event-section (between the
 * filter bar and the scrubber) backed by /api/timeline/branches, /fork, /switch,
 * and /checkpoint.
 */
(() => {
    'use strict';

    interface BranchSummary {
        branch_id: string;
        parent_branch_id: string | null;
        label: string;
        fork_tick: number;
        fork_datetime?: string;
        checkpoint_ticks?: number[];
    }

    let _activeBranchId = 'main';
    let _branches: BranchSummary[] = [];
    let _barEl: HTMLDivElement | null = null;
    let _viewMode: 'log' | 'timeline' = 'log';
    let _dockedEl: HTMLDivElement | null = null;
    let _dockedHandle: { refresh: () => Promise<void> } | null = null;

    function _setViewMode(mode: 'log' | 'timeline'): void {
        _viewMode = mode;
        const streamEl = document.getElementById('event-stream');
        const parent = streamEl?.parentElement;
        if (!streamEl || !parent) return;
        const scrubber = parent.querySelector(':scope > .timeline-scrubber') as HTMLElement | null;

        if (mode === 'timeline') {
            streamEl.style.display = 'none';
            if (scrubber) scrubber.style.display = 'none';
            if (!_dockedEl || !parent.contains(_dockedEl)) {
                _dockedEl = document.createElement('div');
                _dockedEl.id = 'timeline-docked-host';
                _dockedEl.style.cssText = 'flex:1;min-height:280px;display:flex;flex-direction:column;overflow:hidden;';
                parent.insertBefore(_dockedEl, streamEl);
            }
            _dockedEl.style.display = 'flex';
            if (typeof (window as any).TimelineView?.mount === 'function') {
                void (window as any).TimelineView.mount(_dockedEl, { docked: true }).then((h: any) => {
                    _dockedHandle = h;
                });
            }
        } else {
            streamEl.style.display = '';
            if (scrubber) scrubber.style.display = '';
            if (_dockedEl) _dockedEl.style.display = 'none';
        }
        _render();
    }

    function _ensureBar(): HTMLDivElement | null {
        if (_barEl && document.body.contains(_barEl)) return _barEl;
        const streamEl = document.getElementById('event-stream');
        if (!streamEl || !streamEl.parentElement) return null;

        const bar = document.createElement('div');
        bar.id = 'timeline-branch-bar';
        bar.style.cssText = [
            'display:flex',
            'align-items:center',
            'gap:6px',
            'padding:4px 8px',
            'background:var(--bg-secondary,#161b22)',
            'border-bottom:1px solid var(--border,#30363d)',
            'font-size:11px',
            'flex-wrap:wrap',
            'flex-shrink:0',
        ].join(';');

        // Insert above the scrubber (if present) or directly above #event-stream
        const scrubber = streamEl.parentElement.querySelector(':scope > .timeline-scrubber');
        streamEl.parentElement.insertBefore(bar, scrubber || streamEl);
        _barEl = bar;
        return bar;
    }

    function _render(): void {
        const bar = _ensureBar();
        if (!bar) return;
        bar.innerHTML = '';

        const title = document.createElement('span');
        title.textContent = '🌿 Timeline:';
        title.style.cssText = 'color:var(--text-muted,#8b949e);font-weight:600;font-size:10px;text-transform:uppercase;letter-spacing:.05em;';
        bar.appendChild(title);

        const list = _branches.length ? _branches : [{ branch_id: 'main', parent_branch_id: null, label: 'Main', fork_tick: 0 }];
        for (const b of list) {
            const isActive = b.branch_id === _activeBranchId;
            const pill = document.createElement('button');
            pill.type = 'button';
            const tickHint = b.parent_branch_id ? ` · t${b.fork_tick}` : '';
            pill.textContent = `${b.label}${tickHint}`;
            pill.title = b.parent_branch_id
                ? `Branch ${b.branch_id} (forked from ${b.parent_branch_id} at tick ${b.fork_tick})`
                : 'Primary timeline (main)';
            pill.style.cssText = [
                'padding:1px 7px',
                'border-radius:10px',
                'font-size:10.5px',
                'cursor:pointer',
                isActive
                    ? 'background:var(--accent,#1f6feb);color:#fff;border:1px solid var(--accent,#388bfd);font-weight:600'
                    : 'background:var(--bg-input,#0d1117);color:var(--text-muted,#8b949e);border:1px solid var(--border,#30363d)',
            ].join(';');
            pill.addEventListener('click', () => {
                if (!isActive) void switchBranch(b.branch_id);
            });
            bar.appendChild(pill);
        }

        const spacer = document.createElement('span');
        spacer.style.flex = '1';
        bar.appendChild(spacer);

        // Log | Timeline inline docked switcher (task-1013)
        const modeWrap = document.createElement('div');
        modeWrap.style.cssText = 'display:inline-flex;border:1px solid var(--border,#30363d);border-radius:4px;overflow:hidden;';
        (['log', 'timeline'] as const).forEach((m) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.textContent = m === 'log' ? 'Log' : 'Timeline';
            btn.style.cssText = [
                'border:none',
                'padding:1px 7px',
                'font-size:10.5px',
                'cursor:pointer',
                _viewMode === m
                    ? 'background:var(--accent,#1f6feb);color:#fff;font-weight:600'
                    : 'background:transparent;color:var(--text-muted,#8b949e)',
            ].join(';');
            btn.addEventListener('click', () => { if (_viewMode !== m) _setViewMode(m); });
            modeWrap.appendChild(btn);
        });
        bar.appendChild(modeWrap);

        const viewBtn = document.createElement('button');
        viewBtn.type = 'button';
        viewBtn.textContent = '⛶';
        viewBtn.title = 'Open full-screen Interactive Timeline & Branch Explorer';
        viewBtn.style.cssText = 'padding:1px 6px;border-radius:4px;font-size:10.5px;cursor:pointer;background:transparent;color:var(--text,#c9d1d9);border:1px solid var(--border,#30363d);';
        viewBtn.addEventListener('click', () => {
            if (typeof (window as any).TimelineView?.open === 'function') {
                void (window as any).TimelineView.open();
            } else {
                void openTimelineModal();
            }
        });
        bar.appendChild(viewBtn);

        const forkBtn = document.createElement('button');
        forkBtn.type = 'button';
        forkBtn.textContent = '+ Fork';
        forkBtn.title = 'Fork a new isolated timeline branch at the current tick';
        forkBtn.style.cssText = 'padding:1px 7px;border-radius:4px;font-size:10.5px;cursor:pointer;background:transparent;color:var(--accent,#79c0ff);border:1px solid var(--border,#30363d);';
        forkBtn.addEventListener('click', () => { void forkHere(); });
        bar.appendChild(forkBtn);

        const cpBtn = document.createElement('button');
        cpBtn.type = 'button';
        cpBtn.textContent = '📌 Checkpoint';
        cpBtn.title = 'Save a rewindable snapshot of the current world state on this branch';
        cpBtn.style.cssText = 'padding:1px 7px;border-radius:4px;font-size:10.5px;cursor:pointer;background:transparent;color:var(--text-muted,#8b949e);border:1px solid var(--border,#30363d);';
        cpBtn.addEventListener('click', () => { void saveCheckpoint(); });
        bar.appendChild(cpBtn);
    }

    async function refresh(): Promise<void> {
        try {
            const resp = await fetch('/api/timeline/branches');
            if (!resp.ok) return;
            const data = await resp.json();
            _activeBranchId = String(data?.active_branch_id || 'main');
            _branches = Array.isArray(data?.branches) ? data.branches : [];
            _render();
            if (_viewMode === 'timeline' && _dockedHandle) {
                void _dockedHandle.refresh();
            }
        } catch { /* ignore when offline */ }
    }

    async function switchBranch(branchId: string): Promise<void> {
        const resp = await fetch('/api/timeline/switch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ branch_id: branchId, restore: true }),
        });
        if (resp.ok) {
            const data = await resp.json();
            await refresh();
            await (window as any).worldState?.fetch?.();
            const restoredTick = typeof data?.tick === 'number' ? data.tick : undefined;
            const forkTick = typeof data?.branch?.fork_tick === 'number' ? data.branch.fork_tick : 0;
            await (window as any).events?.syncToTimeline?.({
                branchId: data?.active_branch_id || branchId,
                maxTick: restoredTick,
                forkTick,
            });
        }
    }

    async function forkHere(): Promise<void> {
        const curTick = Number((window as any).VW?.state?.tick ?? 0) || 0;
        const label = window.prompt('Name for new timeline branch:', `Fork @ Tick ${curTick}`);
        if (label === null) return;
        const resp = await fetch('/api/timeline/fork', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ label: label.trim(), fork_tick: curTick, switch: true }),
        });
        if (resp.ok) {
            const data = await resp.json();
            await refresh();
            await (window as any).worldState?.fetch?.();
            await (window as any).events?.syncToTimeline?.({
                branchId: data?.active_branch_id,
                maxTick: typeof data?.tick === 'number' ? data.tick : curTick,
                forkTick: curTick,
            });
            (window as any).VW?.ui?.setStatus?.(`Forked branch: ${label.trim() || `Tick ${curTick}`}`, 'info');
        }
    }

    async function saveCheckpoint(): Promise<void> {
        const resp = await fetch('/api/timeline/checkpoint', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}),
        });
        if (resp.ok) {
            const data = await resp.json();
            (window as any).VW?.ui?.setStatus?.(`Checkpoint saved @ Tick ${data?.tick ?? 0}`, 'info');
            await refresh();
        }
    }

    async function openTimelineModal(): Promise<void> {
        document.getElementById('vw-timeline-modal-overlay')?.remove();
        await refresh();

        const overlay = document.createElement('div');
        overlay.id = 'vw-timeline-modal-overlay';
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.68);z-index:10100;display:flex;align-items:center;justify-content:center;';
        overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });

        const modal = document.createElement('div');
        modal.style.cssText = 'width:clamp(720px,86vw,1320px);height:min(86vh,880px);background:var(--bg-panel,#0d1117);border:1px solid var(--border,#30363d);border-radius:8px;display:flex;flex-direction:column;overflow:hidden;color:var(--text,#c9d1d9);box-shadow:0 16px 48px rgba(0,0,0,0.55);';

        const header = document.createElement('div');
        header.style.cssText = 'display:flex;align-items:center;gap:10px;padding:10px 14px;border-bottom:1px solid var(--border,#30363d);background:var(--bg-secondary,#161b22);flex-shrink:0;';
        header.innerHTML = `<strong style="font-size:13px;">📅 Scenario Timeline & Branches</strong>`;

        const searchInput = document.createElement('input');
        searchInput.type = 'text';
        searchInput.placeholder = 'Search events, speech, thoughts...';
        searchInput.style.cssText = 'background:var(--bg-input,#0d1117);color:var(--text,#c9d1d9);border:1px solid var(--border,#30363d);border-radius:4px;padding:4px 8px;font-size:12px;width:clamp(180px,22vw,320px);';

        const actorSel = document.createElement('select');
        actorSel.style.cssText = 'background:var(--bg-input,#0d1117);color:var(--text,#c9d1d9);border:1px solid var(--border,#30363d);border-radius:4px;padding:4px 6px;font-size:12px;';
        actorSel.innerHTML = '<option value="">All characters</option>';

        let zoom = 1;
        const zoomBtn = document.createElement('button');
        zoomBtn.type = 'button';
        zoomBtn.textContent = '🔍 Zoom: 1x';
        zoomBtn.style.cssText = 'background:transparent;color:var(--text,#c9d1d9);border:1px solid var(--border,#30363d);border-radius:4px;padding:4px 8px;font-size:11.5px;cursor:pointer;';

        const closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.textContent = '✕';
        closeBtn.style.cssText = 'margin-left:auto;background:transparent;border:none;color:var(--text-muted,#8b949e);font-size:16px;cursor:pointer;';
        closeBtn.addEventListener('click', () => overlay.remove());

        header.append(searchInput, actorSel, zoomBtn, closeBtn);

        const body = document.createElement('div');
        body.style.cssText = 'flex:1;overflow:auto;padding:16px;background:var(--bg-input,#0a0e14);min-height:280px;position:relative;';

        const inspector = document.createElement('div');
        inspector.style.cssText = 'padding:10px 16px;border-top:1px solid var(--border,#30363d);background:var(--bg-secondary,#161b22);font-size:12px;display:flex;align-items:center;gap:12px;min-height:48px;flex-shrink:0;';
        inspector.innerHTML = '<span style="color:var(--text-muted,#8b949e);">Hover or click any node on the branch graph to inspect, switch branch, or fork & redo.</span>';

        modal.append(header, body, inspector);
        overlay.appendChild(modal);
        document.body.appendChild(overlay);

        const LANE_COLORS = ['#58a6ff', '#3fb950', '#d2a8ff', '#f0883e', '#f778ba', '#79c0ff'];

        const loadAndRender = async () => {
            const wsData = (window as any).worldState?.data;
            const worldId = String(wsData?._scenario_name || wsData?.world_name || wsData?.name || '').trim();
            const params = new URLSearchParams({ limit: '500' });
            if (worldId) params.set('world_id', worldId);
            if (searchInput.value.trim()) params.set('search', searchInput.value.trim());
            if (actorSel.value) params.set('actor', actorSel.value);
            const resp = await fetch(`/api/stream?${params.toString()}`);
            if (!resp.ok) return;
            const data = await resp.json();
            const actors: string[] = Array.isArray(data?.actors) ? data.actors : [];
            if (actorSel.options.length <= 1 && actors.length) {
                for (const a of actors) {
                    const opt = document.createElement('option');
                    opt.value = a;
                    opt.textContent = a;
                    actorSel.appendChild(opt);
                }
            }
            const rawEvts: any[] = Array.isArray(data?.events) ? data.events : [];
            const evts = rawEvts.filter((e) => e.kind !== 'rawllm' && e.kind !== 'phase' && e.kind !== 'recall' && String(e?.payload?.text || e?.payload?.rawText || '').trim());

            const branchList = _branches.length ? _branches : [{ branch_id: 'main', parent_branch_id: null, label: 'Main', fork_tick: 0 }];
            const laneH = 74;
            const leftPad = 170;
            const stepX = Math.round(52 * zoom);
            const nodeCount = Math.max(evts.length, 6);
            const svgW = Math.max(820, leftPad + nodeCount * stepX + 120);
            const svgH = Math.max(240, branchList.length * laneH + 70);

            const ns = 'http://www.w3.org/2000/svg';
            const svg = document.createElementNS(ns, 'svg');
            svg.setAttribute('width', String(svgW));
            svg.setAttribute('height', String(svgH));
            svg.style.display = 'block';

            const laneIndex = new Map<string, number>();
            branchList.forEach((b, i) => laneIndex.set(b.branch_id, i));

            // Draw branch lanes & Bezier fork connectors
            branchList.forEach((b, idx) => {
                const y = 44 + idx * laneH;
                const color = LANE_COLORS[idx % LANE_COLORS.length];
                const isActive = b.branch_id === _activeBranchId;

                // Lane label pill on left
                const label = document.createElementNS(ns, 'text');
                label.setAttribute('x', '12');
                label.setAttribute('y', String(y + 4));
                label.setAttribute('fill', isActive ? '#ffffff' : '#8b949e');
                label.setAttribute('font-size', '12');
                label.setAttribute('font-weight', isActive ? '700' : '500');
                label.style.cursor = 'pointer';
                label.textContent = `${isActive ? '● ' : '○ '}${b.label}`;
                label.addEventListener('click', async () => {
                    await switchBranch(b.branch_id);
                    await loadAndRender();
                });
                svg.appendChild(label);

                // Fork connector curve from parent lane
                let startX = leftPad;
                if (b.parent_branch_id && laneIndex.has(b.parent_branch_id)) {
                    const pIdx = laneIndex.get(b.parent_branch_id)!;
                    const py = 44 + pIdx * laneH;
                    const forkIdx = Math.max(0, evts.findIndex((e) => Number(e.tick || 0) >= Number(b.fork_tick || 0)));
                    const fx = leftPad + forkIdx * stepX;
                    startX = fx + stepX;
                    const path = document.createElementNS(ns, 'path');
                    path.setAttribute('d', `M ${fx} ${py} C ${fx + stepX * 0.5} ${py}, ${fx + stepX * 0.5} ${y}, ${startX} ${y}`);
                    path.setAttribute('fill', 'none');
                    path.setAttribute('stroke', color);
                    path.setAttribute('stroke-width', '2.5');
                    path.setAttribute('stroke-dasharray', '4 3');
                    svg.appendChild(path);
                }

                // Main horizontal track line
                const line = document.createElementNS(ns, 'line');
                line.setAttribute('x1', String(startX));
                line.setAttribute('y1', String(y));
                line.setAttribute('x2', String(svgW - 40));
                line.setAttribute('y2', String(y));
                line.setAttribute('stroke', color);
                line.setAttribute('stroke-width', isActive ? '3' : '2');
                line.setAttribute('stroke-opacity', isActive ? '0.95' : '0.45');
                svg.appendChild(line);
            });

            // Plot interactive event nodes on the active branch lane
            const activeIdx = laneIndex.get(_activeBranchId) ?? 0;
            const activeY = 44 + activeIdx * laneH;
            const activeColor = LANE_COLORS[activeIdx % LANE_COLORS.length];

            evts.forEach((ev, i) => {
                const cx = leftPad + i * stepX;
                const g = document.createElementNS(ns, 'g');
                g.style.cursor = 'pointer';

                const circle = document.createElementNS(ns, 'circle');
                circle.setAttribute('cx', String(cx));
                circle.setAttribute('cy', String(activeY));
                circle.setAttribute('r', ev.kind === 'speech' ? '7' : '5.5');
                circle.setAttribute('fill', ev.kind === 'speech' ? '#3fb950' : ev.kind === 'action' ? '#f0883e' : activeColor);
                circle.setAttribute('stroke', '#0d1117');
                circle.setAttribute('stroke-width', '2');
                g.appendChild(circle);

                if (i % (zoom < 1 ? 3 : 1) === 0) {
                    const caption = document.createElementNS(ns, 'text');
                    caption.setAttribute('x', String(cx));
                    caption.setAttribute('y', String(activeY - 13));
                    caption.setAttribute('text-anchor', 'middle');
                    caption.setAttribute('fill', '#8b949e');
                    caption.setAttribute('font-size', '9.5');
                    caption.textContent = `${ev.payload?.time || `t${ev.tick ?? 0}`}`;
                    g.appendChild(caption);

                    const who = document.createElementNS(ns, 'text');
                    who.setAttribute('x', String(cx));
                    who.setAttribute('y', String(activeY + 20));
                    who.setAttribute('text-anchor', 'middle');
                    who.setAttribute('fill', '#c9d1d9');
                    who.setAttribute('font-size', '9.5');
                    who.textContent = String(ev.actor || '').slice(0, 8);
                    g.appendChild(who);
                }

                const showDetails = () => {
                    const txt = String(ev?.payload?.text || ev?.payload?.rawText || '').trim();
                    inspector.innerHTML = '';
                    const info = document.createElement('div');
                    info.style.cssText = 'flex:1;line-height:1.4;';
                    info.innerHTML = `<strong style="color:#79c0ff;">${ev.actor}</strong> <span style="color:#8b949e;">[${ev.payload?.time || `t${ev.tick ?? 0}`} · ${ev.kind}]</span>: `;
                    const span = document.createElement('span');
                    span.textContent = txt;
                    info.appendChild(span);
                    inspector.appendChild(info);

                    if (ev.actor && ev.actor !== 'World') {
                        const redo = document.createElement('button');
                        redo.type = 'button';
                        redo.textContent = '↺ Fork & Redo Here';
                        redo.style.cssText = 'flex-shrink:0;background:#1f6feb;color:#fff;border:none;border-radius:4px;padding:5px 10px;font-size:11.5px;cursor:pointer;font-weight:600;';
                        redo.addEventListener('click', async () => {
                            await fetch('/api/timeline/redo', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ character: ev.actor, at_tick: Number(ev.tick || 0), at_seq: ev.seq }),
                            });
                            await refresh();
                            await (window as any).worldState?.fetch?.();
                            await loadAndRender();
                        });
                        inspector.appendChild(redo);
                    }
                };
                g.addEventListener('mouseenter', showDetails);
                g.addEventListener('click', showDetails);
                svg.appendChild(g);
            });

            body.innerHTML = '';
            body.appendChild(svg);
        };

        searchInput.addEventListener('input', () => { void loadAndRender(); });
        actorSel.addEventListener('change', () => { void loadAndRender(); });
        zoomBtn.addEventListener('click', () => {
            zoom = zoom === 1 ? 1.6 : zoom === 1.6 ? 0.6 : 1;
            zoomBtn.textContent = `🔍 Zoom: ${zoom}x`;
            void loadAndRender();
        });
        await loadAndRender();
    }

    (window as any).TimelineBar = { refresh, switchBranch, forkHere, saveCheckpoint, openTimelineModal };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => { void refresh(); });
    } else {
        void refresh();
    }
})();
