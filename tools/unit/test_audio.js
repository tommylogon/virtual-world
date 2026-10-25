/**
 * test_audio.js - Unit tests for procedural Web Audio sound synthesis (task-826).
 */

test('SoundManager instance exists on window with toggleMute', () => {
    assertTrue(!!window.SoundManager, 'SoundManager class exists on window');
    assertTrue(!!window.soundManager, 'soundManager singleton exists on window');
    assertEq(typeof window.soundManager.toggleMute, 'function', 'has toggleMute method');
    assertEq(typeof window.soundManager.playTurn, 'function', 'has playTurn method');
});

test('SoundManager toggles mute and reflects state', () => {
    const sm = new window.SoundManager();
    sm.setMuted(false);
    assertEq(sm.isMuted(), false, 'starts unmuted');

    const muted = sm.toggleMute();
    assertEq(muted, true, 'toggled to muted');
    assertEq(sm.isMuted(), true, 'isMuted reports true');

    const unmuted = sm.toggleMute();
    assertEq(unmuted, false, 'toggled to unmuted');
    assertEq(sm.isMuted(), false, 'isMuted reports false');
});

test('SoundManager playTurn creates dual harmonic tones when AudioContext is present', () => {
    const oscillators = [];
    const gains = [];

    // Mock AudioContext for headless unit test
    const mockCtx = {
        state: 'running',
        currentTime: 0,
        createOscillator() {
            const osc = {
                type: 'sine',
                frequency: {
                    setValueAtTime(val) { osc.freqVal = val; },
                },
                connect() {},
                start() { osc.started = true; },
                stop() { osc.stopped = true; },
            };
            oscillators.push(osc);
            return osc;
        },
        createGain() {
            const g = {
                gain: {
                    setValueAtTime(val) { g.gainVal = val; },
                    exponentialRampToValueAtTime() {},
                },
                connect() {},
            };
            gains.push(g);
            return g;
        },
        createBiquadFilter() {
            return {
                type: 'lowpass',
                frequency: { setValueAtTime() {} },
                connect() {},
            };
        },
        destination: {},
    };

    const prevCtx = window.AudioContext;
    window.AudioContext = function() { return mockCtx; };

    try {
        const sm = new window.SoundManager();
        sm.setMuted(false);
        sm.playTurn();

        assertEq(oscillators.length, 2, 'created dual oscillators for turn chime chord');
        assertEq(Math.round(oscillators[0].freqVal), 523, 'first tone is C5 (523Hz)');
        assertEq(Math.round(oscillators[1].freqVal), 659, 'second tone is E5 (659Hz)');
        assertTrue(oscillators[0].started, 'first tone started');
        assertTrue(oscillators[1].started, 'second tone started');
    } finally {
        window.AudioContext = prevCtx;
    }
});

test('SoundManager suppresses playback when muted', () => {
    let oscCreated = 0;
    const mockCtx = {
        state: 'running',
        currentTime: 0,
        createOscillator() {
            oscCreated++;
            return { connect() {}, start() {}, stop() {} };
        },
        createGain() {
            return { gain: { setValueAtTime() {} }, connect() {} };
        },
        destination: {},
    };

    const prevCtx = window.AudioContext;
    window.AudioContext = function() { return mockCtx; };

    try {
        const sm = new window.SoundManager();
        sm.setMuted(true);
        sm.playClick();
        sm.playTurn();
        sm.playError();
        assertEq(oscCreated, 0, 'no oscillators created while muted');
    } finally {
        window.AudioContext = prevCtx;
    }
});
