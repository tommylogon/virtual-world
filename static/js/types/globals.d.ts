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
declare const GraphBackground: any;    // graph/graph-background.ts (converted)
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
declare const GraphNetwork: {
    revealItemsForNode(nodeId: string): void;
    revealAreasForWay(nodeId: string): void;
    hideRevealedItems(): void;
    hideRevealedAreas(): void;
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
