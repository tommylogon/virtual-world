/**
 * SearchSelect — Single-value searchable select with a TagMultiselect-style dropdown.
 * Click/focus to show all options, type to filter, click or Enter to pick.
 *
 * Usage:
 *   new SearchSelect(container, {
 *     options: [{ value: "door_south", label: "Rusted Door", icon: "🚪" }],
 *     value: "door_south",          // initial value
 *     placeholder: "Search ways...",
 *     inputClass: "eff-unlock",     // class for the hidden value input (so existing
 *                                   // row.querySelector(".eff-unlock").value reads still work)
 *     allowFreeText: false,         // false = only listed options can be committed
 *     onChange: (value) => { ... }
 *   });
 */

// Lazy tag: window.Lit only exists at call time (deferred module bootstrap).
const searchSelectHtmlTag = (strings, ...values) => window.Lit.html(strings, ...values);

class SearchSelect {
    constructor(container, opts = {}) {
        this.container = container;
        this.options = opts.options || [];
        this.value = opts.value || '';
        this.placeholder = opts.placeholder || 'Search...';
        this.inputClass = opts.inputClass || '';
        this.inputId = opts.inputId || '';
        this.allowFreeText = opts.allowFreeText !== false;
        this.onChange = opts.onChange || (() => {});
        this._rows = [];
        this._highlight = 0;

        this._build();
    }

    _labelFor(value) {
        const opt = this.options.find(o => o.value === value);
        return opt ? opt.label : value;
    }

    _build() {
        window.Lit.render(searchSelectHtmlTag`${''}`, this.container);

        this.hidden = document.createElement('input');
        this.hidden.type = 'hidden';
        if (this.inputClass) this.hidden.className = this.inputClass;
        if (this.inputId) this.hidden.id = this.inputId;
        this.hidden.value = this.value;

        this.wrapper = document.createElement('div');
        this.wrapper.style.cssText = 'position:relative;display:flex;align-items:center;gap:4px;background:var(--bg-input);border:1px solid var(--border);border-radius:4px;padding:1px 6px;cursor:text;';
        this.wrapper.addEventListener('mousedown', (e) => {
            if (e.target === this.wrapper) e.preventDefault();
        });
        this.wrapper.addEventListener('click', () => this.input.focus());

        this.input = document.createElement('input');
        this.input.type = 'text';
        this.input.placeholder = this.placeholder;
        this.input.style.cssText = 'border:none;background:transparent;outline:none;flex:1;min-width:0;font-size:11px;color:var(--text);padding:3px 0;';
        this.input.value = this._labelFor(this.value);
        this.input.addEventListener('focus', () => this._open());
        this.input.addEventListener('input', () => this._onInput());
        this.input.addEventListener('keydown', (e) => this._onKeyDown(e));
        this.input.addEventListener('blur', () => { this._commitText(); this._close(); });

        this.clearBtn = document.createElement('span');
        this.clearBtn.textContent = '\u00d7';
        this.clearBtn.style.cssText = 'cursor:pointer;color:var(--text-muted);font-size:13px;line-height:1;display:' + (this.value ? 'block' : 'none') + ';';
        this.clearBtn.addEventListener('mousedown', (e) => e.preventDefault());
        this.clearBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.setValue('');
            this.input.focus();
            this._open();
        });

        this.wrapper.appendChild(this.input);
        this.wrapper.appendChild(this.clearBtn);
        this.container.appendChild(this.hidden);
        this.container.appendChild(this.wrapper);

        this.dropdown = document.createElement('div');
        this.dropdown.style.cssText = 'position:absolute;top:100%;left:-1px;right:-1px;z-index:1000;background:var(--bg-card);border:1px solid var(--border);border-radius:4px;max-height:200px;overflow-y:auto;display:none;box-shadow:0 4px 12px rgba(0,0,0,0.3);';
        this.wrapper.appendChild(this.dropdown);
    }

    _filtered(query) {
        const needle = (query || '').trim().toLowerCase();
        if (!needle) return this.options;
        return this.options.filter(o =>
            String(o.label || '').toLowerCase().includes(needle) ||
            String(o.value || '').toLowerCase().includes(needle)
        );
    }

    _open() {
        this._render(this.options);
    }

    _onInput() {
        this._render(this._filtered(this.input.value));
    }

    _render(list) {
        this._rows = list;
        this._highlight = 0;

        if (!list.length) {
            window.Lit.render(searchSelectHtmlTag`<div style="padding:8px;font-size:10px;color:var(--text-muted);text-align:center;">No matches</div>`, this.dropdown);
        } else {
            const rows = list.map((o, i) => searchSelectHtmlTag`<div data-value=${o.value} style="display:flex;align-items:center;gap:6px;padding:5px 8px;cursor:pointer;font-size:11px;border-bottom:1px solid var(--border);" @mouseenter=${() => {
                this._highlight = i;
                this._applyHighlight();
            }} @mousedown=${(e) => {
                e.preventDefault();
                this._select(o.value);
            }}>
                ${o.icon ? searchSelectHtmlTag`<span style="font-size:13px;">${o.icon}</span>` : ''}
                <span style="font-weight:600;">${o.label}</span>
                <span style="color:var(--text-muted);font-size:9px;margin-left:auto;">${o.value}</span>
            </div>`);
            window.Lit.render(searchSelectHtmlTag`${rows}`, this.dropdown);
            this._applyHighlight();
        }

        this.dropdown.style.display = 'block';
    }

    _applyHighlight() {
        this._rows.forEach((o, i) => {
            const row = this.dropdown.children[i];
            if (!row) return;
            row.style.background = i === this._highlight ? 'var(--bg-inset)' : 'transparent';
        });
    }

    _select(value) {
        this.setValue(value);
        this._close();
        this.input.focus();
        this.onChange(value);
    }

    setValue(value) {
        this.value = value || '';
        this.hidden.value = this.value;
        this.input.value = this._labelFor(this.value);
        this.clearBtn.style.display = this.value ? 'block' : 'none';
    }

    setPlaceholder(text) {
        this.input.placeholder = text;
    }

    getValue() { return this.value; }

    _commitText() {
        const text = this.input.value.trim();
        if (!text) {
            this.input.value = this._labelFor(this.value);
            return;
        }
        // Display already matches the committed value — nothing to do.
        // (Without this, blur would re-select and refocus, stealing focus
        // from whatever the user clicked next, e.g. the success message field.)
        if (text === this._labelFor(this.value)) return;
        const byValue = this.options.find(o => String(o.value) === text);
        const byLabel = this.options.find(o => String(o.label).toLowerCase() === text.toLowerCase());
        const match = byValue || byLabel;
        if (match) {
            this.setValue(match.value);
            this.onChange(match.value);
            return;
        }
        if (this.allowFreeText) {
            this.setValue(text);
            this.onChange(text);
            return;
        }
        this.input.value = this._labelFor(this.value);
    }

    _onKeyDown(e) {
        if (e.key === 'Escape') { this._close(); this.input.blur(); return; }
        if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
            e.preventDefault();
            if (this.dropdown.style.display === 'none') { this._open(); return; }
            if (!this._rows.length) return;
            const delta = e.key === 'ArrowDown' ? 1 : -1;
            this._highlight = Math.max(0, Math.min(this._rows.length - 1, this._highlight + delta));
            this._applyHighlight();
            return;
        }
        if (e.key === 'Enter') {
            e.preventDefault();
            if (this.dropdown.style.display !== 'none' && this._rows.length) {
                this._select(this._rows[this._highlight].value);
                return;
            }
            this._commitText();
        }
    }

    _close() {
        this.dropdown.style.display = 'none';
        window.Lit.render(searchSelectHtmlTag`${''}`, this.dropdown);
        this._rows = [];
    }

    destroy() { window.Lit.render(searchSelectHtmlTag`${''}`, this.container); }
}

window.SearchSelect = SearchSelect;
