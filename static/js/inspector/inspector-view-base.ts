/**
 * InspectorView — Base class for all inspector views.
 *
 * Provides lifecycle hooks, breadcrumb integration, state coalescing, and safe
 * worldState access. Every inspector view (agent, item, area, way, etc.) extends
 * this instead of managing its own state and event wiring from scratch.
 *
 * Views stay classic scripts (Option B): they build TemplateResults via the
 * lazy `window.Lit.html` tag and hand them to InspectorPanel.render().
 *
 * @module inspector/inspector-view-base
 * @contributes InspectorView: lifecycle, breadcrumbs, coalescing, worldState access
 * @powers Node inspectors — every view extends this instead of reinventing state
 * @relates InspectorPanel (only panel writer), InspectorHelpers (shared builders)
 * @docs docs/virtualWorld/UI & Settings/Inspector Panels.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

const InspectorViewBase = (() => {
    'use strict';

    /**
     * Contract every view must satisfy.
     */
    class InspectorView {
        /** The node id this view is currently showing, or null if hidden. */
        nodeId: string | null = null;
        /** Whether the view is currently mounted in the panel. */
        mounted = false;
        /** Deferred render flag — coalesces multiple show() calls into one render. */
        _deferRender = false;
        /** Pending render callback. */
        _renderPending = null;

        /** Sub-classes override to render their content into a lit-html TemplateResult. */
        render(): unknown { return null; }

        /** Sub-classes override to clean up (remove listeners, clear timers). */
        dispose(): void { /* no-op by default */ }

        /** Show this view for the given node id. Coalesces with any pending render. */
        show(nodeId: string): void {
            this.nodeId = nodeId;
            this.mounted = true;
            this._scheduleRender();
        }

        /** Hide this view. Cleans up and renders the empty state. */
        hide(): void {
            this._cancelRender();
            this.mounted = false;
            this.nodeId = null;
            this.dispose();
            window.InspectorPanel.renderStatic(
                window.Lit.html`<div class="inspector-empty"><div class="inspector-empty-icon">🔍</div><p>Select a node or agent to inspect</p></div>`
            );
        }

        /** Refresh the current view in place (re-render with latest state). */
        refresh(): void {
            if (!this.mounted || !this.nodeId) return;
            this._scheduleRender();
        }

        /** Push a breadcrumb crumb via the Inspector singleton. */
        _pushCrumb(kind: string, idOrName: string, label: string): void {
            const inspector = (window as unknown as { inspector?: any }).inspector;
            if (!inspector || typeof inspector._pushCrumb !== 'function') return;
            inspector._pushCrumb({ kind, id: kind === 'node' ? idOrName : undefined,
                                   name: kind === 'agent' ? idOrName : undefined,
                                   label });
        }

        /** Read the current worldState safely. */
        _worldState(): any {
            return (window as unknown as { worldState?: any }).worldState;
        }

        /** Read the current graph node for this view's nodeId, if any. */
        _node(): any {
            const ws = this._worldState();
            if (!ws || !this.nodeId) return null;
            return ws.getNode ? ws.getNode(this.nodeId) : null;
        }

        /** Schedule a render (coalesced via microtask). */
        _scheduleRender(): void {
            if (this._deferRender) return;
            this._deferRender = true;
            queueMicrotask(() => {
                this._deferRender = false;
                if (!this.mounted) return;
                const template = this.render();
                if (template) {
                    window.InspectorPanel.render(template);
                }
            });
        }

        /** Cancel any pending render. */
        _cancelRender(): void {
            this._deferRender = false;
        }
    }

    return InspectorView;
})();

(window as unknown as { InspectorView: typeof InspectorViewBase }).InspectorView = InspectorViewBase;
