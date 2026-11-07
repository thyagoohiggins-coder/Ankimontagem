"""Janelinhas de sub-cards encadeadas: descendo pelos sub-cards ou subindo até a raiz.

Cada janelinha pode ser movida (arrastando o topo), redimensionada (canto inferior direito)
e minimizada (—). O tamanho escolhido fica lembrado e vale para todas.
"""
from __future__ import annotations

import html

from PySide6.QtCore import QPoint, QRect, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QGuiApplication, QPalette
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton, QSizeGrip, QTextBrowser, QToolButton,
                               QVBoxLayout, QWidget)

from . import settings
from .editor import FRONT_COLOR, HL_RED, TIFFANY, RichEditor, apply_highlight_style, default_font
from .model import HL_PREFIX

DEFAULT_SIZE = QSize(400, 430)
MIN_SIZE = QSize(260, 200)
GAP = 10


def remembered_size() -> QSize:
    w = settings.get_int("popup/width", DEFAULT_SIZE.width())
    h = settings.get_int("popup/height", DEFAULT_SIZE.height())
    return QSize(max(MIN_SIZE.width(), w), max(MIN_SIZE.height(), h))


class _Header(QFrame):
    """Barra do topo: arrastar move a janelinha; duplo clique minimiza/restaura."""

    def __init__(self, popup: "CardPopup") -> None:
        super().__init__(objectName="popupHeader")
        self.popup = popup
        self._drag: QPoint | None = None
        self.setCursor(Qt.SizeAllCursor)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.popup.frameGeometry().topLeft()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._drag is not None and e.buttons() & Qt.LeftButton:
            self.popup.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e):
        self._drag = None
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        self.popup.toggle_minimized()


class CardPopup(QFrame):
    def __init__(self, win, card_id: str, at: QPoint, direction: str = "down", parent_popup=None) -> None:
        super().__init__(win, Qt.Tool | Qt.FramelessWindowHint)
        self.win = win
        self.card = win.store.get(card_id)
        self.parent_popup = parent_popup
        self.children_popups: list[CardPopup] = []
        self.chain_index = parent_popup.chain_index + 1 if parent_popup else 0
        self.chain_origin = parent_popup.chain_origin if parent_popup else None
        self.minimized = False
        self._restore_h = 0
        self.setObjectName("cardPopup")
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setFocusPolicy(Qt.StrongFocus)
        if parent_popup:
            parent_popup.children_popups.append(self)
        s = win.store
        depth = s.depth(card_id)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(1, 1, 1, 1)
        outer.setSpacing(0)

        # ---- topo (mover / minimizar / fechar)
        self.header = _Header(self)
        hl = QHBoxLayout(self.header)
        hl.setContentsMargins(12, 6, 6, 6)
        hl.setSpacing(4)
        if depth:
            meta = (f"NÍVEL {depth} · de <span style='color:{HL_RED};font-weight:600'>"
                    f"“{html.escape(self.card.snippet[:36])}”</span>")
        else:
            meta = "🌳 CARD RAIZ"
        m = QLabel(meta, objectName="cardMeta")
        m.setTextFormat(Qt.RichText)
        hl.addWidget(m, 1)
        n = s.direct_count(card_id)
        badge = QLabel(str(n), objectName="badge")
        badge.setProperty("zero", n == 0)
        badge.setToolTip("Trechos destacados no back deste card")
        hl.addWidget(badge)
        self.min_btn = QToolButton(objectName="popupBtn")
        self.min_btn.setText("—")
        self.min_btn.setToolTip("Minimizar / restaurar")
        self.min_btn.clicked.connect(self.toggle_minimized)
        close = QToolButton(objectName="popupBtn")
        close.setText("✕")
        close.setToolTip("Fechar (Esc) — fecha também os sub-cards abertos a partir deste")
        close.clicked.connect(self.close)
        hl.addWidget(self.min_btn)
        hl.addWidget(close)
        outer.addWidget(self.header)

        # ---- conteúdo
        self.body = QWidget()
        lay = QVBoxLayout(self.body)
        lay.setContentsMargins(14, 4, 14, 4)
        lay.setSpacing(4)
        lay.addWidget(QLabel("FRONT", objectName="sideLabel"))
        self.front = self._browser(self.card.front, FRONT_COLOR, "frontView", "(sem front)")
        lay.addWidget(self.front)
        lay.addWidget(QLabel("BACK", objectName="sideLabel"))
        self.back = self._browser(self.card.back, TIFFANY, "backView", "(sem back)")
        self.back.anchorClicked.connect(lambda url: self._open_href(url.toString()))
        lay.addWidget(self.back, 1)

        kids = s.children(card_id)
        if kids:
            links = " · ".join(
                f"<a href='{HL_PREFIX}{k.id}' style='color:{HL_RED};text-decoration:none'>"
                f"↓ “{html.escape(k.snippet[:28])}”</a>" for k in kids)
            sub = QLabel(f"<span style='color:#8a96a3'>Sub-cards:</span> {links}", objectName="subLinks")
            sub.setTextFormat(Qt.RichText)
            sub.setWordWrap(True)
            sub.linkActivated.connect(self._open_href)
            sub.setToolTip("Abrir o sub-card (também dá para clicar no trecho vermelho do back)")
            lay.addWidget(sub)
        outer.addWidget(self.body, 1)

        # ---- rodapé
        self.foot = QWidget()
        foot = QHBoxLayout(self.foot)
        foot.setContentsMargins(8, 0, 0, 0)
        foot.setSpacing(4)
        if self.card.parent_id:
            up = QPushButton("▲ Card pai", objectName="ghost")
            up.setToolTip("Abrir o card de onde este trecho saiu (↑)")
            up.clicked.connect(self.open_parent)
            foot.addWidget(up)
        foot.addStretch(1)
        edit = QPushButton("✎ Editar", objectName="ghost")
        edit.setToolTip("Abrir este card na linha do tempo para editar (Enter)")
        edit.clicked.connect(self.edit)
        foot.addWidget(edit)
        grip = QSizeGrip(self)
        grip.setToolTip("Arraste para redimensionar (o tamanho fica lembrado)")
        foot.addWidget(grip, 0, Qt.AlignBottom | Qt.AlignRight)
        outer.addWidget(self.foot)

        self.setMinimumSize(MIN_SIZE)
        self.resize(remembered_size())
        self._place(at, direction)
        self._ready = True

    # ---------- montagem ----------
    def _browser(self, content: str, color: str, name: str, empty: str) -> QTextBrowser:
        b = QTextBrowser(objectName=name)
        b.setOpenLinks(False)
        b.setFrameShape(QFrame.NoFrame)
        b.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        pal = b.palette()
        pal.setColor(QPalette.Text, QColor(color))
        b.setPalette(pal)
        b.setHtml(content or f"<i style='color:#a5afb9'>{empty}</i>")
        b.document().setDefaultFont(default_font())
        b.document().setDocumentMargin(4)
        apply_highlight_style(b.document(), RichEditor.hl_shadow)
        return b

    def _fit_front(self) -> None:
        """O FRONT ocupa a altura do seu texto (sem cortar a última linha); o BACK fica com o resto."""
        doc = self.front.document()
        doc.setTextWidth(self.front.viewport().width())
        need = int(doc.size().height()) + 6
        self.front.setFixedHeight(max(30, min(need, max(60, self.height() // 3))))

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fit_front()
        # o tamanho só é lembrado depois que a janelinha aparece (redimensionada pelo usuário)
        if getattr(self, "_shown", False) and not self.minimized:
            self._save_size.start()

    def showEvent(self, e):
        super().showEvent(e)
        QTimer.singleShot(0, self._fit_front)
        if not hasattr(self, "_save_size"):
            self._save_size = QTimer(self, singleShot=True, interval=300)
            self._save_size.timeout.connect(self._remember_size)
        QTimer.singleShot(50, lambda: setattr(self, "_shown", True))

    def _remember_size(self) -> None:
        if self.minimized:
            return
        settings.set_value("popup/width", self.width())
        settings.set_value("popup/height", self.height())

    def _place(self, at: QPoint, direction: str) -> None:
        screen = QGuiApplication.screenAt(at) or QGuiApplication.primaryScreen()
        area: QRect = screen.availableGeometry()
        w, h = self.width(), self.height()
        if self.win.view_mode == "grid" and self.chain_origin is not None:
            # grade: 1º à esquerda, 2º à direita, 3º abaixo do 1º, 4º abaixo do 2º...
            col, row = self.chain_index % 2, self.chain_index // 2
            x = self.chain_origin.x() + col * (w + GAP)
            y = self.chain_origin.y() + row * (h + GAP)
        else:
            x = at.x() - 24
            y = at.y() + 14 if direction == "down" else at.y() - h - 8
            if direction == "down" and y + h > area.bottom():
                y = at.y() - h - 8
            if direction == "up" and y < area.top():
                y = at.y() + 14
        x = max(area.left() + 4, min(x, area.right() - w - 4))
        y = max(area.top() + 4, min(y, area.bottom() - h - 4))
        self.move(x, y)
        if self.chain_origin is None:
            self.chain_origin = QPoint(x, y)

    # ---------- ações ----------
    def toggle_minimized(self) -> None:
        self.minimized = not self.minimized
        if self.minimized:
            self._restore_h = self.height()
            self.body.hide()
            self.foot.hide()
            self.setMinimumHeight(0)
            self.resize(self.width(), self.header.sizeHint().height() + 2)
            self.min_btn.setText("▢")
        else:
            self.body.show()
            self.foot.show()
            self.setMinimumSize(MIN_SIZE)
            self.resize(self.width(), self._restore_h or remembered_size().height())
            self.min_btn.setText("—")

    def _open_href(self, href: str) -> None:
        if not href.startswith(HL_PREFIX):
            return
        cid = href[len(HL_PREFIX):]
        if not self.win.store.get(cid):
            return
        for p in self.children_popups:      # já aberto: só traz para a frente
            if p.card.id == cid and p.isVisible():
                p.raise_(); p.activateWindow()
                return
        at = self.mapToGlobal(QPoint(28, self.height()))
        CardPopup(self.win, cid, at, "down", self).show()

    def open_parent(self) -> None:
        pid = self.card.parent_id
        if not pid:
            return
        at = self.mapToGlobal(QPoint(-20, 0))
        CardPopup(self.win, pid, at, "up", self).show()

    def edit(self) -> None:
        cid = self.card.id
        root = self
        while root.parent_popup is not None:
            root = root.parent_popup
        root.close()
        self.win.open_card(cid)

    def closeEvent(self, e):
        for p in list(self.children_popups):
            p.close()
        if self.parent_popup and self in self.parent_popup.children_popups:
            self.parent_popup.children_popups.remove(self)
        super().closeEvent(e)

    def keyPressEvent(self, e):
        k = e.key()
        if k == Qt.Key_Escape:
            self.close()
        elif k == Qt.Key_Up:
            self.open_parent()
        elif k in (Qt.Key_Return, Qt.Key_Enter):
            self.edit()
        elif k == Qt.Key_Down:
            kids = self.win.store.children(self.card.id)
            if kids:
                self._open_href(HL_PREFIX + kids[0].id)
        else:
            super().keyPressEvent(e)
