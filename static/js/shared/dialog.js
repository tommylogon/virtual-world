"use strict";
/**
 * Shared in-app dialog — promise-based alert / confirm / prompt.
 *
 * Replaces native `window.alert` / `confirm` / `prompt`, which ignore the app's
 * theme and focus management. One overlay, focus-trapped; `Esc` and backdrop
 * click cancel, `Enter` submits, `Tab` cycles within the card.
 *
 * @module shared/dialog — promise-based in-app modal dialogs
 * @contributes Dialog.alert / Dialog.confirm / Dialog.prompt, published as VW.dialog
 * @relates used by the trigger graph's blueprint save and other confirm/rename flows
 * @docs docs/virtualWorld/UI & Settings/Rendering & UI Modules.md
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.
window.Dialog = (() => {
    function esc(text) {
        return String(text == null ? '' : text)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }
    const btnStyle = 'padding:6px 14px;border-radius:6px;border:1px solid var(--border,#333a45);background:var(--bg-inset,#242a33);color:var(--text,#e6e6e6);cursor:pointer;font-size:13px;';
    const btnPrimary = 'padding:6px 14px;border-radius:6px;border:1px solid #3d6ea8;background:#2f5f92;color:#fff;cursor:pointer;font-size:13px;';
    const btnDanger = 'padding:6px 14px;border-radius:6px;border:1px solid #a8333d;background:#8f2f37;color:#fff;cursor:pointer;font-size:13px;';
    /**
     * Build the overlay and wire the lifecycle. `submit` is called on Enter or the
     * primary button, `cancel` on Esc / backdrop / cancel button. Both receive the
     * card so the caller can read inputs; both are expected to close.
     */
    function openModal(opts) {
        return new Promise((resolve) => {
            const root = document.createElement('div');
            root.className = 'vw-dialog-overlay';
            root.style.cssText = 'position:fixed;inset:0;z-index:10000;display:flex;align-items:center;justify-content:center;background:rgba(0,0,0,.55);';
            root.innerHTML = `<div class="vw-dialog" role="dialog" aria-modal="true" style="min-width:320px;max-width:560px;background:var(--bg-panel,#1b1f27);border:1px solid var(--border,#333a45);border-radius:10px;box-shadow:0 20px 60px rgba(0,0,0,.6);padding:16px;color:var(--text,#e6e6e6);font-size:13px;">
                ${opts.title ? `<div class="vw-dialog-title" style="font-weight:600;margin-bottom:8px;">${esc(opts.title)}</div>` : ''}
                ${opts.bodyHtml || ''}
                <div class="vw-dialog-actions" style="display:flex;gap:8px;justify-content:flex-end;margin-top:14px;">${opts.actionsHtml}</div>
            </div>`;
            const card = root.firstElementChild;
            let done = false;
            const finish = (result) => {
                if (done)
                    return;
                done = true;
                document.removeEventListener('keydown', onKey, true);
                if (root.parentNode)
                    root.parentNode.removeChild(root);
                resolve(result);
            };
            const cardOf = (el) => (el && root.contains(el) ? el : null);
            const focusables = () => Array.from(card.querySelectorAll('input,textarea,button,select,[tabindex]:not([tabindex="-1"])'));
            const onKey = (e) => {
                if (e.key === 'Escape') {
                    e.preventDefault();
                    cancel();
                }
                else if (e.key === 'Enter' && !(e.target instanceof HTMLTextAreaElement)) {
                    const primary = card.querySelector('[data-vw-dialog-primary]');
                    if (primary) {
                        e.preventDefault();
                        primary.click();
                    }
                }
                else if (e.key === 'Tab') {
                    const f = focusables();
                    if (!f.length)
                        return;
                    const first = f[0], last = f[f.length - 1];
                    const active = document.activeElement;
                    if (e.shiftKey && active === first) {
                        e.preventDefault();
                        last.focus();
                    }
                    else if (!e.shiftKey && active === last) {
                        e.preventDefault();
                        first.focus();
                    }
                }
            };
            let cancel = () => finish(null);
            card.querySelectorAll('[data-vw-dialog-cancel]').forEach((b) => {
                b.addEventListener('click', () => cancel());
            });
            // Backdrop click cancels; clicks inside the card do not bubble to root.
            root.addEventListener('mousedown', (e) => { if (e.target === root)
                cancel(); });
            document.addEventListener('keydown', onKey, true);
            document.body.appendChild(root);
            opts.onReady(card, finish);
            (focusables()[0] || card).focus();
            void cardOf; // (kept for readability; no-op)
        });
    }
    function alert(opts) {
        return openModal({
            title: opts.title,
            bodyHtml: opts.message ? `<div style="white-space:pre-wrap;">${esc(opts.message)}</div>` : '',
            actionsHtml: `<button type="button" data-vw-dialog-primary data-vw-dialog-cancel style="${btnPrimary}">${esc(opts.confirmLabel || 'OK')}</button>`,
            onReady: (card, finish) => {
                card.querySelector('[data-vw-dialog-primary]')?.addEventListener('click', () => finish());
            },
        });
    }
    function confirm(opts) {
        return openModal({
            title: opts.title,
            bodyHtml: opts.message ? `<div style="white-space:pre-wrap;">${esc(opts.message)}</div>` : '',
            actionsHtml: `<button type="button" data-vw-dialog-cancel style="${btnStyle}">${esc(opts.cancelLabel || 'Cancel')}</button>` +
                `<button type="button" data-vw-dialog-primary style="${opts.danger ? btnDanger : btnPrimary}">${esc(opts.confirmLabel || 'OK')}</button>`,
            onReady: (card, finish) => {
                card.querySelector('[data-vw-dialog-primary]')?.addEventListener('click', () => finish(true));
                card.querySelector('[data-vw-dialog-cancel]')?.addEventListener('click', () => finish(false));
            },
        });
    }
    function prompt(opts) {
        const fields = (opts.fields || []).map((f, i) => {
            const tag = f.type === 'textarea' ? 'textarea' : 'input';
            const typeAttr = tag === 'input' ? ` type="${esc(f.type || 'text')}"` : '';
            const valueAttr = tag === 'input' ? ` value="${esc(f.value || '')}"` : '';
            const inner = tag === 'textarea' ? esc(f.value || '') : '';
            const common = `data-field="${esc(f.key)}" data-vw-dialog-input placeholder="${esc(f.placeholder || '')}" style="width:100%;box-sizing:border-box;padding:6px 8px;border-radius:6px;border:1px solid var(--border,#333a45);background:var(--bg-inset,#242a33);color:var(--text,#e6e6e6);font-size:13px;"`;
            const autofocus = i === 0 ? ' data-vw-dialog-autofocus' : '';
            return `<label style="display:block;margin:8px 0 0;"><span style="display:block;margin-bottom:3px;color:var(--text-muted,#9aa3b2);font-size:11.5px;">${esc(f.label)}</span><${tag}${typeAttr}${valueAttr} ${common}${autofocus}>${inner}</${tag}></label>`;
        }).join('');
        return openModal({
            title: opts.title,
            bodyHtml: (opts.message ? `<div style="margin-bottom:6px;white-space:pre-wrap;">${esc(opts.message)}</div>` : '') + fields,
            actionsHtml: `<button type="button" data-vw-dialog-cancel style="${btnStyle}">${esc(opts.cancelLabel || 'Cancel')}</button>` +
                `<button type="button" data-vw-dialog-primary style="${btnPrimary}">${esc(opts.confirmLabel || 'Save')}</button>`,
            onReady: (card, finish) => {
                card.querySelector('[data-vw-dialog-primary]')?.addEventListener('click', () => {
                    const out = {};
                    card.querySelectorAll('[data-vw-dialog-input]').forEach((el) => {
                        out[el.dataset.field || ''] = el.value;
                    });
                    finish(out);
                });
            },
        });
    }
    return { alert, confirm, prompt };
})();
