/**
 * timeline-view.ts - Zoomable, Scrollable Multi-Month Calendar Timeline & Branch Graph (task-980)
 *
 * True calendar time axis (empty days & hour slots are clickable/selectable),
 * horizontal branch lanes with Bezier fork curves, floating hover tooltips,
 * click-to-open detail drawer, wheel/slider zoom, drag-to-pan, and time-jump /
 * fork / redo / PlayMode actions.
 */
(() => {
    'use strict';

    type ZoomLevel = 'month' | 'day' | 'hour';

    interface BranchSummary {
        branch_id: string;
        parent_branch_id: string | null;
        label: string;
        fork_tick: number;
        fork_datetime?: string;
    }

    const LANE_COLORS = ['#58a6ff', '#3fb950', '#d2a8ff', '#f0883e', '#f778ba', '#79c0ff'];
    const PX_PER_HOUR: Record<ZoomLevel, number> = { month: 4, day: 24, hour: 120 };

    function _pad2(n: number): string { return String(n).padStart(2, '0'); }

    function _formatSlot(baseYear: number, totalHours: number): { label: string; iso: string; dayNum: number; hour: number } {
        const dayOffset = Math.floor(totalHours / 24);
        const hour = ((Math.floor(totalHours) % 24) + 24) % 24;
        const d = new Date(Date.UTC(baseYear, 0, 1 + dayOffset, hour, 0, 0));
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const label = `${months[d.getUTCMonth()]} ${d.getUTCDate()} · ${_pad2(hour)}:00`;
        const iso = `${d.getUTCFullYear()}-${_pad2(d.getUTCMonth() + 1)}-${_pad2(d.getUTCDate())}T${_pad2(hour)}:00:00`;
        return { label, iso, dayNum: dayOffset + 1, hour };
    }

    async function open(): Promise<void> {
        document.getElementById('vw-timeline-modal-overlay')?.remove();

        const overlay = document.createElement('div');
        overlay.id = 'vw-timeline-modal-overlay';
        overlay.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.72);z-index:10100;display:flex;align-items:center;justify-content:center;';
        overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });

        const modal = document.createElement('div');
        modal.style.cssText = 'width:clamp(820px,92vw,1480px);height:min(90vh,920px);background:var(--bg-panel,#0d1117);border:1px solid var(--border,#30363d);border-radius:8px;display:flex;flex-direction:column;overflow:hidden;color:var(--text,#c9d1d9);box-shadow:0 18px 54px rgba(0,0,0,0.6);';

        // Top toolbar
        const header = document.createElement('div');
        header.style.cssText = 'display:flex;align-items:center;gap:8px;padding:10px 14px;border-bottom:1px solid var(--border,#30363d);background:var(--bg-secondary,#161b22);flex-shrink:0;flex-wrap:wrap;';
        header.innerHTML = `<strong style="font-size:13px;">📅 Interactive Timeline & Branch Graph</strong>`;

        const searchInput = document.createElement('input');
        searchInput.type = 'text';
        searchInput.placeholder = 'Search events...';
        searchInput.style.cssText = 'background:var(--bg-input,#0d1117);color:var(--text,#c9d1d9);border:1px solid var(--border,#30363d);border-radius:4px;padding:4px 8px;font-size:12px;width:clamp(140px,18vw,240px);';

        const actorSel = document.createElement('select');
        actorSel.style.cssText = 'background:var(--bg-input,#0d1117);color:var(--text,#c9d1d9);border:1px solid var(--border,#30363d);border-radius:4px;padding:4px 6px;font-size:12px;';
        actorSel.innerHTML = '<option value="">All characters</option>';

        let zoom: ZoomLevel = 'day';
        const zoomWrap = document.createElement('div');
        zoomWrap.style.cssText = 'display:flex;gap:3px;border:1px solid var(--border,#30363d);border-radius:4px;padding:2px;';
        const zoomBtns: Record<ZoomLevel, HTMLButtonElement> = {} as any;
        (['month', 'day', 'hour'] as ZoomLevel[]).forEach((z) => {
            const b = document.createElement('button');
            b.type = 'button';
            b.textContent = z === 'month' ? 'Months' : z === 'day' ? 'Days' : 'Hours';
            b.style.cssText = 'border:none;border-radius:3px;padding:3px 8px;font-size:11px;cursor:pointer;';
            b.addEventListener('click', () => {
                zoom = z;
                syncZoomBtns();
                void renderGraph();
            });
            zoomBtns[z] = b;
            zoomWrap.appendChild(b);
        });
        const syncZoomBtns = () => {
            (['month', 'day', 'hour'] as ZoomLevel[]).forEach((z) => {
                zoomBtns[z].style.background = z === zoom ? 'var(--accent,#1f6feb)' : 'transparent';
                zoomBtns[z].style.color = z === zoom ? '#fff' : 'var(--text-muted,#8b949e)';
            });
        };
        syncZoomBtns();

        const hint = document.createElement('span');
        hint.textContent = 'Drag to pan · Click empty day/hour slot to select time · Click node to inspect';
        hint.style.cssText = 'font-size:10.5px;color:var(--text-muted,#8b949e);margin-left:4px;';

        const closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.textContent = '✕';
        closeBtn.style.cssText = 'margin-left:auto;background:transparent;border:none;color:var(--text-muted,#8b949e);font-size:16px;cursor:pointer;';
        closeBtn.addEventListener('click', () => overlay.remove());

        header.append(searchInput, actorSel, zoomWrap, hint, closeBtn);

        // Main split: scrollable SVG graph + right detail drawer
        const mainSplit = document.createElement('div');
        mainSplit.style.cssText = 'flex:1;display:flex;min-height:0;overflow:hidden;position:relative;';

        const viewport = document.createElement('div');
        viewport.style.cssText = 'flex:1;overflow:auto;background:#0a0e14;position:relative;cursor:grab;user-select:none;';

        const drawer = document.createElement('div');
        drawer.style.cssText = 'width:clamp(260px,26vw,360px);border-left:1px solid var(--border,#30363d);background:var(--bg-secondary,#161b22);padding:14px;overflow-y:auto;display:flex;flex-direction:column;gap:10px;flex-shrink:0;';
        drawer.innerHTML = '<div style="font-size:12px;color:var(--text-muted,#8b949e);line-height:1.5;"><strong>Select a time slot or event node</strong><br/><br/>- Click any <b>empty day/hour slot</b> on the calendar ruler to jump the world clock or fork a branch there.<br/>- Hover any <b>event dot</b> for a quick preview.<br/>- Click any <b>event dot</b> to open full details and redo that character\'s decision.</div>';

        // Floating hover tooltip
        const tooltip = document.createElement('div');
        tooltip.style.cssText = 'position:fixed;display:none;pointer-events:none;z-index:10200;max-width:340px;background:#161b22;border:1px solid #388bfd;border-radius:6px;padding:8px 10px;font-size:11.5px;color:#c9d1d9;box-shadow:0 8px 24px rgba(0,0,0,0.6);line-height:1.4;';
        overlay.appendChild(tooltip);

        mainSplit.append(viewport, drawer);
        modal.append(header, mainSplit);
        overlay.appendChild(modal);
        document.body.appendChild(overlay);

        // Drag-to-pan on viewport
        let dragging = false;
        let dragStartX = 0;
        let dragScrollLeft = 0;
        viewport.addEventListener('mousedown', (e) => {
            if ((e.target as HTMLElement).closest('g[data-node="1"], text[data-branch="1"]')) return;
            dragging = true;
            dragStartX = e.clientX;
            dragScrollLeft = viewport.scrollLeft;
            viewport.style.cursor = 'grabbing';
        });
        window.addEventListener('mousemove', (e) => {
            if (!dragging) return;
            viewport.scrollLeft = dragScrollLeft - (e.clientX - dragStartX);
        });
        window.addEventListener('mouseup', () => {
            dragging = false;
            viewport.style.cursor = 'grab';
        });

        // Ctrl+Wheel zoom
        viewport.addEventListener('wheel', (e) => {
            if (!e.ctrlKey) return;
            e.preventDefault();
            if (e.deltaY < 0) zoom = zoom === 'month' ? 'day' : 'hour';
            else zoom = zoom === 'hour' ? 'day' : 'month';
            syncZoomBtns();
            void renderGraph();
        }, { passive: false });

        let selectedHour: number | null = null;

        const renderSlotDrawer = (baseYear: number, totalHours: number) => {
            const slot = _formatSlot(baseYear, totalHours);
            const targetTick = Math.max(0, Math.round(totalHours * 12)); // 5 min per tick default
            drawer.innerHTML = '';
            const h = document.createElement('div');
            h.innerHTML = `<div style="font-size:10px;text-transform:uppercase;color:#8b949e;letter-spacing:.06em;">Selected Time Slot</div>
                <div style="font-size:15px;font-weight:700;color:#79c0ff;margin-top:2px;">${slot.label}</div>
                <div style="font-size:11px;color:#8b949e;font-family:monospace;margin-top:2px;">${slot.iso} (approx Tick ${targetTick})</div>`;
            drawer.appendChild(h);

            const mkBtn = (label: string, primary: boolean, onClick: () => Promise<void>) => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.textContent = label;
                btn.style.cssText = primary
                    ? 'width:100%;padding:7px 10px;border-radius:5px;border:none;background:#1f6feb;color:#fff;font-size:12px;font-weight:600;cursor:pointer;text-align:left;'
                    : 'width:100%;padding:7px 10px;border-radius:5px;border:1px solid var(--border,#30363d);background:var(--bg-input,#0d1117);color:#c9d1d9;font-size:12px;cursor:pointer;text-align:left;';
                btn.addEventListener('click', () => { void onClick(); });
                return btn;
            };

            drawer.appendChild(mkBtn('⏱ Set / Jump World Clock Here', true, async () => {
                const prevTick = Number((window as any).worldState?.data?.time_ticks ?? 0) || 0;
                const dParts = String(slot.iso || '').split('T')[0].split('-').map(Number);
                if (dParts.length === 3 && !isNaN(dParts[0])) {
                    await fetch('/api/settings/date', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ year: dParts[0], month: dParts[1], day: dParts[2] }),
                    }).catch(() => {});
                }
                await (window as any).ApiClient?.setClockStart?.(slot.hour, 0).catch?.(() => {});
                await (window as any).worldState?.fetch?.();
                const newTick = Number((window as any).worldState?.data?.time_ticks ?? 0) || 0;
                if (newTick < prevTick) {
                    (window as any).events?.pruneAfterTick?.(newTick);
                    (window as any).VW?.agent?.onTimelineSwitch?.({ tick: newTick });
                }
                (window as any).VW?.ui?.setStatus?.(`World clock moved to ${slot.label}`, 'info');
                await renderGraph();
            }));

            drawer.appendChild(mkBtn('🌿 Fork New Branch Here', false, async () => {
                const label = window.prompt('Branch name:', `Branch @ ${slot.label}`);
                if (label === null) return;
                const fResp = await fetch('/api/timeline/fork', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ label: label.trim() || `Branch @ ${slot.label}`, fork_tick: targetTick, fork_datetime: slot.iso, switch: true }),
                });
                const fData = fResp.ok ? await fResp.json() : null;
                await (window as any).TimelineBar?.refresh?.();
                await (window as any).worldState?.fetch?.();
                await (window as any).events?.syncToTimeline?.({
                    branchId: fData?.active_branch_id,
                    maxTick: typeof fData?.tick === 'number' ? fData.tick : targetTick,
                    forkTick: targetTick,
                });
                await renderGraph();
            }));

            drawer.appendChild(mkBtn('▶ Enter Play Mode From Here', false, async () => {
                overlay.remove();
                await (window as any).PlayMode?.enter?.();
            }));
        };

        const renderEventDrawer = (ev: any) => {
            const txt = String(ev?.payload?.text || ev?.payload?.rawText || '').trim();
            drawer.innerHTML = '';
            const head = document.createElement('div');
            head.innerHTML = `<div style="font-size:10px;text-transform:uppercase;color:#8b949e;letter-spacing:.06em;">${ev.kind || 'event'} · Tick ${ev.tick ?? 0}</div>
                <div style="font-size:14px;font-weight:700;color:#79c0ff;margin-top:2px;">${ev.actor || 'World'}</div>
                <div style="font-size:11px;color:#8b949e;margin-top:2px;">${ev.payload?.time || ev.game_time || ''} · ${ev.area || ''}</div>`;
            const bodyTxt = document.createElement('div');
            bodyTxt.style.cssText = 'font-size:12px;line-height:1.55;white-space:pre-wrap;background:var(--bg-input,#0d1117);padding:10px;border-radius:6px;border:1px solid var(--border,#30363d);';
            bodyTxt.textContent = txt;
            drawer.append(head, bodyTxt);

            if (ev.actor && ev.actor !== 'World') {
                const redoBtn = document.createElement('button');
                redoBtn.type = 'button';
                redoBtn.textContent = `↺ Fork & Redo ${ev.actor}'s Decision`;
                redoBtn.style.cssText = 'width:100%;padding:7px 10px;border-radius:5px;border:none;background:#1f6feb;color:#fff;font-size:12px;font-weight:600;cursor:pointer;';
                redoBtn.addEventListener('click', async () => {
                    const rResp = await fetch('/api/timeline/redo', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ character: ev.actor, at_tick: Number(ev.tick || 0), at_seq: ev.seq }),
                    });
                    const rData = rResp.ok ? await rResp.json() : null;
                    await (window as any).TimelineBar?.refresh?.();
                    await (window as any).worldState?.fetch?.();
                    await (window as any).events?.syncToTimeline?.({
                        branchId: rData?.active_branch_id,
                        maxTick: typeof rData?.tick === 'number' ? rData.tick : Number(ev.tick || 0),
                        forkTick: Number(ev.tick || 0),
                        focusCharacter: ev.actor,
                    });
                    await renderGraph();
                });
                drawer.appendChild(redoBtn);
            }
        };

        const renderGraph = async () => {
            const wsData = (window as any).worldState?.data || {};
            const baseYear = Number(wsData.game_year || 2026) || 2026;
            const worldId = String(wsData?._scenario_name || wsData?.world_name || wsData?.name || '').trim();

            const [brResp, stResp] = await Promise.all([
                fetch('/api/timeline/branches'),
                fetch(`/api/stream?${new URLSearchParams({
                    limit: '500',
                    ...(worldId ? { world_id: worldId } : {}),
                    ...(searchInput.value.trim() ? { search: searchInput.value.trim() } : {}),
                    ...(actorSel.value ? { actor: actorSel.value } : {}),
                }).toString()}`),
            ]);
            const brData = brResp.ok ? await brResp.json() : { active_branch_id: 'main', branches: [] };
            const stData = stResp.ok ? await stResp.json() : { events: [], actors: [] };

            const activeBranchId = String(brData.active_branch_id || 'main');
            const branches: BranchSummary[] = (Array.isArray(brData.branches) && brData.branches.length)
                ? brData.branches
                : [{ branch_id: 'main', parent_branch_id: null, label: 'Main', fork_tick: 0 }];

            const actors: string[] = Array.isArray(stData.actors) ? stData.actors : [];
            if (actorSel.options.length <= 1 && actors.length) {
                for (const a of actors) {
                    const opt = document.createElement('option');
                    opt.value = a;
                    opt.textContent = a;
                    actorSel.appendChild(opt);
                }
            }

            const rawEvts: any[] = Array.isArray(stData.events) ? stData.events : [];
            const evts = rawEvts.filter((e) => e.kind !== 'rawllm' && e.kind !== 'phase' && e.kind !== 'recall' && String(e?.payload?.text || e?.payload?.rawText || '').trim());

            // Calendar span: 90 days in month zoom, 14 days in day zoom, 3 days in hour zoom
            const totalDays = zoom === 'month' ? 120 : zoom === 'day' ? 14 : 3;
            const totalHours = totalDays * 24;
            const pxPerHour = PX_PER_HOUR[zoom];
            const leftPad = 175;
            const rulerH = 44;
            const laneH = 72;
            const svgW = Math.max(900, leftPad + totalHours * pxPerHour + 80);
            const svgH = Math.max(300, rulerH + branches.length * laneH + 60);

            const ns = 'http://www.w3.org/2000/svg';
            const svg = document.createElementNS(ns, 'svg');
            svg.setAttribute('width', String(svgW));
            svg.setAttribute('height', String(svgH));
            svg.style.display = 'block';

            // Clickable empty calendar slots (gridlines + ruler)
            const slotStepHours = zoom === 'month' ? 24 * 7 : zoom === 'day' ? 24 : 1;
            for (let h = 0; h <= totalHours; h += slotStepHours) {
                const x = leftPad + h * pxPerHour;
                const slot = _formatSlot(baseYear, h);

                const grid = document.createElementNS(ns, 'line');
                grid.setAttribute('x1', String(x));
                grid.setAttribute('y1', String(rulerH));
                grid.setAttribute('x2', String(x));
                grid.setAttribute('y2', String(svgH));
                grid.setAttribute('stroke', '#1c2128');
                grid.setAttribute('stroke-width', '1');
                svg.appendChild(grid);

                const lbl = document.createElementNS(ns, 'text');
                lbl.setAttribute('x', String(x + 4));
                lbl.setAttribute('y', '26');
                lbl.setAttribute('fill', '#8b949e');
                lbl.setAttribute('font-size', '10');
                lbl.textContent = zoom === 'hour' ? `${_pad2(slot.hour)}:00` : slot.label.split(' · ')[0];
                svg.appendChild(lbl);
            }

            // Click anywhere on background/ruler to select an empty day/hour slot
            const bgHit = document.createElementNS(ns, 'rect');
            bgHit.setAttribute('x', String(leftPad));
            bgHit.setAttribute('y', '0');
            bgHit.setAttribute('width', String(svgW - leftPad));
            bgHit.setAttribute('height', String(svgH));
            bgHit.setAttribute('fill', 'transparent');
            bgHit.style.cursor = 'crosshair';
            bgHit.addEventListener('click', (e) => {
                const rect = svg.getBoundingClientRect();
                const relX = Math.max(0, e.clientX - rect.left - leftPad);
                const clickedHour = Math.round(relX / pxPerHour);
                selectedHour = clickedHour;
                renderSlotDrawer(baseYear, clickedHour);
                void renderGraph();
            });
            svg.appendChild(bgHit);

            // Selected time cursor line
            if (selectedHour !== null) {
                const sx = leftPad + selectedHour * pxPerHour;
                const curLine = document.createElementNS(ns, 'line');
                curLine.setAttribute('x1', String(sx));
                curLine.setAttribute('y1', '0');
                curLine.setAttribute('x2', String(sx));
                curLine.setAttribute('y2', String(svgH));
                curLine.setAttribute('stroke', '#388bfd');
                curLine.setAttribute('stroke-width', '2');
                curLine.setAttribute('stroke-dasharray', '4 3');
                svg.appendChild(curLine);
            }

            // Branch lanes + Bezier fork curves
            const laneIdx = new Map<string, number>();
            branches.forEach((b, i) => laneIdx.set(b.branch_id, i));

            branches.forEach((b, i) => {
                const y = rulerH + 36 + i * laneH;
                const color = LANE_COLORS[i % LANE_COLORS.length];
                const isActive = b.branch_id === activeBranchId;

                const lbl = document.createElementNS(ns, 'text');
                lbl.setAttribute('x', '12');
                lbl.setAttribute('y', String(y + 4));
                lbl.setAttribute('fill', isActive ? '#ffffff' : '#8b949e');
                lbl.setAttribute('font-size', '12');
                lbl.setAttribute('font-weight', isActive ? '700' : '500');
                lbl.setAttribute('data-branch', '1');
                lbl.style.cursor = 'pointer';
                lbl.textContent = `${isActive ? '● ' : '○ '}${b.label}`;
                lbl.addEventListener('click', async () => {
                    await (window as any).TimelineBar?.switchBranch?.(b.branch_id);
                    await renderGraph();
                });
                svg.appendChild(lbl);

                const forkHour = Math.max(0, Number(b.fork_tick || 0) / 12);
                let startX = leftPad;
                if (b.parent_branch_id && laneIdx.has(b.parent_branch_id)) {
                    const py = rulerH + 36 + laneIdx.get(b.parent_branch_id)! * laneH;
                    const fx = leftPad + forkHour * pxPerHour;
                    startX = fx + 28;
                    const path = document.createElementNS(ns, 'path');
                    path.setAttribute('d', `M ${fx} ${py} C ${fx + 14} ${py}, ${fx + 14} ${y}, ${startX} ${y}`);
                    path.setAttribute('fill', 'none');
                    path.setAttribute('stroke', color);
                    path.setAttribute('stroke-width', '2.4');
                    path.setAttribute('stroke-dasharray', '4 3');
                    svg.appendChild(path);
                }

                const track = document.createElementNS(ns, 'line');
                track.setAttribute('x1', String(startX));
                track.setAttribute('y1', String(y));
                track.setAttribute('x2', String(svgW - 24));
                track.setAttribute('y2', String(y));
                track.setAttribute('stroke', color);
                track.setAttribute('stroke-width', isActive ? '3' : '2');
                track.setAttribute('stroke-opacity', isActive ? '0.95' : '0.45');
                svg.appendChild(track);
            });

            // Plot event nodes on the active lane at their real calendar hour (with tiny jitter for same-tick events)
            const activeI = laneIdx.get(activeBranchId) ?? 0;
            const activeY = rulerH + 36 + activeI * laneH;
            const activeColor = LANE_COLORS[activeI % LANE_COLORS.length];

            evts.forEach((ev, idx) => {
                const tickHours = (Number(ev.tick || 0) * 5) / 60;
                const cx = leftPad + tickHours * pxPerHour + (idx % 12) * 14;
                const g = document.createElementNS(ns, 'g');
                g.setAttribute('data-node', '1');
                g.style.cursor = 'pointer';

                const dot = document.createElementNS(ns, 'circle');
                dot.setAttribute('cx', String(cx));
                dot.setAttribute('cy', String(activeY));
                dot.setAttribute('r', ev.kind === 'speech' ? '6.5' : '5');
                dot.setAttribute('fill', ev.kind === 'speech' ? '#3fb950' : ev.kind === 'action' ? '#f0883e' : activeColor);
                dot.setAttribute('stroke', '#0a0e14');
                dot.setAttribute('stroke-width', '2');
                g.appendChild(dot);

                g.addEventListener('mouseenter', (me) => {
                    const txt = String(ev?.payload?.text || ev?.payload?.rawText || '').trim();
                    tooltip.innerHTML = `<strong style="color:#79c0ff;">${ev.actor}</strong> <span style="color:#8b949e;">[t${ev.tick ?? 0} · ${ev.kind}]</span><br/>${txt.slice(0, 180)}${txt.length > 180 ? '...' : ''}`;
                    tooltip.style.display = 'block';
                    tooltip.style.left = `${Math.min(window.innerWidth - 360, me.clientX + 14)}px`;
                    tooltip.style.top = `${Math.min(window.innerHeight - 120, me.clientY + 14)}px`;
                });
                g.addEventListener('mouseleave', () => { tooltip.style.display = 'none'; });
                g.addEventListener('click', (ce) => {
                    ce.stopPropagation();
                    renderEventDrawer(ev);
                });
                svg.appendChild(g);
            });

            viewport.innerHTML = '';
            viewport.appendChild(svg);
        };

        searchInput.addEventListener('input', () => { void renderGraph(); });
        actorSel.addEventListener('change', () => { void renderGraph(); });
        await renderGraph();
    }

    (window as any).TimelineView = { open };
})();
