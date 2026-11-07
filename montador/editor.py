"""Editor de texto rico: formatação, colar sem formatação, destaques e menu de contexto."""
from __future__ import annotations

from PySide6.QtCore import QPoint, QSize, Qt, Signal
from PySide6.QtGui import (QAction, QColor, QFont, QIcon, QKeySequence, QPainter, QPalette, QPixmap,
                           QTextCharFormat, QTextCursor, QTextFormat)
from PySide6.QtWidgets import QColorDialog, QFrame, QHBoxLayout, QMenu, QTextEdit, QToolButton, QWidget

from . import settings
from .model import HL_PREFIX

TIFFANY = "#0ABAB5"
FRONT_COLOR = "#1f2933"
HL_RED = "#e11d2e"
HL_BG = QColor(225, 29, 46, 38)

FONT_COLORS = [
    ("Azul Tiffany", TIFFANY), ("Preto", FRONT_COLOR), ("Azul", "#2563eb"), ("Verde", "#16a34a"),
    ("Laranja", "#ea580c"), ("Roxo", "#7c3aed"), ("Rosa", "#db2777"), ("Cinza", "#6b7785"),
]
FONT_SIZES = [9, 10, 11, 11.5, 12, 13, 14, 16, 18, 20, 24, 28, 32]
BASE_SIZE = 11.5

UNDERLINE_COLORS = [
    ("Amarelo", "#facc15"), ("Laranja", "#f97316"), ("Verde", "#22c55e"), ("Azul", "#3b82f6"),
    ("Roxo", "#a855f7"), ("Rosa", "#ec4899"), ("Azul Tiffany", TIFFANY), ("Preto", "#111827"),
]


def default_font() -> QFont:
    f = QFont("Segoe UI")
    f.setStyleHint(QFont.SansSerif)
    f.setPointSizeF(BASE_SIZE)
    return f


def swatch(color: str, underline: bool = False) -> QIcon:
    pm = QPixmap(16, 16)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(color))
    if underline:
        p.drawRoundedRect(1, 11, 14, 4, 2, 2)
        p.setPen(QColor("#374151"))
        f = QFont(); f.setPixelSize(11); f.setBold(True); p.setFont(f)
        p.drawText(pm.rect().adjusted(0, -4, 0, 0), Qt.AlignCenter, "U")
    else:
        p.drawRoundedRect(1, 1, 14, 14, 4, 4)
    p.end()
    return QIcon(pm)


def color_menu(parent: QWidget, palette: list[tuple[str, str]], on_pick, underline: bool, title: str) -> QMenu:
    m = QMenu(title, parent)
    for name, col in palette:
        a = m.addAction(swatch(col, underline), name)
        a.triggered.connect(lambda _=False, c=col: on_pick(QColor(c)))
    m.addSeparator()

    def custom():
        c = QColorDialog.getColor(parent=parent.window(), title=title)
        if c.isValid():
            on_pick(c)
    m.addAction("Outra cor…").triggered.connect(custom)
    return m


class RichEditor(QTextEdit):
    """QTextEdit que cresce com o conteúdo, com atalhos e menu de contexto em português."""

    highlightRequested = Signal(object)      # editor
    openChildRequested = Signal(str, QPoint)  # id do sub-card, posição na tela
    removeHighlightRequested = Signal(str)   # id do sub-card
    formatSelection = Signal(object)         # editor com seleção (mostrar barra)
    pendingChanged = Signal(object)          # partes de uma estrutura separada (ex.: got … back)
    joinRequested = Signal(object)
    focusLost = Signal(object)

    plain_paste_default = True               # configuração global "Colar sem formatação"
    hl_shadow = False                        # sombra vermelha atrás dos trechos destacados (opcional)

    # Última formatação escolhida, separada para FRONT (False) e BACK (True).
    # Vira o padrão do texto novo e é lembrada entre sessões.
    styles: dict[bool, dict] = {}

    @staticmethod
    def default_style(is_back: bool) -> dict:
        return {"size": BASE_SIZE, "bold": False, "italic": False, "underline": False, "strike": False,
                "color": TIFFANY if is_back else FRONT_COLOR, "ucolor": ""}

    @classmethod
    def load_styles(cls) -> None:
        for side, key in ((False, "style/front"), (True, "style/back")):
            st = cls.default_style(side)
            saved = settings.get_json(key, {})
            if isinstance(saved, dict):
                st.update({k: v for k, v in saved.items() if k in st})
            cls.styles[side] = st

    @classmethod
    def reset_styles(cls) -> None:
        for side, key in ((False, "style/front"), (True, "style/back")):
            cls.styles[side] = cls.default_style(side)
            settings.set_json(key, cls.styles[side])

    @property
    def style(self) -> dict:
        if self.is_back not in RichEditor.styles:
            RichEditor.styles[self.is_back] = RichEditor.default_style(self.is_back)
        return RichEditor.styles[self.is_back]

    def remember(self, **changes) -> None:
        self.style.update(changes)
        settings.set_json("style/back" if self.is_back else "style/front", self.style)

    def style_format(self) -> QTextCharFormat:
        st = self.style
        f = QTextCharFormat()
        f.setForeground(QColor(st["color"]))
        f.setFontPointSize(float(st["size"]))
        f.setFontWeight(QFont.Bold if st["bold"] else QFont.Normal)
        f.setFontItalic(bool(st["italic"]))
        f.setFontUnderline(bool(st["underline"]))
        f.setFontStrikeOut(bool(st["strike"]))
        if st["underline"] and st["ucolor"]:
            f.setUnderlineColor(QColor(st["ucolor"]))
        return f

    def __init__(self, is_back: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.is_back = is_back
        self.base_color = QColor(TIFFANY if is_back else FRONT_COLOR)
        self._force_plain = False
        self.pending: list[QTextCursor] = []   # partes já escolhidas de uma estrutura separada
        self.setAcceptRichText(True)
        self.setTabChangesFocus(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setObjectName("backEditor" if is_back else "frontEditor")
        self.document().setDefaultFont(default_font())
        self.document().setDocumentMargin(10)
        pal = self.palette()
        pal.setColor(QPalette.Text, self.base_color)
        pal.setColor(QPalette.PlaceholderText, QColor("#9aa5b1"))
        self.setPalette(pal)
        self._adjust_typing_format()
        self.setPlaceholderText(
            "Resposta / explicação…   Selecione um trecho que você não conhece e aperte Ctrl+D"
            if is_back else "Pergunta / conceito…")
        self.setMouseTracking(True)
        self.document().contentsChanged.connect(self._fit_height)
        self.selectionChanged.connect(self._on_selection)
        self.cursorPositionChanged.connect(self._adjust_typing_format)
        self._fit_height()

    # ---------- conteúdo ----------
    def set_content(self, html: str) -> None:
        self.blockSignals(True)
        if html:
            self.setHtml(html)
            apply_highlight_style(self.document(), RichEditor.hl_shadow)
            self.document().clearUndoRedoStacks()
        else:
            self.clear()
        self.document().setDefaultFont(default_font())
        self.blockSignals(False)
        self._adjust_typing_format()
        self._fit_height()

    _STYLE_PROPS = (QTextFormat.ForegroundBrush, QTextFormat.FontPointSize, QTextFormat.FontWeight,
                    QTextFormat.FontItalic, QTextFormat.FontUnderline, QTextFormat.TextUnderlineStyle,
                    QTextFormat.FontStrikeOut, QTextFormat.TextUnderlineColor)

    def _adjust_typing_format(self) -> None:
        """Define a formatação do próximo texto digitado.

        - Depois de um trecho destacado, o texto novo não fica vermelho.
        - Em card vazio ou parágrafo vazio, usa a última formatação escolhida.
        - Dentro de um texto existente, segue o texto ao redor; só completa o que faltar.
        """
        cur = self.textCursor()
        if cur.hasSelection():
            return
        fmt = self.currentCharFormat()
        if fmt.anchorHref().startswith(HL_PREFIX) or cur.block().length() <= 1:
            self.setCurrentCharFormat(self.style_format())
            return
        st = self.style_format()
        changed = False
        for p in self._STYLE_PROPS:
            if not fmt.hasProperty(p) and st.hasProperty(p):
                fmt.setProperty(p, st.property(p))
                changed = True
        if changed:
            self.setCurrentCharFormat(fmt)

    def _fit_height(self) -> None:
        h = int(self.document().size().height()) + 4
        self.setFixedHeight(max(h, 96 if self.is_back else 64))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fit_height()

    # ---------- colar ----------
    def insertFromMimeData(self, source):
        plain = self._force_plain or RichEditor.plain_paste_default
        if plain and source.hasText():
            cur = self.textCursor()
            if cur.hasSelection():
                cur.removeSelectedText()
                self.setTextCursor(cur)
            self._adjust_typing_format()
            fmt = self.currentCharFormat()
            fmt.clearBackground()
            for p in (QTextFormat.AnchorHref, QTextFormat.IsAnchor):
                fmt.clearProperty(p)
            if not fmt.hasProperty(QTextFormat.ForegroundBrush):
                fmt.setForeground(QColor(self.style["color"]))
            cur.insertText(source.text(), fmt)
            self.setTextCursor(cur)
        else:
            super().insertFromMimeData(source)

    def paste_plain(self) -> None:
        self._force_plain = True
        try:
            self.paste()
        finally:
            self._force_plain = False

    def paste_formatted(self) -> None:
        old = RichEditor.plain_paste_default
        RichEditor.plain_paste_default = False
        try:
            self.paste()
        finally:
            RichEditor.plain_paste_default = old

    # ---------- formatação ----------
    def _merge(self, fmt: QTextCharFormat) -> None:
        self.mergeCurrentCharFormat(fmt)

    # Cada escolha de formatação é aplicada e lembrada como padrão do texto novo.
    def toggle_bold(self):
        on = not self.fontWeight() > QFont.Normal
        f = QTextCharFormat(); f.setFontWeight(QFont.Bold if on else QFont.Normal); self._merge(f)
        self.remember(bold=on)

    def toggle_italic(self):
        on = not self.fontItalic()
        f = QTextCharFormat(); f.setFontItalic(on); self._merge(f)
        self.remember(italic=on)

    def toggle_underline(self):
        on = not self.fontUnderline()
        f = QTextCharFormat(); f.setFontUnderline(on); self._merge(f)
        self.remember(underline=on, **({} if on else {"ucolor": ""}))

    def toggle_strike(self):
        on = not self.currentCharFormat().fontStrikeOut()
        f = QTextCharFormat(); f.setFontStrikeOut(on); self._merge(f)
        self.remember(strike=on)

    def set_font_color(self, c: QColor):
        f = QTextCharFormat(); f.setForeground(c); self._merge(f)
        self.remember(color=c.name())

    def set_underline_color(self, c: QColor):
        f = QTextCharFormat()
        f.setFontUnderline(True)
        f.setUnderlineStyle(QTextCharFormat.SingleUnderline)
        f.setUnderlineColor(c)
        self._merge(f)
        self.remember(underline=True, ucolor=c.name())

    def current_size(self) -> float:
        return self.textCursor().charFormat().fontPointSize() or float(self.style["size"])

    def set_size(self, size: float):
        size = max(7.0, min(40.0, float(size)))
        f = QTextCharFormat(); f.setFontPointSize(size); self._merge(f)
        self.remember(size=size)

    def change_size(self, delta: float):
        self.set_size(self.current_size() + delta)

    def clear_format(self):
        """Remove a formatação da seleção (mantendo os destaques) e volta ao padrão original."""
        self.remember(**RichEditor.default_style(self.is_back))
        cur = self.textCursor()
        if not cur.hasSelection():
            self.setCurrentCharFormat(self.style_format())
            return
        start, end = cur.selectionStart(), cur.selectionEnd()
        anchors = self._anchor_ranges(start, end)
        cur.beginEditBlock()
        cur.setCharFormat(self.style_format())
        for a, b, href in anchors:
            c = QTextCursor(self.document()); c.setPosition(a); c.setPosition(b, QTextCursor.KeepAnchor)
            c.mergeCharFormat(highlight_format(href))
        cur.endEditBlock()

    # ---------- destaques ----------
    def _anchor_ranges(self, start: int = 0, end: int | None = None) -> list[tuple[int, int, str]]:
        out = []
        block = self.document().begin()
        while block.isValid():
            it = block.begin()
            while not it.atEnd():
                frag = it.fragment()
                href = frag.charFormat().anchorHref()
                a, b = frag.position(), frag.position() + frag.length()
                if href.startswith(HL_PREFIX) and b > start and (end is None or a < end):
                    out.append((a, b, href))
                it += 1
            block = block.next()
        return out

    def highlight_ids(self) -> set[str]:
        return {href[len(HL_PREFIX):] for _, _, href in self._anchor_ranges()}

    def selection_has_highlight(self) -> bool:
        cur = self.textCursor()
        return bool(self._anchor_ranges(cur.selectionStart(), cur.selectionEnd()))

    # ---------- estruturas separadas (ex.: "got … back") ----------
    def _overlaps(self, a: int, b: int) -> bool:
        if self._anchor_ranges(a, b):
            return True
        return any(p.selectionStart() < b and a < p.selectionEnd() for p in self.pending)

    def join_part(self) -> str:
        """Guarda a seleção atual como uma parte; a próxima seleção destacada se junta a ela."""
        cur = self.textCursor()
        if not cur.hasSelection() or not cur.selectedText().strip():
            return "Selecione a primeira parte (ex.: “got”) e clique em 🔗 Juntar."
        if self._overlaps(cur.selectionStart(), cur.selectionEnd()):
            return "Esse trecho já está destacado ou já foi escolhido."
        self.pending.append(QTextCursor(cur))
        self.pending.sort(key=lambda c: c.selectionStart())
        cur.clearSelection()
        self.setTextCursor(cur)
        self._refresh_pending_marks()
        self.pendingChanged.emit(self)
        return (f"🔗 {self.pending_text()} — agora selecione a outra parte (ex.: “back”) e aperte Ctrl+D. "
                "Esc cancela.")

    def clear_pending(self) -> None:
        if self.pending:
            self.pending = []
            self._refresh_pending_marks()
            self.pendingChanged.emit(self)

    def _refresh_pending_marks(self) -> None:
        sels = []
        for c in self.pending:
            es = QTextEdit.ExtraSelection()
            es.cursor = c
            f = QTextCharFormat()
            f.setBackground(QColor(225, 29, 46, 30))
            f.setFontUnderline(True)
            f.setUnderlineStyle(QTextCharFormat.DashUnderline)
            f.setUnderlineColor(QColor(HL_RED))
            es.format = f
            sels.append(es)
        self.setExtraSelections(sels)

    def pending_text(self) -> str:
        return " … ".join(" ".join(c.selectedText().replace("\u2029", " ").split()) for c in self.pending)

    def highlight_parts(self) -> list[QTextCursor]:
        """Partes a destacar juntas: as já escolhidas + a seleção atual."""
        parts = [c for c in self.pending if c.hasSelection()]
        cur = self.textCursor()
        if cur.hasSelection() and cur.selectedText().strip() and not any(
                p.selectionStart() == cur.selectionStart() and p.selectionEnd() == cur.selectionEnd() for p in parts):
            parts.append(QTextCursor(cur))
        return sorted(parts, key=lambda c: c.selectionStart())

    def parts_overlap_highlight(self, parts: list[QTextCursor]) -> bool:
        return any(self._anchor_ranges(c.selectionStart(), c.selectionEnd()) for c in parts)

    def apply_highlight(self, child_id: str, parts: list[QTextCursor] | None = None) -> None:
        parts = parts or [QTextCursor(self.textCursor())]
        edit = QTextCursor(self.document())
        edit.beginEditBlock()
        for c in parts:
            c.mergeCharFormat(highlight_format(HL_PREFIX + child_id))
        edit.endEditBlock()
        self.pending = []
        self._refresh_pending_marks()
        cur = self.textCursor()
        cur.clearSelection()
        self.setTextCursor(cur)
        self._adjust_typing_format()
        self.pendingChanged.emit(self)

    def unhighlight(self, predicate) -> bool:
        """Remove o destaque dos trechos cujo id satisfaz ``predicate``."""
        ranges = [(a, b, h) for a, b, h in self._anchor_ranges() if predicate(h[len(HL_PREFIX):])]
        if not ranges:
            return False
        c = QTextCursor(self.document())
        c.beginEditBlock()
        for a, b, _ in ranges:
            c.setPosition(a); c.setPosition(b, QTextCursor.KeepAnchor)
            fmt = c.charFormat()
            for p in (QTextFormat.AnchorHref, QTextFormat.IsAnchor, QTextFormat.TextUnderlineStyle,
                      QTextFormat.TextUnderlineColor, QTextFormat.FontUnderline):
                fmt.clearProperty(p)
            fmt.clearBackground()
            fmt.setForeground(QColor(self.style["color"]))
            c.setCharFormat(fmt)
        c.endEditBlock()
        return True

    def child_at(self, pos: QPoint) -> str | None:
        href = self.anchorAt(pos)
        return href[len(HL_PREFIX):] if href.startswith(HL_PREFIX) else None

    # ---------- eventos ----------
    def _on_selection(self):
        self.formatSelection.emit(self)

    def focusInEvent(self, e):
        super().focusInEvent(e)
        self._adjust_typing_format()

    def focusOutEvent(self, e):
        super().focusOutEvent(e)
        if e.reason() != Qt.PopupFocusReason:
            self.focusLost.emit(self)

    def keyPressEvent(self, e):
        ctrl = e.modifiers() & Qt.ControlModifier
        shift = e.modifiers() & Qt.ShiftModifier
        k = e.key()
        if ctrl and not shift and k == Qt.Key_B: return self.toggle_bold()
        if ctrl and not shift and k == Qt.Key_I: return self.toggle_italic()
        if ctrl and not shift and k == Qt.Key_U: return self.toggle_underline()
        if ctrl and shift and k == Qt.Key_X: return self.toggle_strike()
        if ctrl and shift and k == Qt.Key_V: return self.paste_plain()
        if ctrl and k == Qt.Key_Space: return self.clear_format()
        if ctrl and not shift and k == Qt.Key_D and self.is_back:
            return self.highlightRequested.emit(self)
        if ctrl and not shift and k == Qt.Key_J and self.is_back:
            return self.joinRequested.emit(self)
        if k == Qt.Key_Escape and self.pending:
            return self.clear_pending()
        super().keyPressEvent(e)

    def mouseMoveEvent(self, e):
        super().mouseMoveEvent(e)
        if self.is_back and self.child_at(e.position().toPoint()):
            self.viewport().setCursor(Qt.PointingHandCursor if e.modifiers() & Qt.ControlModifier else Qt.IBeamCursor)
            self.setToolTip("Trecho destacado · Ctrl+clique abre o sub-card")
        else:
            self.viewport().setCursor(Qt.IBeamCursor)
            self.setToolTip("")

    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        if self.is_back and e.modifiers() & Qt.ControlModifier and not self.textCursor().hasSelection():
            cid = self.child_at(e.position().toPoint())
            if cid:
                self.openChildRequested.emit(cid, e.globalPosition().toPoint())

    def contextMenuEvent(self, e):
        m = QMenu(self)
        has_sel = self.textCursor().hasSelection()
        child = self.child_at(e.pos()) if self.is_back else None

        def act(text, fn, shortcut=None, enabled=True):
            a = m.addAction(text)
            a.triggered.connect(fn)
            a.setEnabled(enabled)
            if shortcut:
                a.setShortcut(QKeySequence(shortcut))
                a.setShortcutVisibleInContextMenu(True)
            return a

        if self.is_back:
            label = f"🖍  Destacar “{self.pending_text()} …”" if self.pending else "🖍  Destacar como desconhecido"
            hl = act(label, lambda: self.highlightRequested.emit(self), "Ctrl+D", has_sel or bool(self.pending))
            f = hl.font(); f.setBold(True); hl.setFont(f)
            act("🔗  Juntar com outro trecho (estrutura separada, ex.: got … back)",
                lambda: self.joinRequested.emit(self), "Ctrl+J", has_sel)
            if self.pending:
                act("Cancelar junção", self.clear_pending, "Esc")
        if child:
            act("↪  Abrir sub-card deste trecho", lambda: self.openChildRequested.emit(child, e.globalPos()))
            act("✕  Remover este destaque", lambda: self.removeHighlightRequested.emit(child))
        if self.is_back or child:
            m.addSeparator()
        act("Desfazer", self.undo, "Ctrl+Z", self.document().isUndoAvailable())
        act("Refazer", self.redo, "Ctrl+Y", self.document().isRedoAvailable())
        m.addSeparator()
        act("Recortar", self.cut, "Ctrl+X", has_sel)
        act("Copiar", self.copy, "Ctrl+C", has_sel)
        act("Colar sem formatação", self.paste_plain, "Ctrl+Shift+V", self.canPaste())
        act("Colar com formatação", self.paste_formatted, None, self.canPaste())
        act("Selecionar tudo", self.selectAll, "Ctrl+A")
        m.addSeparator()
        fm = m.addMenu("Formatação")
        for text, fn, sc in (("Negrito", self.toggle_bold, "Ctrl+B"), ("Itálico", self.toggle_italic, "Ctrl+I"),
                             ("Sublinhado", self.toggle_underline, "Ctrl+U"),
                             ("Tachado", self.toggle_strike, "Ctrl+Shift+X")):
            a = fm.addAction(text); a.triggered.connect(fn)
            a.setShortcut(QKeySequence(sc)); a.setShortcutVisibleInContextMenu(True)
        fm.addSeparator()
        fm.addAction("Aumentar fonte").triggered.connect(lambda: self.change_size(+2))
        fm.addAction("Diminuir fonte").triggered.connect(lambda: self.change_size(-2))
        m.addMenu(size_menu(m, self.set_size, self.current_size()))
        m.addMenu(color_menu(m, FONT_COLORS, self.set_font_color, False, "Cor da fonte"))
        m.addMenu(color_menu(m, UNDERLINE_COLORS, self.set_underline_color, True, "Cor do sublinhado"))
        m.addAction("Limpar formatação (volta ao padrão)").triggered.connect(self.clear_format)
        m.exec(e.globalPos())


def size_menu(parent: QWidget, on_pick, current: float) -> QMenu:
    m = QMenu("Tamanho da fonte", parent)
    for sz in FONT_SIZES:
        a = m.addAction(f"{sz:g}")
        a.setCheckable(True)
        a.setChecked(abs(sz - current) < 0.01)
        a.triggered.connect(lambda _=False, v=sz: on_pick(v))
    return m


def apply_highlight_style(doc, shadow: bool) -> None:
    """Liga/desliga a sombra vermelha em todos os trechos destacados de um documento."""
    ranges = []
    block = doc.begin()
    while block.isValid():
        it = block.begin()
        while not it.atEnd():
            frag = it.fragment()
            if frag.charFormat().anchorHref().startswith(HL_PREFIX):
                ranges.append((frag.position(), frag.position() + frag.length()))
            it += 1
        block = block.next()
    if not ranges:
        return
    undo = doc.isUndoRedoEnabled()
    doc.setUndoRedoEnabled(False)
    c = QTextCursor(doc)
    for a, b in ranges:
        c.setPosition(a); c.setPosition(b, QTextCursor.KeepAnchor)
        fmt = c.charFormat()
        if shadow:
            fmt.setBackground(HL_BG)
        else:
            fmt.clearBackground()
        fmt.setForeground(QColor(HL_RED))
        fmt.setFontUnderline(True)
        fmt.setUnderlineColor(QColor(HL_RED))
        c.setCharFormat(fmt)
    doc.setUndoRedoEnabled(undo)


def highlight_format(href: str) -> QTextCharFormat:
    f = QTextCharFormat()
    f.setAnchor(True)
    f.setAnchorHref(href)
    f.setForeground(QColor(HL_RED))
    if RichEditor.hl_shadow:
        f.setBackground(HL_BG)
    f.setFontUnderline(True)
    f.setUnderlineColor(QColor(HL_RED))
    return f


class FormatBar(QFrame):
    """Barra de formatação flutuante que aparece só quando há texto selecionado."""

    def __init__(self, host: QWidget) -> None:
        super().__init__(host)
        self.setObjectName("formatBar")
        self.editor: RichEditor | None = None
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 3, 4, 3)
        lay.setSpacing(1)

        def btn(text, tip, fn=None, bold=False, menu=None, obj=None):
            b = QToolButton(self)
            b.setText(text)
            b.setToolTip(tip)
            b.setFocusPolicy(Qt.NoFocus)
            b.setAutoRaise(True)
            if obj:
                b.setObjectName(obj)
            if bold:
                f = b.font(); f.setBold(True); b.setFont(f)
            if fn:
                b.clicked.connect(lambda: self.editor and (fn(self.editor), self._sync_size()))
            if menu:
                b.setMenu(menu)
                b.setPopupMode(QToolButton.InstantPopup)
            lay.addWidget(b)
            return b

        self.hl_btn = btn("🖍 Destacar", "Destacar como desconhecido e criar sub-card (Ctrl+D)",
                          lambda e: e.highlightRequested.emit(e), True, obj="hlButton")
        self.join_btn = btn("🔗 Juntar", "Estrutura separada (ex.: phrasal verb “got … back”): guarda este trecho; "
                            "depois selecione a outra parte e destaque (Ctrl+J)",
                            lambda e: e.joinRequested.emit(e), obj="joinButton")
        btn("B", "Negrito (Ctrl+B)", RichEditor.toggle_bold, True)
        i = btn("I", "Itálico (Ctrl+I)", RichEditor.toggle_italic)
        f = i.font(); f.setItalic(True); i.setFont(f)
        u = btn("U", "Sublinhado (Ctrl+U)", RichEditor.toggle_underline)
        f = u.font(); f.setUnderline(True); u.setFont(f)
        s = btn("S", "Tachado (Ctrl+Shift+X)", RichEditor.toggle_strike)
        f = s.font(); f.setStrikeOut(True); s.setFont(f)
        fc = btn("A", "Cor da fonte", bold=True,
                 menu=color_menu(self, FONT_COLORS, lambda c: self.editor and self.editor.set_font_color(c), False, "Cor da fonte"))
        fc.setIcon(swatch(TIFFANY)); fc.setToolButtonStyle(Qt.ToolButtonTextBesideIcon); fc.setIconSize(QSize(10, 10))
        uc = btn("", "Cor do sublinhado",
                 menu=color_menu(self, UNDERLINE_COLORS, lambda c: self.editor and self.editor.set_underline_color(c), True, "Cor do sublinhado"))
        uc.setIcon(swatch("#facc15", True))
        self.size_btn = btn("11.5", "Tamanho da fonte (fica lembrado como padrão)")
        self.size_btn.setPopupMode(QToolButton.InstantPopup)
        self.size_btn.setMinimumWidth(38)
        btn("⌫", "Limpar formatação e voltar ao padrão (Ctrl+Espaço)", RichEditor.clear_format)
        self.hide()

    def show_for(self, editor: RichEditor) -> None:
        self.editor = editor
        self.hl_btn.setVisible(editor.is_back)
        self.join_btn.setVisible(editor.is_back)
        wide = self.parentWidget().width() >= 470
        n = len(editor.pending)
        if n:
            self.hl_btn.setText(f"🖍 Destacar ({n + 1} partes)" if wide else f"🖍 {n + 1}")
        else:
            self.hl_btn.setText("🖍 Destacar" if wide else "🖍")
        self.join_btn.setText("🔗 Juntar" if wide else "🔗")
        self.size_btn.setText(f"{editor.current_size():g}")
        self.size_btn.setMenu(size_menu(self, lambda v: (editor.set_size(v), self.size_btn.setText(f"{v:g}")),
                                        editor.current_size()))
        self.adjustSize()
        self.reposition()
        self.show()
        self.raise_()

    def _sync_size(self) -> None:
        if self.editor:
            self.size_btn.setText(f"{self.editor.current_size():g}")

    def reposition(self) -> None:
        e = self.editor
        if not e:
            return
        cur = QTextCursor(e.textCursor())
        cur.setPosition(e.textCursor().selectionStart())
        r = e.cursorRect(cur)
        host = self.parentWidget()
        top_left = e.viewport().mapTo(host, r.topLeft())
        x = max(6, min(top_left.x() - 20, host.width() - self.width() - 6))
        y = top_left.y() - self.height() - 6
        if y < 6:
            y = e.viewport().mapTo(host, r.bottomLeft()).y() + 6
        self.move(x, y)
