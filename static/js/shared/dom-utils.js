/**
 * Shared DOM utilities: HTML escaping for the classic scripts.
 *
 * @module shared/dom-utils — small DOM helpers
 * @contributes the HTML attribute escaper
 * @powers consistent, XSS-safe DOM construction in the classic scripts
 * @relates leaf utility; used wherever a lit-html template isn't warranted
 * @docs none
 */

/** Escape a string for use in HTML attribute context (replaces " with &quot;) */
function escapeForHtmlAttribute(value) {
    return String(value == null ? '' : value).replace(/"/g, '&quot;');
}
