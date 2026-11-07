/* Envio para o Anki no Android: gera um Pacote de Baralho (.apkg) e abre no AnkiDroid.
 * Mesmas regras do programa do Windows: cores e formatação mantidas, tamanhos relativos ao texto normal,
 * um único sublinhado vermelho nos trechos destacados, ordem dos sub-cards até o card raiz.
 */
'use strict';
(() => {
  const M = window.Montador;
  const RED = '#e11d2e', BASE_PT = 11.5;
  const KEEP = new Set(['color', 'background-color', 'font-weight', 'font-style', 'text-decoration', 'text-decoration-line',
    'text-decoration-color', 'font-size']);
  const BASE91 = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!#$%&()*+,-./:;<=>?@[]^_`{|}~';

  // ---------------------------------------------------------------- HTML → Anki
  function relSize(v) {
    const m = String(v).replace(/\s/g, '').match(/^([\d.]+)(pt|px)$/);
    if (!m) return null;
    const pt = parseFloat(m[1]) * (m[2] === 'px' ? 0.75 : 1);
    const em = Math.round(pt / BASE_PT * 1000) / 1000;
    return Math.abs(em - 1) < 0.01 ? null : `${em}em`;
  }
  function cleanStyle(style, inHl) {
    const out = [];
    String(style || '').split(';').forEach(part => {
      const i = part.indexOf(':'); if (i < 0) return;
      const k = part.slice(0, i).trim().toLowerCase(); let v = part.slice(i + 1).trim();
      if (!KEEP.has(k) || !v) return;
      if (inHl && (k.startsWith('text-decoration') || k === 'color' || k === 'background-color')) return;
      if (k === 'font-size') { v = relSize(v); if (!v) return; }
      if (k === 'color' || k === 'text-decoration-color') v = v.replace(/\s/g, '');
      out.push(`${k}:${v}`);
    });
    return out;
  }
  const TAG_STYLE = { b: 'font-weight:700', strong: 'font-weight:700', i: 'font-style:italic', em: 'font-style:italic',
    u: 'text-decoration:underline', s: 'text-decoration:line-through', strike: 'text-decoration:line-through' };
  function hlStyle(shadow) {
    return `color:${RED}; text-decoration:underline; text-decoration-color:${RED}; text-decoration-thickness:0.07em; ` +
      `text-underline-offset:0.12em${shadow ? '; background-color:rgba(225,29,46,0.15)' : ''}`;
  }
  function walk(node, ctx) {
    let html = '';
    node.childNodes.forEach(n => {
      if (n.nodeType === 3) {
        const t = M.esc(n.data.replace(/​/g, ''));
        if (!t) return;
        html += ctx.inHl && !ctx.decorated ? `<span style="${hlStyle(ctx.shadow)}">${t}</span>` : t;
        return;
      }
      if (n.nodeType !== 1) return;
      const tag = n.tagName.toLowerCase();
      if (['style', 'script', 'meta', 'title', 'head'].includes(tag)) return;
      if (tag === 'br') { html += '<br>'; return; }
      if (tag === 'a' && (n.getAttribute('href') || '').startsWith('hl:')) {
        html += `<span class="hl" style="color:${RED}">${walk(n, { ...ctx, inHl: true, decorated: false })}</span>`;
        return;
      }
      if (['p', 'div', 'ul', 'ol', 'li'].includes(tag)) {
        const out = tag === 'p' ? 'div' : tag;
        const st = cleanStyle(n.getAttribute('style'), ctx.inHl).join('; ');
        html += `<${out}${st ? ` style="${st}"` : ''}>${walk(n, ctx)}</${out}>`;
        return;
      }
      if (['span', 'b', 'strong', 'i', 'em', 'u', 's', 'strike', 'font', 'sub', 'sup'].includes(tag)) {
        const st = cleanStyle(n.getAttribute('style'), ctx.inHl);
        if (TAG_STYLE[tag] && !(ctx.inHl && tag in { u: 1, s: 1, strike: 1 })) st.push(TAG_STYLE[tag]);
        if (tag === 'font' && n.getAttribute('color') && !ctx.inHl) st.push(`color:${n.getAttribute('color')}`);
        let inner;
        if (ctx.inHl && !ctx.decorated) { st.push(hlStyle(ctx.shadow)); inner = walk(n, { ...ctx, decorated: true }); }
        else inner = walk(n, ctx);
        html += st.length ? `<span style="${st.join('; ')}">${inner}</span>` : inner;
        return;
      }
      html += walk(n, ctx);
    });
    return html;
  }
  function toAnki(html, shadow) {
    const doc = new DOMParser().parseFromString(M.cleanForView(html || ''), 'text/html');
    return walk(doc.body, { inHl: false, decorated: false, shadow }).replace(/<div><br><\/div>/g, '<br>').trim();
  }

  // ---------------------------------------------------------------- .apkg
  function guidFor(cardId) {                      // igual ao genanki.guid_for("montador-v2", id) do Windows
    const h = window.sha256(`montador-v2__${cardId}`);
    let n = 0n; for (let i = 0; i < 8; i++) n = (n << 8n) + BigInt(h[i]);
    let s = ''; while (n > 0n) { s = BASE91[Number(n % 91n)] + s; n /= 91n; }
    return s;
  }
  function deckId(name) {
    const h = window.sha256('deck__' + name);
    return (1 << 30) + ((h[0] << 20) | (h[1] << 12) | (h[2] << 4) | (h[3] >> 4));
  }
  function css(basePx) {
    return `.card { font-family: "Segoe UI", Arial, sans-serif; font-size: ${basePx}px; color: #1f2933;\n` +
      `  background: #ffffff; text-align: center; line-height: 1.4; }\n.verso { color: #0ABAB5; }\n.hl { color: #e11d2e; }\n`;
  }
  function loadScript(src) {
    return new Promise((ok, fail) => { const s = document.createElement('script'); s.src = src; s.onload = ok; s.onerror = () => fail(new Error('não carregou ' + src)); document.head.appendChild(s); });
  }
  let SQL = null;
  async function sqlReady() {
    if (SQL) return SQL;
    await loadScript('vendor/sql-wasm.js'); await loadScript('vendor/sql-wasm-b64.js'); await loadScript('vendor/jszip.min.js');
    const bin = Uint8Array.from(atob(window.SQL_WASM_B64), c => c.charCodeAt(0));
    SQL = await window.initSqlJs({ wasmBinary: bin });
    return SQL;
  }
  async function buildApkg(rootId, deckName, subFirst, basePx, shadow) {
    const SQLm = await sqlReady();
    const db = new SQLm.Database();
    db.run(ANKI_SCHEMA);
    const now = Math.floor(Date.now() / 1000), did = deckId(deckName);
    const model = JSON.parse(JSON.stringify(ANKI_MODEL));
    model.css = css(basePx); model.mod = now; model.did = did;
    model.tmpls[0].qfmt = ANKI_FRONT_TMPL; model.tmpls[0].afmt = ANKI_BACK_TMPL;
    const deck = JSON.parse(JSON.stringify(ANKI_DECK));
    Object.assign(deck, { id: did, name: deckName, mod: now });
    const decks = { 1: ANKI_DEFAULT_DECK, [did]: deck };
    db.run('INSERT INTO col VALUES(null,?,?,?,11,0,0,0,?,?,?,?,?)',
      [1411124400, Date.now(), Date.now(), JSON.stringify(ANKI_CONF), JSON.stringify({ [ANKI_MODEL_ID]: model }),
        JSON.stringify(decks), JSON.stringify(ANKI_DCONF), '{}']);
    let order = M.studyOrder(rootId);
    if (!subFirst) order = order.reverse();
    let id = Date.now();
    order.forEach((c, i) => {
      const front = toAnki(c.front, shadow), back = toAnki(c.back, shadow);
      const nid = id++, cid = id++;
      db.run('INSERT INTO notes VALUES(?,?,?,?,?,?,?,?,?,?,?)',
        [nid, guidFor(c.id), ANKI_MODEL_ID, now, -1, ' montador-flashcards ', front + '\x1f' + back, M.plain(c.front), 0, 0, '']);
      db.run('INSERT INTO cards VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
        [cid, nid, did, 0, now, -1, 0, 0, i + 1, 0, 0, 0, 0, 0, 0, 0, 0, '']);
    });
    const bytes = db.export(); db.close();
    const zip = new window.JSZip();
    zip.file('collection.anki2', bytes); zip.file('media', '{}');
    return { b64: await zip.generateAsync({ type: 'base64' }), count: order.length };
  }
  window.MontadorAnki = { toAnki, buildApkg, guidFor };

  // ---------------------------------------------------------------- janela "Enviar para o Anki"
  window.showAnki = function () {
    const s = M.settings, store = M.store, rid = store.current_root;
    if (!rid) return;
    M.saveNow();
    const title = M.plain(M.getCard(rid).front, 50) || '(sem título)';
    M.openSheet(() => {
      document.querySelector('#sheet-title').textContent = 'Enviar para o Anki';
      const body = document.querySelector('#sheet-body');
      const n = M.totalCount(rid) + 1;
      const recent = (s.recentDecks || []).map(d => `<option value="${M.esc(d)}">`).join('');
      body.innerHTML = `
        <p><b>${n} card(s)</b> do card raiz “${M.esc(title)}”, com as mesmas cores e formatação.</p>
        <label class="field">Baralho no Anki (o nome de um baralho que já existe faz os cards entrarem nele)
          <input id="ak-deck" list="ak-recent" value="${M.esc(s.ankiDeck || ('Montador::' + title.replace(/::/g, ' ')))}">
          <datalist id="ak-recent">${recent}</datalist></label>
        <label class="field">Tamanho do texto normal no Anki (px) — use o mesmo dos seus outros cards
          <input id="ak-size" type="number" min="10" max="120" value="${s.ankiBasePx || 20}"></label>
        <div class="menu">
          <label><input type="radio" name="ak-order" value="1" ${s.subFirst !== false ? 'checked' : ''}>
            <span>Sub-cards primeiro: do último sub-card até o card raiz</span></label>
          <label><input type="radio" name="ak-order" value="0" ${s.subFirst === false ? 'checked' : ''}>
            <span>Card raiz primeiro, depois os sub-cards</span></label>
        </div>
        <p class="muted">“Abrir no AnkiDroid” importa o baralho direto. Importar de novo atualiza os mesmos cards.
          Também dá para compartilhar o arquivo .apkg (Drive, e-mail, Anki no computador).</p>`;
      const opts = () => {
        const deck = document.querySelector('#ak-deck').value.trim() || 'Montador';
        const size = Math.max(10, Math.min(120, parseInt(document.querySelector('#ak-size').value, 10) || 20));
        const subFirst = document.querySelector('input[name="ak-order"]:checked').value === '1';
        Object.assign(s, { ankiDeck: deck, ankiBasePx: size, subFirst,
          recentDecks: [deck, ...(s.recentDecks || []).filter(d => d !== deck)].slice(0, 10) });
        M.saveSettings();
        return { deck, size, subFirst };
      };
      const run = async mode => {
        const o = opts();
        M.toast('Gerando o pacote do Anki…', 1500);
        try {
          const { b64, count } = await buildApkg(rid, o.deck, o.subFirst, o.size, !!s.shadow);
          const name = (o.deck.split('::').pop().replace(/[^\w\- ]+/g, '').trim() || 'flashcards') + '.apkg';
          if (M.isAndroid()) {
            if (mode === 'save') Android.saveFile(name, b64, 'application/apkg');
            else Android.shareFile(name, b64, 'application/apkg', mode);
          } else {
            const a = document.createElement('a'); a.href = 'data:application/octet-stream;base64,' + b64; a.download = name; a.click();
          }
          M.toast(`${count} card(s) no pacote “${name}”.`);
        } catch (e) { alert('Não foi possível gerar o pacote: ' + e.message); }
      };
      M.footBtn('Salvar arquivo', 'ghost', () => run('save'));
      M.footBtn('Compartilhar…', 'ghost', () => run('send'));
      M.footBtn('Abrir no AnkiDroid', 'primary', () => run('view'));
    });
  };
})();
