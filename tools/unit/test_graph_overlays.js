/**
 * test_graph_overlays.js - Unit tests for graph overlays (task-642).
 * Verifies distinct color mappings for heat, sound, light, and overlay palette distinctions.
 */
'use strict';

test('heatColors maps temperature ranges to distinct thermal color pairs', () => {
    const GO = window.GraphOverlays;
    assertTrue(!!GO, 'GraphOverlays defined');

    const freezing = GO.heatColors(-25);
    assertEq(freezing.background, '#0a0a2e');
    assertEq(freezing.border, '#6e9eff');

    const cool = GO.heatColors(10);
    assertEq(cool.background, '#1a2840');
    assertEq(cool.border, '#58a6ff');

    const warm = GO.heatColors(30);
    assertEq(warm.background, '#3a2a18');
    assertEq(warm.border, '#e3b341');

    const blazing = GO.heatColors(55);
    assertEq(blazing.background, '#4a1010');
    assertEq(blazing.border, '#f85149');
});

test('noiseColors provides distinct palette from heat and light scales', () => {
    const GO = window.GraphOverlays;
    const quiet = GO.noiseColors('quiet');
    const moderate = GO.noiseColors('moderate');
    const busy = GO.noiseColors('busy');
    const chaotic = GO.noiseColors('chaotic');

    assertEq(quiet.background, '#0f241d');
    assertEq(quiet.border, '#2ea043');

    assertEq(moderate.background, '#13382c');
    assertEq(moderate.border, '#3fb950');

    assertEq(busy.background, '#1b4b52');
    assertEq(busy.border, '#38bdf8');

    assertEq(chaotic.background, '#3b1d42');
    assertEq(chaotic.border, '#d946ef');
});

test('areaEnvironment resolves temperature and noise from node properties or state', () => {
    const GO = window.GraphOverlays;

    window.worldState = {
        areas: {
            'Forge': { environment: { temperature: 48, noise: 'loud' } }
        },
        graph: {
            nodes: {
                'area_forge_1': {
                    id: 'area_forge_1',
                    name: 'Forge',
                    type: 'area',
                    properties: { environment: { temperature: 52, noise: 'loud' } }
                }
            }
        }
    };

    const env = GO.areaEnvironment('area_forge_1');
    assertEq(env.temperature, 52, 'reads node properties.environment');
    assertEq(env.noise, 'loud');
});
