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
};

/** AppEventBus singleton (event-bus.js): `state:updated` and friends. */
declare const appEvents: {
    on(event: string, handler: (...args: unknown[]) => void): void;
    off?(event: string, handler: (...args: unknown[]) => void): void;
};

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
