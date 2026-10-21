"""
DubStage Dual-Waveform Synchronizer Canvas
Interactive QPainter waveform renderer with cue bounding boxes, playhead scrub, and dual-track comparison
"""

from typing import List, Optional
import numpy as np
from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QLinearGradient, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from ...models import ClipEntity
from ..theme import format_timecode

class WaveformCanvas(QWidget):
    seek_requested = pyqtSignal(int)      # ms
    clip_selected = pyqtSignal(str)       # clip_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(140)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

        self._duration_ms: int = 60000
        self._playhead_ms: int = 0

        self._reference_peaks: np.ndarray = np.zeros(0, dtype=np.float32)
        self._take_peaks: np.ndarray = np.zeros(0, dtype=np.float32)

        self._clips: List[ClipEntity] = []
        self._active_clip_id: Optional[str] = None

        self._is_dragging_playhead = False

    def set_duration(self, duration_ms: int):
        self._duration_ms = max(1000, duration_ms)
        self.update()

    def set_playhead(self, playhead_ms: int):
        self._playhead_ms = max(0, min(self._duration_ms, playhead_ms))
        self.update()

    def set_reference_peaks(self, peaks: np.ndarray):
        self._reference_peaks = peaks
        self.update()

    def set_take_peaks(self, peaks: np.ndarray):
        self._take_peaks = peaks
        self.update()

    def set_clips(self, clips: List[ClipEntity], active_clip_id: Optional[str] = None):
        self._clips = clips
        self._active_clip_id = active_clip_id
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging_playhead = True
            self._handle_mouse_seek(event.pos().x())

            # Check if clicked on a dialogue cue
            clicked_ms = int((event.pos().x() / max(1, self.width())) * self._duration_ms)
            for c in self._clips:
                if c.start_ms <= clicked_ms <= c.end_ms:
                    self._active_clip_id = c.id
                    self.clip_selected.emit(c.id)
                    break

    def mouseMoveEvent(self, event):
        if self._is_dragging_playhead:
            self._handle_mouse_seek(event.pos().x())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging_playhead = False

    def _handle_mouse_seek(self, x_pos: float):
        w = max(1, self.width())
        pct = max(0.0, min(1.0, x_pos / w))
        target_ms = int(pct * self._duration_ms)
        self._playhead_ms = target_ms
        self.seek_requested.emit(target_ms)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)

        w = self.width()
        h = self.height()

        # Background
        painter.fillRect(0, 0, w, h, QColor("#0A0C11"))

        # Center separator dividing reference track (top) & take track (bottom)
        half_h = h / 2.0
        painter.setPen(QPen(QColor("#1F2433"), 1))
        painter.drawLine(0, int(half_h), w, int(half_h))

        # Time ruler tick marks (every 5 seconds or 10 seconds depending on duration)
        tick_interval_ms = 5000 if self._duration_ms <= 60000 else 10000
        total_ticks = self._duration_ms // tick_interval_ms
        painter.setPen(QPen(QColor("#1A202E"), 1))
        painter.setFont(QFont("Segoe UI", 8))

        for t in range(total_ticks + 1):
            t_ms = t * tick_interval_ms
            x = int((t_ms / self._duration_ms) * w)
            painter.drawLine(x, 0, x, h)
            if x < w - 40:
                painter.setPen(QColor("#475569"))
                painter.drawText(x + 4, 12, format_timecode(t_ms))
                painter.setPen(QPen(QColor("#1A202E"), 1))

        # Draw Dialogue Cue Bounding Boxes
        for clip in self._clips:
            x_start = (clip.start_ms / self._duration_ms) * w
            x_end = (clip.end_ms / self._duration_ms) * w
            cue_w = max(4.0, x_end - x_start)

            is_active = (clip.id == self._active_clip_id)
            cue_color = QColor(139, 92, 246, 50) if is_active else QColor(30, 41, 59, 80)
            border_color = QColor(139, 92, 246, 200) if is_active else QColor(71, 85, 105, 120)

            painter.fillRect(QRectF(x_start, 0, cue_w, h), QBrush(cue_color))
            painter.setPen(QPen(border_color, 1))
            painter.drawRect(QRectF(x_start, 0, cue_w, h))

            # Cue Tag
            tag_text = f"#{clip.clip_index} {clip.speaker_name}"
            painter.setPen(QColor("#CBD5E1") if is_active else QColor("#64748B"))
            painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold if is_active else QFont.Weight.Normal))
            painter.drawText(int(x_start + 4), int(half_h - 6), tag_text)

        # Draw Top Track Waveform: Original Vocal Stem (Purple / Magenta)
        if len(self._reference_peaks) > 0:
            ref_grad = QLinearGradient(0, 0, 0, half_h)
            ref_grad.setColorAt(0.0, QColor("#C084FC"))
            ref_grad.setColorAt(1.0, QColor("#7C3AED"))
            painter.setPen(QPen(QBrush(ref_grad), 1))

            num_points = len(self._reference_peaks)
            for i in range(num_points):
                x = (i / num_points) * w
                amp = self._reference_peaks[i] * (half_h - 16.0)
                y1 = half_h - amp
                y2 = half_h
                painter.drawLine(QPointF(x, y1), QPointF(x, y2))

        # Draw Bottom Track Waveform: Actor Take (Emerald Green)
        if len(self._take_peaks) > 0:
            take_grad = QLinearGradient(0, half_h, 0, h)
            take_grad.setColorAt(0.0, QColor("#10B981"))
            take_grad.setColorAt(1.0, QColor("#047857"))
            painter.setPen(QPen(QBrush(take_grad), 1))

            num_points = len(self._take_peaks)
            for i in range(num_points):
                x = (i / num_points) * w
                amp = self._take_peaks[i] * (half_h - 16.0)
                y1 = half_h
                y2 = half_h + amp
                painter.drawLine(QPointF(x, y1), QPointF(x, y2))

        # Track Labels
        painter.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        painter.setPen(QColor("#A855F7"))
        painter.drawText(8, 26, "REFERENCE VOCALS")

        painter.setPen(QColor("#10B981"))
        painter.drawText(8, int(half_h + 20), "RECORDED TAKE")

        # Draw Scrub Playhead Cursor (Amber #F59E0B)
        playhead_x = (self._playhead_ms / self._duration_ms) * w
        painter.setPen(QPen(QColor("#F59E0B"), 2))
        painter.drawLine(int(playhead_x), 0, int(playhead_x), h)

        # Playhead triangle cap
        painter.setBrush(QBrush(QColor("#F59E0B")))
        painter.drawPolygon([
            QPointF(playhead_x - 5, 0),
            QPointF(playhead_x + 5, 0),
            QPointF(playhead_x, 8)
        ])
