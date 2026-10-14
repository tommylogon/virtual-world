"use strict";
/**
 * @module stage-chat-agent — Agent decision loop and pacing for Stage Chat
 * @contributes StageChatAgent: character timers, phone app perspective prompt, tool execution
 * @powers Autonomous character participation in Stage Chat
 * @relates StageChatApi, StageChatState
 * @docs docs/virtualWorld/dev_tasks/todo/gameplay/task-824-stage-chat-turn-based-character-perspective-chat-page.md
 */
(function () {
    'use strict';
    class StageChatAgent {
        static timers = {};
        static talkativeness = {};
        static isRunning = false;
        static getTalkativeness(name) {
            return this.talkativeness[name] || 25; // default 25 seconds
        }
        static setTalkativeness(name, val) {
            this.talkativeness[name] = Math.max(5, Math.min(120, parseInt(val) || 25));
            this.resetTimer(name);
        }
        static start() {
            this.isRunning = true;
            this.scheduleAll();
        }
        static stop() {
            this.isRunning = false;
            for (const t of Object.values(this.timers)) {
                clearTimeout(t);
            }
            this.timers = {};
        }
        static resetTimer(charName) {
            if (this.timers[charName]) {
                clearTimeout(this.timers[charName]);
                delete this.timers[charName];
            }
            if (!this.isRunning)
                return;
            const baseSec = this.getTalkativeness(charName);
            // Add jitter (-25% to +25%)
            const jitter = (Math.random() * 0.5 - 0.25) * baseSec;
            const delayMs = Math.max(3000, (baseSec + jitter) * 1000);
            this.timers[charName] = setTimeout(() => {
                this.actCharacter(charName).finally(() => {
                    this.resetTimer(charName);
                });
            }, delayMs);
        }
        static scheduleAll() {
            const participants = window.StageChatState.participants || {};
            for (const name of Object.keys(participants)) {
                this.resetTimer(name);
            }
        }
        static async stepOne() {
            const participants = window.StageChatState.participants || {};
            const available = Object.keys(participants).filter(n => participants[n].active && !participants[n].blocked);
            if (available.length === 0)
                return;
            const chosen = available[Math.floor(Math.random() * available.length)];
            await this.actCharacter(chosen);
        }
        static async actCharacter(charName) {
            const state = window.StageChatState;
            if (state.isPaused)
                return;
            const pInfo = state.participants[charName];
            if (!pInfo || !pInfo.active || pInfo.blocked)
                return;
            try {
                // 1. Fetch character details & memory recall
                let charBio = "";
                try {
                    const charRes = await fetch(`/api/players/${encodeURIComponent(charName)}`);
                    if (charRes.ok) {
                        const cData = await charRes.json();
                        charBio = `You are ${charName}. Traits: ${JSON.stringify(cData.player?.traits || {})}. Description: ${cData.player?.description || ''}`;
                    }
                }
                catch (e) {
                    charBio = `You are ${charName}.`;
                }
                // 2. Build phone app framing prompt
                const systemPrompt = `You are roleplaying as ${charName}.
You are using a chat app on your phone.
You can choose what to do on your turn:
1. "read_chat": Check unseen messages on your phone screen to see what was posted.
2. "write_chat": Post a message into the chat room for others to see.
3. "think": Do nothing, don't look at your phone, just stew or think to yourself.

Respond ONLY with valid JSON in this exact structure:
{
  "thought": "Your private inner thoughts right now (1-3 sentences)",
  "action": "read_chat" | "write_chat" | "think",
  "text": "Your message if write_chat, else empty string",
  "read_mode": "all" | "latest",
  "subjective_memory": "A 1-2 sentence first person reflection summarizing your thoughts/feelings for your memory"
}`;
                const userPrompt = `${charBio}
You have ${pInfo.unread_count || 0} unread notification(s) on your phone chat app.
Last message ID you saw was ${pInfo.last_read_message_id === null ? 'none' : pInfo.last_read_message_id}.
Decide what to do: look at your phone, write a message, or ignore it and think.`;
                let responseJson = null;
                if (window.llmClient && typeof window.llmClient.completePrompt === 'function') {
                    const reply = await window.llmClient.completePrompt(userPrompt, { systemPrompt });
                    try {
                        const clean = reply.replace(/```json/g, '').replace(/```/g, '').trim();
                        responseJson = JSON.parse(clean);
                    }
                    catch (e) {
                        // fallback parse
                    }
                }
                // Fallback deterministic behavior if LLM is unavailable or failed parse
                if (!responseJson || !responseJson.action) {
                    if (pInfo.unread_count > 0 && Math.random() < 0.6) {
                        responseJson = {
                            thought: "I see new notifications on my screen, let me read them.",
                            action: "read_chat",
                            read_mode: "all",
                            subjective_memory: "I decided to check my phone notifications."
                        };
                    }
                    else if (Math.random() < 0.4) {
                        responseJson = {
                            thought: "I have something to say to the group.",
                            action: "write_chat",
                            text: `Hey everyone, ${charName} here.`,
                            subjective_memory: "I texted the stage chat."
                        };
                    }
                    else {
                        responseJson = {
                            thought: "I don't feel like looking at my phone right now.",
                            action: "think",
                            subjective_memory: "I let my thoughts drift without looking at my screen."
                        };
                    }
                }
                // 3. Execute chosen action
                if (responseJson.action === 'read_chat') {
                    await window.StageChatApi.readMessages(charName, responseJson.read_mode || 'all', 3);
                }
                else if (responseJson.action === 'write_chat' && responseJson.text) {
                    await window.StageChatApi.postMessage(charName, responseJson.text);
                }
                // 4. Log inner monologue
                window.StageChatState.logMonologue(charName, responseJson.action, responseJson.thought);
                // 5. Store subjective memory
                if (responseJson.subjective_memory) {
                    await window.StageChatApi.storeMemory(charName, responseJson.subjective_memory, 4);
                }
                await window.StageChatState.sync();
            }
            catch (err) {
                console.error(`[StageChatAgent] Error during act for ${charName}:`, err);
            }
        }
    }
    window.StageChatAgent = StageChatAgent;
})();
