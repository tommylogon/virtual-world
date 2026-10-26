/**
 * Typed domain model interfaces for player runtime state, memory, and goals.
 *
 * Runtime state (vitals, memories, emotion, plan, perception, behavioral tags/traits)
 * belongs to the Player model.
 */

/**
 * Memory record stored on a character player model.
 */
export interface MemoryRecord {
    id: string;
    text: string;
    timestamp?: number;
    subject_node_id?: string | null;
    novelty?: number;
    valence?: number;
    tick?: number;
    importance?: number;
    type?: string;
    tags?: string[];
    source?: string;
    location?: string;
    reinforcements?: number;
    reflection_depth?: number;
    [key: string]: unknown;
}

/**
 * Goal status lifecycle: active, completed, or abandoned.
 */
export type GoalStatus = 'active' | 'completed' | 'abandoned';

/**
 * Character-private goal model.
 */
export interface GoalModel {
    id: string;
    what: string;
    status: 'active' | 'completed' | 'abandoned';
    motivation?: string;
    intention?: string;
    tick?: number;
    [key: string]: unknown;
}

/**
 * Character obligation model (promises, contracts, tasks from others).
 */
export interface ObligationModel {
    id: string;
    from?: string;
    due?: number;
    reward?: string;
    goal_id?: string;
    charge?: string;
    status?: string;
    [key: string]: unknown;
}

/**
 * Executable plan step in a pursuit approach.
 */
export interface PlanStep {
    kind?: string;
    action?: string;
    target?: string;
    description?: string;
    completed?: boolean;
    [key: string]: unknown;
}

/**
 * Authored or derived multi-step plan model.
 */
export interface PlanModel {
    pursuit_template?: string;
    template_id?: string;
    current_step_index?: number;
    index?: number;
    steps: Array<PlanStep | string | unknown>;
    label?: string;
    reason?: string;
    purpose?: string;
    assignment_id?: string;
    bindings?: Record<string, unknown>;
    [key: string]: unknown;
}

/**
 * Active pursuit assigned to or chosen by a character.
 */
export interface ActivePursuitModel {
    template_id?: string;
    label?: string;
    reason?: string;
    assignment_id?: string;
    bindings?: Record<string, unknown>;
    progress?: number;
    plan?: PlanModel | null;
    [key: string]: unknown;
}

/**
 * Character vital meters and drive levels.
 */
export interface PlayerVitals {
    HP?: number;
    Max_HP?: number;
    Hunger?: number;
    Thirst?: number;
    Hygiene?: number;
    Energy?: number;
    Social?: number;
    Bladder?: number;
    Sanity?: number;
    Entertainment?: number;
    Temperature?: number;
    Mana?: number;
    Arousal?: number;
    Stimulation?: number;
    Pleasure?: number;
    [key: string]: number | undefined;
}

/**
 * Core character statistics.
 */
export interface PlayerStats {
    STR?: number;
    DEX?: number;
    CON?: number;
    INT?: number;
    WIS?: number;
    CHA?: number;
    [key: string]: number | undefined;
}

/**
 * Active condition instance on a character.
 */
export interface ConditionInstance {
    duration?: number | null;
    source?: string | null;
    level?: number;
    periodic?: boolean;
    ends_on?: string;
    symptoms?: string[];
    known?: boolean;
    [key: string]: unknown;
}

/**
 * Player runtime model representing active character simulation state.
 */
export interface PlayerRuntimeModel {
    id: string;
    name: string;
    node_id: string;
    vitals: PlayerVitals;
    stats: PlayerStats;
    personality_dials: Record<string, number>;
    goals: GoalModel[];
    memories: MemoryRecord[];
    conditions: Record<string, ConditionInstance[]> | string[];
    active_pursuit?: ActivePursuitModel | null;
    plan?: PlanModel | null;
    obligations?: ObligationModel[];
    skills?: Record<string, number>;
    traits?: Record<string, unknown>;
    tags?: string[];
    current_area?: string | null;
    autonomy?: boolean;
    [key: string]: unknown;
}
