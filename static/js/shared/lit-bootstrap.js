/**
 * LitHTML bootstrap (task-216)
 *
 * Loads lit-html (vendored, no CDN) as an ES module and stamps the
 * `html` tag, `render()`, and the directives used by the inspector views
 * onto `window.Lit` so classic (synchronous) scripts can use them.
 *
 * Classic scripts can't `import`, and module scripts are deferred — which
 * is what made the original edge-inspector PoC race with the other
 * inspectors that write to the same #inspector-panel. This module is the
 * ONE deferred load; the inspector files themselves stay classic scripts
 * and reference `window.Lit` only inside functions (never at parse time),
 * so there is no async race.
 */
import { html, svg, render, nothing, noChange } from 'lit-html';
import { classMap } from 'lit-html/directives/class-map.js';
import { styleMap } from 'lit-html/directives/style-map.js';
import { repeat } from 'lit-html/directives/repeat.js';
import { ifDefined } from 'lit-html/directives/if-defined.js';
import { guard } from 'lit-html/directives/guard.js';
import { live } from 'lit-html/directives/live.js';
import { unsafeHTML } from 'lit-html/directives/unsafe-html.js';

/**
 * Render a lit-html TemplateResult into the inspector panel.
 * Central render point so nothing can accidentally write raw innerHTML
 * to the same container (which breaks lit-html's diffing).
 * @param {TemplateResult} template - lit-html template to render
 */
export function renderPanel(template) {
    const panel = document.getElementById('inspector-panel');
    if (!panel) return;
    render(template, panel);
}

/**
 * Render a lit-html TemplateResult into any element.
 * @param {TemplateResult} template - lit-html template to render
 * @param {HTMLElement} target - element to render into
 */
export function renderInto(template, target) {
    if (!target) return;
    render(template, target);
}

window.Lit = { html, svg, render, renderInto, renderPanel, nothing, noChange, classMap, styleMap, repeat, ifDefined, guard, live, unsafeHTML };