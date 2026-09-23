/**
 * Shared DOM utilities: escaping, element creation, event helpers.
 *
 * @module shared/dom-utils — small DOM helpers
 * @contributes escaping, element creation, and event helper utilities
 * @powers consistent, XSS-safe DOM construction in the classic scripts
 * @relates leaf utility; used wherever a lit-html template isn't warranted
 * @docs none
 */

/** Escape a string for use in HTML attribute context (replaces " with &quot;) */
function escapeForHtmlAttribute(value) {
    return String(value == null ? '' : value).replace(/"/g, '&quot;');
}

/** Escape a string for use inside a single-quoted JavaScript string literal (replaces ' with \') */
function escapeForJsSingleQuoteString(value) {
    return String(value == null ? '' : value).replace(/'/g, "\\'");
}

/** Sanitize a string to be a valid DOM element id attribute (replaces non-alphanumeric with _) */
function sanitizeToDomId(value) {
    return String(value == null ? '' : value).replace(/[^a-zA-Z0-9_-]/g, '_');
}

/** Create a DOM element with attributes and optional text content */
function createDomElement(tag, attributes = {}, text = '') {
    const element = document.createElement(tag);
    for (const [key, value] of Object.entries(attributes)) {
        if (key === 'className') {
            element.className = value;
        } else if (key === 'style' && typeof value === 'object') {
            Object.assign(element.style, value);
        } else if (key.startsWith('on')) {
            element.addEventListener(key.slice(2), value);
        } else {
            element.setAttribute(key, value);
        }
    }
    if (text) element.textContent = text;
    return element;
}
