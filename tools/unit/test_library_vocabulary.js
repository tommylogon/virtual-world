/**
 * Unit tests for the library Vocabulary tab (task-589).
 *
 * The tab lists/edits compiler vocabulary (biomes, features) — read by the
 * compiler, never materialized — so there must be no "place in world" control.
 * These are source/wiring pins; the live behaviour is a browser check.
 */

const html = window.__readFile('templates/index.html');
const src = window.__readFile('static/js/library-browser.js');

test('the library modal has a Vocabulary tab and pane (task-589)', () => {
    assertTrue(/data-tab="vocabulary"/.test(html), 'tab button exists');
    assertTrue(/id="lib-pane-vocabulary"/.test(html), 'pane exists');
    assertTrue(/id="lib-vocab-root"/.test(html), 'root container exists');
});

test('the vocabulary tab is wired to the browser and the vocabulary API (task-589)', () => {
    assertTrue(/tab === 'vocabulary'/.test(src), 'switchTab handles the tab');
    assertTrue(/loadVocabulary/.test(src), 'loads entries');
    assertTrue(/LibraryApi\.listVocabulary/.test(src), 'reads the vocabulary API');
    assertTrue(/LibraryApi\.saveVocabulary/.test(src), 'saves via the vocabulary API');
    assertTrue(/LibraryApi\.deleteVocabulary/.test(src), 'deletes via the vocabulary API');
});

test('the vocabulary pane offers no place/import action (task-588)', () => {
    const idx = html.indexOf('id="lib-pane-vocabulary"');
    const pane = html.slice(idx, idx + 600);
    assertFalse(/Import to World|placeItem/i.test(pane), 'no place/import control in the pane');
    // And the renderer never reaches the materialize APIs.
    const rv = src.slice(src.indexOf('renderVocabulary'), src.indexOf('renderVocabulary') + 6000);
    assertFalse(/FromLibrary\(/.test(rv), 'no materialize call in the vocabulary renderer');
});
