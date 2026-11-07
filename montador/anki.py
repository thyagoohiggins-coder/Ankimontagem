"""Envio dos cards para o Anki, mantendo cores e formatação.

Dois caminhos:
- AnkiConnect (complemento do Anki, código 2055492159): envia direto para o Anki aberto.
- Arquivo .txt (HTML separado por tabulação) para importar em Arquivo → Importar.

A ordem de envio define a ordem dos cards novos no Anki.
"""
from __future__ import annotations

import html
import json
import re
import urllib.error
import urllib.request
from html.parser import HTMLParser

from .model import HL_PREFIX, Card, Store

ANKI_URL = "http://127.0.0.1:8765"
MODEL = "Montador de Flashcards"
FIELDS = ["Frente", "Verso"]
OLD_FIELDS = ["Origem", "Nivel"]   # usados até a 2.4; removidos do tipo de nota
TIFFANY = "#0ABAB5"
HL_RED = "#e11d2e"

CSS = """.card { font-family: "Segoe UI", Arial, sans-serif; font-size: 11.5pt; color: #1f2933;
  background: #ffffff; text-align: left; line-height: 1.45; }
.verso { color: #0ABAB5; }
.origem { color: #8a96a3; font-size: 13px; margin-bottom: 8px; }
.origem b { color: #e11d2e; }
.hl { color: #e11d2e; }
"""
FRONT_TMPL = """<div class="frente">{{Frente}}</div>"""
BACK_TMPL = """{{FrontSide}}
<hr id="answer">
<div class="verso">{{Verso}}</div>"""

_KEEP_STYLES = {"color", "background-color", "font-weight", "font-style", "text-decoration",
                "text-decoration-color", "font-size", "text-decoration-line", "text-underline-offset"}
_BLOCK = {"p": "div", "li": "li", "ul": "ul", "ol": "ol"}
_INLINE = {"span", "b", "strong", "i", "em", "u", "s", "sub", "sup"}


def _clean_style(style: str, drop_bg: bool) -> str:
    out = []
    for part in style.split(";"):
        if ":" not in part:
            continue
        k, v = part.split(":", 1)
        k, v = k.strip().lower(), v.strip()
        if k not in _KEEP_STYLES or not v:
            continue
        if drop_bg and k == "background-color":
            continue
        if k == "font-size" and not re.fullmatch(r"[\d.]+(pt|px)", v.replace(" ", "")):
            continue   # tamanhos relativos (x-large, em…) não seriam iguais aos do programa
        out.append(f"{k}:{v}")
    return "; ".join(out)


class _QtHtmlToAnki(HTMLParser):
    """Converte o HTML do Qt (documento completo) num fragmento limpo para o Anki."""

    def __init__(self, shadow: bool) -> None:
        super().__init__(convert_charrefs=True)
        self.shadow = shadow
        self.out: list[str] = []
        self.stack: list[str] = []
        self.in_body = False
        self.skip = 0
        self.empty_par = False
        self.hl_depth = 0          # dentro de um trecho destacado: um único sublinhado vermelho
        self.hl_open: list[list] = []

    def _hl_style(self) -> str:
        bg = "; background-color:rgba(225,29,46,0.15)" if self.shadow else ""
        return (f"color:{HL_RED}; text-decoration:underline; text-decoration-color:{HL_RED}; "
                f"text-decoration-thickness:1.5px; text-underline-offset:2px{bg}")

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("head", "style", "title"):
            self.skip += 1
            return
        if tag == "body":
            self.in_body = True
            return
        if not self.in_body or self.skip:
            return
        style = a.get("style") or ""
        if tag == "br":
            self.out.append("<br>")
            return
        if tag == "a":
            href = a.get("href") or ""
            if href.startswith(HL_PREFIX):
                # O sublinhado vai no MESMO elemento que tem o texto (e o tamanho da fonte), com todo o estilo
                # inline: fica colado à palavra, fino, e não depende do CSS do tipo de nota.
                self.hl_open.append([len(self.out), False])
                self.out.append('<span class="hl">')
                self.hl_depth += 1
                self.stack.append("/hl")
                return
            else:
                self.out.append(f'<a href="{html.escape(href)}">')
            self.stack.append("span" if href.startswith(HL_PREFIX) else "a")
            return
        if tag in _BLOCK:
            self.empty_par = "-qt-paragraph-type:empty" in style
            out_tag = _BLOCK[tag]
            st = _clean_style(style, False)
            self.out.append(f'<{out_tag} style="{st}">' if st else f"<{out_tag}>")
            self.stack.append(out_tag)
            return
        if tag in _INLINE:
            st = _clean_style(style, False)
            if self.hl_depth:
                st = "; ".join([x for x in st.split("; ")
                                if x and not x.startswith(("text-decoration", "color", "background-color",
                                                           "text-underline"))] + [self._hl_style()])
                self.hl_open[-1][1] = True
            self.out.append(f'<span style="{st}">' if st else "<span>")
            self.stack.append("span")

    def handle_endtag(self, tag):
        if tag in ("head", "style", "title"):
            self.skip = max(0, self.skip - 1)
            return
        if tag == "body":
            self.in_body = False
            return
        if not self.in_body or self.skip:
            return
        if tag in _BLOCK or tag in _INLINE or tag == "a":
            if self.stack:
                t = self.stack.pop()
                if t == "/hl":
                    self.hl_depth -= 1
                    idx, has_inner = self.hl_open.pop()
                    if not has_inner:   # texto direto dentro do destaque: o estilo vai no próprio span
                        self.out[idx] = f'<span class="hl" style="{self._hl_style()}">'
                    t = "span"
                self.out.append(f"</{t}>")

    def handle_data(self, data):
        if self.in_body and not self.skip:
            self.out.append(html.escape(data, quote=False))


def qt_html_to_anki(qt_html: str, shadow: bool = False) -> str:
    if not qt_html:
        return ""
    p = _QtHtmlToAnki(shadow)
    p.in_body = "<body" not in qt_html.lower()     # front recém-criado é só texto
    p.feed(qt_html)
    p.close()
    frag = "".join(p.out)
    frag = re.sub(r"<span>(.*?)</span>", r"\1", frag, flags=re.S)
    frag = frag.replace("<div><br></div>", "<br>")
    return frag.strip()


def ordered_cards(store: Store, root_id: str, subcards_first: bool) -> list[Card]:
    order = store.study_order(root_id)          # último sub-card → raiz
    return order if subcards_first else list(reversed(order))


def note_fields(store: Store, card: Card, shadow: bool) -> dict:
    return {
        "Frente": qt_html_to_anki(card.front, shadow),
        "Verso": qt_html_to_anki(card.back, shadow),
    }


# ====================================================================== AnkiConnect
class AnkiError(Exception):
    pass


def invoke(action: str, url: str = ANKI_URL, timeout: float = 8.0, **params):
    body = json.dumps({"action": action, "version": 6, "params": params}).encode("utf-8")
    req = urllib.request.Request(url, body, {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            resp = json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as exc:
        raise AnkiError(
            "Não foi possível conectar ao Anki. Abra o Anki e confira se o complemento "
            "AnkiConnect (código 2055492159) está instalado.") from exc
    if not isinstance(resp, dict) or "result" not in resp:
        raise AnkiError("Resposta inesperada do AnkiConnect.")
    if resp.get("error"):
        raise AnkiError(str(resp["error"]))
    return resp["result"]


def ensure_model(url: str = ANKI_URL) -> None:
    if MODEL in invoke("modelNames", url):
        # mantém o visual do tipo de nota em dia (ex.: sem “Nível” no front)
        invoke("updateModelTemplates", url,
               model={"name": MODEL, "templates": {"Cartão 1": {"Front": FRONT_TMPL, "Back": BACK_TMPL}}})
        invoke("updateModelStyling", url, model={"name": MODEL, "css": CSS})
        try:  # tira os campos antigos (Origem, Nível); AnkiConnect antigo pode não ter essa ação
            existing = invoke("modelFieldNames", url, modelName=MODEL)
            for f in OLD_FIELDS:
                if f in existing:
                    invoke("modelFieldRemove", url, modelName=MODEL, fieldName=f)
        except AnkiError:
            pass
        return
    invoke("createModel", url, modelName=MODEL, inOrderFields=FIELDS, css=CSS,
           cardTemplates=[{"Name": "Cartão 1", "Front": FRONT_TMPL, "Back": BACK_TMPL}])


def send_to_anki(store: Store, root_id: str, deck: str, subcards_first: bool, shadow: bool,
                 url: str = ANKI_URL) -> tuple[int, int]:
    """Envia os cards da árvore. Cards já enviados são atualizados. Retorna (novos, atualizados)."""
    ensure_model(url)
    invoke("createDeck", url, deck=deck)
    cards = ordered_cards(store, root_id, subcards_first)

    known = [c.anki_note_id for c in cards if c.anki_note_id]
    alive = set()
    if known:
        info = invoke("notesInfo", url, notes=known)
        alive = {n["noteId"] for n in info if n and n.get("noteId")}

    updated = 0
    new_cards: list[Card] = []
    for c in cards:
        if c.anki_note_id in alive:
            invoke("updateNoteFields", url, note={"id": c.anki_note_id, "fields": note_fields(store, c, shadow)})
            invoke("changeDeck", url, cards=invoke("findCards", url, query=f"nid:{c.anki_note_id}"), deck=deck)
            updated += 1
        else:
            new_cards.append(c)

    if new_cards:
        notes = [{
            "deckName": deck, "modelName": MODEL, "fields": note_fields(store, c, shadow),
            "tags": ["montador-flashcards"],
            "options": {"allowDuplicate": True},
        } for c in new_cards]
        ids = invoke("addNotes", url, notes=notes)      # na ordem da lista = ordem dos cards novos
        for c, nid in zip(new_cards, ids):
            c.anki_note_id = nid
    return len(new_cards), updated


# ====================================================================== arquivo
def export_txt(store: Store, root_id: str, deck: str, subcards_first: bool, shadow: bool, path: str) -> int:
    """Arquivo para Arquivo → Importar no Anki (tipo de nota Básico: Frente, Verso)."""
    def cell(s: str) -> str:
        return s.replace("\t", " ").replace("\r", "").replace("\n", " ")

    lines = ["#separator:tab", "#html:true", f"#deck:{deck}", "#tags column:3"]
    cards = ordered_cards(store, root_id, subcards_first)
    for c in cards:
        f = note_fields(store, c, shadow)
        front = f["Frente"]
        back = f'<div style="color:{TIFFANY}">{f["Verso"]}</div>'
        lines.append("\t".join([cell(front), cell(back), "montador-flashcards"]))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return len(cards)


# ====================================================================== pacote .apkg
MODEL_ID = 1731000917      # fixo: reimportar atualiza o mesmo tipo de nota (novo na 2.5: só Frente e Verso)


def _deck_id(name: str) -> int:
    import hashlib
    return (1 << 30) + int(hashlib.md5(name.encode("utf-8")).hexdigest()[:7], 16)


def export_apkg(store: Store, root_id: str, deck: str, subcards_first: bool, shadow: bool, path: str) -> int:
    """Pacote de Baralho do Anki (.apkg): abrir com dois cliques importa baralho, tipo de nota, cores e ordem.
    Reimportar o mesmo card atualiza a nota em vez de duplicar (mesmo GUID)."""
    import genanki

    model = genanki.Model(
        MODEL_ID, MODEL,
        fields=[{"name": f} for f in FIELDS],
        templates=[{"name": "Cartão 1", "qfmt": FRONT_TMPL, "afmt": BACK_TMPL}],
        css=CSS)
    deck_id = _deck_id(deck)
    try:   # baralho que já existe no Anki: usa o id real para os cards entrarem nele
        deck_id = int(invoke("deckNamesAndIds", timeout=1.5).get(deck, deck_id))
    except (AnkiError, AttributeError, TypeError, ValueError):
        pass   # sem AnkiConnect: o Anki junta pelo nome do baralho
    d = genanki.Deck(deck_id, deck)
    cards = ordered_cards(store, root_id, subcards_first)
    for i, c in enumerate(cards, 1):
        f = note_fields(store, c, shadow)
        note = genanki.Note(model=model, fields=[f[k] for k in FIELDS], tags=["montador-flashcards"],
                            guid=genanki.guid_for("montador-v2", c.id), due=i)
        d.add_note(note)
    genanki.Package(d).write_to_file(path)
    return len(cards)
