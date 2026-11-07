"""Pop-ups encadeados de cards, como menus: descendo pelos sub-cards ou subindo até a raiz."""
from __future__ import annotations

import html

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QGuiApplication, QPalette, QTextCursor
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QTextBrowser, QVBoxLayout

from .editor import FRONT_COLOR, HL_RED, TIFFANY, RichEditor, apply_highlight_style, default_font
from .model import HL_PREFIX

WIDTH = 380
MAX_TEXT_H = 240


class CardPopup(QFrame):
    """Mostra um card (somente leitura). Clicar num trecho vermelho abre o sub-card logo abaixo;
    ▲ Card pai abre o card de cima. Fecha como um menu: clique fora ou Esc."""

    def __init__(self, win, card_id: str, at: QPoint, direction: str = "down", parent_popup=None) -> None:
        super().__init__(parent_popup or win, Qt.Popup | Qt.FramelessWindowHint)
        self.win = win
        self.card = win.store.get(card_id)
        self.parent_popup = parent_popup
        self.setObjectName("cardPopup")
        self.setAttribute(Qt.WA_DeleteOnClose)
        s = win.store
        depth = s.depth(card_id)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(5)
        head = QHBoxLayout()
        if depth:
            meta = (f"NÍVEL {depth} · de <span style='color:{HL_RED};font-weight:600'>"
                    f"“{html.escape(self.card.snippet[:40])}”</span>")
        else:
            meta = "🌳 CARD RAIZ"
        m = QLabel(meta, objectName="cardMeta")
        m.setTextFormat(Qt.RichText)
        head.addWidget(m, 1)
        n = s.direct_count(card_id)
        badge = QLabel(str(n), objectName="badge")
        badge.setProperty("zero", n == 0)
        badge.setToolTip("Trechos destacados no back deste card")
        head.addWidget(badge)
        lay.addLayout(head)

        lay.addWidget(QLabel("FRONT", objectName="sideLabel"))
        self.front = self._browser(self.card.front, FRONT_COLOR, "frontView", "(sem front)")
        lay.addWidget(self.front)
        lay.addWidget(QLabel("BACK", objectName="sideLabel"))
        self.back = self._browser(self.card.back, TIFFANY, "backView", "(sem back)")
        self.back.anchorClicked.connect(self._open_child)
        self.back.setMouseTracking(True)
        lay.addWidget(self.back)
        if n:
            hint = QLabel("Clique num trecho vermelho para descer ao sub-card", objectName="hint")
            lay.addWidget(hint)

        foot = QHBoxLayout()
        if self.card.parent_id:
            up = QPushButton("▲ Card pai", objectName="ghost")
            up.setToolTip("Abrir o card de onde este trecho saiu, acima (↑)")
            up.clicked.connect(self.open_parent)
            foot.addWidget(up)
        foot.addStretch(1)
        edit = QPushButton("✎ Editar", objectName="ghost")
        edit.setToolTip("Fechar os pop-ups e abrir este card na linha do tempo (Enter)")
        edit.clicked.connect(self.edit)
        foot.addWidget(edit)
        lay.addLayout(foot)

        self.setFixedWidth(WIDTH)
        self.adjustSize()
        self._place(at, direction)

    def _browser(self, content: str, color: str, name: str, empty: str) -> QTextBrowser:
        b = QTextBrowser(objectName=name)
        b.setOpenLinks(False)
        b.setFrameShape(QFrame.NoFrame)
        pal = b.palette()
        pal.setColor(QPalette.Text, QColor(color))
        b.setPalette(pal)
        b.setHtml(content or f"<i style='color:#a5afb9'>{empty}</i>")
        b.document().setDefaultFont(default_font())
        apply_highlight_style(b.document(), RichEditor.hl_shadow)
        b.document().setTextWidth(WIDTH - 30)
        h = int(b.document().size().height()) + 6
        b.setFixedHeight(min(max(h, 28), MAX_TEXT_H))
        return b

    def _place(self, at: QPoint, direction: str) -> None:
        screen = QGuiApplication.screenAt(at) or QGuiApplication.primaryScreen()
        area: QRect = screen.availableGeometry()
        w, h = self.width(), self.sizeHint().height()
        x = at.x() - 24
        y = at.y() + 14 if direction == "down" else at.y() - h - 8
        if direction == "down" and y + h > area.bottom():
            y = at.y() - h - 8
        if direction == "up" and y < area.top():
            y = at.y() + 14
        x = max(area.left() + 4, min(x, area.right() - w - 4))
        y = max(area.top() + 4, min(y, area.bottom() - h - 4))
        self.move(x, y)

    # ---------- navegação ----------
    def _open_child(self, url) -> None:
        href = url.toString()
        if not href.startswith(HL_PREFIX):
            return
        cid = href[len(HL_PREFIX):]
        if not self.win.store.get(cid):
            return
        # posição do trecho clicado
        cur = self.back.cursorForPosition(self.back.mapFromGlobal(self.cursor().pos()))
        r = self.back.cursorRect(cur)
        at = self.back.viewport().mapToGlobal(r.bottomLeft()) + QPoint(28, 0)
        CardPopup(self.win, cid, at, "down", self).show()

    def open_parent(self) -> None:
        pid = self.card.parent_id
        if not pid:
            return
        at = self.mapToGlobal(QPoint(-20, 0))
        CardPopup(self.win, pid, at, "up", self).show()

    def edit(self) -> None:
        cid = self.card.id
        self.close_all()
        self.win.open_card(cid)

    def close_all(self) -> None:
        p = self
        while p is not None:
            nxt = p.parent_popup
            p.close()
            p = nxt

    def keyPressEvent(self, e):
        k = e.key()
        if k == Qt.Key_Escape:
            self.close()
        elif k == Qt.Key_Up:
            self.open_parent()
        elif k in (Qt.Key_Return, Qt.Key_Enter):
            self.edit()
        elif k == Qt.Key_Down:
            # desce para o primeiro sub-card deste card
            kids = self.win.store.children(self.card.id)
            if kids:
                at = self.mapToGlobal(QPoint(28, self.height()))
                CardPopup(self.win, kids[0].id, at, "down", self).show()
        else:
            super().keyPressEvent(e)
