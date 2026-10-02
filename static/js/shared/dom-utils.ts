/**
 * Shared DOM utilities: HTML escaping for the classic scripts.
 *
 * @module shared/dom-utils — small DOM helpers
 * @contributes the HTML attribute escaper
 * @powers consistent, XSS-safe DOM construction in the classic scripts
 * @relates leaf utility; used wherever a lit-html template isn't warranted
 * @docs none
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

/** Escape a string for use in HTML attribute context (replaces " with &quot;) */
function escapeForHtmlAttribute(value: unknown): string {
    return String(value == null ? '' : value).replace(/"/g, '&quot;');
}
