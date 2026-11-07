"""Tema claro e estilos da interface."""
from PySide6.QtGui import QColor, QPalette

QSS = """
QMainWindow, #studyPage { background: #f3f5f7; }
QWidget { font-family: "Segoe UI", "Noto Sans", sans-serif; font-size: 10pt; color: #1f2933; }
#topBar { background: white; border-bottom: 1px solid #e1e6eb; }
#stats { color: #6b7785; padding: 6px 14px; background: #f3f5f7; border-bottom: 1px solid #e8ecef; }
#timeline { background: #f3f5f7; }
QScrollArea { background: #f3f5f7; }

QPushButton { border: 1px solid #d5dce2; border-radius: 7px; padding: 6px 12px; background: white; }
QPushButton:hover { background: #eef3f6; }
QPushButton:disabled { color: #a5afb9; }
QPushButton#primary { background: #0a8f8b; color: white; border-color: #0a8f8b; font-weight: 600; }
QPushButton#primary:hover { background: #087571; }
QPushButton#primary:disabled { background: #9fd3d1; border-color: #9fd3d1; }
QPushButton#ghost { background: transparent; border-color: transparent; color: #0a8f8b; font-weight: 600; }
QPushButton#ghost:hover { background: #e3f4f3; }
QToolButton#ghostTool { border: none; border-radius: 7px; padding: 4px 9px; font-size: 13pt; color: #4b5763; }
QToolButton#ghostTool:hover { background: #eef3f6; }
QToolButton#ghostTool::menu-indicator { image: none; }
QComboBox { border: 1px solid #d5dce2; border-radius: 7px; padding: 5px 8px; background: white; font-weight: 600; }

#cardBox { background: white; border: 1px solid #e1e6eb; border-radius: 10px; }
#cardBox:hover { border-color: #b9c6d0; }
#cardBox[open="true"] { border: 2px solid #0a8f8b; }
#cardBox[flash="true"] { border: 2px solid #e11d2e; background: #fff5f5; }
#cardMeta { color: #8a96a3; font-size: 8pt; font-weight: 600; letter-spacing: 0.5px; }
#cardTitle { font-size: 10.5pt; font-weight: 600; }
#cardTitle[empty="true"] { color: #a5afb9; font-style: italic; font-weight: 400; }
#badge { background: #fde4e6; color: #e11d2e; border-radius: 10px; min-width: 20px; max-height: 20px;
         padding: 0 6px; font-weight: 700; font-size: 9pt; }
#badge[zero="true"] { background: #edf0f3; color: #8a96a3; }
#sideLabel { color: #8a96a3; font-size: 8pt; font-weight: 700; letter-spacing: 1px; }
#editorBox { border: 1px solid #dde3e9; border-radius: 8px; background: white; }
#editorBox:focus-within { border-color: #0a8f8b; }
QTextEdit, QTextBrowser { background: white; border: none; selection-background-color: #b3e5e3; selection-color: #111; }
QTextEdit#frontEditor, QTextBrowser#frontView { color: #1f2933; }
QTextEdit#backEditor, QTextBrowser#backView { color: #0ABAB5; }

#formatBar { background: white; border: 1px solid #cfd8df; border-radius: 9px; }
#formatBar QToolButton { border: none; border-radius: 6px; padding: 3px 6px; min-width: 22px; font-size: 10pt; }
#formatBar QToolButton:hover { background: #eef3f6; }
#formatBar QToolButton::menu-indicator { image: none; width: 0; }
#formatBar QToolButton#hlButton { color: #e11d2e; }
#formatBar QToolButton#hlButton:hover { background: #fde4e6; }

#cardPopup { background: white; border: 1px solid #b9c6d0; border-radius: 10px; }
#emptyMsg { color: #4b5763; font-size: 11pt; padding: 20px; }
#studyCard { background: white; border: 1px solid #e1e6eb; border-radius: 14px; }
#studyProgress { font-weight: 700; color: #4b5763; }
#studyOrigin { color: #6b7785; padding: 0 4px; }
#progressTrack { background: #e1e6eb; border-radius: 2px; }
#progressFill { background: #0ABAB5; border-radius: 2px; }
#hint { color: #a5afb9; font-size: 10pt; }
#bigNumber { color: #e11d2e; font-size: 40pt; font-weight: 800; }
#muted { color: #6b7785; }
QMenu { background: white; border: 1px solid #d5dce2; padding: 4px; }
QMenu::item { padding: 6px 22px 6px 12px; border-radius: 5px; }
QMenu::item:selected { background: #e3f4f3; color: #1f2933; }
QMenu::item:disabled { color: #a5afb9; }
QMenu::separator { height: 1px; background: #e8ecef; margin: 4px 6px; }
QStatusBar { background: white; color: #4b5763; border-top: 1px solid #e8ecef; }
QToolTip { background: #1f2933; color: white; border: none; padding: 5px; }
"""


def light_palette() -> QPalette:
    p = QPalette()
    for role, c in (
        (QPalette.Window, "#f3f5f7"), (QPalette.WindowText, "#1f2933"), (QPalette.Base, "#ffffff"),
        (QPalette.AlternateBase, "#f6f8fa"), (QPalette.Text, "#1f2933"), (QPalette.Button, "#ffffff"),
        (QPalette.ButtonText, "#1f2933"), (QPalette.Highlight, "#0a8f8b"), (QPalette.HighlightedText, "#ffffff"),
        (QPalette.ToolTipBase, "#1f2933"), (QPalette.ToolTipText, "#ffffff"), (QPalette.PlaceholderText, "#9aa5b1"),
        (QPalette.Link, "#0a8f8b"),
    ):
        p.setColor(role, QColor(c))
    return p
