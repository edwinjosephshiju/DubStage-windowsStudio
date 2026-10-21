"""
DubStage Centralized Keyboard Shortcuts System
Provides complete keyboard-driven studio DAW workflow with modal cheatsheet
"""

from dataclasses import dataclass
from typing import Callable, List, Optional
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

@dataclass
class ShortcutDefinition:
    key_sequence: str
    action_name: str
    category: str
    description: str

SHORTCUTS_CATALOG: List[ShortcutDefinition] = [
    # Transport & Playback
    ShortcutDefinition("Space", "Toggle Play / Pause", "Transport", "Play or pause audio/video at current playhead position"),
    ShortcutDefinition("R", "Record / Stop Take", "Transport", "Initiate 3s pre-roll countdown and record hardware vocal take"),
    ShortcutDefinition("Left", "Nudge Back 1s", "Transport", "Step playhead backward by 1 second"),
    ShortcutDefinition("Right", "Nudge Forward 1s", "Transport", "Step playhead forward by 1 second"),
    ShortcutDefinition("Shift+Left", "Nudge Back 5s", "Transport", "Step playhead backward by 5 seconds"),
    ShortcutDefinition("Shift+Right", "Nudge Forward 5s", "Transport", "Step playhead forward by 5 seconds"),
    ShortcutDefinition("Esc", "Stop / Cancel", "Transport", "Immediately stop playback, recording, or dismiss open dialogs"),

    # Navigation & Cue Editing
    ShortcutDefinition("Up", "Previous Dialogue Cue", "Editing", "Navigate to and highlight the previous dialogue span"),
    ShortcutDefinition("Down", "Next Dialogue Cue", "Editing", "Navigate to and highlight the next dialogue span"),
    ShortcutDefinition("[", "Previous Cue (Alt)", "Editing", "Bracket shortcut to select previous cue"),
    ShortcutDefinition("]", "Next Cue (Alt)", "Editing", "Bracket shortcut to select next cue"),
    ShortcutDefinition("S", "Slice Cue at Playhead", "Editing", "Split the active dialogue cue precisely at the playhead"),
    ShortcutDefinition("Delete", "Delete Active Take", "Editing", "Delete the currently active recorded vocal take"),

    # Audition Modes
    ShortcutDefinition("1", "Full Dub Mix", "Audition", "Audition Backing + Recorded user takes (with original fills)"),
    ShortcutDefinition("2", "Original + Residual", "Audition", "Audition original vocals with phase-perfect backing"),
    ShortcutDefinition("3", "Recorded + Residual", "Audition", "Audition recorded actor take with backing stem"),
    ShortcutDefinition("4", "Solo Original Vocals", "Audition", "Solo original vocal stem only"),
    ShortcutDefinition("5", "Solo Active Take", "Audition", "Solo currently highlighted user take only"),
    ShortcutDefinition("6", "Backing Only", "Audition", "Audition instrumental backing stem only (karaoke)"),

    # Studio Operations
    ShortcutDefinition("Ctrl+O", "Import Video File", "Operations", "Open file picker to ingest a new MP4/MKV video"),
    ShortcutDefinition("Ctrl+D", "Start Stem Separation", "Operations", "Execute Demucs v4 ONNX neural stem separation"),
    ShortcutDefinition("Ctrl+Shift+V", "Run Auto-VAD Detection", "Operations", "Detect acoustic dialogue cues automatically"),
    ShortcutDefinition("Ctrl+E", "Export Master MP4", "Operations", "Open master MP4 and subtitle export dialog"),
    ShortcutDefinition("Ctrl+M", "AI Model Manager", "Operations", "Open Demucs model download and backend settings"),
    ShortcutDefinition("F11", "Toggle Fullscreen", "View", "Toggle borderless fullscreen studio window"),
    ShortcutDefinition("F1", "Keyboard Shortcuts", "Help", "Display complete keyboard shortcuts cheatsheet"),
]

class ShortcutsCheatsheetDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("DubStage - Studio Keyboard Shortcuts")
        self.resize(650, 520)
        self.setStyleSheet("""
            QDialog {
                background-color: #12151D;
                color: #F1F5F9;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        header = QLabel("Studio Keyboard Shortcuts")
        header.setStyleSheet("font-size: 18px; font-weight: 700; color: #8B5CF6;")
        layout.addWidget(header)

        sub = QLabel("Master every DubStage workflow with precision keyboard commands:")
        sub.setStyleSheet("color: #94A3B8; font-size: 12px;")
        layout.addWidget(sub)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #232736; border-radius: 8px; background-color: #161922; }")

        content_widget = QWidget()
        grid = QGridLayout(content_widget)
        grid.setContentsMargins(16, 16, 16, 16)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)

        current_category = ""
        row = 0

        for sc in SHORTCUTS_CATALOG:
            if sc.category != current_category:
                current_category = sc.category
                cat_label = QLabel(current_category.upper())
                cat_label.setStyleSheet("color: #10B981; font-weight: 700; font-size: 11px; margin-top: 8px;")
                grid.addWidget(cat_label, row, 0, 1, 3)
                row += 1

            key_badge = QLabel(f"  {sc.key_sequence}  ")
            key_badge.setStyleSheet("""
                background-color: #242938;
                color: #F8FAFC;
                border: 1px solid #3F4761;
                border-radius: 4px;
                font-family: monospace;
                font-weight: 700;
                font-size: 12px;
                padding: 2px 6px;
            """)
            action_lbl = QLabel(sc.action_name)
            action_lbl.setStyleSheet("font-weight: 600; color: #F1F5F9;")

            desc_lbl = QLabel(sc.description)
            desc_lbl.setStyleSheet("color: #94A3B8; font-size: 11px;")

            grid.addWidget(key_badge, row, 0)
            grid.addWidget(action_lbl, row, 1)
            grid.addWidget(desc_lbl, row, 2)
            row += 1

        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #8B5CF6;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #7C3AED; }
        """)
        close_btn.clicked.connect(self.accept)
        btn_box.addWidget(close_btn)
        layout.addLayout(btn_box)
