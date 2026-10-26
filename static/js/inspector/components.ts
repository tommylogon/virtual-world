/**
 * InspectorComponents - Composable UI components for inspector views.
 *
 * Extracted from duplication across agent-view, item-view, area-view, way-view.
 * Each component is a pure function returning a lit-html TemplateResult that
 * views embed in their own render() output.
 *
 * @module inspector/components
 * @contributes InspectorComponents: Header, PropertyGrid, TabNav, Section, ActionGrid, Breadcrumb, NodeHeader, DangerZone
 * @powers Node inspectors - reusable sections instead of duplicated HTML strings
 * @relates InspectorView base class, InspectorHelpers field builders
 * @docs docs/virtualWorld/UI & Settings/Inspector Panels.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

const InspectorComponents = (() => {
    'use strict';

    const htmlTag = (strings: TemplateStringsArray, ...values: unknown[]) => window.Lit.html(strings, ...values);
    const liveVal = (val: unknown): unknown => {
        const lit = (window as unknown as { Lit?: { live?: (v: unknown) => unknown } }).Lit;
        return lit && typeof lit.live === 'function' ? lit.live(val) : val;
    };

    // ----------------------------------------------------------------------
    // Field definition type (shared contract between views and components)
    // ----------------------------------------------------------------------

    /** A single editable field rendered by PropertyGridComponent. */
    class FieldDef {
        key: string;
        label: string;
        type: 'text' | 'number' | 'select' | 'tags' | 'checkbox' | 'textarea';
        options?: string[];        // for 'select' and 'tags'
        placeholder?: string;
        hint?: string;
        locked?: boolean;          // AI Improve lock
        constructor(key: string, label: string, type: 'text' | 'number' | 'select' | 'tags' | 'checkbox' | 'textarea' = 'text',
                    options?: string[], placeholder?: string, hint?: string, locked?: boolean) {
            this.key = key; this.label = label; this.type = type;
            this.options = options; this.placeholder = placeholder; this.hint = hint; this.locked = locked;
        }
    }

    // ----------------------------------------------------------------------
    // HeaderComponent - title + subtitle + node type badge
    // ----------------------------------------------------------------------

    /**
     * Renders the inspector header: node name, type badge, optional subtitle, optional close button.
     * @param {object} opts - { title, subtitle?, nodeType?, color?, onClose? }
     */
    function HeaderComponent(opts: { title: string; subtitle?: string; nodeType?: string; color?: string; onClose?: () => void }): unknown {
        const { title, subtitle, nodeType, color, onClose } = opts;
        const typeBadge = nodeType
            ? htmlTag`<span class="inspector-type-badge inspector-header-badge" style="background:${color || 'var(--bg-inset)'}">${nodeType}</span>`
            : '';
        const closeBtn = onClose
            ? htmlTag`<button class="btn btn-sm btn-ghost" @click=${onClose}>✕</button>`
            : '';
        return htmlTag`<div class="inspector-header">
            ${typeBadge}
            <div class="inspector-header-title"><h2>${title}</h2></div>
            ${subtitle ? htmlTag`<div class="inspector-header-sub">${subtitle}</div>` : ''}
            ${closeBtn}
        </div>`;
    }

    // ----------------------------------------------------------------------
    // SectionComponent - titled section wrapper with optional hint
    // ----------------------------------------------------------------------

    /**
     * Renders a titled section containing content.
     * @param {object} opts - { title?, hint?, content }
     */
    function SectionComponent(opts: { title?: string; hint?: string; content: unknown }): unknown {
        const { title, hint, content } = opts;
        return htmlTag`<div class="inspector-section">
            ${title ? htmlTag`<h3>${title}</h3>` : ''}
            ${hint ? htmlTag`<p class="section-hint">${hint}</p>` : ''}
            ${content}
        </div>`;
    }

    // ----------------------------------------------------------------------
    // PropertyGridComponent - labeled input fields from a FieldDef[] + values
    // ----------------------------------------------------------------------

    /**
     * Renders a grid of labeled input fields.
     * @param {object} opts - { fields: FieldDef[], values: Record<string, unknown>, onChange: (key, value) => void, lockedFields?: string[] }
     */
    function PropertyGridComponent(opts: {
        fields: FieldDef[];
        values: Record<string, unknown>;
        onChange: (key: string, value: unknown) => void;
        lockedFields?: string[];
    }): unknown {
        const { fields, values, onChange, lockedFields = [] } = opts;
        return htmlTag`<div class="inspector-property-grid">
            ${fields.map((f: FieldDef) => {
                const isLocked = Boolean(f.locked) || lockedFields.includes(f.key);
                const value = values[f.key] ?? '';
                const lockIcon = isLocked ? '🔒' : '🔓';
                switch (f.type) {
                    case 'checkbox':
                        return htmlTag`<div class="field">
                            <label style="display:flex;align-items:center;gap:6px;">
                                <input type="checkbox" .checked=${liveVal(Boolean(value))} ?disabled=${isLocked}
                                    @change=${(ev: Event) => onChange(f.key, (ev.target as HTMLInputElement).checked)}>
                                ${lockIcon} ${f.label}
                            </label>
                            ${f.hint ? htmlTag`<div class="section-hint">${f.hint}</div>` : ''}
                        </div>`;
                    case 'textarea':
                        return htmlTag`<div class="field">
                            <label>${lockIcon} ${f.label}</label>
                            <textarea .value=${liveVal(String(value))} placeholder="${f.placeholder || ''}" ?disabled=${isLocked}
                                @change=${(ev: Event) => onChange(f.key, (ev.target as HTMLTextAreaElement).value)}></textarea>
                            ${f.hint ? htmlTag`<div class="section-hint">${f.hint}</div>` : ''}
                        </div>`;
                    case 'select':
                        return htmlTag`<div class="field">
                            <label>${lockIcon} ${f.label}</label>
                            <select .value=${liveVal(String(value))} ?disabled=${isLocked}
                                @change=${(ev: Event) => onChange(f.key, (ev.target as HTMLSelectElement).value)}>
                                ${(f.options || []).map((opt: string) => htmlTag`<option value="${opt}" ?selected=${opt === value}>${opt}</option>`)}
                            </select>
                            ${f.hint ? htmlTag`<div class="section-hint">${f.hint}</div>` : ''}
                        </div>`;
                    case 'tags':
                        return htmlTag`<div class="field">
                            <label>${lockIcon} ${f.label}</label>
                            <input type="text" .value=${liveVal(Array.isArray(value) ? value.join(', ') : String(value))}
                                placeholder="${f.placeholder || 'comma-separated tags'}" ?disabled=${isLocked}
                                @change=${(ev: Event) => onChange(f.key, (ev.target as HTMLInputElement).value.split(',').map((s: string) => s.trim()).filter(Boolean))}>
                            ${f.hint ? htmlTag`<div class="section-hint">${f.hint}</div>` : ''}
                        </div>`;
                    case 'number':
                        return htmlTag`<div class="field">
                            <label>${lockIcon} ${f.label}</label>
                            <input type="number" .value=${liveVal(String(value))} placeholder="${f.placeholder || ''}" ?disabled=${isLocked}
                                @change=${(ev: Event) => onChange(f.key, Number((ev.target as HTMLInputElement).value) || 0)}>
                            ${f.hint ? htmlTag`<div class="section-hint">${f.hint}</div>` : ''}
                        </div>`;
                    case 'text':
                    default:
                        return htmlTag`<div class="field">
                            <label>${lockIcon} ${f.label}</label>
                            <input type="text" .value=${liveVal(String(value))} placeholder="${f.placeholder || ''}" ?disabled=${isLocked}
                                @change=${(ev: Event) => onChange(f.key, (ev.target as HTMLInputElement).value)}>
                            ${f.hint ? htmlTag`<div class="section-hint">${f.hint}</div>` : ''}
                        </div>`;
                }
            })}
        </div>`;
    }

    // ----------------------------------------------------------------------
    // TabNavComponent - tab navigation bar
    // ----------------------------------------------------------------------

    /**
     * Renders tab navigation.
     * @param {object} opts - { tabs: string[], activeTab: string, onTabChange: (tab: string) => void }
     */
    function TabNavComponent(opts: { tabs: string[]; activeTab: string; onTabChange: (tab: string) => void }): unknown {
        const { tabs, activeTab, onTabChange } = opts;
        return htmlTag`<div class="inspector-tab-nav">
            ${tabs.map((tab: string) => {
                const active = tab === activeTab;
                return htmlTag`<button class="inspector-tab${active ? ' inspector-tab-active' : ''}"
                    @click=${() => onTabChange(tab)}>${tab}</button>`;
            })}
        </div>`;
    }

    // ----------------------------------------------------------------------
    // ActionGridComponent - action buttons grid
    // ----------------------------------------------------------------------

    /**
     * Renders a grid of action buttons.
     * @param {object} opts - { actions: string[], onAction: (action: string) => void, locked?: string[] }
     */
    function ActionGridComponent(opts: { actions: string[]; onAction: (action: string) => void; locked?: string[] }): unknown {
        const { actions, onAction, locked = [] } = opts;
        return htmlTag`<div class="inspector-action-grid">
            ${actions.map((action: string) => {
                const isLocked = locked.includes(action);
                return htmlTag`<button class="inspector-action-btn${isLocked ? ' inspector-action-locked' : ''}"
                    ?disabled=${isLocked} @click=${() => onAction(action)}>${action}</button>`;
            })}
        </div>`;
    }

    // ----------------------------------------------------------------------
    // BreadcrumbComponent - centralized breadcrumb trail
    // ----------------------------------------------------------------------

    /**
     * Renders the breadcrumb trail from the Inspector singleton's history.
     * Uses the canonical .inspector-crumb* classes styled in index.html.
     * @param {object} opts - { onBack?: () => void, onCrumbClick?: (index: number) => void }
     */
    function BreadcrumbComponent(opts: { onBack?: () => void; onCrumbClick?: (index: number) => void }): unknown {
        const inspector = (window as unknown as { inspector?: any }).inspector;
        const history = inspector?._history || [];
        if (!history.length) return window.Lit.nothing;
        const { onBack, onCrumbClick } = opts;
        const trail = history.map((crumb: any, i: number) => {
            const last = i === history.length - 1;
            const sep = i > 0 ? htmlTag`<span class="inspector-crumb-sep">›</span>` : '';
            const body = last
                ? htmlTag`<span class="inspector-crumb-label">${crumb.label}</span>`
                : htmlTag`<button class="inspector-crumb-btn" title="Back to ${crumb.label}"
                    @click=${() => onCrumbClick?.(i)}>${crumb.label}</button>`;
            return htmlTag`<span class="inspector-crumb">${sep}${body}</span>`;
        });
        const back = history.length > 1 && onBack
            ? htmlTag`<button class="inspector-crumb-back" title="Back one step" @click=${onBack}>←</button>`
            : '';
        return htmlTag`${back}${trail}`;
    }

    // ----------------------------------------------------------------------
    // InspectorNodeHeader - standardized node header with rename and sync ID
    // ----------------------------------------------------------------------

    const TYPE_ICONS: Record<string, string> = {
        item: '📦',
        area: '🏠',
        way: '🚪',
        agent: '👤',
        character: '👤',
        player: '👤',
    };

    const TYPE_COLORS: Record<string, string> = {
        item: '#e3b341',
        area: '#58a6ff',
        way: '#4ec9b0',
        agent: '#bc8cff',
        character: '#bc8cff',
    };

    /**
     * Standardized component rendering the type badge, color indicator,
     * name input with rename callback, generated-node check/label, and sync ID button.
     * @param {object} opts - { nodeId, nodeType, name, color?, isGenerated?, onRename, onSyncId, onClose?, onRenameId?, actions? }
     */
    function InspectorNodeHeader(opts: {
        nodeId: string;
        nodeType: string;
        name: string;
        color?: string;
        isGenerated?: boolean;
        onRename: (newName: string) => void;
        onSyncId: () => void;
        onClose?: () => void;
        onRenameId?: (newId: string) => void;
        actions?: unknown;
    }): unknown {
        const { nodeId, nodeType, name, color, onRename, onSyncId, onClose, onRenameId, actions } = opts;
        const isGenerated = opts.isGenerated !== undefined
            ? opts.isGenerated
            : Boolean((window as unknown as { InspectorHelpers?: { isGeneratedNode?: (id: string) => boolean } }).InspectorHelpers?.isGeneratedNode?.(nodeId));

        const icon = TYPE_ICONS[nodeType.toLowerCase()];
        const badgeLabel = (icon && !nodeType.includes(icon))
            ? `${icon} ${nodeType.charAt(0).toUpperCase() + nodeType.slice(1)}`
            : nodeType;
        const badgeColor = color || TYPE_COLORS[nodeType.toLowerCase()] || 'var(--bg-inset)';

        const closeHandler = onClose || (() => {
            const w = window as unknown as { hideInspectorPanel?: () => void; InspectorPanel?: { hide?: () => void } };
            if (typeof w.hideInspectorPanel === 'function') w.hideInspectorPanel();
            else if (w.InspectorPanel?.hide) w.InspectorPanel.hide();
        });

        const renameIdHandler = onRenameId || ((newId: string) => {
            (window as unknown as { InspectorHelpers?: { renameNode?: (oldId: string, nextId: string) => void } }).InspectorHelpers?.renameNode?.(nodeId, newId);
        });

        const closeBtn = htmlTag`<button class="btn btn-sm btn-ghost" @click=${closeHandler}>✕</button>`;

        return htmlTag`<div class="inspector-header">
            <span class="inspector-type-badge" style="background:${badgeColor}">${badgeLabel}</span>
            <div style="flex:1;display:flex;flex-direction:column;min-width:0;">
                <h2 style="margin:0;font-size:16px;">
                    <input type="text" .value=${name}
                        @change=${(ev: Event) => onRename((ev.target as HTMLInputElement).value)}
                        style="font-size:1em;background:transparent;border:1px solid var(--border);color:inherit;width:100%;">
                </h2>
                <div class="field" style="margin:1px 0 0;"><label style="font-size:9px;color:var(--text-muted);margin:0;">Node ID</label>
                    <div style="display:flex;gap:2px;align-items:center;">
                        ${isGenerated
                            ? htmlTag`<span style="font-size:10px;color:var(--text-muted);flex:1;min-width:0;" title="Generated node id - owned by the world compiler; it is regenerated on recompile and cannot be renamed">${nodeId}</span>`
                            : htmlTag`<input type="text" .value=${nodeId}
                                @change=${(ev: Event) => renameIdHandler((ev.target as HTMLInputElement).value)}
                                style="font-size:10px;padding:1px 4px;background:transparent;border:1px solid transparent;color:var(--text-muted);flex:1;min-width:0;cursor:text;"
                                title="Change node ID (lowercase, no spaces)">
                                <button class="btn btn-sm btn-ghost" @click=${onSyncId} title="Sync ID from name">🔄</button>`}
                    </div>
                </div>
            </div>
            ${actions || ''}
            ${closeBtn}
        </div>`;
    }

    // ----------------------------------------------------------------------
    // InspectorDangerZone - standardized node deletion with confirm trigger
    // ----------------------------------------------------------------------

    /**
     * Standardized component rendering the delete node button, confirmation prompt/modal trigger, and delete callback.
     * @param {object} opts - { nodeId, nodeName, nodeType, onDelete }
     */
    function InspectorDangerZone(opts: {
        nodeId: string;
        nodeName: string;
        nodeType: string;
        onDelete: () => void;
    }): unknown {
        const { nodeId, nodeName, nodeType, onDelete } = opts;
        const typeLabel = nodeType ? (nodeType.charAt(0).toUpperCase() + nodeType.slice(1)) : 'Node';
        return htmlTag`<div class="inspector-danger-zone inspector-section" style="margin-top:12px;padding-top:12px;border-top:1px solid var(--border-danger, rgba(248,81,73,0.3));">
            <div style="display:flex;align-items:center;justify-content:space-between;gap:8px;flex-wrap:wrap;">
                <div>
                    <div style="font-size:11px;font-weight:600;color:var(--red, #f85149);">Danger Zone</div>
                    <div style="font-size:10px;color:var(--text-muted);">Permanently delete this ${nodeType} (${nodeName || nodeId}) from the world.</div>
                </div>
                <button class="btn btn-sm btn-red" @click=${onDelete} title="Delete this ${nodeType}">🗑 Delete ${typeLabel}</button>
            </div>
        </div>`;
    }

    return {
        FieldDef,
        HeaderComponent,
        SectionComponent,
        PropertyGridComponent,
        TabNavComponent,
        ActionGridComponent,
        BreadcrumbComponent,
        InspectorNodeHeader,
        InspectorDangerZone,
    };
})();

(window as unknown as { InspectorComponents: typeof InspectorComponents }).InspectorComponents = InspectorComponents;
