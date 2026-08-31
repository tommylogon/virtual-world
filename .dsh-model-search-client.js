return {
  apply(ctx) {
    var slots = ctx.get('slots');
    if (!slots) return;
    var e = React.createElement;
    var useState = React.useState;
    var useEffect = React.useEffect;
    var useCallback = React.useCallback;
    var useMemo = React.useMemo;
    var useRef = React.useRef;
    slots.inject('conversation.input.model', function() {
      return slots.register({ name: 'conversation.input.model' }, function(props) {
        var st0 = useState(null);
        var state = st0[0];
        var setState = st0[1];
        var op0 = useState(false);
        var open = op0[0];
        var setOpen = op0[1];
        var qu0 = useState('');
        var query = qu0[0];
        var setQuery = qu0[1];
        var fo0 = useState(-1);
        var focusedIndex = fo0[0];
        var setFocusedIndex = fo0[1];
        var bu0 = useState(false);
        var busy = bu0[0];
        var setBusy = bu0[1];
        var inputRef = useRef(null);
        var listRef = useRef(null);
        var rootRef = useRef(null);
        var sid = props.sessionId;
        var load = useCallback(async function() {
          setState({ g: [], f: [], s: 'loading', e: null, cur: null });
          try {
            var r = await host.call('get-models', { sessionId: sid });
            if (r.ok) {
              var v = r.value;
              setState({ g: v.groups || [], f: v.failures || [], s: 'ready', e: null, cur: v.current });
            } else {
              setState({ g: [], f: [], s: 'error', e: r.error, cur: null });
            }
          } catch(x) {
            setState({ g: [], f: [], s: 'error', e: String(x), cur: null });
          }
        }, [sid]);
        useEffect(function() {
          if (props.available !== false) load();
        }, [props.available, load]);
        useEffect(function() {
          if (!open) return;
          function co(ev) {
            if (rootRef.current && !rootRef.current.contains(ev.target)) setOpen(false);
          }
          document.addEventListener('mousedown', co);
          return function() { document.removeEventListener('mousedown', co); };
        }, [open]);
        var choices = useMemo(function() {
          if (!state || state.s !== 'ready') return [];
          var q = query.toLowerCase().trim();
          var out = [];
          for (var i = 0; i < state.g.length; i++) {
            var g = state.g[i];
            for (var j = 0; j < g.models.length; j++) {
              var m = g.models[j];
              if (q) {
                var ok = m.name.toLowerCase().indexOf(q) !== -1 ||
                  g.name.toLowerCase().indexOf(q) !== -1 ||
                  (m.description && m.description.toLowerCase().indexOf(q) !== -1);
                if (!ok) continue;
              }
              var sel = { provider: g.id, model: m.id };
              if (m.reasoning && m.reasoning.defaultEffort !== void 0) sel.reasoningEffort = m.reasoning.defaultEffort;
              var act = state.cur && state.cur.provider === g.id && state.cur.model === m.id;
              out.push({ g: g, m: m, sel: sel, act: act });
            }
          }
          return out;
        }, [state, query]);
        var currentChoice = null;
        if (state && state.cur) {
          for (var i = 0; i < choices.length; i++) {
            if (choices[i].sel.provider === state.cur.provider && choices[i].sel.model === state.cur.model) {
              currentChoice = choices[i];
              break;
            }
          }
        }
        var selectModel = useCallback(async function(selection) {
          setBusy(true);
          try {
            var r = await host.call('select-model', {
              sessionId: sid, provider: selection.provider,
              model: selection.model, reasoningEffort: selection.reasoningEffort
            });
            if (r.ok) {
              setState(function(s) {
                return { g: s.g, f: s.f, s: 'ready', e: null, cur: { provider: selection.provider, model: selection.model, reasoningEffort: selection.reasoningEffort } };
              });
              setOpen(false);
              setQuery('');
            } else {
              setState(function(s) {
                return { g: s.g, f: s.f, s: 'error', e: (r.error && r.error.message) || 'failed', cur: s.cur };
              });
            }
          } catch(x) {
            setState(function(s) {
              return { g: s.g, f: s.f, s: 'error', e: String(x), cur: s.cur };
            });
          } finally {
            setBusy(false);
          }
        }, [sid]);
        function kd(ev) {
          if (ev.key === 'Escape') {
            ev.preventDefault();
            if (query) { setQuery(''); return; }
            setOpen(false); return;
          }
          if (ev.key === 'Enter') {
            ev.preventDefault();
            if (focusedIndex >= 0 && focusedIndex < choices.length) selectModel(choices[focusedIndex].sel);
            else if (choices.length === 1) selectModel(choices[0].sel);
            return;
          }
          if (ev.key === 'ArrowDown') {
            ev.preventDefault();
            if (choices.length) setFocusedIndex(function(i) { return Math.min(i + 1, choices.length - 1); });
            return;
          }
          if (ev.key === 'ArrowUp') {
            ev.preventDefault();
            setFocusedIndex(function(i) { return Math.max(i - 1, 0); });
            return;
          }
        }
        function ic(ev) {
          setQuery(ev.target.value);
          setFocusedIndex(-1);
          if (!open) setOpen(true);
        }
        useEffect(function() {
          if (focusedIndex >= 0 && listRef.current) {
            var items = listRef.current.querySelectorAll('[data-si]');
            if (items[focusedIndex]) items[focusedIndex].scrollIntoView({ block: 'nearest' });
          }
        }, [focusedIndex]);
        useEffect(function() {
          if (open && inputRef.current) inputRef.current.focus();
        }, [open]);
        var label = 'Select model';
        var effort = null;
        if (currentChoice) {
          label = currentChoice.m.name;
          if (currentChoice.m.reasoning && state && state.cur && state.cur.reasoningEffort) {
            var ef = currentChoice.m.reasoning.efforts.find(function(e2) { return e2.id === state.cur.reasoningEffort; });
            effort = ef ? ef.name : state.cur.reasoningEffort;
          } else if (currentChoice.m.reasoning && currentChoice.m.reasoning.defaultEffort !== void 0) {
            effort = 'Default';
          }
        }
        var triggerTitle = effort ? label + ' \u00b7 ' + effort : label;
        var cssId = 'mscss2';
        useEffect(function() {
          if (!document.querySelector('style[data-m="' + cssId + '"]')) {
            var st = document.createElement('style');
            st.dataset.m = cssId;
            st.textContent = '.mr{min-width:0;position:relative}.mt{min-width:0;max-width:min(360px,45cqw);height:28px;color:var(--dsw-alias-label-secondary);cursor:pointer;background:0 0;border:none;border-radius:24px;outline:none;display:flex;align-items:center;gap:4px;padding:0 4px 0 8px;font-size:13px;font-weight:500;line-height:20px}.mt:hover{background:var(--dsw-alias-interactive-bg-hover)}.mt:focus-visible{box-shadow:0 0 0 2px var(--dsw-alias-border-l3)}.ml{text-overflow:ellipsis;white-space:nowrap;min-width:0;overflow:hidden}.me{color:var(--dsw-alias-label-caption);flex:none}.mv{color:var(--dsw-alias-label-caption);flex:none;transition:transform .12s}.mvo{transform:rotate(180deg)}.md{z-index:20;border:1px solid var(--dsw-alias-border-inverted);background:var(--dsw-specific-menu);width:max-content;min-width:min(240px,100vw - 32px);max-width:min(420px,100vw - 32px);max-height:min(480px,100vh - 96px);box-shadow:var(--dsw-shadow-lv3);color:var(--dsw-alias-label-primary);border-radius:12px;flex-direction:column;display:flex;position:absolute;bottom:calc(100% + 8px);right:0;padding:4px;overflow:hidden}.msb{display:flex;align-items:center;gap:4px;border-bottom:1px solid var(--dsw-alias-border-inverted);padding:4px 4px 8px;margin:0 4px}.msi{flex:1;outline:none;border:none;background:none;color:var(--dsw-alias-label-primary);font-size:14px;line-height:20px;padding:4px 8px}.msi::placeholder{color:var(--dsw-alias-label-tertiary)}.mslst{overflow-y:auto;flex:1;padding:0 0 4px}.msgh{color:var(--dsw-alias-label-caption);font-size:11px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;padding:8px 8px 4px}.mso{display:flex;align-items:center;justify-content:space-between;width:100%;padding:6px 8px;border:none;background:none;border-radius:8px;cursor:pointer;color:var(--dsw-alias-label-primary);font-size:13px;line-height:18px;text-align:left;gap:8px}.mso:hover,.msof{background:var(--dsw-alias-interactive-bg-hover)}.msoa{background:var(--dsw-alias-interactive-bg-selected)}.msoc{display:flex;flex-direction:column;gap:2px;overflow:hidden;flex:1}.msmn{text-overflow:ellipsis;white-space:nowrap;overflow:hidden}.msde{color:var(--dsw-alias-label-tertiary);font-size:12px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.msck{flex:none;width:16px;height:16px;color:var(--dsw-alias-brand-primary);font-size:14px;line-height:16px}.msmt,.msem,.mser{padding:10px;font-size:13px;line-height:20px;color:var(--dsw-alias-label-tertiary)}.mser{color:var(--dsw-alias-state-error-primary)}';
            document.head.appendChild(st);
          }
        }, []);
        if (!props.available) return null;
        function buildGroups(items) {
          var groups = {};
          for (var i = 0; i < items.length; i++) {
            var c = items[i];
            if (!groups[c.g.id]) groups[c.g.id] = { name: c.g.name, items: [] };
            groups[c.g.id].items.push(c);
          }
          return groups;
        }
        return e('div', { ref: rootRef, className: 'mr', onKeyDown: kd }, [
          e('button', {
            type: 'button', className: 'mt',
            'aria-label': 'Select model, current ' + label + (effort ? ', reasoning effort ' + effort : ''),
            'aria-haspopup': 'menu', 'aria-expanded': String(open),
            title: triggerTitle, disabled: props.locked,
            onClick: function() {
              if (open) { setOpen(false); setQuery(''); }
              else { setOpen(true); setQuery(''); setFocusedIndex(-1); }
            }
          }, [
            e('span', { className: 'ml' }, label),
            effort ? e('span', { className: 'me' }, effort) : null,
            e('svg', { width: 14, height: 14, className: 'mv' + (open ? ' mvo' : ''), viewBox: '0 0 14 14', fill: 'none' },
              e('path', { d: 'M11.8486 5.5L11.4238 5.92383L8.69727 8.65137C8.44157 8.90706 8.21562 9.13382 8.01172 9.29785C7.79912 9.46883 7.55595 9.61756 7.25 9.66602C7.08435 9.69222 6.91565 9.69222 6.75 9.66602C6.44405 9.61756 6.20088 9.46883 5.98828 9.29785C5.78438 9.13382 5.55843 8.90706 5.30273 8.65137L2.57617 5.92383L2.15137 5.5L3 4.65137L3.42383 5.07617L6.15137 7.80273C6.42595 8.07732 6.59876 8.24849 6.74023 8.3623C6.87291 8.46904 6.92272 8.47813 6.9375 8.48047C6.97895 8.48703 7.02105 8.48703 7.0625 8.48047C7.07728 8.47813 7.12709 8.46904 7.25977 8.3623C7.40124 8.24849 7.57405 8.07732 7.84863 7.80273L10.5762 5.07617L11 4.65137L11.8486 5.5Z', fill: 'currentColor' })
            )
          ]),
          open ? e('div', { className: 'md', role: 'menu', 'aria-label': 'Model and reasoning effort' }, [
            e('div', { className: 'msb' },
              e('input', {
                ref: inputRef, type: 'text', className: 'msi',
                placeholder: 'Search models...',
                value: query, onChange: ic, 'aria-label': 'Search models'
              })
            ),
            state && state.e ? e('div', { className: 'mser' }, state.e) : null,
            state && state.s === 'loading' ? e('div', { className: 'msmt' }, 'Loading models...') : null,
            choices.length === 0 && state && state.s === 'ready' ? e('div', { className: 'msem' }, query ? 'No models match your search' : 'No models available') : null,
            e('div', { ref: listRef, className: 'mslst' }, function() {
              if (choices.length === 0) return null;
              var groups = buildGroups(choices);
              var k = Object.keys(groups);
              var els = [];
              var globalIdx = 0;
              for (var gi = 0; gi < k.length; gi++) {
                var gd = groups[k[gi]];
                els.push(e('div', { key: 'h-' + k[gi], className: 'msgh' }, gd.name));
                for (var mi = 0; mi < gd.items.length; mi++) {
                  var ci = gd.items[mi];
                  if (globalIdx > 0 && !els._lastItemFn) {}
                  var cls = 'mso';
                  if (focusedIndex === globalIdx) cls += ' msof';
                  if (ci.act) cls += ' msoa';
                  var myIdx = globalIdx;
                  els.push(e('button', {
                    key: ci.sel.provider + '/' + ci.sel.model,
                    'data-si': String(myIdx),
                    type: 'button', className: cls, role: 'menuitemradio',
                    'aria-checked': String(ci.act),
                    disabled: busy,
                    onClick: function(cap) { return function() { selectModel(cap.sel); }; }(ci)
                  }, [
                    e('span', { className: 'msoc' }, [
                      e('span', { className: 'msmn' }, ci.m.name),
                      ci.m.description ? e('span', { className: 'msde' }, ci.m.description) : null
                    ]),
                    ci.act ? e('span', { className: 'msck' }, '\u2713') : null
                  ]));
                  globalIdx++;
                }
              }
              return e('div', null, els);
            }())
          ]) : null
        ]);
      });
    });
  }
}