/* Montador de Flashcards com aprofundamento por trechos destacados.
 *
 * Modelo:
 *   card = { id, parentId, seq, front, back }   (front/back são HTML)
 *   Cada trecho destacado (vermelho) no "back" de um card é um <mark class="hl" data-child="ID">
 *   que aponta para o sub-card criado a partir dele.
 *   Ordem de estudo: do último sub-card criado (seq maior) até o card raiz (o último é o primeiro).
 */
(() => {
  'use strict';

  const STORAGE_KEY = 'montador-flashcards-v1';
  const TIFFANY = '#0ABAB5';

  // ---------- Estado ----------
  let state = load() || { cards: {}, roots: [], seq: 0, currentRoot: null, focusId: null };

  function load() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY)); } catch { return null; }
  }
  let saveTimer = null;
  function save() {
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {
      try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch { /* ignore */ }
    }, 200);
  }

  const uid = () => 'c' + Date.now().toString(36) + Math.random().toString(36).slice(2, 7);

  function createCard(parentId, front = '', back = '') {
    const card = { id: uid(), parentId, seq: ++state.seq, front, back };
    state.cards[card.id] = card;
    return card;
  }
  const getCard = id => state.cards[id];
  const childrenOf = id => Object.values(state.cards).filter(c => c.parentId === id).sort((a, b) => a.seq - b.seq);
  function subtree(id) {
    const out = [];
    (function walk(cid) { const c = getCard(cid); if (!c) return; out.push(c); childrenOf(cid).forEach(ch => walk(ch.id)); })(id);
    return out;
  }
  function pathTo(id) {
    const p = [];
    let c = getCard(id);
    while (c) { p.unshift(c); c = getCard(c.parentId); }
    return p;
  }
  const depthOf = id => pathTo(id).length - 1;
  function rootOf(id) { return pathTo(id)[0]; }
  function deleteSubtree(id) { subtree(id).forEach(c => delete state.cards[c.id]); }

  // número de trechos destacados no back do card (= sub-cards diretos)
  const directCount = id => childrenOf(id).length;
  // total de trechos destacados a partir do card (todos os descendentes)
  const totalCount = id => subtree(id).length - 1;

  function plain(html, max = 60) {
    const d = document.createElement('div');
    d.innerHTML = html || '';
    const t = (d.textContent || '').replace(/\s+/g, ' ').trim();
    return t.length > max ? t.slice(0, max - 1) + '…' : t;
  }
  function esc(s) { return s.replace(/[&<>"']/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch])); }
  function snippetOf(card) {
    const parent = getCard(card.parentId);
    if (!parent) return '';
    const d = document.createElement('div');
    d.innerHTML = parent.back;
    const m = d.querySelector(`mark.hl[data-child="${card.id}"]`);
    return m ? m.textContent.trim() : '';
  }

  // ---------- Toast ----------
  const toastEl = document.getElementById('toast');
  let toastTimer;
  function toast(msg) {
    toastEl.textContent = msg;
    toastEl.classList.remove('hidden');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toastEl.classList.add('hidden'), 2600);
  }

  // ---------- Editor rico ----------
  // Guarda a última seleção de cada editor, para que os seletores de cor funcionem.
  const lastRanges = new WeakMap();
  document.addEventListener('selectionchange', () => {
    const sel = document.getSelection();
    if (!sel.rangeCount) return;
    const r = sel.getRangeAt(0);
    const node = r.commonAncestorContainer;
    const ed = (node.nodeType === 1 ? node : node.parentElement)?.closest?.('.editor');
    if (ed) lastRanges.set(ed, r.cloneRange());
  });
  function restoreRange(ed) {
    const cur = document.getSelection();
    if (cur.rangeCount && ed.contains(cur.getRangeAt(0).commonAncestorContainer)) {
      lastRanges.set(ed, cur.getRangeAt(0).cloneRange());
    }
    const r = lastRanges.get(ed);
    if (!r || !ed.contains(r.commonAncestorContainer)) return null;
    ed.focus();
    const sel = document.getSelection();
    sel.removeAllRanges();
    sel.addRange(r);
    return r;
  }
  function exec(ed, cmd, value = null) {
    restoreRange(ed) || ed.focus();
    document.execCommand('styleWithCSS', false, true);
    document.execCommand(cmd, false, value);
    ed.dispatchEvent(new Event('input', { bubbles: true }));
  }
  function wrapSelection(ed, makeWrapper) {
    const r = restoreRange(ed);
    if (!r || r.collapsed) { toast('Selecione um trecho de texto primeiro.'); return null; }
    const w = makeWrapper();
    w.appendChild(r.extractContents());
    r.insertNode(w);
    const sel = document.getSelection();
    sel.removeAllRanges();
    const nr = document.createRange();
    nr.selectNodeContents(w);
    sel.addRange(nr);
    return w;
  }

  function buildToolbar(ed, { isBack, card }) {
    const tb = document.createElement('div');
    tb.className = 'toolbar';
    const btn = (label, title, fn, cls = '') => {
      const b = document.createElement('button');
      b.type = 'button'; b.innerHTML = label; b.title = title; if (cls) b.className = cls;
      b.addEventListener('mousedown', e => e.preventDefault()); // mantém a seleção
      b.addEventListener('click', fn);
      tb.appendChild(b);
      return b;
    };
    const sep = () => { const s = document.createElement('span'); s.className = 'sep'; tb.appendChild(s); };

    btn('<b>B</b>', 'Negrito (Ctrl+B)', () => exec(ed, 'bold'));
    btn('<i>I</i>', 'Itálico (Ctrl+I)', () => exec(ed, 'italic'));
    btn('<u>U</u>', 'Sublinhado (Ctrl+U)', () => exec(ed, 'underline'));
    btn('<s>S</s>', 'Tachado', () => exec(ed, 'strikeThrough'));
    sep();

    const size = document.createElement('select');
    size.title = 'Tamanho da fonte';
    [['', 'Tam.'], ['2', 'Pequeno'], ['3', 'Normal'], ['5', 'Grande'], ['6', 'Enorme']].forEach(([v, t]) => {
      const o = document.createElement('option'); o.value = v; o.textContent = t; size.appendChild(o);
    });
    size.addEventListener('change', () => { if (size.value) exec(ed, 'fontSize', size.value); size.value = ''; });
    tb.appendChild(size);
    sep();

    // Cor da fonte
    const fc = document.createElement('label');
    fc.className = 'color'; fc.title = 'Cor da fonte';
    fc.innerHTML = '<span style="font-weight:700">A</span>';
    const fcInput = document.createElement('input');
    fcInput.type = 'color'; fcInput.value = isBack ? TIFFANY.toLowerCase() : '#1f2933';
    fcInput.addEventListener('input', () => exec(ed, 'foreColor', fcInput.value));
    fc.appendChild(fcInput);
    tb.appendChild(fc);

    // Cor do sublinhado
    const uc = document.createElement('label');
    uc.className = 'color'; uc.title = 'Sublinhar com cor';
    uc.innerHTML = '<span style="text-decoration:underline;text-decoration-color:#e11d2e;text-decoration-thickness:2px">U</span>';
    const ucInput = document.createElement('input');
    ucInput.type = 'color'; ucInput.value = '#f59e0b';
    ucInput.addEventListener('change', () => {
      const span = wrapSelection(ed, () => {
        const s = document.createElement('span');
        s.style.textDecorationLine = 'underline';
        s.style.textDecorationColor = ucInput.value;
        s.style.textDecorationThickness = '2px';
        s.style.textUnderlineOffset = '3px';
        return s;
      });
      if (span) ed.dispatchEvent(new Event('input', { bubbles: true }));
    });
    uc.appendChild(ucInput);
    tb.appendChild(uc);
    sep();

    btn('•', 'Lista', () => exec(ed, 'insertUnorderedList'));
    btn('1.', 'Lista numerada', () => exec(ed, 'insertOrderedList'));
    btn('⌫', 'Limpar formatação', () => exec(ed, 'removeFormat'));

    if (isBack) {
      sep();
      btn('🖍 Destacar seleção', 'Destaca o trecho selecionado em vermelho e cria um sub-card', () => {
        const r = restoreRange(ed);
        if (!r || r.collapsed) { toast('Selecione no BACK o trecho que você não conhece.'); return; }
        highlightRange(card, ed, r);
      }, 'hl-btn');
      const mode = btn('Modo destaque: OFF', 'No modo destaque, basta selecionar o texto com o mouse para destacar', () => {
        const on = !ed.classList.contains('highlight-mode');
        ed.classList.toggle('highlight-mode', on);
        ed.contentEditable = on ? 'false' : 'true';
        mode.textContent = 'Modo destaque: ' + (on ? 'ON' : 'OFF');
        mode.classList.toggle('on', on);
      }, 'hl-btn');
    }
    return tb;
  }

  function buildEditor(card, field) {
    const isBack = field === 'back';
    const wrap = document.createElement('div');
    wrap.className = 'field';
    const label = document.createElement('div');
    label.className = 'field-label';
    label.innerHTML = `<span>${isBack ? 'BACK' : 'FRONT'}</span>`;
    if (isBack) {
      const c = document.createElement('span');
      c.innerHTML = `trechos destacados: <span class="count" data-count-for="${card.id}"></span>`;
      label.appendChild(c);
    }
    const ed = document.createElement('div');
    ed.className = 'editor rich' + (isBack ? ' back-content' : '');
    ed.contentEditable = 'true';
    ed.dataset.cardId = card.id;
    ed.dataset.field = field;
    ed.dataset.placeholder = isBack
      ? 'Resposta / explicação… (selecione trechos desconhecidos para aprofundar)'
      : 'Pergunta / conceito…';
    ed.innerHTML = card[field] || '';

    ed.addEventListener('input', () => {
      card[field] = ed.innerHTML;
      if (isBack) syncHighlights(card, ed);
      refreshMeta();
      save();
    });

    if (isBack) {
      // Modo destaque: selecionar com o mouse já destaca
      ed.addEventListener('mouseup', () => {
        if (!ed.classList.contains('highlight-mode')) return;
        const sel = document.getSelection();
        if (!sel.rangeCount) return;
        const r = sel.getRangeAt(0);
        if (r.collapsed || !ed.contains(r.commonAncestorContainer)) return;
        highlightRange(card, ed, r);
      });
      // Clicar num trecho destacado leva ao sub-card
      ed.addEventListener('click', e => {
        const m = e.target.closest('mark.hl');
        if (!m || !document.getSelection().isCollapsed) return;
        goToChild(card.id, m.dataset.child);
      });
    }

    wrap.append(label, buildToolbar(ed, { isBack, card }), ed);
    return wrap;
  }

  // ---------- Destaques ----------
  function highlightRange(card, ed, range) {
    const startMark = (range.startContainer.nodeType === 1 ? range.startContainer : range.startContainer.parentElement).closest('mark.hl');
    const endMark = (range.endContainer.nodeType === 1 ? range.endContainer : range.endContainer.parentElement).closest('mark.hl');
    if (startMark || endMark) { toast('Esse trecho já está destacado.'); return; }
    const probe = document.createElement('div');
    probe.appendChild(range.cloneContents());
    if (probe.querySelector('mark.hl')) { toast('A seleção contém um trecho já destacado.'); return; }
    const text = probe.textContent.replace(/\s+/g, ' ').trim();
    if (!text) return;

    const child = createCard(card.id, esc(text), '');
    const mark = document.createElement('mark');
    mark.className = 'hl';
    mark.dataset.child = child.id;
    mark.contentEditable = 'false';
    mark.title = 'Clique para ir ao sub-card';
    mark.appendChild(range.extractContents());
    range.insertNode(mark);
    document.getSelection().removeAllRanges();

    card.back = ed.innerHTML;
    save();
    toast(`Trecho destacado → sub-card criado (${directCount(card.id)} neste card)`);

    if (card.id === state.focusId) {
      renderSubcards();
      refreshMeta();
      flashCard(child.id);
    } else {
      refreshMeta();
    }
  }

  // Mantém marcações e sub-cards consistentes quando o usuário apaga/desfaz texto.
  function syncHighlights(card, ed) {
    const marks = [...ed.querySelectorAll('mark.hl')];
    const markIds = new Set(marks.map(m => m.dataset.child));
    let changed = false;
    // marca sem sub-card (ex.: Ctrl+Z após remoção) → remove a marcação
    marks.forEach(m => {
      if (!getCard(m.dataset.child)) { m.replaceWith(...m.childNodes); changed = true; }
    });
    // sub-card sem marca → trecho apagado, remove o sub-card e seus descendentes
    let removed = 0;
    childrenOf(card.id).forEach(ch => {
      if (!markIds.has(ch.id)) { removed += subtree(ch.id).length; deleteSubtree(ch.id); changed = true; }
    });
    if (changed) {
      card.back = ed.innerHTML;
      if (removed) toast(`Trecho apagado: ${removed} sub-card(s) removido(s).`);
      if (card.id === state.focusId) renderSubcards();
    }
  }

  function removeHighlight(childId) {
    const child = getCard(childId);
    if (!child) return;
    const n = subtree(childId).length;
    if (!confirm(`Remover este destaque e ${n} card(s) (incluindo sub-cards)?`)) return;
    const parent = getCard(child.parentId);
    const d = document.createElement('div');
    d.innerHTML = parent.back;
    const m = d.querySelector(`mark.hl[data-child="${childId}"]`);
    if (m) m.replaceWith(...m.childNodes);
    parent.back = d.innerHTML;
    deleteSubtree(childId);
    if (!getCard(state.focusId)) state.focusId = parent.id;
    save();
    render();
  }

  // ---------- Navegação ----------
  function setFocus(id) {
    state.focusId = id;
    state.currentRoot = rootOf(id).id;
    save();
    render();
    document.getElementById('main').scrollTo({ top: 0 });
    window.scrollTo({ top: 0 });
  }
  function goToChild(parentId, childId) {
    if (state.focusId !== parentId) setFocus(parentId);
    flashCard(childId);
  }
  function flashCard(id) {
    const el = document.getElementById('card-' + id);
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    el.classList.remove('flash'); void el.offsetWidth; el.classList.add('flash');
  }

  // ---------- Render ----------
  const main = document.getElementById('main');

  function render() {
    renderRoots();
    renderTree();
    const focus = getCard(state.focusId);
    main.innerHTML = '';
    if (!focus) {
      main.innerHTML = `<div class="empty"><h2>Nenhum card aberto</h2>
        <p>Crie um <b>card raiz</b> para começar. No BACK, destaque os trechos que você não conhece:
        cada trecho vira um novo sub-card, e você pode se aprofundar o quanto quiser.</p>
        <button class="btn primary" id="empty-new">+ Novo card raiz</button></div>`;
      main.querySelector('#empty-new').onclick = newRoot;
      return;
    }

    // Breadcrumb
    const bc = document.createElement('div');
    bc.className = 'breadcrumb';
    pathTo(focus.id).forEach((c, i, arr) => {
      if (i) bc.append(' › ');
      const label = (i === 0 ? '🌳 ' : '') + (plain(c.front, 30) || '(sem front)');
      if (i === arr.length - 1) { const s = document.createElement('b'); s.textContent = label; bc.append(s); }
      else { const a = document.createElement('a'); a.textContent = label; a.onclick = () => setFocus(c.id); bc.append(a); }
    });
    main.appendChild(bc);

    main.appendChild(buildCard(focus, true));

    // Ações
    const actions = document.createElement('div');
    actions.className = 'focus-actions';
    const root = rootOf(focus.id);
    actions.innerHTML = `<span class="stat">Neste card: <b data-count-text="${focus.id}"></b> trecho(s) ·
      a partir da raiz: <b data-total-text="${root.id}"></b> trecho(s)</span>`;
    if (focus.parentId) {
      const up = document.createElement('button');
      up.className = 'btn'; up.textContent = '↑ Voltar ao card pai';
      up.onclick = () => setFocus(focus.parentId);
      actions.prepend(up);
    }
    const done = document.createElement('button');
    done.className = 'btn primary'; done.textContent = '✔ Concluir aprofundamento';
    done.onclick = () => showSummary(root.id);
    const study = document.createElement('button');
    study.className = 'btn'; study.textContent = '▶ Estudar';
    study.onclick = () => startStudy(root.id);
    actions.append(done, study);
    main.appendChild(actions);

    const title = document.createElement('h2');
    title.className = 'subcards-title';
    title.innerHTML = `Sub-cards deste card <span class="count" data-count-for="${focus.id}"></span>`;
    main.appendChild(title);
    const sub = document.createElement('div');
    sub.id = 'subcards';
    sub.className = 'subcards';
    main.appendChild(sub);
    renderSubcards();
    refreshMeta();
  }

  function renderSubcards() {
    const sub = document.getElementById('subcards');
    if (!sub) return;
    const focus = getCard(state.focusId);
    sub.innerHTML = '';
    const kids = childrenOf(focus.id);
    if (!kids.length) {
      sub.innerHTML = `<div class="hint">Selecione no <b>BACK</b> acima um trecho que você desconhece e clique em
        <b>🖍 Destacar seleção</b> (ou ative o <b>Modo destaque</b> e apenas selecione com o mouse).
        O trecho fica <span style="color:var(--hl);font-weight:700">vermelho</span> e um novo FRONT/BACK aparece aqui.</div>`;
      return;
    }
    kids.forEach(k => sub.appendChild(buildCard(k, false)));
  }

  function buildCard(card, isFocus) {
    const el = document.createElement('div');
    el.className = 'card' + (isFocus ? ' focus-card' : '');
    el.id = 'card-' + card.id;
    const head = document.createElement('div');
    head.className = 'card-head';
    const lvl = depthOf(card.id);
    const t = document.createElement('div');
    t.className = 'card-title';
    t.innerHTML = `${lvl === 0 ? '🌳 Card raiz' : 'Sub-card · nível ' + lvl}`;
    const left = document.createElement('div');
    left.appendChild(t);
    const snip = snippetOf(card);
    if (snip) {
      const o = document.createElement('div');
      o.className = 'card-origin';
      o.innerHTML = `originado do trecho: <span class="snip"></span>`;
      o.querySelector('.snip').textContent = '“' + snip + '”';
      left.appendChild(o);
    }
    const btns = document.createElement('div');
    btns.className = 'card-buttons';
    if (!isFocus) {
      const deeper = document.createElement('button');
      deeper.className = 'btn small primary';
      deeper.innerHTML = `Aprofundar → <span class="count" data-total-for="${card.id}"></span>`;
      deeper.title = 'Abrir este sub-card para destacar trechos no BACK dele';
      deeper.onclick = () => setFocus(card.id);
      btns.appendChild(deeper);
    }
    if (card.parentId) {
      const rm = document.createElement('button');
      rm.className = 'btn small danger';
      rm.textContent = '🗑 Remover destaque';
      rm.onclick = () => removeHighlight(card.id);
      btns.appendChild(rm);
    }
    head.append(left, btns);

    const sides = document.createElement('div');
    sides.className = 'sides';
    sides.append(buildEditor(card, 'front'), buildEditor(card, 'back'));
    el.append(head, sides);
    return el;
  }

  // Atualiza contadores, lista de raízes e árvore sem recriar os editores
  function refreshMeta() {
    document.querySelectorAll('[data-count-for]').forEach(e => {
      const n = directCount(e.dataset.countFor); e.textContent = n; e.classList.toggle('zero', !n);
    });
    document.querySelectorAll('[data-total-for]').forEach(e => {
      const n = totalCount(e.dataset.totalFor); e.textContent = n; e.classList.toggle('zero', !n);
      e.title = n + ' trecho(s) destacado(s) a partir deste card';
    });
    document.querySelectorAll('[data-count-text]').forEach(e => { e.textContent = directCount(e.dataset.countText); });
    document.querySelectorAll('[data-total-text]').forEach(e => { e.textContent = totalCount(e.dataset.totalText); });
    renderRoots();
    renderTree();
  }

  function renderRoots() {
    const ul = document.getElementById('root-list');
    ul.innerHTML = '';
    if (!state.roots.length) { ul.innerHTML = '<li style="cursor:default;color:var(--muted)">Nenhum card ainda</li>'; return; }
    state.roots.forEach(id => {
      const c = getCard(id); if (!c) return;
      const li = document.createElement('li');
      if (state.currentRoot === id) li.classList.add('active');
      const n = totalCount(id);
      li.innerHTML = `<span class="name"></span><span class="count ${n ? '' : 'zero'}" title="trechos destacados a partir da raiz">${n}</span><button class="del" title="Excluir">🗑</button>`;
      li.querySelector('.name').textContent = plain(c.front, 40) || '(sem front)';
      li.onclick = () => setFocus(id);
      li.querySelector('.del').onclick = e => {
        e.stopPropagation();
        if (!confirm(`Excluir este card raiz e seus ${n} sub-card(s)?`)) return;
        deleteSubtree(id);
        state.roots = state.roots.filter(r => r !== id);
        if (state.currentRoot === id) { state.currentRoot = state.roots[0] || null; state.focusId = state.currentRoot; }
        save(); render();
      };
      ul.appendChild(li);
    });
  }

  function renderTree() {
    const box = document.getElementById('tree');
    box.innerHTML = '';
    const root = getCard(state.currentRoot);
    if (!root) { box.innerHTML = '<div style="color:var(--muted);font-size:13px">—</div>'; return; }
    const build = c => {
      const li = document.createElement('li');
      const node = document.createElement('div');
      node.className = 'node' + (c.id === state.focusId ? ' focus' : '');
      const n = directCount(c.id);
      node.innerHTML = `<span class="label"></span><span class="count ${n ? '' : 'zero'}" title="trechos destacados neste card">${n}</span>`;
      node.querySelector('.label').textContent = plain(c.front, 34) || '(sem front)';
      node.onclick = () => setFocus(c.id);
      li.appendChild(node);
      const kids = childrenOf(c.id);
      if (kids.length) { const ul = document.createElement('ul'); kids.forEach(k => ul.appendChild(build(k))); li.appendChild(ul); }
      return li;
    };
    const ul = document.createElement('ul');
    ul.appendChild(build(root));
    box.appendChild(ul);
  }

  // ---------- Resumo ----------
  const modal = document.getElementById('summary-modal');
  modal.addEventListener('click', e => { if (e.target === modal || e.target.hasAttribute('data-close')) modal.classList.add('hidden'); });

  // Ordem: último sub-card adicionado primeiro, ..., card raiz por último.
  const studyOrder = rootId => subtree(rootId).sort((a, b) => b.seq - a.seq);

  function showSummary(rootId) {
    const root = getCard(rootId);
    const total = totalCount(rootId);
    const box = document.getElementById('summary-content');
    const rows = [];
    (function walk(c, lvl) {
      rows.push(`<tr><td style="padding-left:${8 + lvl * 18}px">${lvl ? '↳ ' : '🌳 '}${esc(plain(c.front, 50) || '(sem front)')}</td>
        <td>${lvl}</td><td><span class="count ${directCount(c.id) ? '' : 'zero'}">${directCount(c.id)}</span></td>
        <td>${totalCount(c.id)}</td></tr>`);
      childrenOf(c.id).forEach(k => walk(k, lvl + 1));
    })(root, 0);
    const order = studyOrder(rootId).map(c => {
      const lvl = depthOf(c.id);
      return `<li>${esc(plain(c.front, 60) || '(sem front)')} <span class="lvl">· ${lvl ? 'nível ' + lvl : 'raiz'}</span></li>`;
    }).join('');
    box.innerHTML = `
      <h2 style="margin-top:0">Aprofundamento concluído</h2>
      <p style="margin:0 0 4px">Trechos destacados a partir do card raiz <b>“${esc(plain(root.front, 50) || '(sem front)')}”</b>:</p>
      <div class="big-number">${total}</div>
      <p class="stat">Profundidade máxima: ${Math.max(0, ...subtree(rootId).map(c => depthOf(c.id)))} nível(is) · ${total + 1} card(s) no total</p>
      <table class="summary-table">
        <thead><tr><th>Card</th><th>Nível</th><th>Trechos no card</th><th>Total abaixo</th></tr></thead>
        <tbody>${rows.join('')}</tbody>
      </table>
      <h3>Ordem de estudo <span class="stat">(o último sub-card adicionado é o primeiro)</span></h3>
      <ol class="order-list">${order}</ol>
      <div style="display:flex;gap:8px;justify-content:flex-end">
        <button class="btn" data-close>Continuar editando</button>
        <button class="btn primary" id="summary-study">▶ Estudar nesta ordem</button>
      </div>`;
    box.querySelector('#summary-study').onclick = () => { modal.classList.add('hidden'); startStudy(rootId); };
    modal.classList.remove('hidden');
  }

  // ---------- Estudo ----------
  const studyEl = document.getElementById('study');
  const sFront = document.getElementById('study-front');
  const sBack = document.getElementById('study-back');
  const sLabel = document.getElementById('study-side-label');
  let study = { list: [], i: 0, flipped: false };

  function startStudy(rootId) {
    study = { list: studyOrder(rootId), i: 0, flipped: false };
    studyEl.classList.remove('hidden');
    showStudyCard();
  }
  function showStudyCard() {
    const c = study.list[study.i];
    document.getElementById('study-progress').textContent = `${study.i + 1} / ${study.list.length}`;
    const lvl = depthOf(c.id);
    const snip = snippetOf(c);
    document.getElementById('study-path').textContent =
      (lvl ? `Nível ${lvl}` : 'Card raiz') + (snip ? ` · trecho: “${snip}”` : '');
    sFront.innerHTML = c.front || '<i style="color:#a5afb9">(sem front)</i>';
    sBack.innerHTML = c.back || '<i style="color:#a5afb9">(sem back)</i>';
    sBack.querySelectorAll('[contenteditable]').forEach(n => n.removeAttribute('contenteditable'));
    sBack.classList.toggle('hidden', !study.flipped);
    sLabel.textContent = study.flipped ? 'FRONT + BACK' : 'FRONT';
    document.getElementById('study-prev').disabled = study.i === 0;
    document.getElementById('study-next').textContent = study.i === study.list.length - 1 ? 'Finalizar ✔' : 'Próximo →';
  }
  const flip = () => { study.flipped = !study.flipped; showStudyCard(); };
  const next = () => {
    if (study.i < study.list.length - 1) { study.i++; study.flipped = false; showStudyCard(); }
    else { exitStudy(); toast('Estudo concluído! 🎉'); }
  };
  const prev = () => { if (study.i > 0) { study.i--; study.flipped = false; showStudyCard(); } };
  function exitStudy() { studyEl.classList.add('hidden'); }
  document.getElementById('study-card').onclick = flip;
  document.getElementById('study-flip').onclick = flip;
  document.getElementById('study-next').onclick = next;
  document.getElementById('study-prev').onclick = prev;
  document.getElementById('study-exit').onclick = exitStudy;
  document.addEventListener('keydown', e => {
    if (studyEl.classList.contains('hidden')) {
      if (e.key === 'Escape') modal.classList.add('hidden');
      return;
    }
    if (e.key === ' ' || e.key === 'Enter') { e.preventDefault(); flip(); }
    else if (e.key === 'ArrowRight') next();
    else if (e.key === 'ArrowLeft') prev();
    else if (e.key === 'Escape') exitStudy();
  });

  // ---------- Topo ----------
  function newRoot() {
    const c = createCard(null);
    state.roots.push(c.id);
    setFocus(c.id);
    setTimeout(() => document.querySelector(`.editor[data-card-id="${c.id}"][data-field="front"]`)?.focus(), 0);
  }
  document.getElementById('btn-new-root').onclick = newRoot;

  document.getElementById('btn-export').onclick = () => {
    const blob = new Blob([JSON.stringify(state, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'flashcards.json';
    a.click();
    URL.revokeObjectURL(a.href);
  };
  document.getElementById('input-import').onchange = async e => {
    const f = e.target.files[0];
    if (!f) return;
    try {
      const data = JSON.parse(await f.text());
      if (!data.cards || !Array.isArray(data.roots)) throw new Error('formato inválido');
      state = data;
      save(); render();
      toast('Flashcards importados.');
    } catch (err) { alert('Não foi possível importar: ' + err.message); }
    e.target.value = '';
  };

  // ---------- Início ----------
  if (!getCard(state.focusId)) { state.focusId = state.roots[0] || null; state.currentRoot = state.focusId; }
  render();
})();
