/**
 * InspectorComponents - Composable UI components for inspector views.
 *
 * Extracted from duplication across agent-view, item-view, area-view, way-view.
 * Each component is a pure function returning a lit-html TemplateResult that
 * views embed in their own render() output.
 *
 * @module inspector/components
 * @contributes InspectorComponents: Header, PropertyGrid, TabNav, Section, ActionGrid, Breadcrumb
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

    return {
        FieldDef,
        HeaderComponent,
        SectionComponent,
        PropertyGridComponent,
        TabNavComponent,
        ActionGridComponent,
        BreadcrumbComponent,
    };
})();

(window as unknown as { InspectorComponents: typeof InspectorComponents }).InspectorComponents = InspectorComponents;
