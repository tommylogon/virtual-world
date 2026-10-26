/**
 * UiPrimitives - Shared reusable UI presentational components for Viwo and The Commons.
 *
 * Implements Phase 2 of task-904. Pure presentational functions returning lit-html
 * TemplateResults for modals, collapsible sections, badges, and action buttons.
 *
 * @module shared/components/ui-primitives
 * @contributes UiPrimitives: ModalDialog, StatusBadge, CollapsibleSection, ActionBtn
 * @powers Viwo panels and The Commons drawer
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

const UiPrimitives = (() => {
    'use strict';

    const htmlTag = (strings: TemplateStringsArray, ...values: unknown[]) => {
        const lit = (window as unknown as { Lit?: { html: (s: TemplateStringsArray, ...v: unknown[]) => unknown } }).Lit;
        return lit ? lit.html(strings, ...values) : '';
    };

    /**
     * Renders a status badge pill.
     * @param opts - { label, color?, icon?, active?, title? }
     */
    function StatusBadge(opts: {
        label: string;
        color?: string;
        icon?: string;
        active?: boolean;
        title?: string;
    }): unknown {
        const { label, color, icon, active = true, title } = opts;
        const bg = color || 'var(--bg-inset, #242a33)';
        const opacity = active ? '1' : '0.5';
        const titleAttr = title ? title : label;

        return htmlTag`<span class="status-badge" title="${titleAttr}" style="
            display:inline-flex;
            align-items:center;
            gap:4px;
            padding:2px 8px;
            border-radius:12px;
            font-size:11px;
            font-weight:500;
            background:${bg};
            opacity:${opacity};
            color:var(--text, #e6e6e6);
            border:1px solid rgba(255, 255, 255, 0.1);
            white-space:nowrap;
        ">
            ${icon ? htmlTag`<span class="badge-icon">${icon}</span>` : ''}
            <span class="badge-label">${label}</span>
        </span>`;
    }

    /**
     * Renders a collapsible section / disclosure widget.
     * @param opts - { title, content, defaultOpen?, badge?, onToggle? }
     */
    function CollapsibleSection(opts: {
        title: string;
        content: unknown;
        defaultOpen?: boolean;
        badge?: string;
        onToggle?: (isOpen: boolean) => void;
    }): unknown {
        const { title, content, defaultOpen = true, badge, onToggle } = opts;

        return htmlTag`<details class="collapsible-section" ?open=${defaultOpen} 
            @toggle=${(ev: Event) => {
                const target = ev.target as HTMLDetailsElement;
                if (onToggle) onToggle(target.open);
            }} style="
            margin:6px 0;
            border:1px solid var(--border, #333a45);
            border-radius:6px;
            background:var(--bg-panel, #1a1e24);
            overflow:hidden;
        ">
            <summary style="
                padding:8px 12px;
                font-weight:600;
                font-size:12px;
                cursor:pointer;
                display:flex;
                align-items:center;
                justify-content:space-between;
                background:var(--bg-inset, #242a33);
                user-select:none;
            ">
                <span class="section-title">${title}</span>
                ${badge ? htmlTag`<span class="section-badge" style="font-size:10px;padding:1px 6px;border-radius:8px;background:rgba(255,255,255,0.1);">${badge}</span>` : ''}
            </summary>
            <div class="collapsible-content" style="padding:10px 12px;">
                ${content}
            </div>
        </details>`;
    }

    /**
     * Renders an accessible, themed modal dialog.
     * @param opts - { title, isOpen, size?, content, actions?, onClose }
     */
    function ModalDialog(opts: {
        title: string;
        isOpen: boolean;
        size?: 'sm' | 'md' | 'lg';
        content: unknown;
        actions?: unknown;
        onClose: () => void;
    }): unknown {
        const { title, isOpen, size = 'md', content, actions, onClose } = opts;
        if (!isOpen) return '';

        let maxWidth = '500px';
        if (size === 'sm') maxWidth = '360px';
        if (size === 'lg') maxWidth = '720px';

        return htmlTag`<div class="modal-backdrop" @click=${(ev: MouseEvent) => {
            if (ev.target === ev.currentTarget) onClose();
        }} style="
            position:fixed;
            inset:0;
            background:rgba(0, 0, 0, 0.65);
            backdrop-filter:blur(2px);
            z-index:9999;
            display:flex;
            align-items:center;
            justify-content:center;
            padding:16px;
        ">
            <div class="modal-card" style="
                background:var(--bg-panel, #1a1e24);
                border:1px solid var(--border, #333a45);
                border-radius:8px;
                width:100%;
                max-width:${maxWidth};
                max-height:85vh;
                display:flex;
                flex-direction:column;
                box-shadow:0 12px 32px rgba(0, 0, 0, 0.5);
                overflow:hidden;
            ">
                <div class="modal-header" style="
                    padding:12px 16px;
                    border-bottom:1px solid var(--border, #333a45);
                    display:flex;
                    align-items:center;
                    justify-content:space-between;
                ">
                    <h3 style="margin:0;font-size:15px;color:var(--text, #e6e6e6);">${title}</h3>
                    <button class="btn btn-sm btn-ghost" @click=${onClose} style="cursor:pointer;padding:2px 8px;">✕</button>
                </div>
                <div class="modal-body" style="padding:16px;overflow-y:auto;flex:1;">
                    ${content}
                </div>
                ${actions ? htmlTag`<div class="modal-actions" style="
                    padding:10px 16px;
                    border-top:1px solid var(--border, #333a45);
                    display:flex;
                    gap:8px;
                    justify-content:flex-end;
                    background:var(--bg-inset, #242a33);
                ">${actions}</div>` : ''}
            </div>
        </div>`;
    }

    /**
     * Renders a standardized action button.
     * @param opts - { label, variant?, icon?, disabled?, onClick }
     */
    function ActionBtn(opts: {
        label: string;
        variant?: 'primary' | 'danger' | 'ghost' | 'success';
        icon?: string;
        disabled?: boolean;
        onClick: () => void;
    }): unknown {
        const { label, variant = 'primary', icon, disabled = false, onClick } = opts;
        let btnClass = 'btn btn-sm btn-primary';
        if (variant === 'danger') btnClass = 'btn btn-sm btn-red';
        if (variant === 'ghost') btnClass = 'btn btn-sm btn-ghost';
        if (variant === 'success') btnClass = 'btn btn-sm btn-green';

        return htmlTag`<button class="${btnClass}" ?disabled=${disabled} @click=${onClick} style="
            display:inline-flex;
            align-items:center;
            gap:6px;
        ">
            ${icon ? htmlTag`<span>${icon}</span>` : ''}
            <span>${label}</span>
        </button>`;
    }

    return {
        StatusBadge,
        CollapsibleSection,
        ModalDialog,
        ActionBtn
    };
})();

(window as unknown as { UiPrimitives: typeof UiPrimitives }).UiPrimitives = UiPrimitives;
