"""
DubStage Demucs Model Downloader Card Component
Status reporting, Hugging Face resumable download trigger, progress tracking, and model sideloading
"""

import threading
from typing import Optional
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from ...engine.model_manager import ModelManager, ModelStatus
from ...models.presets import ModelPreset

class ModelDownloaderCard(QFrame):
    model_ready_changed = pyqtSignal(bool)
    status_updated = pyqtSignal(str)

    def __init__(self, model_manager: ModelManager, parent=None):
        super().__init__(parent)
        self.model_manager = model_manager
        self.setObjectName("ModelCard")
        self.setStyleSheet("""
            QFrame#ModelCard {
                background-color: #161922;
                border: 1px solid #232736;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # Header Row
        header_row = QHBoxLayout()
        title_lbl = QLabel("Demucs v4 Neural Separation Model")
        title_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #F1F5F9;")
        header_row.addWidget(title_lbl)

        header_row.addStretch()

        self.status_badge = QLabel("Checking...")
        self.status_badge.setStyleSheet("""
            background-color: #242938;
            color: #94A3B8;
            border-radius: 4px;
            padding: 3px 8px;
            font-size: 11px;
            font-weight: 600;
        """)
        header_row.addWidget(self.status_badge)
        layout.addLayout(header_row)

        # Preset Selector
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Model Preset:"))

        self.preset_combo = QComboBox()
        for p in ModelPreset:
            self.preset_combo.addItem(p.display_name, p)
        self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        preset_row.addWidget(self.preset_combo, 1)

        layout.addLayout(preset_row)

        # Description
        self.desc_label = QLabel(self.model_manager.active_preset.description)
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet("color: #94A3B8; font-size: 12px;")
        layout.addWidget(self.desc_label)

        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Controls Row
        ctrl_row = QHBoxLayout()
        self.download_btn = QPushButton("Download Model (166 MB)")
        self.download_btn.setObjectName("DownloadBtn")
        self.download_btn.setStyleSheet("""
            QPushButton#DownloadBtn {
                background-color: #8B5CF6;
                color: #FFFFFF;
                font-weight: 600;
                padding: 6px 16px;
            }
            QPushButton#DownloadBtn:hover { background-color: #7C3AED; }
        """)
        self.download_btn.clicked.connect(self._start_download)
        ctrl_row.addWidget(self.download_btn)

        self.sideload_btn = QPushButton("Sideload .onnx")
        self.sideload_btn.clicked.connect(self._sideload_model)
        ctrl_row.addWidget(self.sideload_btn)

        ctrl_row.addStretch()
        layout.addLayout(ctrl_row)

        self.refresh_status()

    def _on_preset_changed(self, index: int):
        preset = self.preset_combo.currentData()
        if preset:
            self.model_manager.set_model_preset(preset)
            self.desc_label.setText(preset.description)
            self.refresh_status()

    def refresh_status(self):
        status = self.model_manager.check_status()
        if status.is_ready:
            self.status_badge.setText("Ready")
            self.status_badge.setStyleSheet("background-color: #064E3B; color: #34D399; border-radius: 4px; padding: 3px 8px; font-weight: 600;")
            self.download_btn.setText("Re-Download Model")
            self.download_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            self.model_ready_changed.emit(True)
        else:
            self.status_badge.setText("Missing")
            self.status_badge.setStyleSheet("background-color: #451A03; color: #FBBF24; border-radius: 4px; padding: 3px 8px; font-weight: 600;")
            self.download_btn.setText("Download Model (166 MB)")
            self.download_btn.setEnabled(True)
            self.model_ready_changed.emit(False)

    def _start_download(self):
        self.download_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_badge.setText("Downloading...")
        self.status_badge.setStyleSheet("background-color: #1E1B4B; color: #A78BFA; border-radius: 4px; padding: 3px 8px; font-weight: 600;")

        def progress_callback(status: ModelStatus):
            self.progress_bar.setValue(status.percent)
            self.status_updated.emit(status.message)

        def worker():
            try:
                self.model_manager.download_model(on_progress=progress_callback)
            except Exception as e:
                pass
            finally:
                self.refresh_status()

        threading.Thread(target=worker, daemon=True).start()

    def _sideload_model(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Pre-Downloaded Demucs ONNX Model",
            "",
            "ONNX Models (*.onnx)"
        )
        if file_path:
            try:
                self.model_manager.sideload_model(file_path)
                self.refresh_status()
            except Exception as e:
                self.status_updated.emit(f"Sideload failed: {e}")
