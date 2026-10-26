/**
 * Ambient globals for the classic-script front end.
 *
 * The app loads plain `<script>` tags and shares state through globals rather
 * than ES module imports, so cross-file symbols are declared here as files are
 * migrated. Prefer a precise shape for a global's used surface over `*FIX*`;
 * widen it as more consumers are converted.
 *
 * See docs/design/typescript-migration.md.
 */

/**
 * ConfigManager (config.js) declares `const config = new ConfigManager()` at
 * top level, so the two configs disagree about `config`:
 *
 * - `tsconfig.json` (build) includes only `.ts`, so the `declare const config`
 *   below is the *only* declaration and it is what the build sees.
 * - `tsconfig.check.json` includes `.js` with allowJs, so `config.js`'s own
 *   declaration wins there and `config` is the inferred `ConfigManager`.
 *
 * That is why `controllingPlayer` has to be declared on *both*: it is assigned
 * dynamically (34 sites) and the class does not declare it, so neither view
 * knows it. Converting config.js is the real fix; this keeps both gates green
 * without a runtime change.
 */
interface ConfigManager {
    controllingPlayer?: string;
    // Every remaining settings key read off `config` across static/js,
    // generated rather than hand-picked: the hand-curated list surfaced one
    // TS2339 at a time. `*FIX*` because these come from storage and their
    // shapes differ per key; the index signature already allowed them, so
    // this documents them instead of widening *FIX*thing.
    background_all?: *FIX*;
    decay_overrides?: *FIX*;
    embed?: *FIX*;
    engine_decay?: *FIX*;
    fields?: *FIX*;
    graphArrows?: *FIX*;
    graphCardinalLayout?: *FIX*;
    graphDamping?: *FIX*;
    graphEdgeWidth?: *FIX*;
    graphGravitationalConstant?: *FIX*;
    graphImprovedLayout?: *FIX*;
    graphItemEdgeLength?: *FIX*;
    graphLabelMaxNodes?: *FIX*;
    graphLabelMinScale?: *FIX*;
    graphLayoutMode?: *FIX*;
    graphMapSpacing?: *FIX*;
    graphMapSpacingAuto?: *FIX*;
    graphRepelEnabled?: *FIX*;
    graphRepelMax?: *FIX*;
    graphRepelMin?: *FIX*;
    graphRepelPull?: *FIX*;
    graphSolver?: *FIX*;
    graphSpringConstant?: *FIX*;
    graphSpringLength?: *FIX*;
    js?: *FIX*;
    lastActionResult?: *FIX*;
    lastProfile?: *FIX*;
    manualMode?: *FIX*;
    mature?: *FIX*;
    maxSteps?: *FIX*;
    minutes_per_tick?: *FIX*;
    neutral_environment?: *FIX*;
    provider?: *FIX*;
    reactiveMode?: *FIX*;
    running?: *FIX*;
    saveFromForm?: *FIX*;
    scenario?: *FIX*;
    sections?: *FIX*;
    seed?: *FIX*;
    showLogs?: *FIX*;
    showRawLLM?: *FIX*;
    simultaneousMode?: *FIX*;
    starting_vitals?: *FIX*;
    stepsRun?: *FIX*;
    streaming?: *FIX*;
    structuredOutput?: *FIX*;
    suppressLocalThinking?: *FIX*;
    temperature?: *FIX*;
    ticks?: *FIX*;
    toLLMConfig?: *FIX*;
    traits?: *FIX*;
    turnBased?: *FIX*;
    turnOrder?: *FIX*;
    apiKey?: string;
    // Graph physics, read by network-manager.ts off `config || {}`. The class in
    // config.ts declares these too, but `ConfigManager` as a type reference
    // resolves to THIS interface, so a member missing here is missing for every
    // caller - the same merge asymmetry that affects `config` itself.
    graphSolver?: string;
    graphLayoutMode?: string;
    graphSpringLength?: number;
    graphGravitationalConstant?: number;
    graphSpringConstant?: number;
    graphDamping?: number;
    graphFocusZoom?: number;
    graphNodeScale?: number;
}

/** ConfigManager singleton (config.js): user settings + feature flags. */
declare const config: {
    rpmLimit?: number;
    tpmLimit?: number;
    maxTokens?: number;
    softMaxTokens?: number;
    model?: string;
    apiBase?: string;
    thinking?: boolean;
    thinkingEffort?: string;
    matureContent?: boolean;
    showRawLLM?: boolean;
    // Semantic-memory embeddings (shared/embedding-client.js). Declared here so
    // converted callers get real types instead of `unknown` from the index
    // signature, which would force a String() cast at every use.
    embedEnabled?: boolean;
    embedUrl?: string;
    embedModel?: string;
    embedApiKey?: string;
    embedDims?: number;
    controllingPlayer?: string;
    apiKey?: string;
    save(): void;
    [key: string]: unknown;
};

/** Remaining shared globals  -  narrowed as their modules are converted. */
declare const worldState: *FIX*;
declare const events: *FIX*;
declare const api: *FIX*;
declare const graphManager: *FIX*;
declare const llmClient: *FIX*;
declare const storage: *FIX*;
declare const VW: *FIX*;
declare const TurnFeed: *FIX*;
declare const PromptBuilder: *FIX*;

/** ApiClient (api.js): the HTTP surface. Only the calls converted code makes. */
declare const ApiClient: {
    saveGraphBackground(background: unknown): Promise<unknown>;
    uploadBackgroundImage(file: File): Promise<{ image?: string } | null>;
    batchGraph(ops: unknown[]): Promise<{ errors?: unknown[] } | null>;
    getWorldGrid(scopeId: string): Promise<unknown>;
    getWorldScopes(flat?: boolean): Promise<unknown>;
    setScopeOffset(scopeId: string, offset?: { x?: number; y?: number; reset?: boolean }): Promise<unknown>;
    updateCharacter(name: string, changes: unknown): Promise<unknown>;
    updatePlayerMemory(name: string, entryId: string, data: unknown): Promise<unknown>;
    updateNode(nodeId: string, data: unknown): Promise<unknown>;
    duplicateNode(nodeId: string): Promise<unknown>;
};

/** AppEventBus singleton (event-bus.js): `state:updated` and friends. */
declare const appEvents: {
    on(event: string, handler: (...args: unknown[]) => void): void;
    off?(event: string, handler: (...args: unknown[]) => void): void;
};

/**
 * window.Lit  -  the vendored lit-html 3.2.1 surface, stamped by
 * `shared/lit-bootstrap.js`.
 *
 * W0 of docs/design/typescript-migration-plan.md: `window.Lit` gates 46 files
 * and ~29,800 lines, so it is declared here rather than per-call. The vendored
 * bundle under `static/js/vendor/lit-html/` ships zero `.d.ts` and is excluded
 * from tsconfig, so tsc cannot infer it. This is the hand-declared option the
 * plan lists as the fallback when adding a dependency is unacceptable; the
 * alternative is `npm i -D lit@3.2.1` plus a `paths` entry.
 *
 * Exactly 14 members, enumerable from lit-bootstrap.js  -  not a guess from call
 * sites. Template *values* are `unknown` because these templates are dynamic by
 * design and lit accepts *FIX*thing at runtime; the directive arguments are
 * typed.
 */
interface LitApi {
    html(strings: TemplateStringsArray, ...values: unknown[]): unknown;
    svg(strings: TemplateStringsArray, ...values: unknown[]): unknown;
    render(result: unknown, container: Element | DocumentFragment): unknown;
    renderInto(template: unknown, target: HTMLElement): void;
    renderPanel(template: unknown): void;
    nothing: symbol;
    noChange: symbol;
    classMap(classInfo: Record<string, boolean>): unknown;
    styleMap(styleInfo: Record<string, string | number | null | undefined>): unknown;
    repeat<T>(items: Iterable<T>, key: (item: T, index: number) => unknown,
               template: (item: T, index: number) => unknown): unknown;
    ifDefined<T>(value: T | undefined): unknown;
    guard(deps: readonly unknown[], f: () => unknown): unknown;
    live(value: unknown): unknown;
    unsafeHTML(value: unknown): unknown;
}

declare const Lit: LitApi;

/**
 * Soak lab singletons (soak/soak-ui.js, soak/soak-state.js). Declared with the
 * surface converted callers use, not a bare `*FIX*`, so soak-app.js type-checks
 * against the real contract.
 */
interface SoakUiApi {
    init(): void;
    toast(message: string, level?: string, durationMs?: number): void;
}

interface SoakStateApi {
    init(): Promise<void>;
    state: { meta?: { scenarios?: unknown[] } | null };
}

declare const SoakUI: SoakUiApi;
declare const SoakState: SoakStateApi;

interface Window {
    Lit: LitApi;
    SoakUI: SoakUiApi;
    SoakState: SoakStateApi;
    // Both are declared as bare `*FIX*` above (9 such globals exist); mirroring
    // that on Window is what makes the `window.worldState?.…` spelling  -  used
    // throughout the views  -  type-check at all.
    worldState: *FIX*;
    VW: *FIX*;
    // The prompt-builder modules build this namespace with Object.assign.
    PromptBuilder: *FIX*;
}

/**
 * Provisional declarations for singletons owned by modules that are still .js.
 *
 * These exist so parallel conversion lanes never have to edit this file  -  it is
 * a hub, and concurrent edits lose declarations. Each is `*FIX*` on purpose and
 * honestly: the real shape belongs to the owning module, and should replace
 * these when that module converts. The plan doc's warning applies  -  a file that
 * compiles against `*FIX*` here is typed only as far as its own logic.
 *
 * Format: name  -  owning module.
 */
declare const InspectorHelpers: *FIX*;   // inspector/helpers.js
declare const GraphToolbar: *FIX*;       // graph/toolbar.js
declare const GraphPhysics: *FIX*;       // graph/physics.js  -  the one physics policy
declare const DiffModal: *FIX*;          // shared/diff-modal.js
declare const WayAuthoring: *FIX*;       // inspector/way-authoring.js
declare const EmbeddingClient: *FIX*;    // shared/embedding-client.js (converted; narrow when convenient)
declare const GraphProjector: *FIX*;     // graph/projector.js
declare const GraphEventHandlers: *FIX*; // graph/event-handlers.js
declare const NodeBadges: *FIX*;         // graph/node-badges.js
declare const ActionVerbs: *FIX*;        // agent/action-verbs.generated.js
declare const ActionNormalizer: *FIX*;   // agent/action-normalizer.js
declare const TurnQueue: *FIX*;          // agent/turn-queue.js
declare const GraphContextMenu: *FIX*;   // graph/context-menu.js
declare const InspectorAgentView: *FIX*; // inspector/agent-view.js
declare const WorldExport: *FIX*;        // ui/world-export.js
declare const GraphFocus: *FIX*;         // graph/focus.js
declare const GraphOverlays: *FIX*;      // graph/overlays.js
declare const GraphTooltips: *FIX*;      // graph/tooltips.js
declare const HumanTurnComposer: *FIX*;  // agent/human-turn-composer.js
declare const PlanTracker: *FIX*;        // agent/plan-tracker.js
declare const ResponseParser: *FIX*;     // agent/response-parser.js
declare const TriggerSuggestAI: *FIX*;   // shared/trigger-suggest-ai.js
declare const InspectorTriggers: *FIX*;  // inspector/trigger-helpers.js
declare const InspectorWayView: *FIX*;   // inspector/way-view.js
declare const ValidatorPanel: *FIX*;     // validator-panel.js
declare const ItemLibraryAI: *FIX*;      // item-library/ai-generation.js
declare const SkyScape: *FIX*;           // sky-scape.js
declare const Structures: *FIX*;         // structures.js
declare const NarrationUi: *FIX*;        // narration-ui.js
/**
 * GraphBackground (graph/graph-background.ts)  -  the map art behind the graph.
 *
 * **Not `*FIX*`, on purpose.** This one was `*FIX*`, and `*FIX*` is why commit
 * 6fd774b8 could delete `refreshForScope`, `reconcileAllForGapChange` and
 * `_reconcileReferenceArt` without `tsc` noticing: every cross-module call was
 * unchecked, and the four call sites guarded each one with
 * `typeof … === 'function'`, so a *deleted function* looked exactly like a
 * module that had not loaded yet. Scope switches and map-pitch changes stopped
 * re-deriving the art and nothing said so.
 *
 * Only the members other modules actually call are declared, and every one is
 * **required**  -  the modules are separate `<script>` tags but they are always
 * loaded together, and all four call sites run long after load, so "the method
 * might not exist" is not a real state here. Adding a member to graph-background
 * and calling it from elsewhere means adding it here too; removing one is now a
 * compile error instead of a silent no-op.
 *
 * `tools/unit/test_graph_background.js` pins the same surface at runtime and
 * fails if *FIX*one reintroduces a `typeof … === 'function'` guard at a call site.
 */
declare const GraphBackground: {
    init(): void;
    showCanvasMenu(event?: unknown): void;
    fitToPaintedGrid(): Promise<void>;
    /** Re-derive the loaded scope's art from its grid (bug-51). */
    refreshForScope(): Promise<void>;
    /** Re-derive every mounted reference after the map pitch moved (task-526). */
    reconcileAllForGapChange(): Promise<void>;
    getExportLayers(): unknown[];
};
declare const InspectorPanelRef: *FIX*;  // inspector/panel.ts (converted)

/** lit-html's template type. Our LitApi types template *values* as unknown. */
type TemplateResult = unknown;

/** Vendored / CDN globals that are not modules. */
declare const tippy: *FIX*;              // tooltip library
declare const vis: *FIX*;                // vis-network, canvas-rendered

/** Toast helpers (ui/create-modal.js and friends): transient notifications. */
declare function toastInfo(message: string, ...rest: unknown[]): void;
declare function toastError(message: string, ...rest: unknown[]): void;

/** GraphLayoutEngine (graph/layout-engine.js): map layout helpers. */
declare const GraphLayoutEngine: {
    GRID_SCALE: number;
    PAINT_UNITS_PER_CELL: number;
    hasPaintedGrid(nodes: unknown): boolean;
    hasPaintedCoords(properties: unknown): boolean;
    gridPosition(properties: unknown, scale?: number): { x: number; y: number } | null;
    mapSpacing(): number;
    nodeScopeId(node: unknown): string | null;
    offsetPxFor(node: unknown, offsets?: unknown, spacing?: number): { x: number; y: number };
    scopedGridPosition(properties: unknown, node: unknown, offsets?: unknown,
                       scale?: number): { x: number; y: number } | null;
    refreshGridLayout(nodesObj?: unknown, offsets?: unknown): number;
};

// >>> window members - generated by tools/window_members.py, do not hand-edit >>>
// Generated by tools/window_members.py  -  do not hand-edit.
//
// Only names a module assigns via `window.X =` belong here: that is what
// makes `window.X` a real, undefined-safe property access. Names that are
// lexical top-level `const` are deliberately absent, because `window.X`
// would typecheck for them while being `undefined` at runtime.
//
// WHY `*FIX*` AND NOT `unknown`: the whole point of this interface is to make
// `window.config.maxTokens` COMPILE. With `unknown` every property access
// through a window member errors, the converter is tempted to drop the
// `window.` prefix again, and we are back to ReferenceError land. `*FIX*`
// keeps the guard intact. Behaviour-correctness beats strictness here: the
// alternative is code that compiles and throws.
//
// Narrow the ones that matter by hand  -  config, appEvents, ApiClient, Lit  - 
// and leave the rest until their owning module earns a real shape.
//
// Sources: 123 names assigned to window across static/js.
interface Window {
    ActionVerbs: *FIX*;
    ActionNormalizer: *FIX*;
    AgentMemory: *FIX*;
    AgentState: *FIX*;
    AutoDressModal: *FIX*;
    ChangesPanel: *FIX*;
    BugReport: *FIX*;
    CharacterArt: *FIX*;
    CommandPalette: *FIX*;
    ContextWindowManager: *FIX*;
    DatasetCollector: *FIX*;
    DiffModal: *FIX*;
    DocPanel: *FIX*;
    EdgeInspector: *FIX*;
    EdgeTypes: *FIX*;
    EditFeed: *FIX*;
    EmbeddingClient: *FIX*;
    EmotePicker: *FIX*;
    EmotionMapper: *FIX*;
    EngineConfigView: *FIX*;
    EnvPresets: *FIX*;
    GraphBackground: *FIX*;
    GraphContextMenu: *FIX*;
    GraphEventHandlers: *FIX*;
    GraphExport: *FIX*;
    GraphFocus: *FIX*;
    GraphNetwork: *FIX*;
    GraphNodeOps: *FIX*;
    GraphOverlays: *FIX*;
    GraphPhysics: *FIX*;
    GraphProjector: *FIX*;
    GraphRelativeLayout: *FIX*;
    GraphScopeTree: *FIX*;
    GraphSeparation: *FIX*;
    GraphToolbar: *FIX*;
    GraphTooltips: *FIX*;
    GraphTreeView: *FIX*;
    HelpCenter: *FIX*;
    HumanTurnComposer: *FIX*;
    InspectorAgentView: *FIX*;
    InspectorBehaviors: *FIX*;
    InspectorHelpers: *FIX*;
    InspectorItemView: *FIX*;
    InspectorLore: *FIX*;
    InspectorMemory: *FIX*;
    InspectorPanel: *FIX*;
    InspectorPaperdoll: *FIX*;
    InspectorTemplateSync: *FIX*;
    InspectorTriggers: *FIX*;
    InspectorWayView: *FIX*;
    InspectorWayViewConnections: *FIX*;
    Involuntary: *FIX*;
    ItemContainment: *FIX*;
    ItemLibraryAI: *FIX*;
    ItemLibraryContents: *FIX*;
    ItemLibraryPlacement: *FIX*;
    ItemLibraryTriggerSuggester: *FIX*;
    KnownBySection: *FIX*;
    NLEditor: *FIX*;
    NLEditorAgent: *FIX*;
    NLEditorDiff: *FIX*;
    NLEditorGhosts: *FIX*;
    NLEditorStaging: *FIX*;
    NLEditorTools: *FIX*;
    NLEditorUI: *FIX*;
    NodeBadges: *FIX*;
    ObjectResponder: *FIX*;
    PlanManager: *FIX*;
    PlanTracker: *FIX*;
    RateLimiter: *FIX*;
    ResponseParser: *FIX*;
    RoomTemplatePalette: *FIX*;
    SaveLoadView: *FIX*;
    ScenarioHealth: *FIX*;
    ScenarioManager: *FIX*;
    ScenarioStatus: *FIX*;
    ScenarioWizard: *FIX*;
    SearchSelect: *FIX*;
    SettingsView: *FIX*;
    SetupChecklist: *FIX*;
    SkyScape: *FIX*;
    SoakApi: *FIX*;
    SoakCharts: *FIX*;
    SoakFormat: *FIX*;
    SoakPresets: *FIX*;
    SoakSpacetime: *FIX*;
    SpriteSheet: *FIX*;
    SpriteSheetGeometry: *FIX*;
    StructuredFormats: *FIX*;
    TagMultiselect: *FIX*;
    ThreatDetector: *FIX*;
    Timeskip: *FIX*;
    TriggerGraph: *FIX*;
    TriggerSuggestAI: *FIX*;
    TriggerSuggestDiff: *FIX*;
    TriggerTypes: *FIX*;
    TurnFeed: *FIX*;
    TurnQueue: *FIX*;
    TurnSceneView: *FIX*;
    TurnYouStrip: *FIX*;
    UndoHistory: *FIX*;
    VWSimRound: *FIX*;
    VWSimultaneous: *FIX*;
    VitalColor: *FIX*;
    VitalThresholds: *FIX*;
    WayAuthoring: *FIX*;
    WorldExport: *FIX*;
    _lastRecallStats: *FIX*;
    _traitLibrary: *FIX*;
    _traitLibraryAt: *FIX*;
    appEvents: *FIX*;
    config: *FIX*;
    escapeForHtmlAttribute: *FIX*;
    events: *FIX*;
    graphManager: *FIX*;
    gridModel: *FIX*;
    llmClient: *FIX*;
    runAction: *FIX*;
    storage: *FIX*;
    structures: *FIX*;
    worldPainter: *FIX*;
}
// <<< window members <<<

// >>> hoisted from converted modules - generated, do not hand-edit >>>
// CreateModal  -  owner: main.ts
declare const CreateModal: *FIX*;       // ui/create-modal.js

// DatasetCollector  -  owner: llm-client.ts
declare const DatasetCollector: { capture(messages: unknown, content: unknown, label: string, extra?: unknown): void } | undefined;

// EmotePicker  -  owner: agent/human-turn-composer.ts
declare const EmotePicker: {
    toggle(wrap: HTMLElement, opts: { onPick(emote: string): void }): void;
    close(wrap: HTMLElement): void;
};

// GraphNetwork  -  owner: graph/event-handlers.ts
// owner: static/js/graph/network-manager.js
declare const GraphNetwork: {
    _applyCardinalOverlay(...args: *FIX*[]): *FIX*;
    _applyHeatOverlay(...args: *FIX*[]): *FIX*;
    _applyLightOverlay(...args: *FIX*[]): *FIX*;
    _applyNodeLabelDecorations(...args: *FIX*[]): *FIX*;
    _applySoundOverlay(...args: *FIX*[]): *FIX*;
    _applyTagIconsToLabels(...args: *FIX*[]): *FIX*;
    _applyTriggerOverlay(...args: *FIX*[]): *FIX*;
    _attachTippyTooltips(...args: *FIX*[]): *FIX*;
    _bindEdgeHoverTooltips(...args: *FIX*[]): *FIX*;
    _captureBaseStyles(...args: *FIX*[]): *FIX*;
    _cellSig(...args: *FIX*[]): *FIX*;
    _clearOverlay(...args: *FIX*[]): *FIX*;
    _computeAmbientLight(...args: *FIX*[]): *FIX*;
    _computeVisibleNodeIds(...args: *FIX*[]): *FIX*;
    _escHtml(...args: *FIX*[]): *FIX*;
    _findGraphEdge(...args: *FIX*[]): *FIX*;
    _fitToSearchMatches(...args: *FIX*[]): *FIX*;
    _heatColors(...args: *FIX*[]): *FIX*;
    _kickClusterPhysics(...args: *FIX*[]): *FIX*;
    _lightColors(...args: *FIX*[]): *FIX*;
    _lightToInt(...args: *FIX*[]): *FIX*;
    _nodeLabelPolicy(...args: *FIX*[]): *FIX*;
    _noiseColors(...args: *FIX*[]): *FIX*;
    _syncLayoutButton(...args: *FIX*[]): *FIX*;
    _tagMetaFor(...args: *FIX*[]): *FIX*;
    _updateOverlayLegend(...args: *FIX*[]): *FIX*;
    applyAutoMapSpacing(...args: *FIX*[]): *FIX*;
    applyFilter(...args: *FIX*[]): *FIX*;
    applyGraphSettings(...args: *FIX*[]): *FIX*;
    applyModePhysics(...args: *FIX*[]): *FIX*;
    applyNodeLabelVisibility(...args: *FIX*[]): *FIX*;
    applyOverlay(...args: *FIX*[]): *FIX*;
    applyTagFilter(...args: *FIX*[]): *FIX*;
    applyVisibility(...args: *FIX*[]): *FIX*;
    buildLegendHTML(...args: *FIX*[]): *FIX*;
    buildLegendRows(...args: *FIX*[]): *FIX*;
    buildNodeConfig(...args: *FIX*[]): *FIX*;
    buildOptions(...args: *FIX*[]): *FIX*;
    isNodePinned(...args: *FIX*[]): *FIX*;
    PHYSICS_NODE_LIMIT: *FIX*;
    nodesOverPhysicsLimit(...args: *FIX*[]): *FIX*;
    buildTooltip(...args: *FIX*[]): *FIX*;
    buildTooltipHtml(...args: *FIX*[]): *FIX*;
    centralGravityFor(...args: *FIX*[]): *FIX*;
    ensureTagLibrary(...args: *FIX*[]): *FIX*;
    filterNodes(...args: *FIX*[]): *FIX*;
    fitView(...args: *FIX*[]): *FIX*;
    hideRevealedAreas(...args: *FIX*[]): *FIX*;
    hideRevealedItems(...args: *FIX*[]): *FIX*;
    init(...args: *FIX*[]): *FIX*;
    legendChrome(...args: *FIX*[]): *FIX*;
    loadGraphData(...args: *FIX*[]): *FIX*;
    syncGraphData(...args: *FIX*[]): *FIX*;
    _nodeProjection(...args: *FIX*[]): *FIX*;
    _posTrace(...args: *FIX*[]): *FIX*;
    _edgeSig(...args: *FIX*[]): *FIX*;
    _scopedEdgeSig(...args: *FIX*[]): *FIX*;
    mapCompact(...args: *FIX*[]): *FIX*;
    mapSizeScale(...args: *FIX*[]): *FIX*;
    nodeSizeScale(...args: *FIX*[]): *FIX*;
    refreshEdgeLengths(...args: *FIX*[]): *FIX*;
    _lastArrangement: string;
    renderTagPanel(...args: *FIX*[]): *FIX*;
    resetOverlayStyles(...args: *FIX*[]): *FIX*;
    revealAreasForWay(...args: *FIX*[]): *FIX*;
    revealItemsForNode(...args: *FIX*[]): *FIX*;
    setTagFilter(...args: *FIX*[]): *FIX*;
    settleSearch(...args: *FIX*[]): *FIX*;
    toggleImages(...args: *FIX*[]): *FIX*;
    toggleInhabitedAreas(...args: *FIX*[]): *FIX*;
    toggleItems(...args: *FIX*[]): *FIX*;
    toggleLayoutMode(...args: *FIX*[]): *FIX*;
    toggleLegend(...args: *FIX*[]): *FIX*;
    togglePhysics(...args: *FIX*[]): *FIX*;
    toggleTagPanel(...args: *FIX*[]): *FIX*;
    toggleTriggers(...args: *FIX*[]): *FIX*;
};

// GraphTreeView  -  owner: ui-controller.ts
declare const GraphTreeView: { renderOutlinePanel(target: Element | null): void };

// ItemLibraryContents  -  owner: item-library.ts
declare const ItemLibraryContents: {
    renderContentsSection(this: ItemLibrary, contents: unknown): unknown;
    removeContent(this: ItemLibrary, idx: unknown): unknown;
    addContentUi(this: ItemLibrary): unknown;
    saveContent(this: ItemLibrary, btn: unknown): unknown;
};

// NLEditorGhosts  -  owner: nl-editor/index.ts
declare const NLEditorGhosts: *FIX*;

// NLEditorStaging  -  owner: nl-editor/index.ts
declare const NLEditorStaging: *FIX*;

// NLEditorTools  -  owner: nl-editor/index.ts
declare const NLEditorTools: *FIX*;

// NLEditorUI  -  owner: nl-editor/index.ts
declare const NLEditorUI: *FIX*;

// SaveLoadView  -  owner: main.ts
declare const SaveLoadView: *FIX*;       // ui/save-load-view.js

// TriggerEditor  -  owner: item-library.ts
declare const TriggerEditor: {
    _renderConditionSummary(conditions: unknown): string[];
    show(...args: unknown[]): unknown;
};

// TriggerGraph  -  owner: item-library.ts
declare const TriggerGraph: {
    triggerToGraph(triggerData: unknown, opts?: Record<string, unknown>): unknown;
    triggersToGraph(triggerData: unknown[]): unknown;
    show(...args: unknown[]): unknown;
    compileToEngine(graph: unknown): Record<string, *FIX*> | null;
    compileToTriggers(graph: unknown): Array<Record<string, *FIX*>>;
    compileError(compiled: unknown): string;
    reportCompileError(compiled: unknown): boolean;
    engineToFormData(compiled: unknown): Record<string, *FIX*>;
    triggerDefFromEdge(edge: unknown, nodes: unknown): Record<string, *FIX*>;
    triggerDefFromProperty(entry: unknown): Record<string, *FIX*> | null;
    normalizeTriggerEntry(entry: unknown): Record<string, *FIX*> | null;
    normalizeTriggerList(value: unknown): Array<Record<string, *FIX*>>;
    triggersFromGraphEdges(...args: unknown[]): unknown[];
};

// agent  -  owner: ui-controller.ts
declare const agent: *FIX*;              // VW.agent, the turn-queue owner (agent/turn-queue.js)

// durabilityChip  -  owner: inspector/paperdoll-view.ts
declare const durabilityChip: (props: unknown) => string;

// hideInspectorPanel  -  owner: graph/edge-inspector.ts
declare function hideInspectorPanel(): void;

// inspector  -  owner: main.ts
declare const inspector: *FIX*;         // inspector/inspector.js

// runAction  -  owner: inspector/agent-view.ts
declare function runAction(command: string, charName: string): void;

// selectAgent  -  owner: ui-controller.ts
declare function selectAgent(name: string): void;

// viewerExitMap  -  owner: agent/prompt-builder/room-context.ts
declare const viewerExitMap: Record<string, ExitEntry>;

// >>> ambient shapes for still-unconverted .js modules >>>
// owner: static/js/item-library/placement.js
declare const ItemLibraryPlacement: {
    pickTarget(...args: *FIX*[]): *FIX*;
    // The generator stopped after pickTarget: a multi-line template literal
    // inside it desynchronised the brace-depth walk, so the three members
    // defined later in the same literal were not seen. Added by hand from
    // item-library/placement.js:134, :160, :202. They are `this`-bound and
    // item-library.ts calls them via .call(this), hence the loose signatures.
    placeInRoom(...args: *FIX*[]): *FIX*;
    placeSelectedInRoom(...args: *FIX*[]): *FIX*;
    updatePlaceButton(...args: *FIX*[]): *FIX*;
};
// <<< ambient shapes <<<

/**
 * The GraphManager instance's fields (graph-manager.js), which is still plain
 * JS and so has no declarations of its own.
 *
 * Needed by `build:ts`, which includes only .ts files: with graph-manager.js
 * excluded from that program, `GraphManager` resolves to nothing else. It is
 * inert for `tsconfig.check.json`, which includes the .js and prefers the real
 * class - the same config asymmetry documented for `config`.
 *
 * `*FIX*` rather than inferred shapes on purpose: `unknown` rejects every
 * property access, which just moves the error to each reader.
 *
 * Disappears when graph-manager.js converts.
 */
interface GraphManager {
    _bulkBar: *FIX*;
    _bulkScopesFilled: boolean;
    _bulkSelection: *FIX*;
    _cardinalLayout: *FIX*;
    _contextTarget: *FIX*;
    _edgeLabelSize: number;
    _floorFilter: string;
    _floorOptions: *FIX*;
    _labelCache: *FIX*;
    _lastSig: string;
    _nodeProj: *FIX*;
    _lastEdgeSig: string;
    _legendEl: *FIX*;
    _mapSpacingAuto: *FIX*;
    _nodeLabelsShown: *FIX*;
    _paintedGridLayout: boolean;
    _pendingConnection: *FIX*;
    _physicsEnabled: boolean;
    _revealedAreaIds: *FIX*;
    _revealedItemIds: *FIX*;
    _scopeFilter: *FIX*;
    _scopeOffsets: *FIX*;
    _scopeSummaries: *FIX*;
    _searchQuery: string;
    _showEdgeLabels: boolean;
    _showImages: *FIX*;
    _showItems: boolean;
    _showNodeLabels: *FIX*;
    _showOnlyInhabitedAreas: boolean;
    _viewMode: string;
    network: *FIX*;
    nodes: *FIX*;
}

// ---------------------------------------------------------------------------
// Domain models (static/js/types/models/)
// Ambient type definitions for classic scripts and global scope
// ---------------------------------------------------------------------------

type BaseNodeModel<TProps extends Record<string, unknown> = Record<string, unknown>> = import('./models/index.js').BaseNodeModel<TProps>;
type ItemModel = import('./models/index.js').ItemModel;
type ItemProperties = import('./models/index.js').ItemProperties;
type AreaModel = import('./models/index.js').AreaModel;
type AreaProperties = import('./models/index.js').AreaProperties;
type WayModel = import('./models/index.js').WayModel;
type WayProperties = import('./models/index.js').WayProperties;
type CharacterNodeModel = import('./models/index.js').CharacterNodeModel;
type CharacterNodeProperties = import('./models/index.js').CharacterNodeProperties;
type TriggerModel = import('./models/index.js').TriggerModel;

type PlayerRuntimeModel = import('./models/index.js').PlayerRuntimeModel;
type PlayerVitals = import('./models/index.js').PlayerVitals;
type PlayerStats = import('./models/index.js').PlayerStats;
type GoalModel = import('./models/index.js').GoalModel;
type GoalStatus = import('./models/index.js').GoalStatus;
type ObligationModel = import('./models/index.js').ObligationModel;
type PlanModel = import('./models/index.js').PlanModel;
type PlanStep = import('./models/index.js').PlanStep;
type ActivePursuitModel = import('./models/index.js').ActivePursuitModel;
type ConditionInstance = import('./models/index.js').ConditionInstance;

interface MemoryRecord extends import('./models/index.js').MemoryRecord {}

declare namespace Models {
    export type BaseNode<TProps extends Record<string, unknown> = Record<string, unknown>> = import('./models/index.js').BaseNodeModel<TProps>;
    export type BaseNodeModel<TProps extends Record<string, unknown> = Record<string, unknown>> = import('./models/index.js').BaseNodeModel<TProps>;
    export type Item = import('./models/index.js').ItemModel;
    export type ItemModel = import('./models/index.js').ItemModel;
    export type ItemProperties = import('./models/index.js').ItemProperties;
    export type Area = import('./models/index.js').AreaModel;
    export type AreaModel = import('./models/index.js').AreaModel;
    export type AreaProperties = import('./models/index.js').AreaProperties;
    export type Way = import('./models/index.js').WayModel;
    export type WayModel = import('./models/index.js').WayModel;
    export type WayProperties = import('./models/index.js').WayProperties;
    export type Character = import('./models/index.js').CharacterNodeModel;
    export type CharacterNodeModel = import('./models/index.js').CharacterNodeModel;
    export type CharacterNodeProperties = import('./models/index.js').CharacterNodeProperties;
    export type Trigger = import('./models/index.js').TriggerModel;
    export type TriggerModel = import('./models/index.js').TriggerModel;

    export type PlayerRuntime = import('./models/index.js').PlayerRuntimeModel;
    export type PlayerRuntimeModel = import('./models/index.js').PlayerRuntimeModel;
    export type PlayerVitals = import('./models/index.js').PlayerVitals;
    export type PlayerStats = import('./models/index.js').PlayerStats;
    export type Memory = import('./models/index.js').MemoryRecord;
    export type MemoryRecord = import('./models/index.js').MemoryRecord;
    export type Goal = import('./models/index.js').GoalModel;
    export type GoalModel = import('./models/index.js').GoalModel;
    export type GoalStatus = import('./models/index.js').GoalStatus;
    export type Obligation = import('./models/index.js').ObligationModel;
    export type ObligationModel = import('./models/index.js').ObligationModel;
    export type Plan = import('./models/index.js').PlanModel;
    export type PlanModel = import('./models/index.js').PlanModel;
    export type PlanStep = import('./models/index.js').PlanStep;
    export type ActivePursuitModel = import('./models/index.js').ActivePursuitModel;
    export type ConditionInstance = import('./models/index.js').ConditionInstance;
}

interface Window {
    UiPrimitives?: {
        StatusBadge(opts: { label: string; color?: string; icon?: string; active?: boolean; title?: string }): unknown;
        CollapsibleSection(opts: { title: string; content: unknown; defaultOpen?: boolean; badge?: string; onToggle?: (isOpen: boolean) => void }): unknown;
        ModalDialog(opts: { title: string; isOpen: boolean; size?: 'sm' | 'md' | 'lg'; content: unknown; actions?: unknown; onClose: () => void }): unknown;
        ActionBtn(opts: { label: string; variant?: 'primary' | 'danger' | 'ghost' | 'success'; icon?: string; disabled?: boolean; onClick: () => void }): unknown;
    };
    InspectorComponents?: {
        InspectorNodeHeader(opts: { nodeId: string; nodeType: string; name: string; color?: string; isGenerated?: boolean; onRename: (newName: string) => void; onSyncId: () => void; onClose?: () => void; actions?: unknown }): unknown;
        InspectorDangerZone(opts: { nodeId: string; nodeName: string; nodeType: string; onDelete: () => void }): unknown;
        HeaderComponent(opts: { title: string; subtitle?: string; nodeType?: string; color?: string; onClose?: () => void }): unknown;
        SectionComponent(opts: { title?: string; hint?: string; content: unknown }): unknown;
        PropertyGridComponent(opts: { fields: *FIX*[]; values: Record<string, unknown>; onChange: (key: string, value: unknown) => void; lockedFields?: string[] }): unknown;
        TabNavComponent(opts: { tabs: string[]; activeTab: string; onTabChange: (tab: string) => void }): unknown;
        ActionGridComponent(opts: { actions: string[]; onAction: (action: string) => void; locked?: string[] }): unknown;
        BreadcrumbComponent(opts: { onBack?: () => void; onCrumbClick?: (index: number) => void }): unknown;
    };
}





