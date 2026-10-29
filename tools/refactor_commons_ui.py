import re

p = 'static/js/commons/commons-ui.ts'
txt = open(p, 'r', encoding='utf-8').read()

assert '\u2014' not in txt and '—' not in txt, "Em-dash in original commons-ui.ts"

types_header = """
    interface CommonsUIWindow extends Window {
        CommonsState: {
            perspective: string;
            selectedChannelId: string;
            theme: string;
            messages: Array<{ id: string | number; author: string; timestamp: number; text: string }>;
            channels: Array<{ id: string; name?: string; kind?: string; unread_count?: number; members?: string[]; created_by?: string }>;
            participants: Record<string, { active?: boolean; blocked?: boolean; control_mode?: string }>;
            knownCharacters: string[];
            selectedDrawerCharacter: string | null;
            characterTurns?: Record<string, Array<{ inner: string; action: string; summary: string; timestamp: number; detail?: { text?: string } }>>;
            characterContextCache?: Record<string, { personality?: string; description?: string; traits?: Record<string, boolean> }>;
            selectPerspective: (name: string) => Promise<void>;
            selectChannel: (id: string, explicitRead?: boolean) => Promise<void>;
            setPaused: (paused: boolean) => void;
            isPaused: boolean;
            closeDrawer: () => void;
            openDrawer: (charName: string) => void;
            subscribe: (fn: () => void) => void;
            sync: () => Promise<void>;
        };
        CommonsApi: {
            postMessage: (charName: string, text: string, channelId: string) => Promise<unknown>;
            createChannel: (args: Record<string, unknown>) => Promise<{ channel: { id: string } }>;
            updateMembers: (creator: string, channelId: string, members: string[]) => Promise<unknown>;
            updateParticipant: (name: string, active: boolean, blocked: boolean) => Promise<unknown>;
            getCharacterContext?: (charName: string) => Promise<{ personality?: string; description?: string; traits?: Record<string, boolean> }>;
        };
        CommonsAgent: {
            stepOne: (charName?: string) => Promise<void>;
            randomizeTalkativeness: (name: string, persist?: boolean) => number;
            setTalkativeness: (name: string, val: unknown, persist?: boolean) => void;
            getTalkativeness: (name: string) => number;
            resetTimer: (name: string) => void;
            controllers?: Record<string, AbortController>;
        };
        Lit: typeof window.Lit;
        UiPrimitives: typeof window.UiPrimitives;
        CommonsUI: typeof CommonsUI;
    }

    const getWin = () => window as unknown as CommonsUIWindow;

    const renderMarkup = (htmlStr: string, container: HTMLElement | null) => {
        if (!container) return;
        if (window.Lit?.render && window.Lit?.unsafeHTML) {
            window.Lit.render(window.Lit.unsafeHTML(htmlStr), container);
        } else {
            const t = document.createElement('template');
            t.innerHTML = htmlStr;
            container.replaceChildren(t.content);
        }
    };
"""

txt = txt.replace("'use strict';", "'use strict';\n" + types_header)

# Restore English word
txt = txt.replace("*FIX*one can join", "anyone can join")

# Global window access replacements
txt = txt.replace("(window as *FIX*).CommonsState", "getWin().CommonsState")
txt = txt.replace("(window as *FIX*).CommonsApi", "getWin().CommonsApi")
txt = txt.replace("(window as *FIX*).CommonsAgent", "getWin().CommonsAgent")
txt = txt.replace("(window as *FIX*).Lit", "getWin().Lit")
txt = txt.replace("(window as *FIX*).UiPrimitives", "getWin().UiPrimitives")
txt = txt.replace("(window as *FIX*).CommonsUI = CommonsUI;", "(window as unknown as { CommonsUI: typeof CommonsUI }).CommonsUI = CommonsUI;")

# innerHTML replacements
txt = txt.replace(
    "select.*FIX*= names.map(name => `<option value=\"${escapeHtml(name)}\">${escapeHtml(name)}</option>`).join('');",
    "renderMarkup(names.map(name => `<option value=\"${escapeHtml(name)}\">${escapeHtml(name)}</option>`).join(''), select);"
)

txt = txt.replace(
    "list.*FIX*= channels.map((channel: *FIX*) => {",
    "const channelItems = channels.map((channel: { id: string; name?: string; kind?: string; unread_count?: number; members?: string[] }) => {"
)
# And replace the end of list render
txt = txt.replace(
    "                    <span class=\"commons-channel-preview\">${escapeHtml(people || channel.kind)}</span></span>\n                </button>`;\n            }).join('');",
    "                    <span class=\"commons-channel-preview\">${escapeHtml(people || channel.kind)}</span></span>\n                </button>`;\n            }).join('');\n            renderMarkup(channelItems, list);"
)

txt = txt.replace(
    "(item: *FIX*) => item.id === state.selectedChannelId",
    "(item: { id: string }) => item.id === state.selectedChannelId"
)

txt = txt.replace("if (membersList) membersList.*FIX*= '';", "if (membersList) membersList.replaceChildren();")
txt = txt.replace("if (editor) editor.*FIX*= '';", "if (editor) editor.replaceChildren();")

txt = txt.replace(
    """            if (membersList) {
                membersList.*FIX*= members.map((name: string, index: number) =>
                    `<span class="commons-member-chip commons-char-trigger" data-character="${escapeHtml(name)}" title="Inspect ${escapeHtml(name)} inner world"><span class="commons-member-avatar avatar-${index % 6}">${escapeHtml(initials(name))}</span>${escapeHtml(name)}</span>`
                ).join('') || '<div class="commons-empty-note">No members listed.</div>';
            }""",
    """            if (membersList) {
                const markup = members.map((name: string, index: number) =>
                    `<span class="commons-member-chip commons-char-trigger" data-character="${escapeHtml(name)}" title="Inspect ${escapeHtml(name)} inner world"><span class="commons-member-avatar avatar-${index % 6}">${escapeHtml(initials(name))}</span>${escapeHtml(name)}</span>`
                ).join('') || '<div class="commons-empty-note">No members listed.</div>';
                renderMarkup(markup, membersList);
            }"""
)

txt = txt.replace(
    "static renderMemberEditor(channel: *FIX*) {",
    "static renderMemberEditor(channel: { kind?: string; created_by?: string; members?: string[] }) {"
)

txt = txt.replace("editor.*FIX*= '';", "editor.replaceChildren();")

txt = txt.replace(
    """            editor.*FIX*= `<div class="commons-member-edit-title">Manage members</div>
                <div class="commons-member-add-row"><select id="commons-member-to-add" class="commons-select" ${available.length ? '' : 'disabled'}>
                    ${available.map((name: string) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join('')}
                </select><button type="button" class="commons-small-btn" data-member-action="add" ${available.length ? '' : 'disabled'}>Add</button></div>
                <div class="commons-member-remove-list">${channel.members.filter((name: string) => name !== channel.created_by).map((name: string) =>
                    `<button type="button" class="commons-remove-member" data-member-action="remove" data-name="${escapeHtml(name)}">Remove ${escapeHtml(name)}</button>`
                ).join('')}</div>`;""",
    """            renderMarkup(`<div class="commons-member-edit-title">Manage members</div>
                <div class="commons-member-add-row"><select id="commons-member-to-add" class="commons-select" ${available.length ? '' : 'disabled'}>
                    ${available.map((name: string) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join('')}
                </select><button type="button" class="commons-small-btn" data-member-action="add" ${available.length ? '' : 'disabled'}>Add</button></div>
                <div class="commons-member-remove-list">${(channel.members || []).filter((name: string) => name !== channel.created_by).map((name: string) =>
                    `<button type="button" class="commons-remove-member" data-member-action="remove" data-name="${escapeHtml(name)}">Remove ${escapeHtml(name)}</button>`
                ).join('')}</div>`, editor);"""
)

txt = txt.replace(
    """            feed.*FIX*= messages.map((message: *FIX*) => {
                const own = message.author === (window as *FIX*).CommonsState.perspective;
                const time = new Date(message.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                return `<article class="chat-msg ${own ? 'own' : ''}">
                    <div class="chat-msg-avatar avatar-${hash(message.author) % 6} commons-char-trigger" data-character="${escapeHtml(message.author)}" title="Inspect ${escapeHtml(message.author)} inner world">${escapeHtml(initials(message.author))}</div>
                    <div class="chat-msg-content"><div class="chat-msg-meta"><span class="chat-msg-author commons-char-trigger" data-character="${escapeHtml(message.author)}" title="Inspect ${escapeHtml(message.author)} inner world">${escapeHtml(message.author)}</span><time>${time}</time></div>
                    <div class="chat-msg-text">${escapeHtml(message.text)}</div></div>
                </article>`;
            }).join('') || ((window as *FIX*).CommonsState.theme === 'town_board'
                ? `<div class="commons-feed-empty"><div class="commons-empty-orb">✳</div><h3>It starts here</h3><p>Leave a notice or write a private letter.</p></div>`
                : `<div class="commons-feed-empty"><div class="commons-empty-orb">✳</div><h3>It starts here</h3><p>Send a note, ask a question, or let the conversation find its way.</p></div>`);""",
    """            const state = getWin().CommonsState;
            const messagesMarkup = messages.map((message: { author: string; timestamp: number; text: string }) => {
                const own = message.author === state.perspective;
                const time = new Date(message.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                return `<article class="chat-msg ${own ? 'own' : ''}">
                    <div class="chat-msg-avatar avatar-${hash(message.author) % 6} commons-char-trigger" data-character="${escapeHtml(message.author)}" title="Inspect ${escapeHtml(message.author)} inner world">${escapeHtml(initials(message.author))}</div>
                    <div class="chat-msg-content"><div class="chat-msg-meta"><span class="chat-msg-author commons-char-trigger" data-character="${escapeHtml(message.author)}" title="Inspect ${escapeHtml(message.author)} inner world">${escapeHtml(message.author)}</span><time>${time}</time></div>
                    <div class="chat-msg-text">${escapeHtml(message.text)}</div></div>
                </article>`;
            }).join('') || (state.theme === 'town_board'
                ? `<div class="commons-feed-empty"><div class="commons-empty-orb">✳</div><h3>It starts here</h3><p>Leave a notice or write a private letter.</p></div>`
                : `<div class="commons-feed-empty"><div class="commons-empty-orb">✳</div><h3>It starts here</h3><p>Send a note, ask a question, or let the conversation find its way.</p></div>`);
            renderMarkup(messagesMarkup, feed);"""
)

# In renderParticipants, replace the fallback else branch:
txt = txt.replace(
    """            } else {
                list.*FIX*= names.map(name => {
                    const participant = participants[name];
                    const pace = (window as *FIX*).CommonsAgent.getTalkativeness(name);
                    const isActing = Boolean((window as *FIX*).CommonsAgent.controllers?.[name]);
                    const controlMode = participant.control_mode || 'unavailable';
                    const controlLabel = controlMode === 'human' ? 'Human' : controlMode === 'npc' ? 'Simple NPC' : controlMode === 'llm' ? '' : 'Unavailable';
                    const canUseLlm = controlMode === 'llm';
                    const actTitle = controlMode === 'human' ? `${name} is human-controlled` : controlMode === 'npc' ? `${name} uses simple NPC behavior` : controlMode === 'llm' ? `Trigger an LLM turn for ${name}` : `${name} has no available character record`;
                    return `<div class="participant-item"><div class="participant-row">
                        <span class="participant-name commons-char-trigger" data-character="${escapeHtml(name)}" title="Inspect ${escapeHtml(name)} inner world">${escapeHtml(name)}${controlLabel ? ` <span class="commons-control-badge">${controlLabel}</span>` : ''}</span>
                        <span class="participant-presence ${isActing ? 'thinking' : participant.active && !participant.blocked ? 'online' : ''}">${isActing ? 'thinking...' : participant.blocked ? 'blocked' : participant.active ? 'active' : 'paused'}</span>
                        <button type="button" class="commons-act-btn" data-character="${escapeHtml(name)}" data-role="act" title="${escapeHtml(actTitle)}" ${!canUseLlm || isActing || participant.blocked ? 'disabled' : ''}>▶ Act</button>
                    </div><div class="participant-controls">
                        <label><input type="checkbox" data-character="${escapeHtml(name)}" data-role="active" ${participant.active ? 'checked' : ''}> In chat</label>
                        <label><input type="checkbox" data-character="${escapeHtml(name)}" data-role="blocked" ${participant.blocked ? 'checked' : ''}> Block</label>
                    </div>${canUseLlm ? `<div class="talkativeness-control"><div class="talkativeness-label"><span>Turn pace</span><span class="talkativeness-value"><span data-pace-for="${escapeHtml(name)}">${pace}s</span><button type="button" class="commons-small-btn pace-random-btn" data-character="${escapeHtml(name)}" data-role="pace-random" title="Choose a random turn pace for ${escapeHtml(name)}" aria-label="Randomize ${escapeHtml(name)} turn pace">🎲</button></span></div>
                        <input type="range" class="talkativeness-slider" min="5" max="120" value="${pace}" data-character="${escapeHtml(name)}" data-role="pace" aria-label="${escapeHtml(name)} automatic turn cooldown"></div>` : `<div class="participant-control-note">${controlMode === 'human' ? 'Human-controlled: no LLM turn' : controlMode === 'npc' ? 'Simple NPC: no LLM turn' : 'Control mode unavailable'}</div>`}</div>`;
                }).join('');
            }""",
    """            }"""
)

txt = txt.replace(
    """            roster.*FIX*= names.map((name: string) => `<label class="commons-roster-option">
                <input type="checkbox" value="${escapeHtml(name)}"><span class="commons-member-avatar avatar-${hash(name) % 6}">${escapeHtml(initials(name))}</span><span>${escapeHtml(name)}</span></label>`).join('');""",
    """            renderMarkup(names.map((name: string) => `<label class="commons-roster-option">
                <input type="checkbox" value="${escapeHtml(name)}"><span class="commons-member-avatar avatar-${hash(name) % 6}">${escapeHtml(initials(name))}</span><span>${escapeHtml(name)}</span></label>`).join(''), roster);"""
)

txt = txt.replace(
    """            if (eligibleNames.length === 0) {
                select.*FIX*= '<option value="" disabled selected>No known characters to contact</option>';
            } else {
                select.*FIX*= eligibleNames.map((name: string) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join('');
            }""",
    """            if (eligibleNames.length === 0) {
                renderMarkup('<option value="" disabled selected>No known characters to contact</option>', select);
            } else {
                renderMarkup(eligibleNames.map((name: string) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`).join(''), select);
            }"""
)

txt = txt.replace(
    """traitsEl.*FIX*= traitKeys.map((t: string) => `<span class="commons-trait-badge">${escapeHtml(t)}</span>`).join('');""",
    """renderMarkup(traitKeys.map((t: string) => `<span class="commons-trait-badge">${escapeHtml(t)}</span>`).join(''), traitsEl);"""
)

txt = txt.replace(
    """                if (latest?.inner) {
                    monologueEl.*FIX*= `<blockquote class="commons-inner-quote">"${escapeHtml(latest.inner)}"</blockquote>
                    <div class="commons-inner-time">${new Date(latest.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</div>`;
                } else {
                    monologueEl.*FIX*= `<div class="commons-drawer-empty-state">No thoughts recorded yet for ${escapeHtml(charName)}. Trigger a turn with ▶ Act to observe their inner stream.</div>`;
                }""",
    """                if (latest?.inner) {
                    renderMarkup(`<blockquote class="commons-inner-quote">"${escapeHtml(latest.inner)}"</blockquote>
                    <div class="commons-inner-time">${new Date(latest.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</div>`, monologueEl);
                } else {
                    renderMarkup(`<div class="commons-drawer-empty-state">No thoughts recorded yet for ${escapeHtml(charName)}. Trigger a turn with ▶ Act to observe their inner stream.</div>`, monologueEl);
                }"""
)

txt = txt.replace(
    """                if (latest) {
                    decisionEl.*FIX*= `<div class="commons-decision-card">
                        <div class="commons-decision-header">
                            <span class="commons-decision-action ${escapeHtml(latest.action)}">${escapeHtml(latest.action.replace('_', ' '))}</span>
                            <span class="commons-decision-summary">${escapeHtml(latest.summary)}</span>
                        </div>
                        ${latest.detail?.text ? `<div class="commons-decision-text">"${escapeHtml(latest.detail.text)}"</div>` : ''}
                    </div>`;
                } else {
                    decisionEl.*FIX*= `<div class="commons-drawer-empty-state">No recent decisions.</div>`;
                }""",
    """                if (latest) {
                    renderMarkup(`<div class="commons-decision-card">
                        <div class="commons-decision-header">
                            <span class="commons-decision-action ${escapeHtml(latest.action)}">${escapeHtml(latest.action.replace('_', ' '))}</span>
                            <span class="commons-decision-summary">${escapeHtml(latest.summary)}</span>
                        </div>
                        ${latest.detail?.text ? `<div class="commons-decision-text">"${escapeHtml(latest.detail.text)}"</div>` : ''}
                    </div>`, decisionEl);
                } else {
                    renderMarkup(`<div class="commons-drawer-empty-state">No recent decisions.</div>`, decisionEl);
                }"""
)

txt = txt.replace(
    """                if (turns.length > 1) {
                    historyEl.*FIX*= turns.slice(1, 8).map((t: *FIX*) => `
                        <div class="commons-history-row">
                            <div class="commons-history-header">
                                <span class="commons-decision-action small ${escapeHtml(t.action)}">${escapeHtml(t.action.replace('_', ' '))}</span>
                                <time>${new Date(t.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</time>
                            </div>
                            ${t.inner ? `<div class="commons-history-thought">"${escapeHtml(t.inner)}"</div>` : ''}
                        </div>
                    `).join('');
                } else {
                    historyEl.*FIX*= `<div class="commons-drawer-empty-state">Earlier turns will appear here as the conversation continues.</div>`;
                }""",
    """                if (turns.length > 1) {
                    renderMarkup(turns.slice(1, 8).map((t: { action: string; timestamp: number; inner?: string }) => `
                        <div class="commons-history-row">
                            <div class="commons-history-header">
                                <span class="commons-decision-action small ${escapeHtml(t.action)}">${escapeHtml(t.action.replace('_', ' '))}</span>
                                <time>${new Date(t.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</time>
                            </div>
                            ${t.inner ? `<div class="commons-history-thought">"${escapeHtml(t.inner)}"</div>` : ''}
                        </div>
                    `).join(''), historyEl);
                } else {
                    renderMarkup(`<div class="commons-drawer-empty-state">Earlier turns will appear here as the conversation continues.</div>`, historyEl);
                }"""
)

rem = txt.count('*FIX*')
print(f"Remaining in commons-ui.ts: {rem}")
assert rem == 0, f"Remaining markers in commons-ui.ts: {rem}"
assert '\u2014' not in txt and '—' not in txt, "Em-dash in commons-ui.ts"
open(p, 'w', encoding='utf-8', newline='').write(txt)
print("commons-ui.ts 100% clean!")
