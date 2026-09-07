// @ts-check
/**
 * ESLint flat config for VirtualWorld's browser JS.
 *
 * The codebase is script-tag + `window` global-heavy (156 files, no module
 * system). The single most valuable rule here is `no-undef`: it flags any
 * identifier referenced but not in `globals` — exactly the class of bug that
 * bit us in focus.js (`graphManager is not defined` at load time).
 *
 * `globals` is intentionally large: every cross-file global (window.X,
 * config, events, worldState, graphManager, engines, Lit helpers, etc.).
 * The browser provides the DOM/visibility/env/session globals via
 * `scriptOptions: { globals: 'browser' }` for script-style files.
 *
 * Rules are deliberately light — the goal is catching undefined references
 * and obvious mistakes, not enforcing an opinionated style on a legacy
 * codebase. `no-unused-vars` is off (many files assign `window.X` used only
 * from other scripts).
 */
import eslint from '@eslint/js';
import globals from 'globals';

const GLOBALS = {
    // ---- App-wide runtime globals (script-tag wired) ----
    window: 'readonly',
    document: 'readonly',
    console: 'readonly',
    events: 'readonly',
    config: 'readonly',
    worldState: 'readonly',
    graphManager: 'readonly',
    graphNetwork: 'readonly',
    GraphNetwork: 'readonly',
    GraphFocus: 'readonly',
    GraphProjector: 'readonly',
    InspectorHelpers: 'readonly',
    validatorPanel: 'readonly',
    ValidatorPanel: 'readonly',
    itemLib: 'readonly',
    ItemLibraryAI: 'readonly',
    TriggerSuggestAI: 'readonly',
    TriggerSuggestDiff: 'readonly',
    TriggerEditor: 'readonly',
    SearchSelect: 'readonly',
    TagMultiselect: 'readonly',
    AIGenerator: 'readonly',
    LLMClient: 'readonly',
    llmClient: 'readonly',
    api: 'readonly',
    ApiClient: 'readonly',
    Lit: 'readonly',
    actions: 'readonly',
    toasts: 'readonly',
    toastError: 'readonly',
    toastInfo: 'readonly',
    toastSuccess: 'readonly',
    appEvents: 'readonly',
    StructuredFormats: 'readonly',
    extractAssistantText: 'readonly',
    parseJSONFromResponse: 'readonly',
    parseJsonSafely: 'readonly',
    repairJSON: 'readonly',
    extractTopLevelJSON: 'readonly',
    canonicalizeJSON: 'readonly',
    jsonDeepEqual: 'readonly',
    confirm: 'readonly',
    // ---- VW namespace ----
    VW: 'readonly',
}

// ---- Extend GLOBALS with the full set of cross-file identifiers surfaced by
// ESLint's no-undef on the first run (module-ish classes, UI components,
// helper functions). They're all resolved via window.* at runtime.
for (const name of [
    'ActionNormalizer', 'AgentMemory', 'AgentState', 'Choices',
    'CommandPalette', 'ContextWindowManager', 'CreateModal', 'DiffModal',
    'EdgeTypes', 'EmbeddingClient', 'EmotePicker', 'EventBus',
    'GraphContextMenu', 'GraphEventHandlers', 'GraphLayoutEngine',
    'GraphNodeOps', 'GraphOverlays', 'GraphTooltips', 'GraphTreeView',
    'HumanTurnComposer', 'InspectorAgentView', 'InspectorAreaView',
    'InspectorBehaviors', 'InspectorItemView', 'InspectorLore',
    'InspectorMemory', 'InspectorPanel', 'InspectorPaperdoll',
    'InspectorTriggers', 'InspectorWayView', 'ItemLibraryContents',
    'ItemLibraryPlacement', 'NLEditorAgent', 'NLEditorGhosts',
    'NLEditorStaging', 'NLEditorTools', 'NLEditorUI', 'NodeBadges',
    'Notyf', 'PlanManager', 'PlanTracker', 'PromptBuilder', 'RateLimiter',
    'ResponseParser', 'SaveLoadView', 'ScenarioManager', 'ScenarioStatus',
    'ScenarioWizard', 'SettingsView', 'SkyScape', 'StreamControlMode',
    'StreamFilters', 'StreamPersistence', 'StreamRawLLM', 'StreamScrubber',
    'StreamTurnCards', 'ThreatDetector', 'TriggerGraph', 'TriggerTypes',
    'TurnFeed', 'TurnQueue', 'VitalThresholds', 'WayAuthoring',
    'WorldExport', 'agent', 'agentLens', 'copyPromptToClipboard',
    'durabilityChip', 'escapeForHtmlAttribute', 'eventStream',
    'filterItemLibrary', 'generateWithAI', 'graphEditor', 'hideInspectorPanel',
    'inspector', 'libraryBrowser', 'loadGameList', 'narrationUI',
    'newScenario', 'openCreateModal', 'populateSettingsForm', 'reinitChoices',
    'restartScenario', 'runAction', 'saveGame', 'saveScenarioToFile',
    'selectAgent', 'startAgent', 'stopAgent', 'storage', 'tippy',
    'toastWarning', 'toggleDoorState', 'toggleSpectator', 'ui',
    'viewerExitMap', 'vis', 'worldSync',
]) {
    GLOBALS[name] = 'readonly';
}

export default [
    { ignores: ['**/node_modules/**', '**/.git/**', 'tests/**', 'static/js/vendor/**'] },
    {
        files: ['static/js/**/*.js'],
        languageOptions: {
            ecmaVersion: 2022,
            sourceType: 'script',
            globals: { ...globals.browser, ...GLOBALS },
        },
        rules: {
            'no-undef': 'error',
            'no-redeclare': 'off',
            'no-unused-vars': 'off',
            'no-console': 'off',
            'no-constant-condition': 'off',
            'no-global-assign': 'off',
        },
    },
    // The one genuine ES module in the app loads via `type="module"`; it
    // imports window.Lit and must be linted as a module (no script globals).
    {
        files: ['static/js/shared/lit-bootstrap.js'],
        languageOptions: {
            ecmaVersion: 2022,
            sourceType: 'module',
            globals: { ...globals.browser, ...GLOBALS },
        },
        rules: {
            'no-undef': 'error',
            'no-unused-vars': 'off',
            'no-console': 'off',
        },
    },
];