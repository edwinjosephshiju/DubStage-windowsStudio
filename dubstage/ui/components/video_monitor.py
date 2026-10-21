"""
DubStage Video Monitor Component
Hardware-accelerated video playback with SMPTE timecode overlay and responsive letterboxing
"""

import os
from pathlib import Path
from typing import Optional
from PyQt6.QtCore import QTime, QUrl, Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPainter, QColor
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ..theme import format_timecode

class VideoMonitor(QFrame):
    position_changed = pyqtSignal(int)  # ms
    duration_changed = pyqtSignal(int)  # ms

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("VideoMonitorCard")
        self.setStyleSheet("""
            QFrame#VideoMonitorCard {
                background-color: #07090C;
                border: 1px solid #1C202C;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Video Surface
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: #000000; border-radius: 6px;")
        layout.addWidget(self.video_widget, 1)

        # Player Engine
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)

        # Timecode overlay bar
        bar_layout = QHBoxLayout()
        bar_layout.setContentsMargins(8, 2, 8, 4)

        self.timecode_label = QLabel("00:00.000 / 00:00.000")
        self.timecode_label.setStyleSheet("font-family: monospace; font-size: 12px; font-weight: 700; color: #10B981;")
        bar_layout.addWidget(self.timecode_label)

        bar_layout.addStretch()

        self.res_label = QLabel("1080p")
        self.res_label.setStyleSheet("font-size: 11px; font-weight: 600; color: #64748B;")
        bar_layout.addWidget(self.res_label)

        layout.addLayout(bar_layout)

        # Connect signals
        self.player.positionChanged.connect(self._on_pos_changed)
        self.player.durationChanged.connect(self._on_dur_changed)

        self._duration_ms = 0
        self._current_pos_ms = 0

    def load_video(self, video_path: str, width: int = 1920, height: int = 1080):
        if os.path.exists(video_path):
            url = QUrl.fromLocalFile(str(Path(video_path).resolve()))
            self.player.setSource(url)
            self.res_label.setText(f"{width}x{height}")
            self.seek(0)

    def play(self):
        self.player.play()

    def pause(self):
        self.player.pause()

    def stop(self):
        self.player.stop()

    def seek(self, position_ms: int):
        self._current_pos_ms = position_ms
        self.player.setPosition(position_ms)
        self._update_timecode_text()

    def set_muted(self, muted: bool):
        self.audio_output.setMuted(muted)

    def set_volume(self, volume: float):
        self.audio_output.setVolume(max(0.0, min(1.0, volume)))

    def _on_pos_changed(self, pos_ms: int):
        self._current_pos_ms = pos_ms
        self._update_timecode_text()
        self.position_changed.emit(pos_ms)

    def _on_dur_changed(self, dur_ms: int):
        self._duration_ms = dur_ms
        self._update_timecode_text()
        self.duration_changed.emit(dur_ms)

    def _update_timecode_text(self):
        curr_str = format_timecode(self._current_pos_ms)
        dur_str = format_timecode(self._duration_ms)
        self.timecode_label.setText(f"{curr_str} / {dur_str}")
