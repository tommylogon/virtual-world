/**
 * Typed domain model interfaces for graph nodes and entities.
 *
 * All physical world objects (items, areas, ways, characters) are nodes
 * in the WorldGraph. Non-physical entities (knowledge, recipes, memories)
 * are stored on properties or dedicated stores, never as nodes.
 */

/**
 * Base graph node model representing *FIX* node in WorldGraph.
 */
export interface BaseNodeModel<TProps extends Record<string, unknown> = Record<string, unknown>> {
    id: string;
    type: string;
    name: string;
    properties: TProps;
    created?: number;
    updated?: number;
    [key: string]: unknown;
}

/**
 * Authored and runtime properties for item nodes.
 */
export interface ItemProperties {
    weight?: number;
    uses?: number;
    equip_slot?: string;
    consumable?: boolean;
    quantity?: number;
    tags?: string[];
    traits?: Record<string, unknown> | string[];
    description?: string;
    current_state?: string;
    actions?: string | string[];
    action_costs?: Record<string, unknown>;
    skill_check?: Record<string, unknown>;
    [key: string]: unknown;
}

/**
 * Item node model extending BaseNodeModel with typed item properties.
 */
export interface ItemModel extends BaseNodeModel<ItemProperties> {
    type: 'item' | string;
    properties: ItemProperties;
    weight?: number;
    uses?: number;
    equip_slot?: string;
    consumable?: boolean;
    quantity?: number;
    tags?: string[];
    traits?: Record<string, unknown> | string[];
    description?: string;
}

/**
 * Authored and runtime properties for area nodes.
 */
export interface AreaProperties {
    environment?: string;
    description?: string;
    statuses?: string[];
    light_level?: number | string;
    temperature?: number;
    grid_x?: number;
    grid_y?: number;
    scope?: string;
    indoor?: boolean;
    climate?: string;
    [key: string]: unknown;
}

/**
 * Area node model extending BaseNodeModel with typed area properties.
 */
export interface AreaModel extends BaseNodeModel<AreaProperties> {
    type: 'area' | string;
    properties: AreaProperties;
    environment?: string;
    description?: string;
    statuses?: string[];
    light_level?: number | string;
    temperature?: number;
    grid_x?: number;
    grid_y?: number;
    scope?: string;
}

/**
 * Authored and runtime properties for way nodes.
 */
export interface WayProperties {
    open?: boolean;
    locked?: boolean;
    key_id?: string;
    direction?: string;
    two_way?: boolean;
    prevent_close?: boolean;
    requires?: string;
    current_state?: string;
    one_way?: boolean;
    auto_close?: boolean;
    refusal_message?: string;
    pass_message?: string;
    blocked_description?: string;
    [key: string]: unknown;
}

/**
 * Way node model extending BaseNodeModel with typed way properties.
 */
export interface WayModel extends BaseNodeModel<WayProperties> {
    type: 'way' | 'door' | string;
    properties: WayProperties;
    open?: boolean;
    locked?: boolean;
    key_id?: string;
    direction?: string;
    two_way?: boolean;
    prevent_close?: boolean;
    requires?: string;
}

/**
 * Authored physical properties for character nodes.
 * Authored definition lives on the character node's properties;
 * runtime state belongs to PlayerRuntimeModel.
 */
export interface CharacterNodeProperties {
    base_description?: string;
    description?: string;
    personality?: string;
    tags?: string[];
    traits?: Record<string, unknown> | string[];
    species?: string;
    size?: string;
    gender?: string;
    avatar?: string;
    image?: string;
    unknown_name?: string;
    current_area?: string;
    carcass_item?: string;
    fear_tags?: string[];
    interest_tags?: string[];
    [key: string]: unknown;
}

/**
 * Character node model extending BaseNodeModel with authored physical properties.
 */
export interface CharacterNodeModel extends BaseNodeModel<CharacterNodeProperties> {
    type: 'character' | string;
    properties: CharacterNodeProperties;
    base_description?: string;
    description?: string;
    personality?: string;
    tags?: string[];
    traits?: Record<string, unknown> | string[];
    species?: string;
    size?: string;
    [key: string]: unknown;
}

/**
 * Trigger effect specification.
 */
export interface TriggerEffect {
    type: string;
    params?: Record<string, unknown>;
    target?: string;
    value?: unknown;
    [key: string]: unknown;
}

/**
 * Trigger condition specification.
 */
export interface TriggerCondition {
    type?: string;
    param?: string;
    operator?: string;
    value?: unknown;
    conditions?: TriggerCondition[];
    logic?: 'AND' | 'OR' | string;
    [key: string]: unknown;
}

/**
 * Logic trigger model defining triggers attached to nodes or edges.
 */
export interface TriggerModel {
    id?: string;
    name?: string;
    trigger_type: string | string[];
    conditions?: TriggerCondition[] | { conditions?: TriggerCondition[]; logic?: string } | unknown[];
    conditions_logic?: 'AND' | 'OR' | string;
    effects: TriggerEffect[];
    success_message?: string;
    fail_message?: string;
    cooldown?: number;
    enabled?: boolean;
    [key: string]: unknown;
}
