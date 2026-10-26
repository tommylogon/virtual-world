/**
 * Unit tests for ApiClient helpers (bug-554).
 */

test('ApiClient._errorMessage surfaces reason when error is absent (bug-554)', () => {
    const fn = window.ApiClient._errorMessage;
    const resp = { status: 400, statusText: 'BAD REQUEST' };
    const data = { ok: false, mode: 'character', reason: 'The dead do not wait.' };
    assertEq(fn(resp, data), 'The dead do not wait.', 'surfaces engine refusal reason');
});

test('ApiClient._errorMessage prefers error over reason, message, and detail', () => {
    const fn = window.ApiClient._errorMessage;
    const resp = { status: 400, statusText: 'BAD REQUEST' };
    const data = {
        error: 'Primary error',
        reason: 'Secondary reason',
        message: 'Tertiary message',
        detail: 'Quaternary detail',
    };
    assertEq(fn(resp, data), 'Primary error', 'error has first precedence');
});

test('ApiClient._errorMessage falls back to message then detail', () => {
    const fn = window.ApiClient._errorMessage;
    const resp = { status: 404, statusText: 'NOT FOUND' };
    assertEq(fn(resp, { message: 'Item not found' }), 'Item not found', 'uses message');
    assertEq(fn(resp, { detail: 'Missing identifier' }), 'Missing identifier', 'uses detail');
});

test('ApiClient._errorMessage hides traceback behind generic status line', () => {
    const fn = window.ApiClient._errorMessage;
    const resp = { status: 500, statusText: 'INTERNAL SERVER ERROR' };
    const data = { error: 'Traceback (most recent call last):\n  File "app.py", line 42, in route\nValueError' };
    assertEq(fn(resp, data), 'Request failed (500 INTERNAL SERVER ERROR)', 'traceback hidden behind status line');

    const dataReason = { reason: 'File "engine/timeskip.py", line 10, in broken\nNameError' };
    assertEq(fn(resp, dataReason), 'Request failed (500 INTERNAL SERVER ERROR)', 'file pattern hidden behind status line');
});

test('ApiClient._errorMessage returns generic status line for empty or null payload', () => {
    const fn = window.ApiClient._errorMessage;
    const resp = { status: 400, statusText: 'BAD REQUEST' };
    assertEq(fn(resp, null), 'Request failed (400 BAD REQUEST)', 'null data falls back');
    assertEq(fn(resp, {}), 'Request failed (400 BAD REQUEST)', 'empty data falls back');
});
