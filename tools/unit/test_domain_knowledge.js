/**
 * tools/unit/test_domain_knowledge.js - unit tests for task-968:
 * PromptBuilder CONTEXT_SECTIONS.knowledge + InspectorPersonaView domain controls.
 */
'use strict';

test('PromptBuilder CONTEXT_SECTIONS.knowledge renders domains, skills, knowledge_records, and blind spots', () => {
    const pb = window.PromptBuilder;
    assertTrue(typeof pb.CONTEXT_SECTIONS.knowledge === 'function', 'knowledge section registered');
    assertTrue(typeof pb.buildKnowledgeAndBlindSpotsContext === 'function', 'builder exported');

    const zoe = {
        name: 'Zoe',
        domains: [
            {
                domain: 'silicone_molding',
                level: 'expert',
                notes: 'platinum-cure casting and sulfur inhibition',
                jargon_terms: ['platinum_cure', 'shore_hardness'],
            },
            {
                domain: 'sports',
                level: 'ignorant',
                notes: 'no clue about rules or teams',
                jargon_terms: [],
            },
        ],
        skills: { medicine: 2, stealth: 0 },
        knowledge_records: [
            { type: 'recipe', data: { recipe: 'silicone_cast' }, text: 'Knows recipe: silicone_cast' },
            { type: 'fact', data: { fact: 'Sulfur clay ruins platinum silicone' }, text: 'Sulfur clay ruins platinum silicone' },
        ],
    };

    const rendered = pb.buildContextBlock(zoe, { phase: 'decide' }, ['knowledge']);
    assertTrue(rendered.includes('silicone_molding (expert: platinum-cure casting and sulfur inhibition)'), 'includes expert domain');
    assertTrue(rendered.includes('[jargon: platinum_cure, shore_hardness]'), 'includes jargon terms');
    assertTrue(rendered.includes('Skills: medicine (+2)'), 'includes non-zero skill and skips 0 skill');
    assertTrue(!rendered.includes('stealth'), 'omits zero-value skill');
    assertTrue(rendered.includes('Known recipes: silicone_cast'), 'includes recipe from knowledge_records');
    assertTrue(rendered.includes('Known facts: Sulfur clay ruins platinum silicone'), 'includes fact from knowledge_records');
    assertTrue(rendered.includes('Blind spots (ignorant): sports: no clue about rules or teams'), 'includes explicit blind spot');
});

test('PromptBuilder CONTEXT_SECTIONS.knowledge returns empty string for prose-only characters', () => {
    const pb = window.PromptBuilder;
    const plain = { name: 'Plain', skills: { stealth: 0 } };
    assertEq(pb.buildContextBlock(plain, { phase: 'decide' }, ['knowledge']), '');
});

test('InspectorPersonaView structured domains normalize, render, and collect cleanly (task-968)', () => {
    const PV = window.InspectorPersonaView;
    assertTrue(typeof PV._normalizeDomainEntry === 'function', '_normalizeDomainEntry exists');
    assertTrue(typeof PV._domainRowHtml === 'function', '_domainRowHtml exists');
    assertTrue(typeof PV._collectPersona === 'function', '_collectPersona exists');

    const legacy = PV._normalizeDomainEntry('Silicone Molding');
    assertEq(legacy.domain, 'silicone_molding', 'legacy domain slug');
    assertEq(legacy.level, 'familiar', 'legacy domain defaults to familiar');

    const structured = PV._normalizeDomainEntry({
        domain: 'Law',
        level: 'expert',
        notes: 'Contract and tort litigation',
        jargon_terms: ['estoppel', 'consideration'],
    });
    assertEq(structured.domain, 'law', 'structured domain slug');
    assertEq(structured.level, 'expert', 'structured level');
    assertEq(structured.notes, 'Contract and tort litigation', 'structured notes');
    assertEq(structured.jargon_terms.join(','), 'estoppel,consideration', 'structured jargon_terms');

    const hostState = {
        charName: 'Kayla',
        escName: 'Kayla',
        tab: 'persona',
        persona: {
            structured: true,
            record: {
                capabilities: {
                    domains: [structured],
                },
            },
            schema: {
                properties: {
                    capabilities: {
                        properties: {
                            domains: { type: 'array', description: 'domain competence' },
                        },
                    },
                },
            },
            hints: {},
            suggestions: {},
            dirty: false,
            msg: '',
            prose: '',
            prose_stale: false,
            warnings: [],
            openSections: ['capabilities'],
        },
    };
    const mockRow = {
        querySelector(sel) {
            if (sel === '[data-domain-field="domain"]') return { value: 'Law' };
            if (sel === '[data-domain-field="level"]') return { value: 'expert' };
            if (sel === '[data-domain-field="notes"]') return { value: 'Contract and tort litigation' };
            if (sel === '.pf-chips') {
                return {
                    querySelector(s) {
                        if (s === 'input[type="hidden"]') return { value: 'estoppel\nconsideration' };
                        return null;
                    },
                };
            }
            return null;
        },
    };
    const mockContainer = {
        querySelector(sel) {
            if (sel === '[data-domain-list="capabilities.domains"]') {
                return {
                    querySelectorAll(s) {
                        return s === '[data-domain-row]' ? [mockRow] : [];
                    },
                };
            }
            return null;
        },
        querySelectorAll() { return []; },
    };

    PV.bind(hostState, mockContainer);
    const html = PV.html();
    assertTrue(html.includes('data-domain-list="capabilities.domains"'), 'renders domain list container');
    assertTrue(html.includes('data-domain-row'), 'renders domain row');
    assertTrue(html.includes('data-domain-field="domain"'), 'renders domain slug input');
    assertTrue(html.includes('value="law"'), 'renders normalized domain slug');
    assertTrue(html.includes('<option value="expert" selected>expert</option>'), 'selects expert level');
    assertTrue(html.includes('id="mind-persona-add-domain"'), 'renders add domain button');

    const collected = PV._collectPersona();
    assertTrue(Array.isArray(collected.capabilities?.domains), 'collects capabilities.domains');
    assertEq(collected.capabilities.domains[0].domain, 'law', 'collected domain slug');
    assertEq(collected.capabilities.domains[0].level, 'expert', 'collected domain level');
    assertEq(collected.capabilities.domains[0].notes, 'Contract and tort litigation', 'collected domain notes');
    assertEq(collected.capabilities.domains[0].jargon_terms.join(','), 'estoppel,consideration', 'collected jargon_terms');
    PV.bind(null, null);
});
