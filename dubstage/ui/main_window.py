"""
DubStage Primary MainWindow & Studio Application Controller
Tab navigation, global shortcuts dispatcher, high-DPI viewport scaling, and studio lifecycle management
"""

import sys
from pathlib import Path
from typing import Optional
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .components import VideoMonitor, WaveformCanvas
from .forge_view import ForgeView
from .settings_dialog import SettingsDialog
from .shortcuts import ShortcutsCheatsheetDialog
from .stage_view import StageView
from .theme import STUDIO_QSS
from ..config import APP_DISPLAY_NAME, APP_NAME, APP_VERSION
from ..data.repository import DubStageRepository
from ..engine.mixer_engine import PcmSoftwareMixerEngine
from ..engine.model_manager import ModelManager
from ..models import ProjectEntity, StudioAuditionMode

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_DISPLAY_NAME} v{APP_VERSION}")

        # Core Services
        self.repository = DubStageRepository()
        self.model_manager = ModelManager()
        self.mixer_engine = PcmSoftwareMixerEngine()

        # Shared Interactive Components across workspaces
        self.video_monitor = VideoMonitor()
        self.waveform_canvas = WaveformCanvas()

        self._active_project: Optional[ProjectEntity] = None

        self._init_window_geometry()
        self._init_ui()
        self._setup_shortcuts()
        self._load_last_project()

    def _init_window_geometry(self):
        """Clamp window size safely to desktop work area for any display scaling (100%-200%)"""
        screen = QApplication.primaryScreen()
        if screen:
            work_geo = screen.availableGeometry()
            # 85% of available width & height, minimum 1100x680
            target_w = max(1100, int(work_geo.width() * 0.85))
            target_h = max(680, int(work_geo.height() * 0.85))

            # Clamp so it never overflows screen bounds
            final_w = min(target_w, work_geo.width())
            final_h = min(target_h, work_geo.height())
            x = work_geo.x() + (work_geo.width() - final_w) // 2
            y = work_geo.y() + (work_geo.height() - final_h) // 2
            self.setGeometry(x, y, final_w, final_h)
        else:
            self.resize(1280, 800)

        # Set App Icon if present
        icon_path = Path(__file__).resolve().parent.parent.parent / "Assets" / "Square44x44Logo.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

    def _init_ui(self):
        self.setStyleSheet(STUDIO_QSS)

        central_widget = QWidget()
        central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Top Studio Header Bar
        header_bar = QFrame()
        header_bar.setStyleSheet("background-color: #12151D; border-bottom: 1px solid #1E2332; padding: 4px 12px;")
        hdr_layout = QHBoxLayout(header_bar)
        hdr_layout.setContentsMargins(8, 4, 8, 4)

        logo_label = QLabel("🎙️ DUBSTAGE STUDIO")
        logo_label.setStyleSheet("font-size: 15px; font-weight: 900; color: #8B5CF6; letter-spacing: 1px;")
        hdr_layout.addWidget(logo_label)

        hdr_layout.addStretch()

        # Shortcuts Guide Button
        sc_btn = QPushButton("Shortcuts (F1)")
        sc_btn.setStyleSheet("""
            QPushButton {
                background-color: #1C202C;
                border: 1px solid #2F354A;
                color: #CBD5E1;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 10px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #272C3D; border-color: #8B5CF6; }
        """)
        sc_btn.clicked.connect(self._open_shortcuts_dialog)
        hdr_layout.addWidget(sc_btn)

        # Settings Button
        settings_btn = QPushButton("⚙ Settings (Ctrl+M)")
        settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #1C202C;
                border: 1px solid #2F354A;
                color: #CBD5E1;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 12px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #272C3D; border-color: #8B5CF6; }
        """)
        settings_btn.clicked.connect(self._open_settings_dialog)
        hdr_layout.addWidget(settings_btn)

        root_layout.addWidget(header_bar)

        # Primary Workspaces Tab Widget
        self.tabs = QTabWidget()
        self.forge_view = ForgeView(self.repository, self.model_manager, self.video_monitor, self.waveform_canvas)
        self.stage_view = StageView(self.repository, self.video_monitor, self.waveform_canvas, self.mixer_engine)

        self.tabs.addTab(self.forge_view, "1. DUBFORGE (Separation & Cues)")
        self.tabs.addTab(self.stage_view, "2. DUBSTAGE (Booth & Takes)")

        root_layout.addWidget(self.tabs, 1)

        # Connect inter-view signals
        self.forge_view.project_updated.connect(self._on_project_updated)
        self.forge_view.clip_selected.connect(self.stage_view.set_active_clip)
        self.forge_view.request_switch_to_stage.connect(lambda: self.tabs.setCurrentIndex(1))

        self.waveform_canvas.seek_requested.connect(self._on_waveform_seek)
        self.waveform_canvas.clip_selected.connect(self._on_clip_selected_from_canvas)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready. Press Space to Play/Pause, R to Record Take, F1 for Shortcuts.")

    def _setup_shortcuts(self):
        """Bind global DAW keyboard shortcuts across all window elements"""
        # Space: Play/Pause Toggle
        sc_space = QShortcut(QKeySequence(Qt.Key.Key_Space), self)
        sc_space.activated.connect(self.stage_view.toggle_playback)

        # R: Record Take Toggle
        sc_r = QShortcut(QKeySequence(Qt.Key.Key_R), self)
        sc_r.activated.connect(self.stage_view.toggle_record_take)

        # S: Slice Clip at Playhead
        sc_s = QShortcut(QKeySequence(Qt.Key.Key_S), self)
        sc_s.activated.connect(self.forge_view.slice_clip_at_playhead)

        # Ctrl+O: Import Video
        sc_o = QShortcut(QKeySequence("Ctrl+O"), self)
        sc_o.activated.connect(self.forge_view.prompt_import_video)

        # Ctrl+D: Separate Stems
        sc_d = QShortcut(QKeySequence("Ctrl+D"), self)
        sc_d.activated.connect(self.forge_view.start_demucs_separation)

        # Ctrl+Shift+V: Run VAD
        sc_v = QShortcut(QKeySequence("Ctrl+Shift+V"), self)
        sc_v.activated.connect(self.forge_view.run_auto_vad)

        # Ctrl+E: Export Master MP4
        sc_e = QShortcut(QKeySequence("Ctrl+E"), self)
        sc_e.activated.connect(self.stage_view.export_master_mp4)

        # Ctrl+M: Settings
        sc_m = QShortcut(QKeySequence("Ctrl+M"), self)
        sc_m.activated.connect(self._open_settings_dialog)

        # F1: Shortcuts Guide
        sc_f1 = QShortcut(QKeySequence(Qt.Key.Key_F1), self)
        sc_f1.activated.connect(self._open_shortcuts_dialog)

        # F11: Fullscreen Toggle
        sc_f11 = QShortcut(QKeySequence(Qt.Key.Key_F11), self)
        sc_f11.activated.connect(self._toggle_fullscreen)

        # Esc: Stop Playback / Cancel
        sc_esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        sc_esc.activated.connect(self._on_escape_pressed)

        # Left / Right: Nudge 1s
        sc_left = QShortcut(QKeySequence(Qt.Key.Key_Left), self)
        sc_left.activated.connect(lambda: self._nudge_playhead(-1000))

        sc_right = QShortcut(QKeySequence(Qt.Key.Key_Right), self)
        sc_right.activated.connect(lambda: self._nudge_playhead(1000))

        # Shift+Left / Shift+Right: Nudge 5s
        sc_sleft = QShortcut(QKeySequence("Shift+Left"), self)
        sc_sleft.activated.connect(lambda: self._nudge_playhead(-5000))

        sc_sright = QShortcut(QKeySequence("Shift+Right"), self)
        sc_sright.activated.connect(lambda: self._nudge_playhead(5000))

        # Delete: Delete active take
        sc_del = QShortcut(QKeySequence(Qt.Key.Key_Delete), self)
        sc_del.activated.connect(self.stage_view.delete_selected_take)

        # Audition Modes 1-6
        for mode_num, mode in enumerate([
            StudioAuditionMode.FULL_DUB_MIX,
            StudioAuditionMode.ORIGINAL_WITH_RESIDUAL,
            StudioAuditionMode.RECORDED_WITH_RESIDUAL,
            StudioAuditionMode.SOLO_ORIGINAL,
            StudioAuditionMode.SOLO_ACTIVE_TAKE,
            StudioAuditionMode.BACKING_ONLY
        ], 1):
            sc_num = QShortcut(QKeySequence(str(mode_num)), self)
            sc_num.activated.connect(lambda m=mode_num-1: self.stage_view.mode_combo.setCurrentIndex(m))

    def _nudge_playhead(self, delta_ms: int):
        new_ms = max(0, self.waveform_canvas._playhead_ms + delta_ms)
        self._on_waveform_seek(new_ms)

    def _on_waveform_seek(self, target_ms: int):
        self.video_monitor.seek(target_ms)
        if self.mixer_engine.is_playing:
            self.stage_view.toggle_playback()
            self.stage_view.toggle_playback()

    def _on_clip_selected_from_canvas(self, clip_id: str):
        self.forge_view.set_project(self._active_project)
        self.stage_view.set_active_clip(clip_id)

    def _on_escape_pressed(self):
        if self.mixer_engine.is_playing:
            self.stage_view.toggle_playback()
        if self.stage_view.recording_engine.is_recording:
            self.stage_view.toggle_record_take()

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def _open_shortcuts_dialog(self):
        dlg = ShortcutsCheatsheetDialog(self)
        dlg.exec()

    def _open_settings_dialog(self):
        dlg = SettingsDialog(self.model_manager, self)
        dlg.exec()

    def _on_project_updated(self, project: ProjectEntity):
        self._active_project = project
        self.stage_view.set_project(project)
        self.setWindowTitle(f"{APP_NAME} - {project.title} (v{APP_VERSION})")
        self.status_bar.showMessage(f"Loaded Project: {project.title} ({project.video_duration_ms / 1000.0:.1f}s)")

    def _load_last_project(self):
        projects = self.repository.get_all_projects()
        if projects:
            self.forge_view.set_project(projects[0])
            self._on_project_updated(projects[0])

    def closeEvent(self, event):
        self.mixer_engine.stop()
        self.stage_view.recording_engine.stop_recording()
        self.video_monitor.stop()
        super().closeEvent(event)
