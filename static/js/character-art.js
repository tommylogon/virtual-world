/**
 * character-art — one resolver for a character's live art, plus a portrait viewer.
 *
 * @module character-art — emotion-aware profile/full-body art + a portrait overlay
 * @contributes CharacterArt.avatarFor/fullArtFor/artFor/artForNodeId (pure) + open()
 * @powers the graph node avatar, the turn-composer people chips, and examine portraits
 * @relates reads worldState graph nodes + players; used by network-manager, turn-scene-view, agent-lens
 * @docs docs/virtualWorld/Characters/Character Images & Expression Packs.md
 *
 * Everywhere a character is shown small (a graph node, a "People here" chip) the
 * art should follow their CURRENT emotion, not the static neutral full body. The
 * expression pack stores per-key `profile`/`full`; this module owns the one
 * fallback chain so those consumers cannot drift:
 *
 *   profile: expressions[emotion].profile -> expressions.neutral.profile -> profile_image -> image
 *   full:    expressions[emotion].full    -> expressions.neutral.full    -> image
 *
 * `open()` is the "big" view: current full body if the character has one,
 * otherwise the profile enlarged. It is opened by examining a character (and by
 * clicking a chip's avatar).
 */
window.CharacterArt = (() => {
    'use strict';

    function _expr(props) { return (props && props.expressions) || {}; }
    function _slot(props, key) { return _expr(props)[key] || {}; }

    /**
     * Profile (bust/avatar) for a character, chosen by emotion.
     * @param {object} props - graph node properties (expressions/profile_image/image)
     * @param {string} [emotionKey] - defaults to 'neutral'
     * @returns {string} image URL or ''
     */
    function avatarFor(props, emotionKey) {
        const emotion = emotionKey || 'neutral';
        return _slot(props, emotion).profile
            || _slot(props, 'neutral').profile
            || (props && (props.profile_image || props.image))
            || '';
    }

    /**
     * Full-body art for a character, chosen by emotion.
     * @param {object} props
     * @param {string} [emotionKey]
     * @returns {string} image URL or ''
     */
    function fullArtFor(props, emotionKey) {
        const emotion = emotionKey || 'neutral';
        return _slot(props, emotion).full
            || _slot(props, 'neutral').full
            || (props && props.image)
            || '';
    }

    /** Both renders at once. */
    function artFor(props, emotionKey) {
        return { profile: avatarFor(props, emotionKey), full: fullArtFor(props, emotionKey) };
    }

    /** Current emotion key for a named player (worldState), else 'neutral'. */
    function emotionOf(name) {
        try {
            const p = window.worldState && worldState.players && worldState.players[name];
            return (p && p.emotion && p.emotion.current) || 'neutral';
        } catch (e) {
            return 'neutral';
        }
    }

    /** Graph node by id, tolerating either worldState accessor. */
    function _node(nodeId) {
        try {
            if (window.worldState && typeof worldState.getNode === 'function') {
                const n = worldState.getNode(nodeId);
                if (n) return n;
            }
            return window.worldState && worldState.graph && worldState.graph.nodes
                && worldState.graph.nodes[nodeId];
        } catch (e) {
            return null;
        }
    }

    /**
     * Resolve {name, emotion, profile, full} for a graph node id. The node's real
     * name gives the current emotion (the node carries the art, the player carries
     * the mood).
     */
    function artForNodeId(nodeId) {
        const node = _node(nodeId);
        const props = (node && node.properties) || {};
        const name = (node && node.name) || '';
        const emotion = name ? emotionOf(name) : 'neutral';
        return Object.assign({ name, emotion }, artFor(props, emotion));
    }

    // ── portrait viewer (DOM) ────────────────────────────────────────

    let _overlay = null;

    function close() {
        if (_overlay) { _overlay.remove(); _overlay = null; }
    }

    function _esc(v) {
        return String(v == null ? '' : v).replace(/&/g, '&amp;').replace(/</g, '&lt;')
            .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    /**
     * Open the large portrait overlay.
     * @param {object} opts - {name, nodeId, props, emotionKey, full, profile}
     *   Give nodeId (preferred — resolves name/props/emotion) or props directly.
     */
    function open(opts = {}) {
        close();
        let name = opts.name || '';
        let profile = opts.profile || '';
        let full = opts.full || '';
        let emotion = opts.emotionKey || 'neutral';
        if (opts.nodeId) {
            const a = artForNodeId(opts.nodeId);
            name = name || a.name;
            profile = profile || a.profile;
            full = full || a.full;
            emotion = opts.emotionKey || a.emotion;
        } else if (opts.props) {
            profile = profile || avatarFor(opts.props, emotion);
            full = full || fullArtFor(opts.props, emotion);
        }
        // Big view = full body if there is one, else the profile enlarged.
        const big = full || profile;
        if (!big) return;   // nothing to show

        const root = document.createElement('div');
        root.id = 'character-portrait';
        root.style.cssText = 'position:fixed;inset:0;z-index:1450;background:rgba(0,0,0,0.82);'
            + 'display:flex;align-items:center;justify-content:center;cursor:zoom-out;';
        const hasBoth = !!(full && profile && full !== profile);
        root.innerHTML = `
            <div style="max-width:96vw;max-height:96vh;display:flex;flex-direction:column;align-items:center;gap:8px;padding:14px;">
                <div style="color:#e6e8ee;font-size:14px;font-weight:600;">${_esc(name || 'portrait')}</div>
                ${hasBoth ? `<div style="display:flex;gap:6px;">
                    <button type="button" class="cp-tab" data-src="${_esc(full)}" style="padding:4px 12px;border-radius:999px;border:1px solid #4a3668;background:#2b1f42;color:#d9baff;cursor:pointer;font-size:11.5px;">🧍 Full body</button>
                    <button type="button" class="cp-tab" data-src="${_esc(profile)}" style="padding:4px 12px;border-radius:999px;border:1px solid #333a45;background:#1d212a;color:#9aa3b2;cursor:pointer;font-size:11.5px;">🖼 Profile</button>
                </div>` : ''}
                <img id="cp-img" src="${_esc(big)}" alt="${_esc(name)}"
                     style="max-width:92vw;max-height:80vh;object-fit:contain;border-radius:10px;border:1px solid #333a45;box-shadow:0 20px 70px rgba(0,0,0,.8);background:#141820;">
                <div style="color:#78828e;font-size:11px;">${emoLabel(emotion)}${hasBoth ? ' · click a tab to switch' : ''} · click anywhere to close</div>
            </div>`;
        root.addEventListener('click', close);
        document.body.appendChild(root);
        _overlay = root;

        root.querySelectorAll('.cp-tab').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const img = root.querySelector('#cp-img');
                if (img) img.src = btn.dataset.src;
                root.querySelectorAll('.cp-tab').forEach(b => {
                    const on = b === btn;
                    b.style.background = on ? '#2b1f42' : '#1d212a';
                    b.style.color = on ? '#d9baff' : '#9aa3b2';
                    b.style.borderColor = on ? '#4a3668' : '#333a45';
                });
            });
        });
    }

    function emoLabel(emotion) {
        return emotion ? `showing: ${String(emotion).replace(/_/g, ' ')}` : '';
    }

    return { avatarFor, fullArtFor, artFor, artForNodeId, emotionOf, open, close };
})();
