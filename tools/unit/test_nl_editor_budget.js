/** Unit tests for NlEditorBudget — NL editor LLM budget knobs (task-422). */
'use strict';
const B = window.NlEditorBudget;

test('unknown model gets the conservative token cap, not an assumed large one', () => {
    assertEq(B.contextLengthFor('some-local-model'), null, 'unknown -> null');
    assertEq(B.defaultMaxTokens('some-local-model'), B.CONSERVATIVE_MAX_TOKENS, 'unknown -> conservative');
    assertEq(B.defaultMaxTokens(null), B.CONSERVATIVE_MAX_TOKENS, 'missing model -> conservative');
});

test('model context window is matched by substring', () => {
    assertEq(B.contextLengthFor('gpt-4o'), 128000, 'gpt-4o');
    assertEq(B.contextLengthFor('anthropic/claude-3.5-sonnet'), 200000, 'openrouter claude');
    assertEq(B.contextLengthFor('llama3-8b-8192'), 8192, 'groq llama');
    assertEq(B.contextLengthFor('qwen/qwen3.5-9b'), 32768, 'local qwen');
});

test('default maxTokens is half the model window, capped at 60000', () => {
    assertEq(B.defaultMaxTokens('qwen/qwen3.5-9b'), 16384, 'qwen: 32768/2');
    assertEq(B.defaultMaxTokens('gpt-4o'), 60000, 'gpt-4o: capped at 60000');
});

test('defaults reproduce today behaviour (100 / 30 / 8 / 10)', () => {
    const d = B.defaultBudget('unknown-model');
    assertEq(d.maxIterations, 100, 'maxIterations');
    assertEq(d.maxMessages, 30, 'maxMessages');
    assertEq(d.recentTurnCount, 8, 'recentTurnCount');
    assertEq(d.maxCriticalMessages, 10, 'maxCriticalMessages');
});

test('clamp bounds absurd values to sane limits', () => {
    const c = B.clampBudget({ maxIterations: 0, maxMessages: -5, recentTurnCount: 100000, maxCriticalMessages: 0 }, 'gpt-4o');
    assertEq(c.maxIterations, 1, '0 -> floor 1');
    assertEq(c.maxMessages, 1, 'negative -> floor 1');
    assertEq(c.recentTurnCount, 100, '100000 -> ceiling 100');
    assertEq(c.maxCriticalMessages, 1, '0 -> floor 1');
});

test('clamp caps maxTokens to the model window when known', () => {
    const c = B.clampBudget({ maxTokens: 9999999 }, 'qwen/qwen3.5-9b');
    assertEq(c.maxTokens, 32768, '10x window -> clamped to window');
    const u = B.clampBudget({ maxTokens: 9999999 }, 'unknown-model');
    assertEq(u.maxTokens, 1000000, 'unknown -> absolute ceiling');
});

test('clamp fills missing knobs from the model-aware defaults', () => {
    const c = B.clampBudget({}, 'qwen/qwen3.5-9b');
    assertEq(c.maxIterations, 100, 'default iterations');
    assertEq(c.maxTokens, 16384, 'default tokens for qwen');
    assertEq(c.maxMessages, 30, 'default messages');
    const empty = B.clampBudget({ maxTokens: '' }, 'qwen/qwen3.5-9b');
    assertEq(empty.maxTokens, 16384, 'empty string -> default, not NaN');
});
