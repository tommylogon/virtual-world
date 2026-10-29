import re

p = 'static/js/commons/commons-agent.ts'
txt = open(p, 'r', encoding='utf-8').read()

assert '\u2014' not in txt and '—' not in txt, "Em-dash in original commons-agent.ts"

# Header interface declarations
types_header = """
    interface ToolCall {
        id: string;
        type: 'function';
        function: { name: string; arguments: string | Record<string, unknown> };
    }

    interface ChatMessage {
        role: 'system' | 'user' | 'assistant' | 'tool';
        content?: string;
        tool_calls?: ToolCall[];
        tool_call_id?: string;
    }

    interface ToolOutcome {
        result: Record<string, unknown>;
        summary: string;
        readMessages: Array<Record<string, unknown>>;
    }

    interface TurnOutcome {
        didPost: boolean;
        player?: Record<string, unknown>;
    }

    interface CommonsParticipant {
        control_mode?: string;
        active?: boolean;
        blocked?: boolean;
        state?: string;
        [key: string]: unknown;
    }

    interface CommonsChannel {
        id: string;
        name?: string;
        kind?: string;
        members?: string[];
        [key: string]: unknown;
    }

    interface CommonsStateGlobal {
        isPaused: boolean;
        participants?: Record<string, CommonsParticipant>;
        channels?: CommonsChannel[];
        actingCharacter: string | null;
        characterContextCache: Record<string, unknown>;
        emit: () => void;
        receiveMessage: (msg: unknown) => void;
        recordTurn: (charName: string, turn: { inner: string; action: string; summary: string; detail?: unknown }) => void;
    }

    interface VWSimultaneousGlobal {
        TALKATIVENESS_DEFAULT_SECONDS?: number;
        TALKATIVENESS_MIN_SECONDS?: number;
        TALKATIVENESS_MAX_SECONDS?: number;
        normalizeTalkativeness: (val: unknown) => number;
        jitteredCooldownMs: (pace: number) => number;
    }

    interface CommonsApiGlobal {
        readMessages: (charName: string, channelId: string, mode: string, n?: number, fromId?: unknown, toId?: unknown, signal?: AbortSignal) => Promise<{ messages?: Array<Record<string, unknown>> }>;
        postMessage: (charName: string, text: string, channelId: string, signal?: AbortSignal) => Promise<Record<string, unknown>>;
        createChannel: (args: Record<string, unknown>, signal?: AbortSignal) => Promise<{ channel?: { id?: string } }>;
        storeMemory: (charName: string, text: string, importance: number, tags: string[], signal?: AbortSignal) => Promise<unknown>;
        getCharacterContext: (charName: string, signal?: AbortSignal) => Promise<Record<string, unknown>>;
        retrieveMemories: (charName: string, query: string, signal?: AbortSignal) => Promise<{ memories?: Array<{ text?: string }> }>;
        getState: (charName: string) => Promise<{ channels?: CommonsChannel[]; theme?: string; known_characters?: string[] }>;
    }

    interface LLMClientGlobal {
        chatWithTools: (messages: ChatMessage[], opts: Record<string, unknown>) => Promise<{ content?: string; tool_calls?: ToolCall[] } | null>;
    }

    interface PromptBuilderGlobal {
        buildCommunicationPrompt: (player: unknown, memoryText: string, channels: unknown[], knownCharacters: string[], theme: string) => string;
    }

    interface ConfigGlobal {
        talkativenessByCharacter?: Record<string, number>;
        getTalkativeness?: (name: string) => number;
        setTalkativeness?: (name: string, pace: number) => Promise<void>;
    }

    interface CommonsAgentWindow extends Window {
        config?: ConfigGlobal;
        VWSimultaneous?: VWSimultaneousGlobal;
        CommonsState: CommonsStateGlobal;
        CommonsApi: CommonsApiGlobal;
        llmClient?: LLMClientGlobal;
        PromptBuilder?: PromptBuilderGlobal;
        CommonsAgent: typeof CommonsAgent;
    }

    const getWin = () => window as unknown as CommonsAgentWindow;
"""

# Insert types after 'use strict';
txt = txt.replace("'use strict';", "'use strict';\n" + types_header)

replacements = [
    ("(window as *FIX*).config", "getWin().config"),
    ("(window as *FIX*).VWSimultaneous", "getWin().VWSimultaneous"),
    ("(window as *FIX*).CommonsState", "getWin().CommonsState"),
    ("(window as *FIX*).CommonsApi", "getWin().CommonsApi"),
    ("(window as *FIX*).llmClient", "getWin().llmClient"),
    ("(window as *FIX*).PromptBuilder", "getWin().PromptBuilder"),
    ("(window as *FIX*).CommonsAgent = CommonsAgent;", "(window as unknown as { CommonsAgent: typeof CommonsAgent }).CommonsAgent = CommonsAgent;"),
    ("let turnOutcome: *FIX* = false;", "let turnOutcome: TurnOutcome | boolean | void = false;"),
    ("static handlePostTurnCadence(charName: string, turnOutcome: *FIX*) {", "static handlePostTurnCadence(charName: string, turnOutcome: TurnOutcome | boolean | void) {"),
    ("static onMessageReceived(message: *FIX*) {", "static onMessageReceived(message: { author?: string; channel_id?: string; text?: string; [key: string]: unknown }) {"),
    ("(state?.channels || []).find((c: *FIX*) => c.id === channelId);", "(state?.channels || []).find((c: CommonsChannel) => c.id === channelId);"),
    ("static communicationTools(theme: string): *FIX*[] {", "static communicationTools(theme: string): Array<Record<string, unknown>> {"),
    ("const tools: *FIX*[] = [", "const tools: Array<Record<string, unknown>> = ["),
    ("charName: string, call: *FIX*, channels: *FIX*[], knownCharacters: string[], theme: string, api: *FIX*, signal: AbortSignal\n        ): Promise<{ result: *FIX*; summary: string; readMessages: *FIX*[] }> {",
     "charName: string, call: ToolCall, channels: CommonsChannel[], knownCharacters: string[], theme: string, api: CommonsApiGlobal, signal: AbortSignal\n        ): Promise<ToolOutcome> {"),
    ("let args: *FIX*;", "let args: Record<string, unknown>;"),
    ("messages.slice(-20).map((message: *FIX*) => ({ id: message.id, author: message.author, text: String(message.text || '').slice(0, 1000) }))",
     "messages.slice(-20).map((message: Record<string, unknown>) => ({ id: message.id, author: message.author, text: String(message.text || '').slice(0, 1000) }))"),
    ("} catch (error: *FIX*) {", "} catch (error: unknown) {"),
    (".map((memory: *FIX*) => String(memory.text || '').trim())", ".map((memory: { text?: string }) => String(memory.text || '').trim())"),
    ("const messages: *FIX*[] = [", "const messages: ChatMessage[] = ["),
    ("const readMessages: *FIX*[] = [];", "const readMessages: Array<Record<string, unknown>> = [];"),
    ("let outcome: *FIX*;", "let outcome: ToolOutcome;"),
    ("const summary = readMessages.slice(-4).map((message: *FIX*) =>", "const summary = readMessages.slice(-4).map((message: Record<string, unknown>) =>"),
    ("String((error as Error)?.message || error)", "String((error as Error)?.message || error)"),
]

for src, dst in replacements:
    if src in txt:
        txt = txt.replace(src, dst)
    else:
        print(f"FAILED TO FIND:\n{src[:80]}...")

txt = txt.replace("String(error?.message || error)", "String((error as Error)?.message || error)")

rem = txt.count('*FIX*')
print(f"Remaining in commons-agent.ts: {rem}")
assert rem == 0, f"Remaining markers in commons-agent.ts: {rem}"
assert '\u2014' not in txt and '—' not in txt, "Em-dash in commons-agent.ts"
open(p, 'w', encoding='utf-8', newline='').write(txt)
print("commons-agent.ts 100% clean!")
