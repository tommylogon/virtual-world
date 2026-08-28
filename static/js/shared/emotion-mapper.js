/**
 * emotion-mapper.js — turn any emotion label into an affect dimension.
 *
 * Strategy:
 *   1. Keyword lookup against a curated LABEL_TO_DIM (mirrors the server's
 *      engine/emotion.py LABEL_TO_DIM) — fast path, covers the authored vocab.
 *   2. Semantic fallback: if EmbeddingClient is configured, embed the label
 *      and pick the nearest dimension anchor by cosine similarity. This is how
 *      a novel / agent-invented label ("flibbertigibbet-forlorn") still lands
 *      on the closest real dimension instead of being dropped.
 *   3. Truly unresolvable -> null (caller sends the raw label and lets the
 *      server's keyword map try; if that fails too it stays a no-op).
 *
 * Returns `{ dimension, label }` or null.
 */
(() => {
    'use strict';

    // Curated label -> affect dimension (mirrors engine/emotion.py LABEL_TO_DIM).
    const LABEL_TO_DIM = {
        neutral: 'calm',
        happy: 'happy', glad: 'happy', joy: 'happy', delighted: 'happy',
        elated: 'elated', excited: 'excited', thrilled: 'excited', mischievous: 'excited',
        proud: 'proud',
        sad: 'sad', down: 'sad', melancholic: 'melancholic', wistful: 'melancholic',
        lonely: 'lonely', nostalgic: 'nostalgic', bored: 'melancholic', tired: 'melancholic', hollow: 'melancholic',
        afraid: 'afraid', fear: 'afraid', scared: 'afraid', terrified: 'afraid', frightened: 'afraid', panic: 'afraid',
        anxious: 'anxious', nervous: 'anxious', worried: 'anxious', restless: 'anxious', paranoid: 'anxious',
        uneasy: 'uneasy', unnerved: 'uneasy', spooked: 'spooked', dread: 'dread',
        angry: 'angry', mad: 'angry', furious: 'angry', irritated: 'irritated', frustrated: 'irritated',
        resentful: 'resentful', bitter: 'resentful', defiant: 'angry',
        aroused: 'aroused', eager: 'eager', craving: 'craving', hungry: 'craving', curious: 'curious',
        affectionate: 'affectionate', loving: 'loving', grateful: 'grateful', admiring: 'admiring',
        ashamed: 'ashamed', embarrassed: 'embarrassed', guilty: 'guilty',
        envious: 'envious', jealous: 'jealous',
        disgusted: 'disgusted', repulsed: 'repulsed',
        calm: 'calm', content: 'content', peaceful: 'peaceful', satisfied: 'satisfied',
        relieved: 'calm', safe: 'calm', quiet: 'calm',
        determined: 'excited', brave: 'proud', resolute: 'excited', focused: 'content',
        surprised: 'surprised'
    };

    // Semantic anchors: one short phrase per dimension to embed for cosine match.
    const DIM_ANCHORS = {
        happy: 'happy joy glad', elated: 'elated ecstatic overjoyed', excited: 'excited thrilled',
        proud: 'proud accomplished', sad: 'sad sorrowful', lonely: 'lonely isolated',
        melancholic: 'melancholic wistful gloomy', nostalgic: 'nostalgic reminiscing fond memories',
        afraid: 'afraid scared frightened', anxious: 'anxious nervous worried', uneasy: 'uneasy unsettled',
        dread: 'dread foreboding doom', spooked: 'spooked creeped out chills',
        angry: 'angry mad furious', irritated: 'irritated annoyed', resentful: 'resentful bitter',
        aroused: 'aroused turned on desire', eager: 'eager keen enthusiastic', craving: 'craving longing wanting',
        curious: 'curious inquisitive intrigued', affectionate: 'affectionate warm fond',
        loving: 'loving adoring devoted', grateful: 'grateful thankful', admiring: 'admiring in awe of',
        ashamed: 'ashamed humiliated', embarrassed: 'embarrassed mortified self-conscious',
        guilty: 'guilty remorseful', envious: 'envious covetous', jealous: 'jealous possessive',
        disgusted: 'disgusted repulsed revulsion', repulsed: 'repulsed sickened',
        calm: 'calm serene tranquil', content: 'content at ease', peaceful: 'peaceful peaceful',
        satisfied: 'satisfied fulfilled', surprised: 'surprised astonished startled'
    };

    const _anchorCache = { embed: false, vectors: null };

    async function _anchorVectors() {
        if (!window.EmbeddingClient || !EmbeddingClient.configured()) return null;
        if (_anchorCache.embed && _anchorCache.vectors) return _anchorCache.vectors;
        const phrases = Object.values(DIM_ANCHORS);
        const vecs = await EmbeddingClient.embed(phrases);
        if (!vecs || !Array.isArray(vecs)) return null;
        const map = {};
        Object.keys(DIM_ANCHORS).forEach((dim, i) => { map[dim] = vecs[i]; });
        _anchorCache.embed = true;
        _anchorCache.vectors = map;
        return map;
    }

    function _cosine(a, b) {
        if (!Array.isArray(a) || !Array.isArray(b) || a.length !== b.length) return 0;
        let dot = 0, na = 0, nb = 0;
        for (let i = 0; i < a.length; i++) {
            dot += a[i] * b[i]; na += a[i] * a[i]; nb += b[i] * b[i];
        }
        return dot / Math.max(1e-12, Math.sqrt(na) * Math.sqrt(nb));
    }

    async function _semanticDim(label) {
        const anchors = await _anchorVectors();
        if (!anchors) return null;
        const q = await EmbeddingClient.embed(label);
        if (!q) return null;
        let best = null, bestScore = -1;
        for (const dim in anchors) {
            const s = _cosine(q, anchors[dim]);
            if (s > bestScore) { bestScore = s; best = dim; }
        }
        return bestScore >= 0.15 ? best : null;
    }

    /**
     * Resolve an emotion label to an affect dimension.
     * @param {string} label
     * @returns {Promise<{dimension:string,label:string}|null>}
     */
    async function resolve(label) {
        const key = String(label || '').trim().toLowerCase();
        if (!key) return null;
        if (LABEL_TO_DIM[key]) return { dimension: LABEL_TO_DIM[key], label: label };
        // substring fallback
        for (const lab in LABEL_TO_DIM) {
            if (lab.includes(key) || key.includes(lab)) return { dimension: LABEL_TO_DIM[lab], label: label };
        }
        // semantic fallback for novel labels
        const dim = await _semanticDim(key);
        return dim ? { dimension: dim, label: label } : null;
    }

    window.EmotionMapper = { resolve, LABEL_TO_DIM, DIM_ANCHORS };
})();
