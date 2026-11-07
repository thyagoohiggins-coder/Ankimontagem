"""Preferências do usuário guardadas entre sessões (registro do Windows / arquivo de configuração)."""
from __future__ import annotations

import json

from PySide6.QtCore import QSettings

ORG = "MontadorFlashcards"
APP = "Montador de Flashcards"


def _s() -> QSettings:
    return QSettings(ORG, APP)


def get_json(key: str, default):
    raw = _s().value(key)
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return default


def set_json(key: str, value) -> None:
    s = _s()
    s.setValue(key, json.dumps(value))
    s.sync()


def get_int(key: str, default: int) -> int:
    try:
        return int(_s().value(key, default))
    except (TypeError, ValueError):
        return default


def set_value(key: str, value) -> None:
    s = _s()
    s.setValue(key, value)
    s.sync()
