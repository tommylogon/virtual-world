"use strict";
/**
 * InspectorComponents — Composable UI components for inspector views.
 *
 * Extracted from duplication across agent-view, item-view, area-view, way-view.
 * Each component is a pure function returning a lit-html TemplateResult that
 * views embed in their own render() output.
 *
 * @module inspector/components
 * @contributes InspectorComponents: Header, PropertyGrid, TabNav, Section, ActionGrid, Breadcrumb
 * @powers Node inspectors — reusable sections instead of duplicated HTML strings
 * @relates InspectorView base class, InspectorHelpers field builders
 * @docs docs/virtualWorld/UI & Settings/Inspector Panels.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
const InspectorComponents = (() => {
    'use strict';
    const htmlTag = (strings, ...values) => window.Lit.html(strings, ...values);
    // ──────────────────────────────────────────────────────────────────────
    // Field definition type (shared contract between views and components)
    // ──────────────────────────────────────────────────────────────────────
    /** A single editable field rendered by PropertyGridComponent. */
    class FieldDef {
        key;
        label;
        type;
        options; // for 'select' and 'tags'
        placeholder;
        hint;
        locked; // AI Improve lock
        constructor(key, label, type = 'text', options, placeholder, hint, locked) {
            this.key = key;
            this.label = label;
            this.type = type;
            this.options = options;
            this.placeholder = placeholder;
            this.hint = hint;
            this.locked = locked;
        }
    }
    // ──────────────────────────────────────────────────────────────────────
    // HeaderComponent — title + subtitle + node type badge
    // ──────────────────────────────────────────────────────────────────────
    /**
     * Renders the inspector header: node name, type badge, optional subtitle.
     * @param {object} opts - { title, subtitle?, nodeType?, color? }
     */
    function HeaderComponent(opts) {
        const { title, subtitle, nodeType, color } = opts;
        const typeBadge = nodeType
            ? htmlTag `<span class="inspector-header-badge" style="background:${color || 'var(--bg-inset)'}">${nodeType}</span>`
            : '';
        return htmlTag `<div class="inspector-header">
            <div class="inspector-header-title">${title}${typeBadge}</div>
            ${subtitle ? htmlTag `<div class="inspector-header-sub">${subtitle}</div>` : ''}
        </div>`;
    }
    // ──────────────────────────────────────────────────────────────────────
    // SectionComponent — titled section wrapper with optional hint
    // ──────────────────────────────────────────────────────────────────────
    /**
     * Renders a titled section containing content.
     * @param {object} opts - { title, hint?, content }
     */
    function SectionComponent(opts) {
        const { title, hint, content } = opts;
        return htmlTag `<div class="inspector-section">
            <h3>${title}</h3>
            ${hint ? htmlTag `<p class="section-hint">${hint}</p>` : ''}
            ${content}
        </div>`;
    }
    // ──────────────────────────────────────────────────────────────────────
    // PropertyGridComponent — labeled input fields from a FieldDef[] + values
    // ──────────────────────────────────────────────────────────────────────
    /**
     * Renders a grid of labeled input fields.
     * @param {object} opts - { fields: FieldDef[], values: Record<string, unknown>, onChange: (key, value) => void, lockedFields?: string[] }
     */
    function PropertyGridComponent(opts) {
        const { fields, values, onChange, lockedFields = [] } = opts;
        return htmlTag `<div class="inspector-property-grid">
            ${fields.map((f) => {
            const isLocked = lockedFields.includes(f.key);
            const value = values[f.key] ?? '';
            const lockedAttr = isLocked ? ' disabled' : '';
            const lockIcon = isLocked ? '🔒' : '🔓';
            switch (f.type) {
                case 'checkbox':
                    return htmlTag `<div class="field">
                            <label style="display:flex;align-items:center;gap:6px;">
                                <input type="checkbox" .checked=${Boolean(value)}
                                    @change=${(ev) => onChange(f.key, ev.target.checked)}${lockedAttr}>
                                ${lockIcon} ${f.label}
                            </label>
                            ${f.hint ? htmlTag `<div class="section-hint">${f.hint}</div>` : ''}
                        </div>`;
                case 'textarea':
                    return htmlTag `<div class="field">
                            <label>${lockIcon} ${f.label}</label>
                            <textarea .value=${String(value)} placeholder="${f.placeholder || ''}"
                                @change=${(ev) => onChange(f.key, ev.target.value)}${lockedAttr}></textarea>
                            ${f.hint ? htmlTag `<div class="section-hint">${f.hint}</div>` : ''}
                        </div>`;
                case 'select':
                    return htmlTag `<div class="field">
                            <label>${lockIcon} ${f.label}</label>
                            <select .value=${String(value)} @change=${(ev) => onChange(f.key, ev.target.value)}${lockedAttr}>
                                ${(f.options || []).map((opt) => htmlTag `<option value="${opt}" ?selected=${opt === value}>${opt}</option>`)}
                            </select>
                            ${f.hint ? htmlTag `<div class="section-hint">${f.hint}</div>` : ''}
                        </div>`;
                case 'tags':
                    return htmlTag `<div class="field">
                            <label>${lockIcon} ${f.label}</label>
                            <input type="text" .value=${Array.isArray(value) ? value.join(', ') : String(value)}
                                placeholder="${f.placeholder || 'comma-separated tags'}"
                                @change=${(ev) => onChange(f.key, ev.target.value.split(',').map((s) => s.trim()).filter(Boolean))}${lockedAttr}>
                            ${f.hint ? htmlTag `<div class="section-hint">${f.hint}</div>` : ''}
                        </div>`;
                case 'number':
                default:
                    return htmlTag `<div class="field">
                            <label>${lockIcon} ${f.label}</label>
                            <input type="number" .value=${String(value)} placeholder="${f.placeholder || ''}"
                                @change=${(ev) => onChange(f.key, Number(ev.target.value) || 0)}${lockedAttr}>
                            ${f.hint ? htmlTag `<div class="section-hint">${f.hint}</div>` : ''}
                        </div>`;
            }
        })}
        </div>`;
    }
    // ──────────────────────────────────────────────────────────────────────
    // TabNavComponent — tab navigation bar
    // ──────────────────────────────────────────────────────────────────────
    /**
     * Renders tab navigation.
     * @param {object} opts - { tabs: string[], activeTab: string, onTabChange: (tab: string) => void }
     */
    function TabNavComponent(opts) {
        const { tabs, activeTab, onTabChange } = opts;
        return htmlTag `<div class="inspector-tab-nav">
            ${tabs.map((tab) => {
            const active = tab === activeTab;
            return htmlTag `<button class="inspector-tab${active ? ' inspector-tab-active' : ''}"
                    @click=${() => onTabChange(tab)}>${tab}</button>`;
        })}
        </div>`;
    }
    // ──────────────────────────────────────────────────────────────────────
    // ActionGridComponent — action buttons grid
    // ──────────────────────────────────────────────────────────────────────
    /**
     * Renders a grid of action buttons.
     * @param {object} opts - { actions: string[], onAction: (action: string) => void, locked?: string[] }
     */
    function ActionGridComponent(opts) {
        const { actions, onAction, locked = [] } = opts;
        return htmlTag `<div class="inspector-action-grid">
            ${actions.map((action) => {
            const isLocked = locked.includes(action);
            return htmlTag `<button class="inspector-action-btn${isLocked ? ' inspector-action-locked' : ''}"
                    @click=${() => onAction(action)}${isLocked ? ' disabled' : ''}>${action}</button>`;
        })}
        </div>`;
    }
    // ──────────────────────────────────────────────────────────────────────
    // BreadcrumbComponent — centralized breadcrumb trail
    // ──────────────────────────────────────────────────────────────────────
    /**
     * Renders the breadcrumb trail from the Inspector singleton's history.
     * @param {object} opts - { onBack: () => void, onCrumbClick: (index: number) => void }
     */
    function BreadcrumbComponent(opts) {
        const inspector = window.inspector;
        const history = inspector?._history || [];
        if (!history.length)
            return window.Lit.nothing;
        const { onBack, onCrumbClick } = opts;
        return htmlTag `<div class="inspector-breadcrumb">
            ${history.length > 1 && onBack
            ? htmlTag `<button class="inspector-breadcrumb-back" @click=${onBack}>←</button>`
            : ''}
            ${history.map((crumb, i) => {
            const last = i === history.length - 1;
            const sep = i > 0 ? htmlTag `<span class="inspector-breadcrumb-sep">›</span>` : '';
            const body = last
                ? htmlTag `<span class="inspector-breadcrumb-label">${crumb.label}</span>`
                : htmlTag `<button class="inspector-breadcrumb-btn" @click=${() => onCrumbClick?.(i)}>${crumb.label}</button>`;
            return htmlTag `<span class="inspector-breadcrumb">${sep}${body}</span>`;
        })}
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
    };
})();
window.InspectorComponents = InspectorComponents;
