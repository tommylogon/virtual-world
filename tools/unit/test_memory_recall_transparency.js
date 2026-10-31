/**
 * tools/unit/test_memory_recall_transparency.js
 *
 * Targeted unit tests for Recall Transparency & Negative Knowledge (task-786):
 * - buildAlreadyKnownContext surfaces kind: "absence" memories to block redundant re-searching
 * - InspectorMindView._cardHtml renders signal badges for recalled memories
 * - InspectorMindView._detailHtml renders the Recall Provenance breakdown chip
 */

test('PromptBuilder.buildAlreadyKnownContext surfaces kind: "absence" memories (task-786)', () => {
    const PB = window.PromptBuilder;
    assertTrue(typeof PB.buildAlreadyKnownContext === 'function', 'buildAlreadyKnownContext exists');

    const prevPlayers = window.worldState.data?.players;
    window.worldState.data = window.worldState.data || {};
    window.worldState.data.players = {
        Kaelen: {
            memories: [
                {
                    id: 'abs_1',
                    kind: 'absence',
                    target: 'healing_salve',
                    location: 'Old Apothecary',
                    text: 'Confirmed absent: healing_salve is not in Old Apothecary.'
                },
                {
                    id: 'item_1',
                    kind: 'item',
                    name: 'brass key'
                }
            ]
        }
    };

    try {
        const context = PB.buildAlreadyKnownContext('Kaelen');
        assertTrue(context.includes('=== ALREADY KNOWN ==='), 'includes ALREADY KNOWN header');
        assertTrue(context.includes('brass key'), 'includes examined item');
        assertTrue(context.includes('You already confirmed absent or empty: healing_salve in Old Apothecary.'), 'surfaces absence memory');
    } finally {
        if (prevPlayers) window.worldState.data.players = prevPlayers;
    }
});

test('InspectorMindView renders recall provenance badges and breakdown chip (task-786)', () => {
    const MV = window.InspectorMindView;
    assertTrue(typeof MV._cardHtml === 'function', '_cardHtml exists');
    assertTrue(typeof MV._detailHtml === 'function', '_detailHtml exists');

    const memWithProv = {
        id: 'mem_prov_1',
        text: 'Mikka handed over the supplies in the courtyard.',
        tick: 45,
        source: 'auto',
        type: 'event',
        category: 'social',
        location: 'Courtyard',
        entity_ids: ['player_mikka', 'area_courtyard'],
        importance: 6,
        _provenance: {
            score: 8.8,
            percent_match: 88,
            primary_signal: 'spatial',
            channels: {
                spatial: 3.5,
                social: 2.5,
                need: 2.0,
                semantic: 0.8
            },
            points: {
                spatial: 35,
                social: 25,
                need: 20,
                semantic: 8
            }
        }
    };

    // 1. Verify badge in _cardHtml
    const cardHtml = MV._cardHtml(memWithProv);
    assertTrue(cardHtml.includes('📍 spatial 88%') || cardHtml.includes('spatial'), 'card renders spatial recall signal badge');

    // 2. Verify breakdown chip in _detailHtml
    const detailHtml = MV._detailHtml(memWithProv, [memWithProv]);
    assertTrue(detailHtml.includes('Recall Provenance'), 'detail view contains Recall Provenance section');
    assertTrue(detailHtml.includes('Match: 88%'), 'detail view displays match percentage');
    assertTrue(detailHtml.includes('Spatial (+35)'), 'detail view renders spatial point contribution');
    assertTrue(detailHtml.includes('Social (+25)'), 'detail view renders social point contribution');
    assertTrue(detailHtml.includes('Need (+20)'), 'detail view renders need point contribution');
    assertTrue(detailHtml.includes('Semantic (+8)'), 'detail view renders semantic point contribution');
});
