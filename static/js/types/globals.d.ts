/**
 * Ambient globals for the classic-script front end.
 *
 * The app loads plain `<script>` tags and shares state through globals rather
 * than ES module imports, so cross-file symbols are declared here as files are
 * migrated. Prefer a precise shape for a global's used surface over `any`;
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
    // TS2339 at a time. `any` because these come from storage and their
    // shapes differ per key; the index signature already allowed them, so
    // this documents them instead of widening anything.
    background_all?: any;
    decay_overrides?: any;
    embed?: any;
    engine_decay?: any;
    fields?: any;
    graphArrows?: any;
    graphCardinalLayout?: any;
    graphDamping?: any;
    graphEdgeWidth?: any;
    graphGravitationalConstant?: any;
    graphImprovedLayout?: any;
    graphItemEdgeLength?: any;
    graphLabelMaxNodes?: any;
    graphLabelMinScale?: any;
    graphLayoutMode?: any;
    graphMapSpacing?: any;
    graphMapSpacingAuto?: any;
    graphRepelEnabled?: any;
    graphRepelMax?: any;
    graphRepelMin?: any;
    graphRepelPull?: any;
    graphSolver?: any;
    graphSpringConstant?: any;
    graphSpringLength?: any;
    js?: any;
    lastActionResult?: any;
    lastProfile?: any;
    manualMode?: any;
    mature?: any;
    maxSteps?: any;
    minutes_per_tick?: any;
    neutral_environment?: any;
    provider?: any;
    reactiveMode?: any;
    running?: any;
    saveFromForm?: any;
    scenario?: any;
    sections?: any;
    seed?: any;
    showLogs?: any;
    showRawLLM?: any;
    simultaneousMode?: any;
    starting_vitals?: any;
    stepsRun?: any;
    streaming?: any;
    structuredOutput?: any;
    suppressLocalThinking?: any;
    temperature?: any;
    ticks?: any;
    toLLMConfig?: any;
    traits?: any;
    turnBased?: any;
    turnOrder?: any;
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

/** Remaining shared globals — narrowed as their modules are converted. */
declare const worldState: any;
declare const events: any;
declare const api: any;
declare const graphManager: any;
declare const llmClient: any;
declare const storage: any;
declare const VW: any;
declare const TurnFeed: any;
declare const PromptBuilder: any;

/** ApiClient (api.js): the HTTP surface. Only the calls converted code makes. */
declare const ApiClient: {
    saveGraphBackground(background: unknown): Promise<unknown>;
    uploadBackgroundImage(file: File): Promise<{ image?: string } | null>;
    batchGraph(ops: unknown[]): Promise<{ errors?: unknown[] } | null>;
    getWorldGrid(scopeId: string): Promise<unknown>;
    getWorldScopes(flat?: boolean): Promise<unknown>;
    setScopeOffset(scopeId: string, offset?: { x?: number; y?: number; reset?: boolean }): Promise<unknown>;
    updateCharacter(name: string, changes: unknown): Promise<unknown>;
    updateNode(nodeId: string, data: unknown): Promise<unknown>;
    duplicateNode(nodeId: string): Promise<unknown>;
};

/** AppEventBus singleton (event-bus.js): `state:updated` and friends. */
declare const appEvents: {
    on(event: string, handler: (...args: unknown[]) => void): void;
    off?(event: string, handler: (...args: unknown[]) => void): void;
};

/**
 * window.Lit — the vendored lit-html 3.2.1 surface, stamped by
 * `shared/lit-bootstrap.js`.
 *
 * W0 of docs/design/typescript-migration-plan.md: `window.Lit` gates 46 files
 * and ~29,800 lines, so it is declared here rather than per-call. The vendored
 * bundle under `static/js/vendor/lit-html/` ships zero `.d.ts` and is excluded
 * from tsconfig, so tsc cannot infer it. This is the hand-declared option the
 * plan lists as the fallback when adding a dependency is unacceptable; the
 * alternative is `npm i -D lit@3.2.1` plus a `paths` entry.
 *
 * Exactly 14 members, enumerable from lit-bootstrap.js — not a guess from call
 * sites. Template *values* are `unknown` because these templates are dynamic by
 * design and lit accepts anything at runtime; the directive arguments are
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
 * surface converted callers use, not a bare `any`, so soak-app.js type-checks
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
    // Both are declared as bare `any` above (9 such globals exist); mirroring
    // that on Window is what makes the `window.worldState?.…` spelling — used
    // throughout the views — type-check at all.
    worldState: any;
    VW: any;
    // The prompt-builder modules build this namespace with Object.assign.
    PromptBuilder: any;
}

/**
 * Provisional declarations for singletons owned by modules that are still .js.
 *
 * These exist so parallel conversion lanes never have to edit this file — it is
 * a hub, and concurrent edits lose declarations. Each is `any` on purpose and
 * honestly: the real shape belongs to the owning module, and should replace
 * these when that module converts. The plan doc's warning applies — a file that
 * compiles against `any` here is typed only as far as its own logic.
 *
 * Format: name — owning module.
 */
declare const InspectorHelpers: any;   // inspector/helpers.js
declare const GraphToolbar: any;       // graph/toolbar.js
declare const DiffModal: any;          // shared/diff-modal.js
declare const WayAuthoring: any;       // inspector/way-authoring.js
declare const EmbeddingClient: any;    // shared/embedding-client.js (converted; narrow when convenient)
declare const GraphProjector: any;     // graph/projector.js
declare const GraphEventHandlers: any; // graph/event-handlers.js
declare const NodeBadges: any;         // graph/node-badges.js
declare const ActionNormalizer: any;   // agent/action-normalizer.js
declare const TurnQueue: any;          // agent/turn-queue.js
declare const GraphContextMenu: any;   // graph/context-menu.js
declare const InspectorAgentView: any; // inspector/agent-view.js
declare const WorldExport: any;        // ui/world-export.js
declare const GraphFocus: any;         // graph/focus.js
declare const GraphOverlays: any;      // graph/overlays.js
declare const GraphTooltips: any;      // graph/tooltips.js
declare const HumanTurnComposer: any;  // agent/human-turn-composer.js
declare const PlanTracker: any;        // agent/plan-tracker.js
declare const ResponseParser: any;     // agent/response-parser.js
declare const TriggerSuggestAI: any;   // shared/trigger-suggest-ai.js
declare const InspectorTriggers: any;  // inspector/trigger-helpers.js
declare const InspectorWayView: any;   // inspector/way-view.js
declare const ValidatorPanel: any;     // validator-panel.js
declare const ItemLibraryAI: any;      // item-library/ai-generation.js
declare const SkyScape: any;           // sky-scape.js
declare const Structures: any;         // structures.js
declare const NarrationUi: any;        // narration-ui.js
/**
 * GraphBackground (graph/graph-background.ts) — the map art behind the graph.
 *
 * **Not `any`, on purpose.** This one was `any`, and `any` is why commit
 * 6fd774b8 could delete `refreshForScope`, `reconcileAllForGapChange` and
 * `_reconcileReferenceArt` without `tsc` noticing: every cross-module call was
 * unchecked, and the four call sites guarded each one with
 * `typeof … === 'function'`, so a *deleted function* looked exactly like a
 * module that had not loaded yet. Scope switches and map-pitch changes stopped
 * re-deriving the art and nothing said so.
 *
 * Only the members other modules actually call are declared, and every one is
 * **required** — the modules are separate `<script>` tags but they are always
 * loaded together, and all four call sites run long after load, so "the method
 * might not exist" is not a real state here. Adding a member to graph-background
 * and calling it from elsewhere means adding it here too; removing one is now a
 * compile error instead of a silent no-op.
 *
 * `tools/unit/test_graph_background.js` pins the same surface at runtime and
 * fails if anyone reintroduces a `typeof … === 'function'` guard at a call site.
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
declare const InspectorPanelRef: any;  // inspector/panel.ts (converted)

/** lit-html's template type. Our LitApi types template *values* as unknown. */
type TemplateResult = unknown;

/** Vendored / CDN globals that are not modules. */
declare const tippy: any;              // tooltip library
declare const vis: any;                // vis-network, canvas-rendered

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
// Generated by tools/window_members.py — do not hand-edit.
//
// Only names a module assigns via `window.X =` belong here: that is what
// makes `window.X` a real, undefined-safe property access. Names that are
// lexical top-level `const` are deliberately absent, because `window.X`
// would typecheck for them while being `undefined` at runtime.
//
// WHY `any` AND NOT `unknown`: the whole point of this interface is to make
// `window.config.maxTokens` COMPILE. With `unknown` every property access
// through a window member errors, the converter is tempted to drop the
// `window.` prefix again, and we are back to ReferenceError land. `any`
// keeps the guard intact. Behaviour-correctness beats strictness here: the
// alternative is code that compiles and throws.
//
// Narrow the ones that matter by hand — config, appEvents, ApiClient, Lit —
// and leave the rest until their owning module earns a real shape.
//
// Sources: 123 names assigned to window across static/js.
interface Window {
    ActionNormalizer: any;
    AgentMemory: any;
    AgentState: any;
    AutoDressModal: any;
    ChangesPanel: any;
    BugReport: any;
    CharacterArt: any;
    CommandPalette: any;
    ContextWindowManager: any;
    DatasetCollector: any;
    DiffModal: any;
    DocPanel: any;
    EdgeInspector: any;
    EdgeTypes: any;
    EditFeed: any;
    EmbeddingClient: any;
    EmotePicker: any;
    EmotionMapper: any;
    EngineConfigView: any;
    EnvPresets: any;
    GraphBackground: any;
    GraphContextMenu: any;
    GraphEventHandlers: any;
    GraphExport: any;
    GraphFocus: any;
    GraphNetwork: any;
    GraphNodeOps: any;
    GraphOverlays: any;
    GraphProjector: any;
    GraphRelativeLayout: any;
    GraphScopeTree: any;
    GraphSeparation: any;
    GraphToolbar: any;
    GraphTooltips: any;
    GraphTreeView: any;
    HelpCenter: any;
    HumanTurnComposer: any;
    InspectorAgentView: any;
    InspectorBehaviors: any;
    InspectorHelpers: any;
    InspectorItemView: any;
    InspectorLore: any;
    InspectorMemory: any;
    InspectorPanel: any;
    InspectorPaperdoll: any;
    InspectorTemplateSync: any;
    InspectorTriggers: any;
    InspectorWayView: any;
    InspectorWayViewConnections: any;
    Involuntary: any;
    ItemContainment: any;
    ItemLibraryAI: any;
    ItemLibraryContents: any;
    ItemLibraryPlacement: any;
    ItemLibraryTriggerSuggester: any;
    KnownBySection: any;
    NLEditor: any;
    NLEditorAgent: any;
    NLEditorDiff: any;
    NLEditorGhosts: any;
    NLEditorStaging: any;
    NLEditorTools: any;
    NLEditorUI: any;
    NodeBadges: any;
    ObjectResponder: any;
    PlanManager: any;
    PlanTracker: any;
    RateLimiter: any;
    ResponseParser: any;
    RoomTemplatePalette: any;
    SaveLoadView: any;
    ScenarioHealth: any;
    ScenarioManager: any;
    ScenarioStatus: any;
    ScenarioWizard: any;
    SearchSelect: any;
    SettingsView: any;
    SetupChecklist: any;
    SkyScape: any;
    SoakApi: any;
    SoakCharts: any;
    SoakFormat: any;
    SoakPresets: any;
    SoakSpacetime: any;
    SpriteSheet: any;
    SpriteSheetGeometry: any;
    StructuredFormats: any;
    TagMultiselect: any;
    ThreatDetector: any;
    Timeskip: any;
    TriggerGraph: any;
    TriggerSuggestAI: any;
    TriggerSuggestDiff: any;
    TriggerTypes: any;
    TurnFeed: any;
    TurnQueue: any;
    TurnSceneView: any;
    TurnYouStrip: any;
    UndoHistory: any;
    VWSimRound: any;
    VWSimultaneous: any;
    VitalColor: any;
    VitalThresholds: any;
    WayAuthoring: any;
    WorldExport: any;
    _lastRecallStats: any;
    _traitLibrary: any;
    _traitLibraryAt: any;
    appEvents: any;
    config: any;
    escapeForHtmlAttribute: any;
    events: any;
    graphManager: any;
    gridModel: any;
    llmClient: any;
    runAction: any;
    storage: any;
    structures: any;
    worldPainter: any;
}
// <<< window members <<<

// >>> hoisted from converted modules - generated, do not hand-edit >>>
// CreateModal — owner: main.ts
declare const CreateModal: any;       // ui/create-modal.js

// DatasetCollector — owner: llm-client.ts
declare const DatasetCollector: { capture(messages: unknown, content: unknown, label: string, extra?: unknown): void } | undefined;

// EmotePicker — owner: agent/human-turn-composer.ts
declare const EmotePicker: {
    toggle(wrap: HTMLElement, opts: { onPick(emote: string): void }): void;
    close(wrap: HTMLElement): void;
};

// GraphNetwork — owner: graph/event-handlers.ts
// owner: static/js/graph/network-manager.js
declare const GraphNetwork: {
    _applyCardinalOverlay(...args: any[]): any;
    _applyHeatOverlay(...args: any[]): any;
    _applyLightOverlay(...args: any[]): any;
    _applyNodeLabelDecorations(...args: any[]): any;
    _applySoundOverlay(...args: any[]): any;
    _applyTagIconsToLabels(...args: any[]): any;
    _applyTriggerOverlay(...args: any[]): any;
    _attachTippyTooltips(...args: any[]): any;
    _bindEdgeHoverTooltips(...args: any[]): any;
    _captureBaseStyles(...args: any[]): any;
    _clearOverlay(...args: any[]): any;
    _computeAmbientLight(...args: any[]): any;
    _computeVisibleNodeIds(...args: any[]): any;
    _escHtml(...args: any[]): any;
    _findGraphEdge(...args: any[]): any;
    _fitToSearchMatches(...args: any[]): any;
    _heatColors(...args: any[]): any;
    _kickClusterPhysics(...args: any[]): any;
    _lightColors(...args: any[]): any;
    _lightToInt(...args: any[]): any;
    _nodeLabelPolicy(...args: any[]): any;
    _noiseColors(...args: any[]): any;
    _syncLayoutButton(...args: any[]): any;
    _tagMetaFor(...args: any[]): any;
    _updateOverlayLegend(...args: any[]): any;
    applyAutoMapSpacing(...args: any[]): any;
    applyFilter(...args: any[]): any;
    applyGraphSettings(...args: any[]): any;
    applyModePhysics(...args: any[]): any;
    applyNodeLabelVisibility(...args: any[]): any;
    applyOverlay(...args: any[]): any;
    applyTagFilter(...args: any[]): any;
    applyVisibility(...args: any[]): any;
    buildLegendHTML(...args: any[]): any;
    buildLegendRows(...args: any[]): any;
    buildNodeConfig(...args: any[]): any;
    buildOptions(...args: any[]): any;
    buildTooltip(...args: any[]): any;
    buildTooltipHtml(...args: any[]): any;
    centralGravityFor(...args: any[]): any;
    ensureTagLibrary(...args: any[]): any;
    filterNodes(...args: any[]): any;
    fitView(...args: any[]): any;
    hideRevealedAreas(...args: any[]): any;
    hideRevealedItems(...args: any[]): any;
    init(...args: any[]): any;
    legendChrome(...args: any[]): any;
    loadGraphData(...args: any[]): any;
    mapCompact(...args: any[]): any;
    mapSizeScale(...args: any[]): any;
    nodeSizeScale(...args: any[]): any;
    refreshEdgeLengths(...args: any[]): any;
    _lastArrangement: string;
    renderTagPanel(...args: any[]): any;
    resetOverlayStyles(...args: any[]): any;
    revealAreasForWay(...args: any[]): any;
    revealItemsForNode(...args: any[]): any;
    setTagFilter(...args: any[]): any;
    settleSearch(...args: any[]): any;
    toggleImages(...args: any[]): any;
    toggleInhabitedAreas(...args: any[]): any;
    toggleItems(...args: any[]): any;
    toggleLayoutMode(...args: any[]): any;
    toggleLegend(...args: any[]): any;
    togglePhysics(...args: any[]): any;
    toggleTagPanel(...args: any[]): any;
    toggleTriggers(...args: any[]): any;
};

// GraphTreeView — owner: ui-controller.ts
declare const GraphTreeView: { renderOutlinePanel(target: Element | null): void };

// ItemLibraryContents — owner: item-library.ts
declare const ItemLibraryContents: {
    renderContentsSection(this: ItemLibrary, contents: unknown): unknown;
    removeContent(this: ItemLibrary, idx: unknown): unknown;
    addContentUi(this: ItemLibrary): unknown;
    saveContent(this: ItemLibrary, btn: unknown): unknown;
};

// NLEditorGhosts — owner: nl-editor/index.ts
declare const NLEditorGhosts: any;

// NLEditorStaging — owner: nl-editor/index.ts
declare const NLEditorStaging: any;

// NLEditorTools — owner: nl-editor/index.ts
declare const NLEditorTools: any;

// NLEditorUI — owner: nl-editor/index.ts
declare const NLEditorUI: any;

// SaveLoadView — owner: main.ts
declare const SaveLoadView: any;       // ui/save-load-view.js

// TriggerEditor — owner: item-library.ts
declare const TriggerEditor: {
    _renderConditionSummary(conditions: unknown): string[];
    show(...args: unknown[]): unknown;
};

// TriggerGraph — owner: item-library.ts
declare const TriggerGraph: {
    triggerToGraph(triggerData: unknown): unknown;
    show(...args: unknown[]): unknown;
    compileToEngine(graph: unknown): Record<string, any> | null;
    reportCompileError(compiled: unknown): boolean;
    engineToFormData(compiled: unknown): Record<string, any>;
    triggersFromGraphEdges(...args: unknown[]): unknown[];
};

// agent — owner: ui-controller.ts
declare const agent: any;              // VW.agent, the turn-queue owner (agent/turn-queue.js)

// durabilityChip — owner: inspector/paperdoll-view.ts
declare const durabilityChip: (props: unknown) => string;

// hideInspectorPanel — owner: graph/edge-inspector.ts
declare function hideInspectorPanel(): void;

// inspector — owner: main.ts
declare const inspector: any;         // inspector/inspector.js

// runAction — owner: inspector/agent-view.ts
declare function runAction(command: string, charName: string): void;

// selectAgent — owner: ui-controller.ts
declare function selectAgent(name: string): void;

// viewerExitMap — owner: agent/prompt-builder/room-context.ts
declare const viewerExitMap: Record<string, ExitEntry>;

// >>> ambient shapes for still-unconverted .js modules >>>
// owner: static/js/item-library/placement.js
declare const ItemLibraryPlacement: {
    pickTarget(...args: any[]): any;
    // The generator stopped after pickTarget: a multi-line template literal
    // inside it desynchronised the brace-depth walk, so the three members
    // defined later in the same literal were not seen. Added by hand from
    // item-library/placement.js:134, :160, :202. They are `this`-bound and
    // item-library.ts calls them via .call(this), hence the loose signatures.
    placeInRoom(...args: any[]): any;
    placeSelectedInRoom(...args: any[]): any;
    updatePlaceButton(...args: any[]): any;
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
 * `any` rather than inferred shapes on purpose: `unknown` rejects every
 * property access, which just moves the error to each reader.
 *
 * Disappears when graph-manager.js converts.
 */
interface GraphManager {
    _bulkBar: any;
    _bulkScopesFilled: boolean;
    _bulkSelection: any;
    _cardinalLayout: any;
    _contextTarget: any;
    _edgeLabelSize: number;
    _floorFilter: string;
    _floorOptions: any;
    _labelCache: any;
    _lastSig: string;
    _legendEl: any;
    _mapSpacingAuto: any;
    _nodeLabelsShown: any;
    _paintedGridLayout: boolean;
    _pendingConnection: any;
    _physicsEnabled: boolean;
    _revealedAreaIds: any;
    _revealedItemIds: any;
    _scopeFilter: any;
    _scopeOffsets: any;
    _scopeSummaries: any;
    _searchQuery: string;
    _showEdgeLabels: boolean;
    _showImages: any;
    _showItems: boolean;
    _showNodeLabels: any;
    _showOnlyInhabitedAreas: boolean;
    _viewMode: string;
    network: any;
    nodes: any;
}
