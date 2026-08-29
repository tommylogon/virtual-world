/**
 * TagMultiselect — Searchable tag picker with autocomplete, badges, and create-on-the-fly.
 * Backed by GET /api/tags/search for autocomplete and GET /api/tags/validate for validation.
 *
 * Usage:
 *   new TagMultiselect(container, {
 *     tags: ["flammable", "magic"],     // initial tag IDs
 *     appliesTo: "items",                // optional filter
 *     allowNew: true,                    // allow creating new tags
 *     placeholder: "Search tags...",
 *     onChange: (tags) => { ... }
 *   });
 */

// Lazy tag: window.Lit only exists at call time (deferred module bootstrap).
const tagMultiselectHtmlTag = (strings, ...values) => window.Lit.html(strings, ...values);

// Full-tag-list cache: the inspector re-creates TagMultiselect instances on
// every re-render, and each constructor loaded the whole list. A short TTL
// keeps the dropdown live without flooding /api/tags/search per re-render.
const _tagListCache = { at: 0, tags: null };
const _TAG_LIST_TTL = 15000;

class TagMultiselect {
    constructor(container, opts = {}) {
        this.container = container;
        this.tags = opts.tags || [];
        this.appliesTo = opts.appliesTo || null;
        this.allowNew = opts.allowNew !== false;
        this.placeholder = opts.placeholder || "Search tags...";
        this.onChange = opts.onChange || (() => {});
        this._tagCache = {};
        this._open = false;

        this._build();
        this._loadAllTags();
    }

    _build() {
        // Imperative wipe: Lit.render() only clears content between its own
        // comment markers, so wrappers appended via appendChild would survive
        // it and stack up on every inspector re-render.
        while (this.container.firstChild) {
            this.container.removeChild(this.container.firstChild);
        }
        this.wrapper = document.createElement("div");
        this.wrapper.style.cssText = "position:relative;display:flex;flex-wrap:wrap;gap:4px;align-items:center;padding:4px;background:var(--bg-input);border:1px solid var(--border);border-radius:4px;min-height:32px;cursor:text;";

        this.badgeArea = document.createElement("div");
        this.badgeArea.style.cssText = "display:flex;flex-wrap:wrap;gap:4px;align-items:center;flex:1;";
        this._renderBadges();

        this.input = document.createElement("input");
        this.input.type = "text";
        this.input.placeholder = this.placeholder;
        this.input.style.cssText = "border:none;background:transparent;outline:none;flex:1;min-width:80px;font-size:11px;color:var(--text);padding:2px;";
        this.input.addEventListener("input", () => this._onInput());
        this.input.addEventListener("keydown", (e) => this._onKeyDown(e));
        this.input.addEventListener("blur", () => setTimeout(() => this._closeDropdown(), 200));

        this.wrapper.appendChild(this.badgeArea);
        this.wrapper.appendChild(this.input);
        this.container.appendChild(this.wrapper);

        this.dropdown = document.createElement("div");
        this.dropdown.style.cssText = "position:absolute;top:100%;left:0;right:0;z-index:1000;background:var(--bg-card);border:1px solid var(--border);border-radius:4px;max-height:200px;overflow-y:auto;display:none;box-shadow:0 4px 12px rgba(0,0,0,0.3);";
        this.wrapper.appendChild(this.dropdown);
    }

    _renderBadges() {
        const badges = this.tags.map(id => {
            const t = this._tagCache[id] || { name: id, icon: "🎗️", color: "#888888" };
            return tagMultiselectHtmlTag`<span style="display:inline-flex;align-items:center;gap:3px;padding:1px 6px;border-radius:4px;font-size:10px;background:${t.color}22;color:${t.color};border:1px solid ${t.color}44;cursor:default;">
                ${t.icon} ${t.name || id}
                <span style="cursor:pointer;margin-left:2px;opacity:0.7;font-size:12px;line-height:1;" data-remove="${id}" @click=${(e) => {
                    e.stopPropagation();
                    this.tags = this.tags.filter(tag => tag !== id);
                    this._renderBadges();
                    this.onChange(this.tags);
                }}>&times;</span>
            </span>`;
        });
        window.Lit.render(tagMultiselectHtmlTag`${badges}`, this.badgeArea);
    }

    _loadAllTags() {
        const applyTags = (tags) => {
            this._tagCache = {};
            (tags || []).forEach(t => { this._tagCache[t.id] = t; });
            this._renderBadges();
        };
        if (_tagListCache.tags && Date.now() - _tagListCache.at < _TAG_LIST_TTL) {
            applyTags(_tagListCache.tags);
            return;
        }
        fetch("/api/tags/search").then(r => r.json()).then(tags => {
            const list = Array.isArray(tags) ? tags : ((tags && tags.tags) || []);
            _tagListCache.at = Date.now();
            _tagListCache.tags = list;
            applyTags(list);
        }).catch(() => {});
    }

    async _onInput() {
        const q = this.input.value.trim().toLowerCase();
        if (!q) { this._showAll(); return; }
        try {
            const resp = await fetch("/api/tags/search?q=" + encodeURIComponent(q));
            const results = await resp.json();
            this._showDropdown(results, q);
        } catch { this._closeDropdown(); }
    }

    _showAll() {
        const all = Object.values(this._tagCache);
        this._showDropdown(all, "");
    }

    _showDropdown(results, query) {
        const filtered = results.filter(t => !this.tags.includes(t.id));
        const pick = (e, id) => {
            e.stopPropagation();
            if (id === "__new__") {
                this.tags.push(query);
                // Auto-register in library
                const tagData = { id: query, name: query.charAt(0).toUpperCase() + query.slice(1), description: "", category: "custom", color: "#888888", icon: "\U0001f397\ufe0f", applies_to: this.appliesTo ? [this.appliesTo] : ["items"], examples: [] };
                fetch("/api/library/tags", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(tagData) }).catch(() => {});
            } else {
                this.tags.push(id);
            }
            this.input.value = "";
            this._renderBadges();
            this._closeDropdown();
            this.onChange(this.tags);
            this.input.focus();
        };

        const options = filtered.map(t => tagMultiselectHtmlTag`<div class="tag-option" data-id="${t.id}" style="display:flex;align-items:center;gap:6px;padding:6px 8px;cursor:pointer;font-size:11px;border-bottom:1px solid var(--border);" @click=${(e) => pick(e, t.id)}>
            <span style="font-size:14px;">${t.icon}</span>
            <span style="font-weight:600;">${t.name}</span>
            <span style="color:var(--text-muted);font-size:9px;">${t.category || ""}</span>
            <span style="color:var(--text-dim);font-size:9px;margin-left:auto;">${t.description || ""}</span>
        </div>`);

        if (this.allowNew && query && !Object.values(this._tagCache).some(t => t.id === query || t.name.toLowerCase() === query)) {
            options.push(tagMultiselectHtmlTag`<div class="tag-option tag-create" data-id="__new__" style="display:flex;align-items:center;gap:6px;padding:6px 8px;cursor:pointer;font-size:11px;color:var(--accent);border-top:1px dashed var(--border);" @click=${(e) => pick(e, "__new__")}>
                <span>+ Create "<strong>${query}</strong>"</span>
            </div>`);
        }

        window.Lit.render(tagMultiselectHtmlTag`${options.length ? options : [tagMultiselectHtmlTag`<div style="padding:8px;font-size:10px;color:var(--text-muted);text-align:center;">No tags found</div>`]}`, this.dropdown);
        this.dropdown.style.display = "block";
        this._open = true;
    }

    _closeDropdown() {
        this.dropdown.style.display = "none";
        window.Lit.render(tagMultiselectHtmlTag`${''}`, this.dropdown);
        this._open = false;
    }

    _onKeyDown(e) {
        if (e.key === "Escape") { this._closeDropdown(); this.input.blur(); }
        if (e.key === "Enter") {
            const q = this.input.value.trim().toLowerCase();
            if (this._open) {
                const first = this.dropdown.querySelector(".tag-option");
                if (first) { first.click(); return; }
            }
            if (q && !this.tags.includes(q)) {
                this.tags.push(q);
                if (this.allowNew && !Object.values(this._tagCache).some(t => t.id === q || t.name.toLowerCase() === q)) {
                    const tagData = { id: q, name: q.charAt(0).toUpperCase() + q.slice(1), description: "", category: "custom", color: "#888888", icon: "\U0001f397\ufe0f", applies_to: this.appliesTo ? [this.appliesTo] : ["items"], examples: [] };
                    fetch("/api/library/tags", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(tagData) }).catch(() => {});
                }
                this.input.value = "";
                this._renderBadges();
                this._closeDropdown();
                this.onChange(this.tags);
            }
            this.input.focus();
            e.preventDefault();
        }
        if (e.key === "Backspace" && !this.input.value && this.tags.length > 0) {
            this.tags.pop();
            this._renderBadges();
            this.onChange(this.tags);
        }
    }

    getValue() { return [...this.tags]; }
    setValue(tags) { this.tags = [...tags]; this._renderBadges(); }
    destroy() {
        // Same wipe as _build — Lit.render(empty) would leave the wrapper behind.
        while (this.container.firstChild) {
            this.container.removeChild(this.container.firstChild);
        }
    }
}

window.TagMultiselect = TagMultiselect;
