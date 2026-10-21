"""
DubStage Studio Settings & Neural Backend Configuration Dialog
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ..shortcuts import ShortcutsCheatsheetDialog
from ...engine.model_manager import ModelManager
from ...models.presets import ExecutionBackend, KaraokeMode, ModelPreset

class SettingsDialog(QDialog):
    def __init__(self, model_manager: ModelManager, parent=None):
        super().__init__(parent)
        self.model_manager = model_manager
        self.setWindowTitle("DubStage Studio Settings")
        self.resize(520, 480)
        self.setStyleSheet("""
            QDialog {
                background-color: #12151D;
                color: #F1F5F9;
            }
            QGroupBox {
                border: 1px solid #232736;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 12px;
                font-weight: 700;
                color: #8B5CF6;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 4px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        header = QLabel("Studio Engine & AI Configuration")
        header.setStyleSheet("font-size: 16px; font-weight: 700; color: #F1F5F9;")
        layout.addWidget(header)

        # 1. Neural Separation Backend
        backend_grp = QGroupBox("Hardware Acceleration Backend")
        b_layout = QVBoxLayout(backend_grp)

        self.backend_combo = QComboBox()
        for b in ExecutionBackend:
            self.backend_combo.addItem(f"{b.label} - {b.subtitle}", b)

        # Select active
        curr_b_idx = next((i for i, b in enumerate(ExecutionBackend) if b == self.model_manager.active_backend), 0)
        self.backend_combo.setCurrentIndex(curr_b_idx)
        b_layout.addWidget(self.backend_combo)

        self.persist_backend_cb = QCheckBox("Persist backend choice as studio default")
        self.persist_backend_cb.setChecked(self.model_manager.persist_backend)
        b_layout.addWidget(self.persist_backend_cb)

        layout.addWidget(backend_grp)

        # 2. Separation Algorithm
        algo_grp = QGroupBox("Demucs Backing Separation Mode")
        a_layout = QVBoxLayout(algo_grp)

        self.algo_combo = QComboBox()
        for m in KaraokeMode:
            self.algo_combo.addItem(f"{m.label}", m)

        curr_m_idx = next((i for i, m in enumerate(KaraokeMode) if m == self.model_manager.active_karaoke_mode), 0)
        self.algo_combo.setCurrentIndex(curr_m_idx)
        a_layout.addWidget(self.algo_combo)

        self.algo_desc = QLabel(self.model_manager.active_karaoke_mode.description)
        self.algo_desc.setWordWrap(True)
        self.algo_desc.setStyleSheet("color: #94A3B8; font-size: 11px;")
        a_layout.addWidget(self.algo_desc)

        self.algo_combo.currentIndexChanged.connect(self._on_algo_changed)

        self.persist_algo_cb = QCheckBox("Persist algorithm choice as studio default")
        self.persist_algo_cb.setChecked(self.model_manager.persist_algorithm)
        a_layout.addWidget(self.persist_algo_cb)

        layout.addWidget(algo_grp)

        # 3. Keyboard Shortcuts Reference Button
        sc_btn = QPushButton("View Keyboard Shortcuts Cheatsheet (F1)")
        sc_btn.setStyleSheet("""
            QPushButton {
                background-color: #242938;
                border: 1px solid #3F4761;
                color: #F1F5F9;
                font-weight: 600;
                padding: 8px 16px;
            }
            QPushButton:hover { background-color: #2F364B; }
        """)
        sc_btn.clicked.connect(self._open_shortcuts_dialog)
        layout.addWidget(sc_btn)

        layout.addStretch()

        # Bottom Buttons
        btn_box = QHBoxLayout()
        btn_box.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        save_btn = QPushButton("Save Settings")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #8B5CF6;
                color: #FFFFFF;
                font-weight: 700;
                padding: 6px 20px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #7C3AED; }
        """)
        save_btn.clicked.connect(self._save_and_close)
        btn_box.addWidget(save_btn)

        layout.addLayout(btn_box)

    def _on_algo_changed(self, idx: int):
        mode = self.algo_combo.currentData()
        if mode:
            self.algo_desc.setText(mode.description)

    def _open_shortcuts_dialog(self):
        dlg = ShortcutsCheatsheetDialog(self)
        dlg.exec()

    def _save_and_close(self):
        backend = self.backend_combo.currentData()
        if backend:
            self.model_manager.set_execution_backend(backend)

        algo = self.algo_combo.currentData()
        if algo:
            self.model_manager.set_karaoke_mode(algo)

        self.model_manager.persist_backend = self.persist_backend_cb.isChecked()
        self.model_manager.persist_algorithm = self.persist_algo_cb.isChecked()
        self.model_manager.save_settings()
        self.accept()
