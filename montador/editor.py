"""Editor de texto rico: formatação, colar sem formatação, destaques e menu de contexto."""
from __future__ import annotations

from PySide6.QtCore import QPoint, QSize, Qt, Signal
from PySide6.QtGui import (QAction, QColor, QFont, QIcon, QKeySequence, QPainter, QPalette, QPixmap,
                           QTextCharFormat, QTextCursor, QTextFormat)
from PySide6.QtWidgets import QColorDialog, QFrame, QHBoxLayout, QMenu, QTextEdit, QToolButton, QWidget

from .model import HL_PREFIX

TIFFANY = "#0ABAB5"
FRONT_COLOR = "#1f2933"
HL_RED = "#e11d2e"
HL_BG = QColor(225, 29, 46, 38)

FONT_COLORS = [
    ("Azul Tiffany", TIFFANY), ("Preto", FRONT_COLOR), ("Azul", "#2563eb"), ("Verde", "#16a34a"),
    ("Laranja", "#ea580c"), ("Roxo", "#7c3aed"), ("Rosa", "#db2777"), ("Cinza", "#6b7785"),
]
UNDERLINE_COLORS = [
    ("Amarelo", "#facc15"), ("Laranja", "#f97316"), ("Verde", "#22c55e"), ("Azul", "#3b82f6"),
    ("Roxo", "#a855f7"), ("Rosa", "#ec4899"), ("Azul Tiffany", TIFFANY), ("Preto", "#111827"),
]


def default_font() -> QFont:
    f = QFont("Segoe UI")
    f.setStyleHint(QFont.SansSerif)
    f.setPointSizeF(11.5)
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
    openChildRequested = Signal(str)         # id do sub-card
    removeHighlightRequested = Signal(str)   # id do sub-card
    formatSelection = Signal(object)         # editor com seleção (mostrar barra)
    focusLost = Signal(object)

    plain_paste_default = True               # configuração global "Colar sem formatação"

    def __init__(self, is_back: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.is_back = is_back
        self.base_color = QColor(TIFFANY if is_back else FRONT_COLOR)
        self._force_plain = False
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
        self._reset_typing_color()
        self.setPlaceholderText(
            "Resposta / explicação…   Selecione um trecho que você não conhece e aperte Ctrl+D"
            if is_back else "Pergunta / conceito…")
        self.setMouseTracking(True)
        self.document().contentsChanged.connect(self._fit_height)
        self.selectionChanged.connect(self._on_selection)
        self.cursorPositionChanged.connect(self._dont_extend_highlight)
        self._fit_height()

    # ---------- conteúdo ----------
    def set_content(self, html: str) -> None:
        self.blockSignals(True)
        if html:
            self.setHtml(html)
        else:
            self.clear()
        self.document().setDefaultFont(default_font())
        self.blockSignals(False)
        self._reset_typing_color()
        self._fit_height()

    def _reset_typing_color(self) -> None:
        fmt = self.currentCharFormat()
        fmt.setForeground(self.base_color)
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
            fmt = cur.charFormat()
            fmt.setForeground(self.base_color)
            fmt.clearBackground()
            for p in (QTextFormat.AnchorHref, QTextFormat.IsAnchor):
                fmt.clearProperty(p)
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

    def toggle_bold(self):
        f = QTextCharFormat()
        f.setFontWeight(QFont.Normal if self.fontWeight() > QFont.Normal else QFont.Bold)
        self._merge(f)

    def toggle_italic(self):
        f = QTextCharFormat(); f.setFontItalic(not self.fontItalic()); self._merge(f)

    def toggle_underline(self):
        f = QTextCharFormat(); f.setFontUnderline(not self.fontUnderline()); self._merge(f)

    def toggle_strike(self):
        f = QTextCharFormat(); f.setFontStrikeOut(not self.currentCharFormat().fontStrikeOut()); self._merge(f)

    def set_font_color(self, c: QColor):
        f = QTextCharFormat(); f.setForeground(c); self._merge(f)

    def set_underline_color(self, c: QColor):
        f = QTextCharFormat()
        f.setFontUnderline(True)
        f.setUnderlineStyle(QTextCharFormat.SingleUnderline)
        f.setUnderlineColor(c)
        self._merge(f)

    def change_size(self, delta: float):
        cur = self.textCursor()
        size = cur.charFormat().fontPointSize() or default_font().pointSizeF()
        f = QTextCharFormat(); f.setFontPointSize(max(7.0, min(40.0, size + delta))); self._merge(f)

    def clear_format(self):
        """Remove a formatação da seleção, mantendo os trechos destacados."""
        cur = self.textCursor()
        if not cur.hasSelection():
            return
        start, end = cur.selectionStart(), cur.selectionEnd()
        anchors = self._anchor_ranges(start, end)
        cur.beginEditBlock()
        plain = QTextCharFormat()
        plain.setForeground(self.base_color)
        cur.setCharFormat(plain)
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

    def apply_highlight(self, child_id: str) -> None:
        cur = self.textCursor()
        cur.mergeCharFormat(highlight_format(HL_PREFIX + child_id))
        cur.clearSelection()
        self.setTextCursor(cur)
        self._dont_extend_highlight()

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
            fmt.setForeground(self.base_color)
            c.setCharFormat(fmt)
        c.endEditBlock()
        return True

    def _dont_extend_highlight(self) -> None:
        # Ao digitar logo depois de um trecho destacado, o texto novo não fica vermelho.
        if self.textCursor().hasSelection():
            return
        fmt = self.currentCharFormat()
        if fmt.anchorHref().startswith(HL_PREFIX):
            for p in (QTextFormat.AnchorHref, QTextFormat.IsAnchor, QTextFormat.TextUnderlineStyle,
                      QTextFormat.TextUnderlineColor, QTextFormat.FontUnderline):
                fmt.clearProperty(p)
            fmt.clearBackground()
            fmt.setForeground(self.base_color)
            self.setCurrentCharFormat(fmt)

    def child_at(self, pos: QPoint) -> str | None:
        href = self.anchorAt(pos)
        return href[len(HL_PREFIX):] if href.startswith(HL_PREFIX) else None

    # ---------- eventos ----------
    def _on_selection(self):
        self.formatSelection.emit(self)

    def focusInEvent(self, e):
        super().focusInEvent(e)
        if not self.textCursor().hasSelection() and not self.currentCharFormat().hasProperty(QTextFormat.ForegroundBrush):
            self._reset_typing_color()

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
                self.openChildRequested.emit(cid)

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
            hl = act("🖍  Destacar como desconhecido", lambda: self.highlightRequested.emit(self), "Ctrl+D", has_sel)
            f = hl.font(); f.setBold(True); hl.setFont(f)
        if child:
            act("↪  Abrir sub-card deste trecho", lambda: self.openChildRequested.emit(child))
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
        m.addMenu(color_menu(m, FONT_COLORS, self.set_font_color, False, "Cor da fonte"))
        m.addMenu(color_menu(m, UNDERLINE_COLORS, self.set_underline_color, True, "Cor do sublinhado"))
        a = m.addAction("Limpar formatação"); a.triggered.connect(self.clear_format); a.setEnabled(has_sel)
        m.exec(e.globalPos())


def highlight_format(href: str) -> QTextCharFormat:
    f = QTextCharFormat()
    f.setAnchor(True)
    f.setAnchorHref(href)
    f.setForeground(QColor(HL_RED))
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
                b.clicked.connect(lambda: self.editor and fn(self.editor))
            if menu:
                b.setMenu(menu)
                b.setPopupMode(QToolButton.InstantPopup)
            lay.addWidget(b)
            return b

        self.hl_btn = btn("🖍 Destacar", "Destacar como desconhecido e criar sub-card (Ctrl+D)",
                          lambda e: e.highlightRequested.emit(e), True, obj="hlButton")
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
        btn("A+", "Aumentar fonte", lambda e: e.change_size(+2))
        btn("A-", "Diminuir fonte", lambda e: e.change_size(-2))
        btn("⌫", "Limpar formatação (Ctrl+Espaço)", RichEditor.clear_format)
        self.hide()

    def show_for(self, editor: RichEditor) -> None:
        self.editor = editor
        self.hl_btn.setVisible(editor.is_back)
        self.adjustSize()
        self.reposition()
        self.show()
        self.raise_()

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
