"""Janela principal: linha do tempo de cards, modo de estudo e resumo."""
from __future__ import annotations

import html
import os

from PySide6.QtCore import QPoint, QStandardPaths, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QKeySequence, QPainter, QPalette, QPen, QShortcut, QTextCursor, QTextDocumentFragment
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QFileDialog, QFrame, QHBoxLayout, QHeaderView,
                               QLabel, QListWidget, QMainWindow, QMenu, QMessageBox, QPushButton, QScrollArea,
                               QSizePolicy, QStackedWidget, QTextBrowser, QToolButton, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

from . import settings
from .editor import FRONT_COLOR, HL_RED, TIFFANY, FormatBar, RichEditor, default_font
from .model import Card, Store

APP_NAME = "Montador de Flashcards"
TEAL = "#0a8f8b"
INDENT = 16


def plain(html_text: str, limit: int = 0) -> str:
    t = " ".join(QTextDocumentFragment.fromHtml(html_text or "").toPlainText().split())
    if limit and len(t) > limit:
        t = t[: limit - 1] + "…"
    return t


def data_path() -> str:
    base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation) or os.path.expanduser("~")
    return os.path.join(base, "flashcards.json")


# ====================================================================== card da linha do tempo
class CardItem(QFrame):
    clicked = Signal(str)

    def __init__(self, win: "MainWindow", card: Card) -> None:
        super().__init__()
        self.win = win
        self.card = card
        self.depth = win.store.depth(card.id)
        self.expanded = False
        self.setObjectName("cardItem")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(30 + self.depth * INDENT, 5, 8, 5)

        self.box = QFrame(objectName="cardBox")
        box = QVBoxLayout(self.box)
        box.setContentsMargins(12, 9, 12, 10)
        box.setSpacing(4)
        lay.addWidget(self.box)

        # cabeçalho (sempre visível)
        head = QHBoxLayout()
        head.setSpacing(8)
        texts = QVBoxLayout()
        texts.setSpacing(1)
        self.meta = QLabel(objectName="cardMeta")
        self.meta.setTextFormat(Qt.RichText)
        self.title = QLabel(objectName="cardTitle")
        self.title.setWordWrap(True)
        texts.addWidget(self.meta)
        texts.addWidget(self.title)
        head.addLayout(texts, 1)
        self.badge = QLabel(objectName="badge")
        self.badge.setAlignment(Qt.AlignCenter)
        self.badge.setToolTip("Trechos destacados no back deste card")
        head.addWidget(self.badge, 0, Qt.AlignTop)
        box.addLayout(head)

        # corpo (só no card aberto)
        self.body = QWidget()
        body = QVBoxLayout(self.body)
        body.setContentsMargins(0, 6, 0, 0)
        body.setSpacing(4)
        body.addWidget(QLabel("FRONT", objectName="sideLabel"))
        self.front = RichEditor(False)
        body.addWidget(self._framed(self.front))
        back_head = QHBoxLayout()
        back_head.addWidget(QLabel("BACK", objectName="sideLabel"))
        back_head.addStretch(1)
        self.back_count = QLabel(objectName="sideLabel")
        back_head.addWidget(self.back_count)
        body.addSpacing(4)
        body.addLayout(back_head)
        self.back = RichEditor(True)
        body.addWidget(self._framed(self.back))

        foot = QHBoxLayout()
        foot.setSpacing(6)
        self.parent_btn = QPushButton("↑ Card pai", objectName="ghost")
        self.parent_btn.setToolTip("Abrir o card de onde este trecho saiu (Alt+←)")
        self.parent_btn.clicked.connect(lambda: self.win.open_card(self.card.parent_id))
        self.parent_btn.setVisible(bool(card.parent_id))
        foot.addWidget(self.parent_btn)
        foot.addStretch(1)
        more = QToolButton(objectName="ghostTool")
        more.setText("⋯")
        more.setPopupMode(QToolButton.InstantPopup)
        m = QMenu(more)
        if card.parent_id:
            m.addAction("Remover este destaque e o sub-card").triggered.connect(lambda: self.win.remove_highlight(self.card.id))
        else:
            m.addAction("Excluir este card raiz e todos os sub-cards").triggered.connect(self.win.delete_current_root)
        more.setMenu(m)
        foot.addWidget(more)
        body.addLayout(foot)
        box.addWidget(self.body)
        self.body.hide()

        self.front.set_content(card.front)
        self.back.set_content(card.back)
        for ed in (self.front, self.back):
            ed.formatSelection.connect(win.on_selection)
            ed.focusLost.connect(win.on_editor_focus_lost)
        self.back.highlightRequested.connect(lambda e: win.highlight(self, e))
        self.back.openChildRequested.connect(win.open_card)
        self.back.removeHighlightRequested.connect(win.remove_highlight)
        self.front.textChanged.connect(self._front_changed)
        self.back.textChanged.connect(lambda: win.back_changed(self))
        self.refresh()

    def _framed(self, ed: RichEditor) -> QFrame:
        f = QFrame(objectName="editorBox")
        l = QVBoxLayout(f)
        l.setContentsMargins(1, 1, 1, 1)
        l.addWidget(ed)
        return f

    def _front_changed(self):
        self.card.front = self.front.toHtml() if self.front.toPlainText().strip() else ""
        self.refresh()
        self.win.front_changed(self.card)

    def refresh(self):
        c = self.card
        if self.depth == 0:
            meta = "🌳 CARD RAIZ"
        else:
            snip = html.escape(c.snippet if len(c.snippet) < 40 else c.snippet[:39] + "…")
            meta = f"NÍVEL {self.depth} · de <span style='color:{HL_RED};font-weight:600'>“{snip}”</span>"
        self.meta.setText(meta)
        t = " ".join(self.front.toPlainText().split())
        self.title.setText(t if t else "(sem front)")
        self.title.setProperty("empty", not t)
        n = self.win.store.direct_count(c.id)
        self.badge.setText(str(n))
        self.badge.setProperty("zero", n == 0)
        self.back_count.setText(f"{n} trecho{'s' if n != 1 else ''} destacado{'s' if n != 1 else ''}")
        for w in (self.badge, self.title):
            w.style().unpolish(w); w.style().polish(w)

    def set_expanded(self, on: bool):
        self.expanded = on
        self.body.setVisible(on)
        self.box.setProperty("open", on)
        self.box.style().unpolish(self.box); self.box.style().polish(self.box)
        self.update()

    def flash(self):
        self.box.setProperty("flash", True)
        self.box.style().unpolish(self.box); self.box.style().polish(self.box)

        def off():
            self.box.setProperty("flash", False)
            self.box.style().unpolish(self.box); self.box.style().polish(self.box)
        QTimer.singleShot(1100, off)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and not self.expanded:
            self.clicked.emit(self.card.id)
        super().mousePressEvent(e)

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor("#c9d3dc"), 2))
        p.drawLine(14, 0, 14, self.height())                       # linha do tempo
        cy = 5 + 22
        x = 14 + self.depth * INDENT
        if self.depth:
            p.setPen(QPen(QColor("#e8b4b9"), 2))
            p.drawLine(14, cy, x, cy)
        color = QColor(TEAL if self.depth == 0 else HL_RED)
        r = 7 if self.expanded else 5
        p.setPen(QPen(QColor("white"), 2))
        p.setBrush(color)
        p.drawEllipse(QPoint(x, cy), r, r)
        p.end()


# ====================================================================== estudo
class StudyPage(QWidget):
    finished = Signal()

    def __init__(self, win: "MainWindow") -> None:
        super().__init__()
        self.win = win
        self.cards: list[Card] = []
        self.i = 0
        self.flipped = False
        self.zoom = settings.get_int("study/zoom", 0)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setObjectName("studyPage")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 12)
        lay.setSpacing(8)

        top = QHBoxLayout()
        back = QPushButton("← Editar", objectName="ghost")
        back.clicked.connect(self.finished.emit)
        top.addWidget(back)
        self.progress = QLabel(objectName="studyProgress")
        top.addWidget(self.progress, 1, Qt.AlignCenter)
        for t, d in (("A-", -1), ("A+", 1)):
            b = QPushButton(t, objectName="ghost")
            b.setFixedWidth(38)
            b.clicked.connect(lambda _=False, d=d: self.set_zoom(self.zoom + d))
            top.addWidget(b)
        lay.addLayout(top)

        self.bar = QFrame(objectName="progressTrack")
        self.bar.setFixedHeight(4)
        self.fill = QFrame(self.bar, objectName="progressFill")
        lay.addWidget(self.bar)

        self.origin = QLabel(objectName="studyOrigin")
        self.origin.setWordWrap(True)
        self.origin.setTextFormat(Qt.RichText)
        lay.addWidget(self.origin)

        card = QFrame(objectName="studyCard")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(18, 14, 18, 14)
        cl.setSpacing(6)
        cl.addWidget(QLabel("FRONT", objectName="sideLabel"))
        self.front = self._browser(FRONT_COLOR, "frontView")
        cl.addWidget(self.front, 1)
        self.back_label = QLabel("BACK", objectName="sideLabel")
        cl.addWidget(self.back_label)
        self.back = self._browser(TIFFANY, "backView")
        cl.addWidget(self.back, 1)
        self.hint = QLabel("Espaço para virar", objectName="hint")
        self.hint.setAlignment(Qt.AlignCenter)
        cl.addWidget(self.hint, 1)
        lay.addWidget(card, 1)

        nav = QHBoxLayout()
        self.prev_btn = QPushButton("←", objectName="ghost")
        self.prev_btn.setToolTip("Anterior (←)")
        self.prev_btn.setFixedWidth(52)
        self.flip_btn = QPushButton("Virar  (Espaço)", objectName="primary")
        self.next_btn = QPushButton("→", objectName="ghost")
        self.next_btn.setToolTip("Próximo (→)")
        self.next_btn.setFixedWidth(52)
        for b in (self.prev_btn, self.flip_btn, self.next_btn):
            b.setFocusPolicy(Qt.NoFocus)
            b.setMinimumHeight(40)
        self.prev_btn.clicked.connect(self.prev)
        self.flip_btn.clicked.connect(self.flip)
        self.next_btn.clicked.connect(self.next)
        nav.addWidget(self.prev_btn)
        nav.addWidget(self.flip_btn, 1)
        nav.addWidget(self.next_btn)
        lay.addLayout(nav)

    def _browser(self, color: str, name: str) -> QTextBrowser:
        b = QTextBrowser(objectName=name)
        b.setOpenLinks(False)
        b.setFrameShape(QFrame.NoFrame)
        b.setFocusPolicy(Qt.NoFocus)
        pal = b.palette()
        pal.setColor(QPalette.Text, QColor(color))
        pal.setColor(QPalette.Base, QColor("white"))
        b.setPalette(pal)
        return b

    def start(self, cards: list[Card]):
        self.cards, self.i, self.flipped = cards, 0, False
        self.show_card()
        self.setFocus()

    def set_zoom(self, z: int):
        self.zoom = max(-3, min(8, z))
        settings.set_value("study/zoom", self.zoom)
        self.show_card()

    def _set(self, browser: QTextBrowser, html_text: str, empty: str):
        browser.setHtml(html_text or f"<i style='color:#a5afb9'>{empty}</i>")
        f = default_font()
        f.setPointSizeF(15 + self.zoom * 1.5)
        browser.document().setDefaultFont(f)
        browser.setFont(f)

    def show_card(self):
        if not self.cards:
            return
        c = self.cards[self.i]
        n = len(self.cards)
        self.progress.setText(f"{self.i + 1} / {n}")
        self.fill.setGeometry(0, 0, int(self.bar.width() * (self.i + 1) / n), 4)
        depth = self.win.store.depth(c.id)
        if depth:
            self.origin.setText(f"Nível {depth} · trecho <span style='color:{HL_RED};font-weight:600'>“{html.escape(c.snippet)}”</span>")
        else:
            self.origin.setText("🌳 Card raiz")
        self._set(self.front, c.front, "(sem front)")
        self._set(self.back, c.back, "(sem back)")
        for w in (self.back_label, self.back):
            w.setVisible(self.flipped)
        self.hint.setVisible(not self.flipped)
        self.flip_btn.setText("Esconder resposta" if self.flipped else "Virar  (Espaço)")
        self.prev_btn.setEnabled(self.i > 0)
        self.next_btn.setText("✔" if self.i == n - 1 else "→")

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.cards:
            self.fill.setGeometry(0, 0, int(self.bar.width() * (self.i + 1) / len(self.cards)), 4)

    def flip(self):
        self.flipped = not self.flipped
        self.show_card()

    def next(self):
        if self.i < len(self.cards) - 1:
            self.i += 1
            self.flipped = False
            self.show_card()
        else:
            self.win.statusBar().showMessage("Estudo concluído! 🎉", 4000)
            self.finished.emit()

    def prev(self):
        if self.i > 0:
            self.i -= 1
            self.flipped = False
            self.show_card()

    def mousePressEvent(self, e):
        self.setFocus()
        super().mousePressEvent(e)

    def keyPressEvent(self, e):
        k = e.key()
        if k in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter, Qt.Key_Down, Qt.Key_Up):
            self.flip()
        elif k == Qt.Key_Right:
            self.next()
        elif k == Qt.Key_Left:
            self.prev()
        elif k == Qt.Key_Escape:
            self.finished.emit()
        elif k in (Qt.Key_Plus, Qt.Key_Equal):
            self.set_zoom(self.zoom + 1)
        elif k == Qt.Key_Minus:
            self.set_zoom(self.zoom - 1)
        else:
            super().keyPressEvent(e)


# ====================================================================== resumo
class SummaryDialog(QDialog):
    def __init__(self, win: "MainWindow", root_id: str) -> None:
        super().__init__(win)
        s = win.store
        self.setWindowTitle("Aprofundamento concluído")
        self.resize(min(560, win.width() + 40), 640)
        lay = QVBoxLayout(self)
        root = s.get(root_id)
        total = s.total_count(root_id)
        lay.addWidget(QLabel(f"Trechos destacados a partir do card raiz<br><b>“{html.escape(plain(root.front, 60) or '(sem front)')}”</b>"))
        big = QLabel(str(total), objectName="bigNumber")
        lay.addWidget(big)
        lay.addWidget(QLabel(f"{total + 1} cards no total · profundidade máxima: {s.max_depth(root_id)} nível(is)",
                             objectName="muted"))

        tree = QTreeWidget()
        tree.setHeaderLabels(["Card", "Trechos no card", "Total abaixo"])
        tree.setRootIsDecorated(True)

        def add(card: Card, parent):
            it = QTreeWidgetItem([plain(card.front, 50) or "(sem front)",
                                  str(s.direct_count(card.id)), str(s.total_count(card.id))])
            it.setTextAlignment(1, Qt.AlignCenter)
            it.setTextAlignment(2, Qt.AlignCenter)
            if s.direct_count(card.id):
                it.setForeground(1, QColor(HL_RED))
            (parent.addChild(it) if isinstance(parent, QTreeWidgetItem) else parent.addTopLevelItem(it))
            for ch in s.children(card.id):
                add(ch, it)
        add(root, tree)
        tree.expandAll()
        tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        lay.addWidget(tree, 3)

        lay.addWidget(QLabel("<b>Ordem de estudo</b> — o último sub-card adicionado é o primeiro"))
        order = QListWidget()
        for i, c in enumerate(s.study_order(root_id), 1):
            d = s.depth(c.id)
            order.addItem(f"{i}. {plain(c.front, 60) or '(sem front)'}   · {'nível ' + str(d) if d else 'raiz'}")
        lay.addWidget(order, 2)

        btns = QHBoxLayout()
        btns.addStretch(1)
        close = QPushButton("Continuar editando", objectName="ghost")
        close.clicked.connect(self.reject)
        study = QPushButton("▶  Estudar nesta ordem", objectName="primary")
        study.clicked.connect(self.accept)
        study.setDefault(True)
        btns.addWidget(close)
        btns.addWidget(study)
        lay.addLayout(btns)


# ====================================================================== janela
class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(560, 900)
        self.setMinimumSize(360, 480)
        self.path = data_path()
        self.store = self._load()
        self.items: dict[str, CardItem] = {}
        self.open_id: str | None = None
        self._syncing = False
        RichEditor.load_styles()

        self.save_timer = QTimer(self, singleShot=True, interval=500)
        self.save_timer.timeout.connect(self.save)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)
        self.stack.addWidget(self._build_edit_page())
        self.study = StudyPage(self)
        self.study.finished.connect(lambda: self.stack.setCurrentIndex(0))
        self.stack.addWidget(self.study)
        self.format_bar = FormatBar(self)
        self.scroll.verticalScrollBar().valueChanged.connect(
            lambda: self.format_bar.isVisible() and self.format_bar.reposition())
        self._shortcuts()
        self.statusBar().setSizeGripEnabled(False)
        self.reload_decks()

    # ---------- construção ----------
    def _build_edit_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        top = QFrame(objectName="topBar")
        tl = QHBoxLayout(top)
        tl.setContentsMargins(10, 8, 10, 8)
        tl.setSpacing(6)
        self.deck_combo = QComboBox()
        self.deck_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.deck_combo.setMinimumContentsLength(8)
        self.deck_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.deck_combo.setToolTip("Card raiz (baralho)")
        self.deck_combo.activated.connect(lambda i: self.show_root(self.deck_combo.itemData(i)))
        tl.addWidget(self.deck_combo, 1)
        new = QPushButton("+ Novo", objectName="ghost")
        new.setToolTip("Novo card raiz (Ctrl+N)")
        new.clicked.connect(self.new_root)
        tl.addWidget(new)
        self.study_btn = QPushButton("▶ Estudar", objectName="primary")
        self.study_btn.setToolTip("Estudar do último sub-card até a raiz (F5)")
        self.study_btn.clicked.connect(self.start_study)
        tl.addWidget(self.study_btn)
        menu_btn = QToolButton(objectName="ghostTool")
        menu_btn.setText("☰")
        menu_btn.setPopupMode(QToolButton.InstantPopup)
        menu_btn.setMenu(self._build_menu(menu_btn))
        tl.addWidget(menu_btn)
        lay.addWidget(top)

        self.stats = QLabel(objectName="stats")
        self.stats.setTextFormat(Qt.RichText)
        self.stats.setWordWrap(True)
        self.stats.setCursor(Qt.PointingHandCursor)
        self.stats.setToolTip("Clique para ver o resumo do aprofundamento (Ctrl+R)")
        self.stats.mousePressEvent = lambda e: self.show_summary()
        lay.addWidget(self.stats)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        holder = QWidget(objectName="timeline")
        self.timeline = QVBoxLayout(holder)
        self.timeline.setContentsMargins(0, 8, 0, 24)
        self.timeline.setSpacing(0)
        self.timeline.addStretch(1)
        self.scroll.setWidget(holder)
        lay.addWidget(self.scroll, 1)

        self.empty = QWidget()
        el = QVBoxLayout(self.empty)
        el.addStretch(1)
        msg = QLabel("<h2>Nenhum card ainda</h2>Crie um card raiz. No BACK, selecione os trechos que você "
                     "não conhece e aperte <b>Ctrl+D</b>: cada trecho fica <span style='color:#e11d2e'><b>vermelho</b></span> "
                     "e vira um novo card na linha do tempo.", objectName="emptyMsg")
        msg.setWordWrap(True)
        msg.setAlignment(Qt.AlignCenter)
        el.addWidget(msg)
        b = QPushButton("+ Criar primeiro card", objectName="primary")
        b.clicked.connect(self.new_root)
        b.setMinimumHeight(40)
        el.addWidget(b, 0, Qt.AlignCenter)
        el.addStretch(2)
        lay.addWidget(self.empty, 1)
        return page

    def _build_menu(self, parent) -> QMenu:
        m = QMenu(parent)
        m.addAction("Resumo do aprofundamento", self.show_summary, QKeySequence("Ctrl+R"))
        m.addAction("Novo card raiz", self.new_root, QKeySequence("Ctrl+N"))
        m.addSeparator()
        self.plain_action = m.addAction("Colar sem formatação (Ctrl+V)")
        self.plain_action.setCheckable(True)
        self.plain_action.setChecked(True)
        self.plain_action.toggled.connect(lambda on: setattr(RichEditor, "plain_paste_default", on))
        m.addAction("Restaurar formatação padrão do texto", self.reset_format)
        self.top_action = m.addAction("Fixar janela sempre no topo")
        self.top_action.setCheckable(True)
        self.top_action.toggled.connect(self.set_on_top)
        m.addSeparator()
        m.addAction("Exportar baralhos…", self.export)
        m.addAction("Importar baralhos…", self.import_)
        m.addSeparator()
        m.addAction("Excluir este card raiz", self.delete_current_root)
        m.addSeparator()
        m.addAction("Atalhos do teclado", self.show_help, QKeySequence("F1"))
        return m

    def _shortcuts(self):
        def sc(key, fn):
            s = QShortcut(QKeySequence(key), self)
            s.setContext(Qt.WindowShortcut)
            s.activated.connect(lambda: self.stack.currentIndex() == 0 and fn())
        sc("Ctrl+N", self.new_root)
        sc("F5", self.start_study)
        sc("Ctrl+Return", self.start_study)
        sc("Ctrl+R", self.show_summary)
        sc("F1", self.show_help)
        sc("Alt+Down", lambda: self.step(+1))
        sc("Alt+Up", lambda: self.step(-1))
        sc("Alt+Left", lambda: self.open_id and self.open_card(self.store.get(self.open_id).parent_id))

    # ---------- persistência ----------
    def _load(self) -> Store:
        try:
            if os.path.exists(self.path):
                return Store.load(self.path)
        except Exception as exc:  # arquivo corrompido: guarda cópia e começa vazio
            try:
                os.replace(self.path, self.path + ".corrompido")
            except OSError:
                pass
            QMessageBox.warning(None, APP_NAME, f"Não foi possível ler os cards salvos ({exc}).")
        return Store()

    def schedule_save(self):
        self.save_timer.start()

    def save(self):
        try:
            self.store.save(self.path)
        except OSError as exc:
            self.statusBar().showMessage(f"Erro ao salvar: {exc}", 6000)

    def closeEvent(self, e):
        self.save()
        super().closeEvent(e)

    # ---------- baralhos ----------
    def reload_decks(self):
        self.deck_combo.blockSignals(True)
        self.deck_combo.clear()
        for rid in self.store.roots:
            self.deck_combo.addItem(self._deck_label(rid), rid)
        self.deck_combo.blockSignals(False)
        self.show_root(self.store.current_root)

    def _deck_label(self, rid: str) -> str:
        return f"🌳 {plain(self.store.get(rid).front, 50) or '(card sem título)'}"

    def show_root(self, rid: str | None):
        self.format_bar.hide()
        for it in self.items.values():
            it.setParent(None)
            it.deleteLater()
        self.items.clear()
        self.open_id = None
        self.store.current_root = rid if rid in self.store.cards else None
        has = self.store.current_root is not None
        self.empty.setVisible(not has)
        self.scroll.setVisible(has)
        self.stats.setVisible(has)
        self.study_btn.setEnabled(has)
        if not has:
            return
        self.deck_combo.setCurrentIndex(self.deck_combo.findData(rid))
        for c in self.store.timeline(rid):
            self._add_item(c)
        self.update_counts()
        self.open_card(rid, focus=False)
        self.schedule_save()

    def _add_item(self, card: Card) -> CardItem:
        it = CardItem(self, card)
        it.clicked.connect(self.open_card)
        self.timeline.insertWidget(self.timeline.count() - 1, it)
        self.items[card.id] = it
        return it

    def new_root(self):
        c = self.store.create_card(None)
        self.deck_combo.addItem(self._deck_label(c.id), c.id)
        self.show_root(c.id)
        self.items[c.id].front.setFocus()

    def delete_current_root(self):
        rid = self.store.current_root
        if not rid:
            return
        n = self.store.total_count(rid)
        if QMessageBox.question(self, APP_NAME, f"Excluir este card raiz e seus {n} sub-card(s)?") != QMessageBox.Yes:
            return
        self.store.delete_subtree(rid)
        self.save()
        self.reload_decks()

    # ---------- navegação ----------
    def open_card(self, card_id: str | None, focus: bool = True):
        if not card_id or card_id not in self.items:
            return
        if self.open_id and self.open_id in self.items:
            self.items[self.open_id].set_expanded(False)
        self.open_id = card_id
        it = self.items[card_id]
        it.set_expanded(True)
        QTimer.singleShot(0, lambda: self.scroll.ensureWidgetVisible(it, 0, 40))
        if focus:
            ed = it.front if not it.front.toPlainText().strip() else it.back
            ed.setFocus()
            ed.moveCursor(QTextCursor.End)

    def step(self, d: int):
        ids = list(self.items)
        if not ids:
            return
        i = ids.index(self.open_id) if self.open_id in ids else 0
        self.open_card(ids[max(0, min(len(ids) - 1, i + d))])

    # ---------- edição ----------
    def front_changed(self, card: Card):
        if card.parent_id is None:
            i = self.deck_combo.findData(card.id)
            if i >= 0:
                self.deck_combo.setItemText(i, self._deck_label(card.id))
        self.schedule_save()

    def back_changed(self, item: CardItem):
        if self._syncing:
            return
        ed = item.back
        card = item.card
        self._syncing = True
        try:
            ids = ed.highlight_ids()
            # destaque sem card (ex.: Ctrl+Z depois de remover) → tira o destaque
            ed.unhighlight(lambda i: i not in self.store.cards)
            # card sem destaque (trecho apagado) → remove sub-card e descendentes
            removed = []
            for ch in self.store.children(card.id):
                if ch.id not in ids:
                    removed += self.store.delete_subtree(ch.id)
            for cid in removed:
                w = self.items.pop(cid, None)
                if w:
                    w.setParent(None); w.deleteLater()
            if removed:
                self.statusBar().showMessage(f"Trecho removido: {len(removed)} sub-card(s) apagado(s).", 4000)
            card.back = ed.toHtml() if ed.toPlainText().strip() else ""
        finally:
            self._syncing = False
        self.update_counts()
        self.schedule_save()

    def highlight(self, item: CardItem, ed: RichEditor):
        cur = ed.textCursor()
        text = " ".join(cur.selectedText().replace(" ", " ").split())
        if not cur.hasSelection() or not text:
            self.statusBar().showMessage("Selecione no BACK o trecho que você não conhece e aperte Ctrl+D.", 4000)
            return
        if ed.selection_has_highlight():
            self.statusBar().showMessage("Esse trecho já está destacado.", 3000)
            return
        child = self.store.create_card(item.card.id, front=html.escape(text), snippet=text)
        new_item = self._add_item(child)
        ed.apply_highlight(child.id)          # dispara back_changed → salva e atualiza contagens
        new_item.flash()
        n = self.store.direct_count(item.card.id)
        self.statusBar().showMessage(f"🖍 “{text[:40]}” virou um sub-card ({n} neste card). Alt+↓ para abri-lo.", 5000)

    def remove_highlight(self, child_id: str):
        child = self.store.get(child_id)
        if not child:
            return
        n = len(self.store.subtree(child_id))
        if QMessageBox.question(self, APP_NAME, f"Remover este destaque e {n} card(s) (incluindo sub-cards)?") != QMessageBox.Yes:
            return
        parent_item = self.items.get(child.parent_id)
        if self.open_id in [c.id for c in self.store.subtree(child_id)]:
            self.open_card(child.parent_id, focus=False)
        if parent_item:
            parent_item.back.unhighlight(lambda i: i == child_id)   # back_changed apaga o sub-card

    def update_counts(self):
        rid = self.store.current_root
        if not rid:
            return
        for it in self.items.values():
            it.refresh()
        total = self.store.total_count(rid)
        cards = total + 1
        self.stats.setText(
            f"<span style='color:{HL_RED};font-weight:700'>{total}</span> trecho{'s' if total != 1 else ''} "
            f"destacado{'s' if total != 1 else ''} a partir da raiz · {cards} card{'s' if cards != 1 else ''} · "
            f"{self.store.max_depth(rid)} nível(is) &nbsp;<a style='color:{TEAL}' href='#'>resumo ›</a>")
        i = self.deck_combo.findData(rid)
        if i >= 0:
            self.deck_combo.setItemText(i, self._deck_label(rid))

    # ---------- barra de formatação ----------
    def on_selection(self, ed: RichEditor):
        if ed.textCursor().hasSelection() and ed.hasFocus():
            self.format_bar.show_for(ed)
        elif self.format_bar.editor is ed:
            self.format_bar.hide()

    def on_editor_focus_lost(self, ed: RichEditor):
        def check():
            if QApplication.activePopupWidget() or QApplication.activeModalWidget():
                return
            if self.format_bar.editor is ed and not ed.hasFocus():
                self.format_bar.hide()
        QTimer.singleShot(120, check)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.format_bar.isVisible():
            self.format_bar.reposition()

    # ---------- estudo / resumo ----------
    def start_study(self):
        rid = self.store.current_root
        if not rid:
            return
        self.save()
        self.format_bar.hide()
        self.stack.setCurrentIndex(1)
        self.study.start(self.store.study_order(rid))

    def show_summary(self):
        rid = self.store.current_root
        if not rid:
            return
        if SummaryDialog(self, rid).exec() == QDialog.Accepted:
            self.start_study()

    # ---------- diversos ----------
    def reset_format(self):
        RichEditor.reset_styles()
        for it in self.items.values():
            it.front._adjust_typing_format()
            it.back._adjust_typing_format()
        self.statusBar().showMessage("Formatação padrão restaurada: tamanho 11.5, back em azul Tiffany.", 4000)

    def set_on_top(self, on: bool):
        self.setWindowFlag(Qt.WindowStaysOnTopHint, on)
        self.show()

    def export(self):
        path, _ = QFileDialog.getSaveFileName(self, "Exportar baralhos", "flashcards.json", "Baralho (*.json)")
        if path:
            self.store.save(path)
            self.statusBar().showMessage(f"Exportado para {path}", 4000)

    def import_(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importar baralhos", "", "Baralho (*.json)")
        if not path:
            return
        try:
            new = Store.load(path)
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME, f"Não foi possível importar: {exc}")
            return
        if self.store.roots and QMessageBox.question(
                self, APP_NAME, "Substituir todos os cards atuais pelos do arquivo?") != QMessageBox.Yes:
            return
        self.store = new
        self.save()
        self.reload_decks()

    def show_help(self):
        QMessageBox.information(self, "Atalhos do teclado", (
            "<b>Montar</b><br>"
            "Ctrl+D — destacar o trecho selecionado no BACK (cria sub-card)<br>"
            "Ctrl+clique num trecho vermelho — abrir o sub-card<br>"
            "Tab — passar do FRONT para o BACK<br>"
            "Alt+↓ / Alt+↑ — próximo / anterior card da linha do tempo<br>"
            "Alt+← — voltar ao card pai<br>"
            "Ctrl+N — novo card raiz<br><br>"
            "<b>Texto</b><br>"
            "Ctrl+B / Ctrl+I / Ctrl+U — negrito / itálico / sublinhado<br>"
            "Ctrl+Shift+X — tachado · Ctrl+Espaço — limpar formatação e voltar ao padrão<br>"
            "A última formatação e o último tamanho escolhidos viram o padrão do texto novo<br>"
            "Ctrl+V — colar (sem formatação, se ativado no menu ☰)<br>"
            "Ctrl+Shift+V — colar sem formatação<br>"
            "Botão direito — menu completo (cores, colar com formatação…)<br><br>"
            "<b>Estudar</b><br>"
            "F5 — estudar · Espaço — virar · ← → — navegar · + / − — tamanho do texto · Esc — sair<br>"
            "Ctrl+R — resumo do aprofundamento"))
