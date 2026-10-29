/**
 * llm-bench.js - in-app LLM benchmark dev page.
 *
 * For one selected character, builds the exact turn prompt the simulation
 * sends (the same PromptBuilder calls agent-engine.ts uses each turn), runs it
 * against every model the user picks via VW.llm (LLMClient, the same
 * OpenAI-compatible path the sim uses, LM Studio default), and scores each run
 * in the UI: TTFT, TPS, total latency, input/output tokens, format pass/fail
 * against the engine's expected JSON shape, and hallucination flags
 * (items/actions/speech referencing entities absent from worldState.data).
 * Runs are stored client-side (IndexedDB via `storage`, localStorage fallback)
 * and shown in a dashboard with per-run drill-in, cross-model compare, and
 * canvas graphs. No Python port, no second source of truth.
 *
 * @module llm-bench - in-app model benchmark harness
 * @contributes window.VW.llmBench (floating toggle + benchmark panel)
 * @powers benchmark a character's turn prompt across models; score speed,
 *   format compliance and hallucinations; dashboard + compare + graphs
 * @relates PromptBuilder (prompt capture), VW.llm / LLMClient (provider calls),
 *   worldState (character/room state), config (apiBase/apiKey/model), storage
 *   (run persistence)
 * @docs none
 */
// GENERATED: source is the sibling .ts. Do not hand-edit; run `npm run build:ts`.

(() => {
    'use strict';

    const STORE = 'llm_bench';
    const APPROX_TOKENS_PER_CHAR = 4;
    const DEFAULT_CONTEXT_LIMIT = 4096;

    const REQUIRED_FIELDS = ['inner_monologue', 'action', 'speech', 'volume', 'emote'];
    const ALLOWED_KEYS = [
        'inner_monologue', 'action', 'item', 'target', 'speech', 'volume',
        'emote', 'memory', 'emotion_toward', 'learned_names',
    ];

    let panel: any = null;
    let toggleBtn: any = null;
    let runs: any[] = []; // {id, ts, charName, model, prompt, output, metrics, format, hallucinations}

    // ------------------------------------------------------------------ UI build

    function $ (sel: any, root: any = document) { return root.querySelector(sel); }
    function $$ (sel: any, root: any = document) { return [...root.querySelectorAll(sel)]; }
    function el (tag: any, cls?: any, html?: any) {
        const e = document.createElement(tag);
        if (cls) e.className = cls;
        if (html !== undefined) e.replaceChildren(document.createRange().createContextualFragment(html));
        return e;
    }
    function esc (s: any) { return String(s ?? '').replace(/[&<>"']/g, (c: string) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] || '')); }

    function ensureStyles () {
        if ($('#llm-bench-styles')) return;
        const s = el('style', 'llm-bench-styles');
        s.textContent = `
#llm-bench-toggle {
    position: fixed; top: 54px; right: 10px; z-index: 99999;
    background: #6b21a8; color: #fff; border: none; border-radius: 6px;
    padding: 6px 10px; font: 12px/1 system-ui, -apple-system, sans-serif;
    cursor: pointer; box-shadow: 0 2px 8px rgba(0,0,0,.35);
}
#llm-bench-toggle:hover { background: #7c3aed; }
#llm-bench-panel {
    position: fixed; top: 80px; right: 10px; z-index: 99998;
    width: 520px; max-height: 90vh; background: #111; color: #eee;
    border: 1px solid #444; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,.45);
    display: flex; flex-direction: column; font: 12px/1.4 system-ui, -apple-system, sans-serif;
    overflow: hidden;
}
#llm-bench-panel.hidden { display: none !important; }
#llm-bench-header {
    display: flex; align-items: center; justify-content: space-between;
    padding: 8px 10px; border-bottom: 1px solid #333;
    background: #1a1a1a; font-weight: 600;
}
#llm-bench-close { background: transparent; border: none; color: #aaa; cursor: pointer; font-size: 18px; line-height: 1; }
#llm-bench-close:hover { color: #fff; }
#llm-bench-body { padding: 8px 10px; overflow-y: auto; }
.llmb-section { margin-bottom: 8px; }
.llmb-title { font-size: 11px; text-transform: uppercase; letter-spacing: .06em; color: #999; margin-bottom: 6px; display: flex; align-items: center; gap: 6px; }
.llmb-title .llmb-count { background: #333; border-radius: 3px; padding: 0 5px; font-size: 10px; color: #ccc; }
label { font-size: 11px; color: #ccc; display: block; margin: 4px 0 2px; }
select, input[type=text], input[type=number] {
    width: 100%; background: #1a1a1a; border: 1px solid #444; color: #eee;
    border-radius: 4px; padding: 4px 6px; font-size: 11px; box-sizing: border-box;
}
input[type=checkbox] { margin-right: 6px; }
button.llmb-btn {
    background: #6b21a8; color: #fff; border: none; border-radius: 4px;
    padding: 5px 10px; font-size: 11px; cursor: pointer; margin: 2px 4px 2px 0;
}
button.llmb-btn:hover { background: #7c3aed; }
button.llmb-btn.secondary { background: #2a2a2a; border: 1px solid #444; }
button.llmb-btn.danger { background: #7f1d1d; }
button.llmb-btn:disabled { opacity: .5; cursor: not-allowed; }
table.llmb-runs { width: 100%; border-collapse: collapse; font-size: 11px; }
table.llmb-runs th { text-align: left; color: #999; padding: 4px 6px; border-bottom: 1px solid #333; }
table.llmb-runs td { padding: 5px 6px; border-bottom: 1px solid #222; vertical-align: top; }
table.llmb-runs tr:hover { background: #1a1a1a; }
.run-id { font-family: monospace; font-size: 10px; color: #888; }
.ok { color: #4ade80; } .bad { color: #f87171; } .warn { color: #fbbf24; }
.llmb-chip { display: inline-block; background: #222; border: 1px solid #444; border-radius: 3px; padding: 1px 6px; margin: 2px 4px 0 0; font-size: 10px; color: #ccc; }
.llmb-chip.model { background: #374151; color: #bbf; }
.llmb-chip.model.active { background: #5b21b6; color: #fff; }
.pre { white-space: pre-wrap; background: #0a0a0a; border: 1px solid #222; border-radius: 4px; padding: 8px; font: 11px/1.4 ui-monospace, SFMono-Regular, Menlo, monospace; color: #cfcfcf; max-height: 300px; overflow: auto; margin-top: 6px; }
.pre .key { color: #a5b4fc; } .pre .str { color: #86efac; } .pre .num { color: #fbbf24; }
.drill { border-top: 1px solid #333; padding-top: 8px; margin-top: 8px; }
.canvas-wrap { width: 100%; height: 110px; margin-top: 6px; border: 1px solid #222; border-radius: 4px; background: #0a0a0a; }
.llmb-note { font-size: 10px; color: #888; margin-top: 4px; }
`;
        document.head.appendChild(s);
    }

    function buildPanel () {
        if (panel) return panel;
        panel = el('div', 'llm-bench-panel hidden');
        panel.replaceChildren(document.createRange().createContextualFragment(`
<div id="llm-bench-header">
    <span>LLM Bench</span>
    <button id="llm-bench-close" title="Close">×</button>
</div>
<div id="llm-bench-body">
    <div class="llmb-section">
        <div class="llmb-title">1. Character <span class="llmb-count" id="llmb-char-count">0</span></div>
        <select id="llmb-char-select"><option value="">-- select a character --</option></select>
        <div class="llmb-note">Reads state from worldState.data (in memory).</div>
    </div>
    <div class="llmb-section">
        <div class="llmb-title">2. Models <span class="llmb-count" id="llmb-model-count">0</span></div>
        <div id="llmb-models"></div>
        <div style="display:flex;gap:6px;align-items:center;margin-top:6px;">
            <input type="text" id="llmb-custom-model" placeholder="add a model id...">
            <button class="llmb-btn" id="llmb-add-model">add</button>
        </div>
        <div class="llmb-note">Model list from GET ${(typeof config !== 'undefined' && config.apiBase) ? config.apiBase : ''}/models. Select one or more.</div>
    </div>
    <div class="llmb-section">
        <div class="llmb-title">3. Run</div>
        <button class="llmb-btn" id="llmb-run">Run benchmark</button>
        <button class="llmb-btn secondary" id="llmb-abort" disabled>Abort</button>
        <button class="llmb-btn secondary" id="llmb-export">Export JSON</button>
        <button class="llmb-btn secondary" id="llmb-clear">Clear runs</button>
        <input type="file" id="llmb-import" style="display:none;">
        <label for="llmb-import" class="llmb-btn secondary" style="margin:2px 0;">Import JSON</label>
        <div id="llmb-status" class="llmb-note" style="margin-top:6px;"></div>
    </div>
    <div class="llmb-section">
        <div class="llmb-title">4. Runs <span class="llmb-count" id="llmb-runs-count">0</span></div>
        <table class="llmb-runs" id="llmb-runs-table">
            <thead><tr><th style="width:34%">Model</th><th style="width:14%">TTFT</th><th style="width:14%">TPS</th><th style="width:14%">Latency</th><th style="width:12%">Format</th><th style="width:12%">Halluc.</th></tr></thead>
            <tbody id="llmb-runs-tbody"></tbody>
        </table>
        <div class="canvas-wrap"><canvas id="llmb-chart" width="500" height="110"></canvas></div>
    </div>
    <div id="llmb-drill" class="drill hidden"></div>
</div>`));
        document.body.appendChild(panel);

        $('#llm-bench-close').onclick = () => hide();
        $('#llmb-run').onclick = () => runBenchmark();
        $('#llmb-abort').onclick = () => { if (abortCtrl) abortCtrl.abort(); };
        $('#llmb-export').onclick = exportRuns;
        $('#llmb-clear').onclick = clearRuns;
        $('#llmb-add-model').onclick = addCustomModel;
        $('#llmb-custom-model').onkeypress = (e: any) => { if (e.key === 'Enter') addCustomModel(); };
        // The import input is built by buildPanel (it is not in the DOM at module
        // load time), so its handler is wired here with the rest of the panel.
        $('#llmb-import').onchange = async (e: any) => {
            if (!e.target.files.length) return;
            await importRuns(e.target.files[0]);
            e.target.value = '';
        };
        return panel;
    }

    function show () {
        ensureStyles();
        buildPanel();
        panel.classList.remove('hidden');
        refreshCharSelect();
        refreshModelList();
        renderRuns();
    }
    function hide () { if (panel) panel.classList.add('hidden'); }
    function toggle () { panel && !panel.classList.contains('hidden') ? hide() : show(); }

    function ensureToggle () {
        if (toggleBtn) return;
        toggleBtn = el('button', '', 'LLM Bench');
        toggleBtn.id = 'llm-bench-toggle';
        toggleBtn.title = 'LLM benchmark - run a character turn prompt across models';
        toggleBtn.onclick = toggle;
        document.body.appendChild(toggleBtn);
    }

    // ------------------------------------------------------------------ data

    async function loadRuns () {
        try { runs = await storage.getAllAsArray(STORE) || []; }
        catch (e) { runs = []; }
        runs.sort((a: any, b: any) => (b.ts || 0) - (a.ts || 0));
    }
    async function saveRun (run: any) {
        try { await storage.set(STORE, run.id, run); } catch (e) { console.warn('bench: failed to persist run', e); }
        runs.unshift(run);
        if (runs.length > 200) { runs = runs.slice(0, 200); try { await storage.clear(STORE); } catch (e) {}; for (const r of runs) { try { await storage.set(STORE, r.id, r); } catch (e) {} } }
    }
    async function clearRuns () {
        runs = [];
        try { await storage.clear(STORE); } catch (e) {}
        renderRuns();
        $('#llmb-drill').classList.add('hidden');
        $('#llmb-drill').replaceChildren();
    }

    // ------------------------------------------------------------------ model list

    let abortCtrl: any = null;

    async function fetchModels () {
        const base = (typeof config !== 'undefined' && config.apiBase) ? String(config.apiBase) : '';
        if (!base) return [];
        try {
            const resp = await fetch(base.replace(/\/+$/, '') + '/models', { cache: 'no-cache' });
            if (!resp.ok) return [];
            const data = await resp.json();
            const arr = data && Array.isArray(data.data) ? data.data : Array.isArray(data) ? data : [];
            return arr.map((m: any) => (m && m.id) ? String(m.id) : null).filter(Boolean);
        } catch (e) { return []; }
    }

    async function refreshModelList () {
        const container = $('#llmb-models');
        if (!container) return;
        container.replaceChildren();
        const models = await fetchModels();
        const def = (typeof config !== 'undefined' && config.model) ? String(config.model) : '';
        const selected = new Set(JSON.parse(localStorage.getItem('llmb_selected_models') || '[]'));
        const shown = new Set();
        const add = (id: any, prechecked: any) => {
            if (!id || shown.has(id)) return;
            shown.add(id);
            const checked = prechecked || selected.has(id) || (!selected.size && id === def);
            const wrap = el('label');
            wrap.replaceChildren(document.createRange().createContextualFragment(`<input type="checkbox" value="${esc(id)}" ${checked ? 'checked' : ''}> <span class="llmb-chip model ${checked ? 'active' : ''}">${esc(id)}</span>`));
            container.appendChild(wrap);
        };
        models.forEach((m: any) => add(m, true));
        add(def, false);
        // keep previously selected even if not returned by /models
        selected.forEach(id => add(id, true));
        $('#llmb-model-count').textContent = shown.size.toString();
    }

    function selectedModels () {
        return $$('#llmb-models input[type=checkbox]:checked').map(i => i.value).filter(Boolean);
    }

    function addCustomModel () {
        const input = $('#llmb-custom-model');
        const id = input.value.trim();
        if (!id) return;
        const sel = $('#llmb-models');
        const wrap = el('label');
        wrap.replaceChildren(document.createRange().createContextualFragment(`<input type="checkbox" value="${esc(id)}" checked> <span class="llmb-chip model active">${esc(id)}</span>`));
        sel.appendChild(wrap);
        input.value = '';
    }

    // ------------------------------------------------------------------ character list

    function refreshCharSelect () {
        const sel = $('#llmb-char-select');
        if (!sel) return;
        const players = (typeof worldState !== 'undefined' && worldState.data && worldState.data.players) ? worldState.data.players : {};
        const opt0 = document.createElement('option');
        opt0.value = '';
        opt0.textContent = '-- select a character --';
        sel.replaceChildren(opt0);
        Object.keys(players).sort().forEach(name => {
            const o = document.createElement('option');
            o.value = name; o.textContent = name;
            sel.appendChild(o);
        });
        $('#llmb-char-count').textContent = Object.keys(players).length.toString();
    }

    // ------------------------------------------------------------------ prompt capture (same calls as agent-engine.ts turn start)

    /**
     * The captured prompt comes from the shared capture
     * (prompt-builder/capture.js), which mirrors the turn-start call sequence
     * in agent-engine.ts. A local copy of those calls is a second source of
     * truth that drifts - the copy here already drifted once (it dropped the
     * emotion/learned_names fields the live think-decide prompt asks for).
     */
    async function capturePrompt (charName: any) {
        if (typeof PromptBuilder === 'undefined' || typeof PromptBuilder.captureTurnPrompt !== 'function') {
            throw new Error('PromptBuilder.captureTurnPrompt is not available');
        }
        return await PromptBuilder.captureTurnPrompt(String(charName));
    }

    // ------------------------------------------------------------------ metrics / format / hallucination

    function approxTokens (s: any) { return Math.max(1, Math.round(String(s ?? '').length / APPROX_TOKENS_PER_CHAR)); }

    function validateFormat (output: any) {
        const reasons = [];
        let parsed = null;
        try { parsed = JSON.parse(output); } catch (e) { reasons.push('not valid JSON'); return { pass: false, reasons, parsed: null }; }
        if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) { reasons.push('top level is not an object'); return { pass: false, reasons, parsed }; }
        const keys = Object.keys(parsed);
        for (const req of REQUIRED_FIELDS) { if (!(req in parsed)) reasons.push(`missing required field "${req}"`); }
        for (const k of keys) { if (!ALLOWED_KEYS.includes(k)) reasons.push(`unexpected key "${k}"`); }
        // duplicate-key scan on raw text
        const dup = new Set();
        const keyRe = /"([a-z_]+)"\s*:/g;
        const seen = {};
        output.replace(keyRe, (_: any, k: any) => { (seen as any)[k] = ((seen as any)[k] || 0) + 1; });
        Object.entries(seen).forEach(([k, c]) => { if ((c as any) > 1) dup.add(k); });
        if (dup.size) reasons.push(`duplicate key(s): ${[...dup].join(', ')}`);
        return { pass: reasons.length === 0, reasons, parsed };
    }

    function buildKnownSet (roomParts: any, player: any, currentArea: any) {
        const known = new Set();
        const add = (s: any) => { if (s) known.add(String(s).toLowerCase()); };
        // graph nodes
        const data = (typeof worldState !== 'undefined' && worldState.data) ? worldState.data : {};
        const nodes = data.graph && data.graph.nodes ? data.graph.nodes : [];
        for (const n of nodes) { add(n.name); add(n.id); }
        // player inventory / equipped
        const inv = player && player.inventory ? player.inventory : [];
        for (const it of inv) { add(it); }
        const eq = player && player.equipped ? player.equipped : {};
        for (const slot in eq) { add(eq[slot]); }
        // available actions (verbs)
        const aa = roomParts && roomParts.availableActions ? String(roomParts.availableActions) : '';
        aa.split(/[,/]\s*/).forEach(add);
        // exits
        const ex = roomParts && roomParts.exits ? String(roomParts.exits) : '';
        ex.split(/[,/]\s*/).forEach(add);
        // current area name
        add(currentArea && currentArea.name ? currentArea.name : '');
        add(charNameOf(player));
        return known;
    }
    let charNameOf = (p: any) => p && (p.name || p.id || '');

    function findHallucinations (output: any, parsed: any, roomParts: any, player: any, currentArea: any, charName: any) {
        const flags = [];
        const known = buildKnownSet(roomParts, player, currentArea);
        const common = new Set(['the','you','your','and','a','an','of','to','in','it','is','are','was','were','be','been','have','has','had','do','does','did','will','would','could','should','can','may','might','must','i','me','my','myself','this','that','these','those','with','for','on','at','from','by','as','or','not','no','yes','ok','okay','then','than','so','but','if','then','else','when','where','why','how','what','who','which','whose','whom','into','onto','upon','over','under','again','further','once','here','there','now','today','tonight','morning','evening','night','day','time','way','place','room','area','thing','stuff','some','any','all','each','every','both','either','neither','such','own','same','other','another','many','much','more','most','few','little','less','least','enough','quite','rather','very','too','just','only','even','still','already','yet','soon','late','early','high','low','big','small','large','tiny','huge','great','good','bad','new','old','young','long','short','tall','wide','narrow','thick','thin','hard','soft','easy','difficult','simple','complex','clear','dark','light','bright','dim','loud','quiet','silent','hot','cold','warm','cool','freezing','boiling','wet','dry','clean','dirty','fresh','stale','sweet','sour','bitter','salty','spicy','bland','rich','poor','full','empty','open','closed','locked','unlocked','broken','fixed','whole','half','part','parts','piece','pieces','group','groups','set','sets','list','lists','map','maps','key','keys','door','doors','gate','gates','wall','walls','floor','floors','ceiling','roof','window','windows','chair','chairs','table','tables','bed','beds','shelf','shelves','box','boxes','bag','bags','bottle','bottles','cup','cups','bowl','bowls','plate','plates','knife','knives','fork','forks','spoon','spoons','pan','pans','pot','pots','food','water','drink','drink','bread','meat','fruit','apple','apples','orange','oranges','banana','bananas','car','cars','truck','trucks','bike','bikes','boat','boats','ship','ships','train','trains','plane','planes','bird','birds','cat','cats','dog','dogs','fish','fish','horse','horses','cow','cows','pig','pigs','sheep','sheep','goat','goats','chicken','chickens','duck','ducks','bear','bears','lion','lions','tiger','tigers','wolf','wolves','fox','foxes','deer','deer','rabbit','rabbits','mouse','mice','frog','frogs','snake','snakes','spider','spiders','bug','bugs','bee','bees','ant','ants','fly','flies','tree','trees','flower','flowers','grass','leaf','leaves','root','roots','stone','stones','rock','rocks','sand','dirt','mud','snow','ice','rain','wind','storm','cloud','clouds','sun','moon','star','stars','sky','fire','water','earth','air','light','shadow','sound','noise','voice','word','words','name','names','number','numbers','letter','letters','sign','signs','mark','marks','line','lines','shape','shapes','color','colors','red','blue','green','yellow','black','white','gray','grey','brown','orange','purple','pink','gold','silver','metal','wood','glass','plastic','paper','cloth','leather','wool','cotton','silk','steel','iron','copper','gold','silver','diamond','gem','gems','coin','coins','money','cash','card','cards','ticket','tickets','pass','pass','id','ids','passport','map','maps','guide','book','books','page','pages','paper','pen','pens','pencil','pencils','stamp','stamps','envelope','envelopes','mail','letter','letters','phone','phones','call','calls','message','messages','text','texts','email','emails','internet','web','site','sites','link','links','file','files','folder','folders','app','apps','program','programs','code','screen','screens','keyboard','mouse','monitor','monitor','printer','printer','camera','cameras','photo','photos','picture','pictures','video','videos','music','song','songs','music','album','albums','artist','artists','movie','movies','film','films','show','shows','episode','episodes','channel','channels','news','news','sport','sports','game','games','play','plays','player','players','team','teams','match','matches','race','races','win','wins','loss','losses','score','scores','point','points','goal','goals','win','winner','winners','loser','losers','cup','cups','trophy','trophies','medal','medals','prize','prizes','award','awards','contest','contests','challenge','challenges','test','tests','exam','exams','quiz','quizzes','question','questions','answer','answers','solution','solutions','problem','problems','issue','issues','topic','topics','subject','subjects','lesson','lessons','class','classes','course','courses','school','schools','college','colleges','university','universities','teacher','teachers','student','students','study','studies','learn','learning','school','work','job','jobs','work','career','careers','business','businesses','company','companies','office','offices','work','worker','workers','boss','bosses','employee','employees','staff','client','clients','customer','customers','sale','sales','sell','sells','buy','buys','price','prices','cost','costs','pay','pays','paid','money','cash','dollar','dollars','cent','cents','bill','bills','coin','coins','check','checks','card','cards','account','accounts','bank','banks','loan','loans','debt','debts','tax','taxes','fee','fees','rate','rates','percent','percent','deal','deals','offer','offers','discount','discounts','free','cheap','expensive','cost','worth','value','values','quality','quantity','amount','amounts','number','numbers','total','totals','sum','sums','average','averages','percent','percent','ratio','ratios','scale','scales','size','sizes','weight','weights','length','lengths','height','heights','width','widths','depth','depths','speed','speeds','fast','slow','quick','quickly','slowly','rapid','rapidly','swift','swiftly','prompt','promptly','instant','instantly','immediate','immediately','delay','delays','delayed','late','later','latest','early','earlier','earliest','soon','sooner','soonest','before','after','during','while','until','since','from','to','into','onto','upon','over','under','above','below','beneath','beside','between','among','through','throughout','across','along','around','about','near','far','close','distant','here','there','where','wherever','anywhere','somewhere','nowhere','everywhere','home','house','houses','building','buildings','place','places','spot','spots','location','locations','area','areas','zone','zones','region','regions','district','districts','city','cities','town','towns','village','villages','country','countries','nation','nations','state','states','province','provinces','continent','continents','world','worlds','earth','globe','planet','planets','space','universe','universes','star','stars','sun','moon','sky','sky','cloud','clouds','weather','season','seasons','spring','summer','autumn','winter','day','days','night','nights','morning','afternoon','evening','noon','midnight','time','times','moment','moments','minute','minutes','hour','hours','week','weeks','month','months','year','years','decade','decades','century','centuries','millennium','millennia','age','ages','era','eras','period','periods','epoch','epochs','phase','phases','step','steps','stage','stages','level','levels','tier','tiers','grade','grades','rank','ranks','class','classes','type','types','kind','kinds','sort','sorts','category','categories','group','groups','set','sets','series','series','chain','chains','link','links','network','networks','system','systems','method','methods','way','ways','means','mode','modes','style','styles','form','forms','shape','shapes','pattern','patterns','design','designs','plan','plans','plan','plans','idea','ideas','thought','thoughts','concept','concepts','theory','theories','principle','principles','rule','rules','law','laws','regulation','regulations','policy','policies','standard','standards','norm','norms','custom','customs','tradition','traditions','habit','habits','practice','practices','routine','routines','process','processes','procedure','procedures','operation','operations','function','functions','role','roles','job','jobs','task','tasks','duty','duties','responsibility','responsibilities','obligation','obligations','commitment','commitments','promise','promises','agreement','agreements','contract','contracts','deal','deals','arrangement','arrangements','understanding','understandings','deal','deals','terms','conditions','condition','conditions','requirement','requirements','need','needs','want','wants','wish','wishes','desire','desires','goal','goals','aim','aims','objective','objectives','target','targets','purpose','purposes','intention','intentions','plan','plans','plan','plans','plan','plans','plan','plans','plan','plans','plan','plans']);
        // structured: action/item/target
        if (parsed && typeof parsed === 'object') {
            const action = String(parsed.action ?? '').toLowerCase();
            if (action && action !== 'wait' && !known.has(action)) flags.push(`action "${parsed.action}" not in known verbs/entities`);
            for (const f of ['item', 'target']) {
                const v = parsed[f];
                if (v && typeof v === 'string' && !known.has(String(v).toLowerCase())) flags.push(`${f} "${v}" not in known entities`);
            }
        }
        // free-text heuristic: capitalized words in string fields not in known set
        const strFields = ['inner_monologue', 'speech', 'emote', 'memory'];
        for (const f of strFields) {
            const v = parsed && typeof parsed === 'object' ? parsed[f] : null;
            if (typeof v !== 'string') continue;
            const words = v.match(/[A-Z][a-zA-Z]{2,}/g) || [];
            for (const w of words) {
                const lw = w.toLowerCase();
                if (known.has(lw) || common.has(lw)) continue;
                // skip sentence-starters
                flags.push(`possible unknown entity "${w}" in ${f}`);
            }
        }
        // dedupe
        const seen = new Set(); const out = [];
        for (const f of flags) { if (!seen.has(f)) { seen.add(f); out.push(f); } }
        return out;
    }

    // ------------------------------------------------------------------ run

    async function runBenchmark () {
        const charName = $('#llmb-char-select').value;
        const models = selectedModels();
        if (!charName) { $('#llmb-status').textContent = 'Select a character.'; return; }
        if (!models.length) { $('#llmb-status').textContent = 'Select at least one model.'; return; }
        if (typeof VW === 'undefined' || !VW.llm) { $('#llmb-status').textContent = 'VW.llm not available.'; return; }
        if (typeof PromptBuilder === 'undefined') { $('#llmb-status').textContent = 'PromptBuilder not loaded.'; return; }

        let captured;
        try { captured = await capturePrompt(charName); } catch (e: any) { $('#llmb-status').textContent = 'Prompt capture failed: ' + e.message; return; }

        const messages = [
            { role: 'system', content: captured.systemPrompt },
            { role: 'user', content: captured.userPrompt },
        ];
        const inputTokens = approxTokens(captured.systemPrompt + captured.userPrompt);
        const contextLimit = DEFAULT_CONTEXT_LIMIT;

        abortCtrl = new AbortController();
        $('#llmb-run').disabled = true;
        $('#llmb-abort').disabled = false;
        $('#llmb-status').textContent = `Running ${models.length} model(s) for "${charName}"...`;

        const newRuns = [];
        for (const model of models) {
            if (abortCtrl.signal.aborted) break;
            $('#llmb-status').textContent = `Running ${model}...`;
            const started = performance.now();
            let firstChunk: any = null;
            let chunks = '';
            let output = '';
            let error = null;
            try {
                output = await VW.llm.chat(messages, {
                    model,
                    streaming: true,
                    signal: abortCtrl.signal,
                    onChunk: (chunk: any) => {
                        if (abortCtrl.signal.aborted) return;
                        chunks += chunk;
                        if (firstChunk === null) firstChunk = performance.now();
                    },
                });
                if (output === null) { error = new Error('call returned null (aborted/manual)'); }
                else if (typeof output === 'string') { output = output; }
                else { output = String(output); }
            } catch (e) { error = e; }
            const ended = performance.now();
            const latency = ended - started;
            const ttft = firstChunk ? (firstChunk - started) : null;
            const outputTokens = approxTokens(output);
            const tps = latency > 0 ? (outputTokens / (latency / 1000)) : 0;
            const contextPct = contextLimit > 0 ? Math.min(100, Math.round((inputTokens / contextLimit) * 100)) : 0;

            const format = validateFormat(output);
            const hallucinations = findHallucinations(output, format.parsed, captured.roomParts, captured.player, captured.currentArea, charName);

            const run = {
                id: `bench_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
                ts: Date.now(),
                charName,
                model,
                prompt: captured.userPrompt,
                systemPrompt: captured.systemPrompt,
                output: error ? `(error) ${(error as any).message}` : output,
                error: error ? (error as any).message : null,
                metrics: {
                    inputChars: captured.systemPrompt.length + captured.userPrompt.length,
                    outputChars: output ? output.length : 0,
                    inputTokens,
                    outputTokens,
                    ttftMs: ttft,
                    latencyMs: Math.round(latency),
                    tps: Math.round(tps * 100) / 100,
                    contextLimit,
                    contextPct,
                },
                format: { pass: format.pass, reasons: format.reasons },
                hallucinations,
            };
            await saveRun(run);
            newRuns.push(run);
        }
        abortCtrl = null;
        $('#llmb-run').disabled = false;
        $('#llmb-abort').disabled = true;
        $('#llmb-status').textContent = newRuns.length ? `Done - ${newRuns.length} run(s) recorded.` : 'Aborted.';
        renderRuns();
        if (newRuns.length) showDrill(newRuns[0].id);
    }

    // ------------------------------------------------------------------ render

    function renderRuns () {
        const tbody = $('#llmb-runs-tbody');
        const countEl = $('#llmb-runs-count');
        if (!tbody) return;
        countEl.textContent = runs.length.toString();
        tbody.replaceChildren();
        for (const r of runs) {
            const tr = document.createElement('tr');
            const f = r.format || {};
            const h = r.hallucinations || [];
            const m = r.metrics || {};
            tr.replaceChildren(document.createRange().createContextualFragment(`
<td><span class="run-id">${esc(r.id.replace('bench_',''))}</span> <span class="llmb-chip model">${esc(r.model)}</span> <div style="font-size:10px;color:#888;">${esc(r.charName)}</div> <div style="font-size:10px;color:#888;">${new Date(r.ts || 0).toLocaleTimeString()}</div></td>
<td>${m.ttftMs != null ? m.ttftMs + ' ms' : '-'}</td>
<td>${m.tps != null ? m.tps + ' tok/s' : '-'}</td>
<td>${m.latencyMs != null ? m.latencyMs + ' ms' : '-'}</td>
<td class="${f.pass ? 'ok' : 'bad'}">${f.pass ? 'PASS' : 'FAIL'}${f.reasons && f.reasons.length ? ' <span style="font-size:9px;opacity:.7;">(' + f.reasons.join('; ') + ')</span>' : ''}</td>
<td class="${h.length ? 'bad' : 'ok'}">${h.length || 0}</td>
`));
            tr.onclick = () => showDrill(r.id);
            tbody.appendChild(tr);
        }
        drawChart();
    }

    function drawChart () {
        const canvas = $('#llmb-chart');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const w = canvas.width, h = canvas.height;
        ctx.clearRect(0, 0, w, h);
        const recent = runs.slice(0, 10).reverse();
        if (!recent.length) return;
        const values = recent.map(r => (r.metrics && r.metrics.ttftMs != null) ? r.metrics.ttftMs : 0);
        const max = Math.max(...values) || 1;
        const barW = (w - 40) / recent.length;
        ctx.fillStyle = '#6b21a8';
        recent.forEach((r, i) => {
            const v = (r.metrics && r.metrics.ttftMs != null) ? r.metrics.ttftMs : 0;
            const bh = (v / max) * (h - 30);
            const x = 20 + i * barW + 8;
            const y = h - 20 - bh;
            ctx.fillRect(x, y, barW - 10, bh);
            ctx.fillStyle = '#999';
            ctx.fillText(Math.round(v), x, y - 5);
            ctx.fillStyle = '#6b21a8';
        });
        ctx.fillStyle = '#888';
        ctx.font = '10px sans-serif';
        ctx.fillText('TTFT (ms), last 10 runs', 20, h - 5);
    }

    function showDrill (id: any) {
        const r = runs.find((x: any) => x.id === id);
        if (!r) return;
        const d = $('#llmb-drill');
        d.classList.remove('hidden');
        const f = r.format || {};
        const h = r.hallucinations || [];
        const m = r.metrics || {};
        d.replaceChildren(document.createRange().createContextualFragment(`
<div style="display:flex;gap:8px;align-items:center;margin-bottom:8px;">
    <span class="llmb-chip model">${esc(r.model)}</span>
    <span style="font-size:10px;color:#888;">${esc(r.charName)} · ${new Date(r.ts || 0).toLocaleString()}</span>
    <button class="llmb-btn secondary" onclick="document.getElementById('llmb-drill').classList.add('hidden');document.getElementById('llmb-drill').replaceChildren();">Close</button>
</div>
<div class="llmb-section"><div class="llmb-title">System prompt</div><div class="pre">${esc(r.systemPrompt || '')}</div></div>
<div class="llmb-section"><div class="llmb-title">User prompt (turn)</div><div class="pre">${esc(r.prompt || '')}</div></div>
<div class="llmb-section"><div class="llmb-title">Model output</div><div class="pre">${r.error ? '<span style="color:#f87171;">ERROR: ' + esc(r.error) + '</span>' : esc(r.output || '')}</div></div>
<div class="llmb-section"><div class="llmb-title">Metrics</div>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:6px;font-size:11px;color:#ccc;">
        <div>TTFT <span style="color:#eee;">${m.ttftMs != null ? m.ttftMs + ' ms' : '-'}</span></div>
        <div>TPS <span style="color:#eee;">${m.tps != null ? m.tps + ' tok/s' : '-'}</span></div>
        <div>Latency <span style="color:#eee;">${m.latencyMs != null ? m.latencyMs + ' ms' : '-'}</span></div>
        <div>Context <span style="color:#eee;">${m.contextPct != null ? m.contextPct + '%' : '-'}</span></div>
        <div>In tokens <span style="color:#eee;">${m.inputTokens != null ? m.inputTokens : '-'}</span></div>
        <div>Out tokens <span style="color:#eee;">${m.outputTokens != null ? m.outputTokens : '-'}</span></div>
        <div>In chars <span style="color:#eee;">${m.inputChars != null ? m.inputChars : '-'}</span></div>
        <div>Out chars <span style="color:#eee;">${m.outputChars != null ? m.outputChars : '-'}</span></div>
    </div>
    <div style="margin-top:6px;">Format: <span class="${f.pass ? 'ok' : 'bad'}">${f.pass ? 'PASS' : 'FAIL'}</span>${f.reasons && f.reasons.length ? ' - ' + esc(f.reasons.join('; ')) : ''}</div>
    <div>Hallucinations: <span class="${h.length ? 'bad' : 'ok'}">${h.length || 0}</span>${h.length ? '<ul style="margin:4px 0 0 16px;font-size:10px;color:#f87171;"><li>' + esc(h.join('</li><li>')) + '</li></ul>' : ''}</div>
</div>`));
    }

    async function exportRuns () {
        await loadRuns();
        const blob = new Blob([JSON.stringify(runs, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = `llm_bench_${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }
    async function importRuns (file: any) {
        const text = await file.text();
        const data = JSON.parse(text);
        const arr = Array.isArray(data) ? data : (data && data.runs) ? data.runs : [];
        for (const r of arr) { await saveRun(r); }
        renderRuns();
        $('#llmb-status').textContent = `Imported ${arr.length} run(s).`;
    }

    // ------------------------------------------------------------------ boot

    function boot () {
        ensureToggle();
        // refresh character list whenever state updates
        try {
            if (typeof worldState !== 'undefined' && typeof worldState.on === 'function') {
                worldState.on('update', () => { refreshCharSelect(); });
            }
        } catch (e) {}
        loadRuns().then(renderRuns);
    }

    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
    else boot();

    // public API
    window.VW = window.VW || {};
    window.VW.llmBench = { open: show, close: hide, toggle };
})();
