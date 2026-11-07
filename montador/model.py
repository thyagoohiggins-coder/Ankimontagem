"""Modelo de dados do Montador de Flashcards.

Cada card tem front/back em HTML (formato do Qt). Um trecho destacado no back
de um card é uma âncora ``hl:<id>`` que aponta para o sub-card criado a partir
dele. A ordem de estudo vai do último sub-card criado até o card raiz.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field

HL_PREFIX = "hl:"


@dataclass
class Card:
    id: str
    parent_id: str | None
    seq: int
    front: str = ""
    back: str = ""
    snippet: str = ""          # trecho do back do card pai que originou este card
    created: float = field(default_factory=time.time)


class Store:
    def __init__(self) -> None:
        self.cards: dict[str, Card] = {}
        self.roots: list[str] = []
        self.seq = 0
        self.current_root: str | None = None

    # ---------- criação / remoção ----------
    def create_card(self, parent_id: str | None = None, front: str = "", snippet: str = "") -> Card:
        self.seq += 1
        card = Card(id=uuid.uuid4().hex[:12], parent_id=parent_id, seq=self.seq, front=front, snippet=snippet)
        self.cards[card.id] = card
        if parent_id is None:
            self.roots.append(card.id)
        return card

    def delete_subtree(self, card_id: str) -> list[str]:
        removed = [c.id for c in self.subtree(card_id)]
        for cid in removed:
            self.cards.pop(cid, None)
        if card_id in self.roots:
            self.roots.remove(card_id)
            if self.current_root == card_id:
                self.current_root = self.roots[0] if self.roots else None
        return removed

    # ---------- consultas ----------
    def get(self, card_id: str | None) -> Card | None:
        return self.cards.get(card_id) if card_id else None

    def children(self, card_id: str) -> list[Card]:
        return sorted((c for c in self.cards.values() if c.parent_id == card_id), key=lambda c: c.seq)

    def subtree(self, card_id: str) -> list[Card]:
        out: list[Card] = []
        stack = [card_id]
        while stack:
            c = self.cards.get(stack.pop())
            if not c:
                continue
            out.append(c)
            stack.extend(ch.id for ch in reversed(self.children(c.id)))
        return out

    def path(self, card_id: str) -> list[Card]:
        out: list[Card] = []
        c = self.cards.get(card_id)
        while c:
            out.insert(0, c)
            c = self.cards.get(c.parent_id) if c.parent_id else None
        return out

    def depth(self, card_id: str) -> int:
        return len(self.path(card_id)) - 1

    def root_of(self, card_id: str) -> Card:
        return self.path(card_id)[0]

    def direct_count(self, card_id: str) -> int:
        """Trechos destacados no back deste card (= sub-cards diretos)."""
        return len(self.children(card_id))

    def total_count(self, card_id: str) -> int:
        """Trechos destacados a partir deste card (todos os descendentes)."""
        return len(self.subtree(card_id)) - 1

    def timeline(self, root_id: str) -> list[Card]:
        """Cards da árvore na ordem em que foram criados."""
        return sorted(self.subtree(root_id), key=lambda c: c.seq)

    def study_order(self, root_id: str) -> list[Card]:
        """O último sub-card adicionado é o primeiro; o card raiz é o último."""
        return sorted(self.subtree(root_id), key=lambda c: -c.seq)

    def max_depth(self, root_id: str) -> int:
        return max((self.depth(c.id) for c in self.subtree(root_id)), default=0)

    # ---------- persistência ----------
    def to_dict(self) -> dict:
        return {
            "version": 2,
            "seq": self.seq,
            "roots": self.roots,
            "current_root": self.current_root,
            "cards": [asdict(c) for c in self.cards.values()],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Store":
        if not isinstance(data, dict) or "cards" not in data or "roots" not in data:
            raise ValueError("arquivo não é um baralho do Montador de Flashcards")
        s = cls()
        for raw in data["cards"]:
            c = Card(**{k: raw[k] for k in Card.__dataclass_fields__ if k in raw})
            s.cards[c.id] = c
        s.roots = [r for r in data["roots"] if r in s.cards]
        s.seq = max([data.get("seq", 0)] + [c.seq for c in s.cards.values()])
        s.current_root = data.get("current_root") if data.get("current_root") in s.cards else None
        if s.current_root is None and s.roots:
            s.current_root = s.roots[0]
        return s

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)

    @classmethod
    def load(cls, path: str) -> "Store":
        with open(path, encoding="utf-8") as f:
            return cls.from_dict(json.load(f))
