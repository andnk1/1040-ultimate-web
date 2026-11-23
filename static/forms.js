// Form tabs of the Document inventory: "Summary" (the inventory table) first, then W2 and one tab per form type, every form of that
// type side by side (one column per form), built from the form definition (core/formview.py DEFS) - 6 columns per tab, always
// (W2, W2_2 ...), the Total column = every form of that type. A form type the program can't read (1099-G, 1099-K, 5498) lists
// its documents only; under every table, the documents of that type with no column (not read, excluded). The value read stays as read; a correction is kept
// apart (FV.edits[form], saved to /formview/<form>) and goes to the income / deduction summary after a refresh.
// Ticks = marks "fv|<tab>|<row>".
// Needs: TOKEN, FV, MARKS (marks.js saves the row ticks).
(function () {
  const pick = document.getElementById('fvPick'), pane = document.getElementById('fvPane'), summ = document.getElementById('invSummary');
  if (!pick) return;
  const TABS = [{key: 'summary', label: 'Summary', form: 'summary', cols: []}].concat(FV.tabs);
  const E = FV.edits, extra = new Set();                     // extra = rows added with + (until a value is typed)
  const byId = Object.fromEntries(FV.cols.map(c => [c.id, c]));
  const defOf = t => t.defn ? FV.defs[t.defn] : null;
  const allOf = form => FV.cols.filter(c => c.form === form);     // the Total column: every form of that type
  let cur = null;
  const changed = new Set();                                    // forms changed since the page loaded (refresh banner)
  try { cur = sessionStorage.getItem('fvTab:' + TOKEN); } catch (e) {}
  if (!TABS.some(t => t.key === cur)) cur = 'summary';
  const tab = () => TABS.find(t => t.key === cur);
  const colsOf = t => t.cols.map(id => byId[id]);
  const slots = t => { const cs = colsOf(t); while (cs.length < FV.per) cs.push(null); return cs; };   // always 6 columns
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
  const mk = (t, k) => `fv|${t.key}|${k}`;
  const parsedOf = (c, k) => c.parsed[k] === undefined ? null : c.parsed[k];
  const ed = c => (E[c.form] = E[c.form] || {});
  const edited = (c, k) => !!ed(c)[c.id] && k in ed(c)[c.id];
  const eff = (c, k) => edited(c, k) ? ed(c)[c.id][k] : parsedOf(c, k);
  const empty = v => v === null || v === undefined || v === '' || v === 0 || v === false;
  const n0 = v => typeof v === 'number' ? v : 0;
  const whole = v => v === null || v === undefined || v === '' ? '' : (+v).toLocaleString('en-US', {maximumFractionDigits: 0});
  const cents = v => v === null || v === undefined || v === '' ? '(blank)' : (+v).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
  const num = v => { v = String(v || '').replace(/[,$\s]/g, ''); if (/^\(.*\)$/.test(v)) v = '-' + v.slice(1, -1); return v === '' ? null : isNaN(+v) ? NaN : +v; };
  const same = (a, b, t) => t === 'check' ? !!a === !!b : t === 'money' ? Math.abs((a ?? 0) - (b ?? 0)) < 0.005 && (a === null) === (b === null) : (a || null) === (b || null);
  const feeds = c => new RegExp(FV.defs[c.defn].feeds);          // what the income / deduction summary reads from the form

  // ---- the column header: person (W-2 box e / 1098 borrower) · first word of the payer (employer / lender); the file name until
  //      both are read
  function head(c) {
    if (!c) return {name: '', errs: [], title: ''};
    const H = FV.defs[c.defn].head;
    if (H.doc) {                                                         // no names read on the form: the issuer, else the file
      const name = (c.issuer || c.file.replace(/\.[^.]+$/, '')) + (c.of > 1 ? ` (${c.num})` : '');
      return {name, errs: [], title: [c.issuer && 'Issuer: ' + c.issuer, 'File: ' + c.file + ' (' + c.num + ')'].filter(Boolean).join('\n')};
    }
    const ee = (eff(c, H.who) || '').trim(), er = (eff(c, H.payer) || '').trim();
    const w = er.split(/\s+/).filter(Boolean), first = (w[0] || '').toLowerCase() === 'the' && w.length > 1 ? w[1] : w[0] || '';
    const errs = [];
    if (!ee) errs.push(H.who_miss);
    if (!er) errs.push(H.payer_miss);
    const name = ee && er ? `${ee} · ${first.replace(/[,.]$/, '')}` : c.file.replace(/\.[^.]+$/, '');
    const title = [er && H.payer_lbl + ': ' + er, eff(c, H.id) && H.id_lbl + ': ' + eff(c, H.id), 'File: ' + c.file + ' (' + c.num + ')'].filter(Boolean).join('\n');
    return {name, errs, title};
  }

  // ---- rows: boxes a-f, 1-11 and 13 always; box 12 / 14 lines only when they have an amount (a "none" line otherwise);
  //      state 15-17 / local 18-19 lines per state / locality (blank lines when none). + adds a box 12 code, box 14 label, state, locality.
  const TERM = {st: 'Short-term', lt: 'Long-term', und: 'Term unknown'};
  const has = (cols, k) => cols.some(c => !empty(eff(c, k)));
  // sections / rows marked opt (the 1099 layout) show only when a form in the tab has a value there; a term's rows (grp) together
  function shownOf(sec, rows, cols) {
    if (!sec.opt && !rows.some(r => r.opt)) return rows;
    const on = r => r.grp ? rows.some(x => x.grp === r.grp && has(cols, x.k)) : has(cols, r.k);
    if (sec.opt && !rows.some(on)) return [];
    return rows.filter(r => !r.opt || on(r));
  }
  function rowsOf(sec, cols) { return shownOf(sec, rowsAll(sec, cols), cols); }
  function rowsAll(sec, cols) {
    if (!sec.dyn) return sec.rows;
    const keys = new Set();
    cols.forEach(c => { Object.keys(c.parsed).concat(Object.keys(ed(c)[c.id] || {})).forEach(k => {
      if (k.startsWith(sec.dyn) && !empty(eff(c, k))) keys.add(k); }); });
    extra.forEach(k => { if (k.startsWith(sec.dyn)) keys.add(k); });
    if (sec.pair) {                                                     // st:NJ:15 / 16 / 17 together
      let groups = [...new Set([...keys].map(k => k.split(':')[1]))].sort();
      if (!groups.length) groups = ['-'];
      return groups.flatMap(g => Object.keys(sec.pair).map(b => ({k: `${sec.dyn}${g}:${b}`, box: b, t: (sec.ptype || {})[b] || sec.t,
        label: sec.pair[b], tip: g === '-' ? '' : (sec.kind === 'state' ? 'State: ' : 'Locality (box 20): ') + g})));
    }
    if (!keys.size) return sec.hide_none ? [] : [{k: sec.dyn + '*', box: sec.box, t: 'none', label: sec.none || 'None'}];
    if (sec.kind === 'b8949') {                                          // b8949:st:A -> Short-term, Form 8949 box A
      const ord = {st: 0, lt: 1, und: 2};
      return [...keys].sort((a, b) => { const [, ta, xa] = a.split(':'), [, tb, xb] = b.split(':'); return (ord[ta] - ord[tb]) || (xa < xb ? -1 : 1); })
        .map(k => { const [, t, bx] = k.split(':');
          return {k, box: bx, t: sec.t, label: `${TERM[t] || t} — Form 8949 box ${bx}, gain or (loss)`}; });
    }
    return [...keys].sort().map(k => {
      const c = k.slice(sec.dyn.length);
      return {k, box: sec.box, t: sec.t, html: sec.kind === 'code12',
              label: sec.kind === 'code12' ? `<b>${esc(c)}</b> ${esc(FV.codes[c] || 'Unknown code — check the document')}` : c};
    });
  }
  const lineKeys = t => defOf(t).sections.flatMap(sec => rowsOf(sec, colsOf(t)).map(r => r.k));

  // ---- tabs
  function progress(t) { const keys = lineKeys(t), done = keys.filter(k => MARKS[mk(t, k)]).length; return {done, n: keys.length}; }
  function drawTabs() {
    pick.innerHTML = TABS.map(t => `<button type="button" class="tabbtn${t.key === cur ? ' on' : ''}${!t.defn && t.key !== 'summary' && !t.n ? ' soon' : ''}" data-tab="${esc(t.key)}">` +
      `${esc(t.label)}${t.n ? ` (${t.n})` : ''}</button>`).join('');
  }
  pick.addEventListener('click', e => {
    const b = e.target.closest('[data-tab]'); if (!b) return;
    cur = b.dataset.tab; try { sessionStorage.setItem('fvTab:' + TOKEN, cur); } catch (x) {}
    render();
  });

  // ---- the table
  const boxKeys = (c, pre) => [...new Set(Object.keys(c.parsed).concat(Object.keys(ed(c)[c.id] || {})))].filter(k => k.startsWith(pre));
  const locked = (c, r) => !!r.sumof && boxKeys(c, r.sumof).length > 0;
  const val = (c, r) => locked(c, r) ? boxKeys(c, r.sumof).reduce((s, k) => s + n0(eff(c, k)), 0) : eff(c, r.k);
  function cell(c, r) {
    if (!c || r.t === 'none') return '<td class="fvc"></td>';
    if (locked(c, r))
      return `<td class="fvc fvlock" title="The sum of the Form 8949 box rows below — correct those">${whole(val(c, r))}</td>`;
    const v = eff(c, r.k), p = parsedOf(c, r.k), ed = edited(c, r.k);
    const pv = r.t === 'check' ? (p === null ? 'not read' : p ? 'checked' : 'not checked') : r.t === 'money' ? cents(p) : (p || '(blank)');
    const inp = r.t === 'check'
      ? `<input type="checkbox" class="fvchk" data-col="${esc(c.id)}" data-k="${esc(r.k)}" data-t="check" ${v ? 'checked' : ''}>`
      : `<input class="fvin${r.t === 'text' ? ' txt' : ''}" data-col="${esc(c.id)}" data-k="${esc(r.k)}" data-t="${r.t}"
           data-v="${v ?? ''}" data-shown="${esc(r.t === 'money' ? whole(v) : v ?? '')}" value="${esc(r.t === 'money' ? whole(v) : v ?? '')}" spellcheck="false">`;
    return `<td class="fvc${ed ? ' edited' : ''}" title="Read by the program: ${esc(pv)}"><span class="fvcw">${inp}` +
           `<button type="button" class="fvreset" data-col="${esc(c.id)}" data-k="${esc(r.k)}" title="Back to the value read">↺</button></span></td>`;
  }
  function total(r, t) {                                             // every form of that type, not only this tab's
    if (r.t !== 'money') return '';
    const vs = allOf(t.form).map(c => val(c, r));
    return vs.every(empty) ? '' : whole(vs.reduce((s, v) => s + n0(v), 0));
  }
  function render() {
    drawTabs();
    const t = tab();
    if (summ) summ.style.display = t.key === 'summary' ? '' : 'none';
    pane.style.display = t.key === 'summary' ? 'none' : '';
    if (t.key === 'summary') return;
    const def = defOf(t);
    if (!def || !t.cols.length) {
      const none = def ? `No ${esc(t.label)} was read by the program.` : t.others.length ? `The program has no reader for the ${esc(t.label)} yet — the documents are listed only.` : `No ${esc(t.label)} documents.`;
      pane.innerHTML = `<p class="note fvsoon">${none}</p>` + othersHtml(t);
      return;
    }
    const all = allOf(t.form), cols = slots(t), keys = lineKeys(t), allOk = keys.length && keys.every(k => MARKS[mk(t, k)]);
    // the ✓ sits just left of the table (span.fvck, placed from the row) - no column of its own
    let h = `<thead><tr><th class="fvs1"><span class="fvck"><input type="checkbox" id="okAll" title="Tick every line" ${allOk ? 'checked' : ''}></span>Box</th>
      <th class="fvs2">Description</th>`;
    cols.forEach(c => { const x = head(c);
      h += `<th class="fvdoc" data-col="${esc(c ? c.id : '')}" title="${esc(x.title)}"><span class="fvname">${esc(x.name)}</span>` +
           x.errs.map(m => `<span class="fverr">${esc(m)}</span>`).join('') + '</th>'; });
    h += `<th class="fvtot">Total${all.length > t.cols.length ? `<span class="fvsub">all ${all.length} ${esc(def.label)}s</span>` : ''}</th></tr></thead><tbody>`;
    def.sections.forEach((sec, si) => {
      const rows = rowsOf(sec, colsOf(t));
      if (!rows.length) return;                                        // a section no form in the tab has (opt)
      if (sec.title && sec.head !== false)
        h += `<tr class="fvsec"><td class="fvs1"></td><td class="fvs2">${esc(sec.title)}</td><td colspan="${cols.length + 1}"></td></tr>`;
      rows.forEach((r, i) => {
        const ok = !!MARKS[mk(t, r.k)], add = sec.dyn && i === rows.length - 1;
        h += `<tr class="mk${ok ? ' done' : ''}${r.t === 'none' ? ' fvnone' : ''}" data-mk="${esc(mk(t, r.k))}">
          <td class="fvs1"><span class="fvck"><input type="checkbox" class="fvok" data-mk="${esc(mk(t, r.k))}" ${ok ? 'checked' : ''} title="Line verified"></span>${esc(r.box)}</td><td class="fvs2"${r.tip ? ` title="${esc(r.tip)}"` : ''}>${r.html ? r.label : esc(r.label)}` +
          (add && sec.add ? ` <button type="button" class="plus fvadd" data-sec="${si}" title="Add: ${esc(sec.add)}">+</button>` : '') + '</td>';
        cols.forEach(c => { h += cell(c, r); });
        h += `<td class="fvtot" data-k="${esc(r.k)}">${total(r, t)}</td></tr>`;
      });
    });
    pane.innerHTML = `<div id="fvBanners"></div><div class="fvwrap"><table class="fvt" id="fvGrid">${h}</tbody></table></div>
      <p class="note" id="fvStatus"></p>` + othersHtml(t);
    refresh();
  }
  // the documents of this type with no column (not read, excluded, no reader): the name opens the document
  function othersHtml(t) {
    if (!t.others || !t.others.length) return '';
    return `<div class="fvothers"><p class="note"><b>${t.cols.length ? 'Not in the table' : 'Documents'}:</b></p><ul>` +
      t.others.map(o => `<li><a class="doclink" href="/open?path=${encodeURIComponent(o.path)}" title="Open the document">${esc(o.file)}</a>` +
                        ` — ${esc(o.why)}</li>`).join('') + '</ul></div>';
  }

  // banners, totals, progress (without redrawing the table)
  function refresh() {
    const t = tab(), G = document.getElementById('fvGrid'); if (!G) return;
    const def = defOf(t), all = allOf(t.form), rows = {};
    def.sections.forEach(sec => rowsOf(sec, colsOf(t)).forEach(r => { rows[r.k] = r; }));
    G.querySelectorAll('td.fvtot[data-k]').forEach(td => { if (rows[td.dataset.k]) td.textContent = total(rows[td.dataset.k], t); });
    G.querySelectorAll('th.fvdoc').forEach(th => { const x = head(byId[th.dataset.col] || null); th.title = x.title;
      th.innerHTML = `<span class="fvname">${esc(x.name)}</span>` + x.errs.map(m => `<span class="fverr">${esc(m)}</span>`).join(''); });
    const g = progress(t);
    const ne = colsOf(t).reduce((s, c) => s + Object.keys(ed(c)[c.id] || {}).length, 0);
    document.getElementById('fvStatus').innerHTML = `<b>${g.done} of ${g.n}</b> lines verified · <b>${ne}</b> box${ne === 1 ? '' : 'es'} changed by you · the values read by the program are never overwritten`;
    const a = document.getElementById('okAll'); if (a) a.checked = g.n > 0 && g.done === g.n;
    const out = [];
    if (changed.has(t.form))
      out.push(`${esc(def.label)} amounts changed — the ${def.summary} shows them after a refresh. <button type="button" class="light small" id="fvRefresh">Refresh the ${def.summary}</button>`);
    // excess Social Security: W-2s grouped by the employee name read from box e
    const groups = {}, noname = [];
    (t.form === 'w2' ? all : []).forEach(c => { const n = (eff(c, 'ee') || '').trim().toLowerCase().replace(/\s+/g, ' ');
      if (n) (groups[n] = groups[n] || []).push(c); else noname.push(c); });
    Object.values(groups).filter(cs => cs.length > 1).forEach(cs => {
      if (!FV.base) { out.push(`No Social Security wage base on file for ${FV.year || 'this year'} — the excess Social Security check is skipped.`); return; }
      const w = cs.reduce((s, c) => s + n0(eff(c, 'b3')), 0), tx = cs.reduce((s, c) => s + n0(eff(c, 'b4')), 0), max = FV.base * FV.rate, ex = tx - max;
      if (w > FV.base && ex > 0.005)
        out.push(`${esc(eff(cs[0], 'ee'))}: Social Security wages ${whole(w)} on ${cs.length} W-2s, above the ${FV.year} wage base of ${whole(FV.base)}. ` +
                 `SS tax withheld ${cents(tx)} vs max ${cents(max)} → possible excess SS tax credit ${cents(ex)} (Schedule 3, line 11).`);
    });
    if (noname.length && all.length > 1 && t.form === 'w2')
      out.push(`Left out of the excess Social Security check (employee name not read): ${noname.map(c => esc(c.file)).join('; ')}.`);
    const seen = new Set();
    colsOf(t).forEach(c => {
      const xs = (FV.typed[t.form] || {})[c.file]; if (!xs || seen.has(c.file)) return; seen.add(c.file);
      const what = xs.map(x => `${esc(x.what)} ${whole(x.cy)}` + (x.fit !== null && x.fit !== undefined ? `, withholding ${whole(x.fit)}` : '')).join('; ');
      out.push(`${esc(c.file)}: the ${def.summary} has an amount typed over (${what}) — it wins over this page.`);
    });
    document.getElementById('fvBanners').innerHTML = out.map(m => `<div class="banner">${m}</div>`).join('');
    drawTabs();
  }

  // ---- edits
  let timer = null;
  const post = form => fetch(`/formview/${TOKEN}/${encodeURIComponent(form)}`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(E[form] || {})});
  const save = form => { clearTimeout(timer); timer = setTimeout(() => post(form), 200); };
  function unset(c, k) { const m = ed(c); if (m[c.id]) { delete m[c.id][k]; if (!Object.keys(m[c.id]).length) delete m[c.id]; } }
  function setEdit(c, k, v, t) {
    if (same(parsedOf(c, k), v, t)) unset(c, k);
    else (ed(c)[c.id] = ed(c)[c.id] || {})[k] = v;
    if (feeds(c).test(k)) changed.add(c.form);
    save(c.form);
  }
  function sync(el) {
    const c = byId[el.dataset.col], k = el.dataset.k, t = el.dataset.t, v = eff(c, k);
    if (t === 'check') el.checked = !!v;
    else { el.dataset.v = v ?? ''; el.value = t === 'money' ? whole(v) : v ?? ''; el.dataset.shown = el.value; }
    el.closest('td').classList.toggle('edited', edited(c, k));
  }
  pane.addEventListener('change', e => {
    const el = e.target;
    if (el.id === 'okAll') {
      const o = {};
      pane.querySelectorAll('input.fvok').forEach(b => { b.checked = el.checked; b.closest('tr').classList.toggle('done', el.checked); o[b.dataset.mk] = el.checked;
        if (el.checked) MARKS[b.dataset.mk] = true; else delete MARKS[b.dataset.mk]; });
      fetch(`/marks/${TOKEN}`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(o)});
      refresh(); return;
    }
    if (el.classList.contains('fvok')) {                                     // marks.js saves the tick (it runs after this)
      if (el.checked) MARKS[el.dataset.mk] = true; else delete MARKS[el.dataset.mk];
      refresh(); return;
    }
    if (!el.dataset.col) return;
    const c = byId[el.dataset.col], t = el.dataset.t;
    let v;
    if (t === 'check') v = el.checked;
    else if (t === 'money') {
      if (el.value === el.dataset.shown) return;                              // unchanged: the exact amount stays
      v = num(el.value);
      if (Number.isNaN(v)) { el.classList.add('bad'); el.title = 'Not a number'; return; }
    } else v = el.value.trim() || null;
    el.classList.remove('bad');
    setEdit(c, el.dataset.k, v, t); sync(el); refresh();
  });
  pane.addEventListener('click', e => {
    if (e.target.id === 'fvRefresh') {                                       // the Form view stays open after the reload
      try { sessionStorage.setItem('scrollY', scrollY); } catch (x) {}
      clearTimeout(timer);
      post(tab().form).then(() => reloadPage());
      return;
    }
    const rs = e.target.closest('.fvreset');
    if (rs) {
      const c = byId[rs.dataset.col];
      unset(c, rs.dataset.k);
      if (feeds(c).test(rs.dataset.k)) changed.add(c.form);
      save(c.form); sync(rs.parentElement.querySelector('input')); refresh(); return;
    }
    const add = e.target.closest('.fvadd');
    if (add) {
      const sec = defOf(tab()).sections[+add.dataset.sec];
      let code = (prompt(sec.add + ':') || '').trim(); if (!code) return;
      if (sec.kind === 'code12' || sec.kind === 'state') code = code.toUpperCase();
      if (sec.pair) Object.keys(sec.pair).forEach(b => extra.add(`${sec.dyn}${code}:${b}`)); else extra.add(sec.dyn + code);
      render();
    }
  });
  pane.addEventListener('focusin', e => { if (e.target.matches('input.fvin')) e.target.select(); });
  pane.addEventListener('keydown', e => {                                     // Enter = next box down in the same column
    if (e.key !== 'Enter' || !e.target.matches('input.fvin')) return;
    e.preventDefault();
    const col = [...pane.querySelectorAll(`input.fvin[data-col="${CSS.escape(e.target.dataset.col)}"]`)];
    const nx = col[col.indexOf(e.target) + 1];
    e.target.blur(); if (nx) nx.focus();
  });

  render();
})();
