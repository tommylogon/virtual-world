"use strict";
/**
 * EntityEditor - Full-viewport frame mounting character, item and area editors
 * alongside the right-panel inspector peek (task-673 / Phase 1 of full-entity-editors.md).
 *
 * Requirements:
 * - #entity-editor is a completely separate DOM element from #inspector-panel.
 * - Reuses existing view modules (agent-view, item-view, area-view) without forking.
 * - Shared chrome: kind badge, inline-editable name, copyable node id, saved/in-flight indicator, close button.
 * - Esc key and backdrop click close; focus moves to name input on open and returns to opener on close.
 * - Entry points: expand control (⛶) in inspector header and double-click on canvas node.
 * - Single-click on canvas node remains the contextual peek default.
 *
 * @module inspector/entity-editor
 * @contributes EntityEditor singleton: mount, unmount, setInFlight, isOpen
 * @docs docs/design/full-entity-editors.md
 */
const EntityEditor = (() => {
    let _isOpen = false;
    let _currentKind = null;
    let _currentIdOrName = null;
    let _currentNodeId = null;
    let _openerEl = null;
    let _inFlight = false;
    let _initialized = false;
    const KIND_COLORS = {
        character: '#bc8cff',
        item: '#e3b341',
        area: '#58a6ff',
    };
    const KIND_LABELS = {
        character: '👤 Character',
        item: '📦 Item',
        area: '🏠 Area',
    };
    function ensureContainer() {
        let container = document.getElementById('entity-editor');
        if (!container) {
            container = document.createElement('div');
            container.id = 'entity-editor';
            container.className = 'entity-editor-overlay';
            container.style.display = 'none';
            container.setAttribute('role', 'dialog');
            container.setAttribute('aria-modal', 'true');
            container.setAttribute('aria-label', 'Entity Editor');
            const backdrop = document.createElement('div');
            backdrop.className = 'entity-editor-backdrop';
            container.appendChild(backdrop);
            const frame = document.createElement('div');
            frame.className = 'entity-editor-frame';
            const header = document.createElement('header');
            header.className = 'entity-editor-header';
            const badge = document.createElement('span');
            badge.id = 'entity-editor-kind-badge';
            badge.className = 'entity-editor-kind-badge';
            badge.textContent = 'Entity';
            header.appendChild(badge);
            const nameInput = document.createElement('input');
            nameInput.type = 'text';
            nameInput.id = 'entity-editor-name-input';
            nameInput.className = 'entity-editor-name-input';
            nameInput.placeholder = 'Entity Name';
            nameInput.setAttribute('aria-label', 'Entity Name');
            header.appendChild(nameInput);
            const tabsNav = document.createElement('nav');
            tabsNav.id = 'entity-editor-tabs';
            tabsNav.className = 'entity-editor-tabs';
            tabsNav.style.display = 'none';
            header.appendChild(tabsNav);
            const idWrap = document.createElement('div');
            idWrap.className = 'entity-editor-id-wrap';
            const idLabel = document.createElement('span');
            idLabel.id = 'entity-editor-node-id';
            idLabel.className = 'entity-editor-node-id';
            idWrap.appendChild(idLabel);
            const copyBtn = document.createElement('button');
            copyBtn.type = 'button';
            copyBtn.id = 'entity-editor-copy-id';
            copyBtn.className = 'entity-editor-copy-btn';
            copyBtn.title = 'Copy node ID';
            copyBtn.textContent = '📋';
            idWrap.appendChild(copyBtn);
            header.appendChild(idWrap);
            const status = document.createElement('span');
            status.id = 'entity-editor-status';
            status.className = 'entity-editor-status saved';
            status.textContent = '✔ Saved';
            header.appendChild(status);
            const closeBtn = document.createElement('button');
            closeBtn.type = 'button';
            closeBtn.id = 'entity-editor-close';
            closeBtn.className = 'entity-editor-close';
            closeBtn.title = 'Close editor (Esc)';
            closeBtn.setAttribute('aria-label', 'Close editor');
            closeBtn.textContent = '✕';
            header.appendChild(closeBtn);
            frame.appendChild(header);
            const body = document.createElement('div');
            body.id = 'entity-editor-body';
            body.className = 'entity-editor-body';
            frame.appendChild(body);
            container.appendChild(frame);
            document.body.appendChild(container);
        }
        initListeners(container);
        return container;
    }
    function initListeners(container) {
        if (_initialized)
            return;
        _initialized = true;
        const backdrop = container.querySelector('.entity-editor-backdrop');
        if (backdrop) {
            backdrop.addEventListener('click', () => unmount());
        }
        const closeBtn = container.querySelector('#entity-editor-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => unmount());
        }
        const copyBtn = container.querySelector('#entity-editor-copy-id');
        if (copyBtn) {
            copyBtn.addEventListener('click', () => copyNodeId());
        }
        const nameInput = container.querySelector('#entity-editor-name-input');
        if (nameInput) {
            nameInput.addEventListener('change', (ev) => {
                const target = ev.target;
                handleNameChange(target.value);
            });
        }
        // Global keydown for Escape and Tab focus trap
        document.addEventListener('keydown', onKeyDown);
        // state:updated auto-refresh
        if (window.appEvents) {
            window.appEvents.on('state:updated', () => {
                if (_isOpen)
                    _reRender();
            });
        }
        // Hook ApiClient updates to reflect in-flight indicator
        hookApiClient();
    }
    function hookApiClient() {
        const client = window.ApiClient;
        if (!client)
            return;
        const origUpdateNode = client.updateNode;
        if (typeof origUpdateNode === 'function' && !client._eeHookedNode) {
            client._eeHookedNode = true;
            client.updateNode = function (...args) {
                if (_isOpen)
                    setInFlight(true);
                const res = origUpdateNode.apply(this, args);
                if (res && typeof res.finally === 'function') {
                    res.finally(() => { if (_isOpen)
                        setInFlight(false); });
                }
                return res;
            };
        }
        const origUpdateChar = client.updateCharacter;
        if (typeof origUpdateChar === 'function' && !client._eeHookedChar) {
            client._eeHookedChar = true;
            client.updateCharacter = function (...args) {
                if (_isOpen)
                    setInFlight(true);
                const res = origUpdateChar.apply(this, args);
                if (res && typeof res.finally === 'function') {
                    res.finally(() => { if (_isOpen)
                        setInFlight(false); });
                }
                return res;
            };
        }
    }
    function onKeyDown(e) {
        if (!_isOpen)
            return;
        if (e.key === 'Escape') {
            const active = document.activeElement;
            if (active && (active.tagName === 'SELECT' || active.classList?.contains('search-select-input'))) {
                return;
            }
            e.preventDefault();
            e.stopPropagation();
            unmount();
            return;
        }
        if (e.key === 'Tab') {
            const container = document.getElementById('entity-editor');
            if (!container)
                return;
            const focusables = Array.from(container.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])')).filter(el => el.offsetParent !== null && !el.hasAttribute('disabled'));
            if (!focusables.length)
                return;
            const first = focusables[0];
            const last = focusables[focusables.length - 1];
            if (e.shiftKey) {
                if (document.activeElement === first) {
                    e.preventDefault();
                    last.focus();
                }
            }
            else {
                if (document.activeElement === last) {
                    e.preventDefault();
                    first.focus();
                }
            }
        }
    }
    async function handleNameChange(newName) {
        const trimmed = newName.trim();
        if (!trimmed || !_currentKind || !_currentIdOrName)
            return;
        setInFlight(true);
        try {
            if (_currentKind === 'character') {
                const oldName = _currentIdOrName;
                await window.ApiClient.updateCharacter(oldName, { name: trimmed });
                _currentIdOrName = trimmed;
            }
            else if (_currentKind === 'item' || _currentKind === 'area') {
                const id = _currentIdOrName;
                const api = window.api || window.ApiClient;
                await api.updateNode(id, { name: trimmed, properties: { name: trimmed } });
            }
            if (window.worldState?.fetch) {
                await window.worldState.fetch();
            }
        }
        catch (err) {
            console.error('[EntityEditor] rename failed:', err);
        }
        finally {
            setInFlight(false);
        }
    }
    async function copyNodeId() {
        if (!_currentNodeId)
            return;
        try {
            if (navigator?.clipboard?.writeText) {
                await navigator.clipboard.writeText(_currentNodeId);
            }
        }
        catch (e) {
            // fallback
        }
        const btn = document.getElementById('entity-editor-copy-id');
        if (btn) {
            const orig = btn.textContent;
            btn.textContent = '✔';
            setTimeout(() => { if (btn)
                btn.textContent = orig; }, 1200);
        }
    }
    function resolveEntityInfo(kind, idOrName) {
        const ws = window.worldState;
        if (kind === 'character') {
            const charNode = Object.entries(ws?.graph?.nodes || {}).find(([, n]) => n.type === 'character' && n.name === idOrName);
            const nodeId = charNode ? charNode[0] : (ws?.players?.[idOrName]?.node_id || `player_${idOrName.replace(/\s+/g, '_')}`);
            return { displayName: idOrName, nodeId };
        }
        if (kind === 'item') {
            const node = ws?.getNode ? ws.getNode(idOrName) : null;
            const displayName = node?.name || idOrName;
            return { displayName, nodeId: idOrName };
        }
        // area
        const node = ws?.getNode ? ws.getNode(idOrName) : null;
        const displayName = node?.name || ws?.areas?.[idOrName]?.name || idOrName;
        return { displayName, nodeId: idOrName };
    }
    function renderBody(kind, idOrName, bodyEl) {
        const ws = window.worldState;
        if (kind === 'character') {
            const av = window.InspectorAgentView;
            if (av && typeof av.showAgent === 'function') {
                av.showAgent(idOrName, bodyEl);
            }
        }
        else if (kind === 'item') {
            const iv = window.InspectorItemView;
            if (iv && typeof iv.showItem === 'function') {
                const node = ws?.getNode ? ws.getNode(idOrName) : null;
                iv.showItem(idOrName, node || { name: idOrName, type: 'item', properties: {} }, bodyEl);
            }
        }
        else if (kind === 'area') {
            const rv = window.InspectorAreaView;
            if (rv && typeof rv.showArea === 'function') {
                const node = ws?.getNode ? ws.getNode(idOrName) : null;
                rv.showArea(idOrName, node || { name: idOrName, type: 'area', properties: ws?.areas?.[idOrName] || {} }, bodyEl);
            }
        }
    }
    function mount(kind, idOrName, openerEl) {
        const container = ensureContainer();
        _isOpen = true;
        _currentKind = kind;
        _currentIdOrName = idOrName;
        _openerEl = openerEl || document.activeElement || null;
        const { displayName, nodeId } = resolveEntityInfo(kind, idOrName);
        _currentNodeId = nodeId;
        // Shared chrome updates
        const badge = container.querySelector('#entity-editor-kind-badge');
        if (badge) {
            badge.textContent = KIND_LABELS[kind] || kind;
            badge.style.background = KIND_COLORS[kind] || 'var(--bg-inset)';
        }
        const nameInput = container.querySelector('#entity-editor-name-input');
        if (nameInput) {
            nameInput.value = displayName;
        }
        const idLabel = container.querySelector('#entity-editor-node-id');
        if (idLabel) {
            idLabel.textContent = nodeId;
        }
        setInFlight(false);
        // task-675: Segmented tabs for character in full editor header
        const tabsNav = container.querySelector('#entity-editor-tabs');
        if (tabsNav) {
            if (kind === 'character') {
                const tabs = ['Inventory', 'Bio', 'Persona', 'Images', 'Advanced'];
                const av = window.InspectorAgentView;
                const active = av?._getActiveTab?.() || 'Bio';
                tabsNav.replaceChildren(...tabs.map(t => {
                    const btn = document.createElement('button');
                    btn.type = 'button';
                    btn.className = `entity-editor-tab-btn${t === active ? ' active' : ''}`;
                    btn.setAttribute('data-tab', t);
                    btn.textContent = t;
                    btn.addEventListener('click', () => {
                        if (av?._switchAgentTab) {
                            av._switchAgentTab(t);
                        }
                        tabsNav.querySelectorAll('.entity-editor-tab-btn').forEach(b => {
                            b.classList.toggle('active', b.getAttribute('data-tab') === t);
                        });
                    });
                    return btn;
                }));
                tabsNav.style.display = 'flex';
            }
            else {
                tabsNav.style.display = 'none';
                tabsNav.replaceChildren();
            }
        }
        // Render view body
        const bodyEl = container.querySelector('#entity-editor-body');
        if (bodyEl) {
            renderBody(kind, idOrName, bodyEl);
        }
        // Show editor frame
        container.style.display = 'flex';
        // Focus header name
        if (nameInput) {
            nameInput.focus();
            nameInput.select();
        }
    }
    function unmount() {
        if (!_isOpen)
            return;
        _isOpen = false;
        const container = document.getElementById('entity-editor');
        if (container) {
            container.style.display = 'none';
            const bodyEl = container.querySelector('#entity-editor-body');
            if (bodyEl && window.Lit) {
                window.Lit.render(window.Lit.nothing, bodyEl);
            }
        }
        // Return focus to opener
        if (_openerEl && typeof _openerEl.focus === 'function') {
            try {
                _openerEl.focus();
            }
            catch (e) {
                // ignore
            }
        }
        _openerEl = null;
        _currentKind = null;
        _currentIdOrName = null;
        _currentNodeId = null;
    }
    function setInFlight(inFlight) {
        _inFlight = inFlight;
        const statusEl = document.getElementById('entity-editor-status');
        if (!statusEl)
            return;
        if (inFlight) {
            statusEl.textContent = '⏳ Saving...';
            statusEl.className = 'entity-editor-status saving';
        }
        else {
            statusEl.textContent = '✔ Saved';
            statusEl.className = 'entity-editor-status saved';
        }
    }
    function isInFlight() {
        return _inFlight;
    }
    function isOpen() {
        return _isOpen;
    }
    function _reRender() {
        if (!_isOpen || !_currentKind || !_currentIdOrName)
            return;
        const bodyEl = document.getElementById('entity-editor-body');
        if (!bodyEl)
            return;
        const { displayName, nodeId } = resolveEntityInfo(_currentKind, _currentIdOrName);
        _currentNodeId = nodeId;
        const nameInput = document.getElementById('entity-editor-name-input');
        if (nameInput && document.activeElement !== nameInput) {
            nameInput.value = displayName;
        }
        const idLabel = document.getElementById('entity-editor-node-id');
        if (idLabel) {
            idLabel.textContent = nodeId;
        }
        renderBody(_currentKind, _currentIdOrName, bodyEl);
    }
    return {
        mount,
        unmount,
        setInFlight,
        isInFlight,
        isOpen,
        _reRender,
    };
})();
window.EntityEditor = EntityEditor;
