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
