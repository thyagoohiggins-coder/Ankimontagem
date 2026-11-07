/* Montador de Flashcards — Android.
 * Mesmo formato de dados do programa do Windows (versão 2), para trocar backups entre os dois.
 * Um trecho destacado no BACK é <a href="hl:ID"> e aponta para o sub-card criado a partir dele.
 */
'use strict';

const TIFFANY = '#0ABAB5', FRONT_COLOR = '#1f2933', RED = '#e11d2e';
const HL = 'hl:';
const BASE_PT = 11.5;
const FONT_COLORS = [['Azul Tiffany', TIFFANY], ['Preto', FRONT_COLOR], ['Azul', '#2563eb'], ['Verde', '#16a34a'],
  ['Laranja', '#ea580c'], ['Roxo', '#7c3aed'], ['Rosa', '#db2777'], ['Cinza', '#6b7785']];
const UNDER_COLORS = [['Amarelo', '#facc15'], ['Laranja', '#f97316'], ['Verde', '#22c55e'], ['Azul', '#3b82f6'],
  ['Roxo', '#a855f7'], ['Rosa', '#ec4899'], ['Azul Tiffany', TIFFANY], ['Preto', '#111827']];
const SIZES = [9, 10, 11, 11.5, 12, 13, 14, 16, 18, 20, 24, 28, 32];
const DATA_KEY = 'montador-data-v2', SET_KEY = 'montador-settings';
const $ = s => document.querySelector(s);
const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const isAndroid = () => typeof window.Android !== 'undefined';

// ===================================================================== dados
let store = { seq: 0, roots: [], current_root: null, cards: {} };
let openId = null;

const defaultStyle = back => ({ size: BASE_PT, bold: false, italic: false, underline: false, strike: false,
  color: back ? TIFFANY : FRONT_COLOR, ucolor: '' });
let settings = { plainPaste: true, shadow: false, view: 'timeline', zoom: 0,
  styles: { front: defaultStyle(false), back: defaultStyle(true) },
  ankiBasePx: 20, ankiDeck: '', subFirst: true, recentDecks: [] };

function uid() { return Math.random().toString(16).slice(2, 14).padEnd(12, '0'); }
function getCard(id) { return id ? store.cards[id] : null; }
function children(id) { return Object.values(store.cards).filter(c => c.parent_id === id).sort((a, b) => a.seq - b.seq); }
function subtree(id) {
  const out = [], st = [id];
  while (st.length) { const c = getCard(st.pop()); if (!c) continue; out.push(c); children(c.id).reverse().forEach(k => st.push(k.id)); }
  return out;
}
function pathTo(id) { const p = []; let c = getCard(id); while (c) { p.unshift(c); c = getCard(c.parent_id); } return p; }
const depth = id => pathTo(id).length - 1;
const rootOf = id => pathTo(id)[0];
const directCount = id => children(id).length;
const totalCount = id => subtree(id).length - 1;
const timeline = rid => subtree(rid).sort((a, b) => a.seq - b.seq);
const studyOrder = rid => subtree(rid).sort((a, b) => b.seq - a.seq);
const maxDepth = rid => Math.max(0, ...subtree(rid).map(c => depth(c.id)));
function createCard(parentId, front = '', snippet = '') {
  store.seq += 1;
  const c = { id: uid(), parent_id: parentId, seq: store.seq, front, back: '', snippet, created: Date.now() / 1000, anki_note_id: null };
  store.cards[c.id] = c;
  if (!parentId) store.roots.push(c.id);
  return c;
}
function deleteSubtree(id) {
  const ids = subtree(id).map(c => c.id);
  ids.forEach(i => delete store.cards[i]);
  store.roots = store.roots.filter(r => !ids.includes(r));
  if (ids.includes(store.current_root)) store.current_root = store.roots[0] || null;
  return ids;
}
function plain(html, max = 0) {
  const d = document.createElement('div'); d.innerHTML = cleanForView(html || '');
  let t = (d.textContent || '').replace(/​/g, '').replace(/\s+/g, ' ').trim();
  return max && t.length > max ? t.slice(0, max - 1) + '…' : t;
}

// ---------- persistência (mesmo JSON do programa do Windows)
function toJSON() {
  return { version: 2, seq: store.seq, roots: store.roots, current_root: store.current_root, cards: Object.values(store.cards) };
}
function fromJSON(data) {
  if (!data || !Array.isArray(data.cards) || !Array.isArray(data.roots)) throw new Error('arquivo não é um baralho do Montador de Flashcards');
  const s = { seq: 0, roots: [], current_root: null, cards: {} };
  for (const r of data.cards) {
    s.cards[r.id] = { id: r.id, parent_id: r.parent_id || null, seq: r.seq || 0, front: r.front || '', back: r.back || '',
      snippet: r.snippet || '', created: r.created || 0, anki_note_id: r.anki_note_id || null };
  }
  s.roots = data.roots.filter(r => s.cards[r]);
  s.seq = Math.max(data.seq || 0, ...Object.values(s.cards).map(c => c.seq), 0);
  s.current_root = s.cards[data.current_root] ? data.current_root : (s.roots[0] || null);
  return s;
}
let saveTimer = null;
function save() { clearTimeout(saveTimer); saveTimer = setTimeout(saveNow, 400); }
function saveNow() {
  clearTimeout(saveTimer);
  const json = JSON.stringify(toJSON());
  try { localStorage.setItem(DATA_KEY, json); } catch (e) { /* cheio */ }
  if (isAndroid()) { try { Android.saveData(json); } catch (e) { } }
}
window.saveNow = saveNow;
function load() {
  let raw = null;
  try { raw = localStorage.getItem(DATA_KEY); } catch (e) { }
  if (!raw && isAndroid()) { try { raw = Android.loadData(); } catch (e) { } }
  if (raw) { try { store = fromJSON(JSON.parse(raw)); } catch (e) { toast('Não foi possível ler os cards salvos.'); } }
  try { Object.assign(settings, JSON.parse(localStorage.getItem(SET_KEY) || '{}')); } catch (e) { }
  settings.styles = Object.assign({ front: defaultStyle(false), back: defaultStyle(true) }, settings.styles);
}
function saveSettings() { try { localStorage.setItem(SET_KEY, JSON.stringify(settings)); } catch (e) { } }

// ===================================================================== HTML dos cards
// O programa do Windows salva um documento completo do Qt; aqui mostramos só o corpo.
function cleanForView(html) {
  if (!html) return '';
  if (!/<body|<html|<!doctype/i.test(html)) return html;
  const doc = new DOMParser().parseFromString(html, 'text/html');
  doc.querySelectorAll('style,script,meta,title').forEach(n => n.remove());
  return doc.body.innerHTML.replace(/^\s+|\s+$/g, '');
}
function hlStyle() {
  return `color:${RED}; text-decoration:underline; text-decoration-color:${RED}` +
    (settings.shadow ? '; background-color:rgba(225,29,46,0.15)' : '');
}
function styleAnchors(root) {
  root.querySelectorAll('a[href^="hl:"]').forEach(a => {
    a.setAttribute('style', hlStyle());
    if (!a.dataset.t) a.dataset.t = a.textContent;
  });
}
function editorHtml(ed) {
  const c = ed.cloneNode(true);
  c.querySelectorAll('a[href^="hl:"]').forEach(a => a.removeAttribute('data-t'));
  let h = c.innerHTML.replace(/​/g, '');
  if (!c.textContent.replace(/​/g, '').trim()) h = '';
  return h;
}

// ===================================================================== interface
const list = $('#list');
let items = {};   // id → elemento

function toast(msg, ms = 2800) {
  const t = $('#toast'); t.textContent = msg; t.classList.remove('hidden');
  clearTimeout(toast.t); toast.t = setTimeout(() => t.classList.add('hidden'), ms);
}

function renderDecks() {
  const sel = $('#deck'); sel.innerHTML = '';
  store.roots.forEach(id => {
    const o = document.createElement('option'); o.value = id;
    o.textContent = '🌳 ' + (plain(getCard(id).front, 40) || '(card sem título)');
    sel.appendChild(o);
  });
  sel.value = store.current_root || '';
}

function showRoot(rid) {
  hideBar();
  store.current_root = getCard(rid) ? rid : null;
  items = {}; list.innerHTML = ''; openId = null;
  list.classList.toggle('grid', settings.view === 'grid');
  document.body.classList.toggle('shadow', !!settings.shadow);
  const has = !!store.current_root;
  $('#empty').classList.toggle('hidden', has);
  $('#stats').classList.toggle('hidden', !has);
  $('#btn-study').disabled = !has;
  renderDecks();
  if (!has) return;
  timeline(rid).forEach(addItem);
  openCard(rid, false);
  refresh();
  save();
}

function addItem(card) {
  const d = depth(card.id);
  const el = document.createElement('section');
  el.className = 'item' + (d === 0 ? ' root' : '');
  el.dataset.id = card.id;
  if (settings.view !== 'grid') el.style.paddingLeft = (28 + d * 16) + 'px';
  el.innerHTML = `
    ${d ? `<span class="link" style="width:${d * 16}px"></span>` : ''}
    <span class="dot" style="left:${8 + d * 16}px"></span>
    <div class="box">
      <div class="head"><div class="t"><div class="meta"></div><div class="title"></div></div><span class="badge"></span></div>
      <div class="body hidden">
        <div class="side"><span>FRONT</span></div>
        <div class="ed front rich" contenteditable="true" data-field="front" data-ph="Pergunta / conceito…"></div>
        <div class="side"><span>BACK</span><span class="cnt"></span></div>
        <div class="ed back rich" contenteditable="true" data-field="back"
             data-ph="Resposta… selecione o trecho que você não conhece e toque em 🖍 Destacar"></div>
        <div class="foot">
          <button class="ghost up ${card.parent_id ? '' : 'hidden'}">↑ Card pai</button>
          <span></span>
          <button class="ghost more">⋯</button>
        </div>
      </div>
    </div>`;
  const front = el.querySelector('.ed.front'), back = el.querySelector('.ed.back');
  front.innerHTML = cleanForView(card.front);
  back.innerHTML = cleanForView(card.back);
  styleAnchors(back);
  el.querySelector('.head').addEventListener('click', () => openCard(card.id === openId ? null : card.id));
  el.querySelector('.up').addEventListener('click', () => openCard(card.parent_id));
  el.querySelector('.more').addEventListener('click', () => cardMenu(card.id));
  [front, back].forEach(ed => wireEditor(ed, card));
  list.appendChild(el);
  items[card.id] = el;
  updateItem(card.id);
  return el;
}

function updateItem(id) {
  const el = items[id], c = getCard(id);
  if (!el || !c) return;
  const d = depth(id);
  el.querySelector('.meta').innerHTML = d ? `NÍVEL ${d} · de <span class="sn">“${esc(c.snippet.slice(0, 40))}”</span>` : '🌳 CARD RAIZ';
  const t = plain(c.front);
  const title = el.querySelector('.title');
  title.textContent = t || '(sem front)'; title.classList.toggle('empty', !t);
  const n = directCount(id);
  const b = el.querySelector('.badge'); b.textContent = n; b.classList.toggle('zero', !n);
  el.querySelector('.cnt').textContent = `${n} trecho${n !== 1 ? 's' : ''} destacado${n !== 1 ? 's' : ''}`;
}

function refresh() {
  const rid = store.current_root;
  if (!rid) return;
  Object.keys(items).forEach(updateItem);
  const tot = totalCount(rid), cards = tot + 1;
  $('#stats').innerHTML = `<b>${tot}</b> trecho${tot !== 1 ? 's' : ''} destacado${tot !== 1 ? 's' : ''} a partir da raiz · ` +
    `${cards} card${cards !== 1 ? 's' : ''} · ${maxDepth(rid)} nível(is) <a href="#" id="lnk-sum">resumo ›</a>`;
  $('#lnk-sum').onclick = e => { e.preventDefault(); showSummary(); };
  const o = [...$('#deck').options].find(o => o.value === rid);
  if (o) o.textContent = '🌳 ' + (plain(getCard(rid).front, 40) || '(card sem título)');
}

function openCard(id, focus = true) {
  if (openId && items[openId]) {
    items[openId].classList.remove('open');
    items[openId].querySelector('.body').classList.add('hidden');
  }
  openId = id && items[id] ? id : null;
  if (!openId) return;
  const el = items[openId];
  el.classList.add('open');
  el.querySelector('.body').classList.remove('hidden');
  setTimeout(() => el.scrollIntoView({ behavior: 'smooth', block: 'start' }), 30);
  if (focus) {
    const c = getCard(openId);
    const ed = el.querySelector(plain(c.front) ? '.ed.back' : '.ed.front');
    ed.focus();
    placeCaretEnd(ed);
  }
}
function flash(id) {
  const el = items[id]; if (!el) return;
  el.classList.add('flash'); setTimeout(() => el.classList.remove('flash'), 1100);
}
function placeCaretEnd(ed) {
  const r = document.createRange(); r.selectNodeContents(ed); r.collapse(false);
  const s = getSelection(); s.removeAllRanges(); s.addRange(r);
}

// ===================================================================== editor
let current = null;          // {ed, card}
let pending = [];            // partes de uma estrutura separada (Ranges)

function wireEditor(ed, card) {
  const field = ed.dataset.field, isBack = field === 'back';
  ed.addEventListener('focus', () => { current = { ed, card }; prepareTyping(ed); updateBar(); });
  ed.addEventListener('blur', () => setTimeout(() => {
    if (!document.activeElement || !document.activeElement.classList.contains('ed')) {
      if (!$('#fmtbar').contains(document.activeElement)) hideBar();
    }
  }, 150));
  ed.addEventListener('input', () => {
    if (isBack) keepHighlightEdges(ed);
    card[field] = editorHtml(ed);
    if (isBack) syncHighlights(ed, card);
    updateItem(card.id);
    if (!card.parent_id && field === 'front') refresh();
    save();
  });
  ed.addEventListener('paste', e => {
    if (!settings.plainPaste) return;
    e.preventDefault();
    const text = (e.clipboardData || window.clipboardData).getData('text/plain');
    insertStyledText(ed, text);
  });
  ed.addEventListener('click', e => {
    const a = e.target.closest && e.target.closest('a[href^="hl:"]');
    if (a) e.preventDefault();
    updateBar();
  });
  ed.addEventListener('keyup', updateBar);
}

// Formatação lembrada: o texto novo (card vazio ou linha vazia) usa a última formatação escolhida.
function sideStyle(ed) { return settings.styles[ed.dataset.field === 'back' ? 'back' : 'front']; }
function styleCss(st, back) {
  const p = [];
  if (st.color && st.color.toLowerCase() !== (back ? TIFFANY : FRONT_COLOR).toLowerCase()) p.push(`color:${st.color}`);
  if (st.size && Math.abs(st.size - BASE_PT) > 0.01) p.push(`font-size:${st.size}pt`);
  if (st.bold) p.push('font-weight:700');
  if (st.italic) p.push('font-style:italic');
  const deco = [st.underline ? 'underline' : '', st.strike ? 'line-through' : ''].filter(Boolean).join(' ');
  if (deco) p.push(`text-decoration:${deco}`);
  if (st.underline && st.ucolor) p.push(`text-decoration-color:${st.ucolor}`);
  return p.join('; ');
}
function emptyAtCaret(ed) {
  const s = getSelection(); if (!s.rangeCount) return false;
  const n = s.anchorNode;
  if (!ed.contains(n)) return false;
  if (!ed.textContent.replace(/​/g, '').trim()) return true;
  const block = (n.nodeType === 1 ? n : n.parentElement).closest('div,p,li');
  return !!block && block !== ed && ed.contains(block) && !block.textContent.replace(/​/g, '').trim();
}
function prepareTyping(ed) {
  const css = styleCss(sideStyle(ed), ed.dataset.field === 'back');
  if (!css || !emptyAtCaret(ed)) return;
  const s = getSelection();
  if (s.anchorNode && s.anchorNode.parentElement && s.anchorNode.parentElement.dataset.typing) return;
  const span = document.createElement('span');
  span.setAttribute('style', css); span.dataset.typing = '1';
  span.textContent = '​';
  const r = s.getRangeAt(0);
  if (!ed.textContent.replace(/​/g, '').trim()) { ed.innerHTML = ''; ed.appendChild(span); }
  else r.insertNode(span);
  const nr = document.createRange(); nr.setStart(span.firstChild, 1); nr.collapse(true);
  s.removeAllRanges(); s.addRange(nr);
}
function insertStyledText(ed, text) {
  const s = getSelection(); if (!s.rangeCount) return;
  const r = s.getRangeAt(0); r.deleteContents();
  const css = styleCss(sideStyle(ed), ed.dataset.field === 'back');
  const inHl = r.startContainer.parentElement && r.startContainer.parentElement.closest('a[href^="hl:"]');
  let node;
  if (css && !inHl) { node = document.createElement('span'); node.setAttribute('style', css); node.textContent = text; }
  else node = document.createTextNode(text);
  if (inHl) { inHl.after(node); } else r.insertNode(node);
  const nr = document.createRange(); nr.setStartAfter(node); nr.collapse(true);
  s.removeAllRanges(); s.addRange(nr);
  ed.dispatchEvent(new Event('input'));
}
// Texto digitado colado ao trecho destacado não pode virar parte dele.
function keepHighlightEdges(ed) {
  ed.querySelectorAll('a[href^="hl:"]').forEach(a => {
    const orig = a.dataset.t, now = a.textContent;
    if (!orig || now === orig) return;
    const s = getSelection();
    if (now.startsWith(orig) && now.length > orig.length) {
      const extra = now.slice(orig.length);
      trimAnchorText(a, orig.length, now.length);
      const t = document.createTextNode(extra); a.after(t);
      const r = document.createRange(); r.setStart(t, extra.length); r.collapse(true); s.removeAllRanges(); s.addRange(r);
    } else if (now.endsWith(orig) && now.length > orig.length) {
      const extra = now.slice(0, now.length - orig.length);
      trimAnchorText(a, 0, extra.length);
      const t = document.createTextNode(extra); a.before(t);
      const r = document.createRange(); r.setStart(t, extra.length); r.collapse(true); s.removeAllRanges(); s.addRange(r);
    } else {
      a.dataset.t = now;   // editou o meio do próprio trecho
    }
  });
}
function trimAnchorText(a, from, to) {
  // remove os caracteres [from, to) do texto do link
  const w = document.createTreeWalker(a, NodeFilter.SHOW_TEXT); let pos = 0, n;
  const parts = [];
  while ((n = w.nextNode())) { parts.push([n, pos]); pos += n.data.length; }
  for (const [node, start] of parts.reverse()) {
    const a0 = Math.max(from, start), b0 = Math.min(to, start + node.data.length);
    if (a0 < b0) node.deleteData(a0 - start, b0 - a0);
  }
}

function hlIds(ed) { return new Set([...ed.querySelectorAll('a[href^="hl:"]')].map(a => a.getAttribute('href').slice(HL.length))); }
function syncHighlights(ed, card) {
  const ids = hlIds(ed);
  let changed = false, removed = 0;
  // destaque sem card (ex.: desfazer depois de remover) → vira texto normal
  ed.querySelectorAll('a[href^="hl:"]').forEach(a => {
    if (!getCard(a.getAttribute('href').slice(HL.length))) { a.replaceWith(...a.childNodes); changed = true; }
  });
  // card sem destaque (trecho apagado) → remove sub-card e descendentes
  children(card.id).forEach(ch => {
    if (!ids.has(ch.id)) {
      deleteSubtree(ch.id).forEach(i => { if (items[i]) { items[i].remove(); delete items[i]; } removed++; });
      changed = true;
    }
  });
  if (changed) card.back = editorHtml(ed);
  if (removed) { toast(`Trecho apagado: ${removed} sub-card(s) removido(s).`); refresh(); }
}

function selectionIn(ed) {
  const s = getSelection();
  if (!s.rangeCount) return null;
  const r = s.getRangeAt(0);
  return ed.contains(r.commonAncestorContainer) ? r : null;
}
function rangeHasHighlight(ed, r) {
  return [...ed.querySelectorAll('a[href^="hl:"]')].some(a => r.intersectsNode(a)) ||
    !!(r.startContainer.parentElement && r.startContainer.parentElement.closest('a[href^="hl:"]'));
}
function rangeText(r) { return r.toString().replace(/​/g, '').replace(/\s+/g, ' ').trim(); }

function markPending() {
  if (!window.CSS || !CSS.highlights) return;
  if (pending.length) CSS.highlights.set('pending', new Highlight(...pending));
  else CSS.highlights.delete('pending');
}
function clearPending() { pending = []; markPending(); updateBar(); }

function joinPart() {
  if (!current || current.ed.dataset.field !== 'back') return;
  const r = selectionIn(current.ed);
  if (!r || r.collapsed || !rangeText(r)) { toast('Selecione a primeira parte (ex.: “got”) e toque em 🔗 Juntar.'); return; }
  if (rangeHasHighlight(current.ed, r) || pending.some(p => p.compareBoundaryPoints(Range.END_TO_START, r) < 0 && r.compareBoundaryPoints(Range.END_TO_START, p) < 0)) {
    toast('Esse trecho já está destacado ou já foi escolhido.'); return;
  }
  pending.push(r.cloneRange());
  pending.sort((a, b) => a.compareBoundaryPoints(Range.START_TO_START, b));
  markPending();
  getSelection().collapseToEnd();
  toast(`🔗 ${pending.map(rangeText).join(' … ')} — agora selecione a outra parte (ex.: “back”) e toque em 🖍 Destacar.`, 6000);
  updateBar(true);
}

function highlight() {
  if (!current || current.ed.dataset.field !== 'back') return;
  const { ed, card } = current;
  const parts = pending.filter(p => !p.collapsed && ed.contains(p.commonAncestorContainer));
  const r = selectionIn(ed);
  if (r && !r.collapsed && rangeText(r) && !parts.some(p => p.compareBoundaryPoints(Range.START_TO_START, r) === 0 && p.compareBoundaryPoints(Range.END_TO_END, r) === 0)) parts.push(r.cloneRange());
  parts.sort((a, b) => a.compareBoundaryPoints(Range.START_TO_START, b));
  const texts = parts.map(rangeText).filter(Boolean);
  if (!texts.length) { toast('Selecione no BACK o trecho que você não conhece e toque em 🖍 Destacar.'); return; }
  if (parts.some(p => rangeHasHighlight(ed, p))) { toast('Esse trecho já está destacado.'); return; }
  const snippet = texts.join(' … '), front = texts.join(' ');
  const child = createCard(card.id, esc(front), snippet);
  // do fim para o começo, para as posições não mudarem
  [...parts].reverse().forEach(p => {
    const a = document.createElement('a');
    a.setAttribute('href', HL + child.id);
    a.setAttribute('style', hlStyle());
    a.appendChild(p.extractContents());
    p.insertNode(a);
    a.dataset.t = a.textContent;
  });
  pending = []; markPending();
  getSelection().removeAllRanges();
  card.back = editorHtml(ed);
  addItem(child); flash(child.id);
  refresh(); save();
  toast(`🖍 “${snippet.slice(0, 40)}” virou um sub-card (${directCount(card.id)} neste card).`);
  hideBar();
}

function anchorAtCaret() {
  if (!current) return null;
  const s = getSelection(); if (!s.rangeCount) return null;
  const n = s.anchorNode; if (!n || !current.ed.contains(n)) return null;
  return (n.nodeType === 1 ? n : n.parentElement).closest('a[href^="hl:"]');
}

function removeHighlight(childId) {
  const child = getCard(childId); if (!child) return;
  const n = subtree(childId).length;
  if (!confirm(`Remover este destaque e ${n} card(s) (incluindo sub-cards)?`)) return;
  const pel = items[child.parent_id];
  if (pel) {
    const ed = pel.querySelector('.ed.back');
    ed.querySelectorAll(`a[href="${HL}${childId}"]`).forEach(a => a.replaceWith(...a.childNodes));
    getCard(child.parent_id).back = editorHtml(ed);
  } else {
    const p = getCard(child.parent_id);
    const d = document.createElement('div'); d.innerHTML = cleanForView(p.back);
    d.querySelectorAll(`a[href="${HL}${childId}"]`).forEach(a => a.replaceWith(...a.childNodes)); p.back = d.innerHTML;
  }
  if (subtree(childId).some(c => c.id === openId)) openCard(child.parent_id, false);
  deleteSubtree(childId).forEach(i => { if (items[i]) { items[i].remove(); delete items[i]; } });
  refresh(); save();
}

// ---------- comandos de formatação
function remember(changes) {
  if (!current) return;
  Object.assign(sideStyle(current.ed), changes); saveSettings();
}
function exec(cmd, val = null) {
  document.execCommand('styleWithCSS', false, true);
  document.execCommand(cmd, false, val);
}
function wrapSelection(css) {
  const r = current && selectionIn(current.ed);
  if (!r || r.collapsed) return false;
  const span = document.createElement('span'); span.setAttribute('style', css);
  span.appendChild(r.extractContents()); r.insertNode(span);
  const s = getSelection(); const nr = document.createRange(); nr.selectNodeContents(span); s.removeAllRanges(); s.addRange(nr);
  return true;
}
function afterFormat() {
  if (!current) return;
  styleAnchors(current.ed);
  current.ed.dispatchEvent(new Event('input'));
  updateBar(true);
}
const commands = {
  highlight, join: joinPart,
  open() { const a = anchorAtCaret(); if (a) openSheetCard(a.getAttribute('href').slice(HL.length)); },
  unhl() { const a = anchorAtCaret(); if (a) removeHighlight(a.getAttribute('href').slice(HL.length)); },
  bold() { exec('bold'); remember({ bold: document.queryCommandState('bold') }); afterFormat(); },
  italic() { exec('italic'); remember({ italic: document.queryCommandState('italic') }); afterFormat(); },
  underline() { exec('underline'); remember({ underline: document.queryCommandState('underline') }); afterFormat(); },
  strike() { exec('strikeThrough'); remember({ strike: document.queryCommandState('strikeThrough') }); afterFormat(); },
  color() { palette('color'); }, ucolor() { palette('ucolor'); }, size() { palette('size'); },
  clear() {
    exec('removeFormat');
    if (current) remember(defaultStyle(current.ed.dataset.field === 'back'));
    afterFormat();
  },
};
function palette(kind) {
  const p = $('#palette');
  if (!p.classList.contains('hidden') && p.dataset.kind === kind) { p.classList.add('hidden'); return; }
  p.dataset.kind = kind; p.innerHTML = '';
  const add = (html, cls, fn, on) => {
    const b = document.createElement('button'); b.className = cls + (on ? ' on' : ''); b.innerHTML = html;
    b.addEventListener('pointerdown', e => e.preventDefault());
    b.addEventListener('click', () => { fn(); p.classList.add('hidden'); });
    p.appendChild(b);
  };
  if (kind === 'size') {
    const cur = sideStyle(current.ed).size;
    SIZES.forEach(sz => add(String(sz), 's', () => {
      if (wrapSelection(`font-size:${sz}pt`)) { remember({ size: sz }); afterFormat(); }
      else { remember({ size: sz }); toast(`Tamanho ${sz} para o texto novo.`); updateBar(true); }
    }, Math.abs(cur - sz) < .01));
  } else {
    (kind === 'color' ? FONT_COLORS : UNDER_COLORS).forEach(([name, col]) => add('', 'c', () => {
      if (kind === 'color') { exec('foreColor', col); remember({ color: col }); }
      else if (wrapSelection(`text-decoration:underline; text-decoration-color:${col}`)) remember({ underline: true, ucolor: col });
      afterFormat();
    }));
    [...p.children].forEach((b, i) => { b.style.background = (kind === 'color' ? FONT_COLORS : UNDER_COLORS)[i][1]; b.title = (kind === 'color' ? FONT_COLORS : UNDER_COLORS)[i][0]; });
  }
  p.classList.remove('hidden');
}

const bar = $('#fmtbar');
bar.querySelectorAll('button[data-cmd]').forEach(b => {
  b.addEventListener('pointerdown', e => e.preventDefault());    // não tira a seleção do editor
  b.addEventListener('click', () => commands[b.dataset.cmd]());
});
function hideBar() { bar.classList.add('hidden'); $('#palette').classList.add('hidden'); }
function updateBar(force) {
  if (!current) return hideBar();
  const r = selectionIn(current.ed);
  const sel = r && !r.collapsed && rangeText(r);
  const isBack = current.ed.dataset.field === 'back';
  const a = isBack && anchorAtCaret();
  if (!sel && !pending.length && !a && !force) return hideBar();
  if (!sel && !pending.length && !a && force && bar.classList.contains('hidden')) return;
  bar.querySelector('.hl').classList.toggle('hidden', !isBack || (!sel && !pending.length));
  bar.querySelector('.hl').textContent = pending.length ? `🖍 Destacar (${pending.length + (sel ? 1 : 0)} partes)` : '🖍 Destacar';
  bar.querySelector('.join').classList.toggle('hidden', !isBack || !sel);
  bar.querySelector('.open').classList.toggle('hidden', !a || !!sel);
  bar.querySelector('.unhl').classList.toggle('hidden', !a || !!sel);
  const st = sideStyle(current.ed);
  $('#btn-size').textContent = String(st.size);
  $('#sw-color').style.background = st.color;
  bar.classList.remove('hidden');
}
document.addEventListener('selectionchange', () => { if (current && document.activeElement === current.ed) updateBar(); });

// ===================================================================== painel (sub-cards, menus)
let sheetStack = [];
function openSheet(render) { sheetStack.push(render); drawSheet(); }
function drawSheet() {
  const top = sheetStack[sheetStack.length - 1];
  if (!top) return closeSheet();
  $('#sheet-title').innerHTML = ''; $('#sheet-body').innerHTML = ''; $('#sheet-foot').innerHTML = '';
  top();
  $('#sheet-back').classList.toggle('hidden', sheetStack.length < 2);
  $('#sheet').classList.remove('hidden'); $('#sheet-bg').classList.remove('hidden');
  $('#sheet-body').scrollTop = 0;
  hideBar();
}
function closeSheet() { sheetStack = []; $('#sheet').classList.add('hidden'); $('#sheet-bg').classList.add('hidden'); }
function sheetBack() { sheetStack.pop(); if (sheetStack.length) drawSheet(); else closeSheet(); }
$('#sheet-close').onclick = closeSheet; $('#sheet-bg').onclick = closeSheet; $('#sheet-back').onclick = sheetBack;
function footBtn(label, cls, fn) { const b = document.createElement('button'); b.className = cls; b.textContent = label; b.onclick = fn; $('#sheet-foot').appendChild(b); return b; }

// Palavra que identifica o card no caminho (initiatives → problems → thing)
function keyTerm(c) {
  const d = document.createElement('div'); d.innerHTML = cleanForView(c.front);
  const total = d.textContent.trim().length;
  const isU = el => { const s = getComputedStyle(el); return s.textDecorationLine.includes('underline'); };
  document.body.appendChild(d); d.style.position = 'absolute'; d.style.visibility = 'hidden';
  let underlined = null, bold = [], boldLen = 0;
  const w = document.createTreeWalker(d, NodeFilter.SHOW_TEXT); let n;
  while ((n = w.nextNode())) {
    const t = n.data.replace(/\s+/g, ' ').trim(); if (!t) continue;
    const el = n.parentElement; if (el.closest('a[href^="hl:"]')) continue;
    let u = false; for (let e = el; e && e !== d; e = e.parentElement) if (isU(e)) { u = true; break; }
    if (u && !underlined) underlined = t;
    if (parseInt(getComputedStyle(el).fontWeight, 10) >= 600) { bold.push(t); boldLen += t.length; }
  }
  d.remove();
  if (underlined) return underlined.slice(0, 30);
  if (bold.length && boldLen < total * 0.8) return bold[0].slice(0, 30);
  if (c.snippet) return c.snippet.slice(0, 30);
  const words = plain(c.front).split(' ');
  return words.slice(0, 3).join(' ') + (words.length > 3 ? '…' : '');
}
const cardPath = id => pathTo(id).map(keyTerm);

function openSheetCard(id) {
  openSheet(() => {
    const c = getCard(id); if (!c) return sheetBack();
    const p = cardPath(id), d = depth(id);
    const shown = p.length <= 4 ? p : [p[0], '…', ...p.slice(-2)];
    $('#sheet-title').innerHTML = (d ? '' : '🌳 ') + shown.map((t, i) =>
      `<span class="p ${i === shown.length - 1 && d ? 'last' : ''}">${esc(t)}</span>`).join(' <span class="ar">→</span> ');
    const n = directCount(id);
    $('#sheet-body').innerHTML = `
      <div class="side"><span>FRONT</span><span class="badge ${n ? '' : 'zero'}">${n}</span></div>
      <div class="view rich">${cleanForView(c.front) || '<i style="color:#a5afb9">(sem front)</i>'}</div>
      <div class="side"><span>BACK</span></div>
      <div class="view back rich">${cleanForView(c.back) || '<i style="color:#a5afb9">(sem back)</i>'}</div>
      <div class="chips"></div>`;
    styleAnchors($('#sheet-body'));
    $('#sheet-body').querySelectorAll('a[href^="hl:"]').forEach(a => a.addEventListener('click', e => {
      e.preventDefault(); const cid = a.getAttribute('href').slice(HL.length); if (getCard(cid)) openSheetCard(cid);
    }));
    const chips = $('#sheet-body .chips');
    children(id).forEach(k => {
      const b = document.createElement('button'); b.textContent = `↓ “${k.snippet.slice(0, 28)}”`;
      b.onclick = () => openSheetCard(k.id); chips.appendChild(b);
    });
    if (c.parent_id) footBtn('▲ Card pai', 'ghost', () => openSheetCard(c.parent_id));
    footBtn('✎ Editar', 'ghost', () => { closeSheet(); openCard(id); });
  });
}

function cardMenu(id) {
  const c = getCard(id);
  openSheet(() => {
    $('#sheet-title').textContent = plain(c.front, 40) || '(sem front)';
    const m = document.createElement('div'); m.className = 'menu';
    const add = (label, fn) => { const b = document.createElement('button'); b.textContent = label; b.onclick = fn; m.appendChild(b); };
    add('🪟  Ver em painel (sub-cards e caminho até a raiz)', () => { sheetStack = []; openSheetCard(id); });
    if (c.parent_id) add('✕  Remover este destaque e o sub-card', () => { closeSheet(); removeHighlight(id); });
    else add('🗑  Excluir este card raiz e todos os sub-cards', () => { closeSheet(); deleteRoot(); });
    $('#sheet-body').appendChild(m);
  });
}

function deleteRoot() {
  const rid = store.current_root; if (!rid) return;
  if (!confirm(`Excluir este card raiz e seus ${totalCount(rid)} sub-card(s)?`)) return;
  deleteSubtree(rid); saveNow(); showRoot(store.current_root);
}

function showSummary() {
  const rid = store.current_root; if (!rid) return;
  openSheet(() => {
    const tot = totalCount(rid);
    $('#sheet-title').textContent = 'Aprofundamento concluído';
    const rows = [];
    (function walk(c, lvl) {
      rows.push(`<div><span style="padding-left:${lvl * 14}px">${lvl ? '↳ ' : '🌳 '}${esc(plain(c.front, 40) || '(sem front)')}</span>
        <span class="badge ${directCount(c.id) ? '' : 'zero'}">${directCount(c.id)}</span></div>`);
      children(c.id).forEach(k => walk(k, lvl + 1));
    })(getCard(rid), 0);
    $('#sheet-body').innerHTML = `<div class="muted">Trechos destacados a partir do card raiz</div>
      <div class="big-number">${tot}</div>
      <div class="muted">${tot + 1} cards · profundidade máxima: ${maxDepth(rid)} nível(is)</div>
      <div class="tree">${rows.join('')}</div>
      <h4>Ordem de estudo — o último sub-card adicionado é o primeiro</h4>
      <ol class="order">${studyOrder(rid).map(c => `<li>${esc(plain(c.front, 50) || '(sem front)')}</li>`).join('')}</ol>`;
    footBtn('Fechar', 'ghost', closeSheet);
    footBtn('▶ Estudar nesta ordem', 'primary', () => { closeSheet(); startStudy(); });
  });
}

function showMenu() {
  openSheet(() => {
    $('#sheet-title').textContent = 'Menu';
    const m = document.createElement('div'); m.className = 'menu';
    const btn = (label, fn) => { const b = document.createElement('button'); b.innerHTML = label; b.onclick = fn; m.appendChild(b); };
    const chk = (label, key, fn) => {
      const l = document.createElement('label'); l.innerHTML = `<input type="checkbox"> <span>${label}</span>`;
      const i = l.querySelector('input'); i.checked = !!settings[key];
      i.onchange = () => { settings[key] = i.checked; saveSettings(); fn && fn(); }; m.appendChild(l);
    };
    btn('📊  Resumo do aprofundamento', () => { sheetStack = []; showSummary(); });
    btn('📤  Enviar para o Anki (AnkiDroid)…', () => { sheetStack = []; window.showAnki(); });
    m.insertAdjacentHTML('beforeend', '<h4>Texto</h4>');
    chk('Colar sem formatação', 'plainPaste');
    chk('Sombra vermelha nos trechos destacados', 'shadow', () => {
      document.body.classList.toggle('shadow', settings.shadow);
      Object.values(items).forEach(el => {
        const ed = el.querySelector('.ed.back'); styleAnchors(ed); getCard(el.dataset.id).back = editorHtml(ed);
      });
      save();
    });
    btn('↺  Restaurar formatação padrão do texto', () => {
      settings.styles = { front: defaultStyle(false), back: defaultStyle(true) }; saveSettings();
      toast('Formatação padrão restaurada: tamanho 11.5, back em azul Tiffany.');
    });
    m.insertAdjacentHTML('beforeend', '<h4>Visualização dos cards</h4>');
    [['timeline', 'Linha do tempo (vertical)'], ['grid', 'Grade em 2 colunas']].forEach(([v, label]) => {
      const l = document.createElement('label'); l.innerHTML = `<input type="radio" name="view"> <span>${label}</span>`;
      const i = l.querySelector('input'); i.checked = settings.view === v;
      i.onchange = () => { settings.view = v; saveSettings(); const keep = openId; showRoot(store.current_root); if (keep) openCard(keep, false); };
      m.appendChild(l);
    });
    m.insertAdjacentHTML('beforeend', '<h4>Backup (compatível com o programa do Windows)</h4>');
    btn('💾  Exportar backup (.json)', () => exportBackup());
    btn('📥  Importar backup (.json)', () => $('#file-import').click());
    m.insertAdjacentHTML('beforeend', '<h4>Card raiz</h4>');
    btn('🗑  Excluir este card raiz', () => { closeSheet(); deleteRoot(); });
    m.insertAdjacentHTML('beforeend', `<p class="muted" style="padding:10px 6px">Dicas: selecione um trecho do BACK e toque em
      🖍 Destacar. Para estruturas separadas (ex.: <i>got … back</i>), selecione “got”, toque em 🔗 Juntar, selecione
      “back” e destaque. Toque num trecho vermelho e em ↪ Abrir sub-card para ver o caminho.</p>`);
    $('#sheet-body').appendChild(m);
  });
}

function b64FromString(s) { return btoa(unescape(encodeURIComponent(s))); }
function exportBackup() {
  saveNow();
  const json = JSON.stringify(toJSON(), null, 1);
  if (isAndroid()) Android.saveFile('flashcards.json', b64FromString(json), 'application/json');
  else { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([json], { type: 'application/json' })); a.download = 'flashcards.json'; a.click(); }
}
$('#file-import').addEventListener('change', async e => {
  const f = e.target.files[0]; e.target.value = ''; if (!f) return;
  try {
    const s = fromJSON(JSON.parse(await f.text()));
    if (store.roots.length && !confirm('Substituir todos os cards atuais pelos do arquivo?')) return;
    store = s; saveNow(); closeSheet(); showRoot(store.current_root); toast('Backup importado.');
  } catch (err) { alert('Não foi possível importar: ' + err.message); }
});

// ===================================================================== estudo
let study = { list: [], i: 0, flipped: false };
function startStudy() {
  const rid = store.current_root; if (!rid) return;
  saveNow(); hideBar(); if (document.activeElement) document.activeElement.blur();
  study = { list: studyOrder(rid), i: 0, flipped: false };
  $('#study').classList.remove('hidden'); drawStudy();
}
function drawStudy() {
  const c = study.list[study.i], n = study.list.length;
  $('#study-progress').textContent = `${study.i + 1} / ${n}`;
  $('#study-fill').style.width = ((study.i + 1) / n * 100) + '%';
  $('#study-origin').textContent = depth(c.id) ? cardPath(c.id).join(' → ') : '🌳 Card raiz';
  $('#study-front').innerHTML = cleanForView(c.front) || '<i style="color:#a5afb9">(sem front)</i>';
  $('#study-back').innerHTML = cleanForView(c.back) || '<i style="color:#a5afb9">(sem back)</i>';
  styleAnchors($('#study-back'));
  $('#study-back-wrap').classList.toggle('hidden', !study.flipped);
  $('#study-hint').classList.toggle('hidden', study.flipped);
  $('#study-flip').textContent = study.flipped ? 'Esconder resposta' : 'Virar';
  $('#study-prev').disabled = study.i === 0;
  $('#study-next').textContent = study.i === n - 1 ? '✔' : '→';
  $('#study-card').style.setProperty('--zoom', settings.zoom || 0);
}
function studyNext() {
  if (study.i < study.list.length - 1) { study.i++; study.flipped = false; drawStudy(); }
  else { exitStudy(); toast('Estudo concluído! 🎉'); }
}
function studyPrev() { if (study.i > 0) { study.i--; study.flipped = false; drawStudy(); } }
function studyFlip() { study.flipped = !study.flipped; drawStudy(); }
function exitStudy() { $('#study').classList.add('hidden'); }
$('#study-card').onclick = e => { if (!(e.target.closest && e.target.closest('a'))) studyFlip(); };
$('#study-flip').onclick = studyFlip; $('#study-next').onclick = studyNext; $('#study-prev').onclick = studyPrev;
$('#study-exit').onclick = exitStudy;
$('#z-plus').onclick = () => { settings.zoom = Math.min(8, (settings.zoom || 0) + 1); saveSettings(); drawStudy(); };
$('#z-minus').onclick = () => { settings.zoom = Math.max(-3, (settings.zoom || 0) - 1); saveSettings(); drawStudy(); };
// deslizar para o lado no estudo
(() => {
  let x0 = null;
  $('#study-card').addEventListener('touchstart', e => { x0 = e.touches[0].clientX; }, { passive: true });
  $('#study-card').addEventListener('touchend', e => {
    if (x0 === null) return; const dx = e.changedTouches[0].clientX - x0; x0 = null;
    if (Math.abs(dx) > 70) { (dx < 0 ? studyNext : studyPrev)(); }
  });
})();

// ===================================================================== topo e botão Voltar
function newRoot() {
  const c = createCard(null);
  showRoot(c.id);
  setTimeout(() => { const ed = items[c.id] && items[c.id].querySelector('.ed.front'); if (ed) ed.focus(); }, 60);
}
$('#btn-new').onclick = newRoot; $('#btn-first').onclick = newRoot;
$('#btn-study').onclick = startStudy; $('#btn-menu').onclick = showMenu;
$('#deck').onchange = e => showRoot(e.target.value);

window.appBack = () => {
  if (!$('#palette').classList.contains('hidden')) { $('#palette').classList.add('hidden'); return true; }
  if (pending.length) { clearPending(); toast('Junção cancelada.'); return true; }
  if (!$('#sheet').classList.contains('hidden')) { sheetBack(); return true; }
  if (!$('#study').classList.contains('hidden')) { exitStudy(); return true; }
  if (!bar.classList.contains('hidden')) { hideBar(); if (document.activeElement) document.activeElement.blur(); return true; }
  return false;
};
document.addEventListener('keydown', e => { if (e.key === 'Escape' && window.appBack()) e.preventDefault(); });
document.addEventListener('visibilitychange', () => { if (document.hidden) saveNow(); });

// expõe para o módulo do Anki
window.Montador = { get store() { return store; }, settings, saveSettings, saveNow, studyOrder, getCard, depth, cleanForView,
  plain, openSheet, closeSheet, footBtn, toast, isAndroid, esc, subtree, totalCount, get sheetStack() { return sheetStack; },
  set sheetStack(v) { sheetStack = v; } };

load();
showRoot(store.current_root);
