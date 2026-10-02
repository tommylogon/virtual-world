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
