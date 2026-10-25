"use strict";
/**
 * audio.ts - Procedural Web Audio UI sound synthesis (task-826)
 *
 * Zero external audio files. Generates tactile mechanical clicks, subtle
 * hover blips, harmonic turn chimes, and refusal tones via Web Audio API.
 * Mute state persists across sessions in localStorage.
 *
 * @module audio - procedural Web Audio UI sound synthesis
 * @contributes SoundManager (playClick, playHover, playTurnChime, playError, toggleMute)
 * @powers tactile procedural audio feedback for UI clicks, turn advance, and validation errors
 * @relates used by turn-queue and UI buttons; window.soundManager
 * @docs docs/virtualWorld/UI Reference/Rendering & UI Modules.md
 */
class SoundManager {
    ctx = null;
    masterGain = null;
    muted = false;
    lastHoverTime = 0;
    constructor() {
        if (typeof window !== 'undefined' && typeof localStorage !== 'undefined') {
            this.muted = localStorage.getItem('vw_sound_muted') === 'true';
        }
    }
    initContext() {
        if (this.ctx) {
            if (this.ctx.state === 'suspended') {
                this.ctx.resume().catch(() => { });
            }
            return this.ctx;
        }
        const AudioCtx = typeof window !== 'undefined' ?
            (window.AudioContext || window.webkitAudioContext) :
            null;
        if (!AudioCtx)
            return null;
        try {
            this.ctx = new AudioCtx();
            this.masterGain = this.ctx.createGain();
            this.masterGain.gain.setValueAtTime(this.muted ? 0 : 1, this.ctx.currentTime);
            this.masterGain.connect(this.ctx.destination);
            return this.ctx;
        }
        catch {
            return null;
        }
    }
    isMuted() {
        return this.muted;
    }
    toggleMute() {
        this.muted = !this.muted;
        if (typeof localStorage !== 'undefined') {
            localStorage.setItem('vw_sound_muted', String(this.muted));
        }
        if (this.ctx && this.masterGain) {
            this.masterGain.gain.setValueAtTime(this.muted ? 0 : 1, this.ctx.currentTime);
        }
        return this.muted;
    }
    setMuted(muted) {
        this.muted = muted;
        if (typeof localStorage !== 'undefined') {
            localStorage.setItem('vw_sound_muted', String(this.muted));
        }
        if (this.ctx && this.masterGain) {
            this.masterGain.gain.setValueAtTime(this.muted ? 0 : 1, this.ctx.currentTime);
        }
    }
    playHover() {
        if (this.muted)
            return;
        const now = Date.now();
        if (now - this.lastHoverTime < 50)
            return; // Debounce rapid mouse moves
        this.lastHoverTime = now;
        const ctx = this.initContext();
        if (!ctx || !this.masterGain)
            return;
        const t = ctx.currentTime;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(750, t);
        osc.frequency.exponentialRampToValueAtTime(520, t + 0.02);
        gain.gain.setValueAtTime(0.035, t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 0.02);
        osc.connect(gain);
        gain.connect(this.masterGain);
        osc.start(t);
        osc.stop(t + 0.025);
    }
    playClick() {
        if (this.muted)
            return;
        const ctx = this.initContext();
        if (!ctx || !this.masterGain)
            return;
        const t = ctx.currentTime;
        // Mechanical body click
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'triangle';
        osc.frequency.setValueAtTime(320, t);
        osc.frequency.exponentialRampToValueAtTime(75, t + 0.035);
        gain.gain.setValueAtTime(0.08, t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 0.035);
        osc.connect(gain);
        gain.connect(this.masterGain);
        osc.start(t);
        osc.stop(t + 0.04);
    }
    playTurn() {
        if (this.muted)
            return;
        const ctx = this.initContext();
        if (!ctx || !this.masterGain)
            return;
        const t = ctx.currentTime;
        // Dual-tone harmonic chime (C5 523Hz + E5 659Hz)
        const notes = [523.25, 659.25];
        for (const freq of notes) {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(freq, t);
            gain.gain.setValueAtTime(0.09, t);
            gain.gain.exponentialRampToValueAtTime(0.001, t + 0.35);
            osc.connect(gain);
            gain.connect(this.masterGain);
            osc.start(t);
            osc.stop(t + 0.36);
        }
    }
    playError() {
        if (this.muted)
            return;
        const ctx = this.initContext();
        if (!ctx || !this.masterGain)
            return;
        const t = ctx.currentTime;
        const osc = ctx.createOscillator();
        const filter = ctx.createBiquadFilter();
        const gain = ctx.createGain();
        osc.type = 'sawtooth';
        osc.frequency.setValueAtTime(130, t);
        osc.frequency.exponentialRampToValueAtTime(55, t + 0.16);
        filter.type = 'lowpass';
        filter.frequency.setValueAtTime(320, t);
        gain.gain.setValueAtTime(0.09, t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 0.16);
        osc.connect(filter);
        filter.connect(gain);
        gain.connect(this.masterGain);
        osc.start(t);
        osc.stop(t + 0.18);
    }
    bindUiEvents() {
        if (typeof document === 'undefined' || !document.body)
            return;
        // Event delegation for hover and press on interactive surfaces
        document.body.addEventListener('pointerenter', (e) => {
            const target = e.target?.closest?.('button, .btn, .tab-btn, .toolbar-btn, .menu-item, select, .action-btn');
            if (target && !target.disabled) {
                this.playHover();
            }
        }, true);
        document.body.addEventListener('click', (e) => {
            const target = e.target?.closest?.('button, .btn, .tab-btn, .toolbar-btn, .menu-item, .action-btn');
            if (target && !target.disabled) {
                this.playClick();
            }
        }, true);
    }
}
const soundManager = new SoundManager();
if (typeof window !== 'undefined') {
    window.SoundManager = SoundManager;
    window.soundManager = soundManager;
    if (typeof document !== 'undefined') {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => soundManager.bindUiEvents());
        }
        else {
            soundManager.bindUiEvents();
        }
    }
}
