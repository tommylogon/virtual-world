with open('static/js/commons/commons-ui.ts', 'r', encoding='utf-8') as f:
    txt = f.read()

# Replace feed.*FIX*=
feed_old = """            feed.*FIX*= messages.map((message: *FIX*) => {
                const own = message.author === getWin().CommonsState.perspective;
                const time = new Date(message.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                return `<article class="chat-msg ${own ? 'own' : ''}">
                    <div class="chat-msg-avatar avatar-${hash(message.author) % 6} commons-char-trigger" data-character="${escapeHtml(message.author)}" title="Inspect ${escapeHtml(message.author)} inner world">${escapeHtml(initials(message.author))}</div>
                    <div class="chat-msg-content"><div class="chat-msg-meta"><span class="chat-msg-author commons-char-trigger" data-character="${escapeHtml(message.author)}" title="Inspect ${escapeHtml(message.author)} inner world">${escapeHtml(message.author)}</span><time>${time}</time></div>
                    <div class="chat-msg-text">${escapeHtml(message.text)}</div></div>
                </article>`;
            }).join('') || (getWin().CommonsState.theme === 'town_board'
                ? `<div class="commons-feed-empty"><div class="commons-empty-orb">✳</div><h3>It starts here</h3><p>Leave a notice or write a private letter.</p></div>`
                : `<div class="commons-feed-empty"><div class="commons-empty-orb">✳</div><h3>It starts here</h3><p>Send a note, ask a question, or let the conversation find its way.</p></div>`);"""

feed_new = """            const messagesMarkup = messages.map((message: { author: string; timestamp: number; text: string }) => {
                const own = message.author === getWin().CommonsState.perspective;
                const time = new Date(message.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                return `<article class="chat-msg ${own ? 'own' : ''}">
                    <div class="chat-msg-avatar avatar-${hash(message.author) % 6} commons-char-trigger" data-character="${escapeHtml(message.author)}" title="Inspect ${escapeHtml(message.author)} inner world">${escapeHtml(initials(message.author))}</div>
                    <div class="chat-msg-content"><div class="chat-msg-meta"><span class="chat-msg-author commons-char-trigger" data-character="${escapeHtml(message.author)}" title="Inspect ${escapeHtml(message.author)} inner world">${escapeHtml(message.author)}</span><time>${time}</time></div>
                    <div class="chat-msg-text">${escapeHtml(message.text)}</div></div>
                </article>`;
            }).join('') || (getWin().CommonsState.theme === 'town_board'
                ? `<div class="commons-feed-empty"><div class="commons-empty-orb">✳</div><h3>It starts here</h3><p>Leave a notice or write a private letter.</p></div>`
                : `<div class="commons-feed-empty"><div class="commons-empty-orb">✳</div><h3>It starts here</h3><p>Send a note, ask a question, or let the conversation find its way.</p></div>`);
            renderMarkup(messagesMarkup, feed);"""

assert feed_old in txt, 'feed_old not found'
txt = txt.replace(feed_old, feed_new)

# Replace the else block in renderParticipants
else_old = """            } else {
                list.*FIX*= names.map(name => {
                    const participant = participants[name];
                    const pace = getWin().CommonsAgent.getTalkativeness(name);
                    const isActing = Boolean(getWin().CommonsAgent.controllers?.[name]);
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
            }"""

assert else_old in txt, 'else_old not found'
txt = txt.replace(else_old, '            }')

rem = txt.count('*FIX*')
print(f'Remaining: {rem}')
assert rem == 0
assert '\u2014' not in txt and '—' not in txt, 'Em-dash found!'
with open('static/js/commons/commons-ui.ts', 'w', encoding='utf-8') as f:
    f.write(txt)
print('commons-ui.ts 100% clean!')
